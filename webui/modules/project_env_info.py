"""
Project Environment Information Page
"""
import streamlit as st


def render_project_env_page():
    """Project environment information page"""
    st.markdown("## 📊 Project Environment Information")
    show_project_environment_info()


def show_project_environment_info():
    """Display project environment information in table format"""
    # Load current config file
    config, _ = st.session_state.oma_controller.load_saved_config()
    env_vars = config.get('env_vars', {})
    
    if not env_vars:
        st.warning("⚠️ No saved environment information. Please select a project first.")
        return
    
    # Project basic information
    project_name = env_vars.get('APPLICATION_NAME', 'Unknown')
    st.subheader(f"🎯 Current Project: **{project_name}**")
    
    # Prepare environment variable table data
    table_data = []
    for key, value in sorted(env_vars.items()):
        # Mask passwords
        if 'PASSWORD' in key.upper():
            display_value = "••••••••"
        else:
            display_value = value
        
        table_data.append({
            "Environment Variable": key,
            "Value": display_value
        })
    
    # Display table
    if table_data:
        # Unified height with log container (900px)
        st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True,
            height=900,  # Same height as log container
            column_config={
                "Environment Variable": st.column_config.TextColumn(
                    "Environment Variable",
                    width="medium",
                ),
                "Value": st.column_config.TextColumn(
                    "Value",
                    width="large",
                )
            }
        )
        
        # Summary information
        st.info(f"📊 Total of **{len(env_vars)}** environment variables are configured.")
    else:
        st.error("Unable to load environment variable information.")
