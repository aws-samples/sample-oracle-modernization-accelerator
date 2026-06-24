#!/usr/bin/env python3
"""
SQL Converter using Bedrock LLM
Converts Oracle SQL to target database (PostgreSQL/MySQL) with explicit type casting
Generates test case files with bind variable mappings
"""

import os
import sys
import json
import boto3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class SQLConverter:
    """SQL converter using Bedrock LLM"""

    def __init__(self, source_dir: str, target_dir: str, dict_path: str,
                 target_db: str, bedrock_region: str, model_id: str, max_workers: int = 7):
        # Convert to absolute paths
        self.source_dir = Path(source_dir).resolve()
        self.target_dir = Path(target_dir).resolve()
        self.dict_path = Path(dict_path).resolve()

        # Validate paths
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {self.source_dir}")
        if not self.dict_path.exists():
            raise FileNotFoundError(f"Dictionary file not found: {self.dict_path}")

        # Create target directory
        self.target_dir.mkdir(parents=True, exist_ok=True)

        self.target_db = target_db
        self.bedrock_region = bedrock_region
        self.model_id = model_id
        self.max_workers = max_workers

        # Load Oracle dictionary
        self.oracle_dict = self.load_dictionary()

        # Initialize Bedrock client
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name=bedrock_region
        )

        # Thread lock for stats
        self.stats_lock = threading.Lock()
        self.stats = {
            'total_files': 0,
            'converted_files': 0,
            'failed_files': 0,
            'skipped_files': 0,
            'errors': [],
            'conversion_times': {},  # file -> seconds
            'llm_calls': {
                'table_extraction': 0,
                'sql_conversion': 0,
                'json_fix': 0
            },
            'tables_discovered': set(),
            'tables_matched': set(),
            'tables_not_found': set(),
            'total_bind_variables': 0,
            'total_test_cases': 0,
            'file_details': []  # List of per-file details
        }
        self.start_time = None
        self.end_time = None

    def load_dictionary(self) -> Dict:
        """Load Oracle dictionary"""
        if not self.dict_path.exists():
            print(f"Warning: Oracle dictionary not found at {self.dict_path}")
            return {}

        with open(self.dict_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def lookup_column(self, table_column: str) -> Optional[Dict[str, Any]]:
        """Lookup column info from dictionary"""
        try:
            parts = table_column.upper().split('.')
            if len(parts) != 2:
                return None

            table_name, column_name = parts

            if table_name not in self.oracle_dict.get('tables', {}):
                return None

            table_info = self.oracle_dict['tables'][table_name]

            for column in table_info.get('columns', []):
                if column['column_name'] == column_name:
                    return {
                        'table_name': table_name,
                        'column_name': column_name,
                        'data_type': column['data_type'],
                        'data_length': column.get('data_length'),
                        'data_precision': column.get('data_precision'),
                        'data_scale': column.get('data_scale'),
                        'sample_value': column.get('sample_value'),
                        'nullable': column.get('nullable')
                    }
            return None
        except Exception:
            return None

    def extract_sql_from_xml(self, xml_path: Path) -> Optional[Dict[str, Any]]:
        """Extract SQL content and common elements from mapper XML"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            namespace = root.get('namespace', '')

            # Extract common elements (resultMap only - sql fragments are handled separately)
            common_elements = []
            for child in root:
                if child.tag in ['resultMap']:
                    common_elements.append(child)

            # Get SQL element (should be only one in split file)
            # Include <sql> fragments as well for conversion
            sql_element = None
            for child in root:
                if child.tag in ['select', 'insert', 'update', 'delete', 'sql']:
                    sql_element = ET.tostring(child, encoding='unicode', method='xml')
                    break

            return {
                'namespace': namespace,
                'common_elements': common_elements,
                'sql_element': sql_element
            }
        except Exception as e:
            print(f"  ✗ XML parse error: {e}")
            return None

    def find_included_fragments(self, sql_xml: str, xml_path: Path) -> Dict[str, str]:
        """Find and load fragment files referenced by <include refid="..."/>"""

        # Extract base mapper name (e.g., oms-common-sql-oracle from oms-common-sql-oracle_selectXXX.xml)
        base_name = xml_path.stem.rsplit('_', 1)[0] if '_' in xml_path.stem else xml_path.stem

        # Parse SQL XML to find <include> tags
        refids = []
        try:
            # Wrap in temporary root if needed
            if not sql_xml.strip().startswith('<?xml'):
                wrapped_xml = f'<root>{sql_xml}</root>'
            else:
                wrapped_xml = sql_xml

            temp_root = ET.fromstring(wrapped_xml)

            # Find all <include> elements recursively
            for elem in temp_root.iter('include'):
                refid = elem.get('refid')
                if refid:
                    refids.append(refid)
        except ET.ParseError:
            # If XML parsing fails, SQL might be malformed but continue anyway
            pass

        fragments = {}
        for refid in refids:
            # Look for fragment file: base_name_fragment_refid.xml
            fragment_file = self.source_dir / f"{base_name}_fragment_{refid}.xml"

            if fragment_file.exists():
                try:
                    tree = ET.parse(fragment_file)
                    root = tree.getroot()

                    # Find the sql element with matching id
                    for child in root:
                        if child.tag == 'sql' and child.get('id') == refid:
                            fragment_content = ET.tostring(child, encoding='unicode', method='xml')
                            fragments[refid] = fragment_content
                            break
                except Exception as e:
                    print(f"    ⚠ Error loading fragment {refid}: {e}")

        return fragments

    def call_bedrock(self, prompt: str, system_prompt: str, call_type: str = 'other') -> Optional[str]:
        """Call Bedrock LLM with continuation support for long responses

        Args:
            call_type: 'table_extraction', 'sql_conversion', 'json_fix', or 'other'
        """
        # Record LLM call
        if call_type in self.stats['llm_calls']:
            with self.stats_lock:
                self.stats['llm_calls'][call_type] += 1

        try:
            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            full_response = ""
            max_continuations = 3  # Prevent infinite loops
            continuation_count = 0

            while continuation_count < max_continuations:
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 8192,
                    "system": system_prompt,
                    "messages": messages
                }

                # Note: temperature is deprecated for Opus 4.7+ models
                # Do not add temperature parameter

                response = self.bedrock.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(body)
                )

                response_body = json.loads(response['body'].read())
                content = response_body['content'][0]['text']
                stop_reason = response_body.get('stop_reason', 'end_turn')

                full_response += content

                # If response completed naturally, we're done
                if stop_reason != 'max_tokens':
                    break

                # Response was truncated, continue generation
                continuation_count += 1
                print(f"    ℹ Response truncated, continuing... ({continuation_count}/{max_continuations})")

                # Add assistant's partial response and ask to continue
                messages.append({
                    "role": "assistant",
                    "content": content
                })
                messages.append({
                    "role": "user",
                    "content": "Please continue from where you left off."
                })

            if continuation_count >= max_continuations:
                print(f"    ⚠ Warning: Response may be incomplete after {max_continuations} continuations")

            return full_response

        except Exception as e:
            print(f"  ✗ Bedrock error: {e}")
            return None

    def convert_sql(self, xml_path: Path) -> Optional[Dict[str, Any]]:
        """Convert SQL using LLM"""
        print(f"  Converting: {xml_path.name}")

        # Extract SQL and common elements from XML
        extracted = self.extract_sql_from_xml(xml_path)
        if not extracted or not extracted['sql_element']:
            return None

        sql_xml = extracted['sql_element']
        namespace = extracted['namespace']
        common_elements = extracted['common_elements']

        # Find and load included fragments
        included_fragments = self.find_included_fragments(sql_xml, xml_path)
        if included_fragments:
            print(f"    ℹ Found {len(included_fragments)} included fragments: {', '.join(included_fragments.keys())}")

        # Step 1: Ask LLM to extract table names from SQL
        print(f"    → Step 1: LLM extracts table names from SQL")
        table_extraction_prompt = f"""Analyze this SQL and extract all table names used.

SQL:
{sql_xml}

Output ONLY a JSON array of table names (uppercase):
["TABLE1", "TABLE2", ...]

Include tables from:
- FROM clause
- JOIN clauses (INNER, LEFT, RIGHT, CROSS, etc.)
- Subqueries
- INSERT INTO, UPDATE statements
- Comma-separated table lists (e.g., FROM A, B, C)

Example:
SQL: SELECT * FROM TB_USER A, TB_ORDER B WHERE A.ID = B.USER_ID
Output: ["TB_USER", "TB_ORDER"]

Output JSON only, no markdown."""

        table_list_response = self.call_bedrock(table_extraction_prompt,
                                                "You are a SQL parser. Extract table names accurately.",
                                                call_type='table_extraction')

        # Parse table list
        tables = []
        if table_list_response:
            try:
                # Clean markdown if present
                response = table_list_response.strip()
                if response.startswith('```json'):
                    response = response[7:]
                if response.startswith('```'):
                    response = response[3:]
                if response.endswith('```'):
                    response = response[:-3]
                response = response.strip()

                tables = json.loads(response)
                print(f"    → LLM found {len(tables)} tables: {', '.join(tables)}")
            except json.JSONDecodeError as e:
                print(f"    ⚠ Failed to parse table list from LLM: {e}")
                print(f"    ⚠ LLM response: {table_list_response[:200]}")
                # Fallback: empty list (LLM will still convert SQL without schema info)
                tables = []

        # Step 2: Build column type information from dictionary
        column_types_info = ""
        if self.oracle_dict and 'tables' in self.oracle_dict and tables:
            column_types_info = "\n\n=== Oracle Schema Information ===\n"

            for table_name in tables:
                table_upper = table_name.upper()
                if table_upper in self.oracle_dict['tables']:
                    table_info = self.oracle_dict['tables'][table_upper]
                    column_types_info += f"\nTable: {table_upper}\n"
                    for col in table_info.get('columns', [])[:50]:  # Limit to 50 columns
                        column_types_info += f"  {col['column_name']}: {col['data_type']}"

                        # Add length/precision info
                        if col['data_type'] in ['VARCHAR2', 'VARCHAR', 'CHAR']:
                            column_types_info += f"({col.get('data_length', '?')})"
                        elif col['data_type'] == 'NUMBER':
                            prec = col.get('data_precision')
                            scale = col.get('data_scale')
                            if prec is not None and scale is not None:
                                column_types_info += f"({prec},{scale})"
                            elif prec is not None:
                                column_types_info += f"({prec})"

                        # Add nullable info
                        if not col.get('nullable', True):
                            column_types_info += " NOT NULL"

                        # Add sample if available
                        if col.get('sample_value'):
                            column_types_info += f" (sample: {col['sample_value']})"

                        column_types_info += "\n"

        print(f"    → Step 2: Schema information built for {len(tables)} tables")

        # Prepare LLM prompt
        system_prompt = f"""You are an expert database migration specialist.
Convert Oracle SQL/MyBatis mapper to {self.target_db}.

IMPORTANT: Whether this is a <select>/<insert>/<update>/<delete> OR a <sql> fragment:
- ALWAYS convert all SQL syntax from Oracle to {self.target_db}
- ALWAYS apply type casting rules to arithmetic operations
- Fragment files (<sql> tags) are converted separately - full SQL conversion still required

Key requirements:
1. Convert Oracle syntax to {self.target_db} syntax
2. Add EXPLICIT TYPE CASTING for ALL operations using Schema Information below:

   A. ARITHMETIC OPERATIONS (+ - * /):
      - Check column type in Schema Information
      - If column is NUMBER → column::INTEGER or column::NUMERIC
      - If column is VARCHAR/CHAR but used in arithmetic → column::INTEGER
      - Apply to BOTH columns and parameters
      - Examples:
        * A.CTGLV + 1 = B.CTGLV (Schema: CTGLV is VARCHAR2(2))
          → A.CTGLV::INTEGER + 1 = B.CTGLV::INTEGER
        * A.QTY + #{{qty}} (Schema: QTY is NUMBER(10))
          → A.QTY::INTEGER + #{{qty}}::INTEGER

   B. COMPARISON OPERATIONS (>= > < <= = !=):
      - Check BOTH column type and parameter type
      - If column is VARCHAR but compared with DATE → column::DATE
      - If column is VARCHAR but compared with NUMBER → column::INTEGER
      - Apply casting to BOTH sides
      - Examples:
        * A.CLOSDATE >= #{{sysdate}} (Schema: CLOSDATE is VARCHAR2(8), param is DATE)
          → A.CLOSDATE::DATE >= #{{sysdate}}::DATE
        * B.STATUS = #{{status}} (Schema: STATUS is VARCHAR2(1), param is VARCHAR)
          → No casting needed

   C. PARAMETERS (#{{...}}) TYPE CASTING:
      - Determine parameter type from context and Schema
      - NUMBER columns → #{{param}}::INTEGER or ::NUMERIC
      - DATE columns → #{{param}}::DATE or ::TIMESTAMP
      - VARCHAR columns → NO casting needed

3. Identify ALL bind variables (#{...} or ${{...}})
4. Map each bind variable to its source table.column
5. Identify all conditional branches (if/choose/when/foreach)
6. Generate test cases for each branch with REALISTIC values respecting column constraints:
   - VARCHAR2(20): max 20 characters
   - NUMBER(10,2): max 10 digits total, 2 decimal places
   - NOT NULL: never use null values
   - Use column length/precision from schema info below

TYPE CASTING DECISION TABLE (Use Schema Information):
Column Type | Operation Type | Cast To
VARCHAR2    | Arithmetic     | ::INTEGER
VARCHAR2    | Date Compare   | ::DATE
VARCHAR2    | String Compare | No cast
NUMBER      | Arithmetic     | ::INTEGER or ::NUMERIC
NUMBER      | Compare        | ::INTEGER or ::NUMERIC
DATE        | Any            | ::DATE or ::TIMESTAMP

Output MUST be valid JSON with this structure:
{{
  "converted_xml": "full converted XML content with explicit type casts",
  "bind_variables": {{
    "#{{variable}}": "TABLE.COLUMN"
  }},
  "test_cases": [
    {{"description": "...", "parameters": {{...}}}}
  ]
}}"""

        # Add fragment information if any
        fragment_info = ""
        if included_fragments:
            fragment_info = "\n\n=== Included SQL Fragments ===\n"
            fragment_info += "NOTE: This main SQL includes fragments via <include refid=\"...\"/> tags.\n"
            fragment_info += "IMPORTANT:\n"
            fragment_info += "- KEEP <include> tags as-is in the converted XML (do NOT inline fragment content)\n"
            fragment_info += "- Use fragment content below ONLY for extracting bind variables and generating test cases\n"
            fragment_info += "- Fragment files themselves are converted separately\n\n"
            for refid, fragment_content in included_fragments.items():
                fragment_info += f"Fragment ID: {refid}\n{fragment_content}\n\n"

        prompt = f"""Convert this Oracle MyBatis mapper to {self.target_db}:

{sql_xml}
{column_types_info}
{fragment_info}

Requirements:
- Convert Oracle functions (NVL→COALESCE, DECODE, etc)
- Remove DUAL table references
- Convert SEQUENCE access
- ADD EXPLICIT TYPE CASTING for NUMERIC and DATE types only (NOT for VARCHAR)
- Map ALL bind variables to table.column
- Generate test cases with values that RESPECT column constraints (length, precision, nullable)

TEST CASE VALUE RULES:
- Check column length: VARCHAR2(20) → use max 20 chars (e.g., "STORE001" not "VERYLONGSTORENAME123")
- Check NUMBER precision: NUMBER(10,2) → max 10 digits, 2 decimals (e.g., 12345678.99)
- Check NOT NULL: never generate null for NOT NULL columns
- Generate realistic business values based on column name and type

TYPE CASTING RULES based on schema above:
- NUMBER columns → ::INTEGER (for IDs, counts) or ::NUMERIC (for rates, amounts)
- DATE/TIMESTAMP columns → ::TIMESTAMP
- VARCHAR/CHAR columns → NO CASTING (do not add ::VARCHAR)

Example:
  #{{userId}}::INTEGER     (if userId is NUMBER and used as ID)
  #{{amount}}::NUMERIC     (if amount is NUMBER with decimals)
  #{{createDate}}::TIMESTAMP (if createDate is DATE)
  #{{userName}}            (if userName is VARCHAR - NO CASTING)

Output JSON only, no markdown."""

        # Step 3: Call LLM for SQL conversion
        print(f"    → Step 3: LLM converts SQL to {self.target_db}")
        response = self.call_bedrock(prompt, system_prompt, call_type='sql_conversion')
        if not response:
            return None

        # Parse response
        try:
            # Clean markdown if present
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()

            # Try to parse JSON
            try:
                result = json.loads(response)
            except json.JSONDecodeError as e:
                # If parsing fails, ask LLM to fix the JSON
                print(f"  ⚠ JSON parsing failed: {e}")
                print(f"  → Asking LLM to regenerate valid JSON...")

                fix_prompt = f"""The previous JSON response was malformed. Please regenerate it with proper escaping.

Original (broken) JSON:
{response[:1000]}...

Requirements:
- Escape all special characters in XML content (newlines, quotes, etc.)
- Ensure valid JSON structure
- Do NOT use markdown code blocks

Output ONLY the corrected JSON, nothing else."""

                fixed_response = self.call_bedrock(fix_prompt,
                                                   "You are a JSON formatter. Fix malformed JSON.",
                                                   call_type='json_fix')

                if not fixed_response:
                    print(f"  ✗ Failed to fix JSON")
                    return None

                # Clean and try parsing fixed response
                fixed_response = fixed_response.strip()
                if fixed_response.startswith('```json'):
                    fixed_response = fixed_response[7:]
                if fixed_response.startswith('```'):
                    fixed_response = fixed_response[3:]
                if fixed_response.endswith('```'):
                    fixed_response = fixed_response[:-3]
                fixed_response = fixed_response.strip()

                # Find JSON object boundaries
                json_start = fixed_response.find('{')
                json_end = fixed_response.rfind('}') + 1

                if json_start >= 0 and json_end > json_start:
                    json_str = fixed_response[json_start:json_end]

                    # Try parsing again
                    try:
                        result = json.loads(json_str)
                        print(f"  ✓ JSON fixed by LLM")
                    except json.JSONDecodeError as e2:
                        print(f"  ✗ JSON still invalid after LLM fix: {e2}")
                        print(f"  → Giving up on this file")
                        return None
                else:
                    print(f"  ✗ Could not find JSON boundaries in fixed response")
                    return None

            # Add namespace, common elements, original SQL, and tables to result
            result['namespace'] = namespace
            result['common_elements'] = common_elements
            result['original_sql'] = sql_xml
            result['tables_found'] = tables  # From Phase 2

            # Record tables statistics
            with self.stats_lock:
                for table in tables:
                    self.stats['tables_discovered'].add(table)
                    if table.upper() in self.oracle_dict.get('tables', {}):
                        self.stats['tables_matched'].add(table)
                    else:
                        self.stats['tables_not_found'].add(table)

            return result

        except (json.JSONDecodeError, Exception) as e:
            print(f"  ✗ JSON parse error: {e}")
            print(f"  Response preview: {response[:200]}...")
            return None

    def add_explicit_casting(self, xml_content: str, bind_mappings: Dict[str, str]) -> str:
        """Add explicit type casting for numeric and date types"""
        modified = xml_content

        for bind_var, table_column in bind_mappings.items():
            column_info = self.lookup_column(table_column)
            if not column_info:
                continue

            data_type = column_info['data_type']

            # Add casting for numeric types
            if data_type in ['NUMBER', 'INTEGER', 'NUMERIC', 'DECIMAL', 'FLOAT']:
                if self.target_db == 'postgres':
                    # #{userId}::INTEGER
                    cast_syntax = f"{bind_var}::INTEGER"
                    modified = modified.replace(bind_var, cast_syntax)

            # Add casting for date types
            elif data_type in ['DATE', 'TIMESTAMP']:
                if self.target_db == 'postgres':
                    # #{createDate}::TIMESTAMP
                    cast_syntax = f"{bind_var}::TIMESTAMP"
                    modified = modified.replace(bind_var, cast_syntax)

        return modified

    def extract_schema_info_from_xml(self, xml_content: str) -> str:
        """
        Extract schema information for tables mentioned in XML
        Uses LLM-based approach (no regex) - asks LLM to identify tables
        """
        if not self.oracle_dict or 'tables' not in self.oracle_dict:
            return ""

        # LLM already extracted table.column mappings in 1st pass (bind_variables)
        # For 2nd pass, provide schema for ALL tables in Dictionary (simple approach)
        # This avoids regex and provides complete context

        schema_info = "\n=== Oracle Schema Information ===\n"
        schema_info += "Note: Column types in Oracle (for type casting reference)\n\n"

        # Get tables that are likely relevant (from XML content)
        # Simple string matching without regex
        relevant_tables = []
        for table_name in self.oracle_dict['tables'].keys():
            if table_name in xml_content.upper():
                relevant_tables.append(table_name)

        if not relevant_tables:
            return ""

        for table_name in relevant_tables[:5]:  # Limit to 5 tables
            table_info = self.oracle_dict['tables'][table_name]
            schema_info += f"Table: {table_name}\n"
            for col in table_info.get('columns', [])[:20]:  # Limit to 20 columns
                col_info = f"  {col['column_name']}: {col['data_type']}"
                if col['data_type'] in ['VARCHAR2', 'VARCHAR', 'CHAR']:
                    col_info += f"({col.get('data_length', '?')})"
                elif col['data_type'] == 'NUMBER':
                    prec = col.get('data_precision')
                    scale = col.get('data_scale')
                    if prec is not None and scale is not None:
                        col_info += f"({prec},{scale})"
                schema_info += col_info + "\n"
            schema_info += "\n"

        return schema_info

    def apply_type_casting_pass(self, full_xml: str, xml_path: Path) -> str:
        """
        2nd LLM pass: PostgreSQL type casting specialist
        Simple focused prompt for type casting only
        """
        system_prompt = """You are a PostgreSQL type casting specialist.

Add explicit type casts for:
1. ALL arithmetic operations (+ - * /)
2. ALL comparisons with DATE columns (=, !=, <, >, <=, >=)

Use Schema Information to check column types:
- If column is VARCHAR but used in arithmetic → column::INTEGER
- If column is VARCHAR but compared with DATE → column::DATE
- Apply casting to BOTH sides of operations

Examples:
- A.CTGLV + 1 = B.CTGLV (CTGLV is VARCHAR2)
  → A.CTGLV::INTEGER + 1 = B.CTGLV::INTEGER

- A.CLOSDATE >= #{sysdate} (CLOSDATE is VARCHAR2, sysdate is DATE)
  → A.CLOSDATE::DATE >= #{sysdate}::DATE

Return ONLY the complete XML with casts added."""

        # Extract Schema Information from XML (no regex - simple string matching)
        schema_info = self.extract_schema_info_from_xml(full_xml)

        prompt = f"""Add PostgreSQL type casts to this XML:

{full_xml}

{schema_info}

Add explicit type casts for:
- Arithmetic operations: column + 1, column - value
- Date comparisons: CLOSDATE >= param, INSERTDATE > param

Return ONLY the complete XML (starting with <?xml). No explanations."""

        try:
            response = self.call_bedrock(prompt, system_prompt)
            if not response:
                print(f"    ⚠ Type casting: No LLM response")
                return full_xml

            # Extract XML from response
            response = response.strip()
            if response.startswith('<?xml'):
                # Return only the body (without declaration and doctype, as they'll be added by caller)
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(response)
                    return ET.tostring(root, encoding='unicode', method='xml')
                except Exception as parse_error:
                    print(f"    ⚠ Type casting: XML parse failed - {parse_error}")
                    return full_xml
            else:
                print(f"    ⚠ Type casting: Response doesn't start with <?xml (starts with: {response[:50]}...)")
                return full_xml

        except Exception as e:
            print(f"    ⚠ Type casting pass failed: {e}")
            return full_xml

    def generate_default_value(self, var_name: str, table_column: str, data_types: Dict) -> Any:
        """Generate default value based on data type from TC data_types"""
        # Check if we have type information for this column
        type_info = data_types.get(table_column)
        if not type_info:
            # No type info available (e.g., Extension variables)
            # Return empty string as safe default
            return ""

        data_type = type_info.get('type', '')

        # Use sample value if available (best option)
        if 'sample' in type_info:
            return type_info['sample']

        # Generate default based on data type and constraints
        if data_type in ['VARCHAR2', 'VARCHAR', 'CHAR']:
            length = type_info.get('length', 10)
            # Generate string that fits the length
            if length >= 10:
                return 'TEST_VALUE'
            elif length >= 4:
                return 'TEST'
            elif length >= 1:
                return 'T' * min(length, 1)
            else:
                return ''
        elif data_type == 'NUMBER':
            precision = type_info.get('precision')
            scale = type_info.get('scale', 0)
            if scale and scale > 0:
                return 1.0  # Decimal number
            else:
                return 1  # Integer
        elif data_type == 'DATE':
            return '20250101000000'
        elif data_type == 'TIMESTAMP':
            return '20250101000000'
        else:
            # Unknown type, return empty string
            return ""

    def generate_tc_file(self, xml_path: Path, bind_mappings: Dict[str, str],
                        test_cases: List[Dict]) -> Dict[str, Any]:
        """Generate test case file"""
        tc_data = {
            "file": xml_path.name,
            "bind_variables": bind_mappings,
            "data_types": {},
            "test_cases": test_cases
        }

        # Get data types, sample values, and constraints
        for bind_var, table_column in bind_mappings.items():
            column_info = self.lookup_column(table_column)
            if column_info:
                type_info = {
                    "type": column_info['data_type'],
                    "nullable": column_info.get('nullable', True)
                }

                # Add length for character types
                if column_info['data_type'] in ['VARCHAR2', 'VARCHAR', 'CHAR']:
                    type_info['length'] = column_info.get('data_length')

                # Add precision/scale for numeric types
                elif column_info['data_type'] == 'NUMBER':
                    prec = column_info.get('data_precision')
                    scale = column_info.get('data_scale')
                    if prec is not None:
                        type_info['precision'] = prec
                    if scale is not None:
                        type_info['scale'] = scale

                # Add sample if available
                if column_info.get('sample_value'):
                    type_info['sample'] = column_info['sample_value']

                tc_data["data_types"][table_column] = type_info

        return tc_data

    def convert_file(self, xml_path: Path) -> bool:
        """Convert single mapper file"""
        file_start_time = time.time()
        file_stats = {
            'file': xml_path.name,
            'status': 'unknown',
            'tables_found': [],
            'bind_variables': 0,
            'test_cases': 0,
            'conversion_time': 0,
            'error': None
        }

        try:
            # Check if this is a resultMap or fragment file
            is_resultmap = '_resultMap_' in xml_path.name
            is_fragment = '_fragment_' in xml_path.name

            # Skip resultMap files - no SQL to convert
            if is_resultmap:
                print(f"    ⊘ {xml_path.name} - Skipped (resultMap only)")
                file_stats['status'] = 'skipped'
                file_stats['conversion_time'] = time.time() - file_start_time
                with self.stats_lock:
                    self.stats['skipped_files'] += 1
                    self.stats['file_details'].append(file_stats)
                return True

            # Convert SQL
            result = self.convert_sql(xml_path)
            if not result:
                print(f"    ✗ {xml_path.name} - convert_sql() returned None")
                file_stats['status'] = 'failed'
                file_stats['error'] = 'convert_sql returned None'
                file_stats['conversion_time'] = time.time() - file_start_time
                with self.stats_lock:
                    self.stats['failed_files'] += 1
                    self.stats['file_details'].append(file_stats)
                return False

            # Add explicit casting
            converted_sql = result.get('converted_xml', '')
            bind_mappings = result.get('bind_variables', {})
            namespace = result.get('namespace', '')
            common_elements = result.get('common_elements', [])
            original_sql = result.get('original_sql', '')

            # Note: Extension variable substitution is handled by Java Validator at runtime
            # TC files contain placeholder values that will be replaced during validation

            # Build complete XML with common elements
            xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
            doctype = '<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">\n'

            # Create mapper element
            root = ET.Element('mapper')
            if namespace:
                root.set('namespace', namespace)

            # Add common elements first
            for common_elem in common_elements:
                root.append(common_elem)

            # Parse and add converted SQL
            try:
                sql_elem = ET.fromstring(converted_sql)
                root.append(sql_elem)
            except ET.ParseError:
                # If parsing fails, wrap in a temporary root
                wrapped = f"<root>{converted_sql}</root>"
                temp_root = ET.fromstring(wrapped)
                for child in temp_root:
                    root.append(child)

            # Convert to string
            xml_str = ET.tostring(root, encoding='unicode', method='xml')

            # 2nd pass disabled - type casting will be done by error-driven fix tool
            # if self.target_db == 'postgres':
            #     full_xml = xml_declaration + doctype + xml_str
            #     print(f"    → Applying type casting (2nd pass)...")
            #     xml_str = self.apply_type_casting_pass(full_xml, xml_path)

            # Save converted XML
            output_xml = self.target_dir / xml_path.name
            with open(output_xml, 'w', encoding='utf-8') as f:
                f.write(xml_declaration)
                f.write(doctype)
                f.write(xml_str)

            # Generate and save TC file (skip for fragments)
            if not is_fragment:
                test_cases = result.get('test_cases', [])

                # Generate TC data with data_types first
                tc_data = self.generate_tc_file(xml_path, bind_mappings, test_cases)

                # Fill missing or empty parameters in test cases
                if test_cases:
                    for test_case in test_cases:
                        if 'parameters' not in test_case:
                            continue

                        params = test_case['parameters']

                        # Check each bind variable
                        for var_name, table_column in bind_mappings.items():
                            # Get type info for this column
                            type_info = tc_data.get('data_types', {}).get(table_column)

                            # If parameter exists and has a value
                            if var_name in params and params[var_name] not in [None, ""]:
                                # Correct the type based on data_types
                                if type_info:
                                    data_type = type_info.get('type', '')
                                    current_value = params[var_name]

                                    # Convert to string if VARCHAR/CHAR but value is numeric
                                    if data_type in ['VARCHAR2', 'VARCHAR', 'CHAR']:
                                        if isinstance(current_value, (int, float)):
                                            params[var_name] = str(current_value)
                                    # Convert to int if NUMBER without scale but value is string
                                    elif data_type == 'NUMBER':
                                        scale = type_info.get('scale', 0)
                                        if scale == 0 and isinstance(current_value, str):
                                            try:
                                                params[var_name] = int(current_value)
                                            except ValueError:
                                                pass  # Keep as string if conversion fails
                                continue

                            # Parameter is missing, None, or empty string
                            # Generate default value based on data type
                            default_value = self.generate_default_value(
                                var_name, table_column, tc_data.get('data_types', {})
                            )
                            params[var_name] = default_value

                output_tc = self.target_dir / f"{xml_path.stem}.tc.json"
                with open(output_tc, 'w', encoding='utf-8') as f:
                    json.dump(tc_data, f, indent=2, ensure_ascii=False)

                print(f"    ✓ {xml_path.name} - {len(bind_mappings)} bind vars")

                # Record statistics
                file_stats['status'] = 'success'
                file_stats['bind_variables'] = len(bind_mappings)
                file_stats['test_cases'] = len(test_cases) if test_cases else 0
                file_stats['tables_found'] = result.get('tables_found', [])
                file_stats['conversion_time'] = time.time() - file_start_time

                with self.stats_lock:
                    self.stats['total_bind_variables'] += len(bind_mappings)
                    self.stats['total_test_cases'] += file_stats['test_cases']
                    if 'tables_found' in result:
                        for table in result['tables_found']:
                            self.stats['tables_discovered'].add(table)
                    self.stats['file_details'].append(file_stats)
            else:
                print(f"    ✓ {xml_path.name} - Fragment converted (no TC)")
                file_stats['status'] = 'success_fragment'
                file_stats['conversion_time'] = time.time() - file_start_time
                with self.stats_lock:
                    self.stats['file_details'].append(file_stats)

            return True

        except Exception as e:
            error_msg = f"{xml_path.name}: {e}"
            print(f"    ✗ {xml_path.name} - Error: {e}")
            file_stats['status'] = 'failed'
            file_stats['error'] = str(e)
            file_stats['conversion_time'] = time.time() - file_start_time
            with self.stats_lock:
                self.stats['errors'].append(error_msg)
                self.stats['failed_files'] += 1
                self.stats['file_details'].append(file_stats)
            return False

    def convert_all(self):
        """Convert all mapper files with parallel processing"""
        self.start_time = datetime.now()

        print(f"Source: {self.source_dir}")
        print(f"Target: {self.target_dir}")
        print(f"Dictionary: {self.dict_path}")
        print(f"Target DB: {self.target_db}")
        print(f"Model: {self.model_id}")
        print(f"Parallel workers: {self.max_workers}\n")

        if not self.source_dir.exists():
            print(f"✗ Source directory not found: {self.source_dir}")
            return

        # Create target directory
        self.target_dir.mkdir(parents=True, exist_ok=True)

        # Copy all source files to target directory first
        import shutil
        source_files = list(self.source_dir.glob('*.xml'))
        for src_file in source_files:
            shutil.copy2(src_file, self.target_dir / src_file.name)
        print(f"Copied {len(source_files)} files from source to target\n")

        # Find all XML files in target directory for conversion
        xml_files = list(self.target_dir.glob('*.xml'))
        self.stats['total_files'] = len(xml_files)

        if not xml_files:
            print("No XML files found")
            return

        print(f"Found {len(xml_files)} mapper files")
        print(f"Starting parallel conversion...\n")

        # Process files in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.convert_file, xml_file): xml_file
                for xml_file in xml_files
            }

            # Process completed tasks
            for future in as_completed(future_to_file):
                xml_file = future_to_file[future]
                try:
                    if future.result():
                        with self.stats_lock:
                            self.stats['converted_files'] += 1
                except Exception as e:
                    error_msg = f"{xml_file.name}: {e}"
                    print(f"    ✗ {xml_file.name} - Exception: {e}")
                    with self.stats_lock:
                        self.stats['errors'].append(error_msg)

        print()
        self.end_time = datetime.now()
        self.print_summary()
        self.save_conversion_report()

    def print_summary(self):
        """Print conversion summary"""
        print("=" * 50)
        print("Summary:")
        print(f"  Total files: {self.stats['total_files']}")
        print(f"  Converted files: {self.stats['converted_files']}")
        print(f"  Failed files: {self.stats['failed_files']}")
        print(f"  Skipped files: {self.stats['skipped_files']}")

        if self.stats['converted_files'] > 0:
            success_rate = (self.stats['converted_files'] / self.stats['total_files']) * 100
            print(f"  Success rate: {success_rate:.2f}%")

        if self.stats['errors']:
            print(f"\n  Errors: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:
                print(f"    - {error}")
            if len(self.stats['errors']) > 5:
                print(f"    ... and {len(self.stats['errors']) - 5} more")

    def save_conversion_report(self):
        """Save detailed conversion report to JSON file"""
        if not self.start_time or not self.end_time:
            return

        duration = (self.end_time - self.start_time).total_seconds()

        # Calculate statistics
        conversion_times = [d['conversion_time'] for d in self.stats['file_details']
                           if d['status'] in ['success', 'success_fragment']]

        avg_time = sum(conversion_times) / len(conversion_times) if conversion_times else 0
        fastest = min(conversion_times) if conversion_times else 0
        slowest = max(conversion_times) if conversion_times else 0

        fastest_file = min([d for d in self.stats['file_details']
                           if d['status'] in ['success', 'success_fragment']],
                          key=lambda x: x['conversion_time'],
                          default={'file': 'N/A', 'conversion_time': 0})

        slowest_file = max([d for d in self.stats['file_details']
                           if d['status'] in ['success', 'success_fragment']],
                          key=lambda x: x['conversion_time'],
                          default={'file': 'N/A', 'conversion_time': 0})

        tables_discovered = len(self.stats['tables_discovered'])
        tables_matched = len(self.stats['tables_matched'])
        tables_not_found = len(self.stats['tables_not_found'])
        match_rate = (tables_matched / tables_discovered * 100) if tables_discovered > 0 else 0

        # Build report
        report = {
            "conversion_summary": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration_seconds": round(duration, 2),
                "total_files": self.stats['total_files'],
                "converted_files": self.stats['converted_files'],
                "failed_files": self.stats['failed_files'],
                "skipped_files": self.stats['skipped_files'],
                "success_rate": f"{(self.stats['converted_files'] / self.stats['total_files'] * 100):.2f}%"
                               if self.stats['total_files'] > 0 else "0%"
            },
            "oracle_dictionary": {
                "dictionary_path": str(self.dict_path),
                "total_tables_in_dict": len(self.oracle_dict.get('tables', {})),
                "schema": self.oracle_dict.get('schema', 'UNKNOWN')
            },
            "conversion_details": {
                "tables_discovered": tables_discovered,
                "tables_matched_in_dictionary": tables_matched,
                "tables_not_found": tables_not_found,
                "dictionary_match_rate": f"{match_rate:.2f}%",
                "tables_not_found_list": sorted(list(self.stats['tables_not_found'])),
                "total_bind_variables": self.stats['total_bind_variables'],
                "total_test_cases": self.stats['total_test_cases'],
                "avg_test_cases_per_sql": round(self.stats['total_test_cases'] / self.stats['converted_files'], 2)
                                         if self.stats['converted_files'] > 0 else 0
            },
            "conversion_performance": {
                "avg_conversion_time_seconds": round(avg_time, 2),
                "fastest_file": {
                    "name": fastest_file['file'],
                    "time_seconds": round(fastest_file['conversion_time'], 2)
                },
                "slowest_file": {
                    "name": slowest_file['file'],
                    "time_seconds": round(slowest_file['conversion_time'], 2)
                },
                "llm_calls": {
                    "table_extraction": self.stats['llm_calls']['table_extraction'],
                    "sql_conversion": self.stats['llm_calls']['sql_conversion'],
                    "json_fix": self.stats['llm_calls']['json_fix'],
                    "total": sum(self.stats['llm_calls'].values())
                }
            },
            "errors": [
                {"message": err} for err in self.stats['errors']
            ],
            "file_details": sorted(self.stats['file_details'],
                                  key=lambda x: x['conversion_time'],
                                  reverse=True)[:20]  # Top 20 slowest files
        }

        # Save to file
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        report_path = output_dir / 'conversion-report.json'

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n✓ Conversion report saved to: {report_path}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert Oracle SQL to target database using Bedrock LLM'
    )
    parser.add_argument(
        '--source-dir',
        type=str,
        required=True,
        help='Source directory with Oracle mapper files'
    )
    parser.add_argument(
        '--target-dir',
        type=str,
        required=True,
        help='Target directory for converted files'
    )
    parser.add_argument(
        '--dict-path',
        type=str,
        help='Path to Oracle dictionary JSON (default: from environment)'
    )
    parser.add_argument(
        '--parallel',
        type=int,
        help='Number of parallel workers (default: from environment MAX_WORKERS or 7)'
    )

    args = parser.parse_args()

    # Get all settings from environment variables
    dict_path = args.dict_path or os.getenv('ORACLE_DICT_PATH', './output/oracle_dictionary.json')
    target_db = os.getenv('TARGET_DB_TYPE', 'postgres')
    bedrock_region = os.getenv('BEDROCK_REGION', 'ap-northeast-2')
    model_id = os.getenv('BEDROCK_MODEL_ID')

    # Get max_workers from: CLI arg > ENV var > default(7)
    max_workers = args.parallel
    if max_workers is None:
        max_workers = int(os.getenv('MAX_WORKERS', '7'))

    if not model_id:
        print("Error: BEDROCK_MODEL_ID not found in environment variables")
        print("Please ensure .env is loaded (skills automatically do this)")
        sys.exit(1)

    converter = SQLConverter(
        source_dir=args.source_dir,
        target_dir=args.target_dir,
        dict_path=dict_path,
        target_db=target_db,
        bedrock_region=bedrock_region,
        model_id=model_id,
        max_workers=max_workers
    )

    converter.convert_all()


if __name__ == "__main__":
    main()
