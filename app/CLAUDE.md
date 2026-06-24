# Claude Code 작업 규칙

## 절대 금지 사항

### sed 명령어 사용 금지
- **NEVER** use `sed` command for any file modification
- sed는 어떤 경우에도 사용 금지
- 파일 수정은 반드시 Read/Edit/Write 도구 사용
- sed 사용 시도 시 즉시 중단하고 다른 방법 사용

### 정규식(Regex) 사용 금지
- **NEVER** use regex pattern matching for parsing SQL or XML content
- 정규식으로 테이블명, 컬럼명, 패턴 추출 금지
- SQL/XML 파싱은 LLM이 컨텍스트를 이해하고 판단하도록 설계
- 정규식은 취약하고 예외 케이스 처리 불가능
- **대신 LLM에게 판단 요청**: "Extract table names from this SQL" 같은 프롬프트 사용

## 프로젝트 규칙

### Extension 시스템
- Extension은 TC 파일의 바인드 변수 값을 제공하는 용도
- **타겟 매퍼(PostgreSQL SQL)는 절대 수정 금지**
- GRIDPAGING 변수는 Extension을 통해 TC 파일에서만 치환
- 매퍼 XML의 `#{GRIDPAGING_...}` 구문은 그대로 유지

### 파일 수정 원칙
- 타겟 매퍼 파일은 변환 과정의 최종 결과물로 직접 수정 불가
- 수정이 필요하면 변환 로직을 수정하고 재변환
