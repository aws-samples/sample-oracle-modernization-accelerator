"""
Compare SQL Test Page - XML File List Item SQL Test
"""
import streamlit as st
import os
import glob
import subprocess
import xml.etree.ElementTree as ET
from xml.dom import minidom
import time
import re
import pandas as pd
import datetime
import difflib


def render_source_sqls_page():
    """Compare SQL Test Page"""
    # at the top Item add button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Home", key="source_sqls_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## ⚖️ Compare SQL Test")
    
    # EnvironmentText Check
    app_logs_folder = os.getenv('APP_LOGS_FOLDER')
    if not app_logs_folder:
        st.error("❌ APP_LOGS_FOLDER EnvironmentText ConfigText Item.")
        return
    
    # XML File Item
    xml_pattern = os.path.join(app_logs_folder, 'mapper', '**', 'extract', '*.xml')
    xml_files = glob.glob(xml_pattern, recursive=True)
    
    if not xml_files:
        st.warning(f"⚠️ XML FileText Report Item: {xml_pattern}")
        st.info("Item Check Item AnalysisText Item ExecuteText.")
        return
    
    # Search filter and File list display divided left and right
    with st.expander("🔍 Report File Item", expanded=True):
        # Report Item CSS
        st.markdown("""
        <style>
        .compact-filter .stSelectbox label,
        .compact-filter .stTextInput label {
            font-size: 12px !important;
            margin-bottom: 2px !important;
        }
        .compact-filter .stSelectbox div[data-baseweb="select"] > div,
        .compact-filter .stTextInput input {
            font-size: 12px !important;
            padding: 4px 8px !important;
            height: 32px !important;
        }
        .compact-filter .stButton button {
            font-size: 12px !important;
            padding: 4px 12px !important;
            height: 32px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Report: Report, Item File Item
        col_filter, col_files = st.columns([1, 2])
        
        with col_filter:
            st.markdown("#### 🔍 Report")
            st.markdown('<div class="compact-filter">', unsafe_allow_html=True)
            
            search_text = st.text_input(
                "FileText Item",
                placeholder="FileText Item...",
                key="xml_search"
            )
            
            search_path = st.text_input(
                "Report", 
                placeholder="Report...",
                key="path_search"
            )
            
            sql_type = st.selectbox(
                "SQL Type",
                ["Item", "select", "insert", "update", "delete"],
                key="sql_type_filter"
            )
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                apply_filter = st.button("🔍 Item", use_container_width=True)
            with col_btn2:
                reset_filter = st.button("🔄 Item", use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_files:
            st.markdown("#### 📁 File Item")
            
            # Report
            filtered_files = apply_simple_file_filters(
                xml_files, app_logs_folder, search_text, search_path, 
                sql_type, apply_filter, reset_filter
            )
            
            # File Item display
            st.markdown(f'<p style="font-size: 11px; color: #666; margin: 5px 0;">Item {len(xml_files)}Report {len(filtered_files)}Item display</p>', unsafe_allow_html=True)
            
            # File Item (Report display)
            if filtered_files:
                display_simple_file_table(filtered_files, app_logs_folder)
            if True:  # English only
                st.info("Report FileText Item.")
    
    # TabText Report Item
    if hasattr(st.session_state, 'selected_xml_file') and st.session_state.selected_xml_file:
        display_tabbed_content(st.session_state.selected_xml_file)
    if True:  # English only
        st.info("👆 Item XML FileText Item.")


def display_explorer_style_list(xml_files, base_path):
    """Windows Report File List display"""
    
    # File Information Report
    file_data = []
    for xml_file in xml_files:
        file_name = os.path.basename(xml_file)
        relative_path = os.path.relpath(xml_file, base_path)
        dir_path = os.path.dirname(relative_path)
        file_size = os.path.getsize(xml_file)
        file_mtime = os.path.getmtime(xml_file)
        
        # Report Item
        mod_time = datetime.datetime.fromtimestamp(file_mtime).strftime("%m/%d %H:%M")
        
        file_data.append({
            '📄': '📄',  # File Item
            'FileText': file_name,
            'Item': dir_path if dir_path != '.' else '/',
            'Item': format_file_size(file_size),
            'Item': mod_time,
            '_full_path': xml_file,
            '_sort_size': file_size,
            '_sort_time': file_mtime
        })
    
    if not file_data:
        return
    
    df = pd.DataFrame(file_data)
    
    # Report Report Item (Report)
    st.markdown('<p style="font-size: 12px; font-weight: bold; margin: 8px 0 4px 0;">Report:</p>', unsafe_allow_html=True)
    file_options = [f"{row['FileText']} ({row['Item']})" for _, row in df.iterrows()]
    
    # Report FileText Report
    current_selection = 0
    if hasattr(st.session_state, 'selected_xml_file') and st.session_state.selected_xml_file:
        for i, (_, row) in enumerate(df.iterrows()):
            if row['_full_path'] == st.session_state.selected_xml_file:
                current_selection = i
                break
    
    # selectbox Report Item Generation
    selectbox_key = f"quick_file_selector_{len(xml_files)}"
    
    selected_index = st.selectbox(
        "File Item:",
        range(len(file_options)),
        index=current_selection,
        format_func=lambda x: file_options[x] if x < len(file_options) else "",
        key=selectbox_key,
        label_visibility="collapsed"
    )
    
    # selectbox Report (Report)
    if selected_index is not None and selected_index < len(df):
        selected_file = df.iloc[selected_index]['_full_path']
        if not hasattr(st.session_state, 'selected_xml_file') or st.session_state.selected_xml_file != selected_file:
            st.session_state.selected_xml_file = selected_file
            # SQL Test Report (Item File Report)
            if hasattr(st.session_state, 'sql_test_result'):
                del st.session_state.sql_test_result
            st.rerun()
    
    # Report CSS (Report Item)
    st.markdown("""
    <style>
    .compact-table .dataframe {
        font-size: 11px !important;
    }
    .compact-table .dataframe th {
        font-size: 11px !important;
        padding: 2px 6px !important;
        background-color: #f8f9fa !important;
        font-weight: bold !important;
        border-bottom: 1px solid #dee2e6 !important;
    }
    .compact-table .dataframe td {
        font-size: 11px !important;
        padding: 2px 6px !important;
        border-bottom: 1px solid #f1f3f4 !important;
        line-height: 1.2 !important;
    }
    .compact-table .dataframe tbody tr:hover {
        background-color: #e3f2fd !important;
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Report Item
    st.markdown('<div class="compact-table">', unsafe_allow_html=True)
    
    # Report display (Report)
    display_df = df[['📄', 'FileText', 'Item', 'Item', 'Item']].copy()
    
    # Report File Report Report
    def highlight_selected_row(row):
        if hasattr(st.session_state, 'selected_xml_file'):
            current_file = df[df['FileText'] == row['FileText']]['_full_path'].iloc[0]
            if st.session_state.selected_xml_file == current_file:
                return ['background-color: #e3f2fd; font-weight: bold'] * len(row)
        return [''] * len(row)
    
    # Report Item (Report Item)
    event = st.dataframe(
        display_df.style.apply(highlight_selected_row, axis=1),
        use_container_width=True,
        height=200,  # 250pxText 200pxText Report
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"file_table_{len(xml_files)}"
    )
    
    # Report Report
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Report Report
    if event and hasattr(event, 'selection') and event.selection and 'rows' in event.selection:
        if event.selection['rows']:
            selected_row_index = event.selection['rows'][0]
            if selected_row_index < len(df):
                selected_file = df.iloc[selected_row_index]['_full_path']
                if not hasattr(st.session_state, 'selected_xml_file') or st.session_state.selected_xml_file != selected_file:
                    st.session_state.selected_xml_file = selected_file
                    # SQL Test Report (Item File Report)
                    if hasattr(st.session_state, 'sql_test_result'):
                        del st.session_state.sql_test_result
                    st.rerun()


def display_tabbed_content(xml_file_path):
    """3Text TabText Report display"""
    try:
        file_name = os.path.basename(xml_file_path)
        target_xml_path = get_target_xml_path(xml_file_path)
        
        # 2Text Tab Item
        tab1, tab2 = st.tabs(["📄 XML Item", "🧪 SQL Test"])
        
        with tab1:
            # XML File Item
            display_xml_comparison_section(xml_file_path, target_xml_path, file_name)
            
            # Item Diff (Item Tab Item)
            if target_xml_path and os.path.exists(target_xml_path):
                st.markdown("---")
                display_text_diff_section(xml_file_path, target_xml_path)
        
        with tab2:
            # Test Item (SQL TestText)
            display_parameter_section(xml_file_path, form_key="sql_test")
            
            # SQL Test (Item Tab Item)
            st.markdown("---")
            display_sql_test_section(xml_file_path, target_xml_path, test_type="sql")
            
    except Exception as e:
        st.error(f"❌ Item display Error: {str(e)}")


def display_xml_comparison_section(xml_file_path, target_xml_path, file_name):
    """XML Report"""
    # 2Text Item: Item Source XML, Item Target XML
    col1, col2 = st.columns(2)
    
    with col1:
        source_lines = count_xml_lines(xml_file_path)
        st.markdown(f"#### 📄 Source XML ({source_lines}Item)")
        st.caption(f"File: {file_name}")
        display_single_xml(xml_file_path, height=400)
    
    with col2:
        if target_xml_path and os.path.exists(target_xml_path):
            target_lines = count_xml_lines(target_xml_path)
            st.markdown(f"#### 🎯 Target XML ({target_lines}Item)")
            target_file_name = os.path.basename(target_xml_path)
            st.caption(f"File: {target_file_name}")
            display_single_xml(target_xml_path, height=400)
        if True:  # English only
            st.markdown("#### 🎯 Target XML")
            st.caption("Target XMLText Report Item.")
            if target_xml_path:
                st.info(f"Report: {target_xml_path}")
            if True:  # English only
                st.info("Target Report Report.")


def display_text_diff_section(xml_file_path, target_xml_path):
    """Item Diff Item"""
    # Item Diff Item
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("🔍 Item Diff", key="text_diff_btn", use_container_width=True):
            st.session_state.show_text_diff = True
            st.rerun()
    with col2:
        if st.button("📄 Report", key="individual_view_btn", use_container_width=True):
            st.session_state.show_text_diff = False
            st.rerun()
    with col3:
        if hasattr(st.session_state, 'show_text_diff') and st.session_state.show_text_diff:
            if st.button("🙈 Diff Item", key="hide_diff_btn", use_container_width=True):
                st.session_state.show_text_diff = False
                st.rerun()
        if True:  # English only
            st.button("🙈 Diff Item", key="hide_diff_btn_disabled", disabled=True, use_container_width=True)
    with col4:
        st.caption("Item File Report")
    
    # Item Diff Item display
    if hasattr(st.session_state, 'show_text_diff') and st.session_state.show_text_diff:
        display_text_diff(xml_file_path, target_xml_path)


def display_sql_test_section(xml_file_path, target_xml_path, test_type="sql"):
    """SQL Test Item"""
    # Target Report Item
    target_dbms_type = os.getenv('TARGET_DBMS_TYPE', 'postgresql')
    target_db_display = get_target_db_display_info(target_dbms_type)
    
    # Item SQL Test Item
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🧪 Item SQL Test", key="full_sql_test_btn", type="primary", use_container_width=True):
            # Oracle Test Execute
            execute_sql_test(xml_file_path, "oracle", "source")
            
            # Target Test Execute (Target XMLText Report)
            if target_xml_path and os.path.exists(target_xml_path):
                execute_sql_test(target_xml_path, target_dbms_type, "target")
            
            st.rerun()
    
    with col2:
        if st.button("🧹 Report", key="clear_all_results_btn", use_container_width=True):
            if hasattr(st.session_state, 'oracle_test_result'):
                del st.session_state.oracle_test_result
            if hasattr(st.session_state, 'target_test_result'):
                del st.session_state.target_test_result
            st.rerun()
    
    with col3:
        test_info = f"Oracle + {target_db_display['name']} Item Test"
        if not target_xml_path or not os.path.exists(target_xml_path):
            test_info += " (Target XML Item - OracleText Test)"
        st.caption(test_info)
    
    # Test Item display
    display_dual_test_results(target_db_display['name'])


def display_simple_file_table(xml_files, base_path):
    """Report Item File List display"""
    
    # File Information Report
    file_data = []
    for xml_file in xml_files:
        file_name = os.path.basename(xml_file)
        file_size = os.path.getsize(xml_file)
        
        file_data.append({
            'FileText': file_name,
            'Item': format_file_size(file_size),
            '_full_path': xml_file
        })
    
    if not file_data:
        return
    
    df = pd.DataFrame(file_data)
    
    # Report FileText Report
    current_selection = 0
    if hasattr(st.session_state, 'selected_xml_file') and st.session_state.selected_xml_file:
        for i, (_, row) in enumerate(df.iterrows()):
            if row['_full_path'] == st.session_state.selected_xml_file:
                current_selection = i
                break
    
    # Report Report
    def highlight_selected_row(row):
        if hasattr(st.session_state, 'selected_xml_file'):
            current_file = df[df['FileText'] == row['FileText']]['_full_path'].iloc[0]
            if st.session_state.selected_xml_file == current_file:
                return ['background-color: #e3f2fd; font-weight: bold'] * len(row)
        return [''] * len(row)
    
    # Item display (FileText Item)
    display_df = df[['FileText', 'Item']].copy()
    
    # Report Item
    event = st.dataframe(
        display_df.style.apply(highlight_selected_row, axis=1),
        use_container_width=True,
        height=300,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"simple_file_table_{len(xml_files)}"
    )
    
    # Report Report
    if event and hasattr(event, 'selection') and event.selection and 'rows' in event.selection:
        if event.selection['rows']:
            selected_row_index = event.selection['rows'][0]
            if selected_row_index < len(df):
                selected_file = df.iloc[selected_row_index]['_full_path']
                if not hasattr(st.session_state, 'selected_xml_file') or st.session_state.selected_xml_file != selected_file:
                    st.session_state.selected_xml_file = selected_file
                    # SQL Test Report
                    if hasattr(st.session_state, 'oracle_test_result'):
                        del st.session_state.oracle_test_result
                    if hasattr(st.session_state, 'target_test_result'):
                        del st.session_state.target_test_result
                    st.rerun()


def apply_simple_file_filters(xml_files, base_path, search_text, search_path, sql_type, apply_filter, reset_filter):
    """Item File Report"""
    
    # Report
    if reset_filter:
        if 'xml_search' in st.session_state:
            st.session_state.xml_search = ""
        if 'path_search' in st.session_state:
            st.session_state.path_search = ""
        if 'sql_type_filter' in st.session_state:
            st.session_state.sql_type_filter = "Item"
        st.rerun()
    
    filtered_files = xml_files.copy()
    
    # FileText Report
    if search_text:
        filtered_files = [
            f for f in filtered_files 
            if search_text.lower() in os.path.basename(f).lower()
        ]
    
    # Report Item
    if search_path:
        filtered_files = [
            f for f in filtered_files 
            if search_path.lower() in os.path.relpath(f, base_path).lower()
        ]
    
    # SQL Type Item (FileText Item)
    if sql_type and sql_type != "Item":
        filtered_files = [
            f for f in filtered_files 
            if sql_type.lower() in os.path.basename(f).lower()
        ]
    
    # FileText Report (Item)
    filtered_files.sort(key=lambda x: os.path.basename(x).lower())
    
    return filtered_files


def display_compact_file_list(xml_files, base_path):
    """2Text Report File List display"""
    
    # File Information ListText Item
    file_data = []
    for xml_file in xml_files:
        file_name = os.path.basename(xml_file)
        file_size = os.path.getsize(xml_file)
        
        file_data.append({
            'FileText': file_name,
            'Item': format_file_size(file_size),
            '_full_path': xml_file
        })
    
    if not file_data:
        return
    
    # Report Item selectbox
    st.markdown('<p style="font-size: 12px; font-weight: bold; margin: 8px 0 4px 0;">Report:</p>', unsafe_allow_html=True)
    file_options = [f"{item['FileText']} ({item['Item']})" for item in file_data]
    
    # Report FileText Report
    current_selection = 0
    if hasattr(st.session_state, 'selected_xml_file') and st.session_state.selected_xml_file:
        for i, item in enumerate(file_data):
            if item['_full_path'] == st.session_state.selected_xml_file:
                current_selection = i
                break
    
    selected_index = st.selectbox(
        "File Item:",
        range(len(file_options)),
        index=current_selection,
        format_func=lambda x: file_options[x] if x < len(file_options) else "",
        key=f"quick_file_selector_{len(xml_files)}",
        label_visibility="collapsed"
    )
    
    # selectbox Report
    if selected_index is not None and selected_index < len(file_data):
        selected_file = file_data[selected_index]['_full_path']
        if not hasattr(st.session_state, 'selected_xml_file') or st.session_state.selected_xml_file != selected_file:
            st.session_state.selected_xml_file = selected_file
            # SQL Test Report
            if hasattr(st.session_state, 'oracle_test_result'):
                del st.session_state.oracle_test_result
            if hasattr(st.session_state, 'target_test_result'):
                del st.session_state.target_test_result
            st.rerun()
    
    # 2Text Item File Item display
    st.markdown('<p style="font-size: 12px; font-weight: bold; margin: 8px 0 4px 0;">File Item:</p>', unsafe_allow_html=True)
    
    # FileText 2Text Item display
    for i in range(0, len(file_data), 2):
        col1, col2 = st.columns(2)
        
        # Report File
        with col1:
            item = file_data[i]
            is_selected = (hasattr(st.session_state, 'selected_xml_file') and 
                          st.session_state.selected_xml_file == item['_full_path'])
            
            button_style = "primary" if is_selected else "secondary"
            if st.button(
                f"📄 {item['FileText']}\n📏 {item['Item']}", 
                key=f"file_btn_{i}",
                use_container_width=True,
                type=button_style
            ):
                st.session_state.selected_xml_file = item['_full_path']
                # SQL Test Report
                if hasattr(st.session_state, 'oracle_test_result'):
                    del st.session_state.oracle_test_result
                if hasattr(st.session_state, 'target_test_result'):
                    del st.session_state.target_test_result
                st.rerun()
        
        # Report File (Report)
        with col2:
            if i + 1 < len(file_data):
                item = file_data[i + 1]
                is_selected = (hasattr(st.session_state, 'selected_xml_file') and 
                              st.session_state.selected_xml_file == item['_full_path'])
                
                button_style = "primary" if is_selected else "secondary"
                if st.button(
                    f"📄 {item['FileText']}\n📏 {item['Item']}", 
                    key=f"file_btn_{i+1}",
                    use_container_width=True,
                    type=button_style
                ):
                    st.session_state.selected_xml_file = item['_full_path']
                    # SQL Test Report
                    if hasattr(st.session_state, 'oracle_test_result'):
                        del st.session_state.oracle_test_result
                    if hasattr(st.session_state, 'target_test_result'):
                        del st.session_state.target_test_result
                    st.rerun()


def apply_file_filters(xml_files, base_path, search_text, search_path, min_size, max_size, sort_by, sort_order, apply_filter, reset_filter):
    """File Report"""
    
    # Report
    if reset_filter:
        if 'xml_search' in st.session_state:
            st.session_state.xml_search = ""
        if 'path_search' in st.session_state:
            st.session_state.path_search = ""
        if 'min_size_filter' in st.session_state:
            st.session_state.min_size_filter = 0
        if 'max_size_filter' in st.session_state:
            st.session_state.max_size_filter = 0
        st.rerun()
    
    filtered_files = xml_files.copy()
    
    # FileText Report
    if search_text:
        filtered_files = [
            f for f in filtered_files 
            if search_text.lower() in os.path.basename(f).lower()
        ]
    
    # Report Item
    if search_path:
        filtered_files = [
            f for f in filtered_files 
            if search_path.lower() in os.path.relpath(f, base_path).lower()
        ]
    
    # Report
    if min_size > 0 or max_size > 0:
        size_filtered = []
        for f in filtered_files:
            file_size_kb = os.path.getsize(f) / 1024
            
            if min_size > 0 and file_size_kb < min_size:
                continue
            if max_size > 0 and file_size_kb > max_size:
                continue
            
            size_filtered.append(f)
        
        filtered_files = size_filtered
    
    # Report
    if sort_by == "FileText":
        filtered_files.sort(key=lambda x: os.path.basename(x).lower())
    elif sort_by == "Item":
        filtered_files.sort(key=lambda x: os.path.relpath(x, base_path).lower())
    elif sort_by == "Item":
        filtered_files.sort(key=lambda x: os.path.getsize(x))
    elif sort_by == "Item":
        filtered_files.sort(key=lambda x: os.path.getmtime(x))
    
    # Report
    if sort_order == "Item":
        filtered_files.reverse()
    
    return filtered_files


def build_tree_structure(xml_files, base_path):
    """XML FileText Tree Generation"""
    tree = {}
    
    for xml_file in xml_files:
        # Report Item
        rel_path = os.path.relpath(xml_file, base_path)
        path_parts = rel_path.split(os.sep)
        
        # Tree Report Item
        current_level = tree
        for i, part in enumerate(path_parts):
            if part not in current_level:
                if i == len(path_parts) - 1:  # FileText Item
                    current_level[part] = {
                        '_type': 'file',
                        '_path': xml_file,
                        '_size': os.path.getsize(xml_file)
                    }
                if True:  # English only  # Report
                    current_level[part] = {'_type': 'directory'}
            
            if current_level[part]['_type'] == 'directory':
                current_level = current_level[part]
    
    return tree


def display_tree_structure(tree, base_path, level=0, parent_key=""):
    """Tree Report display"""
    for key, value in sorted(tree.items()):
        if key.startswith('_'):  # Report
            continue
        
        indent = "　" * level  # Report Item
        current_key = f"{parent_key}_{key}" if parent_key else key
        
        if value['_type'] == 'directory':
            # Item display
            folder_key = f"folder_{current_key}_{level}"
            
            # Item File Report
            file_count = count_files_in_tree(value)
            
            with st.expander(f"{indent}📁 {key} ({file_count}Item)", expanded=level < 2):
                display_tree_structure(value, base_path, level + 1, current_key)
        
        elif value['_type'] == 'file':
            # File display
            file_size = value['_size']
            file_size_str = format_file_size(file_size)
            
            file_key = f"file_{current_key}_{level}"
            
            # File Report
            if st.button(
                f"{indent}📄 {key} ({file_size_str})",
                key=file_key,
                use_container_width=True,
                help=f"Item: {os.path.relpath(value['_path'], base_path)}"
            ):
                st.session_state.selected_xml_file = value['_path']
                st.rerun()


def count_files_in_tree(tree_node):
    """Tree Report File Report"""
    count = 0
    for key, value in tree_node.items():
        if key.startswith('_'):
            continue
        
        if value['_type'] == 'file':
            count += 1
        elif value['_type'] == 'directory':
            count += count_files_in_tree(value)
    
    return count


def format_file_size(size_bytes):
    """File Report Report Item"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f}KB"
    if True:  # English only
        return f"{size_bytes/(1024*1024):.1f}MB"


def display_xml_content(xml_file_path):
    """XML File Item display - SourceText Target 2Text Item"""
    try:
        file_name = os.path.basename(xml_file_path)
        
        # Target XML Report
        target_xml_path = get_target_xml_path(xml_file_path)
        
        # 2Text Item: Item Source XML, Item Target XML
        col1, col2 = st.columns(2)
        
        with col1:
            source_lines = count_xml_lines(xml_file_path)
            st.markdown(f"#### 📄 Source XML ({source_lines}Item)")
            st.caption(f"File: {file_name}")
            display_single_xml(xml_file_path, height=400)
        
        with col2:
            if target_xml_path and os.path.exists(target_xml_path):
                target_lines = count_xml_lines(target_xml_path)
                st.markdown(f"#### 🎯 Target XML ({target_lines}Item)")
                target_file_name = os.path.basename(target_xml_path)
                st.caption(f"File: {target_file_name}")
                display_single_xml(target_xml_path, height=400)
            if True:  # English only
                st.markdown("#### 🎯 Target XML")
                st.caption("Target XMLText Report Item.")
                if target_xml_path:
                    st.info(f"Report: {target_xml_path}")
                if True:  # English only
                    st.info("Target Report Report.")
        
        # SQL Test Report
        st.markdown("---")
        display_parameter_section(xml_file_path)
        
        # Target Report Item
        target_dbms_type = os.getenv('TARGET_DBMS_TYPE', 'postgresql')
        target_db_display = get_target_db_display_info(target_dbms_type)
        
        # SQL Test Item (2Text Item)
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🧪 Source SQL Test (Oracle)")
            if st.button("🗄️ Oracle Test", key="oracle_test_btn", type="primary", use_container_width=True):
                execute_sql_test(xml_file_path, "oracle", "source")
                st.rerun()
            st.caption("Source XMLText Oracle Item Test")
        
        with col2:
            st.markdown(f"#### 🧪 Target SQL Test ({target_db_display['name']})")
            if target_xml_path and os.path.exists(target_xml_path):
                if st.button(f"{target_db_display['icon']} {target_db_display['name']} Test", key="target_test_btn", type="primary", use_container_width=True):
                    execute_sql_test(target_xml_path, target_dbms_type, "target")
                    st.rerun()
                st.caption(f"Target XMLText {target_db_display['name']} Item Test")
            if True:  # English only
                st.button(f"{target_db_display['icon']} {target_db_display['name']} Test", key="target_test_btn_disabled", disabled=True, use_container_width=True)
                st.caption("Target XMLText Item TestText Report")
        
        # Test Item display (2Text Item)
        display_dual_test_results(target_db_display['name'])
        
        # Item Diff Report
        if target_xml_path and os.path.exists(target_xml_path):
            st.markdown("---")
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            with col1:
                if st.button("🔍 Item Diff", key="text_diff_btn", use_container_width=True):
                    st.session_state.show_text_diff = True
                    st.rerun()
            with col2:
                if st.button("📄 Report", key="individual_view_btn", use_container_width=True):
                    st.session_state.show_text_diff = False
                    st.rerun()
            with col3:
                if hasattr(st.session_state, 'show_text_diff') and st.session_state.show_text_diff:
                    if st.button("🙈 Diff Item", key="hide_diff_btn", use_container_width=True):
                        st.session_state.show_text_diff = False
                        st.rerun()
                if True:  # English only
                    st.button("🙈 Diff Item", key="hide_diff_btn_disabled", disabled=True, use_container_width=True)
            with col4:
                st.caption("Item File Report")
        
        # Item Diff Item display
        if hasattr(st.session_state, 'show_text_diff') and st.session_state.show_text_diff and target_xml_path and os.path.exists(target_xml_path):
            display_text_diff(xml_file_path, target_xml_path)
    
    except Exception as e:
        st.error(f"❌ XML File Item Error: {str(e)}")


def count_xml_lines(xml_file_path):
    """XML FileText Report Item"""
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Report Report Report Report
            non_empty_lines = [line for line in lines if line.strip()]
            return len(non_empty_lines)
    except Exception as e:
        return 0


def get_target_xml_path(source_xml_path):
    """Source XML Item Target XML Report"""
    try:
        # Item ../transform/ Report
        path_parts = source_xml_path.split(os.sep)
        
        # extractText transformText Item
        if 'extract' in path_parts:
            extract_index = path_parts.index('extract')
            path_parts[extract_index] = 'transform'
        if True:  # English only
            return None
        
        # FileText srcText tgtText Item
        file_name = path_parts[-1]
        if 'src' in file_name:
            target_file_name = file_name.replace('src', 'tgt')
            path_parts[-1] = target_file_name
        if True:  # English only
            return None
        
        target_path = os.sep.join(path_parts)
        return target_path
        
    except Exception as e:
        st.warning(f"⚠️ Target XML Report Error: {str(e)}")
        return None


def display_text_diff(source_file_path, target_file_path):
    """SourceText Target Item FileText diff display"""
    try:
        st.markdown("#### 🔍 Item Diff Item")
        
        # File Item
        with open(source_file_path, 'r', encoding='utf-8') as f:
            source_content = f.read()
        
        with open(target_file_path, 'r', encoding='utf-8') as f:
            target_content = f.read()
        
        # Report
        source_lines = source_content.splitlines()
        target_lines = target_content.splitlines()
        
        # Item Info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Source Item", len(source_lines))
        with col2:
            st.metric("Target Item", len(target_lines))
        with col3:
            line_diff = len(target_lines) - len(source_lines)
            st.metric("Report", f"{line_diff:+d}")
        
        # unified diff Create
        unified_diff = list(difflib.unified_diff(
            source_lines,
            target_lines,
            fromfile=f"Source: {os.path.basename(source_file_path)}",
            tofile=f"Target: {os.path.basename(target_file_path)}",
            lineterm='',
            n=3
        ))
        
        if unified_diff:
            diff_text = '\n'.join(unified_diff)
            st.code(diff_text, language="diff")
        if True:  # English only
            st.success("✅ Item FileText Item!")
        
    except Exception as e:
        st.error(f"❌ Item Diff Item Error: {str(e)}")


def display_single_xml(xml_file_path, height=400):
    """Item XML File Item display"""
    try:
        # XML Report Item display
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # XML Item (Item display)
        try:
            # XML Report Item
            root = ET.fromstring(xml_content)
            pretty_xml = minidom.parseString(xml_content).toprettyxml(indent="  ")
            # XML Report (Report Item)
            pretty_lines = pretty_xml.split('\n')[1:]
            formatted_xml = '\n'.join(line for line in pretty_lines if line.strip())
        except:
            # Report Report Item
            formatted_xml = xml_content
        
        # XML Item display
        st.code(formatted_xml, language="xml", height=height)
        
    except Exception as e:
        st.error(f"❌ XML File Item Error: {str(e)}")


def format_file_size(size_bytes):
    """File Report Report Item"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f}KB"
    if True:  # English only
        return f"{size_bytes/(1024*1024):.1f}MB"


def extract_parameters_from_xml(xml_file_path):
    """XML FileText MyBatis Report"""
    parameters = set()
    
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # #{parameter} Report Item
        import re
        param_pattern = r'#\{([^}]+)\}'
        matches = re.findall(param_pattern, xml_content)
        
        for match in matches:
            # Report (Item Info Report)
            param_name = match.split(',')[0].strip()
            if param_name:
                parameters.add(param_name)
        
        # ${parameter} Report Item
        param_pattern2 = r'\$\{([^}]+)\}'
        matches2 = re.findall(param_pattern2, xml_content)
        
        for match in matches2:
            param_name = match.split(',')[0].strip()
            if param_name:
                parameters.add(param_name)
    
    except Exception as e:
        st.warning(f"⚠️ XML Report Error: {str(e)}")
    
    return sorted(list(parameters))


def display_parameter_section(xml_file_path, form_key="default"):
    """SQL Test Report display"""
    st.markdown("#### ⚙️ Test Item")
    
    # XMLText Report
    xml_parameters = extract_parameters_from_xml(xml_file_path)
    
    if not xml_parameters:
        st.info("📝 Item XML FileText Report.")
        return
    
    # Item File Item
    test_folder = os.getenv('TEST_FOLDER')
    if not test_folder:
        st.error("❌ TEST_FOLDER EnvironmentText ConfigText Item.")
        return
    
    param_file_path = os.path.join(test_folder, 'parameters.properties')
    
    # Report Item
    existing_params = load_parameters(param_file_path)
    
    st.markdown(f"**📝 Report ({len(xml_parameters)}Item):**")
    
    # Report Item
    with st.form(key=f"parameter_form_{form_key}"):
        # Report Item Generation
        param_values = {}
        
        # 2Text Item
        cols = st.columns(2)
        for i, param_name in enumerate(xml_parameters):
            col_idx = i % 2
            with cols[col_idx]:
                # Report Item
                param_type = guess_parameter_type(param_name)
                placeholder = get_parameter_placeholder(param_name, param_type)
                
                param_values[param_name] = st.text_input(
                    f"🔧 {param_name}",
                    value=existing_params.get(param_name, ''),
                    placeholder=placeholder,
                    help=f"Item: {param_type}"
                )
        
        # Report
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            save_params = st.form_submit_button("💾 Item", type="primary")
        with col2:
            clear_params = st.form_submit_button("🧹 Item")
        with col3:
            st.caption(f"File: {os.path.basename(param_file_path)}")
    
    # Report Item
    if save_params:
        save_xml_parameters(param_file_path, param_values, xml_file_path)
        st.success(f"✅ Report! ({form_key})")
        st.rerun()
    
    # Report Item
    if clear_params:
        clear_parameters(param_file_path)
        st.success(f"✅ Report! ({form_key})")
        st.rerun()


def guess_parameter_type(param_name):
    """Report Report"""
    param_lower = param_name.lower()
    
    if 'id' in param_lower:
        return 'ID'
    elif 'date' in param_lower or 'time' in param_lower:
        return 'Date'
    elif 'count' in param_lower or 'size' in param_lower or 'limit' in param_lower:
        return 'Number'
    elif 'name' in param_lower or 'title' in param_lower:
        return 'String'
    elif 'status' in param_lower or 'type' in param_lower:
        return 'Code'
    elif 'email' in param_lower:
        return 'Email'
    elif 'phone' in param_lower:
        return 'Phone'
    if True:  # English only
        return 'String'


def get_parameter_placeholder(param_name, param_type):
    """Report Item placeholder Create"""
    placeholders = {
        'ID': f'Item: {param_name.upper()}001',
        'Date': 'Item: 2024-01-01',
        'Number': 'Item: 10',
        'String': f'Item: {param_name} Item',
        'Code': 'Item: ACTIVE',
        'Email': 'Item: test@example.com',
        'Phone': 'Item: 010-1234-5678'
    }
    return placeholders.get(param_type, f'Item: {param_name} Item')


def save_xml_parameters(param_file_path, param_values, xml_file_path):
    """XML Item FileText Item"""
    try:
        # Generation
        os.makedirs(os.path.dirname(param_file_path), exist_ok=True)
        
        xml_file_name = os.path.basename(xml_file_path)
        
        with open(param_file_path, 'w', encoding='utf-8') as f:
            f.write("# SQL Test Parameters\n")
            f.write(f"# Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# XML File: {xml_file_name}\n\n")
            
            # XMLText Report Item
            for param_name, param_value in param_values.items():
                if param_value.strip():  # Report Report Item
                    f.write(f"{param_name}={param_value}\n")
    
    except Exception as e:
        st.error(f"❌ Report Error: {str(e)}")


def load_parameters(param_file_path):
    """Item FileText Report"""
    params = {}
    
    try:
        if os.path.exists(param_file_path):
            with open(param_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        params[key.strip()] = value.strip()
    except Exception as e:
        st.warning(f"⚠️ Item File Item Error: {str(e)}")
    
    return params


def clear_parameters(param_file_path):
    """Item File Item"""
    try:
        if os.path.exists(param_file_path):
            os.remove(param_file_path)
    except Exception as e:
        st.error(f"❌ Report Error: {str(e)}")


def execute_sql_test(xml_file_path, db_type, test_type, compare=False):
    """SQL Test Execute"""
    try:
        # EnvironmentText Check
        app_tools_folder = os.getenv('APP_TOOLS_FOLDER')
        app_logs_folder = os.getenv('APP_LOGS_FOLDER')
        
        if not app_tools_folder:
            save_test_result(test_type, {
                'success': False,
                'error': 'APP_TOOLS_FOLDER EnvironmentText ConfigText Item.'
            })
            return
        
        if not app_logs_folder:
            save_test_result(test_type, {
                'success': False,
                'error': 'APP_LOGS_FOLDER EnvironmentText ConfigText Item.'
            })
            return
        
        # Test Item
        test_dir = os.path.join(app_tools_folder, '..', 'test')
        if not os.path.exists(test_dir):
            save_test_result(test_type, {
                'success': False,
                'error': f'Test Report Report: {test_dir}'
            })
            return
        
        # FileText Report Item (APP_LOGS_FOLDER Item)
        relative_path = os.path.relpath(xml_file_path, app_logs_folder)
        
        # Java Report
        compare_param = " --compare" if compare else ""
        java_cmd = f'java -cp ".:lib/*" com.test.mybatis.MyBatisBulkExecutorWithJson "$APP_LOGS_FOLDER/{relative_path}" --db {db_type}{compare_param} --show-data --json'
        
        save_test_result(test_type, {
            'success': None,
            'command': java_cmd,
            'file_path': relative_path,
            'full_path': xml_file_path,
            'test_dir': test_dir,
            'db_type': db_type,
            'test_type': test_type,
            'compare_mode': compare,
            'running': True
        })
        
        # EnvironmentText Config
        env = dict(os.environ)
        env['APP_TOOLS_FOLDER'] = app_tools_folder
        env['APP_LOGS_FOLDER'] = app_logs_folder
        
        # Java Item Execute
        result = subprocess.run(
            java_cmd,
            shell=True,
            cwd=test_dir,
            capture_output=True,
            text=True,
            timeout=120,  # 2Text Item
            env=env
        )
        
        # Report (Item Test Application Analysis)
        actual_success = analyze_test_result(result.stdout, result.stderr, result.returncode)
        
        save_test_result(test_type, {
            'success': actual_success,
            'command': java_cmd,
            'file_path': relative_path,
            'full_path': xml_file_path,
            'test_dir': test_dir,
            'db_type': db_type,
            'test_type': test_type,
            'compare_mode': compare,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode,
            'running': False
        })
    
    except subprocess.TimeoutExpired:
        save_test_result(test_type, {
            'success': False,
            'error': 'SQL Test Report (2Text)',
            'command': java_cmd,
            'file_path': relative_path,
            'db_type': db_type,
            'test_type': test_type,
            'running': False
        })
    except Exception as e:
        save_test_result(test_type, {
            'success': False,
            'error': f'SQL Test Execute Error: {str(e)}',
            'db_type': db_type,
            'test_type': test_type,
            'running': False
        })


def extract_test_summary(stdout):
    """Test Report Info Item"""
    try:
        if not stdout:
            return None
        
        lines = stdout.split('\n')
        summary_info = []
        
        for line in lines:
            line = line.strip()
            if any(keyword in line for keyword in ['Item Test Item:', 'Item Execute:', 'Item:', 'Item:', 'Report:']):
                summary_info.append(line)
        
        if summary_info:
            return ' | '.join(summary_info)
        
        return None
        
    except Exception:
        return None


def analyze_test_result(stdout, stderr, return_code):
    """Item Test Item AnalysisText Item/Report"""
    try:
        # stdoutText Report Item
        if not stdout:
            return False
        
        stdout_lower = stdout.lower()
        
        # Execute Report Item Check
        if "Execute Report" in stdout or "Report" in stdout:
            # Item 0%Report
            if "Report: 0.0%" in stdout or "Item: 0Text" in stdout:
                return False
            
            # Report Check
            import re
            failure_match = re.search(r'Item:\s*(\d+)Item', stdout)
            if failure_match:
                failure_count = int(failure_match.group(1))
                if failure_count > 0:
                    return False
            
            # Report Check
            success_match = re.search(r'Item:\s*(\d+)Item', stdout)
            if success_match:
                success_count = int(success_match.group(1))
                if success_count > 0:
                    return True
        
        # Report/Report Check
        failure_keywords = [
            'failed', 'error', 'exception', 'failure',
            'Item', 'Error', 'Item', 'SQLException'
        ]
        
        success_keywords = [
            'success', 'completed', 'passed',
            'Item', 'Complete', 'Item'
        ]
        
        # Report Report
        for keyword in failure_keywords:
            if keyword in stdout_lower:
                return False
        
        # stderrText Item ErrorText Report
        if stderr:
            stderr_lower = stderr.lower()
            critical_errors = ['exception', 'error', 'failed', 'SQLException']
            for error in critical_errors:
                if error in stderr_lower:
                    return False
        
        # Report Report
        for keyword in success_keywords:
            if keyword in stdout_lower:
                return True
        
        # Report Report
        return return_code == 0
        
    except Exception as e:
        # Analysis Item Error Report Report Item
        return return_code == 0


def get_target_db_display_info(target_dbms_type):
    """Target Report Item display Info Item"""
    db_info = {
        'postgresql': {'name': 'PostgreSQL', 'icon': '🐘'},
        'postgres': {'name': 'PostgreSQL', 'icon': '🐘'},
        'mysql': {'name': 'MySQL', 'icon': '🐬'},
        'mariadb': {'name': 'MariaDB', 'icon': '🦭'},
        'sqlite': {'name': 'SQLite', 'icon': '📦'}
    }
    
    return db_info.get(target_dbms_type.lower(), {'name': target_dbms_type.upper(), 'icon': '🗄️'})


def save_test_result(test_type, result):
    """Test Report Item"""
    if test_type == "source":
        st.session_state.oracle_test_result = result
    elif test_type == "target":
        st.session_state.target_test_result = result
    elif test_type == "validation_source":
        st.session_state.validation_oracle_test_result = result
    elif test_type == "validation_target":
        st.session_state.validation_target_test_result = result


def display_dual_test_results(target_db_name):
    """OracleText Target DB Test Report display"""
    col1, col2 = st.columns(2)
    
    with col1:
        if hasattr(st.session_state, 'oracle_test_result') and st.session_state.oracle_test_result:
            display_single_test_result_without_output(st.session_state.oracle_test_result, "Oracle", "oracle")
    
    with col2:
        if hasattr(st.session_state, 'target_test_result') and st.session_state.target_test_result:
            display_single_test_result_without_output(st.session_state.target_test_result, target_db_name, "target")
    
    # JSON Report display
    display_json_comparison_results()
    
    # Report display (JSON Report)
    display_test_outputs(target_db_name)


def display_json_comparison_results():
    """JSON Report display"""
    oracle_result = getattr(st.session_state, 'oracle_test_result', None)
    target_result = getattr(st.session_state, 'target_test_result', None)
    
    if not oracle_result and not target_result:
        return
    
    oracle_json = None
    target_json = None
    
    if oracle_result:
        oracle_json = parse_json_from_output(oracle_result.get('stdout', ''))
    
    if target_result:
        target_json = parse_json_from_output(target_result.get('stdout', ''))
    
    st.markdown("---")
    st.markdown("#### 📊 JSON Report")
    
    # Row Count Info display
    display_row_count_summary(oracle_json, target_json)
    
    # 1Text Report
    display_first_row_comparison(oracle_json, target_json)
    
    # Item JSON Item (Item Status)
    with st.expander("🔍 Item JSON Item", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Oracle JSON Item**")
            if oracle_json:
                st.json(oracle_json)
            if True:  # English only
                st.info("JSON Report")
        
        with col2:
            st.markdown("**Target JSON Item**")
            if target_json:
                st.json(target_json)
            if True:  # English only
                st.info("JSON Report")
        
        # Application Analysis
        if oracle_json and target_json:
            display_json_comparison_analysis(oracle_json, target_json)


def parse_json_from_output(output):
    """Item JSON File Report JSON Item"""
    if not output:
        return None
    
    import json
    import re
    import os
    
    # JSON File Report
    json_file_pattern = r'JSON Item File Create: (.+\.json)'
    match = re.search(json_file_pattern, output)
    
    if match:
        json_file_path = match.group(1)
        
        # Report Report Sample Transform
        if not os.path.isabs(json_file_path):
            # Test Report Report
            app_tools_folder = os.getenv('APP_TOOLS_FOLDER', '')
            if app_tools_folder:
                test_dir = os.path.join(app_tools_folder, '..', 'test')
                json_file_path = os.path.join(test_dir, json_file_path)
        
        # JSON File Item
        try:
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"JSON File Item Error: {e}")
    
    return None


def display_first_row_comparison(oracle_json, target_json):
    """Report Report Report"""
    oracle_first_row = extract_first_row_data(oracle_json)
    target_first_row = extract_first_row_data(target_json)
    
    if oracle_first_row or target_first_row:
        st.markdown("**📋 1Text Item**")
        
        # Report TransformText Item
        oracle_columns = {}
        target_columns = {}
        
        if oracle_first_row:
            oracle_columns = {k.lower(): (k, v) for k, v in oracle_first_row.items()}
        if target_first_row:
            target_columns = {k.lower(): (k, v) for k, v in target_first_row.items()}
        
        # Report Item (Report)
        all_columns = set()
        all_columns.update(oracle_columns.keys())
        all_columns.update(target_columns.keys())
        
        if all_columns:
            # Report Item
            comparison_data = []
            for column_lower in sorted(all_columns):
                oracle_info = oracle_columns.get(column_lower, (column_lower, "N/A"))
                target_info = target_columns.get(column_lower, (column_lower, "N/A"))
                
                oracle_value = oracle_info[1]
                target_value = target_info[1]
                
                # Report Item display
                match_status = "✅" if oracle_value == target_value else "❌"
                
                # Report Item (Oracle Item, Item Target)
                display_column = oracle_info[0] if oracle_info[1] != "N/A" else target_info[0]
                
                comparison_data.append({
                    "Item": display_column,
                    "Oracle": oracle_value,
                    "Target": target_value,
                    "Item": match_status
                })
            
            # Item display
            import pandas as pd
            df = pd.DataFrame(comparison_data)
            st.dataframe(df, use_container_width=True, hide_index=True)


def extract_first_row_data(json_data):
    """JSONText Report Report Item"""
    if not json_data:
        return None
    
    # successfulTests[0].resultData.data[0] Report
    if isinstance(json_data, dict) and 'successfulTests' in json_data:
        successful_tests = json_data['successfulTests']
        if isinstance(successful_tests, list) and len(successful_tests) > 0:
            first_test = successful_tests[0]
            if isinstance(first_test, dict) and 'resultData' in first_test:
                result_data = first_test['resultData']
                if isinstance(result_data, dict) and 'data' in result_data:
                    data_array = result_data['data']
                    if isinstance(data_array, list) and len(data_array) > 0:
                        return data_array[0]
    
    return None


def display_row_count_summary(oracle_json, target_json):
    """Row Count Item Info display"""
    oracle_count = extract_row_count(oracle_json)
    target_count = extract_row_count(target_json)
    
    if oracle_count is not None or target_count is not None:
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if oracle_count is not None:
                st.metric("Oracle Row Count", oracle_count)
        
        with col2:
            if target_count is not None:
                st.metric("Target Row Count", target_count)
        
        with col3:
            if oracle_count is not None and target_count is not None:
                if oracle_count == target_count:
                    st.success(f"✅ Row Count Item: {oracle_count}")
                if True:  # English only
                    st.error(f"❌ Row Count Item: Oracle({oracle_count}) vs Target({target_count})")


def extract_row_count(json_data):
    """JSONText Row Count Item"""
    if not json_data:
        return None
    
    # successfulTests Item rowCount Item
    if isinstance(json_data, dict) and 'successfulTests' in json_data:
        successful_tests = json_data['successfulTests']
        if isinstance(successful_tests, list) and len(successful_tests) > 0:
            first_test = successful_tests[0]
            if isinstance(first_test, dict):
                # rowCount Report
                if 'rowCount' in first_test:
                    return first_test['rowCount']
                # resultData.countText Item
                if 'resultData' in first_test and isinstance(first_test['resultData'], dict):
                    if 'count' in first_test['resultData']:
                        return first_test['resultData']['count']
    
    # Report Item
    if isinstance(json_data, dict):
        for key in ['rowCount', 'row_count', 'totalRows', 'count']:
            if key in json_data:
                return json_data[key]
        
        for value in json_data.values():
            if isinstance(value, dict):
                count = extract_row_count(value)
                if count is not None:
                    return count
    
    return None


def display_json_comparison_analysis(oracle_json, target_json):
    """JSON Application Analysis display"""
    st.markdown("**🔍 Application Analysis**")
    
    differences = []
    
    # Report Item
    if type(oracle_json) != type(target_json):
        differences.append(f"Report Item: Oracle({type(oracle_json).__name__}) vs Target({type(target_json).__name__})")
    
    # Report Report
    if isinstance(oracle_json, dict) and isinstance(target_json, dict):
        oracle_keys = set(oracle_json.keys())
        target_keys = set(target_json.keys())
        
        if oracle_keys != target_keys:
            only_oracle = oracle_keys - target_keys
            only_target = target_keys - oracle_keys
            
            if only_oracle:
                differences.append(f"OracleText Report: {list(only_oracle)}")
            if only_target:
                differences.append(f"TargetText Report: {list(only_target)}")
    
    # ListText Report Item
    if isinstance(oracle_json, list) and isinstance(target_json, list):
        if len(oracle_json) != len(target_json):
            differences.append(f"Report Item: Oracle({len(oracle_json)}) vs Target({len(target_json)})")
    
    if differences:
        for diff in differences:
            st.warning(f"⚠️ {diff}")
    if True:  # English only
        st.success("✅ Report Item")


def display_test_outputs(target_db_name):
    """Test Report Item display"""
    oracle_result = getattr(st.session_state, 'oracle_test_result', None)
    target_result = getattr(st.session_state, 'target_test_result', None)
    
    if not oracle_result and not target_result:
        return
    
    # Report Item StatusText display
    with st.expander("📤 Test Report", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            if oracle_result:
                st.markdown("**Oracle Item**")
                if oracle_result.get('stdout'):
                    with st.expander("📤 Report", expanded=False):
                        st.code(oracle_result['stdout'], language=None)
                if oracle_result.get('stderr'):
                    with st.expander("⚠️ Report", expanded=False):
                        st.code(oracle_result['stderr'], language=None)
        
        with col2:
            if target_result:
                st.markdown(f"**{target_db_name} Item**")
                if target_result.get('stdout'):
                    with st.expander("📤 Report", expanded=False):
                        st.code(target_result['stdout'], language=None)
                if target_result.get('stderr'):
                    with st.expander("⚠️ Report", expanded=False):
                        st.code(target_result['stderr'], language=None)


def display_single_test_result_without_output(result, db_name, result_key):
    """Report Item Test Item display"""
    st.markdown(f"#### 🧪 {db_name} Test Item")
    
    # Execute Item display
    if result.get('running'):
        st.info(f"🔄 {db_name} Test Execute Item... (Item 2Text)")
        return
    
    # Test File Item DB Info
    if 'file_path' in result:
        st.caption(f"**File:** {result['file_path']}")
    if 'db_type' in result:
        st.caption(f"**DB:** {result['db_type'].upper()}")
    
    # Item/Item Status
    if result.get('success') is True:
        st.success("✅ Test Item!")
        # Item Info Report display
        if result.get('stdout'):
            success_info = extract_test_summary(result['stdout'])
            if success_info:
                st.info(f"📊 {success_info}")
    elif result.get('success') is False:
        st.error("❌ Test Item!")
        # Item Info Report display
        if result.get('stdout'):
            failure_info = extract_test_summary(result['stdout'])
            if failure_info:
                st.warning(f"📊 {failure_info}")
    
    # Report
    if result.get('error'):
        st.error(f"**Error:** {result['error']}")
    
    # Report
    if 'return_code' in result:
        if result['return_code'] == 0:
            st.success(f"**Report:** {result['return_code']} (Report)")
        if True:  # English only
            st.error(f"**Report:** {result['return_code']} (Report)")


def display_single_test_result(result, db_name, result_key):
    """Item Test Item display"""
    st.markdown(f"#### 🧪 {db_name} Test Item")
    
    # Execute Item display
    if result.get('running'):
        st.info(f"🔄 {db_name} Test Execute Item... (Item 2Text)")
        return
    
    # Test File Item DB Info
    if 'file_path' in result:
        st.markdown(f"**📄 File:** `{os.path.basename(result['file_path'])}`")
    
    if 'db_type' in result:
        st.markdown(f"**🗄️ DB:** `{result['db_type'].upper()}`")
    
    # Item Info (Item display)
    if 'command' in result:
        st.markdown("**💻 Command:**")
        st.code(f"$ cd {result.get('test_dir', '')}\n$ {result['command']}", language="bash")
    
    # Item Status (Application Analysis)
    if result.get('success') is True:
        st.success("✅ Test Item!")
        # Item Info Report display
        if result.get('stdout'):
            success_info = extract_test_summary(result['stdout'])
            if success_info:
                st.info(f"📊 {success_info}")
    elif result.get('success') is False:
        st.error("❌ Test Item!")
        # Item Info Report display
        if result.get('stdout'):
            failure_info = extract_test_summary(result['stdout'])
            if failure_info:
                st.warning(f"📊 {failure_info}")
    
    # Report Report Item
    if 'return_code' in result:
        code_success = result['return_code'] == 0
        actual_success = result.get('success', False)
        
        if code_success != actual_success:
            st.warning(f"⚠️ Report({result['return_code']})Report Report!")
        
        if result['return_code'] == 0:
            st.success(f"**Report:** {result['return_code']} (Report)")
        if True:  # English only
            st.error(f"**Report:** {result['return_code']} (Report)")
    
    # Report (Item StatusText display)
    if result.get('stdout'):
        with st.expander("📤 Report", expanded=False):
            st.code(result['stdout'], language=None)
    
    # Report (Item display)
    if result.get('stderr'):
        st.markdown("**📥 Report:**")
        st.code(result['stderr'], language=None)
    
    # Report
    if result.get('error'):
        st.error(f"**Error:** {result['error']}")
    
    # Report Item
    if st.button(f"🧹 {db_name} Report", key=f"clear_{result_key}_result"):
        if result_key == "oracle" and hasattr(st.session_state, 'oracle_test_result'):
            del st.session_state.oracle_test_result
        elif result_key == "target" and hasattr(st.session_state, 'target_test_result'):
            del st.session_state.target_test_result
        elif result_key == "validation_oracle" and hasattr(st.session_state, 'validation_oracle_test_result'):
            del st.session_state.validation_oracle_test_result
        elif result_key == "validation_target" and hasattr(st.session_state, 'validation_target_test_result'):
            del st.session_state.validation_target_test_result
        elif result_key == "postgresql" and hasattr(st.session_state, 'postgresql_test_result'):
            del st.session_state.postgresql_test_result
        st.rerun()


def display_test_result():
    """Test Item display"""
    result = st.session_state.sql_test_result
    
    st.markdown("#### 🧪 SQL Test Item")
    
    # Execute Item display
    if result.get('running'):
        st.info("🔄 SQL Test Execute Item... (Item 2Text)")
        return
    
    # Test File Item DB Info
    col1, col2 = st.columns(2)
    with col1:
        if 'file_path' in result:
            st.markdown(f"**📄 Test File:** `{result['file_path']}`")
    with col2:
        if 'db_type' in result:
            st.markdown(f"**🗄️ Item:** `{result['db_type'].upper()}`")
    
    # Item Info
    if 'command' in result:
        st.markdown("**💻 Command:**")
        st.code(f"$ cd {result.get('test_dir', '')}\n$ {result['command']}", language="bash")
    
    # Item Status
    if result.get('success') is True:
        st.success("✅ SQL Test Item!")
    elif result.get('success') is False:
        st.error("❌ SQL Test Item!")
    
    # Report (Item StatusText display)
    if result.get('stdout'):
        with st.expander("📤 Report", expanded=False):
            st.code(result['stdout'], language=None)
    
    # Report
    if result.get('stderr'):
        st.markdown("**📥 Report:**")
        st.code(result['stderr'], language=None)
    
    # Report
    if result.get('error'):
        st.error(f"**Error:** {result['error']}")
    
    # Report
    if 'return_code' in result:
        if result['return_code'] == 0:
            st.success(f"**Report:** {result['return_code']} (Item)")
        if True:  # English only
            st.error(f"**Report:** {result['return_code']} (Item)")
    
    # Report Item
    if st.button("🧹 Report", key="clear_test_result"):
        if hasattr(st.session_state, 'sql_test_result'):
            del st.session_state.sql_test_result
        st.rerun()
