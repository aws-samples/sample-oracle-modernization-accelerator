import streamlit as st
import pandas as pd
import os
import subprocess
import time

def render_parameter_config_page():
    """Parameter configuration page"""
    st.markdown('<div class="main-header"><h1>⚙️ Parameter Configuration</h1></div>', unsafe_allow_html=True)
    
    # Check TEST_FOLDER environment variable
    test_folder = os.environ.get('TEST_FOLDER')
    if not test_folder:
        st.error("❌ TEST_FOLDER environment variable is not set.")
        return
    
    if not os.path.exists(test_folder):
        st.error(f"❌ Directory does not exist: {test_folder}")
        return
    
    # bulk_prepare.sh File Path
    oma_base_dir = os.environ.get('OMA_BASE_DIR')
    if not oma_base_dir:
        st.error("❌ OMA_BASE_DIR environment variable is not set.")
        return
    
    bulk_prepare_script = os.path.join(oma_base_dir, "bin", "test", "bulk_prepare.sh")
    parameters_file = os.path.join(test_folder, "parameters.properties")
    
    st.info(f"📁 Task Directory: {test_folder}")
    
    # Parameter configuration execution button
    if st.button("🚀 Execute Parameter Configuration", type="primary", use_container_width=True):
        if not os.path.exists(bulk_prepare_script):
            st.error(f"❌ bulk_prepare.sh file does not exist: {bulk_prepare_script}")
            return
        
        # Check SOURCE_SQL_MAPPER_FOLDER environment variable
        source_sql_mapper_folder = os.environ.get('SOURCE_SQL_MAPPER_FOLDER')
        if not source_sql_mapper_folder:
            st.error("❌ SOURCE_SQL_MAPPER_FOLDER environment variable is not set.")
            return
        
        # Check APP_TOOLS_FOLDER environment variable
        app_tools_folder = os.environ.get('APP_TOOLS_FOLDER')
        if not app_tools_folder:
            st.error("❌ APP_TOOLS_FOLDER environment variable is not set.")
            return
        
        # Execution log container
        log_container = st.empty()
        
        try:
            with st.spinner("Configuring parameters..."):
                # Execute bulk_prepare.sh in APP_TOOLS_FOLDER/../test
                test_dir = os.path.join(app_tools_folder, "..", "test")
                command = f"{bulk_prepare_script} {source_sql_mapper_folder}"
                process = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=test_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1
                )
                
                # Real-time log output
                logs = []
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        logs.append(line.rstrip())
                        # Display only recent 20 lines
                        recent_logs = logs[-20:] if len(logs) > 20 else logs
                        log_container.code('\n'.join(recent_logs))
                
                # Wait for process completion
                return_code = process.wait()
                
                # Check if parameters.properties file was created in TEST_FOLDER
                if os.path.exists(parameters_file):
                    st.success("✅ Parameter configuration completed!")
                    # Refresh page since parameters.properties file was created
                    time.sleep(1)  # Wait for file creation completion
                    st.rerun()
                else:
                    if return_code == 0:
                        st.warning("⚠️ Script succeeded but parameters.properties file not found.")
                    else:
                        st.error(f"❌ Parameter configuration execution failed (exit code: {return_code})")
                    
        except Exception as e:
            st.error(f"❌ Error occurred during execution: {e}")
    
    st.markdown("---")
    
    # Display and edit parameters.properties file
    render_parameters_editor(parameters_file)

def render_parameters_editor(parameters_file):
    """parameters.properties file editor"""
    st.subheader("📄 parameters.properties")
    
    if not os.path.exists(parameters_file):
        st.warning(f"⚠️ parameters.properties file does not exist.")
        st.info("Please execute parameter configuration first.")
        return
    
    try:
        # Convert properties file to DataFrame
        properties_data = []
        
        with open(parameters_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        properties_data.append({
                            'Key': key.strip(),
                            'Value': value.strip(),
                            'Line': line_num
                        })
                    else:
                        # Also display lines without =
                        properties_data.append({
                            'Key': line,
                            'Value': '',
                            'Line': line_num
                        })
        
        if not properties_data:
            st.info("📝 No configuration items found.")
            return
        
        df = pd.DataFrame(properties_data)
        
        # File Info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Configuration Items", len(df))
        with col2:
            file_size = os.path.getsize(parameters_file)
            st.metric("📁 File Size", f"{file_size:,} bytes")
        with col3:
            mtime = os.path.getmtime(parameters_file)
            st.metric("🕒 Modify Time", time.strftime("%H:%M:%S", time.localtime(mtime)))
        
        # Search functionality
        search_term = st.text_input("🔍 Search", placeholder="Search by key or value")
        
        # Search filtering
        filtered_df = df.copy()
        if search_term:
            mask = (df['Key'].str.contains(search_term, case=False, na=False) | 
                   df['Value'].str.contains(search_term, case=False, na=False))
            filtered_df = df[mask]
            st.info(f"🔍 Search results: {len(filtered_df)} items")
        
        # Editable table (excluding Line column)
        edit_df = filtered_df[['Key', 'Value']].copy()
        
        edited_df = st.data_editor(
            edit_df,
            use_container_width=True,
            num_rows="dynamic",
            key="parameters_editor"
        )
        
        # Save button
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("💾 Save", type="primary"):
                try:
                    # Create backup
                    backup_path = f"{parameters_file}.backup"
                    import shutil
                    shutil.copy2(parameters_file, backup_path)
                    
                    # Write new properties file
                    with open(parameters_file, 'w', encoding='utf-8') as f:
                        f.write("# Parameters Configuration\n")
                        f.write(f"# Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        
                        for _, row in edited_df.iterrows():
                            if row['Key'] and not pd.isna(row['Key']):
                                if row['Value'] and not pd.isna(row['Value']):
                                    f.write(f"{row['Key']}={row['Value']}\n")
                                else:
                                    f.write(f"{row['Key']}=\n")
                    
                    st.success("✅ parameters.properties saved successfully!")
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Save failed: {e}")
        
        with col2:
            if st.button("🔄 Refresh"):
                st.rerun()
        
        with col3:
            st.caption(f"📁 {parameters_file}")
        
        # Original file content preview
        with st.expander("📄 Original File Content", expanded=False):
            with open(parameters_file, 'r', encoding='utf-8') as f:
                content = f.read()
            st.code(content, language='properties')
            
    except Exception as e:
        st.error(f"❌ File read error: {e}")
        
        # Restore from backup
        backup_path = f"{parameters_file}.backup"
        if os.path.exists(backup_path):
            if st.button("🔧 Restore from Backup"):
                try:
                    import shutil
                    shutil.copy2(backup_path, parameters_file)
                    st.success("✅ Restored from backup successfully.")
                    st.rerun()
                except Exception as restore_e:
                    st.error(f"❌ Restore failed: {restore_e}")
