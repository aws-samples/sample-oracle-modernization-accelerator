
# SQL Transformation Error Correction Based on SQL Test Results

Reference: Apply environment information from $APP_TOOLS_FOLDER/environmentContext.md

**IMPORTANT**: This process requires interactive user input. The system MUST pause and wait for user input at designated points. Do not skip or auto-fill any user input sections.

[$TARGET_DBMS_TYPE Expert Mode]
**Objective**: Execute comprehensive SQL tests and perform SQL transformation corrections based on identified errors

**Expert Mode Configuration**: 
- Utilize specialized knowledge for SQL transformation from $SOURCE_DBMS_TYPE to $TARGET_DBMS_TYPE
- Deep understanding of $TARGET_DBMS_TYPE syntax, functions, and data types

---

## Step 1: SQL Test Execution

**MANDATORY USER INTERACTION REQUIRED**

1. **Display Current Setting**:
   ```
   ================================
   SQL Transformation Error Correction System
   ================================
   
   Modify TransformXML files based on SQL test results.
   
   Test execution command:
   cd $APP_TOOLS_FOLDER/../test && java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson $APP_LOGS_FOLDER/mapper --db $TARGET_DBMS_TYPE --include transform --json-file oma_test_result.json
   
   Result file: $APP_TOOLS_FOLDER/../test/out/oma_test_result.json
   ================================
   ```

2. **Test Execution Confirmation**:
   ```
   Do you want to execute SQL Test? (y/s/q)
   y: Yes, execute test
   s: Skip (already executed)
   q: Quit
   > 
   ```
   
   **STOP HERE - WAIT FOR USER INPUT**
   
   The system must pause and wait for user to enter y, s, or q.

Execute tests for transformed SQL using the following command:

```bash
cd $APP_TOOLS_FOLDER/../test && java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson $APP_LOGS_FOLDER/mapper --db $TARGET_DBMS_TYPE --include transform --json-file oma_test_result.json
```

**Test Result File**: `$APP_TOOLS_FOLDER/../test/out/oma_test_result.json`

---

## Step 2: Error Analysis and Correction

### 2.1 Error Identification
- Identify error items from the test result JSON file
- Extract the following information for each error:
  - XML file name
  - SQL ID
  - Error message
  - Error type (syntax error, function compatibility, data type, etc.)

### 2.2 Related File Location Verification
- **Source XML** ($SOURCE_DBMS_TYPE): `$APP_LOGS_FOLDER/mapper/**/extract/*.xml`
- **Transformed XML** ($TARGET_DBMS_TYPE): `$APP_LOGS_FOLDER/mapper/**/transform/*.xml`

### 2.3 Error Analysis Process
Perform the following steps for each error:

1. **Error Cause Analysis**
   - Compare original SQL with transformed SQL
   - Identify syntax differences between $SOURCE_DBMS_TYPE and $TARGET_DBMS_TYPE
   - Identify specific issues based on error messages

2. **Propose Correction Plan**
   - Explain specific correction details
   - Compare SQL before and after correction
   - Review impact of correction on other parts

3. **Request User Approval**
   - Clearly explain proposed corrections to user
   - Proceed with correction only after user approval
   - Suggest alternatives if not approved

**Error Analysis Result Display**:
```
================================
Error Analysis and Correction Plan ($TARGET_DBMS_TYPE Expert Analysis)
================================

📋 SQLID: [sqlid]
📄 File Information:
   - SourceXML: [source_xml_path]
   - TransformXML: [transform_xml_path]

❌ Error Analysis:
   - Error Message: [error_message]
   - Root Cause: [root_cause_analysis]
   - $TARGET_DBMS_TYPE Constraints: [target_constraints]

🔧 Correction Proposal:
   BEFORE: [original_sql_snippet]
   AFTER:  [proposed_sql_snippet]
   
   Correction Details: [specific_changes]

⚠️  Correction Considerations:
   - Impact Scope: [impact_scope]
   - Performance Impact: [performance_impact]
   - Validation Requirements: [validation_requirements]

================================
Do you approve this correction? (y/n/s/q)
y: Approve and proceed with correction
n: Skip this error
s: Auto-approve all corrections
q: Quit
================================
```

**STOP HERE - WAIT FOR USER APPROVAL**

The system must pause and wait for user to enter y, n, s, or q.
Each modification requires explicit user approval.

4. **Execute Correction**
   - Create backup of transformed XML file (filename.xml.YYYYMMDD_HHMMSS)
   - Apply approved corrections
   - Confirm correction completion

**Correction Execution Process**:
```
================================
Executing Correction
================================

📁 Target File: [transform_xml_path]
💾 Backup File: [transform_xml_path].xml.YYYYMMDDHHMM

🔄 Progress:
   ✅ Backup file creation completed
   🔧 Modifying TransformXML...
   ✅ Correction completed
   🔍 Validation completed

================================
```

---

## Step 3: Post-Correction Validation and Testing

### 3.1 Individual File Testing
Perform individual testing for each modified file to verify that corrections have been applied correctly:

**Individual File Test Command**:
```bash
cd $APP_TOOLS_FOLDER/../test && java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson [modified_file_name] --db $TARGET_DBMS_TYPE 
```

**Individual Test Confirmation**:
```
================================
Individual Test for Modified File
================================

📄 Modified File: [modified_file_name]
🧪 Test Command: 
   cd $APP_TOOLS_FOLDER/../test && java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson [modified_file_name] --db $TARGET_DBMS_TYPE 

Do you want to execute individual test? (y/n/s)
y: Yes, execute individual test
n: Skip
s: Go directly to full test
> 
```

**STOP HERE - WAIT FOR USER INPUT**

### 3.2 Full Re-testing
- Re-execute Step 1 full test after all corrections are completed
- Check whether new errors occurred and existing errors were resolved
- Verify side effects caused by corrections

**Full Re-test Command**:
```bash
cd $APP_TOOLS_FOLDER/../test && java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson $APP_LOGS_FOLDER/mapper --db $TARGET_DBMS_TYPE --include transform --json-file oma_test_result_after_fix.json
```

### 3.3 Result Comparison and Analysis
- Compare test results before and after corrections
- Confirm number of resolved errors
- Identify newly occurred errors
- Evaluate overall improvement status

**Result Comparison Display**:
```
================================
Before/After Correction Results Comparison
================================

📊 Test Result Summary:
   Errors before correction: [before_error_count]
   Errors after correction: [after_error_count]
   Resolved errors: [resolved_count]
   New errors: [new_error_count]

✅ Resolved Error List:
   - [resolved_error_1]
   - [resolved_error_2]
   ...

❌ Remaining Error List:
   - [remaining_error_1]
   - [remaining_error_2]
   ...

⚠️  New Errors:
   - [new_error_1]
   - [new_error_2]
   ...

================================
```

### 3.4 Convergence Conditions and Iteration Decision
- Repeat Steps 2-3 until all SQL errors are resolved
- Provide progress report at each iteration
- Report unsolvable errors to user and suggest alternatives

**Iteration Confirmation**:
```
================================
Next Step Selection
================================

Corrections completed so far: [completed_count]
Remaining errors: [remaining_count]
Improvement rate: [improvement_rate]%

Select next action:
1: Continue correcting remaining errors
2: Prioritize newly occurred errors
3: Individual file re-test
4: Execute full test
5: Complete corrections and exit
> 
```

**STOP HERE - WAIT FOR USER DECISION**

The system must pause and wait for user selection.
Continue until all errors are resolved or user chooses to exit.

---

## Important Notes

- **Backup Required**: Backup original files before all corrections
- **Incremental Correction**: Process one error at a time, not multiple errors simultaneously
- **Individual Validation**: Immediately validate with individual tests after each file correction
- **Comprehensive Validation**: Perform comprehensive validation with full tests after multiple file corrections
- **Side Effect Monitoring**: Monitor for new errors caused by corrections
- **Documentation**: Clearly record correction details and reasons
- **User Confirmation**: Proceed with all corrections only after user approval
- **Test Command Utilization**: 
  - Individual file: `cd $APP_TOOLS_FOLDER/../test && java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson [filename] --db $TARGET_DBMS_TYPE `
  - Full test: `cd $APP_TOOLS_FOLDER/../test && java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson $APP_LOGS_FOLDER/mapper --db $TARGET_DBMS_TYPE --include transform --json-file oma_test_result.json`

