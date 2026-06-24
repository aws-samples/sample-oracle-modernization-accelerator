"""
DMS Schema Conversion MCP Tools

Tools for parsing AWS DMS Schema Conversion Tool assessment reports
and identifying objects that failed automatic conversion.
"""

import os
import csv
import json
import zipfile
import glob
from pathlib import Path
from typing import List, Dict
from strands import tool


# Mapping from CSV categories to Oracle object types
CATEGORY_TO_OBJECT_TYPE = {
    "User": "USER",
    "Schema": "SCHEMA",
    "Tablespace": "TABLESPACE",
    "Table": "TABLE",
    "Constraint": "CONSTRAINT",
    "Index": "INDEX",
    "Sequence": "SEQUENCE",
    "View": "VIEW",
    "Synonym": "SYNONYM",
    "Function": "FUNCTION",
    "Procedure": "PROCEDURE",
    "Package": "PACKAGE",
    "Package body": "PACKAGE BODY",
    "Package procedure": "PACKAGE",
    "Package function": "PACKAGE",
    "Trigger": "TRIGGER",
    "Type": "TYPE",
    "Type body": "TYPE BODY",
    "Privilege": "PRIVILEGE",
    "Role": "ROLE"
}


def extract_object_name(occurrence: str, category: str) -> str:
    """
    Extract object name from DMS occurrence field.

    Args:
        occurrence: Occurrence field from CSV
        category: Category field from CSV

    Returns:
        Extracted object name
    """
    if not occurrence:
        return ""

    # Different patterns based on category
    if "Schemas." in occurrence:
        # Extract from patterns like "Schemas.SCT.Packages.MIGRATION_MGR.Public procedures.INSERTDATAQUALITYPARAM"
        parts = occurrence.split('.')
        if len(parts) >= 3:
            if category in ["Package procedure", "Package function"]:
                # For package procedures/functions, return the package name
                if len(parts) >= 4 and "Packages" in parts:
                    pkg_index = parts.index("Packages")
                    if pkg_index + 1 < len(parts):
                        return parts[pkg_index + 1]
            return parts[-1]

    # Default: return the last part of the occurrence
    return occurrence.split('.')[-1]


@tool
def dms_parse_assessment_csv(csv_path: str) -> str:
    """
    Parse DMS Schema Conversion Tool assessment CSV file.

    Args:
        csv_path: Path to DMS assessment CSV file or ZIP file containing CSV

    Returns:
        JSON string with parsed assessment. Format:
        {
            "success": true,
            "total_objects": 150,
            "by_complexity": {
                "Simple": 80,
                "Medium": 45,
                "Complex": 25
            },
            "by_category": {
                "Table": 50,
                "View": 20,
                "Procedure": 30,
                ...
            },
            "medium_complex_objects": [
                {
                    "category": "Procedure",
                    "object_type": "PROCEDURE",
                    "occurrence": "Schemas.HR.Procedures.UPDATE_SALARY",
                    "object_name": "UPDATE_SALARY",
                    "schema_name": "HR",
                    "complexity": "Medium"
                },
                ...
            ]
        }

    Example:
        >>> dms_parse_assessment_csv("/path/to/ORACLE_AURORA_POSTGRESQL_20240301.zip")
    """
    try:
        # Check if input is a ZIP file
        actual_csv_path = csv_path

        if csv_path.endswith('.zip'):
            if not os.path.exists(csv_path):
                return json.dumps({
                    "success": False,
                    "error": f"ZIP file not found: {csv_path}"
                })

            # Extract ZIP to temporary directory
            extract_dir = os.path.join(os.path.dirname(csv_path), 'extracted_csv')
            os.makedirs(extract_dir, exist_ok=True)

            try:
                with zipfile.ZipFile(csv_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to extract ZIP: {str(e)}"
                })

            # Find CSV file in extracted directory
            csv_files = list(Path(extract_dir).rglob('*.csv'))
            if not csv_files:
                return json.dumps({
                    "success": False,
                    "error": "No CSV files found in ZIP archive"
                })

            actual_csv_path = str(csv_files[0])

        elif not os.path.exists(csv_path):
            return json.dumps({
                "success": False,
                "error": f"CSV file not found: {csv_path}"
            })

        # Parse CSV
        objects_by_complexity = {"Simple": 0, "Medium": 0, "Complex": 0}
        objects_by_category = {}
        medium_complex_objects = []

        with open(actual_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                complexity = row.get('Estimated complexity', '')
                category = row.get('Category', '')
                occurrence = row.get('Occurrence', '')
                schema_name = row.get('Schema name', '')

                # Count by complexity
                if complexity in objects_by_complexity:
                    objects_by_complexity[complexity] += 1

                # Count by category
                objects_by_category[category] = objects_by_category.get(category, 0) + 1

                # Collect Medium and Complex objects
                if complexity in ['Medium', 'Complex']:
                    object_name = extract_object_name(occurrence, category)

                    # Add schema prefix if available
                    if schema_name and not object_name.startswith(f"{schema_name}."):
                        full_name = f"{schema_name}.{object_name}"
                    else:
                        full_name = object_name

                    # Map category to object type
                    object_type = CATEGORY_TO_OBJECT_TYPE.get(category, category)

                    medium_complex_objects.append({
                        "category": category,
                        "object_type": object_type,
                        "occurrence": occurrence,
                        "object_name": object_name,
                        "full_name": full_name,
                        "schema_name": schema_name,
                        "complexity": complexity
                    })

        total_objects = sum(objects_by_complexity.values())

        return json.dumps({
            "success": True,
            "csv_file": actual_csv_path,
            "total_objects": total_objects,
            "by_complexity": objects_by_complexity,
            "by_category": objects_by_category,
            "medium_complex_count": len(medium_complex_objects),
            "medium_complex_objects": medium_complex_objects
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })


@tool
def dms_get_failed_objects(csv_path: str) -> str:
    """
    Extract objects that DMS Schema Conversion Tool could not automatically convert.

    This identifies Medium and Complex complexity objects that require manual
    intervention or AI-assisted conversion.

    Args:
        csv_path: Path to DMS assessment CSV file or ZIP file

    Returns:
        JSON string with failed objects grouped by type. Format:
        {
            "success": true,
            "failed_count": 70,
            "by_type": {
                "PROCEDURE": 25,
                "FUNCTION": 15,
                "PACKAGE": 10,
                "VIEW": 12,
                "TRIGGER": 8
            },
            "objects": {
                "PROCEDURE": ["HR.UPDATE_SALARY", "HR.CALC_BONUS", ...],
                "FUNCTION": ["HR.GET_EMPLOYEE_NAME", ...],
                ...
            }
        }

    Example:
        >>> dms_get_failed_objects("/path/to/assessment.zip")
    """
    try:
        # First parse the assessment
        parse_result = json.loads(dms_parse_assessment_csv(csv_path))

        if not parse_result.get("success"):
            return json.dumps(parse_result)

        medium_complex = parse_result.get("medium_complex_objects", [])

        # Group by object type
        objects_by_type = {}
        count_by_type = {}

        for obj in medium_complex:
            obj_type = obj["object_type"]
            full_name = obj["full_name"]

            if obj_type not in objects_by_type:
                objects_by_type[obj_type] = []
                count_by_type[obj_type] = 0

            objects_by_type[obj_type].append(full_name)
            count_by_type[obj_type] += 1

        # Sort each type's objects
        for obj_type in objects_by_type:
            objects_by_type[obj_type].sort()

        return json.dumps({
            "success": True,
            "failed_count": len(medium_complex),
            "by_type": count_by_type,
            "objects": objects_by_type,
            "source_file": parse_result.get("csv_file", csv_path)
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })
