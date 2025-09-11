#!/usr/bin/env python3

import sys
import subprocess
import os
import csv

def analyze_complex_objects(csv_file):
    """Analyze CSV file and find complex objects"""
    try:
        complex_objects = {}
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                complexity = row.get('Estimated complexity', '').strip().lower()
                category = row.get('Category', '').strip().lower()
                
                # Target only Medium and Complex complexity for procedures and functions
                if category in ['procedure', 'function'] and complexity in ['medium', 'complex']:
                    source_object = row.get('Occurrence', '').strip()
                    if source_object:
                        complex_objects[source_object] = complex_objects.get(source_object, 0) + 1
        
        if complex_objects:
            print("복잡도가 Medium 또는 Complex인 오브젝트들:")
            print("-" * 50)
            sorted_objects = sorted(complex_objects.items(), key=lambda x: x[1], reverse=True)
            for i, (obj, count) in enumerate(sorted_objects, 1):
                print(f"{i}. {obj} (반복 횟수: {count})")
            
            # Save objects for later use
            with open('/tmp/complex_objects.txt', 'w') as f:
                for obj, _ in sorted_objects:
                    f.write(f"{obj}\n")
            
            return True
        else:
            print("복잡도가 Medium 또는 Complex인 오브젝트가 없습니다.")
            return False
            
    except Exception as e:
        print(f"Error analyzing CSV: {e}")
        return False

def extract_ddl(object_name, output_file):
    """Extract DDL from Oracle"""
    try:
        # Set Oracle environment
        env = os.environ.copy()
        env['ORACLE_HOME'] = os.environ.get('ORACLE_HOME', '/home/ec2-user/instantclient_19_26')
        env['LD_LIBRARY_PATH'] = f"{env['ORACLE_HOME']}:{env.get('LD_LIBRARY_PATH', '')}"
        env['PATH'] = f"{env['ORACLE_HOME']}:{env['PATH']}"
        env['NLS_LANG'] = os.environ.get('NLS_LANG', 'KOREAN_KOREA.AL32UTF8')
        env['NLS_DATE_FORMAT'] = os.environ.get('NLS_DATE_FORMAT', 'YYYY-MM-DD')
        
        # Get Oracle connection info from environment variables
        oracle_host = os.environ.get('ORACLE_HOST', '10.255.255.155')
        oracle_port = os.environ.get('ORACLE_PORT', '1521')
        oracle_sid = os.environ.get('ORACLE_SID', 'XEPDB1')
        oracle_user = os.environ.get('ORACLE_SVC_USER', 'oma')
        oracle_password = os.environ.get('ORACLE_SVC_PASSWORD', 'welcome1')
        
        connection_string = f"{oracle_user}/{oracle_password}@{oracle_host}:{oracle_port}/{oracle_sid}"
        
        print(f"Extracting DDL for procedure: {object_name}")
        
        # Create SQL commands
        sql_commands = f"""SET PAGESIZE 0
SET LINESIZE 4000
SET LONG 4000000
SET HEADING OFF
SET FEEDBACK OFF
SET ECHO OFF
SET VERIFY OFF

SELECT TEXT FROM USER_SOURCE WHERE NAME = UPPER('{object_name}') AND TYPE = 'PROCEDURE' ORDER BY LINE;

EXIT;
"""
        
        # Execute sqlplus
        process = subprocess.Popen(
            ['sqlplus', '-S', connection_string],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True
        )
        
        stdout, stderr = process.communicate(input=sql_commands)
        
        if process.returncode == 0:
            if stdout.strip():
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(stdout)
                
                print(f"✓ DDL extracted successfully to: {output_file}")
                return True
            else:
                print(f"✗ No procedure found with name: {object_name}")
                return False
        else:
            print(f"✗ SQLPlus error (return code: {process.returncode})")
            if stderr:
                print(f"Error output: {stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def deploy_to_postgresql(sql_file):
    """Deploy DDL to PostgreSQL database"""
    try:
        # Get PostgreSQL connection info from environment - use admin credentials for deployment
        pghost = os.environ.get('PGHOST')
        pgdatabase = os.environ.get('PGDATABASE') 
        # Use admin credentials for deployment
        pguser = os.environ.get('PG_ADMIN_USER', os.environ.get('PGUSER', 'postgres'))
        pgpassword = os.environ.get('PG_ADMIN_PASSWORD', os.environ.get('PGPASSWORD'))
        
        if not all([pghost, pgdatabase, pguser]):
            print("✗ PostgreSQL environment variables not set (PGHOST, PGDATABASE, PGUSER)")
            return False
        
        print(f"Deploying to PostgreSQL: {pguser}@{pghost}/{pgdatabase}")
        
        # Read and clean SQL file
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Clean the SQL content by removing all formatting artifacts
        import re
        
        # Split into lines and clean each line
        lines = sql_content.split('\n')
        cleaned_lines = []
        prev_line = ""
        
        for line in lines:
            # Remove various line number formats and prefixes
            cleaned_line = re.sub(r'^[\s]*[\+\-]?\s*\d+[,\s]*\d*\s*:\s*', '', line)
            # Remove standalone - or + at beginning of lines
            cleaned_line = re.sub(r'^[\s]*[\+\-][\s]*$', '', cleaned_line)
            # Remove lines that are just formatting artifacts
            cleaned_line = re.sub(r'^[\s]*[\+\-][\s]*([^a-zA-Z\-])', r'\1', cleaned_line)
            
            # Skip duplicate comment content
            if not cleaned_line.strip().startswith('--') and prev_line.strip().startswith('--'):
                comment_content = prev_line.strip().replace('--', '').strip()
                if comment_content and comment_content in cleaned_line.strip():
                    continue
            
            # Skip lines that look like orphaned comment content
            if re.match(r'^[A-Z][a-z]+ case:', cleaned_line.strip()):
                continue
                
            # Keep only non-empty lines that contain actual content
            if cleaned_line.strip() and not re.match(r'^[\s]*[\+\-\s]*$', cleaned_line):
                cleaned_lines.append(cleaned_line.strip())
                prev_line = cleaned_line
        
        cleaned_sql = '\n'.join(cleaned_lines)
        
        # Write cleaned SQL to temporary file with schema setup
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
            # Set search path using environment variable
            pg_schema = os.environ.get('PG_SCHEMA', os.environ.get('PGDATABASE', 'public'))
            temp_file.write(f"SET search_path TO {pg_schema}, public;\n\n")
            
            # Extract procedure/function name from SQL for cleanup
            import re
            proc_match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?(?:PROCEDURE|FUNCTION)\s+(?:(\w+)\.)?(\w+)\s*\(', cleaned_sql, re.IGNORECASE)
            if proc_match:
                schema_name = proc_match.group(1) or pg_schema
                object_name = proc_match.group(2)
                
                # Drop all existing procedures/functions with the same name
                temp_file.write(f"-- Cleanup existing procedures/functions with same name\n")
                temp_file.write(f"DO $$\n")
                temp_file.write(f"DECLARE\n")
                temp_file.write(f"    r RECORD;\n")
                temp_file.write(f"BEGIN\n")
                temp_file.write(f"    FOR r IN\n")
                temp_file.write(f"        SELECT rt.routine_name, rt.specific_name, rt.routine_type,\n")
                temp_file.write(f"               string_agg(p.data_type, ', ' ORDER BY p.ordinal_position) as param_types\n")
                temp_file.write(f"        FROM information_schema.routines rt\n")
                temp_file.write(f"        LEFT JOIN information_schema.parameters p ON rt.specific_name = p.specific_name\n")
                temp_file.write(f"        WHERE rt.routine_schema = '{schema_name}' AND rt.routine_name = '{object_name}'\n")
                temp_file.write(f"        GROUP BY rt.routine_name, rt.specific_name, rt.routine_type\n")
                temp_file.write(f"    LOOP\n")
                temp_file.write(f"        EXECUTE 'DROP ' || r.routine_type || ' IF EXISTS {schema_name}.' || r.routine_name || '(' || COALESCE(r.param_types, '') || ') CASCADE';\n")
                temp_file.write(f"        RAISE NOTICE 'Dropped existing %: %.%', r.routine_type, '{schema_name}', r.routine_name;\n")
                temp_file.write(f"    END LOOP;\n")
                temp_file.write(f"END\n")
                temp_file.write(f"$$;\n\n")
            
            temp_file.write(cleaned_sql)
            temp_sql_file = temp_file.name
        
        # Execute psql command with cleaned file
        env = os.environ.copy()
        process = subprocess.Popen(
            ['psql', '-f', temp_sql_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True
        )
        
        stdout, stderr = process.communicate()
        
        # Clean up temporary file
        os.unlink(temp_sql_file)
        
        print(f"psql return code: {process.returncode}")
        # Filter and display meaningful stdout messages
        if stdout.strip():
            stdout_lines = stdout.strip().split('\n')
            meaningful_stdout = [line for line in stdout_lines if line.strip() and line.strip() not in ['SET', 'DO']]
            if meaningful_stdout:
                print("📋 실행 결과:")
                for line in meaningful_stdout:
                    print(f"  {line}")
        
        if stderr.strip():
            # Parse stderr for meaningful messages
            stderr_lines = stderr.strip().split('\n')
            error_lines = [line for line in stderr_lines if 'ERROR:' in line or 'FATAL:' in line]
            warning_lines = [line for line in stderr_lines if 'WARNING:' in line or 'NOTICE:' in line]
            
            if error_lines:
                print("❌ SQL 실행 중 오류 발생:")
                for line in error_lines:
                    print(f"  {line}")
            elif warning_lines:
                print("⚠️  SQL 실행 중 경고:")
                for line in warning_lines:
                    print(f"  {line}")
            else:
                # Show only meaningful parts of stderr, not technical psql output
                meaningful_lines = [line for line in stderr_lines 
                                  if line.strip() and 
                                     not line.strip().startswith('psql:') and 
                                     'psql:' not in line and
                                     '/tmp/' not in line]
                if meaningful_lines:
                    print("ℹ️  추가 정보:")
                    for line in meaningful_lines[:3]:  # Show max 3 lines
                        print(f"  {line}")
        
        # Check for errors in stderr
        has_errors = False
        if stderr:
            error_lines = [line for line in stderr.split('\n') if 'ERROR:' in line or 'FATAL:' in line]
            if error_lines:
                has_errors = True
        
        if process.returncode == 0 and not has_errors:
            print("✓ DDL applied successfully to PostgreSQL")
            return True
        else:
            print("✗ Failed to apply DDL to PostgreSQL")
            if has_errors:
                print("Reason: SQL execution errors detected")
            else:
                print(f"Reason: Non-zero return code ({process.returncode})")
            return False
            
    except Exception as e:
        print(f"✗ Error deploying to PostgreSQL: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python db_operations.py <command> <file>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "analyze":
        if len(sys.argv) != 3:
            print("Usage: python3 db_operations.py analyze <csv_file>")
            sys.exit(1)
        file_path = sys.argv[2]
        success = analyze_complex_objects(file_path)
    elif command == "extract":
        if len(sys.argv) != 4:
            print("Usage: python3 db_operations.py extract <object_name> <output_file>")
            sys.exit(1)
        object_name = sys.argv[2]
        output_file = sys.argv[3]
        success = extract_ddl(object_name, output_file)
    elif command == "deploy":
        if len(sys.argv) != 3:
            print("Usage: python3 db_operations.py deploy <sql_file>")
            sys.exit(1)
        file_path = sys.argv[2]
        success = deploy_to_postgresql(file_path)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    # Exit with proper code
    sys.exit(0 if success else 1)

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 db_operations.py analyze <csv_file>")
        print("  python3 db_operations.py extract <object_name> <output_file>")
        print("  python3 db_operations.py deploy <sql_file>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "analyze":
        if len(sys.argv) != 3:
            print("Usage: python3 db_operations.py analyze <csv_file>")
            sys.exit(1)
        
        csv_file = sys.argv[2]
        success = analyze_complex_objects(csv_file)
        sys.exit(0 if success else 1)
        
    elif command == "extract":
        if len(sys.argv) != 4:
            print("Usage: python3 db_operations.py extract <object_name> <output_file>")
            sys.exit(1)
        
        object_name = sys.argv[2]
        output_file = sys.argv[3]
        success = extract_ddl(object_name, output_file)
        sys.exit(0 if success else 1)
        
    elif command == "deploy":
        if len(sys.argv) != 3:
            print("Usage: python3 db_operations.py deploy <sql_file>")
            sys.exit(1)
        
        sql_file = sys.argv[2]
        success = deploy_to_postgresql(sql_file)
        sys.exit(0 if success else 1)
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
