"""
Welcome Page
"""
import streamlit as st
import os
import plotly.graph_objects as go
import plotly.express as px
from .utils import get_page_text


def render_welcome_page():
    """Render welcome page"""
    # Don't render when in log viewer or qlog viewer state
    selected_action = st.session_state.get('selected_action')
    if selected_action in ["view_running_logs", "view_qlog"]:
        return
    
    show_welcome_screen()


def show_welcome_screen():
    """Display welcome screen"""
    # Don't display when in log viewer or qlog viewer state
    selected_action = st.session_state.get('selected_action')
    if selected_action in ["view_running_logs", "view_qlog"]:
        st.stop()
    
    title = "🔄 OMA - Oracle Migration Assistant"
    subtitle = "Oracle to PostgreSQL Migration Tool - Web Interface"
    workflow_title = "## 🗺️ OMA Workflow"
        
    st.markdown(f"""
    <div class="main-header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Display workflow diagram
    st.markdown(workflow_title)
    show_workflow_diagram()
    
    st.markdown("---")
    
    # Current environment status summary
    env_status = st.session_state.oma_controller.check_environment()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if env_status['is_configured']:
            st.success(f"✅ **Project Configured**\n\nProject: {env_status['application_name']}")
        else:
            st.error("❌ **Environment Setup Required**\n\nPlease configure environment first")
    
    with col2:
        st.info(f"📁 **OMA Directory**\n\n{env_status['oma_base_dir']}")
    
    with col3:
        config_exists = os.path.exists(env_status['config_file'])
        if config_exists:
            st.success("💾 **Config File Exists**\n\nEnvironment variables saved")
        else:
            st.warning("⚠️ **No Config File**\n\nPlease save environment variables")


def show_workflow_diagram():
    """Display OMA workflow diagram - enhanced design"""
    
    # Define workflow steps - including test and result modification
    steps = [
        {"id": 1, "name": "Project<br>Environment Info", "x": 1, "y": 6.2, "color": "#FF6B6B", "gradient": "#FF8E8E", "icon": "📊"},
        {"id": 2, "name": "Application<br>Analysis", "x": 2, "y": 6.2, "color": "#4ECDC4", "gradient": "#6ED5D8", "icon": "🔍"},
        {"id": 3, "name": "Analysis Report<br>Generation", "x": 3, "y": 6.2, "color": "#4ECDC4", "gradient": "#6ED5D8", "icon": "📄"},
        {"id": 4, "name": "Analysis Report<br>Review", "x": 4, "y": 6.2, "color": "#4ECDC4", "gradient": "#6ED5D8", "icon": "📋"},
        {"id": 5, "name": "PostgreSQL<br>Metadata", "x": 5, "y": 6.2, "color": "#4ECDC4", "gradient": "#6ED5D8", "icon": "🗄️"},
        {"id": 6, "name": "Sample Transform", "x": 2, "y": 3.8, "color": "#45B7D1", "gradient": "#67C3DB", "icon": "🧪"},
        {"id": 7, "name": "Full Transform", "x": 3, "y": 3.8, "color": "#45B7D1", "gradient": "#67C3DB", "icon": "🚀"},
        {"id": 8, "name": "Test &<br>Result Fix", "x": 4, "y": 3.2, "color": "#FF9500", "gradient": "#FFB347", "icon": "🔧"},
        {"id": 9, "name": "XML Merge", "x": 5, "y": 3.8, "color": "#45B7D1", "gradient": "#67C3DB", "icon": "🔗"},
        {"id": 10, "name": "Compare<br>SQL Test", "x": 2, "y": 1.4, "color": "#96CEB4", "gradient": "#A8D5C4", "icon": "⚖️"},
        {"id": 11, "name": "Transform Report<br>Generation", "x": 3, "y": 1.4, "color": "#E67E22", "gradient": "#F39C12", "icon": "📊"},
        {"id": 12, "name": "Transform Report<br>View", "x": 4, "y": 1.4, "color": "#E67E22", "gradient": "#F39C12", "icon": "📄"},
    ]
    
    # Define connections - workflow centered around test and result modification
    connections = [
        (1, 2), (2, 3), (3, 4), (4, 5),  # Stage 2: Analysis line
        (5, 6), (5, 7),  # Analysis → Sample/Full Transform
        (6, 8), (7, 8),  # Sample/Full Transform → Test & Result Fix
        (8, 9),  # Test & Result Fix → XML Merge
        (9, 10),  # XML Merge → Compare SQL Test
        (9, 11), (11, 12)  # XML Merge → Transform Report Generation → View
    ]
    
    # Plotly graph creation
    fig = go.Figure()
    
    # Add group background areas - modified for current structure
    group_areas = [
        {"name": "Stage 1: Environment Setup", "x": [0.3, 1.7, 1.7, 0.3, 0.3], "y": [5.0, 5.0, 7.4, 7.4, 5.0], 
         "color": "rgba(255, 107, 107, 0.15)", "border": "rgba(255, 107, 107, 0.4)"},
        {"name": "Stage 2: Analysis", "x": [1.3, 5.7, 5.7, 1.3, 1.3], "y": [5.0, 5.0, 7.4, 7.4, 5.0], 
         "color": "rgba(78, 205, 196, 0.15)", "border": "rgba(78, 205, 196, 0.4)"},
        {"name": "Stage 3: Transform", "x": [1.3, 4.7, 4.7, 1.3, 1.3], "y": [2.6, 2.6, 5.0, 5.0, 2.6], 
         "color": "rgba(69, 183, 209, 0.15)", "border": "rgba(69, 183, 209, 0.4)"},
        {"name": "Stage 4: Test & Report", "x": [1.3, 4.7, 4.7, 1.3, 1.3], "y": [0.2, 0.2, 2.6, 2.6, 0.2], 
         "color": "rgba(230, 126, 34, 0.15)", "border": "rgba(230, 126, 34, 0.4)"}
    ]
    
    # Add background areas - smoother style
    for area in group_areas:
        fig.add_trace(go.Scatter(
            x=area["x"],
            y=area["y"],
            fill="toself",
            fillcolor=area["color"],
            line=dict(color=area["border"], width=3, dash="dot"),
            mode="lines",
            name=area["name"],
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # Add group labels - modified for current structure
    group_labels = [
        {"text": "🔴 Stage 1: Environment Setup", "x": 1.0, "y": 7.2, "color": "#FF6B6B"},
        {"text": "🟢 Stage 2: Analysis", "x": 3.5, "y": 7.2, "color": "#4ECDC4"},
        {"text": "🔵 Stage 3: Transform", "x": 3.0, "y": 4.8, "color": "#45B7D1"},
        {"text": "🟠 Stage 4: Test & Report", "x": 3.0, "y": 2.4, "color": "#E67E22"}
    ]
    
    # Add label text only (remove background box)
    for label in group_labels:
        fig.add_trace(go.Scatter(
            x=[label["x"]],
            y=[label["y"]],
            mode='text',
            text=label["text"],
            textfont=dict(size=16, color=label["color"], family="Arial Black"),
            textposition="middle center",  # Center alignment
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # Report - Report Report Item
    for from_id, to_id in connections:
        from_step = next(s for s in steps if s["id"] == from_id)
        to_step = next(s for s in steps if s["id"] == to_id)
        
        # Report - Test Report Report Report
        if to_id == 8:  # Test Report Report Item
            line_color = '#FF6B35'
            line_width = 5
            line_dash = "solid"
            opacity = 0.8
        else:
            line_color = '#B8BCC8'
            line_width = 4
            line_dash = "solid"
            opacity = 0.7
        
        # Report Report
        fig.add_trace(go.Scatter(
            x=[from_step["x"], to_step["x"]],
            y=[from_step["y"], to_step["y"]],
            mode='lines',
            line=dict(color=line_color, width=line_width, dash=line_dash),
            opacity=opacity,
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Report (Report) - Report
        arrow_x = to_step["x"] - 0.1 * (to_step["x"] - from_step["x"])
        arrow_y = to_step["y"] - 0.1 * (to_step["y"] - from_step["y"])
        
        fig.add_trace(go.Scatter(
            x=[arrow_x],
            y=[arrow_y],
            mode='markers',
            marker=dict(
                symbol='triangle-right',
                size=16,  # 12 → 16
                color=line_color,
                line=dict(color='white', width=2)  # Report
            ),
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # Report Item - Test Report Report display
    for step in steps:
        # Test Report Report Item (Item Task Item)
        if step["id"] == 8:  # Test Report Item
            marker_size = 110
            marker_color = step["color"]
            border_width = 5
            border_color = '#FFD700'  # Report
            text_size = 14
        else:
            marker_size = 95
            marker_color = step["color"]
            border_width = 4
            border_color = 'white'
            text_size = 13
        
        # Report (Report)
        fig.add_trace(go.Scatter(
            x=[step["x"]],
            y=[step["y"]],
            mode='markers+text',
            marker=dict(
                size=marker_size,
                color=marker_color,
                line=dict(color=border_color, width=border_width),
                opacity=0.95
            ),
            text=f"{step['icon']}<br><b>{step['name']}</b>",
            textposition="middle center",
            textfont=dict(size=text_size, color='white', family="Arial"),
            showlegend=False,
            hovertemplate=f"<b>{step['name'].replace('<br>', ' ')}</b><br>Item {step['id']}<br>Item: {get_group_name(step['id'])}<extra></extra>"
        ))
    
    # Item Config - Report Report
    fig.update_layout(
        title={
            'text': "🌟 OMA Item - Report 🌟",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 28, 'color': '#2C3E50', 'family': 'Arial Black'}  # 24 → 28
        },
        xaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            range=[0.2, 5.8]
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            range=[-1.4, 7.8]  # -1.2, 7.6 → -1.4, 7.8 (Report Report Item)
        ),
        plot_bgcolor='rgba(248, 249, 250, 0.9)',
        paper_bgcolor='rgba(255, 255, 255, 0.95)',
        height=750,  # 650 → 750 (Item 100px Item)
        margin=dict(l=40, r=40, t=120, b=50),  # Report 40 → 50
        # Report Item
        hoverlabel=dict(
            bgcolor="white",
            font_size=16,  # 14 → 16
            font_family="Arial"
        )
    )
    
    # Item display - Report Report
    st.markdown("""
    <style>
    .workflow-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Report Report
    st.markdown('<div class="workflow-container">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Report Report
    st.markdown("""
    <div style="text-align: center; margin: 2rem 0;">
        <h3 style="color: #2C3E50; font-family: Arial Black;">✨ Project Environment Information Check ✨</h3>
        <p style="color: #7F8C8D; font-size: 16px;">Task completed successfully!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Report 4Text Item - Report
    st.markdown("### 📋 Task Details")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(255, 107, 107, 0.1), rgba(255, 107, 107, 0.05)); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #FF6B6B; margin-bottom: 1rem; height: 200px; display: flex; flex-direction: column;">
        <h4 style="color: #FF6B6B; margin-top: 0;">🔴 Stage 1: Environment Config</h4>
        <ul style="flex-grow: 1;">
        <li>📊 Project Environment Info</li>
        </ul>
        <small style="margin-top: auto;"><em>Project Environment Configuration</em></small>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(78, 205, 196, 0.1), rgba(78, 205, 196, 0.05)); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #4ECDC4; margin-bottom: 1rem; height: 200px; display: flex; flex-direction: column;">
        <h4 style="color: #4ECDC4; margin-top: 0;">🟢 Stage 2: Analysis</h4>
        <ul style="flex-grow: 1;">
        <li>🔍 Application Analysis</li>
        <li>📄 Analysis Report Item</li>
        <li>📋 Analysis Report Item</li>
        <li>🗄️ PostgreSQL Item</li>
        </ul>
        <small style="margin-top: auto;"><em>Application Analysis and Transform</em></small>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(69, 183, 209, 0.1), rgba(69, 183, 209, 0.05)); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #45B7D1; margin-bottom: 1rem; height: 200px; display: flex; flex-direction: column;">
        <h4 style="color: #45B7D1; margin-top: 0;">🔵 Stage 3: Transform</h4>
        <ul style="flex-grow: 1;">
        <li>🧪 Sample Transform</li>
        <li>🚀 Sample Transform</li>
        <li>🔧 Test Report Item</li>
        <li>🔗 XML Merge</li>
        </ul>
        <small style="margin-top: auto;"><em>SQL Transform Tasks<br>(Test and Result Modification Task)</em></small>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(230, 126, 34, 0.1), rgba(230, 126, 34, 0.05)); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #E67E22; margin-bottom: 1rem; height: 200px; display: flex; flex-direction: column;">
        <h4 style="color: #E67E22; margin-top: 0;">🟠 Stage 4: Test & Report</h4>
        <ul style="flex-grow: 1;">
        <li>⚖️ Compare SQL Test</li>
        <li>📊 Transform Report Create</li>
        <li>📄 Transform Report Item</li>
        </ul>
        <small style="margin-top: auto;"><em>Transform Report Generation</em></small>
        </div>
        """, unsafe_allow_html=True)


def get_group_name(step_id):
    """Item IDText Report Item"""
    if step_id == 1:
        return "1Text: Environment Config"
    elif 2 <= step_id <= 5:
        return "2Text: Analysis"
    elif 6 <= step_id <= 9:
        return "3Text: Transform"
    else:
        return "4Text: Test & Report"
