#!/usr/bin/env python3
"""Test if all imports work after restructuring."""

import sys
import os

# Add paths
schema_migration_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, schema_migration_root)
sys.path.insert(0, os.path.join(schema_migration_root, 'common'))
sys.path.insert(0, os.path.join(schema_migration_root, 'postgresql'))

print("=" * 60)
print("Testing PostgreSQL Module Imports")
print("=" * 60)

# Test common modules
print("\n1. Testing common.orchestrator...")
try:
    from common.orchestrator import state, context_budget, hooks
    print("   ✓ common.orchestrator imports OK")
except Exception as e:
    print(f"   ✗ common.orchestrator import failed: {e}")

print("\n2. Testing common.tools...")
try:
    from common.tools import oracle_tools, dms_sc_tools, analysis_tools
    print("   ✓ common.tools imports OK")
except Exception as e:
    print(f"   ✗ common.tools import failed: {e}")

print("\n3. Testing common.rules...")
try:
    from common.rules import rule_engine, patterns
    print("   ✓ common.rules imports OK")
except Exception as e:
    print(f"   ✗ common.rules import failed: {e}")

# Test postgresql modules
print("\n4. Testing postgresql.tools...")
try:
    from postgresql.tools import postgres_tools, data_transfer_tools
    print("   ✓ postgresql.tools imports OK")
except Exception as e:
    print(f"   ✗ postgresql.tools import failed: {e}")

print("\n5. Testing postgresql.rules...")
try:
    from postgresql.rules import static_rules, oracle_compat_library
    print("   ✓ postgresql.rules imports OK")
except Exception as e:
    print(f"   ✗ postgresql.rules import failed: {e}")

print("\n6. Testing postgresql.agents...")
try:
    from postgresql.agents import factory
    print("   ✓ postgresql.agents.factory imports OK")
except Exception as e:
    print(f"   ✗ postgresql.agents import failed: {e}")

# Test specific agent imports (이건 모델 초기화가 필요할 수 있으므로 skip)
print("\n7. Testing postgresql.agents modules (import only)...")
try:
    from postgresql.agents import discovery, schema_architect, code_migrator
    print("   ✓ postgresql.agents.discovery/schema_architect/code_migrator imports OK")
except Exception as e:
    print(f"   ✗ postgresql.agents modules import failed: {e}")

print("\n" + "=" * 60)
print("Import Test Complete")
print("=" * 60)
