"""
PostgreSQL Metadata Generation Page
"""
import streamlit as st
import subprocess
import os
import re
import html
import pandas as pd


def render_postgresql_meta_page():
    """PostgreSQL metadata generation page"""
    # CSS to forcefully expand full page width
    st.markdown("""
    <style>
    .main .block-container {
        max-width: none !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    .stTextArea > div > div > textarea {
        width: 100% !important;
        max-width: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Place Home button simply at top left
    if st.button("🏠 Home", key="postgresql_meta_home"):
        st.session_state.selected_action = None
        st.rerun()
    
    # Display title in full width
    st.markdown("# 🗄️ PostgreSQL Metadata")
    
    # Tab configuration
    tab1, tab2 = st.tabs(["📊 Generate Metadata", "🔍 Validate Metadata"])
    
    with tab1:
        render_metadata_generation_tab()
    
    with tab2:
        render_metadata_verification_tab()


def render_metadata_generation_tab():
    """Metadata generation tab"""
    st.markdown("## 📊 PostgreSQL Metadata Generation")
    
    # Command Info
    script_path = "$APP_TOOLS_FOLDER/genPostgreSqlMeta.sh"
    expanded_script_path = os.path.expandvars(script_path)
    
    st.info(f"**Execution script:** `{script_path}`")
    st.caption(f"📄 Actual path: {expanded_script_path}")
    
    # Check script existence
    if not os.path.exists(expanded_script_path):
        st.error(f"❌ Script file not found: {expanded_script_path}")
        st.info("💡 Please check environment variable settings or file path.")
        return
    
    # Check running tasks
    if st.session_state.oma_controller.is_any_task_running():
        st.error("❌ Another task is currently running. Please complete or stop the existing task before trying again.")
        return
    
    # Execute button
    if st.button("🚀 Execute", key="run_postgresql_meta", type="primary"):
        execute_postgresql_meta_script(expanded_script_path)
    
    st.caption("Execute script to generate PostgreSQL metadata")


def render_metadata_verification_tab():
    """Metadata verification tab"""
    st.markdown("## 🔍 Metadata Verification")
    
    # Metadata file path
    metadata_file = "$APP_TRANSFORM_FOLDER/oma_metadata.txt"
    expanded_metadata_file = os.path.expandvars(metadata_file)
    
    st.info(f"**Metadata file:** `{metadata_file}`")
    st.caption(f"📄 Actual path: {expanded_metadata_file}")
    
    # Check file existence
    if not os.path.exists(expanded_metadata_file):
        st.error(f"❌ Metadata file not found: {expanded_metadata_file}")
        st.info("💡 Please first generate metadata in the 'Generate Metadata' tab.")
        return
    
    # Load and display metadata
    try:
        metadata_df = load_metadata_file(expanded_metadata_file)
        
        if metadata_df is not None and not metadata_df.empty:
            # Search filter UI
            st.markdown("### 🔍 Search Filters")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Schema filter
                schemas = ['All'] + sorted(metadata_df['table_schema'].unique().tolist())
                selected_schema = st.selectbox("Schema", schemas, key="schema_filter")
            
            with col2:
                # Table name filter
                table_filter = st.text_input("Table Name (partial search)", key="table_filter", 
                                           help="Enter part of table name")
            
            with col3:
                # Column name filter
                column_filter = st.text_input("Column Name (partial search)", key="column_filter",
                                            help="Enter part of column name")
            
            # Apply filters
            filtered_df = apply_metadata_filters(metadata_df, selected_schema, table_filter, column_filter)
            
            # Display results
            st.markdown("### 📋 Search Results")
            st.info(f"Total {len(filtered_df):,} records found.")
            
            if not filtered_df.empty:
                # Display dataframe (height adjusted)
                st.dataframe(
                    filtered_df,
                    use_container_width=True,
                    height=600,
                    column_config={
                        "table_schema": st.column_config.TextColumn("Schema", width="medium"),
                        "table_name": st.column_config.TextColumn("Table Name", width="medium"),
                        "column_name": st.column_config.TextColumn("Column Name", width="medium"),
                        "data_type": st.column_config.TextColumn("Data Type", width="medium"),
                    }
                )
                
                # Download button
                csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 CSV Download",
                    data=csv_data,
                    file_name=f"metadata_filtered_{len(filtered_df)}_records.csv",
                    mime="text/csv",
                    key="download_filtered_metadata"
                )
            else:
                st.warning("No data matches the search criteria.")
        else:
            st.error("Metadata file is empty or in incorrect format.")
            
    except Exception as e:
        st.error(f"❌ Error occurred while loading metadata file: {str(e)}")
        st.info("💡 Please check the metadata file format.")


def load_metadata_file(file_path):
    """Load metadata file and return as DataFrame"""
    try:
        # Read file (pipe separator, 1st row is header, skip 2nd row as separator)
        df = pd.read_csv(file_path, sep='|', encoding='utf-8', header=0, skiprows=[1])
        
        # Clean column names (remove spaces)
        df.columns = df.columns.str.strip()
        
        # Check required columns
        required_columns = ['table_schema', 'table_name', 'column_name', 'data_type']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"Required columns missing: {missing_columns}")
            st.info(f"Current columns: {list(df.columns)}")
            
            # Show first 5 lines of file to check structure
            with open(file_path, 'r', encoding='utf-8') as f:
                first_lines = [f.readline().strip() for _ in range(5)]
            st.info("First 5 lines of file:")
            for i, line in enumerate(first_lines, 1):
                st.text(f"{i}: {line}")
            return None
        
        # Clean data
        df = df.fillna('')  # Change NaN values to empty strings
        df = df.astype(str)  # Convert all columns to string
        
        # Remove spaces from data values as well
        for col in df.columns:
            df[col] = df[col].str.strip()
        
        # Remove empty rows
        df = df[df['table_schema'] != '']
        
        # Check if last line is count info and remove it
        if not df.empty:
            last_row = df.iloc[-1]
            # Remove if last row consists only of numbers or contains "Total:", "Count:" etc
            last_row_text = ' '.join(last_row.values).lower()
            if (last_row_text.isdigit() or 
                'total' in last_row_text or 
                'count' in last_row_text or 
                'records' in last_row_text or
                'items' in last_row_text or
                'rows' in last_row_text):
                df = df.iloc[:-1]  # Remove last row
                st.info(f"Removed last line count info: {last_row_text}")
        
        return df
        
    except pd.errors.EmptyDataError:
        st.error("Metadata file is empty.")
        return None
    except pd.errors.ParserError as e:
        st.error(f"File parsing error: {e}")
        st.info("Please check if the file uses pipe (|) separators.")
        return None
    except Exception as e:
        st.error(f"File load error: {e}")
        return None


def apply_metadata_filters(df, schema_filter, table_filter, column_filter):
    """Apply filters to metadata"""
    filtered_df = df.copy()
    
    # Schema filter
    if schema_filter and schema_filter != 'All':
        filtered_df = filtered_df[filtered_df['table_schema'].str.contains(schema_filter, case=False, na=False)]
    
    # Table name filter
    if table_filter:
        filtered_df = filtered_df[filtered_df['table_name'].str.contains(table_filter, case=False, na=False)]
    
    # Column name filter
    if column_filter:
        filtered_df = filtered_df[filtered_df['column_name'].str.contains(column_filter, case=False, na=False)]
    
    return filtered_df


def clean_ansi_codes(text):
    """Remove ANSI color codes, control characters, and HTML tags"""
    # Remove ANSI color codes (e.g., [0;34m, [1;32m etc)
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    
    # Remove other ANSI escape sequences
    text = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
    
    # Remove cursor control sequences ([?25l, [?25h etc)
    text = re.sub(r'\x1b\[\?[0-9]+[lh]', '', text)
    
    # Remove control characters like backspace, carriage return etc
    text = re.sub(r'[\x08\x0c\x0e\x0f\r]', '', text)
    
    # Remove HTML tags (</textarea>, </div> etc)
    text = re.sub(r'</?(textarea|div)[^>]*>', '', text, flags=re.IGNORECASE)
    
    # Remove other HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # HTML entity decoding (convert &lt;, &gt; etc to <, >)
    import html as html_module
    text = html_module.unescape(text)
    
    # Consolidate consecutive spaces into one
    text = re.sub(r' +', ' ', text)
    
    # Clean up empty lines (reduce 3+ consecutive line breaks to 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def execute_postgresql_meta_script(script_path):
    """Execute PostgreSQL metadata script and display results"""
    st.markdown("## 📊 Execute Result")
    
    # Display progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("🔄 Executing script...")
        progress_bar.progress(25)
        
        # Execute script
        result = subprocess.run(
            f"bash '{script_path}'",
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout
            cwd=os.path.dirname(script_path)
        )
        
        progress_bar.progress(75)
        status_text.text("📝 Processing results...")
        
        # Display results
        progress_bar.progress(100)
        status_text.text("✅ Complete!")
        
        # Remove progress bar
        progress_bar.empty()
        status_text.empty()
        
        # Check success/failure status
        if result.returncode == 0:
            st.success("✅ PostgreSQL Metadata Create Complete!")
            
            # Display Execute Result with appropriate width
            if result.stdout.strip():
                st.markdown("---")
                st.markdown("### 📄 Execute Result")
                
                # Remove ANSI codes and handle HTML escaping
                clean_stdout = clean_ansi_codes(result.stdout)
                escaped_stdout = html.escape(clean_stdout)
                
                # Write HTML structure in one line to prevent line break issues (light theme)
                st.markdown(f'<div style="width: 85%; margin: 0 auto; padding: 0 1rem;"><textarea readonly style="width: 100%; height: 600px; background-color: #f8f9fa; color: #212529; border: 1px solid #dee2e6; border-radius: 0.5rem; padding: 1rem; font-family: \'Source Code Pro\', monospace; font-size: 14px; line-height: 1.4; resize: vertical; box-sizing: border-box;">{escaped_stdout}</textarea></div>', unsafe_allow_html=True)
            
            # If there are warning messages
            if result.stderr.strip():
                st.markdown("### ⚠️ Warning/Info Messages")
                
                # Remove ANSI codes and handle HTML escaping
                clean_stderr = clean_ansi_codes(result.stderr)
                escaped_stderr = html.escape(clean_stderr)
                
                st.markdown(f'<div style="width: 85%; margin: 0 auto; padding: 0 1rem;"><textarea readonly style="width: 100%; height: 200px; background-color: #fff3cd; color: #856404; border: 1px solid #ffeaa7; border-radius: 0.5rem; padding: 1rem; font-family: \'Source Code Pro\', monospace; font-size: 14px; line-height: 1.4; resize: vertical; box-sizing: border-box;">{escaped_stderr}</textarea></div>', unsafe_allow_html=True)
                
        else:
            st.error(f"❌ Script execution failed (exit code: {result.returncode})")
            
            # Error messages
            if result.stderr.strip():
                st.markdown("### 🚨 Error Messages")
                
                # Remove ANSI codes and handle HTML escaping
                clean_stderr = clean_ansi_codes(result.stderr)
                escaped_stderr = html.escape(clean_stderr)
                
                st.markdown(f'<div style="width: 85%; margin: 0 auto; padding: 0 1rem;"><textarea readonly style="width: 100%; height: 400px; background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; border-radius: 0.5rem; padding: 1rem; font-family: \'Source Code Pro\', monospace; font-size: 14px; line-height: 1.4; resize: vertical; box-sizing: border-box;">{escaped_stderr}</textarea></div>', unsafe_allow_html=True)
            
            # Also display standard output
            if result.stdout.strip():
                st.markdown("### 📄 Output Content")
                
                # Remove ANSI codes and handle HTML escaping
                clean_stdout = clean_ansi_codes(result.stdout)
                escaped_stdout = html.escape(clean_stdout)
                
                st.markdown(f'<div style="width: 85%; margin: 0 auto; padding: 0 1rem;"><textarea readonly style="width: 100%; height: 300px; background-color: #f8f9fa; color: #212529; border: 1px solid #dee2e6; border-radius: 0.5rem; padding: 1rem; font-family: \'Source Code Pro\', monospace; font-size: 14px; line-height: 1.4; resize: vertical; box-sizing: border-box;">{escaped_stdout}</textarea></div>', unsafe_allow_html=True)
        
    except subprocess.TimeoutExpired:
        progress_bar.empty()
        status_text.empty()
        st.error("❌ Script execution timeout exceeded (60 seconds)")
        st.info("💡 The script is taking too long to execute. Please check manually.")
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ Error occurred during script execution: {str(e)}")
        st.info("💡 Please check script file permissions or environment setup.")
