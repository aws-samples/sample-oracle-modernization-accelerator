
Step 2. Analyze SQL for all {MAPPER_SRCL1_DIR}/*{ORIGIN_SUFFIX}*.xml files

    1. Initial Setup:
        1.1 Status Update:
            - Location: {L1FolderName}/status.txt
            - Content: "Step 2: In Progress"

    2. Analysis Scope:
        2.1 Primary Focus:
            - Source to Target conversion feasibility
            - PL/SQL block identification and analysis

    3. SQL Statement Validation:
        3.1 Keyword Verification:
            - SELECT
            - INSERT
            - UPDATE
            - DELETE
            - MERGE
            - WITH
            - DECLARE
            - BEGIN
            - CREATE
            - ALTER

        3.2 Structure Analysis:
            A. Basic SQL Validation:
                - Statement structure verification
                - Syntax completeness check

            B. CDATA Section Analysis:
                - Internal SQL structure verification
                - Nested query validation

    4. Non-SQL Pattern Detection:
        4.1 Content Types:
            - HTML/JavaScript code
            - Plain text/descriptive content
            - Whitespace/special characters only
            - XML tags/configuration only

    5. Analysis Documentation:
        5.1 Output File:
            - Location: {L1FolderName}/sql_analysis.txt
            
        5.2 Format:
            SQL Analysis Results:
            1. [Query ID]:
              - Type: [query type]
              - Contains: [key features]
              - Source-specific features: [list if any]
              - Conversion needed: [Yes/No]

        5.3 Example:
            SQL Analysis Results:
            1. checkDrawStatus:
              - Type: SELECT query
              - Contains: COUNT function with BETWEEN and dynamic IN clause
              - Source-specific features: None
              - Conversion needed: No

    6. Completion:
        6.1 Status Update:
            - Location: {L1FolderName}/status.txt
            - Content: "Step 2: Completed"
