# OMA App Conversion

Oracle MyBatis Mapper를 PostgreSQL/MySQL로 자동 변환하는 도구입니다.

> 영어 버전: [README.md](README.md)

## 개요

`app` 폴더는 Oracle MyBatis Mapper XML 파일을 PostgreSQL/MySQL 호환 형식으로 변환하는 도구를 제공합니다.

### 주요 기능

- **Oracle Dictionary 생성**: Oracle 스키마 메타데이터 추출
- **SQL 변환**: Oracle SQL → PostgreSQL/MySQL 자동 변환 (LLM 기반)
- **Mapper 분할/병합**: 대용량 XML 파일 관리
- **Extension 감지**: 고객 프레임워크 바인드 변수 스캔
- **OGNL 감지**: Java 정적 메서드 호출 스캔
- **Validator**: 변환된 SQL 검증 (실제 DB 실행)

---

## 폴더 구조

```
app/
├── .claude/
│   └── skills/           # Claude Code 스킬 (자동화 명령)
│       ├── verify-env.sh         # 환경 검증 (Extension/OGNL 자동 스캔)
│       ├── build-oracle-dict.sh  # Oracle Dictionary 생성
│       ├── split-mappers.sh      # Mapper 분할
│       ├── convert-sql.sh        # SQL 변환 (단일 파일)
│       ├── merge-mappers.sh      # Mapper 병합
│       └── run-validator.sh      # SQL 검증
├── tools/                # Python 변환 스크립트
│   ├── load_oma_env.sh           # oma.properties 로더
│   ├── oracle_dictionary.py      # Oracle 메타데이터 추출
│   ├── split_mapper.py           # Mapper 분할
│   ├── convert_sql.py            # SQL 변환 (LLM)
│   ├── merge_mapper.py           # Mapper 병합
│   ├── scan_extension_variables.py   # Extension 스캔
│   ├── scan_ognl.py              # OGNL 스캔
│   └── validator/        # Java Validator
│       ├── src/
│       └── target/mapper-validator-1.0.0.jar
├── extensions/           # Extension 설정 파일
│   └── extension.json
├── output/               # 실행 결과물
│   ├── oracle_dictionary.json
│   ├── validation-report.json
│   └── validation.log
├── mappers/              # 변환 작업 디렉토리 (중간 산출물)
└── setup.sh              # 초기 설정 스크립트
```

---

## 사전 준비

### 1. 환경 설정

`/home/ec2-user/workspace/oma/env/oma.properties`에서 환경 변수 설정:

```properties
[COMMON]
# Oracle 연결
ORACLE_HOST=10.0.X.X
ORACLE_PORT=1521
ORACLE_SID=ORCLPDB1
ORACLE_USER=username
ORACLE_PASSWORD=password
ORACLE_SCHEMA=SCHEMA_NAME
ORACLE_HOME=/home/ec2-user/oracle

# PostgreSQL 연결 (Standard Variables)
PGHOST=cluster.xxxxx.region.rds.amazonaws.com
PGPORT=5432
PGDATABASE=dbname
PGSCHEMA=schema_name
PGUSER=username
PGPASSWORD=password

# App 변환 설정
SOURCE_WORKSPACE=/home/ec2-user/workspace/source    # 원본 Mapper 위치
TARGET_WORKSPACE=/home/ec2-user/workspace/target    # 변환 결과 위치
BEDROCK_MODEL_ID=global.anthropic.claude-opus-4-7
MAX_WORKERS=7
TARGET_DB_TYPE=postgres
```

> 📝 **참고**: 자세한 환경 설정은 [env/README_KR.md](../env/README_KR.md) 참고

### 2. 소스 Mapper 준비

원본 Oracle Mapper 파일을 SOURCE_WORKSPACE에 배치:

```bash
SOURCE_WORKSPACE/
└── my-project/
    └── mappers/
        ├── UserMapper.xml
        ├── OrderMapper.xml
        └── ProductMapper.xml
```

### 3. Extension 키워드 설정 (고객 협의)

**Extension이란?**
- 고객사 프레임워크의 특수 바인드 변수
- 예: `#{GRIDPAGING_START}`, `#{FRAMEWORK_SESSION_ID}`

**사전 협의 사항:**
1. 고객과 Extension 변수 목록 확인
2. 네이밍 컨벤션 파악 (예: GRIDPAGING_*, EGOVFRAME_*)
3. `tools/scan_extension_variables.py` 키워드 수정:

```python
# Line 63-65 수정
is_extension = (
    var.isupper() and '_' in var
    or 'GRIDPAGING' in var.upper()    # ← 고객 키워드로 변경
    or 'FRAMEWORK' in var.upper()     # ← 고객 키워드로 변경
    or 'EGOVFRAME' in var.upper()     # ← 추가 키워드
)
```

---

## 변환 프로세스

**중요**: 모든 작업은 **app 폴더에서 Claude Code를 실행**하고 **스킬을 통해** 진행합니다.

```bash
# 1. app 폴더로 이동
cd /home/ec2-user/workspace/oma/app

# 2. Claude Code 실행
claude
```

---

### Step 0: 환경 검증 (필수)

변환 작업 전 환경을 검증하고 Extension/OGNL을 자동 스캔합니다.

**Claude Code에서 실행:**
```
/verify-env
```

**검증 항목:**
1. ✅ Python 3.11+ 설치
2. ✅ 환경 변수 로드 (oma.properties)
3. ✅ Oracle Client (sqlplus) 확인
4. ✅ PostgreSQL/MySQL Client 확인
5. ✅ Oracle DB 연결
6. ✅ Target DB 연결
7. ✅ SOURCE_WORKSPACE 확인
8. ✅ Mapper 디렉토리 확인
9. ✅ Bedrock LLM 연결
10. ✅ **Extension 변수 자동 스캔**
11. ✅ **OGNL 표현식 자동 스캔**

**출력 예시:**
```
-------------------------------------------
10. Extension Variable Detection
-------------------------------------------
Scanning for Extension variables...
✓ Extension scan completed
  → Found 3 Extension variables
  → Configuration: extensions/extension.json

-------------------------------------------
11. OGNL Expression Detection
-------------------------------------------
Scanning for OGNL expressions (@Class@method patterns)...
✓ OGNL implementation guide generated
  → Found OGNL expressions requiring implementation
  → Implementation guide: docs/OGNL_IMPLEMENTATION_GUIDE.md

===========================================
Environment Verification Summary
===========================================
  Extension Variables:
    → 3 variables found
    → Review: extensions/extension.json

  OGNL Expressions:
    → FOUND - Implementation required
    → Read guide: docs/OGNL_IMPLEMENTATION_GUIDE.md
```

**Extension 발견 시:**
```bash
# 1. 결과 확인
cat extensions/extension.json

# 2. 수동 검토 (오분류 제거)
vi extensions/extension.json

# 3. Oracle/PostgreSQL 값 입력
{
  "enabled": true,
  "variables": {
    "GRIDPAGING_START": {
      "oracle": "...",
      "postgres": "..."
    }
  }
}
```

**OGNL 발견 시:**
```bash
# 1. 가이드 확인
cat docs/OGNL_IMPLEMENTATION_GUIDE.md

# 2. 고객으로부터 Java 라이브러리(.jar) 제공받기
# 3. Validator 실행 시 클래스패스에 등록 (Step 4 참고)
```

---

### Step 1: Oracle Dictionary 생성

Oracle 스키마의 메타데이터를 추출합니다.

**Claude Code에서 실행:**
```
/build-oracle-dict 10
```

**생성 결과:**
- `output/oracle_dictionary.json` (약 5MB)

**Dictionary 내용:**
- 688개 테이블 메타데이터
- 컬럼 타입, 길이, Precision, Scale
- Primary Key, Foreign Key
- 각 컬럼의 샘플 데이터 (10개)
- Row Count

**조회 방법:**
```bash
# 특정 컬럼 조회
python3.11 tools/oracle_dictionary.py --lookup TB_USER.USER_ID

# 테이블 전체 조회
python3.11 tools/oracle_dictionary.py --table TB_USER
```

---

### Step 2: Mapper 분할 (선택사항)

대용량 Mapper XML을 SQL ID별로 분할합니다.

**Claude Code에서 실행:**
```
/split-mappers my-project
```

**입력:**
```
SOURCE_WORKSPACE/
└── my-project/
    └── mappers/
        └── UserMapper.xml  (10,000 lines)
```

**출력:**
```
mappers/
└── my-project/
    └── oracle/
        └── UserMapper/
            ├── selectUser.xml
            ├── insertUser.xml
            ├── updateUser.xml
            └── deleteUser.xml
```

**언제 사용:**
- Mapper 파일이 5,000 라인 이상
- SQL ID가 50개 이상
- 병렬 변환으로 속도 향상 필요

**언제 생략:**
- Mapper 파일이 작은 경우 (< 3,000 라인)
- 직접 변환 가능

---

### Step 3: SQL 변환 (핵심)

Oracle SQL을 PostgreSQL/MySQL로 자동 변환합니다. 이 단계가 **OMA의 핵심 기능**입니다.

**핵심 원칙: LLM이 SQL을 읽고 이해하고 변환합니다.**
- 정규식 사용 없음 (정규식은 복잡한 SQL 파싱 불가)
- LLM이 테이블 추출, 바인드 변수 매핑, TC 생성 모두 수행
- 아무리 복잡한 SQL도 완벽 처리 (콤마 구문, 서브쿼리, CTE, UNION 등)

#### 실행 방법

**단일 파일 변환 (Claude Code):**
```
/convert-sql mappers/my-project/oracle/UserMapper/selectUser.xml
```

**전체 프로젝트 변환 (Shell - 병렬):**
```bash
# Claude Code에서 빠져나와서 (Ctrl+D)
cd /home/ec2-user/workspace/oma/app

# 병렬 변환 (MAX_WORKERS=7)
find mappers/my-project/oracle -name "*.xml" | \
  xargs -P 7 -I {} bash .claude/skills/convert-sql.sh "{}"
```

#### 변환 프로세스 상세 (3단계 LLM 처리)

**전체 흐름:**
```
분할된 XML 파일 → [LLM 1차: 테이블 추출] → Dictionary 조회 → [LLM 2차: SQL 변환] → TC 파일 생성 → 저장
```

각 Mapper 파일을 개별적으로 변환합니다:

---

**Phase 1: XML 파싱 (Python)**

```python
# 입력: mappers/my-project/oracle/UserMapper/selectUser.xml
# (Step 2에서 이미 SQL ID별로 분할된 파일)

<?xml version="1.0" encoding="UTF-8"?>
<mapper namespace="com.example.UserMapper">
  <select id="selectUser" resultType="User">
    SELECT USER_ID, USER_NAME, SYSDATE AS REG_DT
    FROM TB_USER
    WHERE USER_ID = #{userId}
      AND REG_DT >= #{startDate}
  </select>
</mapper>

# Python ElementTree로 파싱:
# - SQL 본문 추출
# - namespace, resultType 등 메타데이터 추출
# - <include refid="..."/> 참조 감지
```

---

**Phase 2: LLM 1차 호출 - 테이블명 추출**

```python
# LLM에게 SQL을 주고 테이블 목록 요청
Prompt to LLM:
"""
Analyze this SQL and extract all table names:

<select id="selectUser">
  SELECT USER_ID, USER_NAME, SYSDATE AS REG_DT
  FROM TB_USER
  WHERE USER_ID = #{userId}
    AND REG_DT >= #{startDate}
</select>

Output ONLY a JSON array: ["TABLE1", "TABLE2", ...]
Include tables from:
- FROM clause
- JOIN clauses
- Subqueries
- Comma-separated lists (FROM A, B, C)
"""

# LLM 응답:
["TB_USER"]

# 출력:
→ Step 1: LLM extracts table names from SQL
→ LLM found 1 tables: TB_USER
```

**왜 LLM을 사용하는가?**
- ✅ 정규식은 복잡한 SQL 파싱 불가
- ✅ `FROM A, B, C` (콤마 구문) → 정규식은 A만 찾음, LLM은 모두 찾음
- ✅ 서브쿼리, CTE, UNION → 정규식 실패, LLM 완벽
- ✅ 중첩 서브쿼리 → 정규식 불가능, LLM 가능

**LLM이 찾을 수 있는 모든 패턴:**
```sql
-- 1. FROM 콤마 구문
FROM TB_USER A, TB_ORDER B, TB_PRODUCT C  → 3개 모두 찾음

-- 2. 서브쿼리 (모든 위치)
SELECT (SELECT COUNT(*) FROM TB_COUNT) FROM TB_USER  → 2개 찾음
WHERE ID IN (SELECT ID FROM TB_LIST)                 → 2개 찾음

-- 3. CTE (WITH)
WITH TEMP AS (SELECT * FROM TB_TEMP) 
SELECT * FROM TEMP                                   → TB_TEMP 찾음

-- 4. UNION
SELECT * FROM TB_A UNION SELECT * FROM TB_B          → 2개 찾음

-- 5. 중첩 서브쿼리
FROM (SELECT * FROM (SELECT * FROM TB_DEEP))         → TB_DEEP 찾음
```

---

**Phase 3: Dictionary 조회 (Python)**

```python
# LLM이 찾은 테이블로 oracle_dictionary.json 조회
for table in ["TB_USER"]:
    table_info = oracle_dict['tables'][table]
    
# 결과:
TB_USER:
  - USER_ID: VARCHAR2(20), NOT NULL, sample="USER001"
  - USER_NAME: VARCHAR2(50), NULLABLE, sample="홍길동"
  - REG_DT: DATE, NOT NULL, sample="2024-01-15"
  - STATUS: VARCHAR2(1), NOT NULL, sample="Y"

# Schema 정보를 텍스트로 포맷팅:
=== Oracle Schema Information ===
Table: TB_USER
  USER_ID: VARCHAR2(20) NOT NULL (sample: USER001)
  USER_NAME: VARCHAR2(50) (sample: 홍길동)
  REG_DT: DATE NOT NULL (sample: 2024-01-15)
  STATUS: VARCHAR2(1) NOT NULL (sample: Y)

# 출력:
→ Step 2: Schema information built for 1 tables
```

---

**Phase 4: LLM 2차 호출 - SQL 변환**

```python
# LLM에게 Oracle SQL + Schema 정보 전달, PostgreSQL 변환 요청
Prompt to LLM:
"""
Convert this Oracle SQL to PostgreSQL:

<select id="selectUser" resultType="User">
  SELECT USER_ID, USER_NAME, SYSDATE AS REG_DT
  FROM TB_USER
  WHERE USER_ID = #{userId}
    AND REG_DT >= #{startDate}
</select>

=== Oracle Schema Information ===
Table: TB_USER
  USER_ID: VARCHAR2(20) NOT NULL (sample: USER001)
  REG_DT: DATE NOT NULL (sample: 2024-01-15)

Requirements:
1. Convert Oracle syntax to PostgreSQL
2. Add explicit type casting (::DATE, ::INTEGER) using schema info
3. Map bind variables to TABLE.COLUMN
4. Generate test cases respecting column constraints:
   - VARCHAR2(20) → max 20 characters
   - DATE → valid date format
   - NOT NULL → no null values

Output JSON:
{
  "converted_xml": "...",
  "bind_variables": {"#{var}": "TABLE.COLUMN"},
  "test_cases": [{"description": "...", "parameters": {...}}]
}
"""

# LLM 응답:
{
  "converted_xml": "<select id=\"selectUser\" resultType=\"User\">\n  SELECT user_id, user_name, CURRENT_TIMESTAMP AS reg_dt\n  FROM tb_user\n  WHERE user_id = #{userId}\n    AND reg_dt >= #{startDate}::DATE\n</select>",
  
  "bind_variables": {
    "#{userId}": "TB_USER.USER_ID",
    "#{startDate}": "TB_USER.REG_DT"
  },
  
  "test_cases": [
    {
      "description": "Normal user query with date filter",
      "parameters": {
        "userId": "USER001",
        "startDate": "2024-01-01"
      }
    },
    {
      "description": "Recent user query",
      "parameters": {
        "userId": "USER999",
        "startDate": "2024-12-01"
      }
    }
  ]
}

# 출력:
→ Step 3: LLM converts SQL to postgres
✓ selectUser.xml - 2 bind vars
```

**JSON 파싱 실패 시 복구:**
```python
# LLM이 잘못된 JSON 반환 시
try:
    result = json.loads(llm_response)
except JSONDecodeError:
    # LLM에게 JSON 수정 요청 (정규식 사용 안 함!)
    fixed = call_bedrock("Fix this malformed JSON: ...")
    result = json.loads(fixed)
```

---

**Phase 5: TC 파일 생성 (Python)**

```python
# LLM이 반환한 bind_variables, test_cases와
# Dictionary의 data_types를 결합하여 TC 파일 생성

```json
// selectUser.tc.json
{
  "file": "selectUser.xml",
  
  // LLM이 생성한 바인드 변수 매핑
  "bind_variables": {
    "#{userId}": "TB_USER.USER_ID",
    "#{startDate}": "TB_USER.REG_DT"
  },
  
  // Dictionary에서 조회한 데이터 타입 정보
  "data_types": {
    "TB_USER.USER_ID": {
      "type": "VARCHAR2",
      "length": 20,
      "nullable": false,
      "sample": "USER001"
    },
    "TB_USER.REG_DT": {
      "type": "DATE",
      "nullable": false,
      "sample": "2024-01-15"
    }
  },
  
  // LLM이 생성한 테스트 케이스 (제약조건 준수)
  "test_cases": [
    {
      "description": "Normal user query with date filter",
      "parameters": {
        "userId": "USER001",         // 20자 이내 (제약조건 준수)
        "startDate": "2024-01-01"    // DATE 포맷
      }
    },
    {
      "description": "Recent user query",
      "parameters": {
        "userId": "USER999",
        "startDate": "2024-12-01"
      }
    }
  ]
}
```

**TC 파일의 역할:**
- Validator가 SQL을 실행할 때 바인드 변수 값 제공
- 실제 데이터베이스 검증 (Oracle vs PostgreSQL 결과 비교)
- 여러 테스트 케이스로 다양한 시나리오 검증
- **LLM이 생성한 현실적인 테스트 데이터 사용**

---

**Phase 6: 파일 저장 (Python)**

```xml
<!-- 출력: mappers/my-project/target/UserMapper/selectUser.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" 
  "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.example.UserMapper">
  <select id="selectUser" resultType="User">
    SELECT user_id, user_name, CURRENT_TIMESTAMP AS reg_dt
    FROM tb_user
    WHERE user_id = #{userId}
      AND reg_dt >= #{startDate}::DATE
  </select>
</mapper>
```

```json
// 출력: mappers/my-project/target/UserMapper/selectUser.tc.json
{위의 TC 파일 내용}
```

#### 출력 파일

**변환 후 디렉토리 구조:**
```
mappers/
└── my-project/
    └── target/            # PostgreSQL/MySQL 변환 결과
        └── UserMapper/
            ├── selectUser.xml        # 변환된 Mapper
            ├── selectUser.tc.json    # 테스트 케이스
            ├── insertUser.xml
            ├── insertUser.tc.json
            ├── updateUser.xml
            └── updateUser.tc.json
```

#### LLM이 수행하는 변환 작업

**1. 구문 변환:**

| Oracle | PostgreSQL | MySQL |
|--------|-----------|-------|
| `SYSDATE` | `CURRENT_TIMESTAMP` | `NOW()` |
| `DECODE(col, 'A', 1, 2)` | `CASE WHEN col = 'A' THEN 1 ELSE 2 END` | 동일 |
| `NVL(col, 0)` | `COALESCE(col, 0)` | 동일 |
| `col(+) = val` | `LEFT JOIN` | 동일 |
| `ROWNUM <= 10` | `LIMIT 10` | 동일 |
| `TO_CHAR(date, 'YYYYMMDD')` | `TO_CHAR(date, 'YYYYMMDD')` | `DATE_FORMAT(date, '%Y%m%d')` |
| `SEQ_USER.NEXTVAL` | `NEXTVAL('seq_user')` | `AUTO_INCREMENT` |
| `DUAL` | 제거 | 제거 |

**2. 명시적 타입 캐스팅:**

```sql
-- Oracle (암묵적 타입 변환)
WHERE REG_DT >= #{startDate}
  AND USER_LEVEL + 1 = #{nextLevel}
  AND CLOSE_DATE >= '20240101'

-- PostgreSQL (명시적 타입 캐스팅)
WHERE reg_dt >= #{startDate}::DATE
  AND user_level::INTEGER + 1 = #{nextLevel}::INTEGER
  AND close_date::DATE >= '20240101'::DATE
```

**왜 필요한가?**
- PostgreSQL은 암묵적 타입 변환 제한적
- VARCHAR를 NUMBER로 비교 시 에러
- 명시적 캐스팅으로 에러 방지

**3. 바인드 변수 매핑:**

```python
# LLM이 SQL 문맥과 Dictionary로 바인드 변수 출처 파악
#{userId} → TB_USER.USER_ID (VARCHAR2)
#{startDate} → TB_USER.REG_DT (DATE)
#{status} → TB_USER.STATUS (VARCHAR2)
#{level} → TB_USER.USER_LEVEL (NUMBER)
```

**4. 테스트 케이스 생성:**

LLM이 컬럼 제약조건을 준수하는 현실적인 테스트 데이터 생성:

```python
# 제약조건:
USER_ID: VARCHAR2(20) NOT NULL
REG_DT: DATE NOT NULL
STATUS: VARCHAR2(1) NOT NULL
USER_LEVEL: NUMBER(2) NOT NULL

# LLM 생성 테스트 케이스:
Test Case 1: "Normal active user"
  userId: "USER001"          # 20자 이내
  startDate: "2024-01-01"    # DATE 포맷
  status: "Y"                # 1자
  level: 5                   # NUMBER(2) 범위

Test Case 2: "Inactive user with high level"
  userId: "ADMIN999"
  startDate: "2023-12-31"
  status: "N"
  level: 10

# 잘못된 예 (LLM이 생성하지 않음):
  userId: "VERYLONGUSERNAMEEXCEEDING20CHARS"  # ✗ 길이 초과
  startDate: null                             # ✗ NOT NULL 위반
  status: "ACTIVE"                            # ✗ 1자 초과
  level: 999                                  # ✗ NUMBER(2) 초과
```

#### 변환 예시

**복잡한 Oracle SQL:**
```sql
<select id="selectOrderList" resultType="Order">
  SELECT 
    O.ORDER_ID,
    O.ORDER_DATE,
    NVL(O.TOTAL_AMT, 0) AS TOTAL_AMT,
    DECODE(O.STATUS, 'Y', 'Active', 'Inactive') AS STATUS_NAME,
    U.USER_NAME,
    TO_CHAR(O.CREATE_DT, 'YYYY-MM-DD') AS CREATE_DATE,
    SEQ_ORDER.NEXTVAL AS NEXT_SEQ
  FROM TB_ORDER O, TB_USER U
  WHERE O.USER_ID = U.USER_ID(+)
    AND O.ORDER_DATE >= #{startDate}
    AND O.TOTAL_AMT + #{discount} <= #{maxAmt}
    AND ROWNUM <= #{limit}
  ORDER BY O.ORDER_DATE DESC
</select>
```

**PostgreSQL 변환 결과:**
```sql
<select id="selectOrderList" resultType="Order">
  SELECT 
    o.order_id,
    o.order_date,
    COALESCE(o.total_amt, 0) AS total_amt,
    CASE WHEN o.status = 'Y' THEN 'Active' ELSE 'Inactive' END AS status_name,
    u.user_name,
    TO_CHAR(o.create_dt, 'YYYY-MM-DD') AS create_date,
    NEXTVAL('seq_order') AS next_seq
  FROM tb_order o
  LEFT JOIN tb_user u ON o.user_id = u.user_id
  WHERE o.order_date >= #{startDate}::DATE
    AND o.total_amt::NUMERIC + #{discount}::NUMERIC <= #{maxAmt}::NUMERIC
  ORDER BY o.order_date DESC
  LIMIT #{limit}::INTEGER
</select>
```

**변경 사항:**
1. ✅ `NVL` → `COALESCE`
2. ✅ `DECODE` → `CASE WHEN`
3. ✅ `(+)` → `LEFT JOIN`
4. ✅ `SEQ.NEXTVAL` → `NEXTVAL('seq')`
5. ✅ `ROWNUM` → `LIMIT`
6. ✅ 소문자 변환 (테이블명, 컬럼명)
7. ✅ 타입 캐스팅 (`::DATE`, `::NUMERIC`, `::INTEGER`)

**생성된 TC 파일:**
```json
{
  "file": "selectOrderList.xml",
  "bind_variables": {
    "#{startDate}": "TB_ORDER.ORDER_DATE",
    "#{discount}": "TB_ORDER.TOTAL_AMT",
    "#{maxAmt}": "TB_ORDER.TOTAL_AMT",
    "#{limit}": "ROWNUM"
  },
  "test_cases": [
    {
      "description": "Recent orders with small discount",
      "parameters": {
        "startDate": "2024-01-01",
        "discount": 1000,
        "maxAmt": 50000,
        "limit": 10
      }
    },
    {
      "description": "All-time orders with no discount",
      "parameters": {
        "startDate": "2020-01-01",
        "discount": 0,
        "maxAmt": 999999,
        "limit": 100
      }
    }
  ]
}
```

---

### Step 4: Mapper 병합 (분할한 경우만)

분할된 파일을 다시 하나의 Mapper XML로 병합합니다.

**Claude Code에서 실행:**
```
/merge-mappers my-project
```

**입력:**
```
mappers/
└── my-project/
    └── target/
        └── UserMapper/
            ├── selectUser.xml
            ├── insertUser.xml
            └── ...
```

**출력:**
```
TARGET_WORKSPACE/
└── my-project/
    └── mappers/
        └── UserMapper.xml  (통합된 파일)
```

**병합 로직:**
- resultMap, sql fragment 중복 제거
- SQL ID 순서 정렬
- 네임스페이스 유지

---

### Step 5: Validator 실행 (검증)

변환된 SQL을 실제 DB에서 검증합니다.

**Claude Code에서 실행:**
```
/run-validator my-project
```

**검증 방식:**
1. Oracle Mapper + Oracle DB 실행
2. Target Mapper + Target DB 실행
3. 결과 비교 (구조, 데이터 타입, 샘플 데이터)

**OGNL 라이브러리 포함 (발견된 경우):**
```bash
# Claude Code 밖에서
export CLASSPATH=/path/to/customer-lib.jar:/path/to/another-lib.jar
cd /home/ec2-user/workspace/oma/app
claude

# 그 다음
/run-validator my-project
```

**검증 리포트:**
```
output/
├── validation-report.json      # 상세 검증 결과
├── validation.log              # 실행 로그
└── validation-performance.json # 성능 비교
```

**리포트 구조:**
```json
{
  "summary": {
    "total": 150,
    "passed": 145,
    "failed": 5,
    "success_rate": "96.67%",
    "execution_time": "45.2s"
  },
  "failures": [
    {
      "mapper": "UserMapper",
      "sql_id": "selectUserList",
      "error": "Column type mismatch: reg_dt (Oracle: DATE, PG: TIMESTAMP)",
      "oracle_result": {...},
      "target_result": {...}
    }
  ]
}
```

**실패한 SQL 재변환:**
```bash
# validation-report.json에서 실패한 파일 추출
jq -r '.failures[].file_path' output/validation-report.json | \
  while read file; do
    # Claude Code에서
    /convert-sql "$file"
  done

# 재검증
/run-validator my-project
```

---

## Extension과 OGNL 이해하기

### Extension 변수란?

**Extension 변수는 고객사 프레임워크가 제공하는 특수 바인드 변수입니다.**

#### 왜 존재하는가?

고객사는 공통 기능(페이징, 세션 관리, 로깅 등)을 프레임워크로 표준화합니다. 이런 프레임워크는 MyBatis Mapper에 특수한 바인드 변수를 제공하여 개발자가 반복 코드를 작성하지 않도록 합니다.

**일반 바인드 변수 vs Extension 변수:**

| 구분 | 일반 바인드 변수 | Extension 변수 |
|------|----------------|---------------|
| **값 제공** | Java Controller/Service 코드 | 프레임워크 (자동) |
| **예시** | `#{userId}`, `#{startDate}` | `#{GRIDPAGING_START}`, `#{FRAMEWORK_SESSION_ID}` |
| **목적** | 비즈니스 데이터 전달 | 공통 기능 (페이징, 세션, 로깅) |
| **개발자 작업** | 명시적으로 값 설정 | 프레임워크가 자동 설정 |

**구체적 예시 - GRIDPAGING:**

```xml
<!-- Extension 변수 사용 (고객 프레임워크) -->
<select id="selectUserList" resultType="User">
  #{GRIDPAGING_ROWNUMTYPE_TOP}
    SELECT USER_ID, USER_NAME, REG_DT
    FROM TB_USER
    WHERE STATUS = #{status}
  #{GRIDPAGING_ROWNUMTYPE_BOTTOM}
</select>
```

**런타임 시 프레임워크가 자동 치환:**

```sql
-- Oracle 실행 시
SELECT GRID_PAGING.*, 1 AS PAGING_CURRENT, 100 AS PAGING_LIMIT FROM (
  SELECT USER_ID, USER_NAME, REG_DT
  FROM TB_USER
  WHERE STATUS = ?
) GRID_PAGING WHERE ROWNUM <= 100

-- PostgreSQL 실행 시
SELECT GRID_PAGING.*, 1 AS PAGING_CURRENT, 100 AS PAGING_LIMIT FROM (
  SELECT USER_ID, USER_NAME, REG_DT
  FROM TB_USER
  WHERE STATUS = ?
) GRID_PAGING LIMIT 100 OFFSET 0
```

**왜 Extension이 마이그레이션에 중요한가?**

1. **TC 파일 검증 필요**: Extension 변수는 TC(Test Case) 파일에서 실제 값으로 치환되어야 Validator 실행 가능
2. **프레임워크 종속성**: Oracle용 Extension과 PostgreSQL용 Extension이 다를 수 있음
3. **문서화 필요**: Extension 변수 목록과 치환 규칙을 파악해야 마이그레이션 성공

#### OMA의 Extension 처리 방식

**1. 자동 감지 (verify-env):**
```bash
/verify-env  # Extension 변수 자동 스캔
```

출력:
```
-------------------------------------------
10. Extension Variable Detection
-------------------------------------------
✓ Extension scan completed
  → Found 3 Extension variables
  → Configuration: extensions/extension.json
```

**2. 수동 검토 필수:**
```bash
# 스캔 결과 확인
cat extensions/extension.json

{
  "enabled": true,
  "variables": {
    "GRIDPAGING_ROWNUMTYPE_TOP": {},     // ✅ 진짜 Extension
    "GRIDPAGING_ROWNUMTYPE_BOTTOM": {},  // ✅ 진짜 Extension
    "USER_STATUS": {},                   // ❌ 오분류 (일반 컬럼)
    "FRAMEWORK_SESSION_USER": {}         // ✅ 진짜 Extension
  }
}
```

**3. 오분류 제거 및 값 입력:**
```bash
vi extensions/extension.json

{
  "enabled": true,
  "variables": {
    "GRIDPAGING_ROWNUMTYPE_TOP": {
      "oracle": "SELECT GRID_PAGING.*, 1 AS PAGING_CURRENT, 100 AS PAGING_LIMIT FROM (",
      "postgres": "SELECT GRID_PAGING.*, 1 AS PAGING_CURRENT, 100 AS PAGING_LIMIT FROM ("
    },
    "GRIDPAGING_ROWNUMTYPE_BOTTOM": {
      "oracle": ") GRID_PAGING WHERE ROWNUM <= 100",
      "postgres": ") GRID_PAGING LIMIT 100 OFFSET 0"
    },
    "FRAMEWORK_SESSION_USER": {
      "oracle": "SYS_CONTEXT('USERENV', 'SESSION_USER')",
      "postgres": "current_user"
    }
    // USER_STATUS 삭제됨 (일반 바인드 변수)
  }
}
```

**4. 주의사항:**
- Extension 변수는 **TC 파일에서만 치환**
- **변환된 Mapper XML은 수정하지 않음** (`#{GRIDPAGING_START}` 그대로 유지)
- TC 파일 실행 시 프레임워크가 런타임에 치환

#### Extension 탐지 기준 (Heuristic)

**자동 탐지 로직 (`tools/scan_extension_variables.py`):**

```python
is_extension = (
    var.isupper() and '_' in var           # 대문자 + 언더스코어
    or 'GRIDPAGING' in var.upper()         # 하드코딩 키워드
    or 'FRAMEWORK' in var.upper()
    or 'PAGING' in var.upper()
)
```

**문제점: 100% 정확하지 않음**
- `#{USER_ID}` (일반 컬럼) → Extension으로 오분류 가능
- `#{CUSTOM_FW_VAR}` (실제 Extension) → 키워드 없으면 누락

**해결: 고객 협의 필수**

프로젝트 시작 전 고객과 협의:
1. Extension 변수 목록 확인
2. 네이밍 컨벤션 파악 (GRIDPAGING_*, EGOVFRAME_* 등)
3. `tools/scan_extension_variables.py` 키워드 수정:

```python
# Line 63-65 수정
is_extension = (
    var.isupper() and '_' in var
    or 'GRIDPAGING' in var.upper()
    or 'EGOVFRAME' in var.upper()    # 전자정부프레임워크 추가
    or 'CUSTOM_FW' in var.upper()    # 고객 프레임워크 추가
)
```

---

### OGNL 표현식이란?

**OGNL(Object-Graph Navigation Language)은 MyBatis에서 Java 정적 메서드를 호출하는 표현식입니다.**

#### 왜 사용하는가?

복잡한 데이터 변환이나 유틸리티 로직을 SQL에서 직접 호출하기 위해 사용합니다.

**OGNL 표현식 예시:**

```xml
<select id="selectUsers" resultType="User">
  SELECT USER_ID, USER_NAME
  FROM TB_USER
  WHERE 1=1
    <if test="@com.util.StringUtil@isEmpty(userName)">
      AND USER_NAME IS NOT NULL
    </if>
    AND REG_DT >= @com.util.DateUtil@getStartOfMonth()
    AND STATUS = @com.constant.UserStatus@ACTIVE.getValue()
</select>
```

**해석:**
- `@com.util.StringUtil@isEmpty(userName)`: StringUtil 클래스의 isEmpty 정적 메서드 호출
- `@com.util.DateUtil@getStartOfMonth()`: 이번 달 1일 반환
- `@com.constant.UserStatus@ACTIVE.getValue()`: Enum 상수 접근

#### 왜 마이그레이션에 문제가 되는가?

**1. 자동 변환 불가능:**
- OGNL은 고객 Java 코드에 의존
- LLM이 코드 없이 변환 불가능
- 예: `isEmpty()`의 실제 구현을 모름

**2. 라이브러리 종속성:**
- Validator 실행 시 고객 JAR 파일 필요
- CLASSPATH에 등록해야 메서드 호출 가능

**3. 마이그레이션 전략:**
- **옵션 1**: OGNL 그대로 유지 (PostgreSQL에서도 동일 Java 라이브러리 사용)
- **옵션 2**: OGNL → SQL 함수로 변환 (수동 작업)
- **옵션 3**: OGNL → Application 레이어로 이동 (리팩토링)

#### OMA의 OGNL 처리 방식

**1. 자동 감지 (verify-env):**
```bash
/verify-env  # OGNL 표현식 자동 스캔
```

출력:
```
-------------------------------------------
11. OGNL Expression Detection
-------------------------------------------
✓ OGNL implementation guide generated
  → Found OGNL expressions requiring implementation
  → Implementation guide: docs/OGNL_IMPLEMENTATION_GUIDE.md
```

**2. 가이드 문서 확인:**
```bash
cat docs/OGNL_IMPLEMENTATION_GUIDE.md

# OGNL Implementation Guide

## Summary
Found 15 OGNL expressions in 8 mapper files.

## Classes Detected
1. com.util.StringUtil
   - isEmpty(String): boolean
   - Used in: UserMapper.xml, OrderMapper.xml (5 times)

2. com.util.DateUtil
   - getStartOfMonth(): Date
   - getCurrentDate(): String
   - Used in: ReportMapper.xml (3 times)

3. com.constant.UserStatus
   - ACTIVE.getValue(): String
   - Used in: UserMapper.xml (2 times)

## Action Required
1. Request customer Java library (.jar files)
2. Add to CLASSPATH when running Validator
3. Verify OGNL methods work in target DB environment
```

**3. 고객으로부터 JAR 파일 제공받기:**
```bash
# 고객이 제공하는 JAR 파일
customer-util-1.0.jar
customer-constants-2.1.jar
```

**4. Validator 실행 시 CLASSPATH 등록:**
```bash
# Claude Code 밖에서
export CLASSPATH=/path/to/customer-util-1.0.jar:/path/to/customer-constants-2.1.jar
cd /home/ec2-user/workspace/oma/app
claude

# Claude Code 안에서
/run-validator my-project
```

**5. Validator가 OGNL 메서드 호출 테스트:**
- Oracle Mapper 실행 시: OGNL 메서드 호출
- Target Mapper 실행 시: 동일 OGNL 메서드 호출
- 결과 비교: 양쪽 모두 정상 작동 확인

#### OMA는 OGNL을 변환하지 않음

**중요:**
- OMA는 OGNL 표현식을 **스캔만** 수행
- 자동 변환하지 않음
- 고객 Java 라이브러리를 **그대로 사용**
- PostgreSQL/MySQL 환경에서도 **동일한 JAR 파일 필요**

**이유:**
1. OGNL 로직은 고객 비즈니스 로직 (자동 변환 불가)
2. 메서드 구현을 알 수 없음
3. 고객이 이미 검증한 코드 재사용이 안전

**만약 OGNL을 제거하고 싶다면:**
- 수동으로 SQL 함수 또는 Application 코드로 변환
- OMA 범위 밖 (고객 개발팀 작업)

---

## 고급 기능

### Type Cast Error 자동 수정

```bash
# Claude Code에서 실행
/fix-type-errors my-project

# 내부 동작:
# 1. validation-report.json 분석
# 2. Type cast 에러 자동 수정 (::VARCHAR, CAST())
# 3. 재변환
```

### 부분 재변환

```bash
# 실패한 Mapper만 재변환
jq -r '.failures[].mapper' output/validation-report.json | sort -u | \
  while read mapper; do
    find mappers/my-project/oracle/${mapper} -name "*.xml" | \
      while read file; do
        # Claude Code에서
        /convert-sql "$file"
      done
  done
```

---

## 문제 해결

### 환경 변수가 로드되지 않음

**증상**: "Missing ORACLE_HOST" 에러

**해결:**
```bash
# 1. oma.properties 확인
cat ../env/oma.properties

# 2. 수동 로드 테스트
source tools/load_oma_env.sh
echo $ORACLE_HOST

# 3. 권한 확인
chmod +x tools/load_oma_env.sh
```

### verify-env 실패

**증상**: "✗ Oracle database connection failed"

**해결:**
```bash
# 1. Oracle 연결 직접 테스트
sqlplus ${ORACLE_USER}/${ORACLE_PASSWORD}@//${ORACLE_HOST}:${ORACLE_PORT}/${ORACLE_SID}

# 2. 스키마 확인
SELECT username FROM all_users WHERE username = 'WMSON';

# 3. VPN 연결 확인 (온프레미스 Oracle)
```

### SQL 변환이 너무 느림

**증상**: 1개 파일 변환에 30초 이상

**해결:**
```bash
# 1. MAX_WORKERS 증가 (병렬 처리)
vi ../env/oma.properties
MAX_WORKERS=10

# 2. 더 빠른 모델 사용
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-6

# 3. LLM 연결 확인
aws bedrock-runtime invoke-model \
  --model-id global.anthropic.claude-opus-4-7 \
  --body '{"anthropic_version":"bedrock-2023-05-31","messages":[{"role":"user","content":"test"}],"max_tokens":10}' \
  /tmp/response.json
```

### Validator 실행 실패

**증상**: "java.lang.ClassNotFoundException: oracle.jdbc.OracleDriver"

**해결:**
```bash
# 1. ORACLE_HOME 확인
echo $ORACLE_HOME
ls $ORACLE_HOME/jdbc/lib/ojdbc8.jar

# 2. Validator 재빌드
cd tools/validator
mvn clean package

# 3. JAR 파일 확인
ls -lh target/mapper-validator-1.0.0.jar
```

### Extension 변수 오분류

**증상**: 일반 컬럼명이 Extension으로 분류됨

**해결:**
```bash
# 1. extension.json 확인
cat extensions/extension.json

# 2. 오분류된 변수 삭제
vi extensions/extension.json

# 예시: USER_ID는 일반 컬럼명 → 삭제
{
  "enabled": true,
  "variables": {
    "GRIDPAGING_START": {...},  // ✅ Extension
    "USER_ID": {...}             // ❌ 삭제 (일반 바인드 변수)
  }
}
```

---

## 참고

- **환경 설정**: [env/README_KR.md](../env/README_KR.md)
- **스키마 변환**: [schema/README_KR.md](../schema/README_KR.md)
- **Claude Code Skills**: [.claude/skills/README.md](.claude/skills/README.md)

---

**작성일**: 2026-06-18  
**OMA Version**: 2.0
