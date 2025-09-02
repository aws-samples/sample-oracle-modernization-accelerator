# 🔍 3 Bytes 차이의 정확한 원인 분석

## 📋 분석 대상 SQL
- `OrderMapper.selectOrderCount`
- `PaymentMapper.selectPaymentCount` 
- `ProductMapper.selectProductCount`
- `UserMapper.selectUserCount`

## 🎯 차이점 발견

### Oracle 결과 (소스)
```json
"results":[{"count(*)":0}]
```

### PostgreSQL 결과 (타겟)
```json
"results":[{"count":0}]
```

## 📊 정확한 차이점

**컬럼명 차이:**
- **Oracle**: `count(*)` (8글자)
- **PostgreSQL**: `count` (5글자)
- **차이**: 8 - 5 = **3 bytes**

## 🔍 원인 분석

### 1. MyBatis ResultType 처리 차이
- **Oracle**: `COUNT(*)`를 그대로 컬럼명으로 사용
- **PostgreSQL**: `COUNT(*)`를 `count`로 정규화

### 2. JDBC 드라이버 동작 차이
- **Oracle JDBC**: 함수명을 그대로 컬럼명으로 반환
- **PostgreSQL JDBC**: 집계 함수를 간소화된 이름으로 반환

### 3. SQL 표준 준수 차이
- **PostgreSQL**: SQL 표준에 더 엄격하게 준수
- **Oracle**: 더 유연한 컬럼명 처리

## ✅ 결론

**이 차이는 실제 데이터 차이가 아닙니다:**
- 실제 COUNT 값: 둘 다 `0`으로 동일
- 차이점: JSON 응답에서 컬럼명 표현 방식만 다름
- 비즈니스 로직에 영향: **없음**

## 🎯 권장사항

### 1. 무시해도 되는 차이
- 실제 데이터는 완전히 동일
- 애플리케이션 동작에 영향 없음
- 수정 우선순위: **최하위**

### 2. 원한다면 수정 방법
SQL에 명시적 별칭 추가:
```sql
-- 현재
SELECT COUNT(*)

-- 수정안
SELECT COUNT(*) as total_count
```

### 3. 테스트 프레임워크 개선안
- 컬럼명 정규화 로직 추가
- 실제 데이터 값만 비교하는 옵션 제공

## 📈 영향도 평가
- **데이터 정확성**: ✅ 문제없음
- **비즈니스 로직**: ✅ 문제없음  
- **API 응답**: ⚠️ 컬럼명만 다름
- **수정 필요성**: ❌ 불필요

**결론: 이 3 bytes 차이는 실제 문제가 아니며, 무시해도 됩니다.**
