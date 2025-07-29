# Application Discovery and Oracle Migration Analysis

Reference: Apply environment information from $APP_TOOLS_FOLDER/environmentContext.md

## Overview
This discovery process has been split into two phases for better maintainability and reusability:

1. **Analysis Phase** (`$APP_TOOLS_FOLDER/appAnalysis.md`) - Data collection and analysis
2. **Reporting Phase** (`$APP_TOOLS_FOLDER/appReporting.md`) - HTML report generation

## Quick Start

### Phase 1: Data Analysis
Run the analysis phase to collect and analyze application data:
```bash
# Use $APP_TOOLS_FOLDER/appAnalysis.md prompt to generate analysis data files
# This will create 7 MD files + 5 CSV files in $APPLICATION_FOLDER/discovery/
```

### Phase 2: HTML Report Generation  
After analysis is complete, generate the HTML report:
```bash
# Use $APP_TOOLS_FOLDER/appReporting.md prompt to generate HTML report
# This will create DiscoveryReport-[APPLICATION_NAME].html
```

## File Structure

### Analysis Phase Files (`$APP_TOOLS_FOLDER/appAnalysis.md`)
**Input**: Java source code, MyBatis mappers, configuration files
**Output**: Analysis data files in `$APPLICATION_FOLDER/discovery/`

#### Generated Analysis Files (12 files total):
**Markdown Reports (7 files)**:
1. `ApplicationOverview.md` - Application overview and basic information
2. `TechnicalStack.md` - Technology stack and framework analysis  
3. `ProjectDirectory.md` - Project directory structure
4. `MyBatis.md` - MyBatis configuration analysis
5. `MyBatisDetails.md` - MyBatis detailed information
6. `Oracle.md` - Oracle SQL pattern analysis and complexity assessment
7. `JavaCodeDependency.md` - Java code Oracle dependency analysis

**CSV Data Files (5 files)**:
1. `Mapperlist.csv` - MyBatis Mapper file list (No., FileName, Namespace, SqlCount)
2. `DataSource.csv` - DataSource configuration information  
3. `MapperDataSource.csv` - Mapper and datasource mapping relationship
4. `SampleMapperlist.csv` - Critical/High pattern sample mapper files
5. `SampleOracleSQL.txt` - Sample SQL statements and conversion plans

### Reporting Phase Files (`$APP_TOOLS_FOLDER/appReporting.md`)
**Input**: Analysis data files from Phase 1
**Output**: Professional HTML report

#### Generated Report (1 file):
1. `DiscoveryReport-[APPLICATION_NAME].html` - Comprehensive analysis report

## Key Features

### Analysis Phase Features
- **Comprehensive MyBatis Analysis**: Automatic detection of MyBatis mappers using DTD validation
- **Oracle Pattern Detection**: 50+ Oracle-specific patterns classified by migration complexity
- **Smart Sample Selection**: Intelligent selection of representative SQL samples for testing
- **DataSource Mapping**: Complete mapping of datasources and transformation targets
- **Java Dependency Analysis**: Detection of Oracle-specific Java code dependencies
- **Quality Assessment**: Mapper file quality analysis including empty file detection

### Reporting Phase Features  
- **Professional HTML Report**: Clean, responsive design with modern CSS
- **Executive Summary**: High-level overview for stakeholders
- **Interactive Tables**: Sortable and searchable data tables
- **Transform Test Sets**: Ready-to-use test cases for migration validation
- **Visual Complexity Assessment**: Color-coded complexity indicators
- **Migration Timeline**: Estimated effort and timeline calculations
- **Print-Friendly Format**: Optimized for both screen and print

## Migration Complexity Classification

### Critical Patterns (Architecture Change Required)
- Database Links, PL/SQL Blocks, Oracle Packages
- **Impact**: Requires application architecture changes
- **Timeline**: 5-10 days per pattern type

### High Complexity Patterns (Complex Logic Conversion)  
- Hierarchical Queries, Analytic Functions, MERGE statements
- **Impact**: Complex SQL logic conversion required
- **Timeline**: 2-5 days per pattern type

### Medium Complexity Patterns (Function Mapping)
- Oracle functions (NVL, SUBSTR, TO_DATE, etc.)
- **Impact**: Function-level mapping and testing
- **Timeline**: 0.5-2 days per pattern type

### Low Complexity Patterns (Simple Substitution)
- Data types, basic operators, DUAL table
- **Impact**: Simple find-and-replace operations  
- **Timeline**: 0.1-0.5 days per pattern type

## Transform Test Set Generation

The analysis automatically generates test sets for migration validation:

- **Critical Test Set**: Architecture change verification (manual testing required)
- **High Complexity Test Set**: Logic conversion verification (functional testing)
- **Medium Pattern Test Set**: Bulk function conversion testing (automated testing)

Each test set includes:
- Representative SQL samples
- Expected conversion strategies  
- Test execution priorities
- Validation criteria

## Usage Scenarios

### Scenario 1: Initial Assessment
Use for preliminary migration feasibility assessment:
1. Run analysis phase for complexity evaluation
2. Generate executive summary report
3. Present findings to stakeholders

### Scenario 2: Detailed Migration Planning
Use for comprehensive migration planning:
1. Complete full analysis with all patterns
2. Generate detailed HTML report with test sets
3. Use sample files for proof-of-concept development

### Scenario 3: Migration Validation
Use generated test sets for migration validation:
1. Use Critical/High pattern samples for manual testing
2. Use Medium pattern samples for automated testing  
3. Validate conversion accuracy and performance

## Best Practices

### Analysis Phase Best Practices
- Ensure all environment variables are properly set
- Verify Java source and mapper folder paths are correct
- Run analysis on clean, compiled codebase
- Review generated CSV files for data quality

### Reporting Phase Best Practices  
- Always run analysis phase first
- Verify all required data files exist before generating report
- Test HTML report in multiple browsers
- Customize CSS styling for organization branding if needed

### Migration Planning Best Practices
- Start with Critical and High complexity patterns
- Use generated test sets for validation
- Plan for iterative migration approach
- Consider performance impact of converted SQL

## Troubleshooting

### Common Issues
1. **Missing Analysis Files**: Ensure analysis phase completed successfully
2. **Empty Mapper Lists**: Check JAVA_SOURCE_FOLDER path and MyBatis DTD detection
3. **Incorrect Pattern Counts**: Verify CSV file format and header exclusion
4. **HTML Generation Errors**: Check for special characters in data files

### Error Prevention
- Always use quoted variables in bash scripts: `"$variable"`
- Clean numeric variables before arithmetic: `count=${count:-0}`
- Handle empty files gracefully with default values
- Use proper error handling and validation

## Integration with Other Tools

This discovery process is designed to integrate with:
- **Migration Tools**: Generated test sets can be used with automated migration tools
- **CI/CD Pipelines**: Analysis can be automated as part of build processes  
- **Project Management**: Timeline estimates can be imported into project planning tools
- **Documentation Systems**: HTML reports can be embedded in project documentation

## Support for Multiple DBMS Targets

The analysis supports migration to various target databases:
- **MySQL**: Specific conversion strategies for MySQL syntax
- **PostgreSQL**: PostgreSQL-specific function mappings
- **SQL Server**: SQL Server compatibility considerations
- **Generic**: Database-agnostic conversion approaches

Target-specific recommendations are included in the generated reports based on the `TARGET_DBMS_TYPE` environment variable.

---

## Next Steps

1. **Set Environment Variables**: Configure required environment variables
2. **Run Analysis**: Execute `$APP_TOOLS_FOLDER/appAnalysis.md` to generate data files  
3. **Generate Report**: Execute `$APP_TOOLS_FOLDER/appReporting.md` to create HTML report
4. **Review Results**: Analyze findings and plan migration approach
5. **Execute Migration**: Use generated test sets for validation

For detailed instructions, refer to the individual phase documentation:
- `$APP_TOOLS_FOLDER/appAnalysis.md` - Complete analysis phase instructions
- `$APP_TOOLS_FOLDER/appReporting.md` - Complete reporting phase instructions
