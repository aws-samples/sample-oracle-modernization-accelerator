"""
환영 페이지 (Welcome Page)
"""
import streamlit as st
import os
import plotly.graph_objects as go
import plotly.express as px
from .utils import get_page_text


def render_welcome_page():
    """환영 페이지 렌더링"""
    # 로그 뷰어나 qlog 뷰어 상태일 때는 렌더링하지 않음
    selected_action = st.session_state.get('selected_action')
    if selected_action in ["view_running_logs", "view_qlog"]:
        return
    
    show_welcome_screen()


def show_welcome_screen():
    """환영 화면 표시"""
    # 로그 뷰어나 qlog 뷰어 상태일 때는 표시하지 않음
    selected_action = st.session_state.get('selected_action')
    if selected_action in ["view_running_logs", "view_qlog"]:
        st.stop()
    
    current_lang = st.session_state.get('language', 'ko')
    
    # 다국어 제목
    if current_lang == 'ko':
        title = "🔄 OMA - Oracle Migration Assistant"
        subtitle = "Oracle to PostgreSQL Migration Tool - Web Interface"
        workflow_title = "## 🗺️ OMA 워크플로우"
    else:
        title = "🔄 OMA - Oracle Migration Assistant"
        subtitle = "Oracle to PostgreSQL Migration Tool - Web Interface"
        workflow_title = "## 🗺️ OMA Workflow"
        
    st.markdown(f"""
    <div class="main-header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 워크플로우 다이어그램 표시
    st.markdown(workflow_title)
    show_workflow_diagram()
    
    st.markdown("---")
    
    # 현재 환경 상태 요약
    env_status = st.session_state.oma_controller.check_environment()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if env_status['is_configured']:
            if current_lang == 'ko':
                st.success(f"✅ **프로젝트 설정 완료**\n\n프로젝트: {env_status['application_name']}")
            else:
                st.success(f"✅ **Project Configured**\n\nProject: {env_status['application_name']}")
        else:
            if current_lang == 'ko':
                st.error("❌ **환경 설정 필요**\n\n환경 설정을 먼저 실행하세요")
            else:
                st.error("❌ **Environment Setup Required**\n\nPlease configure environment first")
    
    with col2:
        st.info(f"📁 **OMA 디렉토리**\n\n{env_status['oma_base_dir']}")
    
    with col3:
        config_exists = os.path.exists(env_status['config_file'])
        if config_exists:
            st.success("💾 **설정 파일 존재**\n\n환경 변수 저장됨")
        else:
            st.warning("⚠️ **설정 파일 없음**\n\n환경 변수를 저장하세요")


def show_workflow_diagram():
    """OMA 워크플로우 다이어그램 표시 - 향상된 디자인"""
    
    # 워크플로우 단계 정의 - 테스트 및 결과 수정 포함
    steps = [
        {"id": 1, "name": "프로젝트<br>환경 정보", "x": 1, "y": 6.2, "color": "#FF6B6B", "gradient": "#FF8E8E", "icon": "📊"},
        {"id": 2, "name": "애플리케이션<br>분석", "x": 2, "y": 6.2, "color": "#4ECDC4", "gradient": "#6ED5D8", "icon": "🔍"},
        {"id": 3, "name": "분석 보고서<br>작성", "x": 3, "y": 6.2, "color": "#4ECDC4", "gradient": "#6ED5D8", "icon": "📄"},
        {"id": 4, "name": "분석 보고서<br>리뷰", "x": 4, "y": 6.2, "color": "#4ECDC4", "gradient": "#6ED5D8", "icon": "📋"},
        {"id": 5, "name": "PostgreSQL<br>메타데이터", "x": 5, "y": 6.2, "color": "#4ECDC4", "gradient": "#6ED5D8", "icon": "🗄️"},
        {"id": 6, "name": "샘플 변환", "x": 2, "y": 3.8, "color": "#45B7D1", "gradient": "#67C3DB", "icon": "🧪"},
        {"id": 7, "name": "전체 변환", "x": 3, "y": 3.8, "color": "#45B7D1", "gradient": "#67C3DB", "icon": "🚀"},
        {"id": 8, "name": "테스트 및<br>결과 수정", "x": 4, "y": 3.2, "color": "#FF9500", "gradient": "#FFB347", "icon": "🔧"},
        {"id": 9, "name": "XML Merge", "x": 5, "y": 3.8, "color": "#45B7D1", "gradient": "#67C3DB", "icon": "🔗"},
        {"id": 10, "name": "Compare<br>SQL Test", "x": 2, "y": 1.4, "color": "#96CEB4", "gradient": "#A8D5C4", "icon": "⚖️"},
        {"id": 11, "name": "변환 보고서<br>생성", "x": 3, "y": 1.4, "color": "#E67E22", "gradient": "#F39C12", "icon": "📊"},
        {"id": 12, "name": "변환 보고서<br>보기", "x": 4, "y": 1.4, "color": "#E67E22", "gradient": "#F39C12", "icon": "📄"},
    ]
    
    # 연결선 정의 - 테스트 및 결과 수정을 중심으로 한 워크플로우
    connections = [
        (1, 2), (2, 3), (3, 4), (4, 5),  # 2단계: 분석 라인
        (5, 6), (5, 7),  # 분석 → 샘플/전체 변환
        (6, 8), (7, 8),  # 샘플/전체 변환 → 테스트 및 결과 수정
        (8, 9),  # 테스트 및 결과 수정 → XML Merge
        (9, 10),  # XML Merge → Compare SQL Test
        (9, 11), (11, 12)  # XML Merge → 변환 보고서 생성 → 보기
    ]
    
    # Plotly 그래프 생성
    fig = go.Figure()
    
    # 그룹 배경 영역 추가 - 현재 구조에 맞게 수정
    group_areas = [
        {"name": "1단계: 환경 설정", "x": [0.3, 1.7, 1.7, 0.3, 0.3], "y": [5.0, 5.0, 7.4, 7.4, 5.0], 
         "color": "rgba(255, 107, 107, 0.15)", "border": "rgba(255, 107, 107, 0.4)"},
        {"name": "2단계: 분석", "x": [1.3, 5.7, 5.7, 1.3, 1.3], "y": [5.0, 5.0, 7.4, 7.4, 5.0], 
         "color": "rgba(78, 205, 196, 0.15)", "border": "rgba(78, 205, 196, 0.4)"},
        {"name": "3단계: 변환", "x": [1.3, 4.7, 4.7, 1.3, 1.3], "y": [2.6, 2.6, 5.0, 5.0, 2.6], 
         "color": "rgba(69, 183, 209, 0.15)", "border": "rgba(69, 183, 209, 0.4)"},
        {"name": "4단계: 테스트 & 보고서", "x": [1.3, 4.7, 4.7, 1.3, 1.3], "y": [0.2, 0.2, 2.6, 2.6, 0.2], 
         "color": "rgba(230, 126, 34, 0.15)", "border": "rgba(230, 126, 34, 0.4)"}
    ]
    
    # 배경 영역 추가 - 더 부드러운 스타일
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
    
    # 그룹 라벨 추가 - 현재 구조에 맞게 수정
    group_labels = [
        {"text": "🔴 1단계: 환경 설정", "x": 1.0, "y": 7.2, "color": "#FF6B6B"},
        {"text": "🟢 2단계: 분석", "x": 3.5, "y": 7.2, "color": "#4ECDC4"},
        {"text": "🔵 3단계: 변환", "x": 3.0, "y": 4.8, "color": "#45B7D1"},
        {"text": "🟠 4단계: 테스트 & 보고서", "x": 3.0, "y": 2.4, "color": "#E67E22"}
    ]
    
    # 라벨 텍스트만 추가 (배경 박스 제거)
    for label in group_labels:
        fig.add_trace(go.Scatter(
            x=[label["x"]],
            y=[label["y"]],
            mode='text',
            text=label["text"],
            textfont=dict(size=16, color=label["color"], family="Arial Black"),
            textposition="middle center",  # 가운데 정렬
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # 연결선 추가 - 더 예쁜 스타일과 애니메이션 효과
    for from_id, to_id in connections:
        from_step = next(s for s in steps if s["id"] == from_id)
        to_step = next(s for s in steps if s["id"] == to_id)
        
        # 연결선 스타일 - 테스트 및 결과 수정 관련 연결선 강조
        if to_id == 8:  # 테스트 및 결과 수정으로 향하는 연결선
            line_color = '#FF6B35'
            line_width = 5
            line_dash = "solid"
            opacity = 0.8
        else:
            line_color = '#B8BCC8'
            line_width = 4
            line_dash = "solid"
            opacity = 0.7
        
        # 화살표 효과를 위한 연결선
        fig.add_trace(go.Scatter(
            x=[from_step["x"], to_step["x"]],
            y=[from_step["y"], to_step["y"]],
            mode='lines',
            line=dict(color=line_color, width=line_width, dash=line_dash),
            opacity=opacity,
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # 화살표 추가 (연결선 끝부분) - 크기 증가
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
                line=dict(color='white', width=2)  # 테두리도 두껍게
            ),
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # 단계 노드 추가 - 테스트 및 결과 수정 특별 표시
    for step in steps:
        # 테스트 및 결과 수정은 특별한 스타일 (터미널 작업 강조)
        if step["id"] == 8:  # 테스트 및 결과 수정
            marker_size = 110
            marker_color = step["color"]
            border_width = 5
            border_color = '#FFD700'  # 골드 테두리
            text_size = 14
        else:
            marker_size = 95
            marker_color = step["color"]
            border_width = 4
            border_color = 'white'
            text_size = 13
        
        # 메인 노드 (그림자 제거)
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
            hovertemplate=f"<b>{step['name'].replace('<br>', ' ')}</b><br>단계 {step['id']}<br>그룹: {get_group_name(step['id'])}<extra></extra>"
        ))
    
    # 레이아웃 설정 - 더 모던하고 예쁜 스타일
    fig.update_layout(
        title={
            'text': "🌟 OMA 워크플로우 - 단계별 프로세스 🌟",
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
            range=[-1.4, 7.8]  # -1.2, 7.6 → -1.4, 7.8 (더 넓은 범위로 여유 확보)
        ),
        plot_bgcolor='rgba(248, 249, 250, 0.9)',
        paper_bgcolor='rgba(255, 255, 255, 0.95)',
        height=750,  # 650 → 750 (높이 100px 증가)
        margin=dict(l=40, r=40, t=120, b=50),  # 하단 여백 40 → 50
        # 호버 효과 개선
        hoverlabel=dict(
            bgcolor="white",
            font_size=16,  # 14 → 16
            font_family="Arial"
        )
    )
    
    # 다이어그램 표시 - 그라데이션 배경 컨테이너로 감싸기
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
    
    # 그라데이션 배경 컨테이너로 감싸기
    st.markdown('<div class="workflow-container">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 워크플로우 설명을 더 예쁘게
    st.markdown("""
    <div style="text-align: center; margin: 2rem 0;">
        <h3 style="color: #2C3E50; font-family: Arial Black;">✨ 각 단계를 클릭하여 상세 정보를 확인하세요 ✨</h3>
        <p style="color: #7F8C8D; font-size: 16px;">화살표를 따라 순서대로 진행하면 완벽한 마이그레이션이 가능합니다!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 단계별 설명을 4컬럼으로 구성 - 동일한 높이
    st.markdown("### 📋 단계별 상세 가이드")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(255, 107, 107, 0.1), rgba(255, 107, 107, 0.05)); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #FF6B6B; margin-bottom: 1rem; height: 200px; display: flex; flex-direction: column;">
        <h4 style="color: #FF6B6B; margin-top: 0;">🔴 1단계: 환경 설정</h4>
        <ul style="flex-grow: 1;">
        <li>📊 프로젝트 환경 정보</li>
        </ul>
        <small style="margin-top: auto;"><em>모든 작업의 기초가 되는 환경 변수 설정</em></small>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(78, 205, 196, 0.1), rgba(78, 205, 196, 0.05)); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #4ECDC4; margin-bottom: 1rem; height: 200px; display: flex; flex-direction: column;">
        <h4 style="color: #4ECDC4; margin-top: 0;">🟢 2단계: 분석</h4>
        <ul style="flex-grow: 1;">
        <li>🔍 애플리케이션 분석</li>
        <li>📄 분석 보고서 작성</li>
        <li>📋 분석 보고서 리뷰</li>
        <li>🗄️ PostgreSQL 메타데이터</li>
        </ul>
        <small style="margin-top: auto;"><em>소스 코드 분석 및 변환 계획 수립</em></small>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(69, 183, 209, 0.1), rgba(69, 183, 209, 0.05)); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #45B7D1; margin-bottom: 1rem; height: 200px; display: flex; flex-direction: column;">
        <h4 style="color: #45B7D1; margin-top: 0;">🔵 3단계: 변환</h4>
        <ul style="flex-grow: 1;">
        <li>🧪 샘플 변환</li>
        <li>🚀 전체 변환</li>
        <li>🔧 테스트 및 결과 수정</li>
        <li>🔗 XML Merge</li>
        </ul>
        <small style="margin-top: auto;"><em>실제 SQL 변환 작업 수행<br>(테스트 및 수정은 터미널 작업)</em></small>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(230, 126, 34, 0.1), rgba(230, 126, 34, 0.05)); 
                    padding: 1rem; border-radius: 10px; border-left: 4px solid #E67E22; margin-bottom: 1rem; height: 200px; display: flex; flex-direction: column;">
        <h4 style="color: #E67E22; margin-top: 0;">🟠 4단계: 테스트 & 보고서</h4>
        <ul style="flex-grow: 1;">
        <li>⚖️ Compare SQL Test</li>
        <li>📊 변환 보고서 생성</li>
        <li>📄 변환 보고서 보기</li>
        </ul>
        <small style="margin-top: auto;"><em>변환 결과 검증 및 최종 보고서</em></small>
        </div>
        """, unsafe_allow_html=True)


def get_group_name(step_id):
    """단계 ID에 따른 그룹명 반환"""
    if step_id == 1:
        return "1단계: 환경 설정"
    elif 2 <= step_id <= 5:
        return "2단계: 분석"
    elif 6 <= step_id <= 9:
        return "3단계: 변환"
    else:
        return "4단계: 테스트 & 보고서"
