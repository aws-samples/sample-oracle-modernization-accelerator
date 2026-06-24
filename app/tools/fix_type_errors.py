#!/usr/bin/env python3.11
"""
Fix type casting errors in target mapper files using LLM
"""

import json
import sys
import re
import boto3
from pathlib import Path
from typing import Dict, Optional
import os

# Environment variables are loaded by skill script via tools/load_oma_env.sh

class TypeErrorFixer:
    def __init__(self, model_id: str, region: str, dict_path: Path):
        self.model_id = model_id
        self.region = region
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)

        # Load Oracle dictionary for schema info
        self.oracle_dict = None
        if dict_path and dict_path.exists():
            with open(dict_path, 'r', encoding='utf-8') as f:
                self.oracle_dict = json.load(f)

    def extract_schema_info(self, xml_content: str) -> str:
        """Extract relevant schema information from Oracle dictionary"""
        if not self.oracle_dict or 'tables' not in self.oracle_dict:
            return ""

        schema_info = "\n=== Oracle Schema Information ===\n"

        # Find relevant tables (simple string matching, no regex)
        relevant_tables = []
        for table_name in self.oracle_dict['tables'].keys():
            if table_name in xml_content.upper():
                relevant_tables.append(table_name)

        # Add schema for relevant tables
        for table_name in relevant_tables[:5]:
            table_info = self.oracle_dict['tables'][table_name]
            schema_info += f"\nTable: {table_name}\n"

            for col in table_info.get('columns', [])[:20]:
                col_name = col.get('name', '')
                col_type = col.get('type', '')
                col_len = col.get('length', '')
                col_prec = col.get('precision', '')

                if col_len:
                    schema_info += f"  {col_name}: {col_type}({col_len})\n"
                elif col_prec:
                    schema_info += f"  {col_name}: {col_type}({col_prec})\n"
                else:
                    schema_info += f"  {col_name}: {col_type}\n"

        return schema_info

    def call_bedrock(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Call Bedrock API"""
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "system": system_prompt,
                "messages": [{"role": "user", "content": prompt}]
            }

            # Don't add temperature for Opus 4.8
            if not self.model_id.endswith('opus-4-8'):
                body["temperature"] = 0.0

            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )

            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']

        except Exception as e:
            print(f"  ✗ Bedrock error: {e}")
            return None

    def fix_sql(self, xml_path: Path, sql_id: str, pg_error: str) -> bool:
        """Fix type casting error in SQL file"""

        # Read current XML
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()

        # Check if this file references a fragment
        if '<include refid=' in xml_content:
            # Extract fragment id
            import re
            match = re.search(r'<include refid="([^"]+)"', xml_content)
            if match:
                fragment_id = match.group(1)
                # Find fragment file
                fragment_file = xml_path.parent / f"oms-common-sql-oracle_fragment_{fragment_id}.xml"
                if fragment_file.exists():
                    print(f"  → Fragment detected: {fragment_id}, fixing fragment file...")
                    return self.fix_sql(fragment_file, fragment_id, pg_error)
                else:
                    print(f"  ⚠ Fragment {fragment_id} not found, fixing current file...")

        # Extract schema information
        schema_info = self.extract_schema_info(xml_content)

        # System prompt - let LLM infer
        system_prompt = """You are a PostgreSQL SQL expert.

Fix the type casting error in the XML file based on the error message.
Analyze the error and the XML content to determine what needs to be changed."""

        # User prompt
        user_prompt = f"""A PostgreSQL type casting error occurred:

Error: {pg_error}

SQL ID: {sql_id}

Current XML content:
{xml_content}

{schema_info}

Fix the type casting error in this XML.
Return ONLY the complete fixed XML content with NO explanations, NO markdown, NO code blocks."""

        print(f"  → Calling LLM to fix {sql_id}...")

        fixed_xml = self.call_bedrock(user_prompt, system_prompt)

        if not fixed_xml:
            return False

        # Clean LLM response - extract XML only
        fixed_xml = fixed_xml.strip()

        # Remove markdown code blocks
        if '```xml' in fixed_xml:
            fixed_xml = fixed_xml.split('```xml')[1].split('```')[0]
        elif '```' in fixed_xml:
            fixed_xml = fixed_xml.split('```')[1].split('```')[0]

        # Extract from <?xml to last closing tag
        if '<?xml' in fixed_xml:
            xml_start = fixed_xml.index('<?xml')
            fixed_xml = fixed_xml[xml_start:]

        # Remove any trailing text after last >
        last_bracket = fixed_xml.rfind('>')
        if last_bracket != -1:
            fixed_xml = fixed_xml[:last_bracket + 1]

        fixed_xml = fixed_xml.strip()

        # Ensure XML declaration exists
        if not fixed_xml.startswith('<?xml'):
            fixed_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + fixed_xml

        # Save fixed XML
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(fixed_xml)

        print(f"  ✓ Fixed and saved: {xml_path.name}")
        return True

def main():
    if len(sys.argv) < 3:
        print("Usage: python3.11 fix_type_errors.py <type-cast-errors.json> <convert-dir>")
        print("Example: python3.11 fix_type_errors.py output/type-cast-errors.json mappers/daiso-oms/convert")
        sys.exit(1)

    error_report_path = Path(sys.argv[1])
    convert_dir = Path(sys.argv[2])
    dict_path = Path("output/oracle_dictionary.json")

    if not error_report_path.exists():
        print(f"Error: {error_report_path} not found")
        sys.exit(1)

    if not convert_dir.exists():
        print(f"Error: {convert_dir} not found")
        sys.exit(1)

    # Load error report
    with open(error_report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)

    errors = report.get('errors', [])

    if not errors:
        print("No type casting errors to fix!")
        sys.exit(0)

    # Initialize fixer
    model_id = os.getenv('BEDROCK_MODEL_ID', 'global.anthropic.claude-opus-4-8')
    region = os.getenv('BEDROCK_REGION', 'ap-northeast-2')

    fixer = TypeErrorFixer(model_id, region, dict_path)

    print(f"\n{'='*70}")
    print(f"Fixing {len(errors)} type casting errors")
    print(f"{'='*70}\n")

    fixed_count = 0
    failed_count = 0

    for error in errors:
        sql_id = error['sql_id']
        pg_error = error['pg_error']

        print(f"Processing: {sql_id}")
        print(f"  Error: {pg_error}")

        # Find convert XML file for this SQL
        # Pattern: oms-common-sql-oracle_<sql_id>.xml
        xml_file = convert_dir / f"oms-common-sql-oracle_{sql_id}.xml"

        if not xml_file.exists():
            # Try fragment pattern
            xml_file = convert_dir / f"oms-common-sql-oracle_fragment_{sql_id}.xml"

        if xml_file.exists():
            if fixer.fix_sql(xml_file, sql_id, pg_error):
                fixed_count += 1
            else:
                failed_count += 1
        else:
            print(f"  ✗ Convert file not found: {xml_file.name}")
            failed_count += 1

        print()

    print(f"{'='*70}")
    print(f"Summary:")
    print(f"  Fixed: {fixed_count}")
    print(f"  Failed: {failed_count}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
