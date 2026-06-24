"""
MyBatis XML Mapper MCP Tools

Tools for extracting, analyzing, and merging MyBatis XML mapper files.
Based on the original OMA xmlExtractor.py and xmlMerger.py implementations.
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Optional
from lxml import etree
from strands import tool


def parse_mybatis_xml(xml_path: str) -> Dict:
    """
    Parse MyBatis XML mapper file.

    Args:
        xml_path: Path to XML file

    Returns:
        Dictionary with parsed XML structure

    Raises:
        Exception: If XML parsing fails
    """
    with open(xml_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()

    # Extract XML header
    header_match = re.search(r'(<\?xml.*?\?>)', xml_content, re.DOTALL)
    xml_header = header_match.group(1) if header_match else '<?xml version="1.0" encoding="UTF-8"?>'

    # Extract DOCTYPE
    doctype_match = re.search(r'(<!DOCTYPE.*?>)', xml_content, re.DOTALL)
    xml_doctype = doctype_match.group(1) if doctype_match else (
        '<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" '
        '"http://mybatis.org/dtd/mybatis-3-mapper.dtd">'
    )

    # Extract namespace
    namespace_pattern = re.compile(r'<mapper\s+namespace\s*=\s*["\']([^"\']+)["\']')
    namespace_match = namespace_pattern.search(xml_content)
    namespace = namespace_match.group(1) if namespace_match else "Unknown"

    # Parse with lxml
    try:
        root = etree.fromstring(xml_content.encode('utf-8'))
    except Exception as e:
        raise Exception(f"Failed to parse XML: {str(e)}")

    return {
        "header": xml_header,
        "doctype": xml_doctype,
        "namespace": namespace,
        "root": root,
        "content": xml_content
    }


@tool
def mybatis_extract_sqls(xml_path: str) -> str:
    """
    Extract SQL statements from MyBatis XML mapper file.

    Args:
        xml_path: Path to MyBatis XML mapper file

    Returns:
        JSON string with extracted SQL statements. Format:
        {
            "success": true,
            "mapper_file": "UserMapper.xml",
            "namespace": "com.example.mapper.UserMapper",
            "sqls": [
                {
                    "id": "selectUser",
                    "type": "select",
                    "sql": "SELECT * FROM users WHERE id = #{id}",
                    "includes": ["commonColumns"],
                    "dynamic_tags": ["if", "where"],
                    "result_type": "com.example.User",
                    "parameter_type": "int"
                },
                ...
            ]
        }

    Example:
        >>> mybatis_extract_sqls("/path/to/UserMapper.xml")
    """
    try:
        if not os.path.exists(xml_path):
            return json.dumps({
                "success": False,
                "error": f"File not found: {xml_path}"
            })

        parsed = parse_mybatis_xml(xml_path)
        root = parsed["root"]
        namespace = parsed["namespace"]

        sqls = []

        # SQL statement tags
        sql_tags = ['select', 'insert', 'update', 'delete', 'sql']

        for elem in root:
            # Skip non-element nodes (comments, processing instructions)
            if not isinstance(elem.tag, str):
                continue
            tag_name = etree.QName(elem.tag).localname

            if tag_name in sql_tags:
                # Extract attributes
                sql_id = elem.get('id', f'{tag_name}_{len(sqls) + 1}')
                result_type = elem.get('resultType', elem.get('resultMap', ''))
                parameter_type = elem.get('parameterType', '')

                # Extract SQL text (including nested elements)
                sql_text = etree.tostring(elem, encoding='unicode', method='text')
                sql_text = ' '.join(sql_text.split())  # Normalize whitespace

                # Find <include> references
                includes = []
                for include_elem in elem.findall('.//{http://mybatis.org/schema/mybatis-3-mapper}include'):
                    refid = include_elem.get('refid', '')
                    if refid:
                        includes.append(refid)

                # Find dynamic tags
                dynamic_tags = set()
                for descendant in elem.iter():
                    if not isinstance(descendant.tag, str):
                        continue
                    tag = etree.QName(descendant.tag).localname
                    if tag in ['if', 'choose', 'when', 'otherwise', 'foreach', 'where', 'set', 'trim', 'bind']:
                        dynamic_tags.add(tag)

                sqls.append({
                    "id": sql_id,
                    "type": tag_name,
                    "sql": sql_text,
                    "includes": includes,
                    "dynamic_tags": list(dynamic_tags),
                    "result_type": result_type,
                    "parameter_type": parameter_type
                })

        return json.dumps({
            "success": True,
            "mapper_file": os.path.basename(xml_path),
            "namespace": namespace,
            "sqls": sqls,
            "count": len(sqls)
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })


@tool
def mybatis_merge_sqls(original_xml_path: str, converted_sqls: str, output_path: str) -> str:
    """
    Merge converted SQLs back into MyBatis XML mapper file.

    This preserves the original structure, CDATA sections, dynamic tags, and comments
    while replacing only the SQL content.

    Args:
        original_xml_path: Path to original MyBatis XML mapper
        converted_sqls: JSON string with converted SQLs (format: [{"id": "...", "sql": "..."}, ...])
        output_path: Path for output merged XML file

    Returns:
        JSON string with merge result. Format:
        {
            "success": true,
            "merged_count": 5,
            "output_file": "/path/to/output.xml"
        }

    Example:
        >>> mybatis_merge_sqls(
        ...     "/path/to/original.xml",
        ...     '[{"id": "selectUser", "sql": "SELECT * FROM users WHERE id = $1"}]',
        ...     "/path/to/merged.xml"
        ... )
    """
    try:
        if not os.path.exists(original_xml_path):
            return json.dumps({
                "success": False,
                "error": f"Original file not found: {original_xml_path}"
            })

        # Parse converted SQLs
        try:
            converted_map = {item['id']: item['sql'] for item in json.loads(converted_sqls)}
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Invalid converted_sqls JSON: {str(e)}"
            })

        # Read original XML
        with open(original_xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()

        parsed = parse_mybatis_xml(original_xml_path)
        header = parsed["header"]
        doctype = parsed["doctype"]
        namespace = parsed["namespace"]

        # Parse XML with lxml preserving structure
        parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False)
        root = etree.fromstring(xml_content.encode('utf-8'), parser)

        merged_count = 0

        # Update SQL elements
        for elem in root:
            if not isinstance(elem.tag, str):
                continue
            tag_name = etree.QName(elem.tag).localname
            sql_id = elem.get('id', '')

            if tag_name in ['select', 'insert', 'update', 'delete'] and sql_id in converted_map:
                # Replace SQL content
                converted_sql = converted_map[sql_id]

                # Clear existing content
                for child in list(elem):
                    elem.remove(child)
                elem.text = None

                # Store converted SQL for CDATA post-processing
                elem.text = f"__CDATA_START__{sql_id}__CDATA_END__"
                converted_map[f"__placeholder__{sql_id}"] = converted_sql

                merged_count += 1

        # Generate output XML
        output_xml = etree.tostring(
            root,
            encoding='unicode',
            pretty_print=True,
            xml_declaration=False
        )

        # Post-process: replace placeholders with proper CDATA sections
        for sql_id, sql_text in converted_map.items():
            if sql_id.startswith("__placeholder__"):
                real_id = sql_id.replace("__placeholder__", "")
                placeholder = f"__CDATA_START__{real_id}__CDATA_END__"
                cdata_text = f"\n    <![CDATA[\n    {sql_text}\n    ]]>\n  "
                output_xml = output_xml.replace(placeholder, cdata_text)

        # Reconstruct full XML with header and doctype
        full_xml = f"{header}\n{doctype}\n{output_xml}"

        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_xml)

        return json.dumps({
            "success": True,
            "merged_count": merged_count,
            "output_file": output_path,
            "namespace": namespace
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })


@tool
def mybatis_scan_directory(directory: str) -> str:
    """
    Scan directory for MyBatis XML mapper files and count SQL statements.

    Args:
        directory: Directory path to scan

    Returns:
        JSON string with scan results. Format:
        {
            "success": true,
            "mappers": [
                {
                    "file": "UserMapper.xml",
                    "path": "/full/path/UserMapper.xml",
                    "namespace": "com.example.mapper.UserMapper",
                    "sql_count": 12,
                    "select_count": 5,
                    "insert_count": 2,
                    "update_count": 3,
                    "delete_count": 2
                },
                ...
            ]
        }

    Example:
        >>> mybatis_scan_directory("/path/to/mybatis/mappers")
    """
    try:
        if not os.path.isdir(directory):
            return json.dumps({
                "success": False,
                "error": f"Directory not found: {directory}"
            })

        mappers = []

        # Find all XML files
        xml_files = list(Path(directory).rglob('*.xml'))

        for xml_file in xml_files:
            try:
                # Try to parse as MyBatis mapper
                parsed = parse_mybatis_xml(str(xml_file))
                root = parsed["root"]
                namespace = parsed["namespace"]

                # Count SQL statements by type
                counts = {
                    "select": 0,
                    "insert": 0,
                    "update": 0,
                    "delete": 0,
                    "sql": 0
                }

                for elem in root:
                    if not isinstance(elem.tag, str):
                        continue
                    tag_name = etree.QName(elem.tag).localname
                    if tag_name in counts:
                        counts[tag_name] += 1

                total_count = sum(counts.values())

                mappers.append({
                    "file": xml_file.name,
                    "path": str(xml_file.absolute()),
                    "namespace": namespace,
                    "sql_count": total_count,
                    "select_count": counts["select"],
                    "insert_count": counts["insert"],
                    "update_count": counts["update"],
                    "delete_count": counts["delete"]
                })

            except Exception as exc:
                # Skip non-MyBatis XML files (lxml parse error, missing namespace, etc.)
                import logging as _log
                _log.getLogger(__name__).debug("Skipping non-MyBatis XML %s: %s", xml_file, exc)
                continue

        return json.dumps({
            "success": True,
            "directory": directory,
            "mappers": mappers,
            "total_mappers": len(mappers),
            "total_sqls": sum(m["sql_count"] for m in mappers)
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })


@tool
def mybatis_validate_xml(xml_path: str) -> str:
    """
    Validate MyBatis XML structure after merge or modification.

    Args:
        xml_path: Path to XML file to validate

    Returns:
        JSON string with validation result. Format:
        {
            "success": true,
            "valid": true,
            "namespace": "com.example.mapper.UserMapper",
            "sql_count": 10,
            "issues": []
        }

    Example:
        >>> mybatis_validate_xml("/path/to/UserMapper.xml")
    """
    try:
        if not os.path.exists(xml_path):
            return json.dumps({
                "success": False,
                "error": f"File not found: {xml_path}"
            })

        issues = []

        # Try to parse XML
        try:
            parsed = parse_mybatis_xml(xml_path)
            root = parsed["root"]
            namespace = parsed["namespace"]
        except Exception as e:
            return json.dumps({
                "success": True,
                "valid": False,
                "issues": [f"XML parsing failed: {str(e)}"]
            })

        # Check namespace
        if not namespace or namespace == "Unknown":
            issues.append("Missing or invalid namespace attribute")

        # Validate SQL elements
        sql_count = 0
        seen_ids = set()

        for elem in root:
            if not isinstance(elem.tag, str):
                continue
            tag_name = etree.QName(elem.tag).localname

            if tag_name in ['select', 'insert', 'update', 'delete', 'sql']:
                sql_count += 1
                sql_id = elem.get('id', '')

                # Check for duplicate IDs
                if sql_id:
                    if sql_id in seen_ids:
                        issues.append(f"Duplicate ID found: {sql_id}")
                    seen_ids.add(sql_id)
                else:
                    issues.append(f"Missing ID attribute in <{tag_name}> element")

                # Check for empty SQL
                sql_text = etree.tostring(elem, encoding='unicode', method='text').strip()
                if not sql_text:
                    issues.append(f"Empty SQL in element with ID: {sql_id or '(no id)'}")

        # Check for include references
        for elem in root.iter():
            if not isinstance(elem.tag, str):
                continue
            if etree.QName(elem.tag).localname == 'include':
                refid = elem.get('refid', '')
                if refid and refid not in seen_ids:
                    issues.append(f"<include> references undefined SQL fragment: {refid}")

        return json.dumps({
            "success": True,
            "valid": len(issues) == 0,
            "namespace": namespace,
            "sql_count": sql_count,
            "issues": issues
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })
