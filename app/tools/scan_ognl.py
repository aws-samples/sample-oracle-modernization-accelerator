#!/usr/bin/env python3
"""
OGNL Scanner
Scans all mapper files to identify OGNL expressions and generates MyBatis handlers
"""

import os
import sys
import re
import json
import boto3
from pathlib import Path
from typing import Dict, List, Set, Any
from collections import defaultdict


class OGNLScanner:
    """OGNL expression scanner and handler generator"""

    # OGNL pattern: @package.Class@method(...)
    OGNL_PATTERN = r'@([a-zA-Z0-9_.]+)@([a-zA-Z0-9_]+)\s*\('

    def __init__(self, source_dir: str, output_dir: str, bedrock_region: str, model_id: str):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.bedrock_region = bedrock_region
        self.model_id = model_id

        # Initialize Bedrock client
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name=bedrock_region
        )

        self.ognl_expressions = defaultdict(set)  # {class: set of methods}
        self.usage_examples = defaultdict(list)   # {class.method: [examples]}

    def find_mapper_files(self) -> List[Path]:
        """Find all mapper XML files"""
        if not self.source_dir.exists():
            print(f"✗ Source directory not found: {self.source_dir}")
            return []

        return list(self.source_dir.rglob('*.xml'))

    def extract_ognl_from_file(self, file_path: Path):
        """Extract OGNL expressions from a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find all OGNL expressions
            matches = re.finditer(self.OGNL_PATTERN, content)

            for match in matches:
                class_name = match.group(1)
                method_name = match.group(2)

                # Store class and method
                self.ognl_expressions[class_name].add(method_name)

                # Extract full expression for context
                start = match.start()
                end = content.find(')', start) + 1
                if end > start:
                    full_expr = content[start:end]
                    self.usage_examples[f"{class_name}.{method_name}"].append({
                        'file': file_path.name,
                        'expression': full_expr
                    })

        except Exception as e:
            print(f"  ✗ Error reading {file_path.name}: {e}")

    def scan_all(self):
        """Scan all mapper files for OGNL expressions"""
        print(f"=== OGNL Scanner ===\n")
        print(f"Source: {self.source_dir}\n")

        mapper_files = self.find_mapper_files()

        if not mapper_files:
            print("No mapper files found")
            return

        print(f"Scanning {len(mapper_files)} mapper files...\n")

        for mapper_file in mapper_files:
            self.extract_ognl_from_file(mapper_file)

        self.print_summary()

    def print_summary(self):
        """Print OGNL scan summary"""
        print("\n" + "=" * 70)
        print("OGNL Expressions Found:")
        print("=" * 70)

        if not self.ognl_expressions:
            print("No OGNL expressions found")
            return

        for class_name in sorted(self.ognl_expressions.keys()):
            methods = sorted(self.ognl_expressions[class_name])
            print(f"\n📦 {class_name}")
            for method in methods:
                usage_count = len(self.usage_examples[f"{class_name}.{method}"])
                print(f"   ├─ {method}() - {usage_count} usages")

                # Show first example
                examples = self.usage_examples[f"{class_name}.{method}"]
                if examples:
                    print(f"      └─ Example: {examples[0]['expression']}")

        print(f"\n" + "=" * 70)
        print(f"Total classes: {len(self.ognl_expressions)}")
        total_methods = sum(len(methods) for methods in self.ognl_expressions.values())
        print(f"Total methods: {total_methods}")

    def save_report(self):
        """Save OGNL scan report to JSON"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        report = {
            'scan_timestamp': str(Path.cwd()),
            'total_classes': len(self.ognl_expressions),
            'classes': {}
        }

        for class_name in sorted(self.ognl_expressions.keys()):
            methods_data = {}
            for method in sorted(self.ognl_expressions[class_name]):
                key = f"{class_name}.{method}"
                methods_data[method] = {
                    'usage_count': len(self.usage_examples[key]),
                    'examples': self.usage_examples[key][:5]  # First 5 examples
                }

            report['classes'][class_name] = methods_data

        report_file = self.output_dir / 'ognl_scan_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Report saved to: {report_file}")
        return report

    def call_bedrock(self, prompt: str, system_prompt: str) -> str:
        """Call Bedrock LLM"""
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "temperature": 0.0,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )

            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']

        except Exception as e:
            print(f"  ✗ Bedrock error: {e}")
            return None

    def generate_handlers(self):
        """Generate MyBatis OGNL handlers using LLM"""
        if not self.ognl_expressions:
            print("No OGNL expressions to generate handlers for")
            return

        print("\n" + "=" * 70)
        print("Generating MyBatis OGNL Handlers")
        print("=" * 70 + "\n")

        system_prompt = """You are a Java/MyBatis expert specializing in OGNL expression replacement.

Generate replacement handlers for OGNL expressions used in MyBatis mappers.

CRITICAL REQUIREMENTS:
1. Use the EXACT SAME package name and class name as the original OGNL class
   - This ensures MyBatis mappers work WITHOUT any XML modification
   - Example: If original is "com.kns.framework.util.StringUtil", create that EXACT class

2. Method signatures MUST match MyBatis OGNL usage:
   - Methods MUST be public static
   - Parameter types should be generic (String, Object, etc.) for flexibility
   - Return types should match expected MyBatis usage (boolean, String, Object)

3. Common OGNL patterns to handle:
   - String checks: isEmpty, isNotEmpty, isBlank, isNotBlank
   - Null checks: isNull, isNotNull, nvl, defaultIfNull
   - String operations: trim, substring, concat, contains
   - Number operations: toInt, toLong, toDouble
   - Collection operations: size, isEmpty, contains
   - Date operations: format, parse, compare

4. Implementation guidelines:
   - Include proper null checks (all parameters may be null)
   - Return safe defaults (false for boolean, "" for String, null for Object)
   - Be defensive - handle edge cases gracefully
   - Keep methods simple and focused

5. Code quality:
   - Add JavaDoc with @param and @return
   - Include @author tag: "Generated by OMA OGNL Scanner"
   - No external dependencies (use only java.* packages)
   - Follow standard Java conventions

Output format: Plain Java code ONLY. No markdown code blocks, no explanations, no comments outside the code."""

        for class_name in sorted(self.ognl_expressions.keys()):
            methods = sorted(self.ognl_expressions[class_name])

            print(f"Generating handler for: {class_name}")

            # Collect examples for each method
            method_examples = {}
            for method in methods:
                key = f"{class_name}.{method}"
                examples = [ex['expression'] for ex in self.usage_examples[key][:3]]
                method_examples[method] = examples

            prompt = f"""Generate a Java utility class to replace this OGNL class used in MyBatis mappers:

**Original class:** {class_name}

**Methods to implement with usage examples:**
{chr(10).join(f'- {method}():{chr(10).join(f"  Example: {ex}" for ex in method_examples[method])}' for method in methods)}

**Requirements:**
1. Package: {class_name.rsplit('.', 1)[0]}
2. Class name: {class_name.split('.')[-1]}
3. All methods must be public static
4. Infer correct parameter types and return types from usage examples
5. Handle null inputs gracefully
6. Return safe defaults (false for boolean checks, "" for String operations, null for objects)

**Common patterns:**
- isEmpty(String s) -> return s == null || s.isEmpty()
- isNotEmpty(String s) -> return s != null && !s.isEmpty()
- nvl(String s, String defaultVal) -> return s != null ? s : defaultVal
- trim(String s) -> return s != null ? s.trim() : null

Analyze the usage examples to determine the correct method signatures and implementations.

Output ONLY the complete Java class code with package declaration. No markdown, no explanations."""

            response = self.call_bedrock(prompt, system_prompt)

            if response:
                # Save handler code with proper directory structure
                # Create package directory structure
                package_parts = class_name.split('.')[:-1]  # Remove class name
                class_simple_name = class_name.split('.')[-1]

                output_subdir = self.output_dir / '/'.join(package_parts)
                output_subdir.mkdir(parents=True, exist_ok=True)

                output_file = output_subdir / f"{class_simple_name}.java"

                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(response)

                print(f"  ✓ Generated: {output_file.relative_to(self.output_dir)}")
            else:
                print(f"  ✗ Failed to generate handler for {class_name}")

        print(f"\n✓ Handlers saved to: {self.output_dir}")

    def build_handler_jar(self):
        """Build generated handlers into a JAR file"""
        if not self.ognl_expressions:
            print("No handlers to build")
            return None

        print("\n" + "=" * 70)
        print("Building OGNL Handler JAR")
        print("=" * 70 + "\n")

        # Create minimal pom.xml for Maven build
        pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.oma</groupId>
    <artifactId>ognl-handlers</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>

    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <build>
        <sourceDirectory>.</sourceDirectory>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.11.0</version>
            </plugin>
        </plugins>
    </build>
</project>"""

        pom_file = self.output_dir / 'pom.xml'
        with open(pom_file, 'w', encoding='utf-8') as f:
            f.write(pom_content)

        print(f"✓ Created: {pom_file}")

        # Build JAR using Maven
        import subprocess
        try:
            result = subprocess.run(
                ['mvn', 'clean', 'package', '-q'],
                cwd=self.output_dir,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                jar_file = self.output_dir / 'target' / 'ognl-handlers-1.0.0.jar'
                if jar_file.exists():
                    print(f"✓ JAR built: {jar_file}")
                    return jar_file
                else:
                    print("✗ JAR file not found after build")
                    return None
            else:
                print(f"✗ Maven build failed:\n{result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print("✗ Maven build timeout")
            return None
        except FileNotFoundError:
            print("✗ Maven not found. Install Maven to build JAR")
            return None

    def generate_implementation_guide(self, output_path: str):
        """Generate comprehensive implementation guide for developers"""
        if not self.ognl_expressions:
            print("No OGNL expressions found - Guide not needed")
            return

        from datetime import datetime

        print("\n" + "=" * 70)
        print("Generating OGNL Implementation Guide")
        print("=" * 70 + "\n")

        # Prepare OGNL summary for LLM
        ognl_summary = []
        for class_name in sorted(self.ognl_expressions.keys()):
            methods = sorted(self.ognl_expressions[class_name])
            ognl_summary.append(f"\n**Class: {class_name}**")

            for method in methods:
                key = f"{class_name}.{method}"
                examples = self.usage_examples[key][:3]
                usage_count = len(self.usage_examples[key])

                ognl_summary.append(f"  - `{method}()` - Used {usage_count} times")
                for ex in examples:
                    ognl_summary.append(f"    - Example: `{ex['expression']}` in {ex['file']}")

        ognl_text = '\n'.join(ognl_summary)

        # Create LLM prompt
        prompt = f"""You are a senior Java/MyBatis expert helping a developer implement OGNL expression handlers.

# Context
A MyBatis application uses OGNL expressions that need to be re-implemented.

# Discovered OGNL Expressions
{ognl_text}

# Generate Implementation Guide
Create a comprehensive Markdown guide with:

## 1. Overview
- What OGNL expressions were found
- Why re-implementation is needed

## 2. Implementation Strategy
For each class:
- Package & class structure (MUST match original)
- Method signatures (infer from examples)
- Implementation approach
- Common patterns (isEmpty, isNotEmpty, nvl, trim)

## 3. Step-by-Step Guide
- Create Java source files
- Implement with null safety
- Add JavaDoc

## 4. Build Configuration
- Maven pom.xml example
- Build commands
- Expected JAR output

## 5. Integration
- Place JAR in: `lib/ognl_handlers/`
- Update .env: `OMA_OGNL_JAR=./lib/ognl_handlers/ognl-handlers-1.0.0.jar`
- Validator integration

## 6. Testing
- Verification steps
- Troubleshooting

## 7. Complete Example
Full working implementation for ONE class

Output: Clear, actionable Markdown guide."""

        print("Calling LLM to generate guide...")
        guide_content = self.call_bedrock(prompt, "")

        if not guide_content:
            print("✗ Failed to generate guide")
            return

        # Add header
        header = f"""# OGNL Implementation Guide

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Source Directory:** {self.source_dir}
**Total OGNL Classes:** {len(self.ognl_expressions)}
**Total Methods:** {sum(len(methods) for methods in self.ognl_expressions.values())}

---

## Discovered OGNL Expressions

"""
        # Add discovered expressions
        for class_name in sorted(self.ognl_expressions.keys()):
            methods = sorted(self.ognl_expressions[class_name])
            header += f"\n### `{class_name}`\n\n"

            for method in methods:
                key = f"{class_name}.{method}"
                usage_count = len(self.usage_examples[key])
                header += f"- **`{method}()`** - Used {usage_count} times\n"

                examples = self.usage_examples[key][:2]
                for ex in examples:
                    header += f"  ```xml\n  {ex['expression']}\n  ```\n"

        header += "\n---\n\n"

        # Save guide
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(header + guide_content, encoding='utf-8')

        print(f"\n✓ Implementation guide saved to: {output_file}")
        print(f"\n📖 Next Steps:")
        print(f"  1. Read the guide: {output_file}")
        print(f"  2. Implement OGNL handlers as described")
        print(f"  3. Build JAR using Maven")
        print(f"  4. Place in lib/ognl_handlers/")
        print(f"  5. Update .env configuration")

    def update_env_config(self, jar_path: Path = None):
        """Update .env file with OGNL configuration"""
        env_path = Path(__file__).parent.parent / '.env'

        if not env_path.exists():
            print(f"✗ .env file not found: {env_path}")
            return

        print("\n" + "=" * 70)
        print("Updating .env Configuration")
        print("=" * 70 + "\n")

        # Read current .env
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Check if OGNL config already exists
        has_type_handlers = any('OMA_TYPE_HANDLERS=' in line for line in lines)
        has_ognl_jar = any('OMA_OGNL_JAR=' in line for line in lines)

        # Collect TypeHandler classes
        type_handlers = []
        for class_name in self.ognl_expressions.keys():
            # Generate corresponding TypeHandler name
            simple_name = class_name.split('.')[-1]
            type_handlers.append(f"com.oma.typehandler.{simple_name}TypeHandler")

        new_lines = []
        updated = False

        for line in lines:
            if 'OMA_TYPE_HANDLERS=' in line and has_type_handlers:
                # Update existing
                new_lines.append(f"OMA_TYPE_HANDLERS={','.join(type_handlers)}\n")
                updated = True
            elif 'OMA_OGNL_JAR=' in line and has_ognl_jar and jar_path:
                # Update existing
                jar_rel = jar_path.relative_to(env_path.parent.parent)
                new_lines.append(f"OMA_OGNL_JAR=./{jar_rel}\n")
                updated = True
            else:
                new_lines.append(line)

        # Add if not exists
        if not has_type_handlers:
            new_lines.append(f"\n# OGNL Configuration (Auto-generated by scan_ognl.py)\n")
            new_lines.append(f"OMA_TYPE_HANDLERS={','.join(type_handlers)}\n")
            updated = True

        if not has_ognl_jar and jar_path:
            jar_rel = jar_path.relative_to(env_path.parent.parent)
            new_lines.append(f"OMA_OGNL_JAR=./{jar_rel}\n")
            updated = True

        if updated:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"✓ Updated: {env_path}")
            print(f"  - OMA_TYPE_HANDLERS: {len(type_handlers)} handlers")
            if jar_path:
                print(f"  - OMA_OGNL_JAR: {jar_path.relative_to(env_path.parent.parent)}")
        else:
            print("✓ .env already configured")


def load_env_config() -> Dict[str, str]:
    """Load configuration from .env file"""
    config = {}
    env_path = Path(__file__).parent.parent / '.env'

    if not env_path.exists():
        print(f"Warning: .env file not found at {env_path}")
        return config

    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()

    return config


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Scan mapper files for OGNL expressions and generate handlers'
    )
    parser.add_argument(
        '--source-dir',
        type=str,
        required=True,
        help='Source directory with mapper files'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./ognl_handlers',
        help='Output directory for handlers (default: ./ognl_handlers)'
    )
    parser.add_argument(
        '--generate',
        action='store_true',
        help='Generate handler code using LLM, build JAR, and update .env'
    )
    parser.add_argument(
        '--skip-build',
        action='store_true',
        help='Skip JAR building (only generate source code)'
    )
    parser.add_argument(
        '--skip-env-update',
        action='store_true',
        help='Skip .env file update'
    )
    parser.add_argument(
        '--guide-only',
        action='store_true',
        help='Generate implementation guide only (no code generation)'
    )
    parser.add_argument(
        '--guide-output',
        type=str,
        default='docs/OGNL_IMPLEMENTATION_GUIDE.md',
        help='Output path for implementation guide (default: docs/OGNL_IMPLEMENTATION_GUIDE.md)'
    )

    args = parser.parse_args()

    config = load_env_config()
    bedrock_region = config.get('BEDROCK_REGION', 'ap-northeast-2')
    model_id = config.get('BEDROCK_MODEL_ID')

    if not model_id:
        print("Error: BEDROCK_MODEL_ID not found in .env")
        sys.exit(1)

    scanner = OGNLScanner(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        bedrock_region=bedrock_region,
        model_id=model_id
    )

    # Scan for OGNL expressions
    scanner.scan_all()

    # Save report
    scanner.save_report()

    # Generate implementation guide if requested
    if args.guide_only:
        scanner.generate_implementation_guide(args.guide_output)
        print("\n" + "=" * 70)
        print("✓ OGNL Implementation Guide Generated")
        print("=" * 70)
        return

    # Generate handlers if requested
    if args.generate:
        scanner.generate_handlers()

        # Build JAR (unless skipped)
        jar_path = None
        if not args.skip_build:
            jar_path = scanner.build_handler_jar()

        # Update .env configuration (unless skipped)
        if not args.skip_env_update:
            scanner.update_env_config(jar_path)

        print("\n" + "=" * 70)
        print("✓ OGNL Handler Generation Complete")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Review generated handlers in:", args.output_dir)
        print("2. Test handlers by running SQL conversion")
        print("3. Generated JAR is ready to use with Validator")


if __name__ == "__main__":
    main()
