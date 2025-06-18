# Oracle Migration Assistant (OMA)

이 프로젝트는 Oracle 데이터베이스에서 PostgreSQL로의 마이그레이션을 지원하는 도구 모음입니다.

## 프로그램 개요 및 실행 순서

1. **DB00.initOMA.sh**: 환경 설정 및 필요한 도구 설치
2. **DB01.GetDDL.sh**: Oracle과 PostgreSQL에서 테이블 DDL을 추출하여 통합
3. **DB02.FindXMLFiles.py**: 디렉토리에서 XML 파일을 찾아 목록 생성
4. **DB03.XMLToSQL.py**: XML 매퍼 파일에서 SQL 구문을 추출하여 개별 파일로 저장
5. **DB04.GetDictionary.py**: 데이터베이스 메타데이터와 샘플 데이터를 추출하여 딕셔너리 생성
6. **DB06.BindSampler.py**: SQL 파일에서 바인드 변수를 식별하고 적절한 샘플 값 할당
7. **DB07.BindMapper.py**: SQL 파일의 바인드 변수를 실제 샘플 값으로 대체
8. **DB08.SaveSQLToDB.py**: SQL 파일을 PostgreSQL의 sqllist 테이블에 저장
9. **DB09.ExecuteAndCompareSQL.py**: Oracle과 PostgreSQL에서 SQL을 실행하고 결과 비교
10. **DB10.AnalyzeResult.py**: Oracle과 PostgreSQL 쿼리 결과의 차이 분석 및 보고서 생성

## 데이터 흐름

```
DB01.GetDDL.sh → tab_ddl/*.sql (테이블 DDL 파일)
DB02.FindXMLFiles.py → *_xml.lst (XML 파일 목록)
DB03.XMLToSQL.py → *_sql_extract/*.sql (추출된 SQL 파일)
DB04.GetDictionary.py → all_dictionary.json (데이터베이스 딕셔너리)
DB06.BindSampler.py → sampler/*.json (바인드 변수 샘플 값)
DB07.BindMapper.py → *_sql_done/*.sql (바인드 변수가 대체된 SQL 파일)
DB08.SaveSQLToDB.py → PostgreSQL sqllist 테이블
DB09.ExecuteAndCompareSQL.py → sqllist 테이블 업데이트 (결과 저장)
DB10.AnalyzeResult.py → difference_analysis.html (결과 분석 보고서)
```

## 환경 설정

### 필수 환경 변수(예시)

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

### 필수 패키지 및 의존성

- Python 3.6 이상
- Oracle Instant Client
- PostgreSQL Client
- Python 패키지:
  - psycopg2
  - cx_Oracle
  - lxml
  - pandas
  - matplotlib
  - jinja2

## 설치 방법

```bash
# 필요한 시스템 패키지 설치
sudo dnf update
sudo dnf install -y python3 python3-pip postgresql-client unzip jq

# Python 패키지 설치
pip3 install psycopg2-binary cx_Oracle lxml pandas matplotlib jinja2

# 초기화 스크립트 실행
chmod +x DB00.initOMA.sh
./DB00.initOMA.sh
```

## 테스트 및 검증

각 프로그램은 다음과 같이 테스트할 수 있습니다:

1. **DB01.GetDDL.sh**: 
   ```bash
   ./DB01.GetDDL.sh -v
   # 결과: $OMA_ASSESSMENT/tab_ddl 디렉토리에 테이블별 SQL 파일 생성
   ```

2. **DB02.FindXMLFiles.py**:
   ```bash
   python3 DB02.FindXMLFiles.py /path/to/xml/files --orcl
   # 결과: orcl_xml.lst 파일 생성
   ```

3. **DB03.XMLToSQL.py**:
   ```bash
   python3 DB03.XMLToSQL.py orcl_xml.lst
   # 결과: orcl_sql_extract 디렉토리에 SQL 파일 생성
   ```

각 프로그램의 출력을 확인하여 예상대로 작동하는지 검증하세요.

## 오류 처리 및 로깅

모든 프로그램은 다음과 같은 오류 처리 원칙을 따릅니다:

1. 데이터베이스 연결 오류: 연결 정보 확인 및 재시도
2. 파일 접근 오류: 권한 확인 및 디렉토리 생성
3. XML 파싱 오류: 인코딩 변환 및 복구 시도
4. 메모리 부족 오류: 배치 처리 크기 조정

로그는 각 프로그램별로 생성되며, 상세 로깅 옵션을 사용하여 디버깅 정보를 확인할 수 있습니다.

## 보안 고려사항

1. 데이터베이스 자격 증명은 환경 변수로 관리하고, 소스 코드에 직접 포함하지 않습니다.
2. SQL 인젝션 방지를 위해 파라미터화된 쿼리를 사용합니다.
3. 민감한 정보가 포함된 로그 파일은 적절한 권한으로 보호합니다.

## 성능 최적화 팁

1. 대용량 XML 파일 처리 시 배치 크기를 조정하세요.
2. 병렬 처리 옵션을 활용하여 처리 속도를 향상시키세요.
3. 메모리 사용량을 모니터링하고 필요시 배치 크기를 줄이세요.
4. 디스크 I/O를 최소화하기 위해 중간 결과를 메모리에 유지하세요.

## 문서화 및 주석 가이드라인

1. 모든 함수와 클래스에 docstring을 작성하세요.
2. 복잡한 로직에는 인라인 주석을 추가하세요.
3. 주요 변수와 상수에 설명적인 이름을 사용하세요.
4. 코드 변경 시 주석을 업데이트하세요.
