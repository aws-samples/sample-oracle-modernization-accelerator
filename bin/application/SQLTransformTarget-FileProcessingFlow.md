# SQLTransformTarget.py 파일 처리 흐름 가이드

## 📋 개요

SQLTransformTarget.py는 MyBatis XML 파일을 Oracle에서 PostgreSQL로 변환하는 프로그램입니다.
SOURCE_SQL_MAPPER_FOLDER의 XML 파일들을 4단계 파이프라인을 통해 변환하여 TARGET_SQL_MAPPER_FOLDER에 배치합니다.

## 🔄 전체 처리 흐름

### 입력 → 출력 경로
```
SOURCE_SQL_MAPPER_FOLDER/com/example/UserMapper.xml
                    ↓
TARGET_SQL_MAPPER_FOLDER/com/example/UserMapper.xml
```

### 중간 작업 폴더 구조
```
logs/mapper/com/example/UserMapper/
├── origin/          # 1단계: 원본 파일 복사
├── extract/         # 2단계: XML 요소 분해
├── transform/       # 3단계: SQL 변환
└── merge/          # 4단계: XML 병합
```

## 📁 단계별 상세 처리

### 1️⃣ **파일 경로 분석 및 준비**

#### 입력 파일 예시
```
SOURCE_SQL_MAPPER_FOLDER: /app/source/mapper/
입력 파일: /app/source/mapper/com/example/dao/UserMapper.xml
```

#### 상대 경로 추출
```python
xml_parent_path = "/app/source/mapper/com/example/dao"
source_mapper_path = "/app/source/mapper"
relative_path = "com/example/dao"  # 추출된 상대 경로
```

#### 작업 폴더 구성
```
logs/mapper/com/example/dao/UserMapper/
├── origin/
├── extract/
├── transform/
└── merge/
```

### 2️⃣ **Origin 단계 - 원본 파일 복사**

#### 처리 내용
- 원본 XML 파일을 작업 폴더의 origin/ 하위에 복사
- 파일명에 origin_suffix(_src) 추가

#### 파일 경로
```
입력: /app/source/mapper/com/example/dao/UserMapper.xml
출력: logs/mapper/com/example/dao/UserMapper/origin/UserMapper_src.xml
```

#### 코드 로직
```python
origin_file_name = f"{xml_stem}{origin_suffix}{xml_path.suffix}"  # UserMapper_src.xml
origin_file_path = os.path.join(origin_folder, origin_file_name)
copy_file(xml_file, origin_file_path, logger, use_sudo)
```

### 3️⃣ **Extract 단계 - XML 요소 분해**

#### 처리 내용
- xmlExtractor.py를 호출하여 XML을 Level1 요소들로 분해
- 각 SQL 요소(select, insert, update, delete)를 개별 파일로 분리

#### 파일 경로
```
입력: logs/mapper/com/example/dao/UserMapper/origin/UserMapper_src.xml
출력: logs/mapper/com/example/dao/UserMapper/extract/
      ├── select_getUserById.xml
      ├── insert_insertUser.xml
      ├── update_updateUser.xml
      └── delete_deleteUser.xml
```

#### 실행 명령
```python
extractor_cmd = [
    "python3", "xmlExtractor.py",
    "--input", origin_file_path,
    "--output", xmlextract_folder,
    f"--log-level={log_level}"
]
```

### 4️⃣ **Transform 단계 - SQL 변환**

#### 처리 내용
- 프롬프트 템플릿을 처리하여 Q Chat용 프롬프트 생성
- Q Chat을 실행하여 Oracle SQL을 PostgreSQL로 변환
- SQLTransformTarget-pg-rules.txt 규칙 파일 사용

#### 파일 경로
```
입력: logs/mapper/com/example/dao/UserMapper/extract/*.xml
출력: logs/mapper/com/example/dao/UserMapper/transform/
      ├── select_getUserById_tgt.xml
      ├── insert_insertUser_tgt.xml
      ├── update_updateUser_tgt.xml
      └── delete_deleteUser_tgt.xml
```

#### 프롬프트 처리
```python
prompt = prompt_template.replace("{MAPPER_SRCL1_DIR}", extract_folder)
prompt = prompt.replace("{MAPPER_TGTL1_DIR}", xmltransform_folder)
prompt = prompt.replace("{ORIGIN_SUFFIX}", origin_suffix)
prompt = prompt.replace("{TRANSFORM_SUFFIX}", transform_suffix)
```

#### Q Chat 실행
```bash
q chat --trust-all-tools --no-interactive < UserMapper.prompt > UserMapper.log
```

### 5️⃣ **Merge 단계 - XML 병합**

#### 처리 내용
- xmlMerger.py를 호출하여 변환된 Level1 요소들을 하나의 XML로 병합
- 완전한 MyBatis XML 파일 재구성

#### 파일 경로
```
입력: logs/mapper/com/example/dao/UserMapper/transform/*.xml
출력: logs/mapper/com/example/dao/UserMapper/merge/UserMapper_tgt.xml
```

#### 실행 명령
```python
merger_cmd = [
    "python3", "xmlMerger.py",
    "--input", xmltransform_folder,
    "--output", xmlmerge_file,
    f"--log-level={log_level}"
]
```

### 6️⃣ **최종 배치 - TARGET_SQL_MAPPER_FOLDER 복사**

#### 처리 내용
- 병합된 최종 XML 파일을 TARGET_SQL_MAPPER_FOLDER에 복사
- 원본과 동일한 폴더 구조 유지
- 파일명에서 suffix 제거

#### 파일 경로
```
입력: logs/mapper/com/example/dao/UserMapper/merge/UserMapper_tgt.xml
출력: /app/target/mapper/com/example/dao/UserMapper.xml
```

#### 폴더 구조 유지
```
SOURCE_SQL_MAPPER_FOLDER/          TARGET_SQL_MAPPER_FOLDER/
├── com/                          ├── com/
│   └── example/                  │   └── example/
│       └── dao/                  │       └── dao/
│           └── UserMapper.xml    │           └── UserMapper.xml
└── org/                          └── org/
    └── sample/                       └── sample/
        └── ProductMapper.xml             └── ProductMapper.xml
```

## 🔧 환경 변수 및 설정

### 필수 환경 변수
```bash
SOURCE_SQL_MAPPER_FOLDER=/app/source/mapper     # 원본 XML 파일 위치
TARGET_SQL_MAPPER_FOLDER=/app/target/mapper     # 변환된 XML 파일 위치
TARGET_DBMS_TYPE=postgres                       # 대상 DBMS (postgres/mysql)
APP_TOOLS_FOLDER=/app/tools                     # 변환 규칙 파일 위치
```

### 변환 규칙 파일
```
TARGET_DBMS_TYPE=postgres → SQLTransformTarget-pg-rules.txt
TARGET_DBMS_TYPE=mysql   → SQLTransformTarget-mysql-rules.txt
```

## 📊 처리 결과

### 성공 시
- TARGET_SQL_MAPPER_FOLDER에 변환된 XML 파일 생성
- 폴더 구조 완전 보존
- PostgreSQL 호환 SQL로 변환 완료

### 검증 과정
1. **XML 유효성 검사**: xmllint로 XML 구문 검증
2. **변환 결과 검증**: TransformValidation.py 자동 실행
3. **실패 리포팅**: 실패한 파일들을 CSV로 리포트

## 🚨 주의사항

### 파일명 규칙
- **Origin 단계**: `파일명_src.xml`
- **Transform 단계**: `파일명_tgt.xml`  
- **최종 결과**: `파일명.xml` (suffix 제거)

### 폴더 구조
- SOURCE_SQL_MAPPER_FOLDER의 하위 폴더 구조가 TARGET_SQL_MAPPER_FOLDER에 완전히 복제됨
- 중간 작업 폴더는 logs/mapper/ 하위에 생성됨

### 멀티스레드 처리
- 여러 XML 파일을 동시에 처리 가능
- THREAD_COUNT 환경변수로 스레드 수 조정

## 🔍 트러블슈팅

### 자주 발생하는 문제
1. **권한 문제**: `--use-sudo` 옵션 사용
2. **프롬프트 파일 없음**: TARGET_DBMS_TYPE에 맞는 규칙 파일 확인
3. **폴더 구조 문제**: SOURCE_SQL_MAPPER_FOLDER 경로 확인

### 로그 확인
```
logs/
├── qlogs/          # Q Chat 실행 로그
├── prompts/        # 생성된 프롬프트 파일들
├── pylogs/         # Python 실행 로그
└── mapper/         # 중간 작업 파일들
```
