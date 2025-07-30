# SQL 변환 테스트 결과 HTML 보고서 생성 프롬프트

## 역할 정의
SQL 변환 테스트 결과를 기반으로 유려한 HTML 보고서를 생성하는 전문가 역할을 수행합니다.

## 환경 설정
- **애플리케이션 환경**: `$APPLICATION_NAME`
- **통합 테스트 로그 파일**: `$APP_LOGS_FOLDER/postTransform/sqlTestResult.log`
- **보고서 저장 위치**: `$APP_TRASFORM_FOLDER/TransformReport-$APPLICATION_NAME.html`
- **Reference**: Apply environment information from $APP_TOOLS_FOLDER/environmentContext.md

## 목표
SQL 변환 테스트 결과를 분석하여 **유려하고 전문적인 HTML 보고서**를 생성합니다.

## 작업 원칙
1. **통계 데이터 수집**: 테스트 로그에서 결과 통계 추출
2. **시각화**: 차트와 그래프를 포함한 직관적인 데이터 표현
3. **반응형 디자인**: 다양한 디바이스에서 최적화된 표시
4. **전문성**: 기술적 내용을 명확하고 이해하기 쉽게 표현
5. **완전성**: 모든 테스트 결과와 오류 정보 포함

## HTML 보고서 구조

### 1. 기본 HTML 템플릿
```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{APPLICATION_NAME} SQL 변환 테스트 결과 보고서</title>
    <style>
        /* 유려한 CSS 스타일 포함 */
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <!-- 보고서 내용 -->
</body>
</html>
```

### 2. CSS 스타일 가이드라인
```css
/* 전체 레이아웃 */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    background: white;
    border-radius: 15px;
    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
    overflow: hidden;
}

/* 헤더 스타일 */
.header {
    background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
    color: white;
    padding: 30px;
    text-align: center;
}

.header h1 {
    margin: 0;
    font-size: 2.5em;
    font-weight: 300;
}

.header .meta {
    margin-top: 15px;
    opacity: 0.9;
    font-size: 1.1em;
}

/* 섹션 스타일 */
.section {
    padding: 30px;
    border-bottom: 1px solid #eee;
}

.section:last-child {
    border-bottom: none;
}

.section h2 {
    color: #2c3e50;
    border-bottom: 3px solid #3498db;
    padding-bottom: 10px;
    margin-bottom: 25px;
    font-size: 1.8em;
}

/* 통계 카드 */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 25px;
    border-radius: 10px;
    text-align: center;
    box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    transition: transform 0.3s ease;
}

.stat-card:hover {
    transform: translateY(-5px);
}

.stat-card .number {
    font-size: 3em;
    font-weight: bold;
    margin-bottom: 10px;
}

.stat-card .label {
    font-size: 1.2em;
    opacity: 0.9;
}

/* 테이블 스타일 */
.table-container {
    overflow-x: auto;
    margin: 20px 0;
}

table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
}

th {
    background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
    color: white;
    padding: 15px;
    text-align: left;
    font-weight: 600;
}

td {
    padding: 12px 15px;
    border-bottom: 1px solid #eee;
}

tr:hover {
    background-color: #f8f9fa;
}

.success {
    color: #27ae60;
    font-weight: bold;
}

.error {
    color: #e74c3c;
    font-weight: bold;
}

/* 차트 컨테이너 */
.chart-container {
    position: relative;
    height: 400px;
    margin: 30px 0;
}

.chart-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 30px;
}

/* 진행률 바 */
.progress-bar {
    background: #ecf0f1;
    border-radius: 10px;
    overflow: hidden;
    height: 20px;
    margin: 10px 0;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #27ae60 0%, #2ecc71 100%);
    transition: width 0.3s ease;
}

/* 오류 메시지 스타일 */
.error-message {
    background: #fff5f5;
    border-left: 4px solid #e74c3c;
    padding: 15px;
    margin: 10px 0;
    border-radius: 5px;
    font-family: monospace;
    font-size: 0.9em;
}

/* 반응형 디자인 */
@media (max-width: 768px) {
    .container {
        margin: 10px;
        border-radius: 10px;
    }
    
    .header {
        padding: 20px;
    }
    
    .header h1 {
        font-size: 2em;
    }
    
    .section {
        padding: 20px;
    }
    
    .stats-grid {
        grid-template-columns: 1fr;
    }
    
    .chart-grid {
        grid-template-columns: 1fr;
    }
}

/* Summary 섹션 스타일 */
.summary-overview {
    margin: 20px 0;
}

.summary-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.summary-card {
    display: flex;
    align-items: center;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    transition: transform 0.3s ease;
}

.summary-card:hover {
    transform: translateY(-3px);
}

.summary-card.success {
    background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
    color: white;
}

.summary-card.warning {
    background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
    color: white;
}

.summary-card.info {
    background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
    color: white;
}

.summary-icon {
    font-size: 2.5em;
    margin-right: 15px;
}

.summary-content {
    flex: 1;
}

.summary-number {
    font-size: 2.2em;
    font-weight: bold;
    margin-bottom: 5px;
}

.summary-label {
    font-size: 1.1em;
    opacity: 0.9;
}

.conversion-table {
    margin: 30px 0;
}

.conversion-table h3 {
    color: #2c3e50;
    margin-bottom: 20px;
    font-size: 1.4em;
}

.todo-summary {
    margin: 30px 0;
}

.todo-summary h3 {
    color: #e74c3c;
    margin-bottom: 20px;
    font-size: 1.4em;
}

.todo-alerts {
    display: grid;
    gap: 15px;
}

.todo-alert {
    background: #fff3cd;
    border-left: 4px solid #ffc107;
    padding: 15px;
    border-radius: 5px;
    display: flex;
    align-items: center;
}

.todo-alert-icon {
    font-size: 1.5em;
    margin-right: 15px;
    color: #856404;
}

.todo-alert-content {
    flex: 1;
}

.todo-alert-title {
    font-weight: bold;
    color: #856404;
    margin-bottom: 5px;
}

.todo-alert-desc {
    color: #6c757d;
    font-size: 0.9em;
}

/* Badge 스타일 */
.badge {
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 0.8em;
    font-weight: bold;
    text-transform: uppercase;
}

.badge.success {
    background-color: #d4edda;
    color: #155724;
}

.badge.warning {
    background-color: #fff3cd;
    color: #856404;
}

.badge.danger {
    background-color: #f8d7da;
    color: #721c24;
}

/* Function 분석 스타일 */
.function-analysis {
    margin: 20px 0;
}

.function-details {
    margin-top: 30px;
}

.function-details h3 {
    color: #2c3e50;
    margin-bottom: 20px;
    font-size: 1.4em;
}

/* TODO List 스타일 */
.todo-analysis {
    margin: 20px 0;
}

.directory-structure {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 30px;
}

.tree-view {
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
    line-height: 1.6;
    color: #495057;
}

.tree-view .folder {
    color: #007bff;
    font-weight: bold;
}

.tree-view .file {
    color: #28a745;
}

.todo-items {
    margin-top: 20px;
}

.todo-list {
    display: grid;
    gap: 20px;
}

.todo-item {
    background: #fff3cd;
    border-left: 4px solid #ffc107;
    padding: 20px;
    border-radius: 5px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.todo-item h4 {
    color: #856404;
    margin: 0 0 10px 0;
    font-size: 1.1em;
}

.todo-item .file-path {
    color: #6c757d;
    font-size: 0.9em;
    margin-bottom: 15px;
    font-family: monospace;
}

.todo-code {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 5px;
    padding: 15px;
    font-family: 'Courier New', monospace;
    font-size: 0.85em;
    line-height: 1.4;
    overflow-x: auto;
    white-space: pre-wrap;
}

.todo-code .line-number {
    color: #6c757d;
    margin-right: 10px;
    user-select: none;
}

.todo-code .todo-highlight {
    background-color: #fff3cd;
    padding: 2px 4px;
    border-radius: 3px;
}

/* Function 분석 스타일 */
.function-analysis {
    margin: 20px 0;
}

.function-details {
    margin-top: 30px;
}

.function-details h3 {
    color: #2c3e50;
    margin-bottom: 20px;
    font-size: 1.4em;
}

/* TODO List 스타일 */
.todo-analysis {
    margin: 20px 0;
}

.directory-structure {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 30px;
}

.tree-view {
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
    line-height: 1.6;
    color: #495057;
}

.tree-view .folder {
    color: #007bff;
    font-weight: bold;
}

.tree-view .file {
    color: #28a745;
}

.todo-items {
    margin-top: 20px;
}

.todo-list {
    display: grid;
    gap: 20px;
}

.todo-item {
    background: #fff3cd;
    border-left: 4px solid #ffc107;
    padding: 20px;
    border-radius: 5px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.todo-item h4 {
    color: #856404;
    margin: 0 0 10px 0;
    font-size: 1.1em;
}

.todo-item .file-path {
    color: #6c757d;
    font-size: 0.9em;
    margin-bottom: 15px;
    font-family: monospace;
}

.todo-code {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 5px;
    padding: 15px;
    font-family: 'Courier New', monospace;
    font-size: 0.85em;
    line-height: 1.4;
    overflow-x: auto;
    white-space: pre-wrap;
}

.todo-code .line-number {
    color: #6c757d;
    margin-right: 10px;
    user-select: none;
}

.todo-code .todo-highlight {
    background-color: #fff3cd;
    padding: 2px 4px;
    border-radius: 3px;
}
```

### 3. 보고서 섹션 구성

#### 3.1 헤더 섹션
```html
<div class="header">
    <h1>🚀 {APPLICATION_NAME} SQL 변환 테스트 결과</h1>
    <div class="meta">
        <p>📅 생성일시: {GENERATION_TIME}</p>
        <p>🎯 Target DBMS: {TARGET_DBMS_TYPE}</p>
        <p>📱 Application: {APPLICATION_NAME}</p>
    </div>
</div>
```

#### 3.2 Summary 섹션
```html
<div class="section">
    <h2>📋 변환 프로젝트 요약</h2>
    <div class="summary-overview">
        <div class="summary-stats">
            <div class="summary-card success">
                <div class="summary-icon">✅</div>
                <div class="summary-content">
                    <div class="summary-number">{TOTAL_CONVERSION_RATE}%</div>
                    <div class="summary-label">전체 변환율</div>
                </div>
            </div>
            <div class="summary-card warning">
                <div class="summary-icon">⚠️</div>
                <div class="summary-content">
                    <div class="summary-number">{TODO_COUNT}</div>
                    <div class="summary-label">TODO 항목</div>
                </div>
            </div>
            <div class="summary-card info">
                <div class="summary-icon">📊</div>
                <div class="summary-content">
                    <div class="summary-number">{TOTAL_MAPPERS}</div>
                    <div class="summary-label">총 매퍼</div>
                </div>
            </div>
        </div>
        
        <div class="conversion-table">
            <h3>🔄 매퍼별 변환 현황</h3>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>매퍼명</th>
                            <th>Source SQLIDs</th>
                            <th>Target SQLIDs</th>
                            <th>변환율</th>
                            <th>상태</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- 매퍼별 변환 정보 반복 -->
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="todo-summary">
            <h3>⚠️ 주요 TODO 항목</h3>
            <div class="todo-alerts">
                <!-- TODO 경고 항목들 -->
            </div>
        </div>
    </div>
</div>
```

#### 3.3 전체 통계 섹션
```html
<div class="section">
    <h2>📊 전체 통계</h2>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="number">{TOTAL_FILES}</div>
            <div class="label">전체 파일</div>
        </div>
        <div class="stat-card">
            <div class="number">{SUCCESS_COUNT}</div>
            <div class="label">성공</div>
        </div>
        <div class="stat-card">
            <div class="number">{FAIL_COUNT}</div>
            <div class="label">실패</div>
        </div>
        <div class="stat-card">
            <div class="number">{SUCCESS_RATE}%</div>
            <div class="label">성공률</div>
        </div>
    </div>
</div>
```

#### 3.4 SQL 타입별 통계 섹션
```html
<div class="section">
    <h2>🔍 SQL 타입별 상세 통계</h2>
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>SQL 타입</th>
                    <th>전체</th>
                    <th>성공</th>
                    <th>실패</th>
                    <th>성공률</th>
                    <th>테스트 방법</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>📋 SELECT</td>
                    <td>{SELECT_TOTAL}</td>
                    <td class="success">{SELECT_SUCCESS}</td>
                    <td class="error">{SELECT_FAIL}</td>
                    <td>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {SELECT_RATE}%"></div>
                        </div>
                        {SELECT_RATE}%
                    </td>
                    <td>WHERE 1=2 조건 추가</td>
                </tr>
                <!-- 다른 SQL 타입들... -->
            </tbody>
        </table>
    </div>
</div>
```

#### 3.5 시각화 섹션
```html
<div class="section">
    <h2>📈 시각화</h2>
    <div class="chart-grid">
        <div class="chart-container">
            <canvas id="successRateChart"></canvas>
        </div>
        <div class="chart-container">
            <canvas id="sqlTypeChart"></canvas>
        </div>
    </div>
</div>
```

#### 3.6 테스트 방법 섹션
```html
<div class="section">
    <h2>🧪 테스트 유형별 방법</h2>
    <div class="test-methods">
        <div class="method-card">
            <h3>📋 SELECT SQL 테스트</h3>
            <p>WHERE 1=2 조건을 추가하여 실제 데이터 반환 없이 구문 검증</p>
            <ul>
                <li>바인드 변수를 샘플 값으로 대체</li>
                <li>WHERE 조건에 1=2 추가로 안전한 테스트</li>
                <li>실제 DB 연결을 통한 구문 검증</li>
            </ul>
        </div>
        <!-- 다른 테스트 방법들... -->
    </div>
</div>
```

#### 3.7 오류 상세 정보 섹션
```html
<div class="section">
    <h2>❌ 오류 상세 정보</h2>
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>파일명</th>
                    <th>SQL 타입</th>
                    <th>오류 메시지</th>
                    <th>수정 여부</th>
                </tr>
            </thead>
            <tbody>
                <!-- 오류 정보 반복 -->
            </tbody>
        </table>
    </div>
</div>
```

#### 3.8 Function 전환 분석 섹션
```html
<div class="section">
    <h2>🔧 {TARGET_DBMS_TYPE} Function 전환 분석</h2>
    <div class="function-analysis">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="number">{TOTAL_FUNCTIONS}</div>
                <div class="label">전체 함수</div>
            </div>
            <div class="stat-card">
                <div class="number">{CONVERTED_FUNCTIONS}</div>
                <div class="label">변환 완료</div>
            </div>
            <div class="stat-card">
                <div class="number">{UNIQUE_FUNCTIONS}</div>
                <div class="label">고유 함수</div>
            </div>
            <div class="stat-card">
                <div class="number">{CONVERSION_RATE}%</div>
                <div class="label">변환율</div>
            </div>
        </div>
        
        <div class="function-details">
            <h3>📊 함수별 변환 현황</h3>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>함수명</th>
                            <th>사용 횟수</th>
                            <th>변환 상태</th>
                            <th>변환 함수</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- 함수 변환 정보 반복 -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
```

#### 3.9 TODO List 섹션
```html
<div class="section">
    <h2>📝 TODO List</h2>
    <div class="todo-analysis">
        <div class="directory-structure">
            <h3>📁 디렉토리 구조</h3>
            <div class="tree-view">
                <!-- 디렉토리 트리 구조 -->
            </div>
        </div>
        
        <div class="todo-items">
            <h3>⚠️ TODO 항목</h3>
            <div class="todo-list">
                <!-- TODO 항목들 -->
            </div>
        </div>
    </div>
</div>
```

### 4. JavaScript 차트 생성
```javascript
// 성공률 도넛 차트
const successRateCtx = document.getElementById('successRateChart').getContext('2d');
new Chart(successRateCtx, {
    type: 'doughnut',
    data: {
        labels: ['성공', '실패'],
        datasets: [{
            data: [{SUCCESS_COUNT}, {FAIL_COUNT}],
            backgroundColor: ['#27ae60', '#e74c3c'],
            borderWidth: 0
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            title: {
                display: true,
                text: '전체 성공률',
                font: { size: 16 }
            },
            legend: {
                position: 'bottom'
            }
        }
    }
});

// SQL 타입별 막대 차트
const sqlTypeCtx = document.getElementById('sqlTypeChart').getContext('2d');
new Chart(sqlTypeCtx, {
    type: 'bar',
    data: {
        labels: ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'Callable', 'ResultMap'],
        datasets: [{
            label: '성공',
            data: [{SELECT_SUCCESS}, {INSERT_SUCCESS}, {UPDATE_SUCCESS}, {DELETE_SUCCESS}, {CALLABLE_SUCCESS}, {RESULTMAP_SUCCESS}],
            backgroundColor: '#27ae60'
        }, {
            label: '실패',
            data: [{SELECT_FAIL}, {INSERT_FAIL}, {UPDATE_FAIL}, {DELETE_FAIL}, {CALLABLE_FAIL}, {RESULTMAP_FAIL}],
            backgroundColor: '#e74c3c'
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            title: {
                display: true,
                text: 'SQL 타입별 성공/실패',
                font: { size: 16 }
            }
        },
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});
```

## Python 스크립트 구조

### 1. 데이터 수집 및 분석
```python
import os
import re
import json
import glob
from datetime import datetime
from collections import defaultdict

def collect_test_statistics(log_file_path):
    """통합 테스트 로그에서 통계 데이터 수집"""
    stats = {
        'total_files': 0,
        'success_count': 0,
        'fail_count': 0,
        'sql_types': {
            'SELECT': {'total': 0, 'success': 0, 'fail': 0},
            'INSERT': {'total': 0, 'success': 0, 'fail': 0},
            'UPDATE': {'total': 0, 'success': 0, 'fail': 0},
            'DELETE': {'total': 0, 'success': 0, 'fail': 0},
            'Callable': {'total': 0, 'success': 0, 'fail': 0},
            'ResultMap': {'total': 0, 'success': 0, 'fail': 0}
        },
        'errors': []
    }
    
    # 통합 로그 파일 분석 로직
    with open(log_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # 로그 라인 파싱 및 통계 업데이트
            pass
    
    return stats

def analyze_error_patterns(errors):
    """오류 패턴 분석"""
    error_patterns = defaultdict(int)
    for error in errors:
        # 오류 패턴 분석 로직
        pass
    return error_patterns

def analyze_function_conversion(json_file_path):
    """Function 전환 분석"""
    function_stats = {
        'total_functions': 0,
        'converted_functions': 0,
        'unique_functions': 0,
        'conversion_rate': 0,
        'function_details': []
    }
    
    if not os.path.exists(json_file_path):
        return function_stats
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        function_counts = defaultdict(int)
        unique_functions = set()
        
        for item in data:
            if item.get('status') == 'success':
                function_stats['converted_functions'] += 1
                function_stats['total_functions'] += item.get('functions_count', 0)
                function_stats['unique_functions'] = item.get('unique_functions_count', 0)
                
                # 함수별 상세 정보 수집
                # 실제 구현에서는 SQL에서 함수를 파싱하여 분석
                
        if function_stats['total_functions'] > 0:
            function_stats['conversion_rate'] = round(
                (function_stats['converted_functions'] / len(data)) * 100, 1
            )
            
    except Exception as e:
        print(f"Function 분석 중 오류: {e}")
    
    return function_stats

def analyze_mapper_conversion(mapper_directory):
    """매퍼별 변환 현황 분석"""
    mapper_stats = []
    total_mappers = 0
    
    if not os.path.exists(mapper_directory):
        return mapper_stats, total_mappers
    
    # mapper 디렉토리 하위 탐색
    for root, dirs, files in os.walk(mapper_directory):
        # extract와 transform 폴더를 모두 포함하는 디렉토리 찾기
        if 'extract' in dirs and 'transform' in dirs:
            mapper_name = os.path.basename(root)
            total_mappers += 1
            
            # extract 폴더의 XML 파일 개수 (Source SQLIDs)
            extract_path = os.path.join(root, 'extract')
            source_count = 0
            if os.path.exists(extract_path):
                source_count = len([f for f in os.listdir(extract_path) if f.endswith('.xml')])
            
            # transform 폴더의 XML 파일 개수 (Target SQLIDs)
            transform_path = os.path.join(root, 'transform')
            target_count = 0
            if os.path.exists(transform_path):
                target_count = len([f for f in os.listdir(transform_path) if f.endswith('.xml')])
            
            # 변환율 계산
            conversion_rate = 0
            if source_count > 0:
                conversion_rate = round((target_count / source_count) * 100, 1)
            
            # 상태 결정
            status = "완료" if conversion_rate == 100 else "진행중" if conversion_rate > 0 else "대기"
            status_class = "success" if conversion_rate == 100 else "warning" if conversion_rate > 0 else "danger"
            
            mapper_stats.append({
                'name': mapper_name,
                'source_count': source_count,
                'target_count': target_count,
                'conversion_rate': conversion_rate,
                'status': status,
                'status_class': status_class
            })
    
    # 변환율 순으로 정렬
    mapper_stats.sort(key=lambda x: x['conversion_rate'], reverse=True)
    
    return mapper_stats, total_mappers

def summarize_todo_alerts(todo_items):
    """TODO 항목을 요약하여 경고 형태로 생성"""
    todo_alerts = []
    
    if not todo_items:
        return todo_alerts
    
    # 파일별 TODO 개수 집계
    file_todo_count = defaultdict(int)
    critical_todos = []
    
    for todo in todo_items:
        file_todo_count[todo['file']] += 1
        
        # 중요한 TODO 키워드 검색
        todo_content = todo['todo_content'].upper()
        if any(keyword in todo_content for keyword in ['FIXME', 'BUG', 'ERROR', 'CRITICAL', 'URGENT']):
            critical_todos.append(todo)
    
    # 가장 많은 TODO를 가진 파일들
    if file_todo_count:
        max_todo_file = max(file_todo_count.items(), key=lambda x: x[1])
        if max_todo_file[1] > 5:  # 5개 이상인 경우만
            todo_alerts.append({
                'type': 'high',
                'icon': '🚨',
                'title': f'높은 TODO 밀도',
                'description': f'{max_todo_file[0]} 파일에 {max_todo_file[1]}개의 TODO 항목이 있습니다.'
            })
    
    # 중요한 TODO 항목들
    if critical_todos:
        todo_alerts.append({
            'type': 'critical',
            'icon': '⚠️',
            'title': f'긴급 처리 필요',
            'description': f'{len(critical_todos)}개의 중요한 TODO 항목이 발견되었습니다.'
        })
    
    # 전체 TODO 개수가 많은 경우
    if len(todo_items) > 20:
        todo_alerts.append({
            'type': 'warning',
            'icon': '📝',
            'title': f'TODO 항목 관리 필요',
            'description': f'총 {len(todo_items)}개의 TODO 항목이 있습니다. 정기적인 정리가 필요합니다.'
        })
    
    return todo_alerts

def search_todo_items(mapper_directory):
    """TODO 항목 검색"""
    todo_items = []
    directory_structure = []
    
    if not os.path.exists(mapper_directory):
        return todo_items, directory_structure
    
    # 디렉토리 구조 생성
    for root, dirs, files in os.walk(mapper_directory):
        level = root.replace(mapper_directory, '').count(os.sep)
        indent = '  ' * level
        folder_name = os.path.basename(root)
        directory_structure.append(f"{indent}📁 {folder_name}/")
        
        # transform 폴더 내 XML 파일 검색
        if 'transform' in root:
            for file in files:
                if file.endswith('.xml'):
                    file_path = os.path.join(root, file)
                    sub_indent = '  ' * (level + 1)
                    directory_structure.append(f"{sub_indent}📄 {file}")
                    
                    # TODO 검색
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            
                        for i, line in enumerate(lines):
                            if 'TODO' in line.upper():
                                # TODO 주변 10줄 추출
                                start_line = max(0, i - 5)
                                end_line = min(len(lines), i + 6)
                                code_snippet = []
                                
                                for j in range(start_line, end_line):
                                    line_num = j + 1
                                    line_content = lines[j].rstrip()
                                    if 'TODO' in line_content.upper():
                                        code_snippet.append(f"{line_num:3d}: {line_content} ← TODO")
                                    else:
                                        code_snippet.append(f"{line_num:3d}: {line_content}")
                                
                                todo_items.append({
                                    'file': file,
                                    'file_path': file_path,
                                    'line_number': i + 1,
                                    'todo_content': line.strip(),
                                    'code_snippet': '\n'.join(code_snippet)
                                })
                                
                    except Exception as e:
                        print(f"파일 읽기 오류 {file_path}: {e}")
    
    return todo_items, directory_structure
```

### 2. HTML 생성
```python
def generate_html_report(stats, function_stats, mapper_stats, total_mappers, todo_items, todo_alerts, directory_structure, output_path):
    """HTML 보고서 생성"""
    
    # 전체 변환율 계산
    total_conversion_rate = 0
    if mapper_stats:
        total_conversion_rate = round(sum(m['conversion_rate'] for m in mapper_stats) / len(mapper_stats), 1)
    
    # 템플릿 데이터 준비
    template_data = {
        'APPLICATION_NAME': os.environ.get('APPLICATION_NAME', 'Unknown'),
        'TARGET_DBMS_TYPE': os.environ.get('TARGET_DBMS_TYPE', 'Unknown'),
        'GENERATION_TIME': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'TOTAL_FILES': stats['total_files'],
        'SUCCESS_COUNT': stats['success_count'],
        'FAIL_COUNT': stats['fail_count'],
        'SUCCESS_RATE': round((stats['success_count'] / stats['total_files']) * 100, 1) if stats['total_files'] > 0 else 0,
        
        # Summary 데이터
        'TOTAL_CONVERSION_RATE': total_conversion_rate,
        'TOTAL_MAPPERS': total_mappers,
        
        # Function 분석 데이터
        'TOTAL_FUNCTIONS': function_stats['total_functions'],
        'CONVERTED_FUNCTIONS': function_stats['converted_functions'],
        'UNIQUE_FUNCTIONS': function_stats['unique_functions'],
        'CONVERSION_RATE': function_stats['conversion_rate'],
        
        # TODO 데이터
        'TODO_COUNT': len(todo_items),
        'DIRECTORY_TREE': '\n'.join(directory_structure)
    }
    
    # SQL 타입별 데이터 추가
    for sql_type, data in stats['sql_types'].items():
        template_data[f'{sql_type}_TOTAL'] = data['total']
        template_data[f'{sql_type}_SUCCESS'] = data['success']
        template_data[f'{sql_type}_FAIL'] = data['fail']
        template_data[f'{sql_type}_RATE'] = round((data['success'] / data['total']) * 100, 1) if data['total'] > 0 else 0
    
    # HTML 템플릿 렌더링
    html_content = render_html_template(template_data, stats['errors'], function_stats, mapper_stats, todo_items, todo_alerts)
    
    # 파일 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML 보고서 생성 완료: {output_path}")

def render_html_template(data, errors, function_stats, mapper_stats, todo_items, todo_alerts):
    """HTML 템플릿 렌더링"""
    
    # 매퍼별 변환 현황 테이블 HTML 생성
    mapper_table_html = ""
    for mapper in mapper_stats:
        status_badge = f'<span class="badge {mapper["status_class"]}">{mapper["status"]}</span>'
        mapper_table_html += f"""
        <tr>
            <td>{mapper['name']}</td>
            <td>{mapper['source_count']}</td>
            <td>{mapper['target_count']}</td>
            <td>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {mapper['conversion_rate']}%"></div>
                </div>
                {mapper['conversion_rate']}%
            </td>
            <td>{status_badge}</td>
        </tr>
        """
    
    # TODO 경고 알림 HTML 생성
    todo_alerts_html = ""
    for alert in todo_alerts:
        todo_alerts_html += f"""
        <div class="todo-alert">
            <div class="todo-alert-icon">{alert['icon']}</div>
            <div class="todo-alert-content">
                <div class="todo-alert-title">{alert['title']}</div>
                <div class="todo-alert-desc">{alert['description']}</div>
            </div>
        </div>
        """
    
    # Summary 섹션 HTML
    summary_section_html = f"""
    <div class="section">
        <h2>📋 변환 프로젝트 요약</h2>
        <div class="summary-overview">
            <div class="summary-stats">
                <div class="summary-card success">
                    <div class="summary-icon">✅</div>
                    <div class="summary-content">
                        <div class="summary-number">{{TOTAL_CONVERSION_RATE}}%</div>
                        <div class="summary-label">전체 변환율</div>
                    </div>
                </div>
                <div class="summary-card warning">
                    <div class="summary-icon">⚠️</div>
                    <div class="summary-content">
                        <div class="summary-number">{{TODO_COUNT}}</div>
                        <div class="summary-label">TODO 항목</div>
                    </div>
                </div>
                <div class="summary-card info">
                    <div class="summary-icon">📊</div>
                    <div class="summary-content">
                        <div class="summary-number">{{TOTAL_MAPPERS}}</div>
                        <div class="summary-label">총 매퍼</div>
                    </div>
                </div>
            </div>
            
            <div class="conversion-table">
                <h3>🔄 매퍼별 변환 현황</h3>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>매퍼명</th>
                                <th>Source SQLIDs</th>
                                <th>Target SQLIDs</th>
                                <th>변환율</th>
                                <th>상태</th>
                            </tr>
                        </thead>
                        <tbody>
                            {mapper_table_html}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="todo-summary">
                <h3>⚠️ 주요 TODO 항목</h3>
                <div class="todo-alerts">
                    {todo_alerts_html}
                </div>
            </div>
        </div>
    </div>
    """
    
    # 기존 섹션들과 함께 Summary 섹션 추가
    data['SUMMARY_SECTION'] = summary_section_html
    
    # 나머지 렌더링 로직은 기존과 동일...
    return render_complete_template(data, function_stats, todo_items)
```

### 3. 메인 실행 함수
```python
def main():
    """메인 실행 함수"""
    app_logs_folder = os.environ.get('APP_LOGS_FOLDER')
    app_transform_folder = os.environ.get('APP_TRANSFORM_FOLDER')
    application_name = os.environ.get('APPLICATION_NAME')
    
    # 통합 로그 파일 경로
    log_file_path = f"{app_logs_folder}/postTransform/sqlTestResult.log"
    
    if not os.path.exists(log_file_path):
        print("통합 테스트 로그 파일을 찾을 수 없습니다.")
        return
    
    # 통계 수집
    stats = collect_test_statistics(log_file_path)
    
    # Function 전환 분석
    json_file_path = f"{app_transform_folder}/sqlTestResult.json"
    function_stats = analyze_function_conversion(json_file_path)
    
    # 매퍼별 변환 현황 분석
    mapper_directory = f"{app_logs_folder}/mapper"
    mapper_stats, total_mappers = analyze_mapper_conversion(mapper_directory)
    
    # TODO 항목 검색
    todo_items, directory_structure = search_todo_items(mapper_directory)
    
    # TODO 요약 경고 생성
    todo_alerts = summarize_todo_alerts(todo_items)
    
    # HTML 보고서 생성
    output_path = f"{app_logs_folder}/TransformTestReport-{application_name}.html"
    generate_html_report(stats, function_stats, mapper_stats, total_mappers, todo_items, todo_alerts, directory_structure, output_path)

if __name__ == "__main__":
    main()
```

## 실행 방법
```bash
# HTML 보고서 생성 스크립트 실행
python3 /path/to/generate_html_report.py

# 또는 직접 호출
cd $APP_LOGS_FOLDER/postTransform/
python3 -c "
import sys
sys.path.append('/path/to/script')
from generate_html_report import main
main()
"
```

## 예상 결과물
- **파일 위치**: `$APP_LOGS_FOLDER/TransformTestReport-$APPLICATION_NAME.html`
- **특징**: 
  - 반응형 웹 디자인
  - 인터랙티브 차트 및 그래프
  - 전문적이고 직관적인 UI/UX
  - 통합 테스트 결과 및 오류 정보 포함
  - 브라우저에서 바로 열어볼 수 있는 완전한 HTML 파일
