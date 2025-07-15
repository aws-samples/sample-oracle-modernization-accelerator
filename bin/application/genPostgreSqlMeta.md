# PostgreSQL 메타데이터 추출 프롬프트 (테이블 + 뷰)

Reference: Apply environment information from $APP_TOOLS_FOLDER/environment_context.md

## 요청사항
PostgreSQL 데이터베이스에서 비즈니스 스키마의 테이블과 뷰의 컬럼 메타데이터를 추출하여 `/tmp/oma_metadata.txt` 파일을 생성해주세요.

## 접속 정보
- 데이터베이스 접속 정보는 환경변수에 설정되어 있습니다
- `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` 사용

## 실행할 명령어
```bash
psql -c "
SELECT 
    table_schema,
    table_name,
    column_name,
    data_type
FROM information_schema.columns 
WHERE table_schema NOT IN (
    'information_schema', 
    'pg_catalog', 
    'pg_toast',
    'aws_commons',
    'aws_oracle_context',
    'aws_oracle_data', 
    'aws_oracle_ext',
    'public'
)
ORDER BY table_schema, table_name, ordinal_position;
" > /tmp/oma_metadata.txt
```

## 추출할 컬럼 정보
- `table_schema` - 스키마명
- `table_name` - 테이블/뷰명
- `column_name` - 컬럼명
- `data_type` - 데이터 타입

## 포함 대상
- **테이블 (Tables)** - 실제 데이터가 저장되는 테이블
- **뷰 (Views)** - 가상 테이블 (SELECT 쿼리 기반)
- **머티리얼라이즈드 뷰 (Materialized Views)** - 물리적으로 저장된 뷰

## 제외 스키마 (완전 제외)
- `information_schema` - PostgreSQL 정보 스키마
- `pg_catalog` - PostgreSQL 시스템 카탈로그  
- `pg_toast` - PostgreSQL TOAST 테이블
- `aws_commons` - AWS 공통 함수
- `aws_oracle_context` - AWS Oracle 컨텍스트
- `aws_oracle_data` - AWS Oracle 데이터
- `aws_oracle_ext` - AWS Oracle 확장
- `public` - 퍼블릭 스키마 (시스템/확장 테이블)

## 포함 스키마 (비즈니스 스키마만)
- `itsm_app` - ITSM 애플리케이션
- `itsm_inf` - ITSM 인프라
- `itsm_own` - ITSM 소유자
- `mro_app` - MRO 애플리케이션
- `oas_own` - OAS 소유자

## 출력 파일
- 파일명: `/tmp/oma_metadata.txt`
- 형식: PostgreSQL 테이블 형식 (헤더 포함)
- 정렬: 스키마명, 테이블/뷰명, 컬럼 순서대로
- 컬럼: 4개 컬럼 (스키마, 테이블/뷰명, 컬럼명, 데이터타입)

## 검증 명령어
```bash
# 파일 생성 확인
ls -la /tmp/oma_metadata.txt

# 총 라인 수 확인
wc -l /tmp/oma_metadata.txt

# 첫 10줄 확인
head -10 /tmp/oma_metadata.txt

# 스키마별 테이블/뷰 개수 확인
grep -v "^-" /tmp/oma_metadata.txt | grep -v "table_schema" | awk '{print $1}' | sort | uniq -c
```

## 예상 출력 형식
```
 table_schema |        table_name        | column_name |     data_type     
--------------+--------------------------+-------------+-------------------
 itsm_app     | some_table               | id          | integer
 itsm_app     | some_view                | name        | character varying
 itsm_inf     | another_table            | created_at  | timestamp
 ...
```

## 참고사항
- `information_schema.columns`는 테이블과 뷰를 모두 포함합니다
- 뷰의 컬럼도 테이블 컬럼과 동일하게 메타데이터가 추출됩니다
- 머티리얼라이즈드 뷰도 자동으로 포함됩니다

이 프롬프트에 따라 비즈니스 스키마의 모든 테이블과 뷰의 메타데이터를 `/tmp/oma_metadata.txt` 파일로 추출해주세요.
