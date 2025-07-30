# Application Analysis and DB Migration Pre-Analysis and Report Generation Prompt

Reference: Apply environment information from $APP_TOOLS_FOLDER/environmentContext.md

## Objective
1. Analyze Java Source code of the Application to perform pre-analysis work for changing Source DBMS to Target DBMS and create a report

## Work Procedure
1. Part 1: Analysis Phase execution
2. Part 2: Reporting Phase

## Environment Information Verification and Output Directory Creation within Prompt

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

# Part 1: Analysis Phase

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
   - **Apply header exclusion calculation when using in HTML reports as well**

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
2. Aggregate total usage count and file count for each pattern
3. Calculate overall migration complexity score by applying weights by complexity
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
     # When combining find and grep
     find "$JAVA_SOURCE_FOLDER" -name "*.xml" -exec grep -l "pattern" {} \; 2>/dev/null
     
     # When using pipelines
     command1 | command2 || true
     
     # Ignore error output
     grep "pattern" "$file" 2>/dev/null || echo 0
     ```
   
   **🚨 Absolutely Prohibited:**
   - `if [ $variable -gt 0 ]` (no quotes)
   - `count=$(wc -l)` (no newline removal)
   - `total=$((total + $count))` (arithmetic without variable cleanup)
   
   **⚠️ Not following these rules will cause the following errors:**
   - `[: integer expression expected`
   - `syntax error in expression`  
   - `[: too many arguments`
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

5. **Sample SQL Extraction**:
   - Extract representative SQL statements for each pattern from all selected files
   - Select SQL that clearly shows pattern characteristics (within 20-30 lines)
   - Utilize conversion plan information from Oracle.md

**Expected Selection Structure** (Based on Oracle.md):
```
Critical Patterns (1 per pattern type):
- Database Links (if exists) → 1 file
- PL/SQL Blocks (if exists) → 1 file

High Patterns (1 per pattern type):
- CONNECT BY pattern → 1 file
- Oracle Outer Join (+) pattern → 1 file  
- ROW_NUMBER pattern → 1 file
- MERGE pattern → 1 file
- Other High pattern types, 1 each

Medium Patterns (1 per top usage pattern type):
- NVL pattern → 1 file (highest usage)
- SUBSTR pattern → 1 file
- REPLACE pattern → 1 file  
- TO_CHAR pattern → 1 file
- DECODE pattern → 1 file
- FROM DUAL pattern → 1 file
- SYSDATE pattern → 1 file
- Other high-frequency pattern types, 1 each
```

**Flexibility Considerations**:
- Pattern type usage may vary by project
- Selected pattern types automatically adjust according to Oracle.md analysis results
- Small projects: Critical + High + several major Medium pattern types
- Large projects: Critical + High + many Medium pattern types
- **Core**: Focus on representativeness by pattern type, not file count per pattern

**Validation Criteria**:
- Verify consistency with Oracle.md analysis results
- Verify that selected samples represent major Oracle pattern types
- Final review for missing high-frequency pattern types
- **Important**: Prevent duplicate selection of same pattern type

**Output Files**: 
- `$APPLICATION_FOLDER/discovery/SampleMapperlist.csv` (priority-based, variable per project)
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
   
   **Examples**:
   ```
   If $TRANSFORM_JNDI=jdbc:
   - ${topas_db_ibe} → Transform='Yes' (all JNDI)
   - TOPASAIRDB → Transform='Yes' (all JNDI)
   - YELLOWBRIDGEDB → Transform='Yes' (all JNDI)
   
   If $TRANSFORM_JNDI=topas_db_ibe:
   - ${topas_db_ibe} → Transform='Yes' (match)
   - topas_db_ibe_backup → Transform='Yes' (contains)
   - TOPASAIRDB → Transform='No' (no match)
   ```

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
1. Aggregate usage file count and usage count per pattern
2. Classify by dependency level (Low/Medium/High)
3. Provide conversion plans and alternatives
4. Write risk assessment and recommendations
5. **Variable Handling Precautions in Bash Script Writing (100% identical application of section 3.2 rule 7)**:
   - **🚨 Important**: Apply rule 7 from Oracle pattern analysis section (3.2) above **100% identically**
   - **Clean all numeric variables before use**: `dependency_count=$(echo "$dependency_count" | tr -d '\n' | tr -d ' ')`
   - **Variables must have quotes in conditional statements**: `if [ "$dependency_count" -gt 0 ]`
   - **wc -l result processing**: `count=$(grep -c "pattern" "$file" 2>/dev/null | tr -d '\n')`
   - **Set variable default values**: `dependency_count=${dependency_count:-0}`
   - **SIGPIPE Error Prevention**:
     - Java file search: `find "$JAVA_SOURCE_FOLDER" -name "*.java" -exec grep -l "oracle.jdbc" {} \; 2>/dev/null`
     - Safe counting: `grep -c "pattern" "$file" 2>/dev/null || echo 0`
     - Pipeline processing: `command | grep pattern || true`
   
   **⚠️ Absolutely Prohibited**: `if [ $dependency_count -gt 0 ]`, `count=$(wc -l)` (no newline removal)
   **🔧 Apply all bash rules from section 3.2 identically here to prevent errors.**

---

## Part 1 Output File List (Analysis Results)

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

## Part 1 Completion Verification and Part 2 Preparation

### Analysis Result Verification
```bash
# Check required file generation
echo "=== Part 1 Analysis Result File Check ==="
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
        echo "✗ $file missing - Cannot proceed to Part 2"
        all_files_exist=false
    fi
done

if [ "$all_files_exist" = true ]; then
    echo "✅ Part 1 analysis completed - Part 2 report generation ready"
else
    echo "❌ Part 1 analysis incomplete - Create missing files first"
    exit 1
fi
```

### Part 2 Progress Condition Checklist
- [ ] All analysis files generated (7 MD + 5 CSV/TXT)
- [ ] Oracle pattern analysis completed (complexity score calculated)
- [ ] Sample mapper selection completed (based on Critical/High patterns)
- [ ] DataSource Transform configuration verified (based on `$TRANSFORM_JNDI`)
- [ ] Application name extraction completed (for report filename generation)

### Analysis Result Summary Output
```bash
echo "=== Part 1 Analysis Result Summary ==="
echo "Analysis Target: $(grep -h "Application Name" $APPLICATION_FOLDER/discovery/ApplicationOverview.md 2>/dev/null || echo "Unknown")"
echo "Total Mapper Files: $(wc -l < $APPLICATION_FOLDER/discovery/Mapperlist.csv 2>/dev/null || echo "0") files"
echo "Oracle Pattern Complexity: $(grep -h "Complexity Score" $APPLICATION_FOLDER/discovery/Oracle.md 2>/dev/null || echo "Not calculated")"
echo "Transform Target JNDI: $TRANSFORM_JNDI"
echo "Target DBMS: $TARGET_DBMS_TYPE"
echo ""
echo "🚀 Starting Part 2 (Report Generation Phase)..."
```

# Part 2: Reporting Phase

Integrate analysis result files generated in Part 1 to create a professional HTML report.

## Part 2 Output File List (Reports)

### HTML Report (1 file)
1. `DiscoveryReport-[APPLICATION_NAME].html` - Comprehensive analysis report

**Reports are saved in the `$APPLICATION_FOLDER/` directory.**

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

---

## HTML Report Generation

### Objective
Generate comprehensive HTML report by integrating analysis result files (7 MD files + 3 CSV files)

### HTML Generation and Combination by Work Unit

#### Step 1: Basic Information Collection and HTML Header Generation
**Work Instructions**:
1. **Application Name Extraction**: Extract application name from `ApplicationOverview.md`
2. **Analysis Date**: Set to current date
3. **HTML Header Generation**: Include CSS styles from `./discovery-details/appDiscoveryTemplate.html`
4. **Basic Variable Setup**: APPLICATION_NAME, ANALYSIS_DATE, TARGET_DBMS_TYPE

**Output**: `/tmp/html_header.html`

#### Step 2: Executive Summary Section Generation
**Work Instructions**:
1. Generate Executive Summary by integrating all analysis results
2. Generate migration timeline
3. Generate priority recommendation list
4. Present risk assessment and response plans

**Output**: `/tmp/html_summary.html`

#### Step 3: Application Overview Section Generation
**Work Instructions**:
1. Convert **ApplicationOverview.md** content to HTML
2. Convert **TechnicalStack.md** content to technology stack cards
3. Convert **ProjectDirectory.md** content to directory tree format
4. Replace template variables like `[APPLICATION_NAME]`, `[BUILD_TOOL]`, `[JAVA_VERSION]`

**Output**: `/tmp/html_overview.html`

#### Step 4: DataSource Information Section Generation
**Work Instructions**:
1. Convert **DataSource.csv** file to HTML table
2. Convert **MapperDataSource.csv** file to mapping relationship table
3. Highlight Transform='Yes' items
4. Generate statistics by JNDI

**Output**: `/tmp/html_datasource.html`

#### Step 5: MyBatis Analysis Section Generation
**Work Instructions**:
1. Convert **MyBatis.md** content to configuration analysis section
2. Convert **MyBatisDetails.md** content to detailed information section
3. Generate mapper statistics from **Mapperlist.csv** (total count, classification by namespace)
4. **Add Mapper File Quality Analysis**:
   ```html
   <div class="warning-box">
       <h3>📊 Mapper File Quality Analysis</h3>
       <div class="grid">
           <div class="card">
               <h4>Total Mapper Files</h4>
               <div class="metric">
                   <span class="metric-value">[TOTAL_MAPPER_FILES]</span>
                   <span class="metric-label">Total searched files</span>
               </div>
           </div>
           <div class="card">
               <h4>Valid SQL Mappers</h4>
               <div class="metric">
                   <span class="metric-value">[VALID_MAPPER_FILES]</span>
                   <span class="metric-label">Files with actual SQL</span>
               </div>
           </div>
           <div class="card">
               <h4>Empty Mapper Files</h4>
               <div class="metric">
                   <span class="metric-value">[EMPTY_MAPPER_FILES]</span>
                   <span class="metric-label">Files without SQL</span>
               </div>
           </div>
           <div class="card">
               <h4>Quality Index</h4>
               <div class="metric">
                   <span class="metric-value">[MAPPER_QUALITY_RATIO]%</span>
                   <span class="metric-label">Valid file ratio</span>
               </div>
           </div>
       </div>
       
       <h4>🔍 Empty Mapper File Details</h4>
       <table class="pattern-table">
           <thead>
               <tr>
                   <th>File Name</th>
                   <th>Namespace</th>
                   <th>Status</th>
                   <th>Description</th>
                   <th>Recommendation</th>
               </tr>
           </thead>
           <tbody>
               [EMPTY_MAPPER_FILES_TABLE]
           </tbody>
       </table>
       
       <div class="summary-box">
           <h4>💡 Mapper File Cleanup Recommendations</h4>
           <ul>
               <li><strong>Empty File Cleanup</strong>: Review removal of [EMPTY_MAPPER_FILES] empty Mapper files before migration</li>
               <li><strong>Code Cleanup</strong>: Review necessity of unused Custom Mapper files</li>
               <li><strong>Quality Management</strong>: Strengthen code review process to prevent future empty Mapper file creation</li>
               <li><strong>Migration Target</strong>: Actual analysis and conversion target is <strong>[VALID_MAPPER_FILES]</strong> files</li>
           </ul>
       </div>
   </div>
   ```
5. Prepare SQL count statistics and chart data
6. **Important**: 
   - Calculate total Mapper file count with `tail -n +2 Mapperlist.csv | wc -l`
   - Calculate valid Mapper file count with `awk -F',' 'NR>1 && $4>0 {count++} END {print count}' Mapperlist.csv`
   - Calculate empty Mapper file count with `grep ",0$" Mapperlist.csv | wc -l`
   - **Base actual migration analysis target on valid Mapper file count**

**Output**: `/tmp/html_mybatis.html`

#### Step 6: Oracle Pattern Analysis Section Generation (Core)
**Work Instructions**:
1. Extract pattern statistics from **Oracle.md** file
2. Classify patterns by complexity (Critical/High/Medium/Low)
3. Generate tables for each complexity level:
   - `[CRITICAL_PATTERNS_TABLE]`
   - `[HIGH_PATTERNS_TABLE]`
   - `[MEDIUM_PATTERNS_TABLE]`
   - `[LOW_PATTERNS_TABLE]`
4. Calculate complexity score and determine migration level
5. Calculate expected timeline

**Output**: `/tmp/html_oracle.html`

#### Step 7: Transform Test Set and Sample SQL Section Generation
**Work Instructions**:
1. **Combined Analysis of SampleMapperlist.csv and SampleOracleSQL.txt**:
   - Extract sample file list and pattern information from SampleMapperlist.csv
   - Extract actual SQL statements for each pattern from SampleOracleSQL.txt
   - Match information from both files to create integrated table

2. **Transform Test Set Configuration**:
   - Use selected sample files as test set for Oracle → Target DBMS conversion testing
   - Display conversion complexity and test priority for each pattern
   - Classify Critical/High patterns as essential conversion verification items
   - Classify Medium patterns as bulk conversion test items

3. **SQL Sample and Conversion Example Display**:
   - **Important**: Use `<div class="sql-sample">` or `<div class="transform-example">` class for all SQL statements and conversion examples
   - Convert `\n` to actual line breaks when generating HTML for proper line break display
   - Apply `max-height: 300px` for long SQL statements to enable scrolling

**Output**: `/tmp/html_transform_testset.html`

#### Step 8: Java Dependency Analysis Section Generation
**Work Instructions**:
1. Convert **JavaCodeDependency.md** content to HTML
2. Generate Oracle-specific code usage status table
3. Classify and visualize by dependency level
4. Present recommendations and alternatives
5. **Conversion Plan and Example Display**:
   - **Important**: Use `<div class="transform-example">` class for all code examples and conversion plans
   - Convert `\n` to actual line breaks when generating HTML for proper line break display
   - Use `<div class="code-block">` class for code blocks

**Output**: `/tmp/html_java.html`

#### Step 9: Final HTML Report Combination
**Work Instructions**:
1. Combine all HTML fragments in order:
   - `/tmp/html_header.html`
   - `/tmp/html_summary.html` (Executive Summary)
   - `/tmp/html_overview.html`
   - `/tmp/html_datasource.html`
   - `/tmp/html_mybatis.html`
   - `/tmp/html_oracle.html`
   - `/tmp/html_transform_testset.html`
   - `/tmp/html_java.html`
2. Complete all template variable substitutions
3. Validate HTML
4. Generate final file

**Final Output**: `$APPLICATION_FOLDER/DiscoveryReport-[APPLICATION_NAME].html`

#### Step 10: Temporary File Cleanup
**Work Instructions**:
```bash
# Clean up temporary HTML files
rm -f /tmp/html_*.html
```

### Variable Substitution List
- `[APPLICATION_NAME]`: Application name
- `[ANALYSIS_DATE]`: Analysis date
- `[TARGET_DBMS_TYPE]`: Target DBMS
- `[TOTAL_MAPPER_FILES]`: Total mapper file count (**Important**: Calculate excluding headers with `tail -n +2 Mapperlist.csv | wc -l`)
- `[VALID_MAPPER_FILES]`: Valid SQL Mapper file count (files with SqlCount > 0)
- `[EMPTY_MAPPER_FILES]`: Empty Mapper file count (files with SqlCount = 0)
- `[MAPPER_QUALITY_RATIO]`: Mapper quality index (valid files/total files*100)
- `[EMPTY_MAPPER_FILES_TABLE]`: Empty Mapper file detail table
- `[MIGRATION_COMPLEXITY_LEVEL]`: Migration complexity level
- `[ESTIMATED_TIMELINE]`: Expected timeline
- `[COMPLEXITY_SCORE]`: Complexity score
- `[CRITICAL_PATTERNS_TOTAL]`: Total Critical pattern count
- `[HIGH_PATTERNS_TOTAL]`: Total High pattern count
- `[MEDIUM_PATTERNS_TOTAL]`: Total Medium pattern count
- `[LOW_PATTERNS_TOTAL]`: Total Low pattern count
- `[CRITICAL_TEST_COUNT]`: Critical pattern test file count (1 per pattern type)
- `[HIGH_TEST_COUNT]`: High pattern test file count (1 per pattern type)
- `[MEDIUM_TEST_COUNT]`: Medium pattern test file count (1 per pattern type)
- `[TOTAL_TEST_FILES]`: Total Transform test file count
- `[CRITICAL_TRANSFORM_TESTSET]`: Critical pattern Transform test set table
- `[HIGH_TRANSFORM_TESTSET]`: High pattern Transform test set table
- `[MEDIUM_TRANSFORM_TESTSET]`: Medium pattern Transform test set table
- Other table and list variables

### Precautions
1. **File Existence Check**: Verify required files exist at each step
2. **Error Handling**: Use default values when files are missing or format is incorrect
3. **Encoding**: Maintain UTF-8 encoding
4. **Responsive Design**: Apply CSS for good mobile viewing
5. **Data Validation**: Validate CSV file data format before HTML conversion
6. **Mapper Count Calculation**: Calculate all Mapper counts with `tail -n +2 Mapperlist.csv | wc -l` method excluding headers
7. **Transform Test Set**: Select 1 per pattern type to prevent duplication
8. **Line Break Handling**: Use appropriate CSS classes for SQL samples and Transform examples to ensure line breaks
9. **Bash Script Variable Handling (100% identical to Part 1 section 3.2 rule 7)**:
   - **🚨 Very Important**: Apply rule 7 from Oracle pattern analysis section (3.2) in Part 1 **100% identically**
   - **All variables must have quotes in conditional statements**: `if [ "$variable" -gt 0 ]`
   - **Remove newline characters when processing wc -l results**: `count=$(echo "$matches" | wc -l | tr -d '\n')`
   - **Clean all numeric variables before use**: `count=$(echo "$count" | tr -d '\n' | tr -d ' ')`
   - **Use quotes for file path variables too**: `find "$JAVA_SOURCE_FOLDER" -name "$filename"`
   - **Set variable default values**: `count=${count:-0}`
   - **Use quotes when checking empty values**: `if [ -n "$file_path" ]; then`
   - **🚨 Absolutely Prohibited**: `if [ $variable -gt 0 ]`, `count=$(wc -l)` (no newline removal)
   - **⚠️ Not following this will cause `[: integer expression expected`, `syntax error in expression` errors**
10. **SIGPIPE Error Prevention**:
   - `find` command and `grep` combination: `find "$JAVA_SOURCE_FOLDER" -name "*.xml" -exec grep -l "pattern" {} \; 2>/dev/null`
   - Or safe file processing: `find "$JAVA_SOURCE_FOLDER" -name "*.xml" | while read file; do grep -q "pattern" "$file" && echo "$file"; done`
   - Add `|| true` when using pipelines: `find ... | grep ... || true`
   - Error output redirection: `2>/dev/null` or `2>&1`

**Final Result**: Professional and visually excellent Oracle migration analysis report

---
