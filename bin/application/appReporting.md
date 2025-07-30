# Application Analysis HTML Report Generation Prompt

Reference: Apply environment information from $APP_TOOLS_FOLDER/environmentContext.md

## Objective
Generate comprehensive HTML report by integrating analysis result files generated from appAnalysis.md

## Prerequisites
- Analysis data files must be generated first using `$APP_TOOLS_FOLDER/appAnalysis.md`
- Required analysis files must exist in `$APPLICATION_FOLDER/discovery/` directory

## Environment Information Verification

**Environment Variable Verification**:
```bash
echo "=== Environment Variable Verification ==="
echo "APPLICATION_FOLDER: $APPLICATION_FOLDER"
echo "TARGET_DBMS_TYPE: $TARGET_DBMS_TYPE"
echo "TRANSFORM_JNDI: $TRANSFORM_JNDI"
```

**Required Analysis Files Check**:
```bash
echo "=== Required Analysis Files Check ==="
required_files=(
    "ApplicationOverview.md"
    "TechnicalStack.md"
    "Oracle.md" 
    "Mapperlist.csv"
    "DataSource.csv"
    "SampleMapperlist.csv"
)

all_files_exist=true
for file in "${required_files[@]}"; do
    if [ -f "$APPLICATION_FOLDER/discovery/$file" ]; then
        echo "✓ $file exists"
    else
        echo "✗ $file missing - Run $APP_TOOLS_FOLDER/appAnalysis.md first"
        all_files_exist=false
    fi
done

if [ "$all_files_exist" = false ]; then
    echo "❌ Missing required analysis files - Cannot generate report"
    exit 1
fi
```

---

# HTML Report Generation Phase

Generate comprehensive HTML report by integrating analysis result files (7 MD files + 5 CSV files)

## HTML Generation and Combination by Work Unit

### Step 1: Basic Information Collection and HTML Header Generation
**Work Instructions**:
1. **Application Name Extraction**: Extract application name from `ApplicationOverview.md`
2. **Analysis Date**: Set to current date
3. **HTML Header Generation**: Include CSS styles from `$APP_TOOLS_FOLDER/discovery-details/appDiscoveryTemplate.html`
4. **Basic Variable Setup**: APPLICATION_NAME, ANALYSIS_DATE, TARGET_DBMS_TYPE

**Output**: `/tmp/html_header.html`

### Step 2: Executive Summary Section Generation
**Work Instructions**:
1. Generate Executive Summary by integrating all analysis results
2. Generate migration timeline
3. Generate priority recommendation list
4. Present risk assessment and response plans

**Key Metrics to Include**:
- Total Mapper Files: `tail -n +2 $APPLICATION_FOLDER/discovery/Mapperlist.csv | wc -l`
- Valid Mapper Files: `awk -F',' 'NR>1 && $4>0 {count++} END {print count}' $APPLICATION_FOLDER/discovery/Mapperlist.csv`
- Oracle Pattern Complexity Score from Oracle.md
- Migration Complexity Level determination
- Estimated Timeline calculation

**Output**: `/tmp/html_summary.html`

### Step 3: Application Overview Section Generation
**Work Instructions**:
1. Convert **ApplicationOverview.md** content to HTML
2. Convert **TechnicalStack.md** content to technology stack cards
3. Convert **ProjectDirectory.md** content to directory tree format
4. Replace template variables like `[APPLICATION_NAME]`, `[BUILD_TOOL]`, `[JAVA_VERSION]`

**Output**: `/tmp/html_overview.html`

### Step 4: DataSource Information Section Generation
**Work Instructions**:
1. Convert **DataSource.csv** file to HTML table
2. Convert **MapperDataSource.csv** file to mapping relationship table
3. Highlight Transform='Yes' items with special styling
4. Generate statistics by JNDI
5. Show Transform target configuration based on `$TRANSFORM_JNDI`

**Transform Highlighting Rules**:
- Transform='Yes': Green background with checkmark icon
- Transform='No': Gray background
- Transform='Unknown': Yellow background with warning icon

**Output**: `/tmp/html_datasource.html`

### Step 5: MyBatis Analysis Section Generation
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

5. **Important Calculations**:
   - Total Mapper Files: `tail -n +2 Mapperlist.csv | wc -l` (exclude header)
   - Valid Mapper Files: `awk -F',' 'NR>1 && $4>0 {count++} END {print count}' Mapperlist.csv`
   - Empty Mapper Files: `grep ",0$" Mapperlist.csv | wc -l`
   - Quality Ratio: `(Valid Files / Total Files) * 100`

**Output**: `/tmp/html_mybatis.html`

### Step 6: Oracle Pattern Analysis Section Generation (Core)
**Work Instructions**:
1. Extract pattern statistics from **Oracle.md** file
2. Classify patterns by complexity (Critical/High/Medium/Low)
3. Generate tables for each complexity level:
   - `[CRITICAL_PATTERNS_TABLE]`
   - `[HIGH_PATTERNS_TABLE]`
   - `[MEDIUM_PATTERNS_TABLE]`
   - `[LOW_PATTERNS_TABLE]`
4. Calculate complexity score and determine migration level
5. Calculate expected timeline based on complexity
6. Generate migration complexity visualization

**Complexity Level Determination**:
- **Critical (Score 1000+)**: Very High Risk - Architecture redesign required
- **High (Score 500-999)**: High Risk - Complex logic conversion required
- **Medium (Score 200-499)**: Medium Risk - Function mapping required
- **Low (Score 50-199)**: Low Risk - Simple substitution
- **Very Low (Score <50)**: Very Low Risk - Minimal changes

**Timeline Estimation Formula**:
- Critical patterns: 5-10 days per pattern type
- High patterns: 2-5 days per pattern type
- Medium patterns: 0.5-2 days per pattern type
- Low patterns: 0.1-0.5 days per pattern type

**Output**: `/tmp/html_oracle.html`

### Step 7: Transform Test Set and Sample SQL Section Generation
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

3. **HTML Structure Generation**:
```html
<div class="section">
    <h2>🧪 Transform Test Set and Sample SQL Analysis</h2>
    <p>Representative sample files and actual SQL statement analysis for Oracle → [TARGET_DBMS_TYPE] conversion function testing</p>
    
    <!-- Transform Test Set Overview -->
    <div class="summary-box">
        <h3>📋 Transform Test Set Overview</h3>
        <div class="grid">
            <div class="card">
                <h4>Critical Tests</h4>
                <p style="font-size: 1.5em; color: #dc3545; font-weight: bold;">[CRITICAL_TEST_COUNT]</p>
                <p>Architecture change verification</p>
            </div>
            <div class="card">
                <h4>High Complexity Tests</h4>
                <p style="font-size: 1.5em; color: #fd7e14; font-weight: bold;">[HIGH_TEST_COUNT]</p>
                <p>Logic conversion verification</p>
            </div>
            <div class="card">
                <h4>Medium Bulk Tests</h4>
                <p style="font-size: 1.5em; color: #0066cc; font-weight: bold;">[MEDIUM_TEST_COUNT]</p>
                <p>Function conversion verification</p>
            </div>
            <div class="card">
                <h4>Total Test Files</h4>
                <p style="font-size: 1.5em; color: #28a745; font-weight: bold;">[TOTAL_TEST_FILES]</p>
                <p>Transform verification targets</p>
            </div>
        </div>
    </div>
    
    <!-- Critical Pattern Test Set -->
    <div class="critical-box">
        <h3>🚨 Critical Pattern Transform Test Set</h3>
        <p>Conversion tests for patterns requiring architecture changes - Manual verification required</p>
        <table class="pattern-table">
            <thead>
                <tr>
                    <th>Test File</th>
                    <th>Pattern Type</th>
                    <th>Pattern Count</th>
                    <th>SQL Preview</th>
                    <th>Transform Strategy</th>
                    <th>Test Priority</th>
                </tr>
            </thead>
            <tbody>
                [CRITICAL_TRANSFORM_TESTSET]
            </tbody>
        </table>
    </div>

    <!-- High Complexity Pattern Test Set -->
    <div class="warning-box">
        <h3>⚠️ High Complexity Pattern Transform Test Set</h3>
        <p>Conversion tests for patterns requiring complex logic conversion - Function verification required</p>
        <table class="pattern-table">
            <thead>
                <tr>
                    <th>Test File</th>
                    <th>Pattern Type</th>
                    <th>Pattern Count</th>
                    <th>SQL Preview</th>
                    <th>Transform Strategy</th>
                    <th>Test Priority</th>
                </tr>
            </thead>
            <tbody>
                [HIGH_TRANSFORM_TESTSET]
            </tbody>
        </table>
    </div>

    <!-- Medium Pattern Bulk Test Set -->
    <div class="summary-box">
        <h3>📊 Medium Pattern Bulk Transform Test Set</h3>
        <p>Bulk conversion tests for high-frequency Oracle functions - Performance and accuracy verification</p>
        <table class="pattern-table">
            <thead>
                <tr>
                    <th>Test File</th>
                    <th>Pattern Type</th>
                    <th>Usage Rank</th>
                    <th>Total Usage</th>
                    <th>Transform Method</th>
                    <th>Test Type</th>
                </tr>
            </thead>
            <tbody>
                [MEDIUM_TRANSFORM_TESTSET]
            </tbody>
        </table>
    </div>

    <!-- Transform Test Guide -->
    <div class="warning-box">
        <h3>🔧 Transform Test Execution Guide</h3>
        <div class="grid">
            <div class="card">
                <h4>Phase 1: Critical Tests</h4>
                <ul>
                    <li>Database Links → API integration test</li>
                    <li>PL/SQL Blocks → Java logic conversion test</li>
                    <li>Manual verification and architecture review</li>
                </ul>
            </div>
            <div class="card">
                <h4>Phase 2: High Complexity Tests</h4>
                <ul>
                    <li>CONNECT BY → Recursive CTE conversion</li>
                    <li>ROW_NUMBER → Window Function conversion</li>
                    <li>Functional equivalence verification</li>
                </ul>
            </div>
            <div class="card">
                <h4>Phase 3: Medium Bulk Tests</h4>
                <ul>
                    <li>NVL, SUBSTR, REPLACE function conversion</li>
                    <li>Large data performance testing</li>
                    <li>Automated regression testing</li>
                </ul>
            </div>
            <div class="card">
                <h4>Phase 4: Integration Tests</h4>
                <ul>
                    <li>Full application integration testing</li>
                    <li>Performance benchmark comparison</li>
                    <li>Production environment verification</li>
                </ul>
            </div>
        </div>
    </div>
</div>
```

4. **SQL Sample and Conversion Example Display**:
   - **Important**: Use `<div class="sql-sample">` or `<div class="transform-example">` class for all SQL statements and conversion examples
   - Convert `\n` to actual line breaks when generating HTML for proper line break display
   - Apply `max-height: 300px` for long SQL statements to enable scrolling
   - Use syntax highlighting for SQL code blocks

**Output**: `/tmp/html_transform_testset.html`

### Step 8: Java Dependency Analysis Section Generation
**Work Instructions**:
1. Convert **JavaCodeDependency.md** content to HTML
2. Generate Oracle-specific code usage status table
3. Classify and visualize by dependency level
4. Present recommendations and alternatives
5. **Conversion Plan and Example Display**:
   - **Important**: Use `<div class="transform-example">` class for all code examples and conversion plans
   - Convert `\n` to actual line breaks when generating HTML for proper line break display
   - Use `<div class="code-block">` class for code blocks
   - Apply syntax highlighting for Java code

**Output**: `/tmp/html_java.html`

### Step 9: Final HTML Report Combination
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
3. Validate HTML structure
4. Generate final file with proper encoding

**Final Output**: `$APPLICATION_FOLDER/DiscoveryReport-[APPLICATION_NAME].html`

### Step 10: Temporary File Cleanup
**Work Instructions**:
```bash
# Clean up temporary HTML files
rm -f /tmp/html_*.html
echo "✅ HTML Report generated successfully"
echo "📄 Report location: $APPLICATION_FOLDER/DiscoveryReport-[APPLICATION_NAME].html"
```

---

## Variable Substitution List

### Basic Information Variables
- `[APPLICATION_NAME]`: Application name extracted from ApplicationOverview.md
- `[ANALYSIS_DATE]`: Current analysis date
- `[TARGET_DBMS_TYPE]`: Target DBMS type from environment variable

### Mapper Statistics Variables
- `[TOTAL_MAPPER_FILES]`: Total mapper file count (**Important**: Calculate excluding headers with `tail -n +2 Mapperlist.csv | wc -l`)
- `[VALID_MAPPER_FILES]`: Valid SQL Mapper file count (files with SqlCount > 0)
- `[EMPTY_MAPPER_FILES]`: Empty Mapper file count (files with SqlCount = 0)
- `[MAPPER_QUALITY_RATIO]`: Mapper quality index (valid files/total files*100)
- `[EMPTY_MAPPER_FILES_TABLE]`: Empty Mapper file detail table

### Oracle Pattern Variables
- `[MIGRATION_COMPLEXITY_LEVEL]`: Migration complexity level (Critical/High/Medium/Low)
- `[ESTIMATED_TIMELINE]`: Expected timeline in days/weeks
- `[COMPLEXITY_SCORE]`: Overall complexity score
- `[CRITICAL_PATTERNS_TOTAL]`: Total Critical pattern count
- `[HIGH_PATTERNS_TOTAL]`: Total High pattern count
- `[MEDIUM_PATTERNS_TOTAL]`: Total Medium pattern count
- `[LOW_PATTERNS_TOTAL]`: Total Low pattern count
- `[CRITICAL_PATTERNS_TABLE]`: Critical patterns detail table
- `[HIGH_PATTERNS_TABLE]`: High patterns detail table
- `[MEDIUM_PATTERNS_TABLE]`: Medium patterns detail table
- `[LOW_PATTERNS_TABLE]`: Low patterns detail table

### Transform Test Set Variables
- `[CRITICAL_TEST_COUNT]`: Critical pattern test file count (1 per pattern type)
- `[HIGH_TEST_COUNT]`: High pattern test file count (1 per pattern type)
- `[MEDIUM_TEST_COUNT]`: Medium pattern test file count (1 per pattern type)
- `[TOTAL_TEST_FILES]`: Total Transform test file count
- `[CRITICAL_TRANSFORM_TESTSET]`: Critical pattern Transform test set table
- `[HIGH_TRANSFORM_TESTSET]`: High pattern Transform test set table
- `[MEDIUM_TRANSFORM_TESTSET]`: Medium pattern Transform test set table

### DataSource Variables
- `[DATASOURCE_COUNT]`: Total datasource count
- `[TRANSFORM_DATASOURCE_COUNT]`: Transform target datasource count
- `[JNDI_DATASOURCE_TABLE]`: JNDI datasource detail table
- `[DIRECT_DATASOURCE_TABLE]`: Direct datasource detail table

---

## CSS Styling Guidelines

### Required CSS Classes
```css
.critical-box { border-left: 5px solid #dc3545; background: #fff5f5; }
.warning-box { border-left: 5px solid #fd7e14; background: #fff8f0; }
.summary-box { border-left: 5px solid #0066cc; background: #f0f8ff; }
.success-box { border-left: 5px solid #28a745; background: #f0fff0; }

.sql-sample { 
    background: #f8f9fa; 
    border: 1px solid #dee2e6; 
    padding: 15px; 
    border-radius: 5px; 
    font-family: 'Courier New', monospace; 
    white-space: pre-wrap; 
    max-height: 300px; 
    overflow-y: auto; 
}

.transform-example { 
    background: #e7f3ff; 
    border: 1px solid #b3d9ff; 
    padding: 15px; 
    border-radius: 5px; 
    font-family: 'Courier New', monospace; 
    white-space: pre-wrap; 
}

.code-block { 
    background: #2d3748; 
    color: #e2e8f0; 
    padding: 15px; 
    border-radius: 5px; 
    font-family: 'Courier New', monospace; 
    white-space: pre-wrap; 
    overflow-x: auto; 
}

.pattern-table { 
    width: 100%; 
    border-collapse: collapse; 
    margin: 15px 0; 
}

.pattern-table th, .pattern-table td { 
    border: 1px solid #dee2e6; 
    padding: 8px 12px; 
    text-align: left; 
}

.pattern-table th { 
    background: #f8f9fa; 
    font-weight: bold; 
}

.metric { text-align: center; }
.metric-value { 
    display: block; 
    font-size: 2em; 
    font-weight: bold; 
    color: #0066cc; 
}
.metric-label { 
    display: block; 
    font-size: 0.9em; 
    color: #6c757d; 
}

.grid { 
    display: grid; 
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
    gap: 20px; 
    margin: 20px 0; 
}

.card { 
    background: white; 
    border: 1px solid #dee2e6; 
    border-radius: 8px; 
    padding: 20px; 
    box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
}
```

---

## Error Handling and Validation

### File Existence Validation
```bash
# Validate each required file before processing
validate_file() {
    local file_path="$1"
    local file_desc="$2"
    
    if [ ! -f "$file_path" ]; then
        echo "❌ Error: $file_desc not found at $file_path"
        return 1
    fi
    
    if [ ! -s "$file_path" ]; then
        echo "⚠️ Warning: $file_desc is empty at $file_path"
        return 2
    fi
    
    echo "✅ $file_desc validated"
    return 0
}
```

### Data Processing Safety Rules
1. **Variable Handling (Critical for avoiding bash errors)**:
   ```bash
   # Always wrap variables in quotes
   if [ "$count" -gt 0 ]; then
   
   # Clean numeric variables before use
   count=$(echo "$count" | tr -d '\n' | tr -d ' ')
   count=${count:-0}
   
   # Safe file processing
   find "$JAVA_SOURCE_FOLDER" -name "*.xml" -exec grep -l "pattern" {} \; 2>/dev/null
   ```

2. **CSV Processing Safety**:
   ```bash
   # Always exclude headers when counting
   total_mappers=$(tail -n +2 "$csv_file" | wc -l)
   
   # Safe field extraction
   awk -F',' 'NR>1 && $4>0 {count++} END {print count+0}' "$csv_file"
   ```

3. **HTML Generation Safety**:
   ```bash
   # Escape HTML special characters
   escaped_content=$(echo "$content" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')
   
   # Handle line breaks properly
   html_content=$(echo "$content" | sed 's/$/\\n/g' | tr -d '\n')
   ```

---

## Report Quality Assurance

### Final Report Validation Checklist
- [ ] All variable substitutions completed
- [ ] No broken HTML tags or structure
- [ ] All CSS classes properly applied
- [ ] SQL samples properly formatted with line breaks
- [ ] All tables have proper headers and data
- [ ] Responsive design works on mobile devices
- [ ] File encoding is UTF-8
- [ ] Report opens properly in web browsers
- [ ] All links and navigation work correctly
- [ ] Print-friendly formatting applied

### Performance Considerations
- Optimize large tables with pagination or scrolling
- Compress CSS and minimize HTML where possible
- Use efficient data processing for large datasets
- Implement progress indicators for long-running operations

---

## Usage Instructions

1. **Prerequisites**: Run `$APP_TOOLS_FOLDER/appAnalysis.md` first to generate required data files
2. **Environment Setup**: Ensure all environment variables are properly set
3. **Execution**: Run this prompt to generate HTML report
4. **Output**: Professional HTML report will be generated at `$APPLICATION_FOLDER/DiscoveryReport-[APPLICATION_NAME].html`

### Integration with Analysis Phase
This reporting phase is designed to work seamlessly with the analysis phase:
- Reads all data files generated by `$APP_TOOLS_FOLDER/appAnalysis.md`
- Maintains consistency in data interpretation
- Provides comprehensive visualization of analysis results
- Generates actionable insights for migration planning

**Final Result**: Professional and visually excellent Oracle migration analysis report ready for stakeholder presentation and migration planning.
