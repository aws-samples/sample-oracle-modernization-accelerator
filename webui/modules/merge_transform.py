"""
XML Merge Page
"""
import streamlit as st
import subprocess
import os
import re
import html
import pandas as pd


def render_merge_transform_page():
    """XML Merge execution page"""
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
    if st.button("🏠 Home", key="merge_transform_home"):
        st.session_state.selected_action = None
        st.rerun()
    
    # Display title in full width
    st.markdown("# 🔗 XML Merge Execute")
    
    # Tab configuration
    tab1, tab2 = st.tabs(["🔗 XML Merge Execute", "📋 Execute Result"])
    
    with tab1:
        render_xml_merge_execution_tab()
    
    with tab2:
        render_xml_merge_results_tab()


def render_xml_merge_execution_tab():
    """XML Merge execution tab"""
    st.markdown("## 🔗 XML Merge Task")
    
    # Task description
    st.info("""
    **XML Merge Task Order:**
    1. Delete existing target XML files (`delete_target_xml_files.sh`)
    2. Execute SQL Transform Merge Task (`processSqlTransform.sh merge`)
    
    This task merges transformed SQL files to create final XML files.
    """)
    
    # Check environment variables
    app_tools_folder = os.environ.get('APP_TOOLS_FOLDER')
    oma_base_dir = os.environ.get('OMA_BASE_DIR')
    
    if not app_tools_folder or not oma_base_dir:
        st.error("❌ Required environment variables are not set. Please configure project environment first.")
        return
    
    # Check script file existence
    delete_script = os.path.join(app_tools_folder, "..", "postTransform", "delete_target_xml_files.sh")
    transform_script = os.path.join(oma_base_dir, "bin", "processSqlTransform.sh")
    
    st.markdown("### 📁 Script File Check")
    col1, col2 = st.columns(2)
    
    with col1:
        if os.path.exists(delete_script):
            st.success(f"✅ delete_target_xml_files.sh")
        else:
            st.error(f"❌ delete_target_xml_files.sh file not found")
        st.caption(f"Path: {delete_script}")
    
    with col2:
        if os.path.exists(transform_script):
            st.success(f"✅ processSqlTransform.sh")
        else:
            st.error(f"❌ processSqlTransform.sh file not found")
        st.caption(f"Path: {transform_script}")
    
    # Execute button
    st.markdown("### 🚀 XML Merge Execute")
    
    # Check if execution is in progress
    if st.session_state.oma_controller.is_any_task_running():
        st.warning("⚠️ Another task is currently running. Please try again later.")
        return
    
    if st.button("🔗 XML Merge Start", type="primary", use_container_width=True):
        if os.path.exists(delete_script) and os.path.exists(transform_script):
            # Compose compound command
            command = f"{delete_script} && cd {oma_base_dir}/bin && ./processSqlTransform.sh merge"
            
            # Execute directly without TaskManager
            execute_xml_merge_directly(command)
        else:
            st.error("❌ Required script files do not exist.")


def execute_xml_merge_directly(command):
    """Execute XML Merge directly without TaskManager"""
    st.info(f"🔗 **XML Merge Execute:** `{command}`")
    
    # Log container
    log_container = st.empty()
    
    try:
        # Execute process
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Collect real-time logs
        log_lines = []
        
        while True:
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    break
                continue
            
            clean_line = line.rstrip('\n\r')
            if clean_line:
                log_lines.append(clean_line)
                
                # Display logs (last 100 lines only)
                display_lines = log_lines[-100:] if len(log_lines) > 100 else log_lines
                log_text = '\n'.join(display_lines)
                
                with log_container.container():
                    st.markdown(f"""
                    <div class="log-container">
{log_text}
                    </div>
                    """, unsafe_allow_html=True)
        
        # Wait for process completion
        return_code = process.wait()
        
        if return_code == 0:
            st.success("✅ XML Merge task completed successfully!")
        else:
            st.error(f"❌ XML Merge task failed. (Exit code: {return_code})")
            
    except Exception as e:
        st.error(f"❌ An error occurred during XML Merge execution: {str(e)}")


def render_xml_merge_results_tab():
    """XML Merge results tab"""
    st.markdown("## 📋 XML Merge Execute Result")
    
    # Check TARGET_SQL_MAPPER_FOLDER
    target_sql_mapper_folder = os.environ.get('TARGET_SQL_MAPPER_FOLDER')
    
    if not target_sql_mapper_folder:
        st.warning("⚠️ TARGET_SQL_MAPPER_FOLDER environment variable is not set.")
        return
    
    if not os.path.exists(target_sql_mapper_folder):
        st.error(f"❌ TARGET_SQL_MAPPER_FOLDER path does not exist: {target_sql_mapper_folder}")
        return
    
    st.info(f"📁 **TARGET_SQL_MAPPER_FOLDER:** {target_sql_mapper_folder}")
    
    # 1/3, 2/3 column split
    col_list, col_content = st.columns([1, 2])
    
    with col_list:
        st.markdown("### 🔍 XML File List")
        
        # Filename filter
        file_filter = st.text_input(
            "Filename Filter",
            value="",
            placeholder="e.g.: mapper, user",
            help="Filter by text contained in filename or path"
        )
        
        show_all = st.checkbox("Show All Files", value=True)
        
        # Search XML files
        xml_files = []
        if os.path.exists(target_sql_mapper_folder):
            for root, dirs, files in os.walk(target_sql_mapper_folder):
                for file in files:
                    if file.endswith('.xml'):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, target_sql_mapper_folder)
                        
                        # Apply filter
                        if show_all or not file_filter or file_filter.lower() in full_path.lower():
                            xml_files.append({
                                'name': file,
                                'rel_path': rel_path,
                                'full_path': full_path,
                                'size': os.path.getsize(full_path),
                                'dir': os.path.dirname(rel_path) if os.path.dirname(rel_path) else '.'
                            })
        
        # Display results
        if xml_files:
            st.success(f"✅ {len(xml_files)} Files")
            
            # Display in table format
            # Create dataframe
            df_data = []
            for xml_file in sorted(xml_files, key=lambda x: x['rel_path']):
                df_data.append({
                    'Directory': xml_file['dir'],
                    'Filename': xml_file['name'],
                    'Size': f"{xml_file['size']:,}",
                    'Path': xml_file['full_path']
                })
            
            df = pd.DataFrame(df_data)
            
            # Display as selectable table
            selected_indices = st.dataframe(
                df[['Directory', 'Filename', 'Size']],
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            # Display file content if row is selected
            if selected_indices.selection.rows:
                selected_idx = selected_indices.selection.rows[0]
                selected_file_path = df.iloc[selected_idx]['Path']
                st.session_state.selected_xml_file = selected_file_path
        
        else:
            if file_filter:
                st.info(f"No files match the condition '{file_filter}'.")
            else:
                st.info("No XML files found.")
    
    with col_content:
        st.markdown("### 📄 XML File Content")
        
        # Display selected file content
        if 'selected_xml_file' in st.session_state and st.session_state.selected_xml_file:
            display_xml_content_inline(st.session_state.selected_xml_file)
        else:
            st.info("👈 Please select an XML file from the left.")


def display_xml_content_inline(file_path):
    """Display selected XML file content inline"""
    # File information
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    rel_path = os.path.relpath(file_path, os.environ.get('TARGET_SQL_MAPPER_FOLDER', ''))
    
    # Header (File info + close button)
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"**{file_name}**")
        st.caption(f"📁 {rel_path} | 💾 {file_size:,} bytes")
    with col2:
        if st.button("❌", key="close_xml_viewer", help="Close"):
            del st.session_state.selected_xml_file
            st.rerun()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Statistics info (simple)
        line_count = len(content.split('\n'))
        char_count = len(content)
        sql_count = content.count('<select') + content.count('<insert') + content.count('<update') + content.count('<delete')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Lines", f"{line_count:,}")
        with col2:
            st.metric("Characters", f"{char_count:,}")
        with col3:
            st.metric("SQL", f"{sql_count:,}")
        
        # Display XML content as code block (height adjusted)
        st.code(content, language='xml', line_numbers=True)
        
        # Download button
        st.download_button(
            "💾 File Download",
            data=content,
            file_name=file_name,
            mime="application/xml",
            key=f"download_{file_path}",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"❌ Cannot read file: {str(e)}")
        if st.button("🔄 Retry", key="retry_xml_read"):
            st.rerun()
