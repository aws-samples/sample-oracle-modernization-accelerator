#!/usr/bin/env python3
"""
ASCT (AWS Schema Conversion Tool) Helper
This script helps convert Oracle schema objects to PostgreSQL compatible syntax
using Amazon Q for objects that DMS Schema Conversion couldn't automatically convert.
"""

import os
import csv
import subprocess
import glob
import re
from collections import defaultdict
import logging
import sys
import tempfile
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('../Logs/asct.log')
    ]
)
logger = logging.getLogger(__name__)

# Environment variables
ASCT_HOME = os.environ.get('ASCT_HOME', os.getcwd())
ORACLE_ADM_USER = os.environ.get('ORACLE_ADM_USER')
ORACLE_ADM_PASSWORD = os.environ.get('ORACLE_ADM_PASSWORD')
ORACLE_SVC_USER = os.environ.get('ORACLE_SVC_USER')
ORACLE_HOST = os.environ.get('ORACLE_HOST')
ORACLE_PORT = os.environ.get('ORACLE_PORT')
ORACLE_SID = os.environ.get('ORACLE_SID')
ORACLE_CONNECTION = f"{ORACLE_ADM_USER}/{ORACLE_ADM_PASSWORD}@{ORACLE_HOST}:{ORACLE_PORT}/{ORACLE_SID}"

# PostgreSQL connection variables
PGHOST = os.environ.get('PGHOST')
PGUSER = os.environ.get('PGUSER')
PGPORT = os.environ.get('PGPORT', '5432')
PGDATABASE = os.environ.get('PGDATABASE')
PGPASSWORD = os.environ.get('PGPASSWORD')
# Set PGPASSWORD environment variable for psql
if PGPASSWORD:
    os.environ['PGPASSWORD'] = PGPASSWORD

# Object type extraction order
OBJECT_TYPE_ORDER = [
    "USER", "SCHEMA",
    "TABLESPACE",
    "TABLE",
    "CONSTRAINT",
    "INDEX",
    "SEQUENCE",
    "VIEW",
    "SYNONYM",
    "FUNCTION",
    "PROCEDURE",
    "PACKAGE",
    "TRIGGER",
    "TYPE",
    "PRIVILEGE",
    "ROLE"
]
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

def find_csv_files():
    """Find the CSV files from the ORACLE_AURORA_POSTGRESQL zip file."""
    # Look for ORACLE_AURORA_POSTGRESQL zip files
    zip_files = glob.glob(os.path.join(ASCT_HOME, 'Assessments', 'ORACLE_AURORA_POSTGRESQL*.zip'))
    if not zip_files:
        logger.error(f"No ORACLE_AURORA_POSTGRESQL*.zip files found in {os.path.join(ASCT_HOME, 'Assessments')}")
        return None
    
    # Use the most recent zip file if multiple exist
    zip_file = sorted(zip_files)[-1]
    logger.info(f"Using zip file: {zip_file}")
    
    # Create extraction directory if it doesn't exist
    extract_dir = os.path.join(ASCT_HOME, 'Assessments', 'extracted_csv')
    os.makedirs(extract_dir, exist_ok=True)
    
    # Extract the zip file
    try:
        import zipfile
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        logger.info(f"Extracted {zip_file} to {extract_dir}")
    except Exception as e:
        logger.error(f"Error extracting zip file: {e}")
        return None
    
    # Find all CSV files in the extracted directory
    csv_files = glob.glob(os.path.join(extract_dir, '**', '*.csv'), recursive=True)
    if csv_files:
        # Return the first matching file
        logger.info(f"Found CSV file: {csv_files[0]}")
        return csv_files[0]
    
    logger.error("No CSV files found in the extracted directory")
    return None
def extract_objects_from_csv(csv_file):
    """
    Extract objects with Medium or Complex complexity from the CSV file.
    Returns a dictionary with object types as keys and sets of object names as values.
    """
    objects_by_type = defaultdict(set)

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                complexity = row.get('Estimated complexity', '')
                if complexity in ['Medium', 'Complex']:
                    category = row.get('Category', '')
                    occurrence = row.get('Occurrence', '')
                    schema_name = row.get('Schema name', '')

                    # Extract object name from occurrence
                    object_name = extract_object_name(occurrence, category)
                    if object_name:
                        # Add schema prefix if available
                        if schema_name and not object_name.startswith(f"{schema_name}."):
                            object_name = f"{schema_name}.{object_name}"

                        # Map category to object type
                        object_type = CATEGORY_TO_OBJECT_TYPE.get(category, category)
                        objects_by_type[object_type].add(object_name)

    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        return {}

    return objects_by_type

def extract_object_name(occurrence, category):
    """Extract the object name from the occurrence field."""
    if not occurrence:
        return None

    # Different patterns based on category
    if "Schemas." in occurrence:
        # Extract from patterns like "Schemas.SCT.Packages.MIGRATION_MGR.Public procedures.INSERTDATAQUALITYPARAM"
        parts = occurrence.split('.')
        if len(parts) >= 3:
            if category in ["Package procedure", "Package function"]:
                # For package procedures/functions, return the package name
                # Format: Schemas.SCT.Packages.MIGRATION_MGR.Public procedures.INSERTDATAQUALITYPARAM
                # We want to extract MIGRATION_MGR
                if len(parts) >= 4 and "Packages" in parts:
                    pkg_index = parts.index("Packages")
                    if pkg_index + 1 < len(parts):
                        return parts[pkg_index + 1]
            return parts[-1]

    # Default: return the last part of the occurrence
    return occurrence.split('.')[-1]
def save_incompatible_list(objects_by_type):
    """Save the list of incompatible objects to a file."""
    output_file = os.path.join(ASCT_HOME, 'Assessments', 'incompatible.lst')

    try:
        with open(output_file, 'w') as f:
            for object_type, objects in objects_by_type.items():
                for object_name in objects:
                    f.write(f"{object_type}\t{object_name}\n")

        logger.info(f"Saved incompatible objects list to {output_file}")
        return True

    except Exception as e:
        logger.error(f"Error saving incompatible objects list: {e}")
        return False

def generate_oracle_ddl_script(object_type, object_name):
    """Generate SQL script to extract DDL for an object."""
    # Set transformation parameters
    setup_commands = """
SET LONG 2000000
SET PAGESIZE 0
SET LINES 200
SET LINESIZE 32767
SET TRIMSPOOL ON
SET ECHO OFF
SET FEEDBACK OFF
SET VERIFY OFF
SET HEADING OFF

exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'STORAGE',false);
exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'TABLESPACE',false);
exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'SEGMENT_ATTRIBUTES',false);
exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'SQLTERMINATOR',true);
exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'PRETTY',true);
exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'BODY',true);
exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'CONSTRAINTS',false);
exec dbms_metadata.set_transform_param(dbms_metadata.session_transform,'PARTITIONING',false);
"""

    # Split schema and object name
    parts = object_name.split('.')
    if len(parts) > 1:
        schema = parts[0]
        name = parts[-1]
    else:
        schema = ORACLE_SVC_USER  # Default to the service user if no schema specified
        name = object_name

    # Generate the appropriate DBMS_METADATA call based on object type
    if object_type == "USER" or object_type == "SCHEMA":
        ddl_command = f"SELECT DBMS_METADATA.GET_DDL('USER', '{name}') FROM DUAL;"
    elif object_type == "PACKAGE":
        # For packages, we need both specification and body
        ddl_command = f"""
SELECT DBMS_METADATA.GET_DDL('PACKAGE_SPEC', '{name}', '{schema}') FROM DUAL;
SELECT DBMS_METADATA.GET_DDL('PACKAGE_BODY', '{name}', '{schema}') FROM DUAL;
"""
    elif object_type == "TYPE":
        # For types, we need both specification and body
        ddl_command = f"""
SELECT DBMS_METADATA.GET_DDL('TYPE_SPEC', '{name}', '{schema}') FROM DUAL;
SELECT DBMS_METADATA.GET_DDL('TYPE_BODY', '{name}', '{schema}') FROM DUAL;
"""
    else:
        # For other object types
        ddl_command = f"SELECT DBMS_METADATA.GET_DDL('{object_type}', '{name}', '{schema}') FROM DUAL;"

    return setup_commands + ddl_command
def extract_ddl_from_oracle(object_type, object_name):
    """Extract DDL from Oracle database using sqlplus."""
    try:
        # Create a temporary SQL file
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.sql', delete=False) as temp_file:
            # Add the script content
            temp_file.write(generate_oracle_ddl_script(object_type, object_name))
            # Add EXIT command to ensure sqlplus terminates
            temp_file.write("\nEXIT;\n")
            temp_file_path = temp_file.name

        # Execute sqlplus command
        cmd = f"sqlplus -S {ORACLE_CONNECTION} @{temp_file_path}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        # Clean up the temporary file
        os.unlink(temp_file_path)

        if result.returncode != 0:
            logger.error(f"Error executing sqlplus: {result.stderr}")
            return None

        return result.stdout.strip()

    except Exception as e:
        logger.error(f"Error extracting DDL: {e}")
        return None

def extract_object_info_from_filename(sql_file):
    """Extract object type and name from SQL filename."""
    basename = os.path.basename(sql_file)
    parts = basename.split('.')
    
    if len(parts) >= 3:
        obj_type = parts[0]
        # 나머지 부분을 객체 이름으로 결합 (마지막 .sql 제외)
        obj_name = '.'.join(parts[1:-1])
        return obj_type, obj_name
    
    return None, None
def convert_to_postgres(oracle_ddl, object_type, object_name, strict_mode=False):
    """
    Convert Oracle DDL to PostgreSQL compatible syntax using Amazon Q.
    
    Args:
        oracle_ddl: The Oracle DDL to convert
        object_type: The type of the object (TABLE, VIEW, etc.)
        object_name: The name of the object
        strict_mode: If True, use stricter conversion options for error recovery
    """
    try:
        # Save the original Oracle DDL first
        save_original_ddl(object_type, object_name, oracle_ddl)

        # Read the prompt template
        prompt_template_path = os.path.join(ASCT_HOME, 'Tools', 'DB01.oracle_to_postgres_prompt.txt')
        with open(prompt_template_path, 'r') as f:
            prompt_template = f.read()

        # Format the prompt with the object type and DDL
        prompt = prompt_template.format(object_type=object_type, oracle_ddl=oracle_ddl)
        
        # If in strict mode, add additional instructions for error recovery
        if strict_mode:
            prompt += "\n\n이 SQL은 이전에 변환 시도에서 구문 오류가 발생했습니다. 더 엄격한 PostgreSQL 호환성을 위해 다음 사항에 특히 주의해 주세요:\n"
            prompt += "1. 모든 식별자에 적절한 따옴표 사용\n"
            prompt += "2. 데이터 타입 호환성 확인\n"
            prompt += "3. 함수 인자와 반환 타입 명시\n"
            prompt += "4. 모든 문장이 세미콜론으로 끝나는지 확인\n"
            prompt += "5. Oracle 특정 기능을 PostgreSQL 대안으로 정확히 변환\n"

        # Create a temporary file for the prompt
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as prompt_file:
            prompt_file.write(prompt)
            prompt_file_path = prompt_file.name

        # Execute q chat command with output processing to remove log messages
        cmd = f"q chat < {prompt_file_path}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        # Clean up temporary file
        os.unlink(prompt_file_path)

        if result.returncode != 0:
            error_msg = f"Error executing Amazon Q: {result.stderr}"
            logger.error(error_msg)
            # Save the conversion failure reason
            save_failed_conversion(object_type, object_name, oracle_ddl, error_msg)
            return None

        # For debugging - save the raw output
        debug_file = os.path.join(ASCT_HOME, 'Logs', f'debug_{object_name.split(".")[-1]}.txt')
        with open(debug_file, 'w') as f:
            f.write(result.stdout)
        
        # Process the output to extract the PostgreSQL code
        # First, clean up ANSI color codes
        cleaned_output = re.sub(r'\u001B\[\d+(?:;\d+)*m', '', result.stdout)
        
        # Try to find SQL code blocks with markdown formatting
        sql_blocks = re.findall(r'```sql\n(.*?)\n```', cleaned_output, re.DOTALL)
        if sql_blocks:
            postgres_code = '\n\n'.join(sql_blocks)
        else:
            # If no SQL code blocks found, try to extract the relevant part
            # Look for CREATE statements
            create_match = re.search(r'(CREATE\s+OR\s+REPLACE\s+.*?;)', cleaned_output, re.DOTALL)
            if create_match:
                postgres_code = create_match.group(1)
            else:
                # Try to extract any SQL-like content
                lines = cleaned_output.strip().split('\n')
                code_lines = []
                in_code = False
                for line in lines:
                    # Check for markdown code block markers
                    if line.startswith('```') and not in_code:
                        in_code = True
                        continue
                    elif line.startswith('```') and in_code:
                        in_code = False
                        continue
                    # Include lines that are in a code block or start with SQL keywords
                    elif in_code or line.strip().startswith('CREATE ') or line.strip().startswith('ALTER '):
                        code_lines.append(line)
                
                postgres_code = '\n'.join(code_lines)
        
        # Clean up the PostgreSQL code
        postgres_code = postgres_code.strip()
        
        # Remove any markdown tags that might be at the end
        postgres_code = re.sub(r'<\/?\w+>$', '', postgres_code)
        
        # Check if this is a package - packages need special handling
        if object_type.upper() == 'PACKAGE' or 'PACKAGE' in object_type.upper():
            postgres_code = fix_package_conversion(postgres_code, object_name)
        else:
            # Format the code for better readability
            postgres_code = format_sql_code(postgres_code)
            
            # Final check for semicolons at the end of each CREATE statement
            postgres_code = ensure_semicolons_for_create_statements(postgres_code)
        
        # Check if we actually got valid PostgreSQL code
        if not postgres_code or len(postgres_code.strip()) < 10:  # Arbitrary minimum length for valid SQL
            # Try to manually create a basic conversion based on the object type
            if object_type.upper() == 'VIEW':
                # Extract view name and columns from Oracle DDL
                view_name_match = re.search(r'CREATE\s+OR\s+REPLACE.*?VIEW\s+"?(\w+)"?\."?(\w+)"?\s*\((.*?)\)\s+AS', oracle_ddl, re.DOTALL)
                if view_name_match:
                    schema = view_name_match.group(1)
                    name = view_name_match.group(2)
                    columns = view_name_match.group(3)
                    
                    # Extract the query part
                    query_match = re.search(r'AS\s+(SELECT.*?);', oracle_ddl, re.DOTALL)
                    if query_match:
                        query = query_match.group(1)
                        # Create a basic PostgreSQL view
                        postgres_code = f'CREATE OR REPLACE VIEW "{schema}"."{name}" ({columns}) AS\n{query};'
            
            elif object_type.upper() == 'PROCEDURE':
                # Extract procedure name from Oracle DDL
                proc_name_match = re.search(r'CREATE\s+OR\s+REPLACE.*?PROCEDURE\s+"?(\w+)"?\."?(\w+)"?', oracle_ddl, re.DOTALL)
                if proc_name_match:
                    name = proc_name_match.group(2).lower()
                    
                    # Create a basic PostgreSQL procedure
                    postgres_code = f"""CREATE OR REPLACE PROCEDURE {name}()
LANGUAGE plpgsql
AS $$
BEGIN
  -- Converted from Oracle procedure
  NULL;
END;
$$;"""
            
            # If we still don't have valid code, report failure
            if not postgres_code or len(postgres_code.strip()) < 10:
                error_msg = "Conversion failed: Empty or invalid PostgreSQL code generated"
                logger.error(error_msg)
                save_failed_conversion(object_type, object_name, oracle_ddl, error_msg)
                return None
        
        return postgres_code

    except Exception as e:
        error_msg = f"Error converting to PostgreSQL: {e}"
        logger.error(error_msg)
        # Save the original Oracle DDL to a failure log with the error message
        save_failed_conversion(object_type, object_name, oracle_ddl, error_msg)
        return None
def fix_package_conversion(postgres_code, package_name):
    """
    Fix common issues with package conversions.
    Oracle packages typically convert to multiple PostgreSQL functions.
    """
    # Extract the schema and package name
    parts = package_name.split('.')
    schema = parts[0] if len(parts) > 1 else 'public'
    pkg_name = parts[-1]

    # Check if the code is just a list of function declarations without bodies
    if all(line.strip().startswith('CREATE OR REPLACE FUNCTION') and ')' in line and not 'BEGIN' in postgres_code for line in postgres_code.split('\n')):
        # This is likely just function declarations without implementations
        functions = []
        for line in postgres_code.split('\n'):
            if line.strip().startswith('CREATE OR REPLACE FUNCTION'):
                # Extract function name
                match = re.search(r'FUNCTION\s+(\w+\.\w+)', line)
                if match:
                    func_name = match.group(1)
                    # Create a proper function with implementation
                    functions.append(f"""
CREATE OR REPLACE FUNCTION {func_name}()
RETURNS VOID AS $$
BEGIN
  -- Implementation for {func_name}
  NULL;
END;
$$ LANGUAGE plpgsql;
""")

        if functions:
            # Add a comment explaining this is a package conversion
            header = f"-- Converted from Oracle package {package_name}\n-- Each function represents a package procedure/function\n\n"
            # Add a variables table if needed
            vars_table = f"""
-- Package variables table
CREATE TABLE {schema}.{pkg_name}_vars (
  variable_name VARCHAR(100) PRIMARY KEY,
  variable_value VARCHAR(4000)
);

"""
            return header + vars_table + "\n".join(functions)

    # If we get here, try to format the code normally
    formatted_code = format_sql_code(postgres_code)
    return ensure_semicolons_for_create_statements(formatted_code)

def ensure_semicolons_for_create_statements(sql_code):
    """Ensure that each CREATE statement ends with a semicolon."""
    lines = sql_code.split('\n')
    result_lines = []

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        line_stripped = line.strip()

        # Check if this line is a CREATE statement
        if line_stripped.startswith('CREATE '):
            # Collect the entire CREATE statement which might span multiple lines
            create_stmt = [line]
            j = i + 1
            paren_count = line.count('(') - line.count(')')

            # Continue collecting lines until we find the end of the statement
            while j < len(lines) and (paren_count > 0 or not lines[j].strip().startswith('CREATE ')):
                next_line = lines[j].rstrip()
                create_stmt.append(next_line)
                paren_count += next_line.count('(') - next_line.count(')')

                # If we've closed all parentheses and found a natural end, break
                if paren_count <= 0 and (next_line.strip().endswith(';') or
                                        next_line.strip() == ')' or
                                        j == len(lines) - 1):
                    break
                j += 1

            # Join the collected statement and ensure it ends with a semicolon
            full_stmt = '\n'.join(create_stmt)
            if not full_stmt.rstrip().endswith(';'):
                full_stmt += ';'

            result_lines.append(full_stmt)
            i = j + 1
        else:
            result_lines.append(line)
            i += 1

    return '\n'.join(result_lines)
def save_original_ddl(object_type, object_name, oracle_ddl):
    """Save the original Oracle DDL to a file."""
    # Create oracle directory if it doesn't exist
    oracle_dir = os.path.join(ASCT_HOME, 'Assessments', 'oracle')
    os.makedirs(oracle_dir, exist_ok=True)

    # Extract just the object name without schema
    simple_name = object_name.split('.')[-1]

    # Save original Oracle DDL
    filename = f"{simple_name}.sql"
    with open(os.path.join(oracle_dir, filename), 'w') as f:
        f.write(oracle_ddl)

    logger.info(f"Saved original Oracle DDL to {filename}")

def format_sql_code(sql_code):
    """Format SQL code for better readability."""
    # Split into statements (assuming they end with semicolons)
    statements = re.split(r';\s*', sql_code)
    formatted_statements = []

    for stmt in statements:
        if not stmt.strip():
            continue

        # Basic formatting for common SQL keywords
        formatted = stmt.strip()

        # Add proper indentation after keywords
        keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING',
                   'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'OUTER JOIN',
                   'CREATE TABLE', 'CREATE FUNCTION', 'CREATE PROCEDURE', 'CREATE VIEW',
                   'ALTER TABLE', 'BEGIN', 'END', 'DECLARE', 'RETURN']

        for keyword in keywords:
            pattern = r'(?i)\b' + keyword + r'\b'
            if re.search(pattern, formatted):
                # Add newline and indentation after the keyword
                formatted = re.sub(pattern, '\n' + keyword, formatted)

        # Handle parentheses for better readability
        paren_level = 0
        chars = list(formatted)
        for i, char in enumerate(chars):
            if char == '(':
                paren_level += 1
                # Add newline after opening parenthesis for nested levels
                if paren_level > 1 and i+1 < len(chars):
                    chars[i] = '(\n' + '  ' * paren_level
            elif char == ')':
                paren_level = max(0, paren_level - 1)  # Avoid negative levels
                # Add newline before closing parenthesis for nested levels
                if paren_level > 0 and i > 0 and chars[i-1] != '\n':
                    chars[i] = '\n' + '  ' * paren_level + ')'

        formatted = ''.join(chars)

        # Ensure statement ends with semicolon
        if not formatted.rstrip().endswith(';'):
            formatted += ';'

        formatted_statements.append(formatted)

    # Join all statements and ensure each statement has a semicolon
    result = '\n\n'.join(formatted_statements)

    # Handle CREATE statements that might be on separate lines without semicolons
    # This is a common pattern in the output
    lines = result.split('\n')
    final_lines = []

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if line_stripped.startswith('CREATE ') and not line_stripped.endswith(';'):
            # Check if this is the last line or the next line also starts with CREATE
            if i == len(lines) - 1 or lines[i+1].strip().startswith('CREATE '):
                line += ';'
        final_lines.append(line)

    return '\n'.join(final_lines)
def save_failed_conversion(object_type, object_name, oracle_ddl, error_message=None):
    """Save the original Oracle DDL and error message for failed conversions."""
    # Create failed directory if it doesn't exist
    failed_dir = os.path.join(ASCT_HOME, 'failed_conversions')
    os.makedirs(failed_dir, exist_ok=True)

    # Sanitize object name for filename
    safe_name = re.sub(r'[^\w\-\.]', '_', object_name)

    # Save original Oracle DDL
    filename = f"{object_type}.{safe_name}.original.sql"
    with open(os.path.join(failed_dir, filename), 'w') as f:
        f.write(oracle_ddl)

    # Save error message if provided
    if error_message:
        log_filename = os.path.join(failed_dir, 'conversion_errors.log')
        with open(log_filename, 'a') as f:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] {object_type}.{object_name}: {error_message}\n")

    logger.info(f"Saved original Oracle DDL for failed conversion to {filename}")

def save_conversion_results(object_type, object_name, postgres_ddl):
    """Save the conversion results to files."""
    # Create transform directory if it doesn't exist
    transform_dir = os.path.join(ASCT_HOME, 'Transform')
    os.makedirs(transform_dir, exist_ok=True)

    # Sanitize object name for filename
    safe_name = re.sub(r'[^\w\-\.]', '_', object_name)

    # Save PostgreSQL DDL with the pattern object_type.object_name.sql
    filename = f"{object_type}.{safe_name}.sql"
    with open(os.path.join(transform_dir, filename), 'w') as f:
        f.write(postgres_ddl)

    logger.info(f"Saved conversion results to {filename}")

def execute_sql_command(sql_file):
    """Execute a SQL command and return the result."""
    cmd = f"psql -h {PGHOST} -U {PGUSER} -p {PGPORT} -d {PGDATABASE} -f {sql_file}"
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)
def execute_sql_with_recovery(sql_file, dependency_queue):
    """Execute SQL file with automatic recovery strategies."""
    # 첫 번째 시도
    result = execute_sql_command(sql_file)
    
    if result.returncode != 0:
        # 에러 메시지 출력
        logger.error(f"SQL execution error in {sql_file}: {result.stderr}")
        
        # 1. 구문 에러 처리 (다시 변환 시도)
        if "syntax error" in result.stderr:
            logger.info(f"Syntax error detected in {sql_file}, attempting to reconvert")
            
            # 원본 Oracle DDL 찾기
            obj_type, obj_name = extract_object_info_from_filename(sql_file)
            if obj_type and obj_name:
                # 원본 Oracle DDL 파일 경로
                oracle_file = os.path.join(ASCT_HOME, 'oracle', f"{obj_name.split('.')[-1]}.sql")
                
                if os.path.exists(oracle_file):
                    # 원본 DDL 읽기
                    with open(oracle_file, 'r') as f:
                        oracle_ddl = f.read()
                    
                    # 다시 변환 시도 (더 엄격한 옵션 사용)
                    logger.info(f"Reconverting {obj_type} {obj_name}")
                    postgres_ddl = convert_to_postgres(oracle_ddl, obj_type, obj_name, strict_mode=True)
                    
                    if postgres_ddl:
                        # 변환된 내용으로 임시 파일 생성
                        with tempfile.NamedTemporaryFile(mode='w+', suffix='.sql', delete=False) as temp_file:
                            temp_file.write(postgres_ddl)
                            temp_file_path = temp_file.name
                        
                        # 다시 변환된 파일로 재시도
                        logger.info(f"Retrying with reconverted SQL: {sql_file}")
                        result = execute_sql_command(temp_file_path)
                        
                        # 성공하면 원본 파일 업데이트
                        if result.returncode == 0:
                            with open(sql_file, 'w') as f:
                                f.write(postgres_ddl)
                            logger.info(f"Successfully reconverted and executed: {sql_file}")
                        else:
                            logger.error(f"Reconversion failed: {result.stderr}")
                        
                        os.unlink(temp_file_path)
        
        # 2. 객체가 이미 존재하는 경우 처리
        elif "already exists" in result.stderr:
            # SQL 파일 내용 수정: CREATE를 CREATE IF NOT EXISTS로 변경
            with open(sql_file, 'r') as f:
                content = f.read()
            
            modified_content = content.replace(
                'CREATE TABLE', 'CREATE TABLE IF NOT EXISTS'
            ).replace(
                'CREATE VIEW', 'CREATE OR REPLACE VIEW'
            ).replace(
                'CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION'
            ).replace(
                'CREATE PROCEDURE', 'CREATE OR REPLACE PROCEDURE'
            )
            
            # 수정된 내용으로 임시 파일 생성
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.sql', delete=False) as temp_file:
                temp_file.write(modified_content)
                temp_file_path = temp_file.name
            
            # 수정된 파일로 다시 시도
            logger.info(f"Retrying with IF NOT EXISTS clauses: {sql_file}")
            result = execute_sql_command(temp_file_path)
            
            # 성공하면 원본 파일 업데이트
            if result.returncode == 0:
                with open(sql_file, 'w') as f:
                    f.write(modified_content)
                logger.info(f"Successfully modified and executed: {sql_file}")
            else:
                logger.error(f"Modified SQL execution failed: {result.stderr}")
            
            os.unlink(temp_file_path)
        
        # 3. 참조하는 객체가 존재하지 않는 경우 (종속성 문제)
        elif "does not exist" in result.stderr:
            # 존재하지 않는 객체 이름 추출
            obj_match = re.search(r'relation "([^"]+)" does not exist', result.stderr)
            missing_obj = obj_match.group(1) if obj_match else None
            
            if missing_obj:
                logger.info(f"Missing dependency: {missing_obj}, adding to dependency queue")
                
                # 이 파일을 종속성 큐에 추가
                dependency_queue.append({
                    'file': sql_file,
                    'depends_on': missing_obj,
                    'attempts': 1
                })
                
                # 종속성 큐에 있는 파일들은 나중에 다시 시도
                return {'status': 'deferred', 'depends_on': missing_obj}
            else:
                logger.error(f"Could not extract missing dependency from error: {result.stderr}")
        
        # 4. 스키마가 존재하지 않는 경우
        elif "schema does not exist" in result.stderr:
            # 스키마 이름 추출
            schema_match = re.search(r'schema "([^"]+)" does not exist', result.stderr)
            if schema_match:
                schema_name = schema_match.group(1)
                
                # 스키마 생성 명령 실행
                create_schema_cmd = f"psql -h {PGHOST} -U {PGUSER} -p {PGPORT} -d {PGDATABASE} -c 'CREATE SCHEMA IF NOT EXISTS {schema_name};'"
                logger.info(f"Creating missing schema: {schema_name}")
                schema_result = subprocess.run(create_schema_cmd, shell=True, capture_output=True, text=True)
                
                if schema_result.returncode == 0:
                    logger.info(f"Successfully created schema: {schema_name}")
                    # 원래 SQL 다시 시도
                    result = execute_sql_command(sql_file)
                    if result.returncode != 0:
                        logger.error(f"SQL execution still failed after schema creation: {result.stderr}")
                else:
                    logger.error(f"Failed to create schema: {schema_result.stderr}")
            else:
                logger.error(f"Could not extract schema name from error: {result.stderr}")
        
        # 5. 따옴표 문제 처리 (식별자에 큰따옴표가 있는 경우)
        elif "syntax error" in result.stderr and '"' in result.stderr:
            # SQL 파일 내용 수정: 큰따옴표 제거
            with open(sql_file, 'r') as f:
                content = f.read()
            
            # 식별자에서 큰따옴표 제거
            modified_content = re.sub(r'"([^"]+)"', r'\1', content)
            
            # 수정된 내용으로 임시 파일 생성
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.sql', delete=False) as temp_file:
                temp_file.write(modified_content)
                temp_file_path = temp_file.name
            
            # 수정된 파일로 다시 시도
            logger.info(f"Retrying without quotes around identifiers: {sql_file}")
            result = execute_sql_command(temp_file_path)
            
            # 성공하면 원본 파일 업데이트
            if result.returncode == 0:
                with open(sql_file, 'w') as f:
                    f.write(modified_content)
                logger.info(f"Successfully modified and executed: {sql_file}")
            else:
                logger.error(f"Modified SQL execution failed: {result.stderr}")
            
            os.unlink(temp_file_path)
        
        # 6. 기타 에러 처리
        else:
            logger.error(f"Unhandled SQL error: {result.stderr}")
    
    return {'status': 'completed', 'result': result}
def deploy_to_postgres_with_dependency_handling():
    """Deploy SQL files with dependency handling."""
    if not PGHOST or not PGUSER or not PGDATABASE:
        logger.error("PostgreSQL connection environment variables not set")
        return 0, 0
    
    # 변환된 SQL 파일 가져오기
    transform_dir = os.path.join(ASCT_HOME, 'transform')
    if not os.path.exists(transform_dir):
        logger.error(f"Transform directory not found: {transform_dir}")
        return 0, 0
        
    sql_files = glob.glob(os.path.join(transform_dir, '*.sql'))
    if not sql_files:
        logger.warning("No SQL files found in transform directory")
        return 0, 0
    
    logger.info(f"Found {len(sql_files)} SQL files to deploy to PostgreSQL")
    
    # 객체 타입 순서에 따라 정렬
    sorted_files = []
    for object_type in OBJECT_TYPE_ORDER:
        for sql_file in list(sql_files):
            file_basename = os.path.basename(sql_file)
            if file_basename.upper().startswith(object_type.upper() + '.'):
                sorted_files.append(sql_file)
                sql_files.remove(sql_file)
    
    # 남은 파일들 추가
    sorted_files.extend(sql_files)
    
    # 종속성 큐 초기화
    dependency_queue = []
    executed_files = set()
    max_attempts = 3  # 최대 재시도 횟수
    
    # 첫 번째 실행 시도
    for sql_file in sorted_files:
        if sql_file not in executed_files:
            result = execute_sql_with_recovery(sql_file, dependency_queue)
            
            if result['status'] == 'completed' and result['result'].returncode == 0:
                executed_files.add(sql_file)
            # 종속성 문제로 지연된 파일은 큐에 이미 추가됨
    
    # 종속성 큐에 있는 파일 처리
    attempt = 1
    while dependency_queue and attempt <= max_attempts:
        logger.info(f"Processing deferred files, attempt {attempt}/{max_attempts}")
        
        # 현재 큐의 복사본 생성 (반복 중 큐가 수정될 수 있으므로)
        current_queue = dependency_queue.copy()
        dependency_queue = []
        
        for item in current_queue:
            sql_file = item['file']
            if sql_file in executed_files:
                continue
                
            # 재시도
            result = execute_sql_with_recovery(sql_file, dependency_queue)
            
            if result['status'] == 'completed' and result['result'].returncode == 0:
                executed_files.add(sql_file)
            elif result['status'] == 'deferred':
                # 시도 횟수 증가
                item['attempts'] += 1
                if item['attempts'] <= max_attempts:
                    dependency_queue.append(item)
                else:
                    logger.error(f"Failed to execute {sql_file} after {max_attempts} attempts")
        
        attempt += 1
    
    # 실행 결과 보고
    total_files = len(sorted_files)
    executed_count = len(executed_files)
    failed_count = total_files - executed_count
    
    logger.info(f"Deployment summary: {executed_count}/{total_files} files successfully executed")
    if failed_count > 0:
        logger.warning(f"{failed_count} files failed to execute")
        # 실패한 파일 목록
        failed_files = set(sorted_files) - executed_files
        for failed_file in failed_files:
            logger.warning(f"Failed to execute: {failed_file}")
    
    return executed_count, failed_count
def execute_sql_in_postgres(sql_file):
    """Execute a SQL file in PostgreSQL."""
    if not PGHOST or not PGUSER or not PGDATABASE:
        logger.error("PostgreSQL connection environment variables not set")
        return False

    try:
        # Build the psql command
        cmd = f"psql -h {PGHOST} -U {PGUSER} -p {PGPORT} -d {PGDATABASE} -f {sql_file}"
        
        # Execute the command
        logger.info(f"Executing SQL file in PostgreSQL: {sql_file}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Error executing SQL file in PostgreSQL: {result.stderr}")
            # Save the error to a log file
            error_log_file = os.path.join(ASCT_HOME, 'postgres_errors.log')
            with open(error_log_file, 'a') as f:
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] Error executing {sql_file}:\n")
                f.write(result.stderr)
                f.write("\n\n")
            return False
        
        logger.info(f"Successfully executed SQL file in PostgreSQL: {sql_file}")
        return True
    
    except Exception as e:
        logger.error(f"Exception executing SQL file in PostgreSQL: {e}")
        return False

def deploy_to_postgres():
    """Deploy all converted SQL files to PostgreSQL."""
    logger.info("Starting deployment with dependency handling")
    return deploy_to_postgres_with_dependency_handling()

def analyze_postgres_errors():
    """Analyze PostgreSQL error logs and generate a summary report."""
    error_log_file = os.path.join(ASCT_HOME, 'postgres_errors.log')
    if not os.path.exists(error_log_file):
        logger.info("No PostgreSQL errors found")
        return
    
    # 에러 유형별 카운트
    error_types = {
        "syntax_errors": 0,
        "object_exists": 0,
        "object_not_exists": 0,
        "permission_denied": 0,
        "connection_errors": 0,
        "other_errors": 0
    }
    
    # 에러 로그 분석
    with open(error_log_file, 'r') as f:
        content = f.read()
        
        error_types["syntax_errors"] = content.count("syntax error")
        error_types["object_exists"] = content.count("already exists")
        error_types["object_not_exists"] = content.count("does not exist")
        error_types["permission_denied"] = content.count("permission denied")
        error_types["connection_errors"] = content.count("could not connect")
        
        # 기타 에러는 전체 에러 수에서 위의 에러들을 뺀 값
        total_errors = content.count("[20")  # 타임스탬프로 에러 수 추정
        error_types["other_errors"] = total_errors - sum(error_types.values())
    
    # 보고서 생성
    report_file = os.path.join(ASCT_HOME, 'postgres_error_report.txt')
    with open(report_file, 'w') as f:
        f.write("PostgreSQL Error Analysis Report\n")
        f.write("==============================\n\n")
        f.write(f"Total errors: {total_errors}\n\n")
        f.write("Error breakdown:\n")
        for error_type, count in error_types.items():
            f.write(f"  - {error_type.replace('_', ' ').title()}: {count}\n")
        
        f.write("\nRecommended actions:\n")
        if error_types["syntax_errors"] > 0:
            f.write("  - Review and fix syntax errors in the SQL files\n")
        if error_types["object_exists"] > 0:
            f.write("  - Add IF NOT EXISTS clauses or DROP statements\n")
        if error_types["object_not_exists"] > 0:
            f.write("  - Check object dependencies and creation order\n")
        if error_types["permission_denied"] > 0:
            f.write("  - Grant necessary permissions to the PostgreSQL user\n")
        if error_types["connection_errors"] > 0:
            f.write("  - Verify PostgreSQL connection parameters\n")
    
    logger.info(f"Error analysis report generated: {report_file}")
    return report_file
def main():
    """Main function to run the ASCT helper."""
    logger.info("Starting ASCT helper")

    # Check environment variables
    if not ORACLE_ADM_USER or not ORACLE_ADM_PASSWORD or not ORACLE_SVC_USER:
        logger.error("Oracle connection environment variables not set")
        sys.exit(1)

    # Find CSV files
    csv_file = find_csv_files()
    if not csv_file:
        logger.error("No CSV file found")
        sys.exit(1)

    logger.info(f"Processing CSV file: {csv_file}")

    # Extract objects from CSV
    objects_by_type = extract_objects_from_csv(csv_file)
    if not objects_by_type:
        logger.error("No objects found for conversion")
        sys.exit(1)

    logger.info(f"Found {sum(len(objects) for objects in objects_by_type.values())} objects for conversion")

    # Save the list of incompatible objects
    save_incompatible_list(objects_by_type)

    # Read incompatible.lst file if it exists
    incompatible_objects = []
    incompatible_file = os.path.join(ASCT_HOME, 'Assessments', 'incompatible.lst')
    if os.path.exists(incompatible_file):
        with open(incompatible_file, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    obj_type = parts[0].upper()  # Normalize to uppercase for comparison
                    obj_name = parts[1]
                    incompatible_objects.append((obj_type, obj_name))

    # Group objects by their type
    objects_by_type = {}
    for obj_type, obj_name in incompatible_objects:
        if obj_type not in objects_by_type:
            objects_by_type[obj_type] = []
        objects_by_type[obj_type].append(obj_name)

    # Process objects in the specified order
    for object_type_key in OBJECT_TYPE_ORDER:
        # Check if we have objects of this type
        for obj_type in list(objects_by_type.keys()):
            # Check if this object type matches the current type in the order
            if obj_type.upper() == object_type_key.upper() or object_type_key.upper() in obj_type.upper():
                logger.info(f"Processing {len(objects_by_type[obj_type])} {obj_type} objects")

                for obj_name in objects_by_type[obj_type]:
                    logger.info(f"Extracting DDL for {obj_type} {obj_name}")

                    # Extract DDL from Oracle
                    oracle_ddl = extract_ddl_from_oracle(obj_type, obj_name)
                    if not oracle_ddl:
                        logger.warning(f"Failed to extract DDL for {obj_type} {obj_name}")
                        continue

                    # Convert to PostgreSQL
                    logger.info(f"Converting {obj_type} {obj_name} to PostgreSQL")
                    postgres_ddl = convert_to_postgres(oracle_ddl, obj_type, obj_name)
                    if not postgres_ddl:
                        logger.warning(f"Failed to convert {obj_type} {obj_name} to PostgreSQL")
                        continue

                    # Save results
                    save_conversion_results(obj_type, obj_name, postgres_ddl)

                # Remove processed object type to avoid processing it again
                del objects_by_type[obj_type]

    # Process any remaining objects that weren't in the order list
    for obj_type, obj_names in objects_by_type.items():
        logger.info(f"Processing {len(obj_names)} remaining {obj_type} objects")

        for obj_name in obj_names:
            logger.info(f"Extracting DDL for {obj_type} {obj_name}")

            # Extract DDL from Oracle
            oracle_ddl = extract_ddl_from_oracle(obj_type, obj_name)
            if not oracle_ddl:
                logger.warning(f"Failed to extract DDL for {obj_type} {obj_name}")
                continue

            # Convert to PostgreSQL
            logger.info(f"Converting {obj_type} {obj_name} to PostgreSQL")
            postgres_ddl = convert_to_postgres(oracle_ddl, obj_type, obj_name)
            if not postgres_ddl:
                logger.warning(f"Failed to convert {obj_type} {obj_name} to PostgreSQL")
                continue

            # Save results
            save_conversion_results(obj_type, obj_name, postgres_ddl)
    
    # Deploy to PostgreSQL if connection variables are set
    if PGHOST and PGUSER and PGDATABASE:
        logger.info("Deploying converted objects to PostgreSQL")
        success_count, failed_count = deploy_to_postgres()
        
        # Generate error analysis report if there were failures
        if failed_count > 0:
            logger.info("Generating error analysis report")
            report_file = analyze_postgres_errors()
            if report_file:
                logger.info(f"Error analysis report available at: {report_file}")
    else:
        logger.info("PostgreSQL connection variables not set, skipping deployment")

    logger.info("ASCT helper completed")

if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--deploy-only":
        # Only deploy to PostgreSQL without running the conversion
        logger.info("Running in deploy-only mode")
        if PGHOST and PGUSER and PGDATABASE:
            deploy_to_postgres()
        else:
            logger.error("PostgreSQL connection variables not set")
            sys.exit(1)
    else:
        # Run the full conversion and deployment process
        main()
