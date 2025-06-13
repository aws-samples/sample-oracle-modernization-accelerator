# Oracle Migration Assistant (OMA) 프롬프트 보강 사항

## 전체적인 프로그램 흐름 설명

OMA는 Oracle에서 PostgreSQL로의 마이그레이션을 지원하는 10개의 프로그램으로 구성된 도구 세트입니다. 각 프로그램은 다음과 같은 순서로 실행되며 서로 연결됩니다:

1. **DB00.initOMA.sh**: 환경 설정 및 필요한 도구 설치
   - Oracle Instant Client, PostgreSQL Client 설치
   - 환경 변수 설정
   - 작업 디렉토리 생성

2. **DB01.GetDDL.sh**: Oracle과 PostgreSQL에서 테이블 DDL을 추출하여 통합
   - 출력: $OMA_ASSESSMENT/tab_ddl/*.sql 파일

3. **DB02.FindXMLFiles.py**: 디렉토리에서 XML 파일을 찾아 목록 생성
   - 입력: XML 파일이 있는 디렉토리 경로
   - 출력: orcl_xml.lst 또는 pg_xml.lst 파일

4. **DB03.XMLToSQL.py**: XML 매퍼 파일에서 SQL 구문을 추출하여 개별 파일로 저장
   - 입력: DB02에서 생성한 XML 목록 파일
   - 출력: orcl_sql_extract/*.sql 또는 pg_sql_extract/*.sql 파일

5. **DB04.GetDictionary.py**: 데이터베이스 메타데이터와 샘플 데이터를 추출하여 딕셔너리 생성
   - 출력: all_dictionary.json 파일

6. **DB06.BindSampler.py**: SQL 파일에서 바인드 변수를 식별하고 적절한 샘플 값 할당
   - 입력: DB03에서 생성한 SQL 파일, DB04에서 생성한 딕셔너리
   - 출력: sampler/*.json 파일

7. **DB07.BindMapper.py**: SQL 파일의 바인드 변수를 실제 샘플 값으로 대체
   - 입력: DB03에서 생성한 SQL 파일, DB06에서 생성한 샘플 값
   - 출력: orcl_sql_done/*.sql 또는 pg_sql_done/*.sql 파일

8. **DB08.SaveSQLToDB.py**: SQL 파일을 PostgreSQL의 sqllist 테이블에 저장
   - 입력: DB07에서 생성한 SQL 파일
   - 출력: PostgreSQL의 sqllist 테이블에 데이터 저장

9. **DB09.ExecuteAndCompareSQL.py**: Oracle과 PostgreSQL에서 SQL을 실행하고 결과 비교
   - 입력: DB08에서 저장한 sqllist 테이블 데이터
   - 출력: sqllist 테이블 업데이트 (결과 저장)

10. **DB10.AnalyzeResult.py**: Oracle과 PostgreSQL 쿼리 결과의 차이 분석 및 보고서 생성
    - 입력: DB09에서 업데이트한 sqllist 테이블 데이터
    - 출력: difference_analysis.html 보고서

## 환경 설정 및 의존성 정보

### 필수 환경 변수
```bash
# Oracle 환경 변수
export ORACLE_HOME=/path/to/oracle/home
export ORACLE_SID=orcl
export ORACLE_ADM_USER=system
export ORACLE_ADM_PASSWORD=password
export ORACLE_SVC_USER=service_user
export ORACLE_SVC_PASSWORD=password

# PostgreSQL 환경 변수
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=postgres
export PGUSER=postgres
export PGPASSWORD=password

# OMA 환경 변수
export OMA_HOME=/path/to/oma
export OMA_ASSESSMENT=$OMA_HOME/Assessment
export OMA_TEST=$OMA_HOME/Test
export OMA_TRANSFORM=$OMA_HOME/Transform
```

### 필수 패키지 및 라이브러리
- Python 3.6 이상
- Oracle Instant Client 19 이상
- PostgreSQL Client 12 이상
- Python 패키지:
  - psycopg2 또는 psycopg2-binary: PostgreSQL 연결
  - cx_Oracle: Oracle 연결
  - lxml: XML 파싱
  - pandas: 데이터 처리
  - matplotlib: 차트 생성
  - jinja2: HTML 템플릿 처리

### 설치 방법
```bash
# 필요한 시스템 패키지 설치
sudo apt-get update
sudo apt-get install -y python3 python3-pip postgresql-client unzip jq

# Python 패키지 설치
pip3 install psycopg2-binary cx_Oracle lxml pandas matplotlib jinja2

# 초기화 스크립트 실행
chmod +x DB00.initOMA.sh
./DB00.initOMA.sh
```

## 테스트 케이스 및 검증 방법

각 프로그램은 다음과 같이 테스트할 수 있습니다:

1. **DB01.GetDDL.sh**: 
   ```bash
   ./DB01.GetDDL.sh -v
   # 결과: $OMA_ASSESSMENT/tab_ddl 디렉토리에 테이블별 SQL 파일 생성
   # 검증: 파일 내용에 Oracle DDL과 PostgreSQL DDL이 모두 포함되어 있는지 확인
   ```

2. **DB02.FindXMLFiles.py**:
   ```bash
   python3 DB02.FindXMLFiles.py /path/to/xml/files --orcl
   # 결과: orcl_xml.lst 파일 생성
   # 검증: 파일에 모든 XML 파일 경로가 올바르게 나열되어 있는지 확인
   ```

3. **DB03.XMLToSQL.py**:
   ```bash
   python3 DB03.XMLToSQL.py orcl_xml.lst
   # 결과: orcl_sql_extract 디렉토리에 SQL 파일 생성
   # 검증: SQL 파일에 XML에서 추출한 SQL 구문이 올바르게 포함되어 있는지 확인
   ```

4. **DB04.GetDictionary.py**:
   ```bash
   python3 DB04.GetDictionary.py
   # 결과: all_dictionary.json 파일 생성
   # 검증: JSON 파일에 모든 테이블과 컬럼 정보가 포함되어 있는지 확인
   ```

5. **DB06.BindSampler.py**:
   ```bash
   python3 DB06.BindSampler.py
   # 결과: sampler 디렉토리에 JSON 파일 생성
   # 검증: JSON 파일에 바인드 변수와 적절한 샘플 값이 매핑되어 있는지 확인
   ```

6. **DB07.BindMapper.py**:
   ```bash
   python3 DB07.BindMapper.py
   # 결과: orcl_sql_done 및 pg_sql_done 디렉토리에 SQL 파일 생성
   # 검증: SQL 파일에서 바인드 변수가 실제 값으로 대체되었는지 확인
   ```

7. **DB08.SaveSQLToDB.py**:
   ```bash
   python3 DB08.SaveSQLToDB.py
   # 결과: PostgreSQL의 sqllist 테이블에 데이터 저장
   # 검증: sqllist 테이블에 모든 SQL 문이 올바르게 저장되었는지 확인
   ```

8. **DB09.ExecuteAndCompareSQL.py**:
   ```bash
   python3 DB09.ExecuteAndCompareSQL.py -t S
   # 결과: sqllist 테이블 업데이트 (결과 저장)
   # 검증: sqllist 테이블의 orcl_result, pg_result, same 컬럼이 업데이트되었는지 확인
   ```

9. **DB10.AnalyzeResult.py**:
   ```bash
   python3 DB10.AnalyzeResult.py
   # 결과: difference_analysis.html 보고서 생성
   # 검증: HTML 보고서에 차이 분석 결과가 올바르게 표시되는지 확인
   ```

## 오류 처리 및 복구 방법

### 데이터베이스 연결 오류
- 연결 정보(호스트, 포트, 사용자 이름, 비밀번호)가 올바른지 확인
- 데이터베이스 서버가 실행 중인지 확인
- 네트워크 연결 상태 확인
- 재시도 메커니즘 구현 (최대 3회 재시도, 지수 백오프 적용)

### 파일 접근 오류
- 파일 및 디렉토리 권한 확인
- 필요한 디렉토리 자동 생성
- 디스크 공간 부족 확인
- 임시 파일 사용 및 안전한 파일 쓰기 구현

### XML 파싱 오류
- 다양한 인코딩 시도 (UTF-8, CP949 등)
- 손상된 XML 복구 시도 (recover 옵션 사용)
- 네임스페이스 처리
- 대체 파싱 방법 구현 (정규식 기반)

### 메모리 부족 오류
- 배치 처리 크기 동적 조정
- 메모리 사용량 모니터링
- 임시 결과를 디스크에 저장
- 가비지 컬렉션 명시적 호출

## 성능 최적화 팁

1. **대용량 XML 파일 처리**:
   - 스트리밍 파서 사용 (SAX 또는 iterparse)
   - 배치 크기를 시스템 메모리에 맞게 조정
   - 불필요한 XML 요소 조기 제거

2. **병렬 처리 구현**:
   - ThreadPoolExecutor 또는 ProcessPoolExecutor 사용
   - CPU 코어 수에 맞게 작업자 수 조정
   - 공유 리소스에 대한 락 메커니즘 구현
   - 작업 분배 최적화 (작업 크기 균등화)

3. **데이터베이스 최적화**:
   - 배치 삽입/업데이트 사용
   - 트랜잭션 크기 최적화
   - 인덱스 활용
   - 연결 풀링 구현

4. **I/O 최적화**:
   - 버퍼링 I/O 사용
   - 임시 결과를 메모리에 유지
   - 불필요한 파일 읽기/쓰기 최소화
   - 압축 사용 고려

## 보안 고려사항

1. **데이터베이스 자격 증명 관리**:
   - 환경 변수 사용 (코드에 하드코딩 금지)
   - AWS Secrets Manager 또는 유사한 서비스 활용
   - 최소 권한 원칙 적용

2. **SQL 인젝션 방지**:
   - 파라미터화된 쿼리 사용
   - 사용자 입력 검증
   - ORM 또는 안전한 SQL 빌더 사용

3. **파일 시스템 보안**:
   - 적절한 파일 권한 설정
   - 임시 파일 안전하게 처리
   - 경로 순회 공격 방지

4. **로그 보안**:
   - 민감한 정보 로깅 제한
   - 로그 파일 접근 제한
   - 로그 순환 구현

## 문서화 및 주석 가이드라인

1. **함수 및 클래스 문서화**:
   ```python
   def function_name(param1, param2):
       """
       함수 설명을 여기에 작성합니다.
       
       Args:
           param1 (type): 파라미터 설명
           param2 (type): 파라미터 설명
           
       Returns:
           type: 반환값 설명
           
       Raises:
           ExceptionType: 예외 발생 조건 설명
       """
       # 함수 구현
   ```

2. **인라인 주석**:
   - 복잡한 로직에 대한 설명
   - 왜 특정 방식으로 구현했는지 설명
   - 알고리즘의 시간/공간 복잡도 명시

3. **변수 및 상수 명명**:
   - 설명적인 이름 사용
   - 상수는 대문자와 언더스코어 사용 (예: MAX_BATCH_SIZE)
   - 변수는 소문자와 언더스코어 사용 (예: user_name)
   - 클래스는 CamelCase 사용 (예: DatabaseConnection)

4. **코드 구조화**:
   - 관련 기능을 함수로 그룹화
   - 클래스를 사용하여 상태와 동작 캡슐화
   - 모듈을 논리적 단위로 분리
   - 일관된 들여쓰기 및 포맷팅 사용
