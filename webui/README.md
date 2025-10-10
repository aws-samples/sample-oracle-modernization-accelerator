# OMA Streamlit Web Application

Oracle Migration Assistant (OMA) shell scripts converted to a Streamlit web application.

## Key Features

### 🏠 Environment Setup
- Environment variable configuration and verification
- Project initialization

### 📊 Application Analysis
- Java source code and MyBatis Mapper file analysis
- Analysis report generation and SQL transformation target extraction
- PostgreSQL metadata generation

### 🔄 Application Transformation
- Sample SQL transformation
- Full SQL transformation
- Transformation testing and result modification
- XML Merge operations

### 🧪 SQL Testing
- XML List generation
- SQL Unit Test execution

### 📋 Transformation Reports
- Transformation work report generation
- Java Source transformation

## How to Run

### 1. Simple Execution (Recommended)
```bash
./run_oma_app.sh
```

### 2. Manual Execution
```bash
# Install required packages
pip install -r requirements.txt

# Set environment variables (if needed)
export OMA_BASE_DIR="$HOME/workspace/oma"

# Run Streamlit application
streamlit run oma_streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

## Access Method

Once the application starts, access it in your browser at:
- Local: http://localhost:8501
- Remote: http://[server-ip]:8501

## Key Features

### Real-time Log Output
- Execution logs for each task are displayed in real-time in the web browser
- Visual confirmation of task progress

### Task Interruption Feature
- Use the "Stop Current Task" button in the sidebar to interrupt running tasks

### Tab-based Interface
- Each work stage is organized in tabs for easy navigation

### Environment Status Display
- Check current environment configuration status in the sidebar

## Prerequisites

1. **Python 3.7 or higher**
2. **OMA Environment Setup**
   - Set `OMA_BASE_DIR` environment variable
   - Required OMA scripts must be in correct locations
3. **Network Access**
   - For tasks requiring database connections

## Environment Variables

- `OMA_BASE_DIR`: OMA installation directory (default: ~/workspace/oma)
- `APPLICATION_NAME`: Current project name (automatically set after environment setup)

## Troubleshooting

### Port Conflicts
To use a different port:
```bash
streamlit run oma_streamlit_app.py --server.port 8502
```

### Permission Issues
Check script execution permissions:
```bash
chmod +x run_oma_app.sh
```

### Environment Variable Issues
If OMA environment is not properly configured, reset the environment in the "Environment Setup" tab of the web application.

## Differences from Original Shell Scripts

1. **Web Interface**: Runs in web browser instead of terminal
2. **Real-time Logs**: Logs displayed in real-time on web
3. **Visual Feedback**: Progress indicators and status icons
4. **Task Interruption**: Ability to stop running tasks from web interface
5. **Tab-based Navigation**: Easy access to each stage

## Support

If you encounter issues, check the following:
1. Verify OMA environment setup is correct
2. Ensure required script files exist
3. Check network connection status (for DB-related tasks)
