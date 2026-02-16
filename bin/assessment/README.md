# Database Assessment Agent

Runs DMS Schema Conversion assessment and generates HTML discovery report using Amazon Bedrock.

## Usage

```bash
# Load environment
cd /workshop/sample-oracle-modernization-accelerator/bin
source oma_env_demo.sh

# Run assessment agent
cd assessment/database
python3.11 assessment_agent.py
```

## What It Does

1. Runs DMS SC assessment on configured schema
2. Exports PDF and Excel reports to S3
3. Downloads reports from S3
4. Analyzes PDF using Bedrock Claude (vision)
5. Generates HTML discovery report

## Output

- **HTML Report**: `/workshop/dms-sc-output/database_analysis_report.html`
- **PDF Report**: `/workshop/dms-sc-output/Assessment_Report_*.pdf`
- **Excel Report**: `/workshop/dms-sc-output/Assessment_Report_*.xlsx`

## Requirements

- Environment variables from `oma.properties`
- DMS Migration Project configured
- Bedrock access (Claude 3.5 Sonnet)
- Python 3.11+, boto3
