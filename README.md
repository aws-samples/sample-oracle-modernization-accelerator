# OMA (Oracle Modernization Accelerator)

OMA is a comprehensive sample code collection that automates the conversion of Oracle DBMS schemas and application SQL to PostgreSQL. This toolkit is specifically designed to work effectively with Amazon Q Developer, providing automated migration capabilities for enterprise database modernization projects.

## Overview

OMA provides automated scripts and tools for:
- **Database Schema Migration**: Converting Oracle DDL to PostgreSQL-compatible schemas
- **Application SQL Conversion**: Transforming Oracle SQL in MyBatis mapper files to PostgreSQL syntax
- **Validation and Testing**: Ensuring conversion accuracy and compatibility
- **Amazon Q Developer Integration**: Leveraging AI-powered code assistance for complex migration scenarios

The project includes jpetstore-6 as an example application to demonstrate the migration process.

## Project Structure

```
OMA                                              OMA 폴더
├── setup/                                       AWS Environment 설정 (사전 필수 구성요소)
│   ├── deploy-omabox.sh                         - OMA Box 배포 스크립트
│   ├── cleanup-omabox.sh                        - OMA Box 정리 스크립트
│   ├── omabox-cloudformation.yaml               - CloudFormation 템플릿
│   └── README.md                                - 사전 요구사항 가이드
├── 01.Database/                                 데이터베이스 스키마 변환
│   ├── Tools/                                   - 데이터베이스 변환 프로그램
│   │   └── DB01.asct.py                         - 메인 데이터베이스 변환 프로그램
│   ├── Prompts/                                 - 데이터베이스 변환 프롬프트
│   ├── Assessments/                             - 분석 결과 및 추출된 데이터
│   │   ├── extracted_csv/                       - 추출된 CSV 파일
│   │   ├── oracle/                              - Oracle 스키마 파일
│   │   └── incompatible.lst                     - 호환되지 않는 객체 목록
│   ├── Transform/                               - 변환된 PostgreSQL 스키마
│   ├── Logs/                                    - 변환 로그 디렉토리
│   └── README.md                                - 데이터베이스 변환 가이드
├── 02.Application/                              애플리케이션 SQL 변환
│   └── jpetstore-6/                             - 예제 애플리케이션 프로젝트
│       ├── Assessments/                         - 기초 분석 JNDI 정보와 분석 대상 리스트
│       │   ├── JNDI.csv                         - JNDI 설정 정보
│       │   ├── Mapperlist.csv                   - Mapper 파일 목록
│       │   ├── MapperAndJndi.csv                - Mapper와 JNDI 매핑 정보
│       │   └── logs/                            - 분석 로그
│       ├── Tools/                               - Q Prompt와 변환 프로그램
│       │   ├── AP01.GenMapperList.txt           - Mapper 목록 생성 프롬프트
│       │   ├── AP02.GenSQLTransformTarget.py    - SQL 변환 대상 생성 프로그램
│       │   ├── AP03.SQLTransformTarget.py       - SQL 변환 메인 프로그램
│       │   ├── AP03.xmlExtractor.py             - XML 추출 프로그램
│       │   ├── AP03.xmlMerger.py                - XML 병합 프로그램
│       │   └── AP03.TransformValidation.py      - 변환 검증 프로그램
│       └── Transform/                           - 애플리케이션 SQL 변환 결과
│           ├── SQLTransformTarget.csv           - 변환 대상 Mapper 리스트
│           ├── SQLTransformTargetFailure.csv    - 재실행 대상 Mapper 리스트
│           ├── xmllintResult.csv                - XML 검증 결과
│           ├── logs/                            - 변환 로그 디렉토리
│           └── mapper/                          - 최종 변환 결과 Mapper 파일
├── 03.Test/                                     Unit 테스트 수행 결과 및 도구
│   ├── program/                                 - Unit Test 프로그램
│   │   ├── TST01.initOMA.sh                     - 테스트 초기화 스크립트
│   │   ├── TST02.GetDDL.sh                      - DDL 추출 스크립트
│   │   ├── TST03.FindXMLFiles.py                - XML 파일 검색 프로그램
│   │   ├── TST04.XMLToSQL.py                    - XML을 SQL로 변환
│   │   ├── TST05.GetDictionary.py               - 데이터 딕셔너리 추출
│   │   ├── TST06.BindSampler.py                 - 바인드 변수 샘플러
│   │   ├── TST07.BindMapper.py                  - 바인드 매퍼
│   │   ├── TST08.SaveSQLToDB.py                 - SQL을 DB에 저장
│   │   ├── TST09.ExecuteAndCompareSQL.py        - SQL 실행 및 비교
│   │   └── TST10.AnalyzeResult.py               - 결과 분석
│   ├── prompt/                                  - 테스트 관련 프롬프트
│   ├── work/                                    - 임시 저장 파일
│   └── README.md                                - 테스트 가이드
├── 99.Templates/                                OMA 프로젝트 수행을 위한 분석 도구 템플릿
│   ├── AP01.GenMapperList.txt                   - Mapper 목록 생성 템플릿
│   ├── AP02.GenSQLTransformTarget.py            - SQL 변환 대상 생성 템플릿
│   ├── AP03.SQLTransformTarget.py               - SQL 변환 메인 템플릿
│   ├── AP03.xmlExtractor.py                     - XML 추출 템플릿
│   ├── AP03.xmlMerger.py                        - XML 병합 템플릿
│   ├── AP03.TransformValidation.py              - 변환 검증 템플릿
│   ├── DB01.asct.py                             - 데이터베이스 변환 템플릿
│   └── TST*.py                                  - 테스트 프로그램 템플릿
├── SampleApp/                                   샘플 애플리케이션
│   └── jpetstore-6/                             - JPetStore 6 예제 애플리케이션
│       ├── src/main/resources/                  - MyBatis mapper files with Oracle SQL
│       ├── pom.xml                              - Maven 프로젝트 설정
│       ├── docker-compose.yaml                  - Docker 구성
│       └── ...                                  - 표준 Maven 프로젝트 구조
├── initOMA.sh                                   OMA 애플리케이션 변환 프로그램 메인 수행 스크립트
├── pre-requisites.sh                            사전 요구사항 설정 스크립트
├── OMA.properties                               프로젝트 설정 파일 (환경 변수)
├── README.md                                    프로젝트 메인 가이드
└── THIRD-PARTY-LICENSES.md                      서드파티 라이선스 정보
```

## Conversion Process

The conversion process follows these steps:

1. **Generate list of mapper files to be converted**
   - Identifies all Oracle SQL mapper files (_orcl.xml) in the extract directory

2. **Analyze SQL for Oracle-specific features**
   - Examines each file for Oracle-specific SQL syntax
   - Documents findings in sql_analysis.txt

3. **Perform Oracle to PostgreSQL conversion**
   - Converts Oracle SQL to PostgreSQL SQL
   - Handles special cases like PL/SQL blocks, pagination, sequences
   - Preserves MyBatis dynamic SQL features

4. **Validate converted XML files**
   - Uses xmllint to verify XML syntax correctness
   - Ensures all files are well-formed

## Key Conversion Rules

The following Oracle to PostgreSQL conversions are applied:

- ROWNUM → LIMIT/OFFSET
- NVL() → COALESCE()
- DECODE() → CASE WHEN
- SYSDATE → CURRENT_TIMESTAMP
- FROM DUAL → Remove DUAL
- Sequence.NEXTVAL → nextval('sequence')
- LISTAGG → STRING_AGG
- CONNECT BY → WITH RECURSIVE
- Date functions:
  - MONTHS_BETWEEN → AGE/EXTRACT
  - ADD_MONTHS → + INTERVAL
  - LAST_DAY → DATE_TRUNC with INTERVAL

## PL/SQL Block Handling

PL/SQL blocks are converted to PostgreSQL's procedural language (PL/pgSQL):

- Oracle's DECLARE → PostgreSQL's DO $$ DECLARE
- Variable declarations without initialization
- Maintained %TYPE references
- Added $$ LANGUAGE plpgsql; at the end

## Usage

To run the OMA conversion process:

1. **Setup**: Execute `./setup/deploy-omabox.sh` to set up the AWS environment (Aurora, DMS, Amazon Q on EC2)
2. **Setup**: Configure your project settings in `OMA.Properties`
3. **Initialize**: Execute `./initOMA.sh` and select your project to start the conversion process
4. **Review**: Check the conversion results in the respective Transform directories
5. **Validate**: Use the generated test scripts to verify conversion accuracy

The jpetstore-6 example application demonstrates the complete migration workflow from Oracle to PostgreSQL.

## Notes

- All conversions preserve MyBatis dynamic SQL features
- Variable bindings (#{...} and ${...}) are maintained exactly as in the original
- Comments are added to document the conversion changes

## License

This project uses third-party software components. For detailed license information, see [THIRD-PARTY-LICENSES.md](THIRD-PARTY-LICENSES.md).
