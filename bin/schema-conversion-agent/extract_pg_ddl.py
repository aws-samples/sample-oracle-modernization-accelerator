#!/usr/bin/env python3.11
"""
Extract complete DDL from PostgreSQL demo schema (with parallel processing)
"""
import asyncio
import boto3
import json
import psycopg2
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

OUTPUT_DIR = "/workshop/pg-ddl"

def get_db_connection():
    """Get PostgreSQL connection"""
    sm = boto3.client('secretsmanager', region_name='us-east-1')
    secret = sm.get_secret_value(SecretId='MMA-secret-aurora-admin')
    creds = json.loads(secret['SecretString'])
    
    return psycopg2.connect(
        host=creds['host'],
        port=creds['port'],
        database=creds['dbname'],
        user=creds['username'],
        password=creds['password']
    )

def extract_tables():
    """Extract table DDLs"""
    conn = get_db_connection()
    cur = conn.cursor()
    ddl_parts = []
    
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'demo' 
        ORDER BY table_name
    """)
    tables = [row[0] for row in cur.fetchall()]
    
    if tables:
        ddl_parts.append("-- ============================================")
        ddl_parts.append("-- TABLES")
        ddl_parts.append("-- ============================================")
        ddl_parts.append("")
        
        for table in tables:
            cur.execute(f"""
                SELECT 
                    'CREATE TABLE demo.' || quote_ident(c.table_name) || ' (' ||
                    string_agg(
                        quote_ident(c.column_name) || ' ' || 
                        c.data_type ||
                        CASE WHEN c.character_maximum_length IS NOT NULL 
                             THEN '(' || c.character_maximum_length || ')' 
                             ELSE '' END ||
                        CASE WHEN c.is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END,
                        ', ' ORDER BY c.ordinal_position
                    ) || ');'
                FROM information_schema.columns c
                WHERE c.table_schema = 'demo' AND c.table_name = '{table}'
                GROUP BY c.table_name
            """)
            result = cur.fetchone()
            if result:
                ddl_parts.append(f"-- Table: {table}")
                ddl_parts.append(result[0])
                ddl_parts.append("")
    
    cur.close()
    conn.close()
    return ddl_parts

def extract_indexes():
    """Extract index DDLs"""
    conn = get_db_connection()
    cur = conn.cursor()
    ddl_parts = []
    
    cur.execute("""
        SELECT 
            schemaname, tablename, indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'demo'
        ORDER BY tablename, indexname
    """)
    indexes = cur.fetchall()
    
    if indexes:
        ddl_parts.append("-- ============================================")
        ddl_parts.append("-- INDEXES")
        ddl_parts.append("-- ============================================")
        ddl_parts.append("")
        
        for idx in indexes:
            ddl_parts.append(f"-- Index: {idx[2]} on {idx[1]}")
            ddl_parts.append(f"{idx[3]};")
            ddl_parts.append("")
    
    cur.close()
    conn.close()
    return ddl_parts

def extract_functions():
    """Extract function DDLs"""
    conn = get_db_connection()
    cur = conn.cursor()
    ddl_parts = []
    
    cur.execute("""
        SELECT 
            p.proname,
            pg_get_functiondef(p.oid)
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'demo' AND p.prokind = 'f'
        ORDER BY p.proname
    """)
    functions = cur.fetchall()
    
    if functions:
        ddl_parts.append("-- ============================================")
        ddl_parts.append("-- FUNCTIONS")
        ddl_parts.append("-- ============================================")
        ddl_parts.append("")
        
        for func in functions:
            ddl_parts.append(f"-- Function: {func[0]}")
            ddl_parts.append(func[1])
            ddl_parts.append("")
    
    cur.close()
    conn.close()
    return ddl_parts

def extract_procedures():
    """Extract procedure DDLs"""
    conn = get_db_connection()
    cur = conn.cursor()
    ddl_parts = []
    
    cur.execute("""
        SELECT 
            p.proname,
            pg_get_functiondef(p.oid)
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'demo' AND p.prokind = 'p'
        ORDER BY p.proname
    """)
    procedures = cur.fetchall()
    
    if procedures:
        ddl_parts.append("-- ============================================")
        ddl_parts.append("-- PROCEDURES")
        ddl_parts.append("-- ============================================")
        ddl_parts.append("")
        
        for proc in procedures:
            ddl_parts.append(f"-- Procedure: {proc[0]}")
            ddl_parts.append(proc[1])
            ddl_parts.append("")
    
    cur.close()
    conn.close()
    return ddl_parts

def extract_constraints():
    """Extract constraint DDLs"""
    conn = get_db_connection()
    cur = conn.cursor()
    ddl_parts = []
    
    cur.execute("""
        SELECT 
            tc.table_name,
            tc.constraint_name,
            tc.constraint_type,
            pg_get_constraintdef(c.oid)
        FROM information_schema.table_constraints tc
        JOIN pg_constraint c ON c.conname = tc.constraint_name
        WHERE tc.table_schema = 'demo'
        ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name
    """)
    constraints = cur.fetchall()
    
    if constraints:
        ddl_parts.append("-- ============================================")
        ddl_parts.append("-- CONSTRAINTS")
        ddl_parts.append("-- ============================================")
        ddl_parts.append("")
        
        for cons in constraints:
            ddl_parts.append(f"-- {cons[2]}: {cons[1]} on {cons[0]}")
            ddl_parts.append(f"ALTER TABLE demo.{cons[0]} ADD CONSTRAINT {cons[1]} {cons[3]};")
            ddl_parts.append("")
    
    cur.close()
    conn.close()
    return ddl_parts

async def extract_schema_ddl():
    """Extract complete DDL from demo schema in parallel"""
    loop = asyncio.get_event_loop()
    
    # Run all extractions in parallel using thread pool
    with ThreadPoolExecutor(max_workers=5) as executor:
        tasks = [
            loop.run_in_executor(executor, extract_tables),
            loop.run_in_executor(executor, extract_indexes),
            loop.run_in_executor(executor, extract_functions),
            loop.run_in_executor(executor, extract_procedures),
            loop.run_in_executor(executor, extract_constraints)
        ]
        
        results = await asyncio.gather(*tasks)
    
    # Combine results
    ddl_parts = [
        "-- PostgreSQL DDL Export",
        "-- Schema: demo",
        f"-- Generated: {Path(__file__).name}",
        "",
        "-- Create schema",
        "CREATE SCHEMA IF NOT EXISTS demo;",
        ""
    ]
    
    for result in results:
        ddl_parts.extend(result)
    
    return "\n".join(ddl_parts)

async def main():
    """Main function"""
    print("="*60)
    print("PostgreSQL DDL Extraction (Parallel)")
    print("="*60)
    
    print(f"\n📥 Extracting DDL from demo schema (5 parallel tasks)...")
    ddl = await extract_schema_ddl()
    
    # Save to file
    output_file = f"{OUTPUT_DIR}/demo_schema_complete.sql"
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(output_file).write_text(ddl)
    
    print(f"✅ DDL extracted: {output_file}")
    print(f"   Size: {len(ddl)} bytes")
    
    # Count objects
    lines = ddl.split('\n')
    tables = len([l for l in lines if l.startswith('CREATE TABLE')])
    indexes = len([l for l in lines if l.startswith('CREATE INDEX') or l.startswith('CREATE UNIQUE INDEX')])
    functions = len([l for l in lines if '-- Function:' in l])
    procedures = len([l for l in lines if '-- Procedure:' in l])
    
    print(f"\n📊 Summary:")
    print(f"   Tables: {tables}")
    print(f"   Indexes: {indexes}")
    print(f"   Functions: {functions}")
    print(f"   Procedures: {procedures}")

if __name__ == "__main__":
    asyncio.run(main())
