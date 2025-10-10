"""
Welcome Page
"""
import streamlit as st
import os
import plotly.graph_objects as go
import plotly.express as px


def render_welcome_page():
    """Welcome page rendering"""
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
        
    st.markdown("""
    <div class="main-header">
        <h1>🔄 OMA - Oracle Migration Assistant</h1>
        <p>Oracle to PostgreSQL Migration Tool - Web Interface</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Display workflow diagram
    st.markdown("## 🗺️ OMA Workflow")
    show_workflow_diagram()
    
    st.markdown("---")
    
    # Current environment status summary
    env_status = st.session_state.oma_controller.check_environment()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if env_status['is_configured']:
            st.success(f"✅ **Project Setup Complete**\n\nProject: {env_status['application_name']}")
        else:
            st.error("❌ **Environment Setup Required**\n\nPlease run environment setup first")
    
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
        {"id": 4, "name": "Discovery Report<br>Review", "x": 4, "y": 6.2, "color": "#4ECDC4", "gradient": "#6ED5D8", "icon": "📋"},
        {"id": 5, "name": "PostgreSQL<br>Metadata", "x": 5, "y": 6.2, "color": "#4ECDC4", "gradient": "#6ED5D8", "icon": "🗄️"},
        {"id": 6, "name": "Sample Transform", "x": 2, "y": 3.8, "color": "#45B7D1", "gradient": "#67C3DB", "icon": "🧪"},
        {"id": 7, "name": "Full Transform", "x": 3, "y": 3.8, "color": "#45B7D1", "gradient": "#67C3DB", "icon": "🚀"},
        {"id": 8, "name": "Test &<br>Result Fix", "x": 4, "y": 3.2, "color": "#FF9500", "gradient": "#FFB347", "icon": "🔧"},
        {"id": 9, "name": "XML Merge", "x": 5, "y": 3.8, "color": "#45B7D1", "gradient": "#67C3DB", "icon": "🔗"},
        {"id": 10, "name": "Compare<br>SQL Test", "x": 2, "y": 1.4, "color": "#96CEB4", "gradient": "#A8D5C4", "icon": "⚖️"},
        {"id": 11, "name": "Transform Report<br>Generation", "x": 3, "y": 1.4, "color": "#E67E22", "gradient": "#F39C12", "icon": "📊"},
        {"id": 12, "name": "View Transform<br>Report", "x": 4, "y": 1.4, "color": "#E67E22", "gradient": "#F39C12", "icon": "📄"},
    ]
    
    # Define connections - workflow centered around test and result modification
    connections = [
        (1, 2), (2, 3), (3, 4), (4, 5),  # Stage 2: Analysis line
        (5, 6), (5, 7),  # Analysis → Sample/Full transform
        (6, 8), (7, 8),  # Sample/Full transform → Test and result fix
        (8, 9),  # Test and result fix → XML Merge
        (9, 10),  # XML Merge → Compare SQL Test
        (9, 11), (11, 12)  # XML Merge → Transform report generation → View
    ]
    
    # Create Plotly graph
    fig = go.Figure()
    
    # Add group background areas - modified for current structure
    group_areas = [
        {"name": "Stage 1: Environment Setup", "x": [0.3, 1.7, 1.7, 0.3, 0.3], "y": [5.0, 5.0, 7.4, 7.4, 5.0], 
         "color": "rgba(255, 107, 107, 0.15)", "border": "rgba(255, 107, 107, 0.4)"},
        {"name": "Stage 2: Analysis", "x": [1.3, 5.7, 5.7, 1.3, 1.3], "y": [5.0, 5.0, 7.4, 7.4, 5.0], 
         "color": "rgba(78, 205, 196, 0.15)", "border": "rgba(78, 205, 196, 0.4)"},
        {"name": "Stage 3: Transformation", "x": [1.3, 4.7, 4.7, 1.3, 1.3], "y": [2.6, 2.6, 5.0, 5.0, 2.6], 
         "color": "rgba(69, 183, 209, 0.15)", "border": "rgba(69, 183, 209, 0.4)"},
        {"name": "Stage 4: Testing & Reports", "x": [1.3, 4.7, 4.7, 1.3, 1.3], "y": [0.2, 0.2, 2.6, 2.6, 0.2], 
         "color": "rgba(230, 126, 34, 0.15)", "border": "rgba(230, 126, 34, 0.4)"}
    ]
    
    # Add background areas - softer style
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
        {"text": "🔵 Stage 3: Transformation", "x": 3.0, "y": 4.8, "color": "#45B7D1"},
        {"text": "🟠 Stage 4: Testing & Reports", "x": 3.0, "y": 2.4, "color": "#E67E22"}
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
    
    # Add connection lines - prettier style and animation effects
    for from_id, to_id in connections:
        from_step = next(s for s in steps if s["id"] == from_id)
        to_step = next(s for s in steps if s["id"] == to_id)
        
        # Connection line style - emphasize lines to test and result fix
        if to_id == 8:  # Lines going to test and result fix
            line_color = '#FF6B35'
            line_width = 5
            line_dash = "solid"
            opacity = 0.8
        else:
            line_color = '#B8BCC8'
            line_width = 4
            line_dash = "solid"
            opacity = 0.7
        
        # Arrow effect connection line
        fig.add_trace(go.Scatter(
            x=[from_step["x"], to_step["x"]],
            y=[from_step["y"], to_step["y"]],
            mode='lines',
            line=dict(color=line_color, width=line_width, dash=line_dash),
            opacity=opacity,
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Add arrow (end of connection line) - increased size
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
                line=dict(color='white', width=2)  # Thick border
            ),
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # Add step nodes - special display for test and result modification
    for step in steps:
        # Test and result modification has special style (terminal work emphasis)
        if step["id"] == 8:  # Test and result modification
            marker_size = 110
            marker_color = step["color"]
            border_width = 5
            border_color = '#FFD700'  # Gold border
            text_size = 14
        else:
            marker_size = 95
            marker_color = step["color"]
            border_width = 4
            border_color = 'white'
            text_size = 13
        
        # Main node (shadow removed)
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
            hovertemplate=f"<b>{step['name'].replace('<br>', ' ')}</b><br>Step {step['id']}<br>Group: {get_group_name(step['id'])}<extra></extra>"
        ))
    
    # Layout settings - more modern and beautiful style
    fig.update_layout(
        title={
            'text': "🌟 OMA Workflow - Step-by-Step Process 🌟",
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
            range=[-1.4, 7.8]  # -1.2, 7.6 → -1.4, 7.8 (wider range for more space)
        ),
        plot_bgcolor='rgba(248, 249, 250, 0.9)',
        paper_bgcolor='rgba(255, 255, 255, 0.95)',
        height=750,  # 650 → 750 (height increased by 100px)
        margin=dict(l=40, r=40, t=120, b=50),  # bottom margin 40 → 50
        # Improved hover effect
        hoverlabel=dict(
            bgcolor="white",
            font_size=16,  # 14 → 16
            font_family="Arial"
        )
    )
    
    # Display diagram - wrapped in gradient background container
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
    
    # Wrap in gradient background container
    st.markdown('<div class="workflow-container">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Make workflow description more beautiful
    st.markdown("""
    <div style="text-align: center; margin: 2rem 0;">
        <h3 style="color: #2C3E50; font-family: Arial Black;">✨ Click each step to view detailed information ✨</h3>
        <p style="color: #7F8C8D; font-size: 16px;">Follow the arrows in order for perfect migration!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Configure step-by-step description in 4 columns - same height
    st.markdown("### 📋 Step-by-Step Detailed Guide")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(255, 107, 107, 0.1), rgba(255, 107, 107, 0.05)); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #FF6B6B; margin-bottom: 1rem; height: 200px; display: flex; flex-direction: column;">
        <h4 style="color: #FF6B6B; margin-top: 0;">🔴 Step 1: Environment Setup</h4>
        <ul style="flex-grow: 1;">
        <li>📊 Project Environment Information</li>
        </ul>
        <small style="margin-top: auto;"><em>Setting environment variables that form the foundation of all tasks</em></small>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(78, 205, 196, 0.1), rgba(78, 205, 196, 0.05)); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #4ECDC4; margin-bottom: 1rem; height: 200px; display: flex; flex-direction: column;">
        <h4 style="color: #4ECDC4; margin-top: 0;">🟢 Step 2: Analysis</h4>
        <ul style="flex-grow: 1;">
        <li>🔍 Application Analysis</li>
        <li>📄 Analysis Report Generation</li>
        <li>📋 Analysis Report Review</li>
        <li>🗄️ PostgreSQL Metadata</li>
        </ul>
        <small style="margin-top: auto;"><em>Source code analysis and transformation planning</em></small>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(69, 183, 209, 0.1), rgba(69, 183, 209, 0.05)); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #45B7D1; margin-bottom: 1rem; height: 200px; display: flex; flex-direction: column;">
        <h4 style="color: #45B7D1; margin-top: 0;">🔵 Step 3: Transformation</h4>
        <ul style="flex-grow: 1;">
        <li>🧪 Sample Transform</li>
        <li>🚀 Full Transform</li>
        <li>🔧 Test and Result Modification</li>
        <li>🔗 XML Merge</li>
        </ul>
        <small style="margin-top: auto;"><em>Perform actual SQL transformation tasks<br>(Test and modification are terminal tasks)</em></small>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(230, 126, 34, 0.1), rgba(230, 126, 34, 0.05)); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #E67E22; margin-bottom: 1rem; height: 200px; display: flex; flex-direction: column;">
        <h4 style="color: #E67E22; margin-top: 0;">🟠 Step 4: Test & Reports</h4>
        <ul style="flex-grow: 1;">
        <li>⚖️ Compare SQL Test</li>
        <li>📊 Generate Transform Report</li>
        <li>📄 View Transform Report</li>
        </ul>
        <small style="margin-top: auto;"><em>Validate transformation results and final reports</em></small>
        </div>
        """, unsafe_allow_html=True)


def get_group_name(step_id):
    """Return group name based on step ID"""
    if step_id == 1:
        return "Step 1: Environment Setup"
    elif 2 <= step_id <= 5:
        return "Step 2: Analysis"
    elif 6 <= step_id <= 9:
        return "Step 3: Transformation"
    else:
        return "Step 4: Test & Reports"
