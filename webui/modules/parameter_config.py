import streamlit as st
import pandas as pd
import os
import subprocess
import time

def render_parameter_config_page():
    """Parameter Configuration Page"""
    st.markdown('<div class="main-header"><h1>⚙️ Parameter Configuration</h1></div>', unsafe_allow_html=True)
    
    # Check TEST_FOLDER environment variable
    test_folder = os.environ.get('TEST_FOLDER')
    if not test_folder:
        st.error("❌ TEST_FOLDER environment variable is not set.")
        return
    
    if not os.path.exists(test_folder):
        st.error(f"❌ Directory does not exist: {test_folder}")
        return
    
    # bulk_prepare.sh file path
    oma_base_dir = os.environ.get('OMA_BASE_DIR')
    if not oma_base_dir:
        st.error("❌ OMA_BASE_DIR environment variable is not set.")
        return
    
    bulk_prepare_script = os.path.join(oma_base_dir, "bin", "test", "bulk_prepare.sh")
    parameters_file = os.path.join(test_folder, "parameters.properties")
    
    st.info(f"📁 Working Directory: {test_folder}")
    
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
            with st.spinner("Report Item..."):
                # APP_TOOLS_FOLDER/../testText bulk_prepare.sh Execute
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
                
                # Report Item
                logs = []
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        logs.append(line.rstrip())
                        # Item 20Text display
                        recent_logs = logs[-20:] if len(logs) > 20 else logs
                        log_container.code('\n'.join(recent_logs))
                
                # Item Complete Item
                return_code = process.wait()
                
                # TEST_FOLDERText parameters.properties FileText CreateText Check
                if os.path.exists(parameters_file):
                    st.success("✅ Report CompleteText!")
                    # parameters.properties FileText CreateText Page Item
                    time.sleep(1)  # File Create Complete Item
                    st.rerun()
                else:
                    if return_code == 0:
                        st.warning("⚠️ Report parameters.properties FileText Report Item.")
                    else:
                        st.error(f"❌ Report Execute Item (Report: {return_code})")
                    
        except Exception as e:
            st.error(f"❌ Execute Item Error Item: {e}")
    
    st.markdown("---")
    
    # parameters.properties File display Report
    render_parameters_editor(parameters_file)

def render_parameters_editor(parameters_file):
    """parameters.properties File Item"""
    st.subheader("📄 parameters.properties")
    
    if not os.path.exists(parameters_file):
        st.warning(f"⚠️ parameters.properties FileText Report.")
        st.info("Report Item ExecuteText.")
        return
    
    try:
        # properties FileText DataFrameText Transform
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
                        # = Report display
                        properties_data.append({
                            'Key': line,
                            'Value': '',
                            'Line': line_num
                        })
        
        if not properties_data:
            st.info("📝 Config Report.")
            return
        
        df = pd.DataFrame(properties_data)
        
        # File Info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Config Report", len(df))
        with col2:
            file_size = os.path.getsize(parameters_file)
            st.metric("📁 File Item", f"{file_size:,} bytes")
        with col3:
            mtime = os.path.getmtime(parameters_file)
            st.metric("🕒 Report", time.strftime("%H:%M:%S", time.localtime(mtime)))
        
        # Report
        search_term = st.text_input("🔍 Item", placeholder="Report Report")
        
        # Report
        filtered_df = df.copy()
        if search_term:
            mask = (df['Key'].str.contains(search_term, case=False, na=False) | 
                   df['Value'].str.contains(search_term, case=False, na=False))
            filtered_df = df[mask]
            st.info(f"🔍 Report: {len(filtered_df)}Report")
        
        # Report Item (Line Report)
        edit_df = filtered_df[['Key', 'Value']].copy()
        
        edited_df = st.data_editor(
            edit_df,
            use_container_width=True,
            num_rows="dynamic",
            key="parameters_editor"
        )
        
        # Report
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("💾 Item", type="primary"):
                try:
                    # Generation
                    backup_path = f"{parameters_file}.backup"
                    import shutil
                    shutil.copy2(parameters_file, backup_path)
                    
                    # Item properties File Item
                    with open(parameters_file, 'w', encoding='utf-8') as f:
                        f.write("# Parameters Configuration\n")
                        f.write(f"# Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        
                        for _, row in edited_df.iterrows():
                            if row['Key'] and not pd.isna(row['Key']):
                                if row['Value'] and not pd.isna(row['Value']):
                                    f.write(f"{row['Key']}={row['Value']}\n")
                                else:
                                    f.write(f"{row['Key']}=\n")
                    
                    st.success("✅ parameters.properties Item Complete!")
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Report: {e}")
        
        with col2:
            if st.button("🔄 Item"):
                st.rerun()
        
        with col3:
            st.caption(f"📁 {parameters_file}")
        
        # Item File Report
        with st.expander("📄 Item File Item", expanded=False):
            with open(parameters_file, 'r', encoding='utf-8') as f:
                content = f.read()
            st.code(content, language='properties')
            
    except Exception as e:
        st.error(f"❌ File Item Error: {e}")
        
        # Report
        backup_path = f"{parameters_file}.backup"
        if os.path.exists(backup_path):
            if st.button("🔧 Report"):
                try:
                    import shutil
                    shutil.copy2(backup_path, parameters_file)
                    st.success("✅ Report.")
                    st.rerun()
                except Exception as restore_e:
                    st.error(f"❌ Report: {restore_e}")
