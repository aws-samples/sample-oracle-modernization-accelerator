#!/usr/bin/env python3
"""
MyBatis Mapper Merger
Merges split mapper XML files back into original structure
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict


class MapperMerger:
    """MyBatis mapper file merger"""

    def __init__(self, source_dir: str, target_dir: str, original_source_dir: str):
        # Convert to absolute paths
        self.source_dir = Path(source_dir).resolve()
        self.target_dir = Path(target_dir).resolve()
        self.original_source_dir = Path(original_source_dir).resolve()

        # Validate source directories
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {self.source_dir}")
        if not self.original_source_dir.exists():
            raise FileNotFoundError(f"Original source directory not found: {self.original_source_dir}")

        # Create target directory
        self.target_dir.mkdir(parents=True, exist_ok=True)

        self.stats = {
            'total_split_files': 0,
            'merged_files': 0,
            'errors': []
        }

    def find_split_files(self) -> List[Path]:
        """Find all split mapper XML files"""
        # Find files with pattern: Name_sqlId.xml
        split_files = [f for f in self.source_dir.rglob('*.xml') if '_' in f.stem]
        self.stats['total_split_files'] = len(split_files)
        return split_files

    def group_by_original(self, split_files: List[Path]) -> Dict[str, List[Path]]:
        """Group split files by original mapper name"""
        groups = defaultdict(list)

        for file_path in split_files:
            # Extract original name from: OriginalName_sqlId.xml
            stem = file_path.stem
            parts = stem.rsplit('_', 1)
            if len(parts) == 2:
                original_name = parts[0]
                groups[original_name].append(file_path)

        return dict(groups)

    def find_original_path(self, original_name: str) -> Path:
        """Find the original file path structure from source workspace"""
        original_file = f"{original_name}.xml"

        # Search for the original file in source workspace
        for file_path in self.original_source_dir.rglob(original_file):
            # Get relative path from source workspace root
            relative_path = file_path.relative_to(self.original_source_dir)
            return relative_path

        # If not found, default to root level
        return Path(original_file)

    def parse_split_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a split mapper file"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            namespace = root.get('namespace', '')

            # Get all SQL elements (should be only one per split file)
            sql_elements = []
            for child in root:
                if child.tag in ['select', 'insert', 'update', 'delete', 'sql']:
                    sql_elements.append(child)

            return {
                'namespace': namespace,
                'sql_elements': sql_elements,
                'file_path': file_path
            }
        except ET.ParseError as e:
            return {'error': f"XML parse error: {e}"}
        except Exception as e:
            return {'error': f"Error: {e}"}

    def merge_files(self, original_name: str, split_files: List[Path]) -> bool:
        """Merge split files back into one mapper file"""
        print(f"  Merging {original_name}.xml ({len(split_files)} SQL statements)")

        try:
            # Find all resultMap and fragment files (now individual files)
            common_elements = []
            namespace = None

            # Load individual resultMap files
            resultmap_files = list(self.source_dir.glob(f"{original_name}_resultMap_*.xml"))
            if resultmap_files:
                print(f"    ℹ Loading {len(resultmap_files)} resultMap files")
                for rm_file in sorted(resultmap_files):
                    try:
                        tree = ET.parse(rm_file)
                        root = tree.getroot()
                        if namespace is None:
                            namespace = root.get('namespace')
                        for child in root:
                            if child.tag in ['resultMap', 'cache', 'parameterMap']:
                                common_elements.append(child)
                    except Exception as e:
                        print(f"    ⚠ Error loading {rm_file.name}: {e}")

            # Load individual fragment files
            fragment_files = list(self.source_dir.glob(f"{original_name}_fragment_*.xml"))
            if fragment_files:
                print(f"    ℹ Loading {len(fragment_files)} fragment files")
                for frag_file in sorted(fragment_files):
                    try:
                        tree = ET.parse(frag_file)
                        root = tree.getroot()
                        if namespace is None:
                            namespace = root.get('namespace')
                        for child in root:
                            if child.tag == 'sql':
                                common_elements.append(child)
                    except Exception as e:
                        print(f"    ⚠ Error loading {frag_file.name}: {e}")

            # Parse all split files
            all_sql_elements = []

            for split_file in sorted(split_files):
                # Skip resultMap and fragment files
                if '_resultMap_' in split_file.name or '_fragment_' in split_file.name:
                    continue

                parsed = self.parse_split_file(split_file)

                if 'error' in parsed:
                    error_msg = f"{split_file.name}: {parsed['error']}"
                    print(f"    ✗ {error_msg}")
                    self.stats['errors'].append(error_msg)
                    continue

                if namespace is None:
                    namespace = parsed['namespace']

                all_sql_elements.extend(parsed['sql_elements'])

            if not all_sql_elements:
                print(f"    ⚠ No SQL elements found")
                return False

            # Create merged mapper
            root = ET.Element('mapper')
            if namespace:
                root.set('namespace', namespace)

            # Add common elements first (resultMap, sql fragments) with deduplication
            seen_ids = set()
            dedup_count = 0
            for elem in common_elements:
                elem_id = elem.get('id')
                if elem_id:
                    if elem_id not in seen_ids:
                        root.append(elem)
                        seen_ids.add(elem_id)
                    else:
                        dedup_count += 1
                else:
                    root.append(elem)  # No id, just add it

            if dedup_count > 0:
                print(f"    ℹ Removed {dedup_count} duplicate fragments")

            for elem in all_sql_elements:
                root.append(elem)

            # Find original path structure
            relative_path = self.find_original_path(original_name)
            output_path = self.target_dir / relative_path

            # Create directory structure
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write merged file
            xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
            doctype = '<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">\n'

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(xml_declaration)
                f.write(doctype)
                xml_str = ET.tostring(root, encoding='unicode', method='xml')
                xml_str = self.prettify_xml(xml_str)
                f.write(xml_str)

            print(f"    ✓ Merged to: {output_path}")
            return True

        except Exception as e:
            error_msg = f"{original_name}: {e}"
            print(f"    ✗ Error: {e}")
            self.stats['errors'].append(error_msg)
            return False

    def prettify_xml(self, xml_str: str) -> str:
        """Add basic indentation to XML string"""
        lines = []
        indent_level = 0
        indent_str = "  "

        for line in xml_str.split('>'):
            line = line.strip()
            if not line:
                continue

            # Closing tag
            if line.startswith('</'):
                indent_level -= 1
                lines.append(indent_str * indent_level + line + '>')
            # Self-closing or opening tag
            elif line.endswith('/'):
                lines.append(indent_str * indent_level + line + '>')
            # Opening tag
            else:
                lines.append(indent_str * indent_level + line + '>')
                if not line.startswith('<?') and not line.startswith('<!'):
                    indent_level += 1

        return '\n'.join(lines)

    def merge_all(self):
        """Merge all split mapper files"""
        print(f"Source: {self.source_dir}")
        print(f"Target: {self.target_dir}")
        print(f"Original: {self.original_source_dir}\n")

        split_files = self.find_split_files()

        if not split_files:
            print("No split files found")
            return

        print(f"Found {len(split_files)} split files\n")

        # Group by original mapper name
        groups = self.group_by_original(split_files)
        print(f"Grouping into {len(groups)} original mappers\n")

        for original_name, files in sorted(groups.items()):
            if self.merge_files(original_name, files):
                self.stats['merged_files'] += 1

        self.print_summary()

    def print_summary(self):
        """Print merge summary"""
        print("\n" + "=" * 50)
        print("Summary:")
        print(f"  Split files processed: {self.stats['total_split_files']}")
        print(f"  Merged mapper files: {self.stats['merged_files']}")

        if self.stats['errors']:
            print(f"\n  Errors: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:
                print(f"    - {error}")
            if len(self.stats['errors']) > 5:
                print(f"    ... and {len(self.stats['errors']) - 5} more")


def simple_merge(source_dir: str, output_file: str, namespace: str = None):
    """Simple merge mode - merge all split files into single output file"""

    # Convert to absolute paths
    source_path = Path(source_dir).resolve()
    output_path = Path(output_file).resolve()

    # Validate source directory
    if not source_path.exists():
        raise FileNotFoundError(f"Source directory not found: {source_path}")

    # Find all XML files
    xml_files = sorted(source_path.glob('*.xml'))
    if not xml_files:
        raise FileNotFoundError(f"No XML files found in {source_path}")

    print(f"Found {len(xml_files)} XML files")

    # Create root mapper element
    root = ET.Element('mapper')
    if namespace:
        root.set('namespace', namespace)
    else:
        # Try to get namespace from first file
        first_tree = ET.parse(xml_files[0])
        first_root = first_tree.getroot()
        ns = first_root.get('namespace')
        if ns:
            root.set('namespace', ns)
            print(f"Using namespace: {ns}")

    # Track common elements (resultMap, sql fragments)
    common_elements = []
    common_ids = set()
    sql_elements = []

    for xml_file in xml_files:
        try:
            tree = ET.parse(xml_file)
            file_root = tree.getroot()

            for child in file_root:
                if child.tag in ['resultMap', 'sql']:
                    # Check if already added
                    elem_id = child.get('id', '')
                    if elem_id and elem_id not in common_ids:
                        common_elements.append(child)
                        common_ids.add(elem_id)
                elif child.tag in ['select', 'insert', 'update', 'delete']:
                    sql_elements.append(child)
        except Exception as e:
            print(f"  ⚠ Error parsing {xml_file.name}: {e}")

    # Add common elements first
    for elem in common_elements:
        root.append(elem)

    # Add SQL elements
    for elem in sql_elements:
        root.append(elem)

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Format XML
    ET.indent(root, space="    ")
    tree = ET.ElementTree(root)

    with open(output_path, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(b'<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" ')
        f.write(b'"http://mybatis.org/dtd/mybatis-3-mapper.dtd">\n')
        tree.write(f, encoding='utf-8', xml_declaration=False)

    print(f"✓ Merged {len(common_elements)} common elements + {len(sql_elements)} SQL statements")
    print(f"✓ Output: {output_path}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Merge split MyBatis mapper files back into original structure'
    )
    parser.add_argument(
        '--source-dir',
        type=str,
        required=True,
        help='Source directory with split files (e.g., ./mappers/project/target)'
    )
    parser.add_argument(
        '--target-dir',
        type=str,
        help='Target directory for merged files (e.g., /workspace/target/project)'
    )
    parser.add_argument(
        '--original-source-dir',
        type=str,
        help='Original source directory to find file paths (e.g., /workspace/source/project)'
    )
    parser.add_argument(
        '--simple',
        action='store_true',
        help='Simple mode: merge into single file'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path (for simple mode)'
    )
    parser.add_argument(
        '--namespace',
        type=str,
        help='Mapper namespace (for simple mode)'
    )

    args = parser.parse_args()

    if args.simple:
        # Simple merge mode
        if not args.output:
            print("✗ --output required for simple mode")
            sys.exit(1)
        simple_merge(args.source_dir, args.output, args.namespace)
    else:
        # Original full merge mode
        if not args.target_dir or not args.original_source_dir:
            print("✗ --target-dir and --original-source-dir required for full mode")
            sys.exit(1)
        merger = MapperMerger(args.source_dir, args.target_dir, args.original_source_dir)
        merger.merge_all()


if __name__ == "__main__":
    main()
