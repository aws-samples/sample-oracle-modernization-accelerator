# MyBatis SQL Mapping 전환 결과 보고서 작성

## 작업 개요
MyBatis Oracle SQL을 Target DBMS로 변환한 결과를 분석하고 HTML 보고서를 생성합니다.

## 디렉토리 정보
- **Source XML 대상**: `$APP_TRANSFORM_FOLDER/SQLTransformTarget.csv`에 리스트된 XML 파일들
- **Target XML 대상**: `$TARGET_SQL_MAPPER_FOLDER` 하위에서 SQLTransformTarget.csv에 있는 XML과 같은 이름을 가진 파일들
- **결과 디렉토리**: `$APP_TRANSFORM_FOLDER/../`
- **임시 디렉토리**: `/tmp`

## 수행 작업

### 1단계: 데이터 수집 및 분석
- **Source 분석**: `$APP_TRANSFORM_FOLDER/SQLTransformTarget.csv`에서 Transform Target='Y'인 **모든** XML 파일들의 SQLID 통계 정보 파악 (Process 상태 무관)
- **Target 분석**: `$TARGET_SQL_MAPPER_FOLDER`에서 SQLTransformTarget.csv에 있는 XML과 같은 이름을 가진 파일들의 SQLID 통계 정보 파악
- **PostgreSQL 변환 규칙**: `TARGET_DBMS_TYPE=postgres`인 경우 `$APP_TOOLS_FOLDER/sqlTransformTargetPgRules.md` 참조
- **MySQL 변환 규칙**: `TARGET_DBMS_TYPE=mysql`인 경우 `$APP_TOOLS_FOLDER/sqlTransformTargetMysqlRules.md` 참조

### 2단계: HTML 보고서 생성
다음 구조의 한글 보고서를 생성합니다:

#### Transform 개요 (5개 카드 형태)
- SQLTransformTarget.csv에서 Transform Target='Y'인 총 XML 파일 수
- TARGET_SQL_MAPPER_FOLDER에서 매칭되는 XML 파일 수
- Source XML들의 총 SQLID 수
- Target XML들의 총 SQLID 수
- 전체 변환 성공률 (Target SQLID / Source SQLID * 100)

#### Process 상태별 현황 (카드 형태)
- Completed: 완료된 파일 수
- Sampled: 샘플링된 파일 수  
- Not yet: 미처리 파일 수
- Failed: 실패한 파일 수
- 기타: 기타 상태 파일 수

#### XML 변환 현황표 (테이블 형태)
SQLTransformTarget.csv 기준 XML 파일별:
- 파일명
- Process 상태
- Source SQLID 수
- Target SQLID 수
- 변환율

#### SQLID 변환 현황표 (테이블 형태)
각 XML 파일별로:
- Source XML 파일 경로 및 SQLID 수
- Target XML 파일 경로 및 SQLID 수
- 변환 성공/실패 상태
- Process 상태 (Not yet, Sampled, Completed, Failed 등)

#### Exceptions (테이블 형태)
다음 경우들을 상세 분석:
- SQLTransformTarget.csv에는 있지만 Target 폴더에 없는 파일들
- SQLID 수가 맞지 않는 파일들
- Process 상태가 'Failed'인 파일들
- SQLTransformTargetSelective.csv에 기록된 선별 변환 대상 파일들

#### SQL 유형별 리스트 (카드 형태)
SQLTransformTarget.csv에서 Transform Target='Y'인 모든 Source XML들을 분석하여 다음으로 분류:
- Select
- Insert
- Delete
- Update
- PL/SQL
- Procedure/Function 호출

#### Transform 결과 표
**테이블 구성**: 변환항목, 빈도수, 난이도, $TARGET_DBMS_TYPE 변환 규칙

- **변환 항목**: 
  - PostgreSQL: `$APP_TOOLS_FOLDER/sqlTransformTargetPgRules.md` 참조
  - MySQL: `$APP_TOOLS_FOLDER/sqlTransformTargetMysqlRules.md` 참조
  - 변환 대상 함수, 문법을 목록화

- **변환 규칙**:
  - PostgreSQL: `$APP_TOOLS_FOLDER/sqlTransformTargetPgRules.md` 참조
  - MySQL: `$APP_TOOLS_FOLDER/sqlTransformTargetMysqlRules.md` 참조

## HTML 스타일링 요구사항

### 스타일링 및 테이블 구성
- 모던한 반응형 디자인
- 통계는 카드형 레이아웃
- 실제 분석 예시는 코드 박스로 표시
  - Source: 빨간색 테두리
  - Target: 초록색 테두리
- 테이블 hover 효과 적용

### 테이블 스타일링 세부사항
- **테이블 폰트 크기**: 0.95em
- **헤더 폰트 크기**: 0.9em
- **행 hover 효과**: 배경색 #f8f9fa
- **배지 스타일**: border-radius: 12px, padding: 4px 8px
- **예시 미리보기**: 회색 배경, 좌측 파란 테두리, Courier New 폰트, 좌측 정렬
- **툴팁 기능**: cursor: help, title 속성 활용

### CSV 기반 분석 추가 요구사항
- **Process 상태별 색상 구분**:
  - 'Completed': 초록색 배지
  - 'Sampled': 파란색 배지
  - 'Not yet': 회색 배지
  - 'Failed': 빨간색 배지

### CSS 클래스 정의
```css
.feature-count { /* 발견 횟수 배지 */ }
.conversion-method { /* 변환 방법 배지 */ }
.example-preview { /* 예시 미리보기 박스 */ }
.complexity-very-high { /* 매우 높음 난이도 */ }
.complexity-high { /* 높음 난이도 */ }
.complexity-medium { /* 중간 난이도 */ }
.action-cell { /* 권장 조치사항 셀 */ }
.conversion-pair { /* Source-Target 비교 */ }
.status-completed { /* Completed 상태 */ }
.status-sampled { /* Sampled 상태 */ }
.status-not-yet { /* Not yet 상태 */ }
.status-failed { /* Failed 상태 */ }
```

## 출력 파일
- **Transform-Report.html** - 종합 보고서 (SQLTransformTarget.csv의 Transform Target='Y' 전체 파일 기반 분석) 
  - PostgreSQL: `$APP_TOOLS_FOLDER/sqlTransformTargetPgRules.md` 참조
  - MySQL: `$APP_TOOLS_FOLDER/sqlTransformTargetMysqlRules.md` 참조
  - 변환 대상 함수, 문법을 목록화

- **변환 규칙**:
  - PostgreSQL: `$APP_TOOLS_FOLDER/sqlTransformTargetPgRules.md` 참조
  - MySQL: `$APP_TOOLS_FOLDER/sqlTransformTargetMysqlRules.md` 참조

## HTML 스타일링 요구사항

### 스타일링 및 테이블 구성
- 모던한 반응형 디자인
- 통계는 카드형 레이아웃
- 실제 분석 예시는 코드 박스로 표시
  - Source: 빨간색 테두리
  - Target: 초록색 테두리
- 테이블 hover 효과 적용

### 테이블 스타일링 세부사항
- **테이블 폰트 크기**: 0.95em
- **헤더 폰트 크기**: 0.9em
- **행 hover 효과**: 배경색 #f8f9fa
- **배지 스타일**: border-radius: 12px, padding: 4px 8px
- **예시 미리보기**: 회색 배경, 좌측 파란 테두리, Courier New 폰트, 좌측 정렬
- **툴팁 기능**: cursor: help, title 속성 활용

### CSS 클래스 정의
```css
.feature-count { /* 발견 횟수 배지 */ }
.conversion-method { /* 변환 방법 배지 */ }
.example-preview { /* 예시 미리보기 박스 */ }
.complexity-very-high { /* 매우 높음 난이도 */ }
.complexity-high { /* 높음 난이도 */ }
.complexity-medium { /* 중간 난이도 */ }
.action-cell { /* 권장 조치사항 셀 */ }
.conversion-pair { /* Source-Target 비교 */ }
```

## 출력 파일
- **Transform-Report.html** - 종합 보고서
