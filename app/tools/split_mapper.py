#!/usr/bin/env python3
"""
MyBatis Mapper Splitter
Splits large mapper XML files into individual SQL statement files
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any
import re


class MapperSplitter:
    """MyBatis mapper file splitter"""

    # SQL statement tags to extract
    SQL_TAGS = ['select', 'insert', 'update', 'delete']
    # Tags that should be preserved in all split files
    COMMON_TAGS = ['resultMap', 'sql']

    def __init__(self, source_dir: str, output_dir: str = None):
        # Convert to absolute paths
        self.source_dir = Path(source_dir).resolve()
        self.output_dir = Path(output_dir).resolve() if output_dir else self.source_dir

        # Validate source directory
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {self.source_dir}")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'total_sqls': 0,
            'errors': []
        }

    def find_mapper_files(self) -> List[Path]:
        """Find all mapper XML files in source directory"""
        mapper_files = list(self.source_dir.rglob('*.xml'))
        self.stats['total_files'] = len(mapper_files)
        return mapper_files

    def parse_mapper(self, file_path: Path) -> Dict[str, Any]:
        """Parse mapper XML file"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Get namespace
            namespace = root.get('namespace', '')

            # Extract common elements (resultMap, sql fragments)
            common_elements = []
            for tag in self.COMMON_TAGS:
                elements = root.findall(f".//{tag}")
                for elem in elements:
                    common_elements.append(elem)

            # Extract all SQL statements
            sql_elements = []
            for tag in self.SQL_TAGS:
                elements = root.findall(f".//{tag}")
                for elem in elements:
                    sql_id = elem.get('id')
                    if sql_id:
                        sql_elements.append({
                            'tag': tag,
                            'id': sql_id,
                            'element': elem
                        })

            return {
                'namespace': namespace,
                'common_elements': common_elements,
                'sql_elements': sql_elements,
                'root': root
            }
        except ET.ParseError as e:
            return {'error': f"XML parse error: {e}"}
        except Exception as e:
            return {'error': f"Error: {e}"}

    def create_split_file(self, file_path: Path, sql_info: Dict[str, Any],
                         namespace: str, common_elements: List) -> Path:
        """Create individual mapper file for a SQL statement"""
        # Generate output filename: OriginalName_sqlId.xml
        base_name = file_path.stem
        sql_id = sql_info['id']
        output_filename = f"{base_name}_{sql_id}.xml"

        # Use output directory if specified, otherwise same as source
        output_path = self.output_dir / output_filename
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create new XML structure
        root = ET.Element('mapper')
        root.set('namespace', namespace)

        # Add common elements (resultMap, sql fragments) first
        for common_elem in common_elements:
            root.append(common_elem)

        # Add the SQL element
        root.append(sql_info['element'])

        # Create XML tree
        tree = ET.ElementTree(root)

        # Add XML declaration and DOCTYPE
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
        doctype = '<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">\n'

        # Write with proper formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_declaration)
            f.write(doctype)

            # Convert element to string and write
            xml_str = ET.tostring(root, encoding='unicode', method='xml')
            # Pretty print
            xml_str = self.prettify_xml(xml_str)
            f.write(xml_str)

        return output_path

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

    def split_mapper_file(self, file_path: Path) -> int:
        """Split a mapper file into individual SQL files"""
        print(f"Processing: {file_path.name}")

        parsed = self.parse_mapper(file_path)

        if 'error' in parsed:
            print(f"  ✗ {parsed['error']}")
            self.stats['errors'].append(f"{file_path.name}: {parsed['error']}")
            return 0

        sql_elements = parsed['sql_elements']
        common_elements = parsed['common_elements']
        namespace = parsed['namespace']

        if not sql_elements:
            print(f"  ⚠ No SQL statements found")
            return 0

        # Show common elements count
        if common_elements:
            print(f"  ℹ {len(common_elements)} common elements (resultMap/sql fragments)")

            base_name = file_path.stem

            # Separate resultMap and sql fragments
            resultMaps = [elem for elem in common_elements if elem.tag == 'resultMap']
            sqlFragments = [elem for elem in common_elements if elem.tag == 'sql']
            otherCommons = [elem for elem in common_elements if elem.tag not in ['resultMap', 'sql']]

            # Save each resultMap to individual file
            for elem in resultMaps:
                elem_id = elem.get('id', 'unknown')
                resultmap_filename = f"{base_name}_resultMap_{elem_id}.xml"
                resultmap_path = self.output_dir / resultmap_filename

                root = ET.Element('mapper')
                root.set('namespace', namespace)
                root.append(elem)

                xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
                doctype = '<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">\n'

                with open(resultmap_path, 'w', encoding='utf-8') as f:
                    f.write(xml_declaration)
                    f.write(doctype)
                    xml_str = ET.tostring(root, encoding='unicode', method='xml')
                    xml_str = self.prettify_xml(xml_str)
                    f.write(xml_str)

                print(f"  ✓ resultMap#{elem_id} → {resultmap_filename}")

            # Save each sql fragment to individual file
            for elem in sqlFragments:
                elem_id = elem.get('id', 'unknown')
                fragment_filename = f"{base_name}_fragment_{elem_id}.xml"
                fragment_path = self.output_dir / fragment_filename

                root = ET.Element('mapper')
                root.set('namespace', namespace)
                root.append(elem)

                xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
                doctype = '<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">\n'

                with open(fragment_path, 'w', encoding='utf-8') as f:
                    f.write(xml_declaration)
                    f.write(doctype)
                    xml_str = ET.tostring(root, encoding='unicode', method='xml')
                    xml_str = self.prettify_xml(xml_str)
                    f.write(xml_str)

                print(f"  ✓ sql#{elem_id} → {fragment_filename}")

            # Save other common elements (cache, parameterMap, etc.) if any
            if otherCommons:
                for elem in otherCommons:
                    elem_id = elem.get('id', elem.tag)
                    other_filename = f"{base_name}_{elem.tag}_{elem_id}.xml"
                    other_path = self.output_dir / other_filename

                    root = ET.Element('mapper')
                    root.set('namespace', namespace)
                    root.append(elem)

                    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
                    doctype = '<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">\n'

                    with open(other_path, 'w', encoding='utf-8') as f:
                        f.write(xml_declaration)
                        f.write(doctype)
                        xml_str = ET.tostring(root, encoding='unicode', method='xml')
                        xml_str = self.prettify_xml(xml_str)
                        f.write(xml_str)

                    print(f"  ✓ {elem.tag}#{elem_id} → {other_filename}")

        split_count = 0
        for sql_info in sql_elements:
            try:
                # Pass empty list for common_elements - they're in separate file now
                output_path = self.create_split_file(
                    file_path,
                    sql_info,
                    namespace,
                    []  # No common elements in individual files
                )
                split_count += 1
                print(f"  ✓ {sql_info['tag']}#{sql_info['id']} → {output_path.name}")
            except Exception as e:
                error_msg = f"{file_path.name} - {sql_info['id']}: {e}"
                print(f"  ✗ Error creating {sql_info['id']}: {e}")
                self.stats['errors'].append(error_msg)

        return split_count

    def split_all(self):
        """Split all mapper files in source directory"""
        print(f"Source: {self.source_dir}")
        print(f"Output: {self.output_dir}\n")

        mapper_files = self.find_mapper_files()

        if not mapper_files:
            print("No mapper files found")
            return

        print(f"Found {len(mapper_files)} mapper files\n")

        for mapper_file in mapper_files:
            split_count = self.split_mapper_file(mapper_file)
            if split_count > 0:
                self.stats['processed_files'] += 1
                self.stats['total_sqls'] += split_count
            print()

        self.print_summary()

    def print_summary(self):
        """Print split summary"""
        print("=" * 50)
        print("Summary:")
        print(f"  Total mapper files: {self.stats['total_files']}")
        print(f"  Processed files: {self.stats['processed_files']}")
        print(f"  Total SQL statements split: {self.stats['total_sqls']}")

        if self.stats['errors']:
            print(f"\n  Errors: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:
                print(f"    - {error}")
            if len(self.stats['errors']) > 5:
                print(f"    ... and {len(self.stats['errors']) - 5} more")


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
        description='Split MyBatis mapper files into individual SQL files'
    )
    parser.add_argument(
        '--source-dir',
        type=str,
        required=True,
        help='Source mapper directory'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory for split files (default: same as source-dir)'
    )

    args = parser.parse_args()

    # Run splitter
    splitter = MapperSplitter(args.source_dir, args.output_dir)
    splitter.split_all()


if __name__ == "__main__":
    main()
