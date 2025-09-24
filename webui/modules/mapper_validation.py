import streamlit as st
import pandas as pd
import os
from pathlib import Path

def render_mapper_validation_page():
    """Mapper File Validation Page"""
    st.markdown('<div class="main-header"><h1>✅ Mapper File Validation</h1></div>', unsafe_allow_html=True)
    
    # Process status meaning explanation
    st.markdown("""
    ### 📋 Process Status Meaning
    - **Not Yet**: Transformation required
    - **Sampled**: Sample transformation (considered processed)  
    - **Processed**: Processed
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
    
    # CSV file paths
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
        if st.button(f"📝 {file_name} Generation", key=f"create_{file_name}"):
            try:
                # Report Item CSV Create
                if "Sample" in file_name:
                    df = pd.DataFrame(columns=['file_path', 'status', 'error_message'])
                else:
                    df = pd.DataFrame(columns=['sql_id', 'file_path', 'status', 'error_message'])
                
                df.to_csv(file_path, index=False, encoding='utf-8')
                st.success(f"✅ {file_name} FileText CreateText.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ File Create Item: {e}")
        return
    
    try:
        # CSV File Item
        df = pd.read_csv(file_path, encoding='utf-8')
        
        # File Info display
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Report Item", len(df))
        with col2:
            st.metric("📋 Report", len(df.columns))
        with col3:
            file_size = os.path.getsize(file_path)
            st.metric("📁 File Item", f"{file_size:,} bytes")
        
        # Report
        st.markdown("### 🔍 Item")
        search_col, filter_col = st.columns([2, 1])
        
        with search_col:
            search_term = st.text_input("Report", key=f"search_{file_name}", placeholder="FileText, SQL ID, Status Report")
        
        with filter_col:
            if len(df.columns) > 0:
                search_column = st.selectbox("Report", ["Item"] + list(df.columns), key=f"search_col_{file_name}")
        
        # Report Item
        filtered_df = df.copy()
        original_indices = df.index.tolist()
        
        if search_term:
            if search_column == "Item":
                # Report Item
                mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
            else:
                # Report Item
                mask = df[search_column].astype(str).str.contains(search_term, case=False, na=False)
            
            filtered_df = df[mask].copy()
            original_indices = df[mask].index.tolist()
            
            st.info(f"🔍 Report: {len(filtered_df)}Report (Item {len(df)}Report)")
        
        # Report
        st.markdown("### 📝 Report")
        
        if len(filtered_df) > 0:
            # Report Report (Report)
            edited_filtered_df = st.data_editor(
                filtered_df,
                use_container_width=True,
                num_rows="dynamic",
                key=f"editor_{file_name}_{len(original_indices)}"  # Report Report Report
            )
            
            # Report Item
            updated_df = df.copy()
            
            # Report Report Report
            for i, original_idx in enumerate(original_indices):
                if i < len(edited_filtered_df):
                    updated_df.loc[original_idx] = edited_filtered_df.iloc[i]
            
            # Report Report (Report Report)
            if len(edited_filtered_df) > len(original_indices):
                new_rows = edited_filtered_df.iloc[len(original_indices):].copy()
                updated_df = pd.concat([updated_df, new_rows], ignore_index=True)
            
            # Report Item (Report Report)
            if len(edited_filtered_df) < len(original_indices):
                deleted_indices = original_indices[len(edited_filtered_df):]
                updated_df = updated_df.drop(deleted_indices).reset_index(drop=True)
        else:
            st.info("📝 Report Item.")
            updated_df = df.copy()
        
        # Report
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("💾 Item", key=f"save_{file_name}", type="primary"):
                try:
                    # Generation
                    backup_path = f"{file_path}.backup"
                    if os.path.exists(file_path):
                        import shutil
                        shutil.copy2(file_path, backup_path)
                    
                    # Report Item
                    updated_df.to_csv(file_path, index=False, encoding='utf-8')
                    st.success(f"✅ {file_name} Item Complete!")
                    
                except Exception as e:
                    st.error(f"❌ Report: {e}")
        
        with col2:
            if st.button("🔄 Item", key=f"refresh_{file_name}"):
                st.rerun()
        
        with col3:
            # File Item display
            st.caption(f"📁 {file_path}")
        
        # Report Item (Report)
        if len(df) > 0:
            with st.expander("👀 Report Item", expanded=False):
                st.dataframe(df, use_container_width=True)
        else:
            st.info("📝 Report. Report Report Item.")
            
    except Exception as e:
        st.error(f"❌ CSV File Item Error: {e}")
        
        # File Report
        backup_path = f"{file_path}.backup"
        if os.path.exists(backup_path):
            if st.button(f"🔧 Report", key=f"restore_{file_name}"):
                try:
                    import shutil
                    shutil.copy2(backup_path, file_path)
                    st.success("✅ Report.")
                    st.rerun()
                except Exception as restore_e:
                    st.error(f"❌ Report: {restore_e}")
