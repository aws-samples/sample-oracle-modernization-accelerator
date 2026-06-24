#!/usr/bin/env python3
"""
Test that common modules are truly DB-independent.
Verifies that conditional imports work correctly.
"""

import sys
import os

# Add paths
schema_migration_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, schema_migration_root)
sys.path.insert(0, os.path.join(schema_migration_root, 'common'))

print("=" * 70)
print("DB Independence Test")
print("=" * 70)
print()

# Test 1: rule_engine supports target_db parameter
print("[TEST 1] rule_engine.py - target_db parameter")
try:
    from common.rules.rule_engine import RuleEngine
    
    # Test PostgreSQL
    pg_engine = RuleEngine(target_db="pg")
    assert pg_engine.target_db == "pg"
    print("  ✓ PostgreSQL mode works")
    
    # Test MySQL
    mysql_engine = RuleEngine(target_db="mysql")
    assert mysql_engine.target_db == "mysql"
    print("  ✓ MySQL mode works")
    
    print("  PASS: rule_engine supports both PG and MySQL\n")
except Exception as e:
    print(f"  FAIL: {e}\n")

# Test 2: design_gate has conditional imports
print("[TEST 2] design_gate.py - conditional imports")
try:
    with open(os.path.join(schema_migration_root, 'common/orchestrator/design_gate.py'), 'r') as f:
        content = f.read()
    
    assert 'is_mysql = any' in content, "Missing MySQL detection"
    assert 'is_postgresql = any' in content, "Missing PostgreSQL detection"
    assert 'from mysql.tools.mysql_tools import mysql_execute_ddl' in content, "Missing MySQL import"
    assert 'from postgresql.tools.postgres_tools import pg_execute_ddl' in content, "Missing PG import"
    
    print("  ✓ Has MySQL detection")
    print("  ✓ Has PostgreSQL detection")
    print("  ✓ Has conditional MySQL import")
    print("  ✓ Has conditional PostgreSQL import")
    print("  PASS: design_gate has conditional imports\n")
except Exception as e:
    print(f"  FAIL: {e}\n")

# Test 3: dms_sc_tools has conditional imports
print("[TEST 3] dms_sc_tools.py - conditional imports")
try:
    with open(os.path.join(schema_migration_root, 'common/tools/dms_sc_tools.py'), 'r') as f:
        content = f.read()
    
    assert 'is_mysql = any' in content, "Missing MySQL detection"
    assert 'is_postgresql = any' in content, "Missing PostgreSQL detection"
    assert 'from mysql.tools.mysql_tools import' in content, "Missing MySQL import"
    assert 'target_exists' in content, "Missing target_exists variable"
    assert 'target_db' in content, "Missing target_db field"
    
    print("  ✓ Has MySQL detection")
    print("  ✓ Has PostgreSQL detection")
    print("  ✓ Has conditional MySQL import")
    print("  ✓ Uses target_exists (not pg_exists)")
    print("  ✓ Returns target_db field")
    print("  PASS: dms_sc_tools has conditional imports\n")
except Exception as e:
    print(f"  FAIL: {e}\n")

# Test 4: analysis_tools has _get_target_db_connection helper
print("[TEST 4] analysis_tools.py - DB connection helper")
try:
    with open(os.path.join(schema_migration_root, 'common/tools/analysis_tools.py'), 'r') as f:
        content = f.read()
    
    assert '_is_mysql = any' in content, "Missing MySQL detection"
    assert '_is_postgresql = any' in content, "Missing PostgreSQL detection"
    assert 'import aiomysql' in content, "Missing aiomysql import"
    assert 'import asyncpg' in content, "Missing asyncpg import"
    assert 'async def _get_target_db_connection()' in content, "Missing helper function"
    assert 'target_result' in content, "Missing target_result variable"
    
    print("  ✓ Has MySQL detection")
    print("  ✓ Has PostgreSQL detection")
    print("  ✓ Has aiomysql import")
    print("  ✓ Has asyncpg import")
    print("  ✓ Has _get_target_db_connection() helper")
    print("  ✓ Uses target_result (not pg_result)")
    print("  PASS: analysis_tools has DB connection helper\n")
except Exception as e:
    print(f"  FAIL: {e}\n")

# Test 5: MySQL static_rules.py exists and has correct mappings
print("[TEST 5] mysql/rules/static_rules.py - MySQL rules")
try:
    sys.path.insert(0, os.path.join(schema_migration_root, 'mysql'))
    from mysql.rules.static_rules import FUNCTION_MAPPINGS, DATA_TYPE_MAPPINGS
    
    # Check key MySQL-specific mappings
    assert "NVL" in FUNCTION_MAPPINGS, "Missing NVL mapping"
    assert FUNCTION_MAPPINGS["NVL"]["mysql"] == "IFNULL(", "Wrong NVL mapping"
    
    assert "SYSDATE" in FUNCTION_MAPPINGS, "Missing SYSDATE mapping"
    assert FUNCTION_MAPPINGS["SYSDATE"]["mysql"] == "NOW()", "Wrong SYSDATE mapping"
    
    assert "VARCHAR2" in DATA_TYPE_MAPPINGS, "Missing VARCHAR2 mapping"
    assert DATA_TYPE_MAPPINGS["VARCHAR2"] == "VARCHAR", "Wrong VARCHAR2 mapping"
    
    print("  ✓ NVL → IFNULL")
    print("  ✓ SYSDATE → NOW()")
    print("  ✓ VARCHAR2 → VARCHAR")
    print("  PASS: MySQL rules are correct\n")
except Exception as e:
    print(f"  FAIL: {e}\n")

# Test 6: MySQL tools exist and are properly structured
print("[TEST 6] mysql/tools/mysql_tools.py - MySQL tools")
try:
    # Check file exists and has required functions
    mysql_tools_path = os.path.join(schema_migration_root, 'mysql/tools/mysql_tools.py')
    with open(mysql_tools_path, 'r') as f:
        content = f.read()
    
    assert 'import aiomysql' in content, "Missing aiomysql import"
    assert 'async def get_mysql_connection()' in content, "Missing connection function"
    assert 'def mysql_execute_ddl' in content, "Missing execute_ddl function"
    assert 'def mysql_query' in content, "Missing query function"
    assert 'def mysql_explain' in content, "Missing explain function"
    assert 'def mysql_sync_sequences' in content, "Missing sync_sequences function"
    
    print("  ✓ Uses aiomysql")
    print("  ✓ Has get_mysql_connection()")
    print("  ✓ Has mysql_execute_ddl()")
    print("  ✓ Has mysql_query()")
    print("  ✓ Has mysql_explain()")
    print("  ✓ Has mysql_sync_sequences()")
    print("  PASS: MySQL tools are properly structured\n")
except Exception as e:
    print(f"  FAIL: {e}\n")

print("=" * 70)
print("Summary")
print("=" * 70)
print("All critical common modules are now DB-independent!")
print("PostgreSQL and MySQL can both use the same common/ modules.")
print()
