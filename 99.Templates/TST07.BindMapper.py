#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#############################################################################
# Script: DB07.BindMapper.py
# Description: This script replaces bind variables in SQL files with actual
#              sample values to create executable SQL statements.
#
# Functionality:
# - Processes SQL files from both Oracle and PostgreSQL extract directories
# - For each SQL file, looks for a corresponding JSON file in the 'sampler' directory
#   created by DB06.BindSampler.py
# - Replaces bind variables in the SQL with their sample values:
#   * :variable format (Oracle style)
#   * #{variable} format (MyBatis style)
# - Formats values appropriately based on their data type:
#   * Strings are quoted
#   * Dates are converted to TO_DATE() functions
#   * Numbers are inserted as-is
# - Saves the modified SQL files to the respective 'done' directories
# - If no bind variables are found or no sample values exist, copies the file unchanged
#
# Usage:
#   python3 DB07.BindMapper.py
#
# Output:
#   Modified SQL files in 'orcl_sql_done' and 'pg_sql_done' directories
#############################################################################

import os
import re
import json
import shutil

# Configuration
ORCL_SQL_DIR = 'orcl_sql_extract'
PG_SQL_DIR = 'pg_sql_extract'
ORCL_SQL_DONE_DIR = 'orcl_sql_done'
PG_SQL_DONE_DIR = 'pg_sql_done'
SAMPLER_DIR = 'sampler'

# Regular expressions for bind variables
BIND_PATTERN_COLON = r':([a-zA-Z0-9_]+)'
BIND_PATTERN_HASH = r'#{([a-zA-Z0-9_]+)}'

def ensure_directories():
    """Ensure output directories exist"""
    os.makedirs(ORCL_SQL_DONE_DIR, exist_ok=True)
    os.makedirs(PG_SQL_DONE_DIR, exist_ok=True)

def get_sql_files(directory):
    """Get list of SQL files in the directory"""
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist")
        return []
    
    return [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.sql')]

def get_bind_variables(sql_file):
    """Get bind variables from a SQL file"""
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Extract bind variables
        colon_vars = re.findall(BIND_PATTERN_COLON, sql_content)
        hash_vars = re.findall(BIND_PATTERN_HASH, sql_content)
        
        return colon_vars, hash_vars, sql_content
    except Exception as e:
        print(f"Error reading {sql_file}: {str(e)}")
        return [], [], ""

def load_bind_values(sql_file):
    """Load bind variable values from sampler directory"""
    base_name = os.path.basename(sql_file)
    bind_file = os.path.join(SAMPLER_DIR, base_name.replace('.sql', '.json'))
    
    if not os.path.exists(bind_file):
        print(f"Bind variable file not found: {bind_file}")
        return {}
    
    try:
        with open(bind_file, 'r', encoding='utf-8') as f:
            bind_data = json.load(f)
        
        # Convert to dictionary for easier lookup
        bind_values = {}
        for item in bind_data:
            bind_values[item['variable']] = {
                'value': item['sample_value'],
                'type': item['type']
            }
        
        return bind_values
    except Exception as e:
        print(f"Error loading bind values from {bind_file}: {str(e)}")
        return {}

def replace_bind_variables(sql_content, colon_vars, hash_vars, bind_values):
    """Replace bind variables in SQL content with their values"""
    modified_sql = sql_content
    
    # Replace :variable format
    for var in colon_vars:
        if var in bind_values:
            value = bind_values[var]['value']
            var_type = bind_values[var]['type']
            
            # Format value based on type
            if var_type == "DATE":
                formatted_value = f"TO_DATE('{value}', 'YYYYMMDDHH24MISS')"
            elif var_type == "VARCHAR2" or (isinstance(value, str) and not value.isdigit()):
                formatted_value = f"'{value}'"
            else:
                formatted_value = value
            
            modified_sql = modified_sql.replace(f":{var}", str(formatted_value))
    
    # Replace #{variable} format
    for var in hash_vars:
        if var in bind_values:
            value = bind_values[var]['value']
            var_type = bind_values[var]['type']
            
            # Format value based on type
            if var_type == "DATE":
                formatted_value = f"TO_DATE('{value}', 'YYYYMMDDHH24MISS')"
            elif var_type == "VARCHAR2" or (isinstance(value, str) and not value.isdigit()):
                formatted_value = f"'{value}'"
            else:
                formatted_value = value
            
            modified_sql = modified_sql.replace(f"#{{{var}}}", str(formatted_value))
    
    return modified_sql

def process_sql_files(source_dir, target_dir):
    """Process SQL files from source directory and save to target directory"""
    sql_files = get_sql_files(source_dir)
    processed_count = 0
    skipped_count = 0
    
    for sql_file in sql_files:
        colon_vars, hash_vars, sql_content = get_bind_variables(sql_file)
        
        # Skip if no bind variables found
        if not colon_vars and not hash_vars:
            shutil.copy(sql_file, os.path.join(target_dir, os.path.basename(sql_file)))
            skipped_count += 1
            continue
        
        # Load bind values
        bind_values = load_bind_values(sql_file)
        
        if not bind_values:
            # If no bind values found, just copy the file
            shutil.copy(sql_file, os.path.join(target_dir, os.path.basename(sql_file)))
            skipped_count += 1
            continue
        
        # Replace bind variables
        modified_sql = replace_bind_variables(sql_content, colon_vars, hash_vars, bind_values)
        
        # Save modified SQL
        output_file = os.path.join(target_dir, os.path.basename(sql_file))
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(modified_sql)
        
        processed_count += 1
    
    return processed_count, skipped_count

def main():
    ensure_directories()
    
    print("Processing Oracle SQL files...")
    orcl_processed, orcl_skipped = process_sql_files(ORCL_SQL_DIR, ORCL_SQL_DONE_DIR)
    
    print("Processing PostgreSQL SQL files...")
    pg_processed, pg_skipped = process_sql_files(PG_SQL_DIR, PG_SQL_DONE_DIR)
    
    print(f"Oracle SQL files: {orcl_processed} processed, {orcl_skipped} copied without changes")
    print(f"PostgreSQL SQL files: {pg_processed} processed, {pg_skipped} copied without changes")
    print("Done!")

if __name__ == "__main__":
    main()
