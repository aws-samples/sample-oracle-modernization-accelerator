#!/usr/bin/env python3.11
"""
Analyze validation errors and extract type casting issues only
"""

import json
import sys
from pathlib import Path

# Type casting error patterns
TYPE_CAST_ERROR_PATTERNS = [
    "operator does not exist",
    "invalid input syntax for type",
    "cannot cast"
]

def is_type_cast_error(error_message: str) -> bool:
    """Check if error is a type casting issue"""
    return any(pattern in error_message for pattern in TYPE_CAST_ERROR_PATTERNS)

def analyze_validation_report(report_path: Path) -> dict:
    """Analyze validation report and extract type casting errors"""

    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)

    type_errors = []

    for error in report.get('errors', []):
        sql_id = error.get('sql_id', '')
        error_msg = error.get('error_message', '')

        if is_type_cast_error(error_msg):
            # Extract PostgreSQL error message
            pg_error = ""
            if "ERROR:" in error_msg:
                pg_error = error_msg.split("ERROR:")[1].split("###")[0].strip()

            type_errors.append({
                'sql_id': sql_id,
                'error_type': 'type_casting',
                'pg_error': pg_error,
                'full_message': error_msg
            })

    return {
        'total_errors': len(report.get('errors', [])),
        'type_cast_errors': len(type_errors),
        'errors': type_errors
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python3.11 analyze_type_errors.py <validation-report.json>")
        sys.exit(1)

    report_path = Path(sys.argv[1])

    if not report_path.exists():
        print(f"Error: {report_path} not found")
        sys.exit(1)

    result = analyze_validation_report(report_path)

    print(f"\n{'='*70}")
    print(f"Type Casting Error Analysis")
    print(f"{'='*70}")
    print(f"Total validation errors: {result['total_errors']}")
    print(f"Type casting errors: {result['type_cast_errors']}")
    print(f"{'='*70}\n")

    if result['type_cast_errors'] > 0:
        print("Type Casting Errors:\n")
        for idx, error in enumerate(result['errors'], 1):
            print(f"{idx}. {error['sql_id']}")
            print(f"   Error: {error['pg_error']}")
            print()

        # Save detailed result
        output_path = report_path.parent / "type-cast-errors.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Detailed report saved: {output_path}")
    else:
        print("✅ No type casting errors found!")

if __name__ == "__main__":
    main()
