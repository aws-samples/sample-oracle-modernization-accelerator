#!/bin/bash

# AppDiscovery Oracle Pattern Analysis Utilities
# Oracle 특화 패턴 분석 및 복잡도 계산 함수들

# Oracle 패턴 분석 함수
analyze_oracle_patterns() {
    local mapper_file="$1"
    local analysis_result="$2"
    
    echo "=== Oracle Pattern Analysis: $(basename "$mapper_file") ===" >> "$analysis_result"
    
    # Critical Features (15점씩) - 아키텍처 변경 필요
    echo "## Critical Oracle Features ##" >> "$analysis_result"
    
    # Database Links
    dblink_count=$(grep -i -E "@[a-zA-Z_][a-zA-Z0-9_]*" "$mapper_file" | wc -l)
    [ $dblink_count -gt 0 ] && echo "Database Links: $dblink_count (Critical - 15점)" >> "$analysis_result"
    
    # Encryption Functions
    crypto_count=$(grep -i -E "DBMS_CRYPTO|CRYPTO\." "$mapper_file" | wc -l)
    obfuscation_count=$(grep -i -E "DBMS_OBFUSCATION|OBFUSCATION_TOOLKIT" "$mapper_file" | wc -l)
    encryption_total=$((crypto_count + obfuscation_count))
    [ $encryption_total -gt 0 ] && echo "Encryption Functions: $encryption_total (Critical - 15점)" >> "$analysis_result"
    
    # DBMS Packages
    dbms_count=$(grep -i -E "DBMS_OUTPUT|DBMS_LOB|DBMS_XMLGEN|DBMS_RANDOM|DBMS_UTILITY" "$mapper_file" | wc -l)
    [ $dbms_count -gt 0 ] && echo "DBMS Packages: $dbms_count (Critical - 15점)" >> "$analysis_result"
    
    # PL/SQL Blocks
    plsql_count=$(grep -i -E "(BEGIN|DECLARE|PROCEDURE|FUNCTION)" "$mapper_file" | wc -l)
    [ $plsql_count -gt 0 ] && echo "PL/SQL Blocks: $plsql_count (Critical - 15점)" >> "$analysis_result"
    
    # XML Functions
    xml_count=$(grep -i -E "XMLType|XMLQuery|XMLTable|XMLElement|XMLAgg" "$mapper_file" | wc -l)
    [ $xml_count -gt 0 ] && echo "XML Functions: $xml_count (Critical - 15점)" >> "$analysis_result"
    
    # Hierarchical Functions
    hierarchical_functions_count=$(grep -i -E "SYS_CONNECT_BY_PATH|CONNECT_BY_ROOT|CONNECT_BY_ISLEAF|CONNECT_BY_ISCYCLE" "$mapper_file" | wc -l)
    [ $hierarchical_functions_count -gt 0 ] && echo "Hierarchical Functions: $hierarchical_functions_count (Critical - 15점)" >> "$analysis_result"
    
    # Flashback Queries
    flashback_count=$(grep -i -E "AS OF TIMESTAMP|AS OF SCN|VERSIONS BETWEEN" "$mapper_file" | wc -l)
    [ $flashback_count -gt 0 ] && echo "Flashback Queries: $flashback_count (Critical - 15점)" >> "$analysis_result"
    
    # MODEL Clause
    model_count=$(grep -i -E "MODEL\s+PARTITION\s+BY|MODEL\s+DIMENSION\s+BY" "$mapper_file" | wc -l)
    [ $model_count -gt 0 ] && echo "MODEL Clause: $model_count (Critical - 15점)" >> "$analysis_result"
    
    # High Complexity Features (10점씩) - 복잡한 로직 변환
    echo "## High Complexity Oracle Features ##" >> "$analysis_result"
    
    # Complex Hierarchical Queries
    connect_by_count=$(grep -i -E "CONNECT BY.*START WITH|START WITH.*CONNECT BY" "$mapper_file" | wc -l)
    [ $connect_by_count -gt 0 ] && echo "Complex Hierarchical Queries: $connect_by_count (High - 10점)" >> "$analysis_result"
    
    # Advanced Aggregate Functions
    listagg_count=$(grep -i -E "LISTAGG|XMLAGG|COLLECT" "$mapper_file" | wc -l)
    [ $listagg_count -gt 0 ] && echo "Advanced Aggregate Functions: $listagg_count (High - 10점)" >> "$analysis_result"
    
    # Complex MERGE Statements
    merge_count=$(grep -i -E "MERGE.*WHEN MATCHED.*WHEN NOT MATCHED" "$mapper_file" | wc -l)
    [ $merge_count -gt 0 ] && echo "Complex MERGE Statements: $merge_count (High - 10점)" >> "$analysis_result"
    
    # Oracle Outer Joins with multiple tables
    outer_join_count=$(grep -E "\(\+\)" "$mapper_file" | wc -l)
    [ $outer_join_count -gt 0 ] && echo "Oracle Outer Joins: $outer_join_count (High - 10점)" >> "$analysis_result"
    
    # Regular Expressions
    regexp_count=$(grep -i -E "REGEXP_LIKE|REGEXP_SUBSTR|REGEXP_REPLACE|REGEXP_INSTR" "$mapper_file" | wc -l)
    [ $regexp_count -gt 0 ] && echo "Regular Expressions: $regexp_count (High - 10점)" >> "$analysis_result"
    
    # Advanced Analytics Functions
    analytics_count=$(grep -i -E "PERCENTILE_CONT|PERCENTILE_DISC|CUME_DIST|PERCENT_RANK|NTILE" "$mapper_file" | wc -l)
    [ $analytics_count -gt 0 ] && echo "Advanced Analytics Functions: $analytics_count (High - 10점)" >> "$analysis_result"
    
    # Complex Window Functions
    window_functions_count=$(grep -i -E "LAG\(|LEAD\(|FIRST_VALUE\(|LAST_VALUE\(.*OVER\s*\(" "$mapper_file" | wc -l)
    [ $window_functions_count -gt 0 ] && echo "Complex Window Functions: $window_functions_count (High - 10점)" >> "$analysis_result"
    
    # Statistical Functions
    stats_functions_count=$(grep -i -E "STDDEV\(|VARIANCE\(|CORR\(|COVAR_POP\(|COVAR_SAMP\(" "$mapper_file" | wc -l)
    [ $stats_functions_count -gt 0 ] && echo "Statistical Functions: $stats_functions_count (High - 10점)" >> "$analysis_result"
    
    # Performance Hints
    performance_hints_count=$(grep -i -E "/\*\+.*PARALLEL|/\*\+.*INDEX|/\*\+.*FULL" "$mapper_file" | wc -l)
    [ $performance_hints_count -gt 0 ] && echo "Performance Hints: $performance_hints_count (High - 10점)" >> "$analysis_result"
    
    # Advanced SQL Structures
    advanced_sql_count=$(grep -i -E "CUBE\s*\(|ROLLUP\s*\(|GROUPING SETS" "$mapper_file" | wc -l)
    [ $advanced_sql_count -gt 0 ] && echo "Advanced SQL Structures: $advanced_sql_count (High - 10점)" >> "$analysis_result"
    
    # Medium-High Complexity Features (7점씩) - 상당한 변환 작업
    echo "## Medium-High Complexity Oracle Features ##" >> "$analysis_result"
    
    # Complex DECODE
    complex_decode_count=$(grep -i -E "DECODE\s*\([^)]*,[^)]*,[^)]*,[^)]*," "$mapper_file" | wc -l)
    [ $complex_decode_count -gt 0 ] && echo "Complex DECODE: $complex_decode_count (Medium-High - 7점)" >> "$analysis_result"
    
    # Advanced Date Functions
    advanced_date_count=$(grep -i -E "ADD_MONTHS\(|MONTHS_BETWEEN\(|NEXT_DAY\(|LAST_DAY\(" "$mapper_file" | wc -l)
    [ $advanced_date_count -gt 0 ] && echo "Advanced Date Functions: $advanced_date_count (Medium-High - 7점)" >> "$analysis_result"
    
    # Oracle Conversion Functions
    conversion_functions_count=$(grep -i -E "TO_BINARY_DOUBLE\(|TO_BINARY_FLOAT\(|HEXTORAW\(|RAWTOHEX\(" "$mapper_file" | wc -l)
    [ $conversion_functions_count -gt 0 ] && echo "Oracle Conversion Functions: $conversion_functions_count (Medium-High - 7점)" >> "$analysis_result"
    
    # Collection Operations
    collection_ops_count=$(grep -i -E "MEMBER OF|SUBMULTISET OF" "$mapper_file" | wc -l)
    [ $collection_ops_count -gt 0 ] && echo "Collection Operations: $collection_ops_count (Medium-High - 7점)" >> "$analysis_result"
    
    # Advanced String Functions
    advanced_string_count=$(grep -i -E "SOUNDEX\(|METAPHONE\(|COMPOSE\(|DECOMPOSE\(|UNISTR\(" "$mapper_file" | wc -l)
    [ $advanced_string_count -gt 0 ] && echo "Advanced String Functions: $advanced_string_count (Medium-High - 7점)" >> "$analysis_result"
    
    # Oracle Math Functions
    math_functions_count=$(grep -i -E "BITAND\(|BITOR\(|BITXOR\(|LN\(|LOG\(|EXP\(" "$mapper_file" | wc -l)
    [ $math_functions_count -gt 0 ] && echo "Oracle Math Functions: $math_functions_count (Medium-High - 7점)" >> "$analysis_result"
    
    # JSON Functions (Oracle 12c+)
    json_functions_count=$(grep -i -E "JSON_VALUE\(|JSON_QUERY\(|JSON_TABLE\(" "$mapper_file" | wc -l)
    [ $json_functions_count -gt 0 ] && echo "JSON Functions: $json_functions_count (Medium-High - 7점)" >> "$analysis_result"
    
    # Medium Complexity Features (5점씩) - 표준 변환 작업
    echo "## Medium Complexity Oracle Features ##" >> "$analysis_result"
    
    # Common Oracle Functions
    nvl_count=$(grep -i -E "NVL\(" "$mapper_file" | wc -l)
    nvl2_count=$(grep -i -E "NVL2\(" "$mapper_file" | wc -l)
    substr_count=$(grep -i -E "SUBSTR\(" "$mapper_file" | wc -l)
    instr_count=$(grep -i -E "INSTR\(" "$mapper_file" | wc -l)
    length_count=$(grep -i -E "LENGTH\(" "$mapper_file" | wc -l)
    common_functions_total=$((nvl_count + nvl2_count + substr_count + instr_count + length_count))
    [ $common_functions_total -gt 0 ] && echo "Common Oracle Functions: $common_functions_total (Medium - 5점)" >> "$analysis_result"
    
    # Basic Date Functions
    to_date_count=$(grep -i "TO_DATE" "$mapper_file" | wc -l)
    to_char_count=$(grep -i "TO_CHAR" "$mapper_file" | wc -l)
    sysdate_count=$(grep -i "SYSDATE" "$mapper_file" | wc -l)
    extract_count=$(grep -i -E "EXTRACT\(" "$mapper_file" | wc -l)
    trunc_count=$(grep -i -E "TRUNC\(" "$mapper_file" | wc -l)
    basic_date_total=$((to_date_count + to_char_count + sysdate_count + extract_count + trunc_count))
    [ $basic_date_total -gt 0 ] && echo "Basic Date Functions: $basic_date_total (Medium - 5점)" >> "$analysis_result"
    
    # String Functions
    ltrim_count=$(grep -i -E "LTRIM\(" "$mapper_file" | wc -l)
    rtrim_count=$(grep -i -E "RTRIM\(" "$mapper_file" | wc -l)
    lpad_count=$(grep -i -E "LPAD\(" "$mapper_file" | wc -l)
    rpad_count=$(grep -i -E "RPAD\(" "$mapper_file" | wc -l)
    replace_count=$(grep -i -E "REPLACE\(" "$mapper_file" | wc -l)
    translate_count=$(grep -i -E "TRANSLATE\(" "$mapper_file" | wc -l)
    upper_count=$(grep -i -E "UPPER\(" "$mapper_file" | wc -l)
    lower_count=$(grep -i -E "LOWER\(" "$mapper_file" | wc -l)
    string_functions_total=$((ltrim_count + rtrim_count + lpad_count + rpad_count + replace_count + translate_count + upper_count + lower_count))
    [ $string_functions_total -gt 0 ] && echo "String Functions: $string_functions_total (Medium - 5점)" >> "$analysis_result"
    
    # Numeric Functions
    round_count=$(grep -i -E "ROUND\(" "$mapper_file" | wc -l)
    ceil_count=$(grep -i -E "CEIL\(" "$mapper_file" | wc -l)
    floor_count=$(grep -i -E "FLOOR\(" "$mapper_file" | wc -l)
    mod_count=$(grep -i -E "MOD\(" "$mapper_file" | wc -l)
    power_count=$(grep -i -E "POWER\(" "$mapper_file" | wc -l)
    sqrt_count=$(grep -i -E "SQRT\(" "$mapper_file" | wc -l)
    abs_count=$(grep -i -E "ABS\(" "$mapper_file" | wc -l)
    sign_count=$(grep -i -E "SIGN\(" "$mapper_file" | wc -l)
    numeric_functions_total=$((round_count + ceil_count + floor_count + mod_count + power_count + sqrt_count + abs_count + sign_count))
    [ $numeric_functions_total -gt 0 ] && echo "Numeric Functions: $numeric_functions_total (Medium - 5점)" >> "$analysis_result"
    
    # Conditional Functions
    nullif_count=$(grep -i -E "NULLIF\(" "$mapper_file" | wc -l)
    coalesce_count=$(grep -i -E "COALESCE\(" "$mapper_file" | wc -l)
    simple_case_count=$(grep -i -E "CASE.*WHEN.*THEN" "$mapper_file" | wc -l)
    conditional_functions_total=$((nullif_count + coalesce_count + simple_case_count))
    [ $conditional_functions_total -gt 0 ] && echo "Conditional Functions: $conditional_functions_total (Medium - 5점)" >> "$analysis_result"
    
    # Basic Conversion Functions
    to_number_count=$(grep -i -E "TO_NUMBER\(" "$mapper_file" | wc -l)
    to_timestamp_count=$(grep -i -E "TO_TIMESTAMP\(" "$mapper_file" | wc -l)
    cast_count=$(grep -i -E "CAST\(" "$mapper_file" | wc -l)
    basic_conversion_total=$((to_number_count + to_timestamp_count + cast_count))
    [ $basic_conversion_total -gt 0 ] && echo "Basic Conversion Functions: $basic_conversion_total (Medium - 5점)" >> "$analysis_result"
    
    # Sequences
    nextval_count=$(grep -i -E "\.NEXTVAL" "$mapper_file" | wc -l)
    currval_count=$(grep -i -E "\.CURRVAL" "$mapper_file" | wc -l)
    sequence_count=$((nextval_count + currval_count))
    [ $sequence_count -gt 0 ] && echo "Sequences: $sequence_count (Medium - 5점)" >> "$analysis_result"
    
    # Basic Hierarchical Queries
    simple_connect_by_count=$(grep -i -E "CONNECT BY\s+PRIOR" "$mapper_file" | wc -l)
    [ $simple_connect_by_count -gt 0 ] && echo "Basic CONNECT BY: $simple_connect_by_count (Medium - 5점)" >> "$analysis_result"
    
    # Oracle Operators
    concat_operator_count=$(grep -E "\|\|" "$mapper_file" | wc -l)
    prior_operator_count=$(grep -i -E "PRIOR\s+" "$mapper_file" | wc -l)
    oracle_operators_total=$((concat_operator_count + prior_operator_count))
    [ $oracle_operators_total -gt 0 ] && echo "Oracle Operators: $oracle_operators_total (Medium - 5점)" >> "$analysis_result"
    
    # Low Complexity Features (2점씩) - 단순 변환
    echo "## Low Complexity Oracle Features ##" >> "$analysis_result"
    
    # FROM DUAL
    dual_count=$(grep -i "FROM DUAL" "$mapper_file" | wc -l)
    [ $dual_count -gt 0 ] && echo "FROM DUAL: $dual_count (Low - 2점)" >> "$analysis_result"
    
    # Basic ROWNUM
    rownum_count=$(grep -i -E "ROWNUM\s*<=?\s*[0-9]+" "$mapper_file" | wc -l)
    [ $rownum_count -gt 0 ] && echo "Basic ROWNUM: $rownum_count (Low - 2점)" >> "$analysis_result"
    
    # Simple Oracle Data Types
    varchar2_count=$(grep -i -E "VARCHAR2\s*\(" "$mapper_file" | wc -l)
    number_count=$(grep -i -E "NUMBER\s*\(" "$mapper_file" | wc -l)
    date_type_count=$(grep -i -E "\bDATE\b" "$mapper_file" | wc -l)
    simple_datatypes_total=$((varchar2_count + number_count + date_type_count))
    [ $simple_datatypes_total -gt 0 ] && echo "Simple Oracle Data Types: $simple_datatypes_total (Low - 2점)" >> "$analysis_result"
    
    # Extended Data Types
    long_count=$(grep -i -E "\bLONG\b" "$mapper_file" | wc -l)
    raw_count=$(grep -i -E "RAW\s*\(" "$mapper_file" | wc -l)
    urowid_count=$(grep -i -E "UROWID" "$mapper_file" | wc -l)
    extended_datatypes_total=$((long_count + raw_count + urowid_count))
    [ $extended_datatypes_total -gt 0 ] && echo "Extended Data Types: $extended_datatypes_total (Low - 2점)" >> "$analysis_result"
    
    # Basic Oracle Hints
    basic_hints_count=$(grep -i -E "/\*\+\s*FIRST_ROWS\s*\*/" "$mapper_file" | wc -l)
    [ $basic_hints_count -gt 0 ] && echo "Basic Oracle Hints: $basic_hints_count (Low - 2점)" >> "$analysis_result"
    
    # Minimal Impact Features (1점씩) - 거의 영향 없음
    echo "## Minimal Impact Oracle Features ##" >> "$analysis_result"
    
    # Commented Oracle Code
    commented_oracle_count=$(grep -E "^\s*--.*ORACLE|^\s*/\*.*ORACLE" "$mapper_file" | wc -l)
    [ $commented_oracle_count -gt 0 ] && echo "Commented Oracle Code: $commented_oracle_count (Minimal - 1점)" >> "$analysis_result"
    
    # Unused Oracle Constructs
    unused_oracle_count=$(grep -i -E "ORACLE|ORA_" "$mapper_file" | grep -v -E "(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE)" | wc -l)
    [ $unused_oracle_count -gt 0 ] && echo "Unused Oracle Constructs: $unused_oracle_count (Minimal - 1점)" >> "$analysis_result"
    
    # 복잡도 점수 계산 - 새로운 6단계 체계
    echo "## Complexity Score Calculation ##" >> "$analysis_result"
    
    critical_score=$(((dblink_count + encryption_total + dbms_count + plsql_count + xml_count + hierarchical_functions_count + flashback_count + model_count) * 15))
    high_score=$(((connect_by_count + listagg_count + merge_count + outer_join_count + regexp_count + analytics_count + window_functions_count + stats_functions_count + performance_hints_count + advanced_sql_count) * 10))
    medium_high_score=$(((complex_decode_count + advanced_date_count + conversion_functions_count + collection_ops_count + advanced_string_count + math_functions_count + json_functions_count) * 7))
    medium_score=$(((common_functions_total + basic_date_total + string_functions_total + numeric_functions_total + conditional_functions_total + basic_conversion_total + sequence_count + simple_connect_by_count + oracle_operators_total) * 5))
    low_score=$(((dual_count + rownum_count + simple_datatypes_total + extended_datatypes_total + basic_hints_count) * 2))
    minimal_score=$(((commented_oracle_count + unused_oracle_count) * 1))
    
    total_score=$((critical_score + high_score + medium_high_score + medium_score + low_score + minimal_score))
    
    echo "Critical Features Score (15점): $critical_score" >> "$analysis_result"
    echo "High Complexity Score (10점): $high_score" >> "$analysis_result"
    echo "Medium-High Complexity Score (7점): $medium_high_score" >> "$analysis_result"
    echo "Medium Complexity Score (5점): $medium_score" >> "$analysis_result"
    echo "Low Complexity Score (2점): $low_score" >> "$analysis_result"
    echo "Minimal Impact Score (1점): $minimal_score" >> "$analysis_result"
    echo "TOTAL COMPLEXITY SCORE: $total_score" >> "$analysis_result"
    
    # 난이도 등급 결정 - 새로운 6단계 체계
    if [ $total_score -le 30 ]; then
        difficulty="Level 1 (Simple)"
        timeline="1-2 weeks"
    elif [ $total_score -le 80 ]; then
        difficulty="Level 2 (Moderate)"
        timeline="3-4 weeks"
    elif [ $total_score -le 150 ]; then
        difficulty="Level 3 (Complex)"
        timeline="2-3 months"
    elif [ $total_score -le 300 ]; then
        difficulty="Level 4 (High Risk)"
        timeline="3-4 months"
    elif [ $total_score -le 500 ]; then
        difficulty="Level 5 (Critical)"
        timeline="6-9 months"
    else
        difficulty="Level 6 (Extreme)"
        timeline="12+ months"
    fi
    
    echo "MIGRATION DIFFICULTY: $difficulty" >> "$analysis_result"
    echo "ESTIMATED TIMELINE: $timeline" >> "$analysis_result"
    echo "================================" >> "$analysis_result"
    
    # CSV용 결과 반환
    echo "$total_score:$difficulty:$timeline"
}

# 전체 Oracle 패턴 분석 실행
analyze_all_oracle_patterns() {
    local application_folder="$1"
    local analysis_file="$application_folder/Oracle_Pattern_Analysis.txt"
    local summary_csv="$application_folder/Oracle_Complexity_Summary.csv"
    
    echo "Oracle Pattern Analysis Report" > "$analysis_file"
    echo "Generated: $(date)" >> "$analysis_file"
    echo "========================================" >> "$analysis_file"
    
    # CSV 헤더
    echo "Mapper_File,Total_Score,Difficulty_Level,Timeline" > "$summary_csv"
    
    total_files=0
    total_oracle_score=0
    critical_files=0
    
    # 전체 Oracle 패턴 카운터 초기화 (새로운 패턴들 포함)
    total_dblink_count=0
    total_encryption_count=0
    total_dbms_count=0
    total_plsql_count=0
    total_xml_count=0
    total_hierarchical_functions_count=0
    total_flashback_count=0
    total_model_count=0
    total_connect_by_count=0
    total_listagg_count=0
    total_merge_count=0
    total_outer_join_count=0
    total_regexp_count=0
    total_analytics_count=0
    total_window_functions_count=0
    total_stats_functions_count=0
    total_performance_hints_count=0
    total_advanced_sql_count=0
    total_functions_count=0
    total_sequence_count=0
    total_rownum_count=0
    total_dual_count=0
    
    echo "Starting comprehensive analysis of ALL mapper files..."
    
    while IFS=',' read -r line_num filename; do
        if [ "$line_num" != "No." ] && [ -f "$filename" ]; then
            echo "Analyzing file $total_files: $(basename "$filename")"
            
            result=$(analyze_oracle_patterns "$filename" "$analysis_file")
            
            IFS=':' read -r score difficulty timeline <<< "$result"
            
            # 통계 집계
            total_files=$((total_files + 1))
            total_oracle_score=$((total_oracle_score + score))
            
            if [ $score -gt 300 ]; then
                critical_files=$((critical_files + 1))
            fi
            
            # 개별 패턴 카운트 집계 (새로운 패턴들 포함)
            file_dblink_count=$(grep -i "@[a-zA-Z_][a-zA-Z0-9_]*" "$filename" | wc -l)
            file_encryption_count=$(grep -i -E "DBMS_CRYPTO|DBMS_OBFUSCATION" "$filename" | wc -l)
            file_dbms_count=$(grep -i -E "DBMS_OUTPUT|DBMS_LOB|DBMS_XMLGEN" "$filename" | wc -l)
            file_plsql_count=$(grep -i -E "BEGIN|DECLARE|PROCEDURE|FUNCTION" "$filename" | wc -l)
            file_xml_count=$(grep -i -E "XMLType|XMLQuery|XMLTable" "$filename" | wc -l)
            file_hierarchical_functions_count=$(grep -i -E "SYS_CONNECT_BY_PATH|CONNECT_BY_ROOT" "$filename" | wc -l)
            file_flashback_count=$(grep -i -E "AS OF TIMESTAMP|VERSIONS BETWEEN" "$filename" | wc -l)
            file_model_count=$(grep -i -E "MODEL\s+PARTITION\s+BY" "$filename" | wc -l)
            file_connect_by_count=$(grep -i -E "CONNECT BY.*START WITH" "$filename" | wc -l)
            file_listagg_count=$(grep -i -E "LISTAGG|XMLAGG" "$filename" | wc -l)
            file_merge_count=$(grep -i -E "MERGE.*WHEN MATCHED" "$filename" | wc -l)
            file_outer_join_count=$(grep -E "\(\+\)" "$filename" | wc -l)
            file_regexp_count=$(grep -i -E "REGEXP_LIKE|REGEXP_SUBSTR" "$filename" | wc -l)
            file_analytics_count=$(grep -i -E "PERCENTILE_CONT|CUME_DIST|NTILE" "$filename" | wc -l)
            file_window_functions_count=$(grep -i -E "LAG\(|LEAD\(|FIRST_VALUE\(" "$filename" | wc -l)
            file_stats_functions_count=$(grep -i -E "STDDEV\(|VARIANCE\(|CORR\(" "$filename" | wc -l)
            file_performance_hints_count=$(grep -i -E "/\*\+.*PARALLEL|/\*\+.*INDEX" "$filename" | wc -l)
            file_advanced_sql_count=$(grep -i -E "CUBE\s*\(|ROLLUP\s*\(" "$filename" | wc -l)
            file_functions_count=$(grep -i -E "NVL\(|DECODE|SUBSTR" "$filename" | wc -l)
            file_sequence_count=$(grep -i -E "\.NEXTVAL|\.CURRVAL" "$filename" | wc -l)
            file_rownum_count=$(grep -i "ROWNUM" "$filename" | wc -l)
            file_dual_count=$(grep -i "FROM DUAL" "$filename" | wc -l)
            
            # 전체 카운트에 누적 (새로운 패턴들 포함)
            total_dblink_count=$((total_dblink_count + file_dblink_count))
            total_encryption_count=$((total_encryption_count + file_encryption_count))
            total_dbms_count=$((total_dbms_count + file_dbms_count))
            total_plsql_count=$((total_plsql_count + file_plsql_count))
            total_xml_count=$((total_xml_count + file_xml_count))
            total_hierarchical_functions_count=$((total_hierarchical_functions_count + file_hierarchical_functions_count))
            total_flashback_count=$((total_flashback_count + file_flashback_count))
            total_model_count=$((total_model_count + file_model_count))
            total_connect_by_count=$((total_connect_by_count + file_connect_by_count))
            total_listagg_count=$((total_listagg_count + file_listagg_count))
            total_merge_count=$((total_merge_count + file_merge_count))
            total_outer_join_count=$((total_outer_join_count + file_outer_join_count))
            total_regexp_count=$((total_regexp_count + file_regexp_count))
            total_analytics_count=$((total_analytics_count + file_analytics_count))
            total_window_functions_count=$((total_window_functions_count + file_window_functions_count))
            total_stats_functions_count=$((total_stats_functions_count + file_stats_functions_count))
            total_performance_hints_count=$((total_performance_hints_count + file_performance_hints_count))
            total_advanced_sql_count=$((total_advanced_sql_count + file_advanced_sql_count))
            total_functions_count=$((total_functions_count + file_functions_count))
            total_sequence_count=$((total_sequence_count + file_sequence_count))
            total_rownum_count=$((total_rownum_count + file_rownum_count))
            total_dual_count=$((total_dual_count + file_dual_count))
            
            # CSV에 추가
            echo "$(basename "$filename"),$score,$difficulty,$timeline" >> "$summary_csv"
            
            # 진행 상황 표시 (100개마다, 하지만 계속 진행)
            if [ $((total_files % 100)) -eq 0 ] && [ $total_files -gt 0 ]; then
                echo "Progress: $total_files files analyzed... (continuing analysis)"
            fi
        fi
    done < "$application_folder/Mapperlist.csv"
    
    echo "Comprehensive analysis completed!"
    echo "Total files analyzed: $total_files"
    echo "Total Oracle complexity score: $total_oracle_score"
    
    # 전체 요약
    echo "" >> "$analysis_file"
    echo "========================================" >> "$analysis_file"
    echo "OVERALL ANALYSIS SUMMARY" >> "$analysis_file"
    echo "========================================" >> "$analysis_file"
    echo "Total Mapper Files: $total_files" >> "$analysis_file"
    echo "Total Oracle Complexity Score: $total_oracle_score" >> "$analysis_file"
    echo "Average Complexity per File: $((total_oracle_score / total_files))" >> "$analysis_file"
    echo "Critical Risk Files: $critical_files" >> "$analysis_file"
    echo "Migration Impact: $((critical_files * 100 / total_files))% of files are high risk" >> "$analysis_file"
    
    # 전체 애플리케이션 난이도 결정
    avg_score=$((total_oracle_score / total_files))
    if [ $avg_score -le 50 ]; then
        app_complexity="LOW"
        app_timeline="2-3 months"
    elif [ $avg_score -le 150 ]; then
        app_complexity="MEDIUM"
        app_timeline="4-6 months"
    elif [ $avg_score -le 300 ]; then
        app_complexity="HIGH"
        app_timeline="6-9 months"
    else
        app_complexity="CRITICAL"
        app_timeline="12+ months"
    fi
    
    echo "OVERALL APPLICATION COMPLEXITY: $app_complexity" >> "$analysis_file"
    echo "ESTIMATED TOTAL TIMELINE: $app_timeline" >> "$analysis_file"
    
    # 전역 변수로 결과 저장 (HTML 생성에서 사용)
    export TOTAL_FILES="$total_files"
    export TOTAL_ORACLE_SCORE="$total_oracle_score"
    export APP_COMPLEXITY="$app_complexity"
    export APP_TIMELINE="$app_timeline"
    export CRITICAL_FILES="$critical_files"
    
    # 패턴별 카운트도 전역 변수로 저장 (새로운 패턴들 포함)
    export TOTAL_DBLINK_COUNT="$total_dblink_count"
    export TOTAL_DBMS_COUNT="$total_dbms_count"
    export TOTAL_ENCRYPTION_COUNT="$total_encryption_count"
    export TOTAL_PLSQL_COUNT="$total_plsql_count"
    export TOTAL_XML_COUNT="$total_xml_count"
    export TOTAL_HIERARCHICAL_FUNCTIONS_COUNT="$total_hierarchical_functions_count"
    export TOTAL_FLASHBACK_COUNT="$total_flashback_count"
    export TOTAL_MODEL_COUNT="$total_model_count"
    export TOTAL_CONNECT_BY_COUNT="$total_connect_by_count"
    export TOTAL_LISTAGG_COUNT="$total_listagg_count"
    export TOTAL_MERGE_COUNT="$total_merge_count"
    export TOTAL_OUTER_JOIN_COUNT="$total_outer_join_count"
    export TOTAL_REGEXP_COUNT="$total_regexp_count"
    export TOTAL_ANALYTICS_COUNT="$total_analytics_count"
    export TOTAL_WINDOW_FUNCTIONS_COUNT="$total_window_functions_count"
    export TOTAL_STATS_FUNCTIONS_COUNT="$total_stats_functions_count"
    export TOTAL_PERFORMANCE_HINTS_COUNT="$total_performance_hints_count"
    export TOTAL_ADVANCED_SQL_COUNT="$total_advanced_sql_count"
    export TOTAL_FUNCTIONS_COUNT="$total_functions_count"
    export TOTAL_SEQUENCE_COUNT="$total_sequence_count"
    export TOTAL_ROWNUM_COUNT="$total_rownum_count"
    export TOTAL_DUAL_COUNT="$total_dual_count"
    
    echo "Oracle Analysis Complete!"
}
