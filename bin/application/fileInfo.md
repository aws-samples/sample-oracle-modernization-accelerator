# File Information

## genDepartedXmls.sh

### 목적 (Purpose)
MyBatis XML Mapper 파일을 개별 Level1 요소로 분리하여 생성하는 배치 스크립트입니다.
- 하나의 XML 파일에 포함된 여러 SQL 요소(select, insert, update, delete, sql 등)를 개별 XML 파일로 분리
- 각 요소는 완전한 XML 구조를 유지하며 독립적인 파일로 저장
- 대량의 XML 파일을 효율적으로 처리하며 진행 상황을 실시간으로 표시

### 주요 기능
- **Level1 요소 분리**: MyBatis XML의 select, insert, update, delete, sql 등 요소를 개별 파일로 추출
- **완전한 XML 구조 유지**: XML 헤더, DOCTYPE, namespace 등을 포함한 완전한 XML 파일 생성
- **배치 처리**: 지정된 폴더의 모든 XML 파일을 자동으로 처리
- **파일 복사 기능**: 외부 폴더의 XML 파일을 내부 구조로 복사
- **진행률 표시**: 실시간 진행률과 상세한 처리 결과 제공
- **환경변수 지원**: 유연한 경로 설정을 위한 환경변수 활용

### 사용법 (Usage)

#### 기본 문법
```bash
./genDepartedXmls.sh [타입]
```

#### 지원되는 타입과 동작

##### 1. source
```bash
./genDepartedXmls.sh source
```
**처리 흐름**: `SOURCE_SQL_MAPPER_FOLDER` → `origin` → `extract`

**상세 동작**:
1. `SOURCE_SQL_MAPPER_FOLDER`의 모든 XML 파일을 검색
2. 각 파일을 `{파일명}_src.xml`로 이름 변경
3. `APP_LOGS_FOLDER/mapper/{경로}/{파일명}/origin/` 폴더에 복사
4. 복사된 파일들을 xmlExtractor.py로 처리하여 개별 요소로 분리
5. 분리된 요소들을 `extract` 폴더에 저장

**예시**:
```
SOURCE_SQL_MAPPER_FOLDER/com/UserDao.xml
↓ 복사 및 이름 변경
APP_LOGS_FOLDER/mapper/com/UserDao/origin/UserDao_src.xml
↓ 분리 처리
APP_LOGS_FOLDER/mapper/com/UserDao/extract/
├── UserDao_src-01-select-userDao.getUser.xml
└── UserDao_src-02-insert-userDao.insertUser.xml
```

##### 2. target
```bash
./genDepartedXmls.sh target
```
**처리 흐름**: `TARGET_SQL_MAPPER_FOLDER` → `merge` → `transform`

**상세 동작**:
1. `TARGET_SQL_MAPPER_FOLDER`의 모든 XML 파일을 검색
2. 각 파일을 `{파일명}_tgt.xml`로 이름 변경
3. `APP_LOGS_FOLDER/mapper/{경로}/{파일명}/merge/` 폴더에 복사
4. 복사된 파일들을 xmlExtractor.py로 처리하여 개별 요소로 분리
5. 분리된 요소들을 `transform` 폴더에 저장

**예시**:
```
TARGET_SQL_MAPPER_FOLDER/itsm/csr/CsrMainDao.xml
↓ 복사 및 이름 변경
APP_LOGS_FOLDER/mapper/itsm/csr/CsrMainDao/merge/CsrMainDao_tgt.xml
↓ 분리 처리
APP_LOGS_FOLDER/mapper/itsm/csr/CsrMainDao/transform/
├── CsrMainDao_tgt-01-select-csrMainDao.getMainInfo.xml
└── CsrMainDao_tgt-02-update-csrMainDao.updateStatus.xml
```

##### 3. origin
```bash
./genDepartedXmls.sh origin
```
**처리 흐름**: `origin` → `extract`

**상세 동작**:
1. `APP_LOGS_FOLDER/mapper/*/origin/` 폴더의 모든 XML 파일을 검색
2. 각 파일을 xmlExtractor.py로 처리하여 개별 요소로 분리
3. 분리된 요소들을 해당하는 `extract` 폴더에 저장

**예시**:
```
APP_LOGS_FOLDER/mapper/com/LoginDao/origin/LoginDao_src.xml
↓ 분리 처리
APP_LOGS_FOLDER/mapper/com/LoginDao/extract/
├── LoginDao_src-01-select-loginDao.checkLogin.xml
└── LoginDao_src-02-update-loginDao.updateLastLogin.xml
```

##### 4. merge
```bash
./genDepartedXmls.sh merge
```
**처리 흐름**: `merge` → `transform`

**상세 동작**:
1. `APP_LOGS_FOLDER/mapper/*/merge/` 폴더의 모든 XML 파일을 검색
2. 각 파일을 xmlExtractor.py로 처리하여 개별 요소로 분리
3. 분리된 요소들을 해당하는 `transform` 폴더에 저장

**예시**:
```
APP_LOGS_FOLDER/mapper/mro/sys/SysAuthDao/merge/SysAuthDao_tgt.xml
↓ 분리 처리
APP_LOGS_FOLDER/mapper/mro/sys/SysAuthDao/transform/
├── SysAuthDao_tgt-01-select-sysAuthDao.getAuthInfo.xml
└── SysAuthDao_tgt-02-update-sysAuthDao.updateAuth.xml
```

### 환경변수 (Environment Variables)

#### 필수 환경변수
- `APP_LOGS_FOLDER`: 애플리케이션 로그 폴더의 기본 경로

#### 타입별 필수 환경변수
- `SOURCE_SQL_MAPPER_FOLDER`: `source` 타입 사용 시 필요
- `TARGET_SQL_MAPPER_FOLDER`: `target` 타입 사용 시 필요

#### 환경변수 설정 예시
```bash
export APP_LOGS_FOLDER="/home/ec2-user/workspace/sample-oracle-modernization-accelerator/your-project/logs/application"
export SOURCE_SQL_MAPPER_FOLDER="/external/source/mappers"
export TARGET_SQL_MAPPER_FOLDER="/external/target/mappers"
```

### 출력 파일 형식
생성되는 개별 XML 파일은 다음 형식을 따릅니다:
```
{원본파일명}-{순번}-{요소타입}-{요소ID}.xml
```

#### 예시
- `LoginDao_src-01-select-loginDao.retrieveUserInfo.xml`
- `LoginDao_src-02-insert-loginDao.insertUser.xml`
- `ComCodeDao_tgt-03-update-comCodeDao.updateCode.xml`

### 폴더 구조
각 타입별로 생성되는 폴더 구조:

#### source/target 타입 (복사 후 분리)
```
APP_LOGS_FOLDER/mapper/
└── {경로}/
    └── {파일명}/
        ├── origin/ 또는 merge/
        │   └── {파일명}_src.xml 또는 {파일명}_tgt.xml
        └── extract/ 또는 transform/
            ├── {파일명}_src-01-select-{id}.xml
            ├── {파일명}_src-02-insert-{id}.xml
            └── ...
```

#### origin/merge 타입 (기존 파일 분리)
```
APP_LOGS_FOLDER/mapper/
└── {경로}/
    ├── origin/ 또는 merge/
    │   └── {기존파일}.xml
    └── extract/ 또는 transform/
        ├── {기존파일}-01-select-{id}.xml
        ├── {기존파일}-02-insert-{id}.xml
        └── ...
```

### 처리 결과
스크립트 실행 후 다음 정보가 제공됩니다:
- 처리 타입 및 입출력 폴더 정보
- 복사 작업 수행 여부 및 결과 (source/target의 경우)
- 총 처리된 파일 수
- 성공/실패 통계
- 생성된 개별 XML 파일 수
- 각 파일별 상세 처리 결과
- 실행 시간

### 의존성 (Dependencies)
- **xmlExtractor.py**: XML 파일에서 Level1 요소를 추출하는 Python 스크립트
- **Python 3**: xmlExtractor.py 실행을 위해 필요
- **find, sed, grep, cp, mkdir**: 파일 검색, 텍스트 처리, 복사, 디렉토리 생성을 위한 Unix 유틸리티

### 오류 처리
- 잘못된 인자 개수 또는 타입 검증
- 필수 환경변수 존재 여부 확인
- 파일 복사 중 발생하는 오류 캡처 및 보고
- XML 분리 처리 중 발생하는 오류 캡처 및 보고

### 로그 기능
- 컬러풀한 로그 출력 (INFO, SUCCESS, WARNING, ERROR)
- 실시간 진행률 표시
- 복사 작업 진행 상황 표시 (source/target의 경우)
- 상세한 처리 결과 요약
- 실패한 파일에 대한 상세 오류 정보

---

## xmlExtractor.py

### 목적 (Purpose)
MyBatis XML Mapper 파일에서 Level1 요소를 추출하여 개별 XML 파일로 저장하는 Python 스크립트입니다.

### 주요 기능
- XML 파일 파싱 및 Level1 요소 추출
- 완전한 XML 구조 생성 (헤더, DOCTYPE, namespace 포함)
- 주석 및 중첩된 태그 구조 보존
- 상세 로깅 기능

### 사용법
```bash
python3 xmlExtractor.py -i [입력파일] -o [출력폴더] [옵션]
```

### 옵션
- `-i, --input`: XML 파일 경로 (필수)
- `-o, --output`: 출력 폴더 경로 (필수)
- `-l, --log`: 로그 파일 경로 (선택)
- `-v, --verbose`: 상세 로깅 활성화
- `--log-level`: 로그 레벨 설정 (DEBUG, INFO, WARNING, ERROR, CRITICAL)

---

## run_xml_extractor_enhanced.sh

### 목적 (Purpose)
origin 폴더의 모든 *src.xml 파일들을 처리하여 extract 폴더에 개별 Level1 요소로 분리하는 배치 스크립트입니다.

### 주요 기능
- origin 폴더의 모든 *src.xml 파일 자동 검색
- xmlExtractor.py를 사용한 배치 처리
- 진행률 표시 및 상세 통계 제공
- 컬러풀한 로그 출력

### 사용법
```bash
./run_xml_extractor_enhanced.sh
```

### 처리 대상
- 경로: `APP_LOGS_FOLDER/mapper/*/origin/*src.xml`
- 출력: 해당하는 extract 폴더
