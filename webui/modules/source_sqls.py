"""
Compare SQL Test Page - XML File List and SQL Testing
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
    """Compare SQL Test page"""
    # Add Home button at the top
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Home", key="source_sqls_home"):
            st.session_state.selected_action = None
            st.rerun()
    with col2:
        st.markdown("## ⚖️ Compare SQL Test")
    
    # Check environment variables
    app_logs_folder = os.getenv('APP_LOGS_FOLDER')
    if not app_logs_folder:
        st.error("❌ APP_LOGS_FOLDER environment variable is not set.")
        return
    
    # XML File Path
    xml_pattern = os.path.join(app_logs_folder, 'mapper', '**', 'extract', '*.xml')
    xml_files = glob.glob(xml_pattern, recursive=True)
    
    if not xml_files:
        st.warning(f"⚠️ XML files not found: {xml_pattern}")
        st.info("Please check the path or run mapper analysis first.")
        return
    
    # Display search filters and file list side by side
    with st.expander("🔍 Search and File List", expanded=True):
        # CSS for compact font
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
        
        # Left-right split: left filters, right file list
        col_filter, col_files = st.columns([1, 2])
        
        with col_filter:
            st.markdown("#### 🔍 Search Filters")
            st.markdown('<div class="compact-filter">', unsafe_allow_html=True)
            
            search_text = st.text_input(
                "Filename Search",
                placeholder="Enter filename...",
                key="xml_search"
            )
            
            search_path = st.text_input(
                "Path Search", 
                placeholder="Enter path...",
                key="path_search"
            )
            
            sql_type = st.selectbox(
                "SQL Type",
                ["All", "select", "insert", "update", "delete"],
                key="sql_type_filter"
            )
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                apply_filter = st.button("🔍 Filter", use_container_width=True)
            with col_btn2:
                reset_filter = st.button("🔄 Reset", use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_files:
            st.markdown("#### 📁 File List")
            
            # Apply filters
            filtered_files = apply_simple_file_filters(
                xml_files, app_logs_folder, search_text, search_path, 
                sql_type, apply_filter, reset_filter
            )
            
            # Display file count
            st.markdown(f'<p style="font-size: 11px; color: #666; margin: 5px 0;">Showing {len(filtered_files)} of {len(xml_files)} files</p>', unsafe_allow_html=True)
            
            # File list (display in table format only)
            if filtered_files:
                display_simple_file_table(filtered_files, app_logs_folder)
            else:
                st.info("No files match the criteria.")
    
    # Bottom area organized with tabs
    if hasattr(st.session_state, 'selected_xml_file') and st.session_state.selected_xml_file:
        display_tabbed_content(st.session_state.selected_xml_file)
    else:
        st.info("👆 Please select an XML file from above.")


def display_explorer_style_list(xml_files, base_path):
    """Display file list in Windows Explorer style"""
    
    # Organize file info into dataframe
    file_data = []
    for xml_file in xml_files:
        file_name = os.path.basename(xml_file)
        relative_path = os.path.relpath(xml_file, base_path)
        dir_path = os.path.dirname(relative_path)
        file_size = os.path.getsize(xml_file)
        file_mtime = os.path.getmtime(xml_file)
        
        # Format modification time
        mod_time = datetime.datetime.fromtimestamp(file_mtime).strftime("%m/%d %H:%M")
        
        file_data.append({
            '📄': '📄',  # File icon
            'Filename': file_name,
            'Path': dir_path if dir_path != '.' else '/',
            'Size': format_file_size(file_size),
            'Modified': mod_time,
            '_full_path': xml_file,
            '_sort_size': file_size,
            '_sort_time': file_mtime
        })
    
    if not file_data:
        return
    
    df = pd.DataFrame(file_data)
    
    # Place quick selection above table (small font)
    st.markdown('<p style="font-size: 12px; font-weight: bold; margin: 8px 0 4px 0;">Quick Selection:</p>', unsafe_allow_html=True)
    file_options = [f"{row['Filename']} ({row['Path']})" for _, row in df.iterrows()]
    
    # Find index of currently selected file
    current_selection = 0
    if hasattr(st.session_state, 'selected_xml_file') and st.session_state.selected_xml_file:
        for i, (_, row) in enumerate(df.iterrows()):
            if row['_full_path'] == st.session_state.selected_xml_file:
                current_selection = i
                break
    
    # Create key for selectbox change detection
    selectbox_key = f"quick_file_selector_{len(xml_files)}"
    
    selected_index = st.selectbox(
        "Select File:",
        range(len(file_options)),
        index=current_selection,
        format_func=lambda x: file_options[x] if x < len(file_options) else "",
        key=selectbox_key,
        label_visibility="collapsed"
    )
    
    # Handle selectbox selection (immediate reflection)
    if selected_index is not None and selected_index < len(df):
        selected_file = df.iloc[selected_index]['_full_path']
        if not hasattr(st.session_state, 'selected_xml_file') or st.session_state.selected_xml_file != selected_file:
            st.session_state.selected_xml_file = selected_file
            # Initialize SQL test result (when new file is selected)
            if hasattr(st.session_state, 'sql_test_result'):
                del st.session_state.sql_test_result
            st.rerun()
    
    # CSS for styling (smaller font)
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
    
    # Compact table container
    st.markdown('<div class="compact-table">', unsafe_allow_html=True)
    
    # Display in table format (clickable)
    display_df = df[['📄', 'Filename', 'Path', 'Size', 'Modified']].copy()
    
    # Style function for highlighting currently selected file
    def highlight_selected_row(row):
        if hasattr(st.session_state, 'selected_xml_file'):
            current_file = df[df['Filename'] == row['Filename']]['_full_path'].iloc[0]
            if st.session_state.selected_xml_file == current_file:
                return ['background-color: #e3f2fd; font-weight: bold'] * len(row)
        return [''] * len(row)
    
    # Selectable table (improved event handling)
    event = st.dataframe(
        display_df.style.apply(highlight_selected_row, axis=1),
        use_container_width=True,
        height=200,  # Reduced from 250px to 200px
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"file_table_{len(xml_files)}"
    )
    
    # Close compact table container
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Handle table selection event
    if event and hasattr(event, 'selection') and event.selection and 'rows' in event.selection:
        if event.selection['rows']:
            selected_row_index = event.selection['rows'][0]
            if selected_row_index < len(df):
                selected_file = df.iloc[selected_row_index]['_full_path']
                if not hasattr(st.session_state, 'selected_xml_file') or st.session_state.selected_xml_file != selected_file:
                    st.session_state.selected_xml_file = selected_file
                    # Initialize SQL test result (when new file is selected)
                    if hasattr(st.session_state, 'sql_test_result'):
                        del st.session_state.sql_test_result
                    st.rerun()


def display_tabbed_content(xml_file_path):
    """Display content organized in 3 tabs"""
    try:
        file_name = os.path.basename(xml_file_path)
        target_xml_path = get_target_xml_path(xml_file_path)
        
        # Configure 2 tabs
        tab1, tab2 = st.tabs(["📄 XML Comparison", "🧪 SQL Test"])
        
        with tab1:
            # XML file comparison
            display_xml_comparison_section(xml_file_path, target_xml_path, file_name)
            
            # Text diff (within same tab)
            if target_xml_path and os.path.exists(target_xml_path):
                st.markdown("---")
                display_text_diff_section(xml_file_path, target_xml_path)
        
        with tab2:
            # Test parameters (for SQL test)
            display_parameter_section(xml_file_path, form_key="sql_test")
            
            # SQL Test (within same tab)
            st.markdown("---")
            display_sql_test_section(xml_file_path, target_xml_path, test_type="sql")
            
    except Exception as e:
        st.error(f"❌ Content display error: {str(e)}")


def display_xml_comparison_section(xml_file_path, target_xml_path, file_name):
    """XML comparison section"""
    # 2-column layout: left Source XML, right Target XML
    col1, col2 = st.columns(2)
    
    with col1:
        source_lines = count_xml_lines(xml_file_path)
        st.markdown(f"#### 📄 Source XML ({source_lines} lines)")
        st.caption(f"File: {file_name}")
        display_single_xml(xml_file_path, height=400)
    
    with col2:
        if target_xml_path and os.path.exists(target_xml_path):
            target_lines = count_xml_lines(target_xml_path)
            st.markdown(f"#### 🎯 Target XML ({target_lines} lines)")
            target_file_name = os.path.basename(target_xml_path)
            st.caption(f"File: {target_file_name}")
            display_single_xml(target_xml_path, height=400)
        else:
            st.markdown("#### 🎯 Target XML")
            st.caption("Target XML not found.")
            if target_xml_path:
                st.info(f"Expected path: {target_xml_path}")
            else:
                st.info("Cannot calculate target path.")


def display_text_diff_section(xml_file_path, target_xml_path):
    """Text diff section"""
    # Text diff buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("🔍 Text Diff", key="text_diff_btn", use_container_width=True):
            st.session_state.show_text_diff = True
            st.rerun()
    with col2:
        if st.button("📄 Individual View", key="individual_view_btn", use_container_width=True):
            st.session_state.show_text_diff = False
            st.rerun()
    with col3:
        if hasattr(st.session_state, 'show_text_diff') and st.session_state.show_text_diff:
            if st.button("🙈 Hide Diff", key="hide_diff_btn", use_container_width=True):
                st.session_state.show_text_diff = False
                st.rerun()
        else:
            st.button("🙈 Hide Diff", key="hide_diff_btn_disabled", disabled=True, use_container_width=True)
    with col4:
        st.caption("Compare text file differences")
    
    # Display text diff result
    if hasattr(st.session_state, 'show_text_diff') and st.session_state.show_text_diff:
        display_text_diff(xml_file_path, target_xml_path)


def display_sql_test_section(xml_file_path, target_xml_path, test_type="sql"):
    """SQL test section"""
    # Determine target database type
    target_dbms_type = os.getenv('TARGET_DBMS_TYPE', 'postgresql')
    target_db_display = get_target_db_display_info(target_dbms_type)
    
    # Integrated SQL test button
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🧪 Full SQL Test", key="full_sql_test_btn", type="primary", use_container_width=True):
            # Oracle Test Execute
            execute_sql_test(xml_file_path, "oracle", "source")
            
            # Execute target test (if target XML exists)
            if target_xml_path and os.path.exists(target_xml_path):
                execute_sql_test(target_xml_path, target_dbms_type, "target")
            
            st.rerun()
    
    with col2:
        if st.button("🧹 Clear Results", key="clear_all_results_btn", use_container_width=True):
            if hasattr(st.session_state, 'oracle_test_result'):
                del st.session_state.oracle_test_result
            if hasattr(st.session_state, 'target_test_result'):
                del st.session_state.target_test_result
            st.rerun()
    
    with col3:
        test_info = f"Oracle + {target_db_display['name']} simultaneous test"
        if not target_xml_path or not os.path.exists(target_xml_path):
            test_info += " (No Target XML - Oracle only test)"
        st.caption(test_info)
    
    # Display test results
    display_dual_test_results(target_db_display['name'])


def display_simple_file_table(xml_files, base_path):
    """Display file list in simple table format"""
    
    # Organize file info into dataframe
    file_data = []
    for xml_file in xml_files:
        file_name = os.path.basename(xml_file)
        file_size = os.path.getsize(xml_file)
        
        file_data.append({
            'Filename': file_name,
            'Size': format_file_size(file_size),
            '_full_path': xml_file
        })
    
    if not file_data:
        return
    
    df = pd.DataFrame(file_data)
    
    # Find index of currently selected file
    current_selection = 0
    if hasattr(st.session_state, 'selected_xml_file') and st.session_state.selected_xml_file:
        for i, (_, row) in enumerate(df.iterrows()):
            if row['_full_path'] == st.session_state.selected_xml_file:
                current_selection = i
                break
    
    # Function to highlight selected row
    def highlight_selected_row(row):
        if hasattr(st.session_state, 'selected_xml_file'):
            current_file = df[df['Filename'] == row['Filename']]['_full_path'].iloc[0]
            if st.session_state.selected_xml_file == current_file:
                return ['background-color: #e3f2fd; font-weight: bold'] * len(row)
        return [''] * len(row)
    
    # Display table (Filename and Size only)
    display_df = df[['Filename', 'Size']].copy()
    
    # Selectable table
    event = st.dataframe(
        display_df.style.apply(highlight_selected_row, axis=1),
        use_container_width=True,
        height=300,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"simple_file_table_{len(xml_files)}"
    )
    
    # Handle table selection event
    if event and hasattr(event, 'selection') and event.selection and 'rows' in event.selection:
        if event.selection['rows']:
            selected_row_index = event.selection['rows'][0]
            if selected_row_index < len(df):
                selected_file = df.iloc[selected_row_index]['_full_path']
                if not hasattr(st.session_state, 'selected_xml_file') or st.session_state.selected_xml_file != selected_file:
                    st.session_state.selected_xml_file = selected_file
                    # Initialize SQL test result
                    if hasattr(st.session_state, 'oracle_test_result'):
                        del st.session_state.oracle_test_result
                    if hasattr(st.session_state, 'target_test_result'):
                        del st.session_state.target_test_result
                    st.rerun()


def apply_simple_file_filters(xml_files, base_path, search_text, search_path, sql_type, apply_filter, reset_filter):
    """Apply simplified file filters"""
    
    # Initialize filters
    if reset_filter:
        if 'xml_search' in st.session_state:
            st.session_state.xml_search = ""
        if 'path_search' in st.session_state:
            st.session_state.path_search = ""
        if 'sql_type_filter' in st.session_state:
            st.session_state.sql_type_filter = "All"
        st.rerun()
    
    filtered_files = xml_files.copy()
    
    # Filename search filter
    if search_text:
        filtered_files = [
            f for f in filtered_files 
            if search_text.lower() in os.path.basename(f).lower()
        ]
    
    # Path search filter
    if search_path:
        filtered_files = [
            f for f in filtered_files 
            if search_path.lower() in os.path.relpath(f, base_path).lower()
        ]
    
    # SQL Type filter (based on filename)
    if sql_type and sql_type != "All":
        filtered_files = [
            f for f in filtered_files 
            if sql_type.lower() in os.path.basename(f).lower()
        ]
    
    # Sort by filename (default)
    filtered_files.sort(key=lambda x: os.path.basename(x).lower())
    
    return filtered_files


def display_compact_file_list(xml_files, base_path):
    """Display file list compactly in 2 columns"""
    
    # Organize file info into list
    file_data = []
    for xml_file in xml_files:
        file_name = os.path.basename(xml_file)
        file_size = os.path.getsize(xml_file)
        
        file_data.append({
            'Filename': file_name,
            'Size': format_file_size(file_size),
            '_full_path': xml_file
        })
    
    if not file_data:
        return
    
    # Selectbox for quick selection
    st.markdown('<p style="font-size: 12px; font-weight: bold; margin: 8px 0 4px 0;">Quick Selection:</p>', unsafe_allow_html=True)
    file_options = [f"{item['Filename']} ({item['Size']})" for item in file_data]
    
    # Find index of currently selected file
    current_selection = 0
    if hasattr(st.session_state, 'selected_xml_file') and st.session_state.selected_xml_file:
        for i, item in enumerate(file_data):
            if item['_full_path'] == st.session_state.selected_xml_file:
                current_selection = i
                break
    
    selected_index = st.selectbox(
        "Select File:",
        range(len(file_options)),
        index=current_selection,
        format_func=lambda x: file_options[x] if x < len(file_options) else "",
        key=f"quick_file_selector_{len(xml_files)}",
        label_visibility="collapsed"
    )
    
    # Handle selectbox selection
    if selected_index is not None and selected_index < len(file_data):
        selected_file = file_data[selected_index]['_full_path']
        if not hasattr(st.session_state, 'selected_xml_file') or st.session_state.selected_xml_file != selected_file:
            st.session_state.selected_xml_file = selected_file
            # Initialize SQL test result
            if hasattr(st.session_state, 'oracle_test_result'):
                del st.session_state.oracle_test_result
            if hasattr(st.session_state, 'target_test_result'):
                del st.session_state.target_test_result
            st.rerun()
    
    # Display file list in 2 columns
    st.markdown('<p style="font-size: 12px; font-weight: bold; margin: 8px 0 4px 0;">File List:</p>', unsafe_allow_html=True)
    
    # Display files 2 at a time
    for i in range(0, len(file_data), 2):
        col1, col2 = st.columns(2)
        
        # First file
        with col1:
            item = file_data[i]
            is_selected = (hasattr(st.session_state, 'selected_xml_file') and 
                          st.session_state.selected_xml_file == item['_full_path'])
            
            button_style = "primary" if is_selected else "secondary"
            if st.button(
                f"📄 {item['Filename']}\n📏 {item['Size']}", 
                key=f"file_btn_{i}",
                use_container_width=True,
                type=button_style
            ):
                st.session_state.selected_xml_file = item['_full_path']
                # Initialize SQL test result
                if hasattr(st.session_state, 'oracle_test_result'):
                    del st.session_state.oracle_test_result
                if hasattr(st.session_state, 'target_test_result'):
                    del st.session_state.target_test_result
                st.rerun()
        
        # Second file (if exists)
        with col2:
            if i + 1 < len(file_data):
                item = file_data[i + 1]
                is_selected = (hasattr(st.session_state, 'selected_xml_file') and 
                              st.session_state.selected_xml_file == item['_full_path'])
                
                button_style = "primary" if is_selected else "secondary"
                if st.button(
                    f"📄 {item['Filename']}\n📏 {item['Size']}", 
                    key=f"file_btn_{i+1}",
                    use_container_width=True,
                    type=button_style
                ):
                    st.session_state.selected_xml_file = item['_full_path']
                    # Initialize SQL test result
                    if hasattr(st.session_state, 'oracle_test_result'):
                        del st.session_state.oracle_test_result
                    if hasattr(st.session_state, 'target_test_result'):
                        del st.session_state.target_test_result
                    st.rerun()


def apply_file_filters(xml_files, base_path, search_text, search_path, min_size, max_size, sort_by, sort_order, apply_filter, reset_filter):
    """Apply file filters"""
    
    # Initialize filters
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
    
    # Filename search filter
    if search_text:
        filtered_files = [
            f for f in filtered_files 
            if search_text.lower() in os.path.basename(f).lower()
        ]
    
    # Path search filter
    if search_path:
        filtered_files = [
            f for f in filtered_files 
            if search_path.lower() in os.path.relpath(f, base_path).lower()
        ]
    
    # Size filter
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
    
    # Apply sorting
    if sort_by == "Filename":
        filtered_files.sort(key=lambda x: os.path.basename(x).lower())
    elif sort_by == "Path":
        filtered_files.sort(key=lambda x: os.path.relpath(x, base_path).lower())
    elif sort_by == "Size":
        filtered_files.sort(key=lambda x: os.path.getsize(x))
    elif sort_by == "ModifyTime":
        filtered_files.sort(key=lambda x: os.path.getmtime(x))
    
    # Sort order
    if sort_order == "Descending":
        filtered_files.reverse()
    
    return filtered_files


def build_tree_structure(xml_files, base_path):
    """Create tree structure from XML files"""
    tree = {}
    
    for xml_file in xml_files:
        # Calculate relative path
        rel_path = os.path.relpath(xml_file, base_path)
        path_parts = rel_path.split(os.sep)
        
        # Add path to tree structure
        current_level = tree
        for i, part in enumerate(path_parts):
            if part not in current_level:
                if i == len(path_parts) - 1:  # If it's a file
                    current_level[part] = {
                        '_type': 'file',
                        '_path': xml_file,
                        '_size': os.path.getsize(xml_file)
                    }
                else:  # If it's a directory
                    current_level[part] = {'_type': 'directory'}
            
            if current_level[part]['_type'] == 'directory':
                current_level = current_level[part]
    
    return tree


def display_tree_structure(tree, base_path, level=0, parent_key=""):
    """Display tree structure recursively"""
    for key, value in sorted(tree.items()):
        if key.startswith('_'):  # Skip metadata
            continue
        
        indent = "　" * level  # Indentation with full-width spaces
        current_key = f"{parent_key}_{key}" if parent_key else key
        
        if value['_type'] == 'directory':
            # Display directory
            folder_key = f"folder_{current_key}_{level}"
            
            # Calculate number of sub-files
            file_count = count_files_in_tree(value)
            
            with st.expander(f"{indent}📁 {key} ({file_count} files)", expanded=level < 2):
                display_tree_structure(value, base_path, level + 1, current_key)
        
        elif value['_type'] == 'file':
            # Display file
            file_size = value['_size']
            file_size_str = format_file_size(file_size)
            
            file_key = f"file_{current_key}_{level}"
            
            # File selection button
            if st.button(
                f"{indent}📄 {key} ({file_size_str})",
                key=file_key,
                use_container_width=True,
                help=f"Path: {os.path.relpath(value['_path'], base_path)}"
            ):
                st.session_state.selected_xml_file = value['_path']
                st.rerun()


def count_files_in_tree(tree_node):
    """Calculate number of files in tree node"""
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
    """Format file size in readable format"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f}KB"
    else:
        return f"{size_bytes/(1024*1024):.1f}MB"


def display_xml_content(xml_file_path):
    """Display XML file content - Source and Target 2-column layout"""
    try:
        file_name = os.path.basename(xml_file_path)
        
        # Calculate Target XML path
        target_xml_path = get_target_xml_path(xml_file_path)
        
        # 2-column layout: left Source XML, right Target XML
        col1, col2 = st.columns(2)
        
        with col1:
            source_lines = count_xml_lines(xml_file_path)
            st.markdown(f"#### 📄 Source XML ({source_lines} lines)")
            st.caption(f"File: {file_name}")
            display_single_xml(xml_file_path, height=400)
        
        with col2:
            if target_xml_path and os.path.exists(target_xml_path):
                target_lines = count_xml_lines(target_xml_path)
                st.markdown(f"#### 🎯 Target XML ({target_lines} lines)")
                target_file_name = os.path.basename(target_xml_path)
                st.caption(f"File: {target_file_name}")
                display_single_xml(target_xml_path, height=400)
            else:
                st.markdown("#### 🎯 Target XML")
                st.caption("Target XML not found.")
                if target_xml_path:
                    st.info(f"Expected path: {target_xml_path}")
                else:
                    st.info("Cannot calculate target path.")
        
        # SQL test parameter section
        st.markdown("---")
        display_parameter_section(xml_file_path)
        
        # Determine target database type
        target_dbms_type = os.getenv('TARGET_DBMS_TYPE', 'postgresql')
        target_db_display = get_target_db_display_info(target_dbms_type)
        
        # SQL test buttons (split into 2)
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🧪 Source SQL Test (Oracle)")
            if st.button("🗄️ Oracle Test", key="oracle_test_btn", type="primary", use_container_width=True):
                execute_sql_test(xml_file_path, "oracle", "source")
                st.rerun()
            st.caption("Test Source XML on Oracle database")
        
        with col2:
            st.markdown(f"#### 🧪 Target SQL Test ({target_db_display['name']})")
            if target_xml_path and os.path.exists(target_xml_path):
                if st.button(f"{target_db_display['icon']} {target_db_display['name']} Test", key="target_test_btn", type="primary", use_container_width=True):
                    execute_sql_test(target_xml_path, target_dbms_type, "target")
                    st.rerun()
                st.caption(f"Test Target XML on {target_db_display['name']} database")
            else:
                st.button(f"{target_db_display['icon']} {target_db_display['name']} Test", key="target_test_btn_disabled", disabled=True, use_container_width=True)
                st.caption("Cannot test because Target XML is missing")
        
        # Display test results (split into 2)
        display_dual_test_results(target_db_display['name'])
        
        # Text diff comparison buttons
        if target_xml_path and os.path.exists(target_xml_path):
            st.markdown("---")
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            with col1:
                if st.button("🔍 Text Diff", key="text_diff_btn", use_container_width=True):
                    st.session_state.show_text_diff = True
                    st.rerun()
            with col2:
                if st.button("📄 Individual View", key="individual_view_btn", use_container_width=True):
                    st.session_state.show_text_diff = False
                    st.rerun()
            with col3:
                if hasattr(st.session_state, 'show_text_diff') and st.session_state.show_text_diff:
                    if st.button("🙈 Hide Diff", key="hide_diff_btn", use_container_width=True):
                        st.session_state.show_text_diff = False
                        st.rerun()
                else:
                    st.button("🙈 Hide Diff", key="hide_diff_btn_disabled", disabled=True, use_container_width=True)
            with col4:
                st.caption("Compare text file differences")
        
        # Display text diff result
        if hasattr(st.session_state, 'show_text_diff') and st.session_state.show_text_diff and target_xml_path and os.path.exists(target_xml_path):
            display_text_diff(xml_file_path, target_xml_path)
    
    except Exception as e:
        st.error(f"❌ XML file reading error: {str(e)}")


def count_xml_lines(xml_file_path):
    """Calculate number of lines in XML file"""
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Count only lines with actual content, excluding empty lines
            non_empty_lines = [line for line in lines if line.strip()]
            return len(non_empty_lines)
    except Exception as e:
        return 0


def get_target_xml_path(source_xml_path):
    """Calculate Target XML path from Source XML path"""
    try:
        # Change path to ../transform/ path
        path_parts = source_xml_path.split(os.sep)
        
        # Change extract to transform
        if 'extract' in path_parts:
            extract_index = path_parts.index('extract')
            path_parts[extract_index] = 'transform'
        else:
            return None
        
        # Change src to tgt in filename
        file_name = path_parts[-1]
        if 'src' in file_name:
            target_file_name = file_name.replace('src', 'tgt')
            path_parts[-1] = target_file_name
        else:
            return None
        
        target_path = os.sep.join(path_parts)
        return target_path
        
    except Exception as e:
        st.warning(f"⚠️ Target XML path calculation error: {str(e)}")
        return None


def display_text_diff(source_file_path, target_file_path):
    """Display diff of Source and Target text files"""
    try:
        st.markdown("#### 🔍 Text Diff Comparison")
        
        # Read files
        with open(source_file_path, 'r', encoding='utf-8') as f:
            source_content = f.read()
        
        with open(target_file_path, 'r', encoding='utf-8') as f:
            target_content = f.read()
        
        # Split by lines
        source_lines = source_content.splitlines()
        target_lines = target_content.splitlines()
        
        # Statistics info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Source Lines", len(source_lines))
        with col2:
            st.metric("Target Lines", len(target_lines))
        with col3:
            line_diff = len(target_lines) - len(source_lines)
            st.metric("Line Difference", f"{line_diff:+d}")
        
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
        else:
            st.success("✅ The two files are identical!")
        
    except Exception as e:
        st.error(f"❌ Text diff comparison error: {str(e)}")


def display_single_xml(xml_file_path, height=400):
    """Display single XML file content"""
    try:
        # Read and display XML content
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # XML formatting (pretty display)
        try:
            # XML parsing and formatting
            root = ET.fromstring(xml_content)
            pretty_xml = minidom.parseString(xml_content).toprettyxml(indent="  ")
            # Remove XML declaration (first line)
            pretty_lines = pretty_xml.split('\n')[1:]
            formatted_xml = '\n'.join(line for line in pretty_lines if line.strip())
        except:
            # Use original if parsing fails
            formatted_xml = xml_content
        
        # Display XML content
        st.code(formatted_xml, language="xml", height=height)
        
    except Exception as e:
        st.error(f"❌ XML file reading error: {str(e)}")


def format_file_size(size_bytes):
    """Format file size in readable format"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f}KB"
    else:
        return f"{size_bytes/(1024*1024):.1f}MB"


def extract_parameters_from_xml(xml_file_path):
    """Extract MyBatis parameters from XML file"""
    parameters = set()
    
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # Extract parameters in #{parameter} format
        import re
        param_pattern = r'#\{([^}]+)\}'
        matches = re.findall(param_pattern, xml_content)
        
        for match in matches:
            # Extract parameter name only (remove type info etc.)
            param_name = match.split(',')[0].strip()
            if param_name:
                parameters.add(param_name)
        
        # Also extract parameters in ${parameter} format
        param_pattern2 = r'\$\{([^}]+)\}'
        matches2 = re.findall(param_pattern2, xml_content)
        
        for match in matches2:
            param_name = match.split(',')[0].strip()
            if param_name:
                parameters.add(param_name)
    
    except Exception as e:
        st.warning(f"⚠️ XML parameter extraction error: {str(e)}")
    
    return sorted(list(parameters))


def display_parameter_section(xml_file_path, form_key="default"):
    """Display SQL test parameter section"""
    st.markdown("#### ⚙️ Test Parameters")
    
    # Extract parameters from XML
    xml_parameters = extract_parameters_from_xml(xml_file_path)
    
    if not xml_parameters:
        st.info("📝 This XML file has no parameters.")
        return
    
    # Parameter file path
    test_folder = os.getenv('TEST_FOLDER')
    if not test_folder:
        st.error("❌ TEST_FOLDER environment variable is not set.")
        return
    
    param_file_path = os.path.join(test_folder, 'parameters.properties')
    
    # Load existing parameters
    existing_params = load_parameters(param_file_path)
    
    st.markdown(f"**📝 Discovered Parameters ({len(xml_parameters)} items):**")
    
    # Parameter input form
    with st.form(key=f"parameter_form_{form_key}"):
        # Dynamically create parameter input fields
        param_values = {}
        
        # Arrange in 2 columns
        cols = st.columns(2)
        for i, param_name in enumerate(xml_parameters):
            col_idx = i % 2
            with cols[col_idx]:
                # Guess parameter type
                param_type = guess_parameter_type(param_name)
                placeholder = get_parameter_placeholder(param_name, param_type)
                
                param_values[param_name] = st.text_input(
                    f"🔧 {param_name}",
                    value=existing_params.get(param_name, ''),
                    placeholder=placeholder,
                    help=f"Type: {param_type}"
                )
        
        # Save button
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            save_params = st.form_submit_button("💾 Save", type="primary")
        with col2:
            clear_params = st.form_submit_button("🧹 Reset")
        with col3:
            st.caption(f"File: {os.path.basename(param_file_path)}")
    
    # Handle parameter save
    if save_params:
        save_xml_parameters(param_file_path, param_values, xml_file_path)
        st.success(f"✅ Parameters have been saved! ({form_key})")
        st.rerun()
    
    # Handle parameter reset
    if clear_params:
        clear_parameters(param_file_path)
        st.success(f"✅ Parameters have been reset! ({form_key})")
        st.rerun()


def guess_parameter_type(param_name):
    """Guess type from parameter name"""
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
    else:
        return 'String'


def get_parameter_placeholder(param_name, param_type):
    """Create placeholder based on parameter type"""
    placeholders = {
        'ID': f'e.g.: {param_name.upper()}001',
        'Date': 'e.g.: 2024-01-01',
        'Number': 'e.g.: 10',
        'String': f'e.g.: {param_name} value',
        'Code': 'e.g.: ACTIVE',
        'Email': 'e.g.: test@example.com',
        'Phone': 'e.g.: 010-1234-5678'
    }
    return placeholders.get(param_type, f'e.g.: {param_name} value')


def save_xml_parameters(param_file_path, param_values, xml_file_path):
    """Save XML parameters to file"""
    try:
        # Create directory
        os.makedirs(os.path.dirname(param_file_path), exist_ok=True)
        
        xml_file_name = os.path.basename(xml_file_path)
        
        with open(param_file_path, 'w', encoding='utf-8') as f:
            f.write("# SQL Test Parameters\n")
            f.write(f"# Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# XML File: {xml_file_name}\n\n")
            
            # Save parameters extracted from XML
            for param_name, param_value in param_values.items():
                if param_value.strip():  # Save only non-empty values
                    f.write(f"{param_name}={param_value}\n")
    
    except Exception as e:
        st.error(f"❌ Parameter save error: {str(e)}")


def load_parameters(param_file_path):
    """Load parameters from parameter file"""
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
        st.warning(f"⚠️ Parameter file reading error: {str(e)}")
    
    return params


def clear_parameters(param_file_path):
    """Reset parameter file"""
    try:
        if os.path.exists(param_file_path):
            os.remove(param_file_path)
    except Exception as e:
        st.error(f"❌ Parameter reset error: {str(e)}")


def execute_sql_test(xml_file_path, db_type, test_type, compare=False):
    """Execute SQL test"""
    try:
        # Check environment variables
        app_tools_folder = os.getenv('APP_TOOLS_FOLDER')
        app_logs_folder = os.getenv('APP_LOGS_FOLDER')
        
        if not app_tools_folder:
            save_test_result(test_type, {
                'success': False,
                'error': 'APP_TOOLS_FOLDER environment variable is not set.'
            })
            return
        
        if not app_logs_folder:
            save_test_result(test_type, {
                'success': False,
                'error': 'APP_LOGS_FOLDER environment variable is not set.'
            })
            return
        
        # Test Directory
        test_dir = os.path.join(app_tools_folder, '..', 'test')
        if not os.path.exists(test_dir):
            save_test_result(test_type, {
                'success': False,
                'error': f'Test directory not found: {test_dir}'
            })
            return
        
        # Calculate relative path of file (based on APP_LOGS_FOLDER)
        relative_path = os.path.relpath(xml_file_path, app_logs_folder)
        
        # Construct Java command
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
        
        # Set environment variables
        env = dict(os.environ)
        env['APP_TOOLS_FOLDER'] = app_tools_folder
        env['APP_LOGS_FOLDER'] = app_logs_folder
        
        # Execute Java command
        result = subprocess.run(
            java_cmd,
            shell=True,
            cwd=test_dir,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
            env=env
        )
        
        # Save result (actual test result analysis)
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
            'error': 'SQL test timeout (2 minutes)',
            'command': java_cmd,
            'file_path': relative_path,
            'db_type': db_type,
            'test_type': test_type,
            'running': False
        })
    except Exception as e:
        save_test_result(test_type, {
            'success': False,
            'error': f'SQL test execution error: {str(e)}',
            'db_type': db_type,
            'test_type': test_type,
            'running': False
        })


def extract_test_summary(stdout):
    """Extract summary info from test result"""
    try:
        if not stdout:
            return None
        
        lines = stdout.split('\n')
        summary_info = []
        
        for line in lines:
            line = line.strip()
            if any(keyword in line for keyword in ['Total Tests:', 'Actual Execution:', 'Success:', 'Failed:', 'Actual Success Rate:']):
                summary_info.append(line)
        
        if summary_info:
            return ' | '.join(summary_info)
        
        return None
        
    except Exception:
        return None


def analyze_test_result(stdout, stderr, return_code):
    """Analyze actual test result to determine success/failure"""
    try:
        # Consider as failure if no stdout
        if not stdout:
            return False
        
        # Check success rate from execution result summary (PRIORITY CHECK)
        if "Execution Results Summary" in stdout or "Actual success rate" in stdout:
            import re
            
            # Check failure count first
            failure_match = re.search(r'Failed:\s*(\d+)\s*(items|tests)', stdout)
            if failure_match:
                failure_count = int(failure_match.group(1))
                if failure_count > 0:
                    return False
            
            # Check success count
            success_match = re.search(r'Success:\s*(\d+)\s*(items|tests)', stdout)
            if success_match:
                success_count = int(success_match.group(1))
                if success_count > 0:
                    return True
            
            # Failure if success rate is 0%
            if "Actual success rate: 0.0%" in stdout or re.search(r'Success:\s*0\s*(items|tests)', stdout):
                return False
        
        # Final judgment by exit code
        return return_code == 0
        
    except Exception as e:
        # Judge by exit code if error occurs during analysis
        return return_code == 0


def get_target_db_display_info(target_dbms_type):
    """Return display info based on target database type"""
    db_info = {
        'postgresql': {'name': 'PostgreSQL', 'icon': '🐘'},
        'postgres': {'name': 'PostgreSQL', 'icon': '🐘'},
        'mysql': {'name': 'MySQL', 'icon': '🐬'},
        'mariadb': {'name': 'MariaDB', 'icon': '🦭'},
        'sqlite': {'name': 'SQLite', 'icon': '📦'}
    }
    
    return db_info.get(target_dbms_type.lower(), {'name': target_dbms_type.upper(), 'icon': '🗄️'})


def save_test_result(test_type, result):
    """Save test result to session"""
    if test_type == "source":
        st.session_state.oracle_test_result = result
    elif test_type == "target":
        st.session_state.target_test_result = result
    elif test_type == "validation_source":
        st.session_state.validation_oracle_test_result = result
    elif test_type == "validation_target":
        st.session_state.validation_target_test_result = result


def display_dual_test_results(target_db_name):
    """Display Oracle and Target DB test results side by side"""
    col1, col2 = st.columns(2)
    
    with col1:
        if hasattr(st.session_state, 'oracle_test_result') and st.session_state.oracle_test_result:
            display_single_test_result_without_output(st.session_state.oracle_test_result, "Oracle", "oracle")
    
    with col2:
        if hasattr(st.session_state, 'target_test_result') and st.session_state.target_test_result:
            display_single_test_result_without_output(st.session_state.target_test_result, target_db_name, "target")
    
    # Display JSON result comparison
    display_json_comparison_results()
    
    # Display standard output (after JSON comparison)
    display_test_outputs(target_db_name)


def display_json_comparison_results():
    """Display JSON result comparison"""
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
    st.markdown("#### 📊 JSON Result Comparison")
    
    # Display row count info
    display_row_count_summary(oracle_json, target_json)
    
    # First row comparison table
    display_first_row_comparison(oracle_json, target_json)
    
    # Full JSON results (collapsed state)
    with st.expander("🔍 Full JSON Results", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Oracle JSON Result**")
            if oracle_json:
                st.json(oracle_json)
            else:
                st.info("No JSON result")
        
        with col2:
            st.markdown("**Target JSON Result**")
            if target_json:
                st.json(target_json)
            else:
                st.info("No JSON result")
        
        # Comparison analysis
        if oracle_json and target_json:
            display_json_comparison_analysis(oracle_json, target_json)


def parse_json_from_output(output):
    """Find JSON file path from output and parse JSON"""
    if not output:
        return None
    
    import json
    import re
    import os
    
    # Find JSON file path - updated pattern to match actual output
    json_file_pattern = r'JSON result file generated: (.+\.json)'
    match = re.search(json_file_pattern, output)
    
    if match:
        json_file_path = match.group(1)
        
        # Transform relative path to absolute path
        if not os.path.isabs(json_file_path):
            # Construct path based on test directory
            app_tools_folder = os.getenv('APP_TOOLS_FOLDER', '')
            if app_tools_folder:
                test_dir = os.path.join(app_tools_folder, '..', 'test')
                json_file_path = os.path.join(test_dir, json_file_path)
        
        # Read JSON file
        try:
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"JSON file reading error: {e}")
    
    return None


def display_first_row_comparison(oracle_json, target_json):
    """First row data comparison table"""
    oracle_first_row = extract_first_row_data(oracle_json)
    target_first_row = extract_first_row_data(target_json)
    
    if oracle_first_row or target_first_row:
        st.markdown("**📋 First Row Comparison**")
        
        # Transform column names to lowercase for mapping
        oracle_columns = {}
        target_columns = {}
        
        if oracle_first_row:
            oracle_columns = {k.lower(): (k, v) for k, v in oracle_first_row.items()}
        if target_first_row:
            target_columns = {k.lower(): (k, v) for k, v in target_first_row.items()}
        
        # Collect all column names (based on lowercase)
        all_columns = set()
        all_columns.update(oracle_columns.keys())
        all_columns.update(target_columns.keys())
        
        if all_columns:
            # Construct table data
            comparison_data = []
            for column_lower in sorted(all_columns):
                oracle_info = oracle_columns.get(column_lower, (column_lower, "N/A"))
                target_info = target_columns.get(column_lower, (column_lower, "N/A"))
                
                oracle_value = oracle_info[1]
                target_value = target_info[1]
                
                # Display if values are different
                match_status = "✅" if oracle_value == target_value else "❌"
                
                # Use original column name (Oracle first, Target if not available)
                display_column = oracle_info[0] if oracle_info[1] != "N/A" else target_info[0]
                
                comparison_data.append({
                    "Column": display_column,
                    "Oracle": oracle_value,
                    "Target": target_value,
                    "Match": match_status
                })
            
            # Display as dataframe
            import pandas as pd
            df = pd.DataFrame(comparison_data)
            st.dataframe(df, use_container_width=True, hide_index=True)


def extract_first_row_data(json_data):
    """Extract first row data from JSON"""
    if not json_data:
        return None
    
    # Find by successfulTests[0].resultData.data[0] path
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
    """Display row count summary info"""
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
                    st.success(f"✅ Row count match: {oracle_count}")
                else:
                    st.error(f"❌ Row count mismatch: Oracle({oracle_count}) vs Target({target_count})")


def extract_row_count(json_data):
    """Extract row count from JSON"""
    if not json_data:
        return None
    
    # Find rowCount in successfulTests array
    if isinstance(json_data, dict) and 'successfulTests' in json_data:
        successful_tests = json_data['successfulTests']
        if isinstance(successful_tests, list) and len(successful_tests) > 0:
            first_test = successful_tests[0]
            if isinstance(first_test, dict):
                # Find rowCount directly
                if 'rowCount' in first_test:
                    return first_test['rowCount']
                # Find in resultData.count
                if 'resultData' in first_test and isinstance(first_test['resultData'], dict):
                    if 'count' in first_test['resultData']:
                        return first_test['resultData']['count']
    
    # Also maintain existing logic
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
    """Display JSON comparison analysis"""
    st.markdown("**🔍 Comparison Analysis**")
    
    differences = []
    
    # Basic structure comparison
    if type(oracle_json) != type(target_json):
        differences.append(f"Data type difference: Oracle({type(oracle_json).__name__}) vs Target({type(target_json).__name__})")
    
    # Key comparison for dictionaries
    if isinstance(oracle_json, dict) and isinstance(target_json, dict):
        oracle_keys = set(oracle_json.keys())
        target_keys = set(target_json.keys())
        
        if oracle_keys != target_keys:
            only_oracle = oracle_keys - target_keys
            only_target = target_keys - oracle_keys
            
            if only_oracle:
                differences.append(f"Keys only in Oracle: {list(only_oracle)}")
            if only_target:
                differences.append(f"Keys only in Target: {list(only_target)}")
    
    # Length comparison for lists
    if isinstance(oracle_json, list) and isinstance(target_json, list):
        if len(oracle_json) != len(target_json):
            differences.append(f"Array length difference: Oracle({len(oracle_json)}) vs Target({len(target_json)})")
    
    if differences:
        for diff in differences:
            st.warning(f"⚠️ {diff}")
    else:
        st.success("✅ No structural differences")


def display_test_outputs(target_db_name):
    """Display test standard output separately"""
    oracle_result = getattr(st.session_state, 'oracle_test_result', None)
    target_result = getattr(st.session_state, 'target_test_result', None)
    
    if not oracle_result and not target_result:
        return
    
    # Display full output in collapsed state
    with st.expander("📤 Test Output Results", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            if oracle_result:
                st.markdown("**Oracle Output**")
                if oracle_result.get('stdout'):
                    with st.expander("📤 Standard Output", expanded=False):
                        st.code(oracle_result['stdout'], language=None)
                if oracle_result.get('stderr'):
                    with st.expander("⚠️ Standard Error", expanded=False):
                        st.code(oracle_result['stderr'], language=None)
        
        with col2:
            if target_result:
                st.markdown(f"**{target_db_name} Output**")
                if target_result.get('stdout'):
                    with st.expander("📤 Standard Output", expanded=False):
                        st.code(target_result['stdout'], language=None)
                if target_result.get('stderr'):
                    with st.expander("⚠️ Standard Error", expanded=False):
                        st.code(target_result['stderr'], language=None)


def display_single_test_result_without_output(result, db_name, result_key):
    """Display test result only without standard output"""
    st.markdown(f"#### 🧪 {db_name} Test Result")
    
    # Display during execution
    if result.get('running'):
        st.info(f"🔄 {db_name} test executing... (max 2 minutes)")
        return
    
    # Test file and DB info
    if 'file_path' in result:
        st.caption(f"**File:** {result['file_path']}")
    if 'db_type' in result:
        st.caption(f"**DB:** {result['db_type'].upper()}")
    
    # Success/failure status
    if result.get('success') is True:
        st.success("✅ Test Success!")
        # Extract and display success rate info
        if result.get('stdout'):
            success_info = extract_test_summary(result['stdout'])
            if success_info:
                st.info(f"📊 {success_info}")
    elif result.get('success') is False:
        st.error("❌ Test Failed!")
        # Extract and display failure info
        if result.get('stdout'):
            failure_info = extract_test_summary(result['stdout'])
            if failure_info:
                st.warning(f"📊 {failure_info}")
    
    # Error message
    if result.get('error'):
        st.error(f"**Error:** {result['error']}")
    
    # Exit code
    if 'return_code' in result:
        if result['return_code'] == 0:
            st.success(f"**Exit Code:** {result['return_code']} (Normal exit)")
        else:
            st.error(f"**Exit Code:** {result['return_code']} (Abnormal exit)")


def display_single_test_result(result, db_name, result_key):
    """Display single test result"""
    st.markdown(f"#### 🧪 {db_name} Test Result")
    
    # Display during execution
    if result.get('running'):
        st.info(f"🔄 {db_name} test executing... (max 2 minutes)")
        return
    
    # Test file and DB info
    if 'file_path' in result:
        st.markdown(f"**📄 File:** `{os.path.basename(result['file_path'])}`")
    
    if 'db_type' in result:
        st.markdown(f"**🗄️ DB:** `{result['db_type'].upper()}`")
    
    # Command info (full display)
    if 'command' in result:
        st.markdown("**💻 Execute Command:**")
        st.code(f"$ cd {result.get('test_dir', '')}\n$ {result['command']}", language="bash")
    
    # Result status (detailed analysis)
    if result.get('success') is True:
        st.success("✅ Test Success!")
        # Extract and display success rate info
        if result.get('stdout'):
            success_info = extract_test_summary(result['stdout'])
            if success_info:
                st.info(f"📊 {success_info}")
    elif result.get('success') is False:
        st.error("❌ Test Failed!")
        # Extract and display failure info
        if result.get('stdout'):
            failure_info = extract_test_summary(result['stdout'])
            if failure_info:
                st.warning(f"📊 {failure_info}")
    
    # Compare exit code with actual result
    if 'return_code' in result:
        code_success = result['return_code'] == 0
        actual_success = result.get('success', False)
        
        if code_success != actual_success:
            st.warning(f"⚠️ Exit code ({result['return_code']}) differs from actual result!")
        
        if result['return_code'] == 0:
            st.success(f"**Exit Code:** {result['return_code']} (Normal exit)")
        else:
            st.error(f"**Exit Code:** {result['return_code']} (Abnormal exit)")
    
    # Standard output (collapsed display)
    if result.get('stdout'):
        with st.expander("📤 Standard Output", expanded=False):
            st.code(result['stdout'], language=None)
    
    # Standard error (full display)
    if result.get('stderr'):
        st.markdown("**📥 Standard Error:**")
        st.code(result['stderr'], language=None)
    
    # Error message
    if result.get('error'):
        st.error(f"**Error:** {result['error']}")
    
    # Clear result button
    if st.button(f"🧹 Clear {db_name} Result", key=f"clear_{result_key}_result"):
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
    """Display test result"""
    result = st.session_state.sql_test_result
    
    st.markdown("#### 🧪 SQL Test Result")
    
    # Display during execution
    if result.get('running'):
        st.info("🔄 SQL test executing... (max 2 minutes)")
        return
    
    # Test file and DB info
    col1, col2 = st.columns(2)
    with col1:
        if 'file_path' in result:
            st.markdown(f"**📄 Test File:** `{result['file_path']}`")
    with col2:
        if 'db_type' in result:
            st.markdown(f"**🗄️ Database:** `{result['db_type'].upper()}`")
    
    # Command Info
    if 'command' in result:
        st.markdown("**💻 Execute Command:**")
        st.code(f"$ cd {result.get('test_dir', '')}\n$ {result['command']}", language="bash")
    
    # Result Status
    if result.get('success') is True:
        st.success("✅ SQL Test Success!")
    elif result.get('success') is False:
        st.error("❌ SQL Test Failed!")
    
    # Standard output (collapsed display)
    if result.get('stdout'):
        with st.expander("📤 Standard Output", expanded=False):
            st.code(result['stdout'], language=None)
    
    # Standard error
    if result.get('stderr'):
        st.markdown("**📥 Standard Error:**")
        st.code(result['stderr'], language=None)
    
    # Error message
    if result.get('error'):
        st.error(f"**Error:** {result['error']}")
    
    # Exit code
    if 'return_code' in result:
        if result['return_code'] == 0:
            st.success(f"**Exit Code:** {result['return_code']} (Success)")
        else:
            st.error(f"**Exit Code:** {result['return_code']} (Failed)")
    
    # Clear result button
    if st.button("🧹 Clear Result", key="clear_test_result"):
        if hasattr(st.session_state, 'sql_test_result'):
            del st.session_state.sql_test_result
        st.rerun()
