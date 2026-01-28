# Strands Framework Guide

## Overview

**Strands Agents SDK**는 AWS에서 만든 오픈소스 AI agent framework입니다. MCP를 네이티브로 지원하며, 최소한의 코드로 AI agent를 구축할 수 있습니다.

## 현재 구조 (Hybrid Approach)

### Strands Agent (Recommended)
- **파일**: `ora_to_pg_strands_agent.py`
- **방식**: Python CSV parsing + Strands SDK conversion
- **코드**: ~150 lines
- **장점**: 
  - 정확한 객체 필터링 (Python)
  - AI 기반 변환 (Strands)
  - Medium/Complex만 처리
- **성능**: 17개 객체, ~3분

### Original Agent (Fallback)
- **파일**: `ora_to_pg_sc_agent.py`
- **방식**: 직접 MCP 클라이언트 호출
- **코드**: ~300 lines, 명시적 워크플로우
- **장점**: 완전한 제어, 예측 가능
- **단점**: 순차 처리, 하드코딩된 로직

## Hybrid Approach 장점

### 1. Python이 CSV 파싱
```python
def parse_csv_for_medium_complex(s3_path):
    # CSV에서 Medium/Complex 객체만 추출
    objects = []
    for row in csv_reader:
        if row['Estimated complexity'] in ['Complex', 'Medium']:
            objects.append(row)
    return objects
```

### 2. Strands가 변환 수행
```python
# 필터링된 객체 리스트를 agent에 전달
agent = Agent(
    tools=mcp_tools,
    system_prompt=f"Convert these {len(objects)} pre-filtered objects..."
)
result = agent.invoke_async("Convert the objects")
```

### 3. 최고의 조합
- ✅ 정확한 필터링 (Python)
- ✅ 유연한 변환 (AI)
- ✅ Simple 객체 제외
- ✅ 예측 가능한 결과

## MCP 호환성

### Working Configuration
```
MCP SDK: 1.11.0
Strands SDK: 1.23.0
Transport: SSE
Spring AI: WebFlux + SSE
```

### Key Points
- MCP 1.11.0이 Strands 1.23.0과 호환
- SSE transport 사용
- Spring WebFlux 필요 (webmvc 아님)
with oma_sc_client:
    agent = Agent(tools=oma_sc_client.list_tools_sync())
```

### 4. 병렬 처리 가능
- LLM이 독립적인 작업을 식별하면 자동으로 병렬 실행
- 명시적 asyncio 코드 불필요

## 설치

```bash
cd /workshop/oma-sc-agent

# setup.sh가 자동으로 Strands SDK 포함 모든 의존성 설치
./setup.sh
```

또는 수동 설치:
```bash
pip install strands-agents
pip install -r requirements.txt
```

## 사용법

### Strands 버전 실행
```bash
python3.11 ora_to_pg_strands_agent.py s3://bucket/project.zip
```

### Original 버전 실행 (비교용)
```bash
python3.11 ora_to_pg_sc_agent.py.original s3://bucket/project.zip
```

## 비교

| 측면 | Original | Strands |
|------|----------|---------|
| **코드 라인** | ~300 | ~100 |
| **워크플로우** | 하드코딩 | AI 결정 |
| **병렬 처리** | 수동 asyncio | 자동 (LLM 판단) |
| **에러 처리** | try/catch | AI 재시도 |
| **커스터마이징** | Python 코드 수정 | 프롬프트 수정 |
| **예측 가능성** | 높음 | 중간 |
| **유연성** | 낮음 | 높음 |
| **디버깅** | Python 디버거 | LLM 추론 로그 |

## Strands 작동 방식

### 1. Agent 생성
```python
agent = Agent(
    tools=mcp_tools,  # MCP 도구들
    system_prompt="..."  # 작업 설명
)
```

### 2. 실행
```python
result = agent("Convert schema from s3://...")
```

### 3. Agent Loop
1. LLM이 프롬프트 분석
2. 필요한 도구 선택
3. 도구 실행
4. 결과 분석
5. 다음 단계 결정
6. 완료될 때까지 반복

## 실제 예시

### Original 방식
```python
# 1. Analyze
result = await call_tool(session, "analyze_dms_sc_project", {"arg0": s3_path})
data = json.loads(result)

# 2. Parse CSV
objects = []
for csv_file in csv_files:
    with open(csv_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['complexity'] in ['Complex', 'Medium']:
                objects.append(row)

# 3. Process each
for obj in objects:
    try:
        ddl = await call_tool(session, "get_offline_ddl", {...})
        converted = await call_tool(session, "convert_ddl_to_pg", {...})
        save(converted)
    except Exception as e:
        handle_error(e)
```

### Strands 방식
```python
agent = Agent(
    tools=mcp_tools,
    system_prompt="""
    1. Analyze DMS SC project
    2. Find Complex/Medium objects
    3. For each: extract DDL, convert, save
    4. Generate report
    """
)

result = agent("Convert from s3://bucket/project.zip")
# LLM이 위 단계들을 자동으로 실행
```

## 장단점 분석

### Strands 장점
1. **개발 속도**: 코드 1/3로 동일 기능
2. **유연성**: 프롬프트만 수정하면 동작 변경
3. **지능형 에러 처리**: LLM이 문제 분석 후 대안 시도
4. **자연어 인터페이스**: 비개발자도 이해 가능한 프롬프트

### Strands 단점
1. **예측 불가능**: LLM 판단에 따라 다르게 동작
2. **디버깅 어려움**: 왜 그렇게 결정했는지 추적 어려움
3. **비용**: LLM API 호출 비용
4. **의존성**: LLM 서비스 필요 (Bedrock, OpenAI 등)

## 권장 사용 시나리오

### Strands 사용
- 복잡한 의사결정이 필요한 경우
- 워크플로우가 자주 변경되는 경우
- 빠른 프로토타이핑
- 다양한 예외 상황 처리 필요

### Original 사용
- 정확한 제어가 필요한 경우
- 예측 가능한 동작 필수
- LLM 비용 절감 필요
- 프로덕션 안정성 우선

## 다음 단계

1. **테스트**: 두 버전으로 동일 데이터 변환 후 비교
2. **성능 측정**: 실행 시간, 성공률 비교
3. **비용 분석**: LLM API 호출 비용 계산
4. **결정**: 프로젝트 요구사항에 맞는 버전 선택

## 참고 자료

- [Strands Agents 공식 문서](https://strandsagents.com/)
- [MCP 프로토콜](https://modelcontextprotocol.io/)
- [Strands GitHub](https://github.com/strands-agents/sdk-python)

---

**Created**: 2026-01-28  
**Backup**: `/workshop/backup/strands-migration-20260128-044037/`  
**Status**: Strands 버전 생성 완료, 테스트 필요
