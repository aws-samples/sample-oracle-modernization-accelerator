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
    """XML Merge Execute Page"""
    # Item Page Report Item CSS
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
    
    # Report Report Report
    if st.button("🏠 Home", key="merge_transform_home"):
        st.session_state.selected_action = None
        st.rerun()
    
    # Report Item display
    st.markdown("# 🔗 XML Merge Execute")
    
    # Report
    tab1, tab2 = st.tabs(["🔗 XML Merge Execute", "📋 Execute Item"])
    
    with tab1:
        render_xml_merge_execution_tab()
    
    with tab2:
        render_xml_merge_results_tab()


def render_xml_merge_execution_tab():
    """XML Merge Execute Item"""
    st.markdown("## 🔗 XML Merge Task")
    
    # Task description
    st.info("""
    **XML Merge Task Item:**
    1. Report XML FileText Item (`delete_target_xml_files.sh`)
    2. SQL Transform Merge Task Execute (`processSqlTransform.sh merge`)
    
    Item Task TransformText SQL FileText Report XML FileText CreateText.
    """)
    
    # Environment Item Check
    app_tools_folder = os.environ.get('APP_TOOLS_FOLDER')
    oma_base_dir = os.environ.get('OMA_BASE_DIR')
    
    if not app_tools_folder or not oma_base_dir:
        st.error("❌ Environment variable is not set.")
        return
    
    if not os.path.exists(target_sql_mapper_folder):
        st.error(f"❌ TARGET_SQL_MAPPER_FOLDER Report Item: {target_sql_mapper_folder}")
        return
    
    st.info(f"📁 **TARGET_SQL_MAPPER_FOLDER:** {target_sql_mapper_folder}")
    
    # 1/3, 2/3 Report
    col_list, col_content = st.columns([1, 2])
    
    with col_list:
        st.markdown("### 🔍 XML File Item")
        
        # FileText Item
        file_filter = st.text_input(
            "FileText Item",
            value="",
            placeholder="Item: mapper, user",
            help="FileText Report Report"
        )
        
        show_all = st.checkbox("Item File display", value=True)
        
        # XML File Item
        xml_files = []
        if os.path.exists(target_sql_mapper_folder):
            for root, dirs, files in os.walk(target_sql_mapper_folder):
                for file in files:
                    if file.endswith('.xml'):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, target_sql_mapper_folder)
                        
                        # Report
                        if show_all or not file_filter or file_filter.lower() in full_path.lower():
                            xml_files.append({
                                'name': file,
                                'rel_path': rel_path,
                                'full_path': full_path,
                                'size': os.path.getsize(full_path),
                                'dir': os.path.dirname(rel_path) if os.path.dirname(rel_path) else '.'
                            })
        
        # Item display
        if xml_files:
            st.success(f"✅ {len(xml_files)}Item File")
            
            # Report display
            # Generation
            df_data = []
            for xml_file in sorted(xml_files, key=lambda x: x['rel_path']):
                df_data.append({
                    'Item': xml_file['dir'],
                    'FileText': xml_file['name'],
                    'Item': f"{xml_file['size']:,}",
                    'Item': xml_file['full_path']
                })
            
            df = pd.DataFrame(df_data)
            
            # Report Item display
            selected_indices = st.dataframe(
                df[['Item', 'FileText', 'Item']],
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            # Report Item File Item display
            if selected_indices.selection.rows:
                selected_idx = selected_indices.selection.rows[0]
                selected_file_path = df.iloc[selected_idx]['Item']
                st.session_state.selected_xml_file = selected_file_path
        
        if True:  # English only
            if file_filter:
                st.info(f"'{file_filter}' Report FileText Item.")
            if True:  # English only
                st.info("XML FileText Item.")
    
    with col_content:
        st.markdown("### 📄 XML File Item")
        
        # Item File Item display
        if 'selected_xml_file' in st.session_state and st.session_state.selected_xml_file:
            display_xml_content_inline(st.session_state.selected_xml_file)
        if True:  # English only
            st.info("👈 Item XML FileText Item.")


def display_xml_content_inline(file_path):
    """Item XML File Report display"""
    # File Info
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    rel_path = os.path.relpath(file_path, os.environ.get('TARGET_SQL_MAPPER_FOLDER', ''))
    
    # Item (File Info + Report)
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"**{file_name}**")
        st.caption(f"📁 {rel_path} | 💾 {file_size:,} bytes")
    with col2:
        if st.button("❌", key="close_xml_viewer", help="Item"):
            del st.session_state.selected_xml_file
            st.rerun()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Item Info (Item)
        line_count = len(content.split('\n'))
        char_count = len(content)
        sql_count = content.count('<select') + content.count('<insert') + content.count('<update') + content.count('<delete')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Item", f"{line_count:,}")
        with col2:
            st.metric("Item", f"{char_count:,}")
        with col3:
            st.metric("SQL", f"{sql_count:,}")
        
        # XML Report Item display (Report)
        st.code(content, language='xml', line_numbers=True)
        
        # Report
        st.download_button(
            "💾 File Item",
            data=content,
            file_name=file_name,
            mime="application/xml",
            key=f"download_{file_path}",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"❌ FileText Report Item: {str(e)}")
        if st.button("🔄 Report", key="retry_xml_read"):
            st.rerun()
