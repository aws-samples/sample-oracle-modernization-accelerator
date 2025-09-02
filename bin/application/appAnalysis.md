# Application Analysis and Oracle Migration Pre-Analysis Prompt

Reference: Apply environment information from $APP_TOOLS_FOLDER/environmentContext.md

## Objective
Analyze Java Source code of the Application to perform pre-analysis work for changing Source DBMS to Target DBMS and generate analysis data files

## Environment Information Verification and Output Directory Creation

**Environment Variable Verification**:
```bash
echo "=== Environment Variable Verification ==="
echo "JAVA_SOURCE_FOLDER: $JAVA_SOURCE_FOLDER"
echo "SOURCE_SQL_MAPPER_FOLDER: $SOURCE_SQL_MAPPER_FOLDER" 
echo "APPLICATION_FOLDER: $APPLICATION_FOLDER"
echo "TARGET_DBMS_TYPE: $TARGET_DBMS_TYPE"
echo "TRANSFORM_JNDI: $TRANSFORM_JNDI"
```

**Directory Creation**:
```bash
mkdir -p $APPLICATION_FOLDER/discovery
```

**Environment Information**:
- **JAVA Source Folder**: `$JAVA_SOURCE_FOLDER`
- **SQL MAPPER Folder**: `$SOURCE_SQL_MAPPER_FOLDER`
- **Discover Output**: `$APPLICATION_FOLDER/discovery`
- **Target DBMS**: `$TARGET_DBMS_TYPE` (Optional, default: general analysis)
- **Transform JNDI**: `$TRANSFORM_JNDI` (Transform target JNDI identifier, e.g., jdbc)

---

# Analysis Phase

This phase systematically analyzes the application structure and Oracle dependencies.

## 1. Application Basic Information Collection

### 1.1 Project Information Identification
```bash
# Explore project files to perform analysis
# Example: find $JAVA_SOURCE_FOLDER -name "pom.xml" -o -name "build.gradle" -o -name "web.xml"

# Analysis items:
# - Project type identification (Maven/Gradle/Traditional Web)
# - Application name extraction (artifactId from pom.xml or display-name from web.xml, etc.)
# - Project version information collection
```
**Output File**: `$APPLICATION_FOLDER/discovery/ApplicationOverview.md`

### 1.2 Technology Stack Analysis
```bash
# Dependency analysis
# - Analyze major dependencies from pom.xml or build.gradle
# - Check Spring Framework version and modules
# - Check Java version
# - Identify web frameworks (Spring MVC, Struts, etc.)
# - Identify other major libraries and frameworks
```
**Output File**: `$APPLICATION_FOLDER/discovery/TechnicalStack.md`

### 1.3 Directory Structure Generation
```bash
# Project structure analysis
find $JAVA_SOURCE_FOLDER -type d | grep -v -E "\.(class|jar|git)" | head -50

# Analysis items:
# - Generate major directory structure
# - Exclude unnecessary files (.class, .jar, .git, etc.)
# - Format to match HTML template directory-tree format
# - Identify directory structure by major modules
```
**Output File**: `$APPLICATION_FOLDER/discovery/ProjectDirectory.md`

---

## 2. MyBatis Detailed Analysis

### 2.1 MyBatis Configuration File Analysis
```bash
# MyBatis configuration file exploration
find $JAVA_SOURCE_FOLDER -name "*mybatis*.xml" -o -name "sqlMapConfig.xml"

# Analysis items:
# - Parse configuration file contents like mybatis-config.xml, sqlMapConfig.xml
# - Extract and analyze Type Aliases
# - Extract Settings information (cacheEnabled, defaultStatementTimeout, etc.)
# - Check custom SqlSessionFactory implementation
# - Analyze Mapper scan configuration
```
**Output File**: `$APPLICATION_FOLDER/discovery/MyBatis.md`

### 2.2 MyBatis Version and Dependency Details
```bash
# MyBatis dependency analysis
grep -r "mybatis" $JAVA_SOURCE_FOLDER --include="pom.xml" --include="build.gradle"

# Analysis items:
# - Check MyBatis version from pom.xml
# - Analyze MyBatis-Spring integration method
# - Check database driver information
```
**Output File**: `$APPLICATION_FOLDER/discovery/MyBatisDetails.md`

---

## 3. MyBatis Mapper List Extraction and Oracle Pattern Analysis

### 3.1 Mapper File List Generation

**Objective**: Find and list MyBatis Mapper XML files within the project

**Work Instructions**:
1. **MyBatis Mapper File Identification Method**: 
   - **Check only MyBatis DTD declaration for all .xml files**
   - File name or directory location is irrelevant

2. **MyBatis XML Identification Criteria (Only judgment criterion)**:
   - MyBatis DTD declaration: `<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"`
   - If this DTD exists, it's definitely a MyBatis Mapper file

3. **Search Method**:
   ```bash
   # Find Mapper by MyBatis DTD in all XML files (case insensitive)
   find "$JAVA_SOURCE_FOLDER" -name "*.xml" -type f -exec grep -l "DTD.*[Mm]apper\|[Mm]apper.*DTD" {} \; 2>/dev/null
   ```

4. **Result Storage**:
   - Save as CSV file: `Mapperlist.csv`
   - Format: `No.,FileName,Namespace,SqlCount`
   - Include full path, namespace, and SQL count for each mapper file

5. **Classification and Statistics**:
   - Classify only actual MyBatis Mapper files (files that passed content-based verification)
   - Aggregate total mapper file count and SQL statement count
   - **Important**: All counts calculate only actual data excluding headers (`tail -n +2 Mapperlist.csv | wc -l`)

6. **Bash Script Writing Precautions**:
   - File search: `find "$JAVA_SOURCE_FOLDER" -name "$pattern"`
   - Condition check: `if [ -f "$file_path" ]`, `if [ "$count" -gt 0 ]`
   - Wrap all variables in quotes to prevent errors from spaces or special characters
   - **SIGPIPE Error Prevention**:
     - `find` and `grep` combination: `find "$JAVA_SOURCE_FOLDER" -name "*.xml" -exec grep -l "namespace" {} \; 2>/dev/null`
     - Safe pipeline handling: `find ... | head -1 || true`
     - Large file processing: `while read file; do ... done < <(find ...)`

### 3.2 Oracle SQL Pattern Discovery and Analysis

**Objective**: Systematically analyze Oracle-specific SQL patterns in Mapper files from Mapperlist.csv to evaluate DB migration complexity

**Analysis Target Patterns (Classified by Complexity)**:

**Critical Patterns (Very Complex Migration - Architecture Change Required)**:
- **Database Links**: `[A-Z0-9_]+@[A-Z0-9_]{3,}` (table@DBLink pattern) - Distributed database redesign required
- **PL/SQL Blocks**: Check file-level existence of `DECLARE` keyword or `(BEGIN + END;)` combination - Conversion to application logic required
- **Oracle Packages**: `DBMS_CRYPTO`, `DBMS_JOB`, `DBMS_SCHEDULER`, `UTL_SMTP`, `UTL_FILE`, `UTL_HTTP`
- **Advanced Queuing**: `DBMS_AQ`, `AQ$` - Message queue system redesign
- **Oracle Text**: `CONTAINS`, `CATSEARCH`, `MATCHES` - Full-text search engine change

**High Complexity Patterns (Complex Logic Conversion)**:
- **Hierarchical Queries**: `CONNECT BY`, `START WITH`, `PRIOR`, `LEVEL` - Convert to recursive queries
- **Oracle Outer Joins**: `(+)` - Convert to standard OUTER JOIN
- **Analytic Functions**: `ROW_NUMBER()`, `RANK()`, `DENSE_RANK()`, `LAG()`, `LEAD()`, `FIRST_VALUE()`, `LAST_VALUE()`
- **MERGE Statement**: `MERGE INTO...WHEN MATCHED...WHEN NOT MATCHED` - Convert to UPSERT logic
- **PIVOT/UNPIVOT**: `PIVOT`, `UNPIVOT` - Convert to dynamic SQL or CASE statements
- **Model Clause**: `MODEL` - Rewrite complex calculation logic
- **Flashback Queries**: `AS OF TIMESTAMP`, `VERSIONS BETWEEN` - Change history management logic

**Medium Complexity Patterns (Function Mapping Required)**:
- **IS NULL Handling**: IS NULL, IS NOT NULL - Statement conversion
- **NULL Handling**: `NVL`, `NVL2`, `NULLIF`, `COALESCE` - Convert to NULL handling functions
- **Conditional Functions**: `DECODE`, `CASE WHEN` - Convert to CASE statements
- **Date Functions**: `SYSDATE`, `SYSTIMESTAMP`, `ADD_MONTHS`, `MONTHS_BETWEEN`, `NEXT_DAY`, `LAST_DAY`, `TRUNC`, `EXTRACT`
- **String Functions**: `SUBSTR`, `INSTR`, `LENGTH`, `LTRIM`, `RTRIM`, `TRIM`, `REPLACE`, `TRANSLATE`, `INITCAP`
- **Conversion Functions**: `TO_DATE`, `TO_CHAR`, `TO_NUMBER`, `TO_TIMESTAMP`, `TO_CLOB`
- **Aggregate Functions**: `LISTAGG`, `WMSYS.WM_CONCAT`, `XMLAGG` - Convert to string aggregation functions
- **Regular Expression Functions**: `REGEXP_LIKE`, `REGEXP_SUBSTR`, `REGEXP_REPLACE`, `REGEXP_INSTR`, `REGEXP_COUNT`
- **Sequences**: `.NEXTVAL`, `.CURRVAL` - Convert to sequences or auto-increment
- **Math Functions**: `POWER`, `SQRT`, `MOD`, `CEIL`, `FLOOR`, `ROUND`, `TRUNC`, `SIGN`

**Low Complexity Patterns (Simple Substitution)**:
- **Dual Table**: `FROM DUAL` - Remove or replace
- **Row Limiting**: `ROWNUM`, `ROWID` - Convert to row limiting statements
- **Data Types**: `VARCHAR2`, `NUMBER`, `CLOB`, `BLOB`, `NVARCHAR2`, `NCLOB`, `RAW`, `LONG`
- **Operators**: `||` (string concatenation) - Convert to string concatenation functions
- **Pseudo Columns**: `LEVEL`, `CONNECT_BY_ISLEAF`, `CONNECT_BY_ISCYCLE`
- **Oracle Hints**: `/*+ FIRST_ROWS */`, `/*+ INDEX */`, `/*+ PARALLEL */`, `/*+ USE_NL */`

**Very Low Complexity Patterns (Almost Compatible)**:
- **Basic Functions**: `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`
- **Basic Operators**: `=`, `!=`, `<>`, `<`, `>`, `<=`, `>=`
- **Logical Operators**: `AND`, `OR`, `NOT`
- **Basic SQL**: `SELECT`, `INSERT`, `UPDATE`, `DELETE`

**Analysis Method**:
1. **Search Target**: Analyze only mapper files from Mapperlist.csv generated in 3.1

2. **Performance Optimized Pattern Search Strategy**:
   ```bash
   # Create pattern files for bulk processing (MUCH FASTER)
   critical_patterns="/tmp/critical_patterns.txt"
   cat > "$critical_patterns" << 'CRIT_EOF'
   [A-Z0-9_]+@[A-Z0-9_]{3,}
   DECLARE
   BEGIN.*END;
   DBMS_CRYPTO
   DBMS_JOB
   DBMS_SCHEDULER
   UTL_SMTP
   UTL_FILE
   UTL_HTTP
   DBMS_AQ
   AQ\$
   CONTAINS
   CATSEARCH
   MATCHES
   CRIT_EOF
   
   high_patterns="/tmp/high_patterns.txt"
   cat > "$high_patterns" << 'HIGH_EOF'
   CONNECT BY
   START WITH
   PRIOR
   LEVEL
   \(\+\)
   ROW_NUMBER\(\)
   RANK\(\)
   DENSE_RANK\(\)
   LAG\(\)
   LEAD\(\)
   FIRST_VALUE\(\)
   LAST_VALUE\(\)
   MERGE INTO
   PIVOT
   UNPIVOT
   MODEL
   AS OF TIMESTAMP
   VERSIONS BETWEEN
   HIGH_EOF
   
   medium_patterns="/tmp/medium_patterns.txt"
   cat > "$medium_patterns" << 'MED_EOF'
   NVL\s*\(
   NVL2\s*\(
   NULLIF\s*\(
   COALESCE\s*\(
   DECODE\s*\(
   SYSDATE
   SYSTIMESTAMP
   ADD_MONTHS
   MONTHS_BETWEEN
   NEXT_DAY
   LAST_DAY
   SUBSTR\s*\(
   INSTR\s*\(
   LENGTH\s*\(
   TO_DATE\s*\(
   TO_CHAR\s*\(
   TO_NUMBER\s*\(
   LISTAGG
   WM_CONCAT
   XMLAGG
   REGEXP_LIKE
   REGEXP_SUBSTR
   REGEXP_REPLACE
   \.NEXTVAL
   \.CURRVAL
   MED_EOF
   
   low_patterns="/tmp/low_patterns.txt"
   cat > "$low_patterns" << 'LOW_EOF'
   FROM DUAL
   ROWNUM
   ROWID
   VARCHAR2
   NUMBER\s*\(
   CLOB
   BLOB
   NVARCHAR2
   NCLOB
   \|\|
   /\*\+.*\*/
   LOW_EOF
   
   # Single-pass bulk analysis (10x faster than file-by-file processing)
   mapperlist_file="$APPLICATION_FOLDER/discovery/Mapperlist.csv"
   mapper_files="/tmp/mapper_files_only.txt"
   
   # Extract only file paths from Mapperlist.csv (skip header)
   tail -n +2 "$mapperlist_file" | cut -d',' -f2 > "$mapper_files"
   
   # Bulk pattern matching with single grep per complexity level
   critical_files=$(cat "$mapper_files" | xargs grep -l -E -f "$critical_patterns" 2>/dev/null | wc -l)
   high_files=$(cat "$mapper_files" | xargs grep -l -E -f "$high_patterns" 2>/dev/null | wc -l)
   medium_files=$(cat "$mapper_files" | xargs grep -l -E -f "$medium_patterns" 2>/dev/null | wc -l)
   low_files=$(cat "$mapper_files" | xargs grep -l -E -f "$low_patterns" 2>/dev/null | wc -l)
   
   # Count occurrences with single pass
   critical_count=$(cat "$mapper_files" | xargs grep -h -E -f "$critical_patterns" 2>/dev/null | wc -l)
   high_count=$(cat "$mapper_files" | xargs grep -h -E -f "$high_patterns" 2>/dev/null | wc -l)
   medium_count=$(cat "$mapper_files" | xargs grep -h -E -f "$medium_patterns" 2>/dev/null | wc -l)
   low_count=$(cat "$mapper_files" | xargs grep -h -E -f "$low_patterns" 2>/dev/null | wc -l)
   ```

3. **Individual Pattern Analysis (Only for Top Patterns)**:
   ```bash
   # Analyze only top 5-10 most used patterns individually for detailed reporting
   # This reduces analysis time from hours to minutes
   
   # Get top patterns by usage first
   top_patterns="/tmp/top_patterns.txt"
   cat "$mapper_files" | xargs grep -h -o -E "(NVL|DECODE|SYSDATE|SUBSTR|TO_DATE|ROWNUM|CONNECT BY)" 2>/dev/null | \
   sort | uniq -c | sort -nr | head -10 > "$top_patterns"
   
   # Then analyze only these top patterns individually
   while read -r count pattern; do
       pattern_files=$(cat "$mapper_files" | xargs grep -l "$pattern" 2>/dev/null | wc -l)
       echo "$pattern,$count,$pattern_files" >> "/tmp/detailed_patterns.csv"
   done < "$top_patterns"
   ```

4. Aggregate total usage count and file count for each pattern
5. Calculate overall migration complexity score by applying weights by complexity
   - Critical: Weight 50
   - High: Weight 20
   - Medium: Weight 8
   - Low: Weight 3
   - Very Low: Weight 1
4. Extract actual usage examples (1-2 per pattern)
5. Provide conversion plans by Target DBMS (PostgreSQL, MySQL, SQL Server, etc.)
6. Identify non-convertible patterns and provide alternatives
7. **Essential Compliance Rules for Bash Script Writing (Error Prevention Required)**:
   
   **⚠️ The following rules must be strictly followed or script execution errors will occur:**
   
   **Variable Handling and Conditional Statement Writing Rules:**
   - **All variables must be wrapped in quotes in conditional statements**: 
     ```bash
     # Correct method (required)
     if [ "$count" -gt 0 ]; then
     if [ "$variable" = "value" ]; then
     if [ -n "$file_path" ]; then
     
     # Wrong method (absolutely prohibited)
     if [ $count -gt 0 ]; then  # [: integer expression expected error
     ```
   
   - **Remove newline characters when processing wc -l results (very important)**:
     ```bash
     # Correct method (required)
     count=$(echo "$matches" | wc -l | tr -d '\n')
     count=$(grep -c "pattern" "$file" 2>/dev/null || echo 0)
     
     # Or safer method
     count=$(echo "$matches" | wc -l)
     count=$(echo "$count" | tr -d '\n')
     
     # Wrong method (absolutely prohibited)
     count=$(echo "$matches" | wc -l)  # Result: "5\n" -> [: 5\n: integer expression expected
     ```
   
   - **Clean variables before arithmetic operations (required)**:
     ```bash
     # Correct method (required)
     count=$(echo "$count" | tr -d '\n' | tr -d ' ')  # Remove newlines and spaces
     count=${count:-0}  # Set to 0 if empty
     
     # Safe method for arithmetic operations
     if [ -n "$count" ] && [ "$count" -gt 0 ]; then
         total=$((total + count))
     fi
     ```
   
   - **Quotes required when using file path variables**:
     ```bash
     find "$JAVA_SOURCE_FOLDER" -name "$filename"
     grep -c "pattern" "$file_path" 2>/dev/null
     ```
   
   - **Safe method for processing grep results (required)**:
     ```bash
     # Correct method (required)
     matches=$(grep -n "pattern" "$file" 2>/dev/null || true)
     if [ -n "$matches" ]; then
         count=$(echo "$matches" | wc -l | tr -d '\n')
         count=${count:-0}  # Additional safety measure
     else
         count=0
     fi
     ```
   
   - **All numeric variables must be cleaned before use (required)**:
     ```bash
     # All count variables must be cleaned before use
     variable_count=$(echo "$variable_count" | tr -d '\n' | tr -d ' ')
     variable_count=${variable_count:-0}
     
     # When using in conditional statements
     if [ "$variable_count" -gt 0 ]; then
         echo "Count: $variable_count"
     fi
     ```
   
   - **SIGPIPE Error Prevention**:
     ```bash
     # When combining find and grep (REQUIRED)
     find "$JAVA_SOURCE_FOLDER" -name "*.xml" -type f 2>/dev/null | while read -r file; do
         if grep -l "pattern" "$file" 2>/dev/null; then
             echo "$file"
         fi
     done
     
     # Alternative safe method
     find "$JAVA_SOURCE_FOLDER" -name "*.xml" -exec grep -l "pattern" {} + 2>/dev/null || true
     
     # When using pipelines
     command1 | command2 2>/dev/null || true
     
     # Ignore error output
     grep "pattern" "$file" 2>/dev/null || echo 0
     ```
   
   - **Variable Declaration Rules (CRITICAL)**:
     ```bash
     # NEVER use 'local' outside functions - use regular variables
     # Correct method (required)
     count=0
     files=0
     score=0
     
     # Wrong method (absolutely prohibited)
     local count=0  # This will cause "local: can only be used in a function" error
     ```
   
   **🚨 Absolutely Prohibited:**
   - `if [ $variable -gt 0 ]` (no quotes)
   - `count=$(wc -l)` (no newline removal)
   - `total=$((total + $count))` (arithmetic without variable cleanup)
   - `local variable=value` (outside functions - causes "local: can only be used in a function" error)
   - `find ... -exec grep ... {} \;` (without proper error handling - causes SIGPIPE errors)
   
   **⚠️ Not following these rules will cause the following errors:**
   - `[: integer expression expected`
   - `syntax error in expression`  
   - `[: too many arguments`
   - `local: can only be used in a function`
   - `find: 'grep' terminated by signal 13` (SIGPIPE errors)
   
   **🔧 Critical Script Generation Rules:**
   1. **Never use `local` keyword outside functions** - use regular variable declarations
   2. **Always use safe find/grep combinations** with proper error handling
   3. **All pattern analysis scripts must use functions or avoid `local` completely**
   4. **Use `|| true` or `2>/dev/null` to prevent SIGPIPE errors**
   5. **Performance Optimization for Large Projects (CRITICAL)**:
      - **Use pattern files with `grep -f`** instead of individual pattern searches
      - **Use `xargs` for bulk file processing** instead of while loops
      - **Combine similar patterns** into single grep operations
      - **Process only mapper files from Mapperlist.csv** (not all XML files)
      - **Use single-pass analysis** where possible
      - **Limit individual pattern analysis** to top 10-20 most used patterns only
      - **Example**: `cat mapper_files.txt | xargs grep -E -f pattern_file.txt` (FAST)
      - **Avoid**: `while read file; do grep pattern "$file"; done` (SLOW)
   - SIGPIPE errors
   
   **🔧 Follow these rules 100% when creating all bash scripts.**

**Result Storage**:
- **Detailed Analysis Report**: `$APPLICATION_FOLDER/discovery/Oracle.md`
- **Pattern Summary Statistics**: `oracle-pattern-summary.csv`
- **Complexity Assessment and Expected Timeline Presentation**

**Output File**: `$APPLICATION_FOLDER/discovery/Oracle.md`

### 3.3 Critical/High Complexity Pattern Sample Extraction

**Objective**: Extract representative samples of patterns with high migration impact based on Oracle.md analysis results

**Sample Selection Rules**:
1. **Oracle.md File Analysis**: Extract pattern usage information from existing Oracle analysis results
2. **Selection Principles by Pattern Type**:
   - **Critical Patterns**: Select 1 per pattern type (Database Links, PL/SQL Blocks, etc.)
   - **High Patterns**: Select 1 per pattern type (CONNECT BY, ROW_NUMBER, MERGE, PIVOT, etc.)
   - **Medium Patterns**: Select 1 per top usage pattern type
     - Usage 1,000+: Priority inclusion
     - Usage 500+: Include considering file count
     - Composed of top pattern types by total usage
   - **Important**: Select only 1 file per same pattern type (e.g., only 1 even if NVL pattern exists in multiple files)

**Work Instructions**:
1. **Extract Pattern Usage from Oracle.md**:
   ```bash
   # Parse pattern usage information from Oracle.md
   grep -E "Found.*count.*:|Total.*count.*:" $APPLICATION_FOLDER/discovery/Oracle.md
   ```

2. **Step-by-step Sample Selection**:
   - **Step 1 - Critical Patterns (1 per pattern type)**:
     - Database Links (if exists) - 1 file
     - PL/SQL Blocks (if exists) - 1 file
   
   - **Step 2 - High Patterns (1 per pattern type)**:
     - 1 each per pattern type classified as High complexity in Oracle.md
     - Example: CONNECT BY pattern → 1 file, ROW_NUMBER pattern → 1 file, MERGE pattern → 1 file
   
   - **Step 3 - Medium Patterns (1 per top usage pattern type)**:
     - Select pattern types in order of high usage from Oracle.md
     - Select only 1 file per selected pattern type
     - Prioritize pattern types with high actual workload during migration
     - Flexible adjustment possible according to project scale

3. **Duplication Handling Method**:
   - **Selection by Pattern Type**: Select only 1 file per same pattern type (e.g., NVL, SUBSTR, CONNECT BY)
   - **Critical/High Patterns**: Select 1 representative file per pattern type
   - **Medium Patterns**: Select 1 per top usage pattern type to minimize duplication
   - **Coverage Goal**: Cover 70%+ of all Oracle pattern types (based on pattern types, not usage count)

4. **Sample File Information Storage**:
   - CSV file: `SampleMapperlist.csv`
   - Format: `No.,FileName,PatternType,Complexity,PatternCount,UsageRank,Description`
   - UsageRank: Overall usage ranking confirmed in Oracle.md
   - Sort by usage for clear prioritization

5. **Additional Random Sample Selection**:
   ```bash
   # Add 10 random mapper files to SampleMapperlist.csv for broader coverage
   # This provides additional samples beyond pattern-based selection
   
   mapperlist_file="$APPLICATION_FOLDER/discovery/Mapperlist.csv"
   sample_file="$APPLICATION_FOLDER/discovery/SampleMapperlist.csv"
   
   # Get total mapper count (excluding header)
   total_mappers=$(tail -n +2 "$mapperlist_file" | wc -l | tr -d '\n')
   total_mappers=${total_mappers:-0}
   
   if [ "$total_mappers" -gt 10 ]; then
       # Create temporary file with all mappers (excluding header)
       temp_mappers="/tmp/all_mappers.csv"
       tail -n +2 "$mapperlist_file" > "$temp_mappers"
       
       # Get existing sample files to avoid duplicates
       existing_samples="/tmp/existing_samples.txt"
       if [ -f "$sample_file" ]; then
           tail -n +2 "$sample_file" | cut -d',' -f2 > "$existing_samples"
       else
           touch "$existing_samples"
       fi
       
       # Filter out already selected files
       available_mappers="/tmp/available_mappers.csv"
       while IFS=',' read -r no filename namespace sqlcount; do
           if ! grep -Fxq "$filename" "$existing_samples" 2>/dev/null; then
               echo "$no,$filename,$namespace,$sqlcount" >> "$available_mappers"
           fi
       done < "$temp_mappers"
       
       # Get available mapper count
       available_count=$(wc -l < "$available_mappers" 2>/dev/null | tr -d '\n')
       available_count=${available_count:-0}
       
       # Select random samples (up to 10 or available count, whichever is smaller)
       if [ "$available_count" -gt 0 ]; then
           sample_count=10
           if [ "$available_count" -lt 10 ]; then
               sample_count="$available_count"
           fi
           
           # Randomly select samples using shuf (if available) or sort -R
           random_samples="/tmp/random_samples.csv"
           if command -v shuf >/dev/null 2>&1; then
               shuf -n "$sample_count" "$available_mappers" > "$random_samples"
           else
               sort -R "$available_mappers" | head -n "$sample_count" > "$random_samples"
           fi
           
           # Add random samples to SampleMapperlist.csv
           # Note: Do not add separator lines or comments to maintain CSV format integrity
           
           # Get current max number from existing samples
           current_max=0
           if [ -f "$sample_file" ]; then
               current_max=$(tail -n +2 "$sample_file" | grep -E "^[0-9]" | cut -d',' -f1 | sort -n | tail -1 2>/dev/null | tr -d '\n')
               current_max=${current_max:-0}
           fi
           
           # Add random samples with incremented numbers
           sample_no=$((current_max + 1))
           while IFS=',' read -r no filename namespace sqlcount; do
               echo "$sample_no,$filename,Random,Low,0,999,Random sample for broader analysis coverage" >> "$sample_file"
               sample_no=$((sample_no + 1))
           done < "$random_samples"
           
           echo "✓ Added $sample_count random mapper samples to SampleMapperlist.csv"
       else
           echo "ℹ All available mappers already selected - no additional random samples added"
       fi
   else
       echo "ℹ Total mapper count ($total_mappers) is 10 or less - no additional random samples needed"
   fi
   
   # Clean up temporary files
   rm -f /tmp/all_mappers.csv /tmp/existing_samples.txt /tmp/available_mappers.csv /tmp/random_samples.csv
   ```

6. **Sample SQL Extraction**:
   - Extract representative SQL statements for each pattern from all selected files
   - Select SQL that clearly shows pattern characteristics (within 20-30 lines)
   - Utilize conversion plan information from Oracle.md
   - Include SQL samples from random selections for comprehensive coverage

**Output Files**: 
- `$APPLICATION_FOLDER/discovery/SampleMapperlist.csv` (pattern-based + 10 random samples, variable per project)
- `$APPLICATION_FOLDER/discovery/SampleOracleSQL.txt`

---

## 4. DataSource Configuration Information Extraction

### 4.1 DataSource Configuration File Exploration

**Objective**: Extract datasource configuration information used by the application

**Work Instructions**:
1. **Configuration File Search**: 
   - Spring configuration files (`*context*.xml`, `*config*.xml`)
   - Application configuration (`application*.properties`, `application*.yml`)
   - Web configuration files (`web.xml`)

2. **DataSource Information Extraction**:
   - **JNDI Method**: `jndiName` attribute, `<jndi-lookup>` tag
   - **Direct Configuration Method**: `driverClassName`, `url`, `username` attributes
   - **Spring Boot Method**: `spring.datasource.*` properties
   - **Environment Variables**: Variable references in `${...}` format

3. **Result Storage**:
   - CSV file: `DataSource.csv`
   - Format: `Type,Name,Value,Description,Transform`
   - Type: JNDI, DIRECT, PROPERTY, etc.
   - **Transform Column Rules**:
     - If `$TRANSFORM_JNDI=jdbc`, **all JNDI have Transform='Yes'**
     - If `$TRANSFORM_JNDI` is a specific JNDI name, only matching JNDI has `Transform='Yes'`
     - If JNDI name contains `$TRANSFORM_JNDI` value, `Transform='Yes'`
     - Otherwise `Transform='No'`
     - If `$TRANSFORM_JNDI` is not set, all are `Transform='Unknown'`

### 4.2 Mapper and DataSource Mapping Information

**Objective**: Identify the relationship between MyBatis Mappers and the datasources they use

**Work Instructions**:
1. **Mapping Relationship Analysis**:
   - Check datasource per SqlSessionFactory
   - Connection relationship between transaction manager and datasource
   - Check multiple datasource usage

2. **Result Storage**:
   - CSV file: `MapperDataSource.csv`
   - Format: `MapperGroup,DataSource,SqlSessionFactory,TransactionManager`

**Output Files**: 
- `$APPLICATION_FOLDER/discovery/DataSource.csv`
- `$APPLICATION_FOLDER/discovery/MapperDataSource.csv`

---

## 5. Java Source Oracle Dependency Analysis

**Objective**: Analyze Oracle-specific code usage in Java source code

### 5.1 Oracle JDBC Driver Usage Status
**Search Targets**:
- `oracle.jdbc.*` package imports
- `OracleDriver`, `OracleConnection`, `OracleStatement` class usage
- Oracle JDBC URL patterns (`jdbc:oracle:thin:@`)

### 5.2 Oracle-Specific Data Type Usage Analysis
**Search Targets**:
- **Basic Types**: `CLOB`, `BLOB`, `NCLOB`, `BFILE`
- **Oracle SQL Types**: `oracle.sql.ARRAY`, `oracle.sql.STRUCT`, `oracle.sql.REF`
- **Time Types**: `oracle.sql.TIMESTAMP`, `oracle.sql.INTERVALDS`

### 5.3 Oracle Sequences and Specific Features
**Search Targets**:
- Sequence calls: `.NEXTVAL`, `.CURRVAL`
- `@SequenceGenerator` annotations
- Oracle exception handling: `ORA-` error codes, `OracleDatabaseException`

### 5.4 Oracle-Specific Frameworks and Libraries
**Search Targets**:
- **Oracle UCP**: `oracle.ucp.jdbc.PoolDataSource`
- **Oracle ADF**: `oracle.adf.model.binding.*`
- **Oracle Coherence**: `oracle.coherence.*`
- Other Oracle-specific annotations

### 5.5 Analysis Result Summary
**Work Instructions**:
1. **Optimized Pattern Search Strategy** (Performance Enhancement):
   ```bash
   # Use single grep with multiple patterns instead of multiple grep calls per file
   # This reduces file I/O operations significantly
   
   # Create combined pattern file for efficient searching
   pattern_file="/tmp/oracle_patterns.txt"
   cat > "$pattern_file" << 'PATTERNS_EOF'
   import.*oracle\.jdbc
   OracleDriver
   OracleConnection
   OracleStatement
   jdbc:oracle
   CLOB
   BLOB
   NCLOB
   BFILE
   oracle\.sql\.
   \.NEXTVAL
   \.CURRVAL
   @SequenceGenerator
   ORA-
   OracleDatabaseException
   oracle\.ucp
   oracle\.adf
   oracle\.coherence
   PATTERNS_EOF
   
   # Single pass analysis with combined patterns
   find "$JAVA_SOURCE_FOLDER" -name "*.java" -type f -print0 | \
   xargs -0 grep -l -E -f "$pattern_file" 2>/dev/null | \
   while read -r file; do
       # Process each matching file only once
       echo "Processing: $file"
   done
   ```

2. **Fast Bulk Analysis Method**:
   ```bash
   # Use grep with file list for bulk processing
   java_files="/tmp/java_files.txt"
   find "$JAVA_SOURCE_FOLDER" -name "*.java" -type f > "$java_files"
   
   # Bulk search for each pattern type
   oracle_jdbc_files=$(grep -l "import.*oracle\.jdbc\|OracleDriver\|OracleConnection" $(cat "$java_files") 2>/dev/null | wc -l)
   oracle_url_files=$(grep -l "jdbc:oracle" $(cat "$java_files") 2>/dev/null | wc -l)
   oracle_types_files=$(grep -l "CLOB\|BLOB\|oracle\.sql\." $(cat "$java_files") 2>/dev/null | wc -l)
   sequence_files=$(grep -l "\.NEXTVAL\|\.CURRVAL\|@SequenceGenerator" $(cat "$java_files") 2>/dev/null | wc -l)
   ```

3. Aggregate usage file count and usage count per pattern
4. Classify by dependency level (Low/Medium/High)
5. Provide conversion plans and alternatives
6. Write risk assessment and recommendations
7. **Variable Handling Precautions in Bash Script Writing (100% identical application of section 3.2 rule 7)**:
   - **🚨 Important**: Apply rule 7 from Oracle pattern analysis section (3.2) above **100% identically**
   - **Clean all numeric variables before use**: `dependency_count=$(echo "$dependency_count" | tr -d '\n' | tr -d ' ')`
   - **Variables must have quotes in conditional statements**: `if [ "$dependency_count" -gt 0 ]`
   - **wc -l result processing**: `count=$(grep -c "pattern" "$file" 2>/dev/null | tr -d '\n')`
   - **Set variable default values**: `dependency_count=${dependency_count:-0}`
   - **SIGPIPE Error Prevention**:
     - Java file search: `find "$JAVA_SOURCE_FOLDER" -name "*.java" -type f -print0 | xargs -0 grep -l "pattern" 2>/dev/null`
     - Safe counting: `grep -c "pattern" "$file" 2>/dev/null || echo 0`
     - Pipeline processing: `command | grep pattern 2>/dev/null || true`
   - **Performance Optimization Rules**:
     - Use `find ... -print0 | xargs -0` for large file sets
     - Combine multiple patterns into single grep calls
     - Use pattern files (`grep -f pattern_file`) for complex searches
     - Avoid nested loops with file I/O operations

**Output File**: `$APPLICATION_FOLDER/discovery/JavaCodeDependency.md`

---

## Analysis Output File List

### Analysis Result Files (7 files)
1. `ApplicationOverview.md` - Application overview and basic information
2. `TechnicalStack.md` - Technology stack and framework analysis
3. `ProjectDirectory.md` - Project directory structure
4. `MyBatis.md` - MyBatis configuration analysis
5. `MyBatisDetails.md` - MyBatis detailed information and integration configuration
6. `Oracle.md` - Oracle SQL pattern analysis and migration complexity assessment
7. `JavaCodeDependency.md` - Java code Oracle dependency analysis

### CSV Data Files (5 files)
1. `Mapperlist.csv` - MyBatis Mapper file list (No., FileName, Namespace, SqlCount)
2. `DataSource.csv` - DataSource configuration information (JNDI, direct configuration, etc.)
3. `MapperDataSource.csv` - Mapper and datasource mapping relationship
4. `SampleMapperlist.csv` - Critical/High pattern sample mapper file list
5. `SampleOracleSQL.txt` - Critical/High pattern sample SQL statements and conversion plans

**All files are saved in the `$APPLICATION_FOLDER/discovery/` directory.**

---

## Analysis Completion Verification

### Analysis Result Verification
```bash
# Check required file generation
echo "=== Analysis Result File Check ==="
ls -la $APPLICATION_FOLDER/discovery/

# Required file checklist
required_files=(
    "ApplicationOverview.md"
    "TechnicalStack.md"
    "Oracle.md" 
    "Mapperlist.csv"
    "DataSource.csv"
    "SampleMapperlist.csv"
)

echo "=== Check Required File Existence ==="
all_files_exist=true
for file in "${required_files[@]}"; do
    if [ -f "$APPLICATION_FOLDER/discovery/$file" ]; then
        echo "✓ $file creation completed"
    else
        echo "✗ $file missing - Cannot proceed to report generation"
        all_files_exist=false
    fi
done

if [ "$all_files_exist" = true ]; then
    echo "✅ Analysis completed - Report generation ready"
else
    echo "❌ Analysis incomplete - Create missing files first"
    exit 1
fi
```

### Analysis Result Summary Output
```bash
echo "=== Analysis Result Summary ==="
echo "Analysis Target: $(grep -h "Application Name" $APPLICATION_FOLDER/discovery/ApplicationOverview.md 2>/dev/null || echo "Unknown")"
echo "Total Mapper Files: $(tail -n +2 $APPLICATION_FOLDER/discovery/Mapperlist.csv | wc -l 2>/dev/null || echo "0") files"
echo "Oracle Pattern Complexity: $(grep -h "Complexity Score" $APPLICATION_FOLDER/discovery/Oracle.md 2>/dev/null || echo "Not calculated")"
echo "Transform Target JNDI: $TRANSFORM_JNDI"
echo "Target DBMS: $TARGET_DBMS_TYPE"
echo ""
echo "🚀 Ready for HTML Report Generation..."
```

---

## Usage

This prompt can be used for pre-analysis of migration from Oracle to other DBMS in various Java/Spring projects.

### Prerequisites
- Environment variable setup required:
  - `$JAVA_SOURCE_FOLDER`: Java source folder path
  - `$SOURCE_SQL_MAPPER_FOLDER`: SQL Mapper folder path  
  - `$APPLICATION_FOLDER`: Result storage folder path
  - `$TARGET_DBMS_TYPE`: Target DBMS for conversion (mysql, postgresql, sqlserver, etc.) - Optional
  - `$TRANSFORM_JNDI`: Transform target JNDI identifier (e.g., jdbc, specific JNDI name) - Optional

### Applicable Projects
- Spring Framework-based projects (all versions)
- MyBatis-using projects
- Oracle Database-using projects
- eGovFrame projects
- Maven/Gradle projects
- Traditional web application projects

### Next Step
After completing this analysis, use `$APP_TOOLS_FOLDER/appReporting.md` to generate HTML reports from the analysis data files.
