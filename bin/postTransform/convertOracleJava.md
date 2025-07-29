# Convert Java Files to Remove Oracle Dependencies

Reference: Apply environment information from $APP_TOOLS_FOLDER/environmentContext.md

**Language Instruction**: All messages, prompts, and user interactions must be displayed in Korean.(한글)

**IMPORTANT**: This process requires interactive user input. The system MUST pause and wait for user input at designated points. Do not skip or auto-fill any user input sections.

[Java Expert Mode]
**Objective**: Convert Java source code with Oracle dependencies to $TARGET_DBMS_TYPE compatible code

## Task Instructions

### 0. Source Directory Configuration
**Interactive Source Directory Setup**

**MANDATORY USER INTERACTION REQUIRED**
The following steps require user input. The system must pause and wait for user responses.

1. **Display Current Setting**:
   ```
   ================================
   JAVA SOURCE DIRECTORY CONFIGURATION
   ================================
   
   Current JAVA_SOURCE_FOLDER: $JAVA_SOURCE_FOLDER
   
   Please specify the source directory where Java files should be scanned.
   The system will recursively search this directory and all subdirectories for Java files.
   
   Example paths:
   - /workspace/project/src/main/java
   - /workspace/project/orcl/src
   - /home/user/myproject/backend
   
   ================================
   ```

2. **User Input Prompt**:
   ```
   Enter the source directory path for Java file scanning:
   > 
   ```
   
   **STOP HERE - WAIT FOR USER INPUT**
   
   The system must pause at this point and wait for the user to enter the source directory path.
   Do not proceed to the next step until the user provides input.
   
   Expected user input format: /path/to/java/source/directory

3. **Directory Validation**:
   - Verify the entered path exists and is accessible
   - Confirm the directory contains Java files (*.java)
   - Display directory structure preview if requested

4. **Confirmation**:
   ```
   ================================
   DIRECTORY SCAN CONFIGURATION
   ================================
   
   📁 Selected Directory: [user_entered_path]
   🔍 Scan Mode: Recursive (includes all subdirectories)
   📄 Target Files: *.java
   
   Proceed with this configuration? (y/n/c)
   y: Yes, start scanning
   n: No, enter different directory
   c: Cancel operation
   ================================
   ```
   
   **STOP HERE - WAIT FOR USER CONFIRMATION**
   
   The system must pause and wait for user to enter y, n, or c.
   Do not proceed until user provides confirmation.

### 1. Identification Phase
- Recursively scan the user-specified Java source directory to identify files and code sections with Oracle dependencies

**Scan Results Display**:
```
================================
JAVA FILE SCAN RESULTS
================================

📁 Scanned Directory: [user_specified_path]
📊 Total Java Files Found: [count]
🔍 Files with Oracle Dependencies: [count_with_oracle]

📋 Files to Process:
   1. [file_path_1] - [oracle_dependency_types]
   2. [file_path_2] - [oracle_dependency_types]
   3. [file_path_3] - [oracle_dependency_types]
   ...

🎯 Oracle Dependency Types Detected:
   - JDBC Drivers: [count] files
   - SQL Functions: [count] files  
   - Data Types: [count] files
   - Connection Strings: [count] files
   - PL/SQL Constructs: [count] files

================================
Proceed with conversion? (y/n/q)
y: Yes, start conversion process
n: No, reconfigure source directory
q: Quit
================================
```

**STOP HERE - WAIT FOR USER DECISION**

The system must pause and wait for user to enter y, n, or q.
Do not proceed until user provides their choice.
- Detect the following Oracle-specific patterns:
  - Oracle JDBC drivers (`oracle.jdbc.*`)
  - Oracle-specific SQL syntax and functions
  - Oracle data types and PL/SQL constructs
  - Oracle connection strings and properties
  - Oracle-specific annotations and imports
  - Proprietary Oracle APIs and utilities

### 2. Analysis and Planning
- Provide detailed conversion guidance for each identified dependency
- Assess compatibility requirements with target database system
- Identify potential risks and breaking changes
- Suggest alternative implementations using standard JDBC or target-specific APIs

**Temporary File Management**:
- **All temporary work files MUST be created in /tmp directory**
- Use descriptive naming convention: `/tmp/oracle_java_conversion_[timestamp]_[purpose].[extension]`
- Examples:
  - `/tmp/oracle_java_conversion_20250729_180000_analysis.txt` - Analysis results
  - `/tmp/oracle_java_conversion_20250729_180000_backup_list.txt` - Backup file tracking
  - `/tmp/oracle_java_conversion_20250729_180000_changes.log` - Temporary change log
  - `/tmp/oracle_java_conversion_20250729_180000_diff.txt` - Code difference previews
- Clean up temporary files after successful completion or user cancellation

### 3. Interactive Approval Process
- Present changes for approval before modification
- Create backup copies of original files in the same directory with timestamp suffix (YYYYMMDD_HHMMSS)
- Execute approved modifications with proper error handling

### 4. Documentation and Logging
- Record all changes in $APP_TRANSFORM_FOLDER/ConvertJava.log
- Include before/after code snippets
- Document any manual intervention required

## Approval Request Template

```
================================
FILE MODIFICATION APPROVAL REQUEST
================================

📁 SOURCE FILE: [file_path]
📝 FILE TYPE: [.java/.properties/.xml] 
🔍 DETECTED PATTERN: [pattern_type] ([pattern_description])
📊 COMPLEXITY: [Low/Medium/High]

❌ IDENTIFIED ISSUES:
   - [specific_oracle_dependency_1]
   - [specific_oracle_dependency_2]
   - [additional_issues...]

🔧 PROPOSED MODIFICATIONS:
   - [specific_change_1_with_code_example]
   - [specific_change_2_with_code_example]
   - [additional_changes...]

📈 CONVERSION QUALITY: [current_state] → [expected_post_conversion_state]

📊 IMPACT ASSESSMENT:
   - Functional Impact: [description_of_functional_changes]
   - Performance Impact: [expected_performance_changes]
   - Compatibility Impact: [compatibility_improvements]
   - Testing Requirements: [recommended_testing_approach]

⚠️  WARNINGS & CONSIDERATIONS:
   - [potential_risks_or_limitations]
   - [manual_verification_needed]
   - [additional_dependencies_required]

🔄 ROLLBACK PLAN:
   - Backup location: [same_directory_as_original]/[original_filename]_backup_YYYYMMDD_HHMMSS.[extension]
   - Working copy: /tmp/oracle_java_work_[filename]_[timestamp].java
   - Diff preview: /tmp/oracle_java_diff_[filename]_[timestamp].txt
   - Rollback procedure: [steps_to_revert_changes]

================================

Proceed with modification? (y/n/s/q/d)
y: Approve and continue to next file
n: Skip this file and continue
s: Auto-approve all remaining modifications
q: Quit conversion process
d: Show detailed diff preview (saved to /tmp/oracle_java_diff_[filename]_[timestamp].txt)
```

**STOP HERE - WAIT FOR USER APPROVAL**

The system must pause and wait for user to enter y, n, s, q, or d.
Each file modification requires explicit user approval.
Do not proceed until user provides their decision.

## Core Principles

### 1. Individual File Assessment
- **No batch pattern replacements**: Each file must be individually analyzed
- **Context-aware conversion**: Consider the specific use case and surrounding code
- **Semantic preservation**: Maintain original functionality while removing Oracle dependencies

### 2. Safety and Reliability
- **Mandatory backups**: Create timestamped backups in the same directory as the original file with format: [filename]_backup_YYYYMMDD_HHMMSS.[extension]
  - Example: `DatabaseConnection.java` → `DatabaseConnection_backup_20250729_180000.java`
- **Temporary work files**: All intermediate processing files MUST be created in `/tmp` directory
  - Working copies for analysis: `/tmp/oracle_java_[filename]_work_[timestamp].java`
  - Diff files for preview: `/tmp/oracle_java_[filename]_diff_[timestamp].txt`
  - Validation results: `/tmp/oracle_java_validation_[timestamp].log`
- **Incremental changes**: Apply changes one file at a time with validation
- **Rollback capability**: Maintain ability to revert changes if issues arise
- **Cleanup**: Remove all temporary files from `/tmp` upon completion or cancellation

### 3. Quality Assurance
- **Code review**: Present clear before/after comparisons
- **Testing recommendations**: Suggest appropriate testing strategies
- **Documentation**: Maintain comprehensive change logs

### 4. Target Database Compatibility
- **Standards compliance**: Prefer ANSI SQL and JDBC standards where possible
- **Target-specific optimization**: Use $TARGET_DBMS_TYPE specific features when beneficial
- **Performance consideration**: Ensure converted code maintains or improves performance

## Common Oracle Dependencies to Address

### Database Connectivity
- `oracle.jdbc.OracleDriver` → Standard JDBC drivers
- Oracle connection URLs → Target database URLs
- Oracle-specific connection properties

### SQL Syntax and Functions
- Oracle-specific functions (NVL, DECODE, ROWNUM, etc.)
- PL/SQL blocks and procedures
- Oracle date/time functions
- Hierarchical queries (CONNECT BY)
- Oracle-specific data types (VARCHAR2, NUMBER, etc.)

### Framework Integration
- Oracle-specific Hibernate dialects
- Oracle sequences and identity columns
- Oracle-specific JPA annotations

## Error Handling and Recovery

### Temporary File Management
- **Location**: All temporary files MUST be created in `/tmp` directory
- **Naming Convention**: `/tmp/oracle_java_conversion_[component]_[timestamp].[ext]`
- **Cleanup Policy**: 
  - Remove temporary files on successful completion
  - Remove temporary files on user cancellation
  - Preserve temporary files only on critical errors for debugging
- **File Types**:
  - Analysis files: `/tmp/oracle_java_analysis_[timestamp].txt`
  - Working copies: `/tmp/oracle_java_work_[filename]_[timestamp].java`
  - Diff previews: `/tmp/oracle_java_diff_[filename]_[timestamp].txt`
  - Error logs: `/tmp/oracle_java_error_[timestamp].log`

### Validation Steps
1. Syntax validation after each change
2. Compilation verification
3. Basic functionality testing recommendations

### Recovery Procedures
1. Automatic backup restoration on critical errors
2. Partial rollback capabilities
3. Change log for manual recovery

## Logging Format

Each entry in ConvertJava.log should include:
```
[TIMESTAMP] [FILE_PATH] [CHANGE_TYPE] [STATUS]
BEFORE: [original_code_snippet]
AFTER:  [modified_code_snippet]
REASON: [explanation_of_change]
IMPACT: [assessment_of_change_impact]
---
```
