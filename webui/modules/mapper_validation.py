import streamlit as st
import pandas as pd
import os
from pathlib import Path

def render_mapper_validation_page():
    """Mapper file validation page"""
    st.markdown('<div class="main-header"><h1>✅ Mapper File Validation</h1></div>', unsafe_allow_html=True)
    
    # Process status explanation
    st.markdown("""
    ### 📋 Process Status Meaning
    - **Not Yet**: Requires transformation
    - **Sampled**: Sample transformation (considered as processed)  
    - **Processed**: Completed processing
    """)
    
    st.markdown("---")
    
    # Check APP_TRANSFORM_FOLDER environment variable
    app_transform_folder = os.environ.get('APP_TRANSFORM_FOLDER')
    if not app_transform_folder:
        st.error("❌ APP_TRANSFORM_FOLDER environment variable is not set.")
        return
    
    if not os.path.exists(app_transform_folder):
        st.error(f"❌ Directory does not exist: {app_transform_folder}")
        return
    
    # CSV File Path
    sample_csv = os.path.join(app_transform_folder, "SampleTransformTarget.csv")
    sql_csv = os.path.join(app_transform_folder, "SQLTransformTarget.csv")
    
    # Create tabs
    tab1, tab2 = st.tabs(["📋 SampleTransformTarget.csv", "📊 SQLTransformTarget.csv"])
    
    with tab1:
        render_csv_editor("SampleTransformTarget.csv", sample_csv)
    
    with tab2:
        render_csv_editor("SQLTransformTarget.csv", sql_csv)

def render_csv_editor(file_name, file_path):
    """CSV file editor"""
    st.subheader(f"📄 {file_name}")
    
    if not os.path.exists(file_path):
        st.warning(f"⚠️ File does not exist: {file_path}")
        
        # Create new file button
        if st.button(f"📝 Create New {file_name}", key=f"create_{file_name}"):
            try:
                # Create empty CSV with default columns
                if "Sample" in file_name:
                    df = pd.DataFrame(columns=['file_path', 'status', 'error_message'])
                else:
                    df = pd.DataFrame(columns=['sql_id', 'file_path', 'status', 'error_message'])
                
                df.to_csv(file_path, index=False, encoding='utf-8')
                st.success(f"✅ {file_name} file has been created.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ File creation failed: {e}")
        return
    
    try:
        # Read CSV file
        df = pd.read_csv(file_path, encoding='utf-8')
        
        # Display file information
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total Rows", len(df))
        with col2:
            st.metric("📋 Columns", len(df.columns))
        with col3:
            file_size = os.path.getsize(file_path)
            st.metric("📁 File Size", f"{file_size:,} bytes")
        
        # Search functionality
        st.markdown("### 🔍 Search")
        search_col, filter_col = st.columns([2, 1])
        
        with search_col:
            search_term = st.text_input("Enter search term", key=f"search_{file_name}", placeholder="Search by filename, SQL ID, status, etc.")
        
        with filter_col:
            if len(df.columns) > 0:
                search_column = st.selectbox("Search column", ["All"] + list(df.columns), key=f"search_col_{file_name}")
        
        # Filter search results
        filtered_df = df.copy()
        original_indices = df.index.tolist()
        
        if search_term:
            if search_column == "All":
                # Search in all columns
                mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
            else:
                # Search in specific column
                mask = df[search_column].astype(str).str.contains(search_term, case=False, na=False)
            
            filtered_df = df[mask].copy()
            original_indices = df[mask].index.tolist()
            
            st.info(f"🔍 Search results: {len(filtered_df)} rows (out of {len(df)} total)")
        
        # Data editor
        st.markdown("### 📝 Data Editor")
        
        if len(filtered_df) > 0:
            # Editable data grid (search results)
            edited_filtered_df = st.data_editor(
                filtered_df,
                use_container_width=True,
                num_rows="dynamic",
                key=f"editor_{file_name}_{len(original_indices)}"  # Change key whenever search results change
            )
            
            # Update original dataframe
            updated_df = df.copy()
            
            # Reflect modifications from search results to original
            for i, original_idx in enumerate(original_indices):
                if i < len(edited_filtered_df):
                    updated_df.loc[original_idx] = edited_filtered_df.iloc[i]
            
            # Handle newly added rows (when added in search results)
            if len(edited_filtered_df) > len(original_indices):
                new_rows = edited_filtered_df.iloc[len(original_indices):].copy()
                updated_df = pd.concat([updated_df, new_rows], ignore_index=True)
            
            # Handle deleted rows (when deleted in search results)
            if len(edited_filtered_df) < len(original_indices):
                deleted_indices = original_indices[len(edited_filtered_df):]
                updated_df = updated_df.drop(deleted_indices).reset_index(drop=True)
        else:
            st.info("📝 No search results found.")
            updated_df = df.copy()
        
        # Save button
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("💾 Save", key=f"save_{file_name}", type="primary"):
                try:
                    # Create backup
                    backup_path = f"{file_path}.backup"
                    if os.path.exists(file_path):
                        import shutil
                        shutil.copy2(file_path, backup_path)
                    
                    # Save new data
                    updated_df.to_csv(file_path, index=False, encoding='utf-8')
                    st.success(f"✅ {file_name} saved successfully!")
                    
                except Exception as e:
                    st.error(f"❌ Save failed: {e}")
        
        with col2:
            if st.button("🔄 Refresh", key=f"refresh_{file_name}"):
                st.rerun()
        
        with col3:
            # Display file path
            st.caption(f"📁 {file_path}")
        
        # Full data preview (read-only)
        if len(df) > 0:
            with st.expander("👀 Full Data Preview", expanded=False):
                st.dataframe(df, use_container_width=True)
        else:
            st.info("📝 No data available. Please add new rows using the editor above.")
            
    except Exception as e:
        st.error(f"❌ CSV file read error: {e}")
        
        # File recovery option
        backup_path = f"{file_path}.backup"
        if os.path.exists(backup_path):
            if st.button(f"🔧 Restore from Backup", key=f"restore_{file_name}"):
                try:
                    import shutil
                    shutil.copy2(backup_path, file_path)
                    st.success("✅ Restored from backup successfully.")
                    st.rerun()
                except Exception as restore_e:
                    st.error(f"❌ Restore failed: {restore_e}")
