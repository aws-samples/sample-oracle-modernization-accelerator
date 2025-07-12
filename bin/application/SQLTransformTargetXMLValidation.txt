
3. XML Validation Process:
    3.1 Validation Command:
        - Tool: xmllint
        - Format: xmllint --noout [filepath] 2>&1
        Example:
        xmllint --noout {MAPPER_TGTL1_DIR}/AuthDAO{TRANSFORM_SUFFIX}-01-select-createAuthNo.xml 2>&1

    3.2 Error Handling:
        - Special Case: "StartTag: invalid element name"
            * If related to inequality signs
            * Can be ignored in MyBatis environment
            * No action required

    3.3 Logging:
        - Do not create separate validation log file
        - Display results in console only
