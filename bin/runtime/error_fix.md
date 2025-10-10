# SQL Error Analysis and Fix Request

## Requirements
1. **Work as PostgreSQL/MySQL Migration expert according to current DB applied in environment variables**
2. **XML File Analysis**: Find and analyze the complete SQL corresponding to SQL ID `{{SQL_ID}}` in `{{FILE_PATH}}`
   - When only XML file is provided, search subdirectories of $TRANSFORM_XML_FOLDER
3. **Error Analysis**: Analyze `{{ERROR_MESSAGE}}` error message to understand why it's problematic, referencing attached SQL `{{SQL_QUERY}}` for analysis and explanation
4. **Provide Solution**: Present fixable solutions
5. **XML Modification**: Maintain original logic, format, and syntax unconditionally, and modify XML with quick fix approach (to run on target database)
6. **Create Backup**: Create backup in /tmp before modification

## Special Error Handling Rules
6. For error type "Every derived table must have its own alias", refer to alias.md in current directory for fixes.
7. For error type "Unknown column 'ROWNUM' in 'order clause'", return as no fix needed.
8. For Unknown column errors, first check if Table Alias and column references are specified with case-sensitive aliases as described in Alias. (e.g., Error: Select a.name from EMP as A -> Solution: A.name with uppercase Alias)
9. If XML contains "simplified" comment, stop work and notify user. Never simplify/truncate.
10. Maintain XML tags. Keep choose, CDATA, and if tags
11. Be careful with outer join, subquery alias
12. Tables and aliases in uppercase.
13. Change MAX ( to MAX(. No space after MAX function.
14. Special tag conversion: "_TAG_" → `_TAG_`, "_ROWI_" → `_ROWI_`, "_COUNT_" → `_COUNT_`

## Work Process
1. Read XML file to check complete SQL for corresponding SQL ID
2. Compare and analyze error message with SQL. Skip if already fixed.
3. Identify problems and provide solutions
4. Create backup file
5. Modify XML file (Reference: Search subdirectories of $ORCL_XML_FOLDER if needed to compare logic with Oracle original)
6. Verify modifications

**⚠️ Important: Code Optimization Absolutely Prohibited**
- Do not perform any code optimization when converting for target DB compatibility
- Maintain identical to Extract file even for duplicate code
- Preserve commented code (<!-- -->) as is
- Keep indentation, spaces, tabs as identical to original as possible
- Restore unnecessary-looking conditionals identical to Extract
- Purpose: Maintain 1:1 accurate correspondence between Extract and Transform

**Please start analysis by reading the XML file right now.**