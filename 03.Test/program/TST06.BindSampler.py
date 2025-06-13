#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#############################################################################
# Script: DB06.BindSampler.py
# Description: This script analyzes SQL files to identify bind variables and
#              assigns appropriate sample values based on variable names and
#              a dictionary of database column values.
#
# Functionality:
# - Scans SQL files in the 'orcl_sql_extract' directory
# - Extracts bind variables (both :variable and #{variable} formats)
# - Determines the likely data type of each variable based on:
#   * Matching against column names in the dictionary
#   * Analyzing variable naming patterns (e.g., date_*, *_id, is_*)
# - Assigns appropriate sample values from the dictionary:
#   * First tries to find a direct match for the variable name
#   * Then looks for similar column names
#   * Falls back to any column of the same data type
#   * Uses default values if no match is found
# - Saves the results as JSON files in the 'sampler' directory
#
# The output JSON files are used by DB07.BindMapper.py to replace bind
# variables with actual values in SQL statements.
#
# Usage:
#   python3 DB06.BindSampler.py
#
# Output:
#   JSON files in the 'sampler' directory, one per SQL file
#############################################################################

import os
import re
import json
import random
from datetime import datetime, timedelta

# Configuration
SQL_DIR = 'orcl_sql_extract'
DICTIONARY_FILE = 'all_dictionary.json'

# Regular expressions for bind variables
BIND_PATTERN = r'[:#{]([a-zA-Z0-9_]+)[}]?'  # Match both :var and #{var}
# Common type patterns
DATE_PATTERN = r'(?i)(date|dt|day|time)'
NUMBER_PATTERN = r'(?i)(num|cnt|count|id|no|seq|amt|amount|rate|pct|percent|age|year|month|day|hour|min|sec)'
BOOLEAN_PATTERN = r'(?i)(yn|flag|is_|has_|use_|active|enabled|status)'

def load_dictionary():
    """Load the dictionary from JSON file"""
    with open(DICTIONARY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_sql_files():
    """Get list of SQL files in the directory"""
    if not os.path.exists(SQL_DIR):
        print(f"Directory {SQL_DIR} does not exist")
        return []
    
    return [os.path.join(SQL_DIR, f) for f in os.listdir(SQL_DIR) if f.endswith('.sql')]

def extract_bind_variables(sql_content):
    """Extract bind variables from SQL content"""
    return re.findall(BIND_PATTERN, sql_content)

def find_column_in_dictionary(var_name, dictionary):
    """Find a column in the dictionary that matches the variable name"""
    # Convert variable name to lowercase for case-insensitive comparison
    var_name_lower = var_name.lower()
    
    # First, try to find an exact match
    for table_name, table_data in dictionary.items():
        if "columns" not in table_data:
            continue
            
        for col_name, col_data in table_data["columns"].items():
            if col_name.lower() == var_name_lower:
                return col_data.get("type", "").upper()
    
    # If no exact match, try to find a partial match
    for table_name, table_data in dictionary.items():
        if "columns" not in table_data:
            continue
            
        for col_name, col_data in table_data["columns"].items():
            # Check if column name contains the variable name or vice versa
            if col_name.lower() in var_name_lower or var_name_lower in col_name.lower():
                return col_data.get("type", "").upper()
    
    # Special case for variables that might map to database columns
    # Map camelCase or snake_case variable names to database column names
    # For example, pnrNo might map to PYPB_PNR_NO
    for table_name, table_data in dictionary.items():
        if "columns" not in table_data:
            continue
            
        for col_name, col_data in table_data["columns"].items():
            col_parts = col_name.lower().split('_')
            var_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', var_name)
            var_parts = [p.lower() for p in var_parts]
            
            # Check if the variable parts are contained in the column parts
            matches = 0
            for var_part in var_parts:
                if any(var_part in col_part for col_part in col_parts):
                    matches += 1
            
            # If more than half of the parts match, consider it a match
            if matches >= len(var_parts) / 2:
                return col_data.get("type", "").upper()
    
    return None

def guess_variable_type(var_name, dictionary):
    """Guess the type of variable based on dictionary first, then name patterns"""
    # First try to find the type in the dictionary
    dict_type = find_column_in_dictionary(var_name, dictionary)
    if dict_type:
        return dict_type
    
    # If not found in dictionary, use naming patterns
    if re.search(DATE_PATTERN, var_name):
        return "DATE"
    elif re.search(NUMBER_PATTERN, var_name):
        return "NUMBER"
    elif re.search(BOOLEAN_PATTERN, var_name):
        return "BOOLEAN"
    else:
        return "VARCHAR2"

def get_sample_value(var_type, var_name, dictionary):
    """Get a sample value for the variable type from dictionary"""
    # Default values if no match found
    default_values = {
        "DATE": datetime.now().strftime("%Y%m%d%H%M%S"),
        "NUMBER": "1",
        "BOOLEAN": "Y",
        "VARCHAR2": "SAMPLE_VALUE"
    }
    
    # First try to find a direct match for the variable name in the dictionary
    matched_column = None
    matched_column_data = None
    
    # Try to find a matching column in the dictionary based on variable name
    for table_name, table_data in dictionary.items():
        if "columns" not in table_data:
            continue
            
        for col_name, col_data in table_data["columns"].items():
            # Check for exact match or if column name contains the variable name or vice versa
            if col_name.lower() == var_name.lower() or col_name.lower() in var_name.lower() or var_name.lower() in col_name.lower():
                # Check if the column has sample values
                if "sample_values" in col_data and col_data["sample_values"]:
                    matched_column = col_name
                    matched_column_data = col_data
                    break
        
        if matched_column:
            break
    
    # If no direct match found, try to find a match using camelCase/snake_case conversion
    if not matched_column:
        for table_name, table_data in dictionary.items():
            if "columns" not in table_data:
                continue
                
            for col_name, col_data in table_data["columns"].items():
                col_parts = col_name.lower().split('_')
                var_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', var_name)
                var_parts = [p.lower() for p in var_parts]
                
                # Check if the variable parts are contained in the column parts
                matches = 0
                for var_part in var_parts:
                    if any(var_part in col_part for col_part in col_parts):
                        matches += 1
                
                # If more than half of the parts match, consider it a match
                if matches >= len(var_parts) / 2:
                    if "sample_values" in col_data and col_data["sample_values"]:
                        matched_column = col_name
                        matched_column_data = col_data
                        break
            
            if matched_column:
                break
    
    # If we found a matching column, use its sample value
    if matched_column and matched_column_data:
        # Get a random sample value
        sample_value = random.choice(matched_column_data["sample_values"])
        
        # Check if the column has a length constraint
        if "length" in matched_column_data:
            max_length = int(matched_column_data["length"])
            # If the sample value exceeds the length, truncate it or get another value
            if len(str(sample_value)) > max_length:
                # Try to find another sample value that fits the length constraint
                valid_samples = [s for s in matched_column_data["sample_values"] if len(str(s)) <= max_length]
                if valid_samples:
                    sample_value = random.choice(valid_samples)
                else:
                    # If no valid sample found, truncate the value
                    sample_value = str(sample_value)[:max_length]
        
        return sample_value
    
    # If no match found for the specific variable, try to find any column of the same type
    # that has a length constraint if applicable
    for table_name, table_data in dictionary.items():
        if "columns" not in table_data:
            continue
            
        for col_name, col_data in table_data["columns"].items():
            if col_data.get("type", "").upper() == var_type:
                if "sample_values" in col_data and col_data["sample_values"]:
                    sample_value = random.choice(col_data["sample_values"])
                    
                    # Check if the column has a length constraint
                    if "length" in col_data:
                        max_length = int(col_data["length"])
                        # If the sample value exceeds the length, truncate it or get another value
                        if len(str(sample_value)) > max_length:
                            # Try to find another sample value that fits the length constraint
                            valid_samples = [s for s in col_data["sample_values"] if len(str(s)) <= max_length]
                            if valid_samples:
                                sample_value = random.choice(valid_samples)
                            else:
                                # If no valid sample found, truncate the value
                                sample_value = str(sample_value)[:max_length]
                    
                    return sample_value
    
    # If still no match, return default value
    return default_values[var_type]

def main():
    dictionary = load_dictionary()
    sql_files = get_sql_files()
    
    results = {}
    
    for sql_file in sql_files:
        try:
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Extract bind variables
            bind_vars = extract_bind_variables(sql_content)
            
            # Remove duplicates while preserving order
            unique_bind_vars = []
            for var in bind_vars:
                if var not in unique_bind_vars:
                    unique_bind_vars.append(var)
            
            if unique_bind_vars:
                file_name = os.path.basename(sql_file)
                results[file_name] = []
                
                for var in unique_bind_vars:
                    var_type = guess_variable_type(var, dictionary)
                    sample_value = get_sample_value(var_type, var, dictionary)
                    
                    results[file_name].append({
                        "variable": var,
                        "type": var_type,
                        "sample_value": sample_value
                    })
    
        except Exception as e:
            print(f"Error processing {sql_file}: {str(e)}")
    
    # Save results to sampler directory
    os.makedirs('sampler', exist_ok=True)
    
    for file_name, bind_vars in results.items():
        output_file = os.path.join('sampler', file_name.replace('.sql', '.json'))
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(bind_vars, f, indent=2, ensure_ascii=False)
    
    print(f"Processed {len(sql_files)} SQL files")
    print(f"Generated {len(results)} bind variable files in 'sampler' directory")

if __name__ == "__main__":
    main()
