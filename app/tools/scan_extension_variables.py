#!/usr/bin/env python3
"""
Extension Variable Scanner
Scans Oracle mapper files for bind variables and manages extension.json configuration
"""

import os
import re
import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List


class ExtensionScanner:
    def __init__(self, mapper_dir: str, extension_config: str):
        self.mapper_dir = Path(mapper_dir)
        self.extension_config = Path(extension_config)
        self.bind_variables = defaultdict(int)  # variable -> count

    def scan_mappers(self) -> Set[str]:
        """Scan all mapper XML files for bind variables"""
        print(f"\n=== Scanning Mapper Files ===")
        print(f"Directory: {self.mapper_dir}")

        xml_files = list(self.mapper_dir.glob("**/*.xml"))
        print(f"Found {len(xml_files)} XML files\n")

        all_variables = set()

        for xml_file in xml_files:
            try:
                content = xml_file.read_text(encoding='utf-8')
                # Extract #{variable} patterns
                variables = re.findall(r'#\{([^}]+)\}', content)

                for var in variables:
                    # Clean up variable name (remove spaces, test conditions)
                    var_clean = var.split(',')[0].strip()
                    all_variables.add(var_clean)
                    self.bind_variables[var_clean] += 1

            except Exception as e:
                print(f"⚠ Error reading {xml_file.name}: {e}")

        return all_variables

    def categorize_variables(self, variables: Set[str]) -> tuple[List[str], List[str]]:
        """Categorize variables into Extension candidates and normal bind variables"""
        extension_candidates = []
        normal_variables = []

        # Heuristics for Extension variables:
        # 1. All uppercase with underscores (GRIDPAGING_ROWNUMTYPE_TOP)
        # 2. Framework-related names (PAGING, FRAMEWORK, etc.)
        # 3. Not matching typical column/table patterns

        for var in variables:
            # Check if it looks like an Extension variable
            is_extension = (
                var.isupper() and '_' in var  # UPPER_CASE_WITH_UNDERSCORES
                or 'GRIDPAGING' in var.upper()
                or 'FRAMEWORK' in var.upper()
                or 'PAGING' in var.upper()
            )

            if is_extension:
                extension_candidates.append(var)
            else:
                normal_variables.append(var)

        return sorted(extension_candidates), sorted(normal_variables)

    def load_existing_config(self) -> Dict:
        """Load existing extension.json if exists"""
        if self.extension_config.exists():
            try:
                with open(self.extension_config, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠ Error loading {self.extension_config}: {e}")
                return self.create_empty_config()
        return self.create_empty_config()

    def create_empty_config(self) -> Dict:
        """Create empty extension configuration"""
        return {
            "enabled": False,
            "variables": {}
        }

    def update_config(self, extension_vars: List[str], existing_config: Dict) -> Dict:
        """Update configuration with new variables"""
        variables = existing_config.get("variables", {})

        # Add new variables with placeholder values
        new_count = 0
        for var in extension_vars:
            if var not in variables:
                variables[var] = {
                    "oracle": "",  # User must fill in
                    "postgres": ""  # User must fill in
                }
                new_count += 1

        # Set enabled flag based on whether there are variables with values
        has_values = any(
            v.get("oracle") or v.get("postgres")
            for v in variables.values()
        )

        config = {
            "enabled": has_values or len(extension_vars) > 0,
            "variables": variables
        }

        return config, new_count

    def save_config(self, config: Dict):
        """Save configuration to extension.json"""
        self.extension_config.parent.mkdir(parents=True, exist_ok=True)

        with open(self.extension_config, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Configuration saved to: {self.extension_config}")

    def print_report(self, extension_vars: List[str], normal_vars: List[str],
                     config: Dict, new_count: int):
        """Print scan report"""
        print("\n" + "="*60)
        print("EXTENSION VARIABLE SCAN REPORT")
        print("="*60)

        print(f"\n📊 Summary:")
        print(f"  Total bind variables found: {len(extension_vars) + len(normal_vars)}")
        print(f"  Extension candidates: {len(extension_vars)}")
        print(f"  Normal bind variables: {len(normal_vars)}")
        print(f"  New variables added: {new_count}")

        if extension_vars:
            print(f"\n🔧 Extension Variables (Framework-specific):")
            for var in extension_vars:
                count = self.bind_variables[var]
                status = "✓ Configured" if config["variables"][var].get("oracle") else "⚠ Needs configuration"
                print(f"  - {var:<40} (used {count}x) - {status}")

        if normal_vars and len(normal_vars) <= 20:
            print(f"\n📝 Normal Bind Variables (top 20):")
            sorted_normal = sorted(normal_vars, key=lambda x: self.bind_variables[x], reverse=True)[:20]
            for var in sorted_normal:
                count = self.bind_variables[var]
                print(f"  - {var:<40} (used {count}x)")

        print(f"\n⚙️  Extension Status:")
        enabled = config.get("enabled", False)
        status_icon = "✓" if enabled else "✗"
        print(f"  {status_icon} Extension is {'ENABLED' if enabled else 'DISABLED'}")

        if extension_vars:
            unconfigured = [v for v in extension_vars
                           if not config["variables"][v].get("oracle")
                           and not config["variables"][v].get("postgres")]

            if unconfigured:
                print(f"\n⚠️  Action Required:")
                print(f"  {len(unconfigured)} Extension variable(s) need configuration:")
                for var in unconfigured:
                    print(f"    - {var}")
                print(f"\n  Edit {self.extension_config} and provide Oracle/PostgreSQL values")
            else:
                print(f"\n✓ All Extension variables are configured")
        else:
            print(f"\n✓ No Extension variables found - Extension not needed for this system")

        print("\n" + "="*60 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scan_extension_variables.py <mapper-directory> [extension-config-path]")
        print("\nExample:")
        print("  python scan_extension_variables.py mappers/daiso-oms/source")
        print("  python scan_extension_variables.py mappers/daiso-oms/source extensions/extension.json")
        sys.exit(1)

    mapper_dir = sys.argv[1]
    extension_config = sys.argv[2] if len(sys.argv) > 2 else "extensions/extension.json"

    if not os.path.exists(mapper_dir):
        print(f"✗ Error: Mapper directory not found: {mapper_dir}")
        sys.exit(1)

    scanner = ExtensionScanner(mapper_dir, extension_config)

    # Scan mappers
    all_variables = scanner.scan_mappers()

    if not all_variables:
        print("✗ No bind variables found in mapper files")
        sys.exit(0)

    # Categorize variables
    extension_vars, normal_vars = scanner.categorize_variables(all_variables)

    # Load existing config
    existing_config = scanner.load_existing_config()

    # Update config
    updated_config, new_count = scanner.update_config(extension_vars, existing_config)

    # Save config
    scanner.save_config(updated_config)

    # Print report
    scanner.print_report(extension_vars, normal_vars, updated_config, new_count)


if __name__ == "__main__":
    main()
