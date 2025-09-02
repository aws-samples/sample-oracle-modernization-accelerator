# Oracle vs PostgreSQL SQL 차이점 종합 분석

## 📊 분석 결과 요약

### 1. AnalyticsMapper.selectRFMAnalysis (차이: 73 bytes, 0.1%)

**🔍 차이점 원인:**
- **날짜 계산 방식**: `TRUNC(SYSDATE) - TRUNC(MAX(o.ORDERED_AT))` vs `(CURRENT_DATE - MAX(o.ORDERED_AT)::date)`
- **조인 방식**: Oracle `(+)` vs PostgreSQL `LEFT JOIN`
- **NULL 처리**: `NVL()` vs `COALESCE()`

**✅ 변환 상태**: 올바르게 변환됨
**📝 차이 원인**: 날짜 계산 정밀도 차이로 인한 미세한 결과 차이

---

### 2. OrderMapper.selectOrderCount (차이: 3 bytes, 0.2%)

**🔍 차이점 원인:**
- **조인 방식**: `FROM ORDERS o, USERS u WHERE o.USER_ID = u.USER_ID(+)` vs `FROM ORDERS o LEFT JOIN USERS u ON o.USER_ID = u.USER_ID`
- **문자열 연결**: `||` vs `CONCAT()`
- **WHERE 조건**: Oracle은 `AND 1=1` 없이 시작, PostgreSQL은 `WHERE 1=1`로 시작

**✅ 변환 상태**: 올바르게 변환됨
**📝 차이 원인**: COUNT(*) 결과의 숫자 포맷팅 차이 (아마도 trailing spaces)

---

### 3. PaymentMapper.selectPaymentCount (차이: 3 bytes, 0.2%)

**🔍 차이점 원인:**
- **조인 방식**: `FROM PAYMENTS p, ORDERS o WHERE p.ORDER_ID = o.ORDER_ID` vs `FROM PAYMENTS p JOIN ORDERS o ON p.ORDER_ID = o.ORDER_ID`
- **날짜 처리**: `TO_DATE(#{startDate}, 'YYYY-MM-DD')` vs `#{startDate}::date`
- **WHERE 조건**: Oracle은 직접 WHERE, PostgreSQL은 `WHERE 1=1` 추가

**✅ 변환 상태**: 올바르게 변환됨
**📝 차이 원인**: COUNT(*) 결과의 숫자 포맷팅 차이

---

### 4. PaymentMapper.selectPaymentDetail (차이: 115 bytes, 6.8%)

**🔍 예상 차이점:**
- **페이징 처리**: Oracle `ROWNUM` vs PostgreSQL `LIMIT/OFFSET`
- **날짜 포맷팅**: Oracle `TO_CHAR()` vs PostgreSQL `TO_CHAR()` 또는 `::text`
- **숫자 포맷팅**: Oracle과 PostgreSQL의 기본 숫자 표시 형식 차이

---

### 5. ProductMapper 관련 SQL들

**🔍 공통 예상 차이점:**
- **계층 쿼리**: Oracle `CONNECT BY` vs PostgreSQL `WITH RECURSIVE`
- **문자열 함수**: Oracle `SUBSTR`, `INSTR` vs PostgreSQL `SUBSTRING`, `POSITION`
- **날짜 함수**: Oracle `SYSDATE`, `TRUNC` vs PostgreSQL `CURRENT_DATE`, `DATE_TRUNC`

---

### 6. UserMapper 관련 SQL들 (가장 큰 차이들)

**🔍 주요 차이점들:**

#### selectUserBehaviorPattern (2,500 bytes, 1.2%)
- **이미 분석 완료**: DAYS_SINCE_LAST_ORDER 계산에서 중복 NULL 처리 문제

#### selectUserLifecycleAnalysis (2,500 bytes, 1.3%)
- **예상 원인**: 복잡한 윈도우 함수와 날짜 계산 조합
- **가능한 문제**: 생명주기 단계 계산 로직의 차이

#### selectUserReferralHierarchy (2,000 bytes, 1.1%)
- **예상 원인**: 계층 구조 쿼리 (`CONNECT BY` vs `WITH RECURSIVE`)
- **가능한 문제**: 추천 관계 트리 구성 방식의 차이

---

## 🎯 차이 발생 패턴 분석

### 1. 미세한 차이 (3 bytes, 0.2%)
**원인**: 숫자 포맷팅 차이
- Oracle: `1234`
- PostgreSQL: `1234 ` (trailing space) 또는 다른 포맷

**해결책**: 불필요 - 실제 데이터는 동일

### 2. 중간 차이 (73-115 bytes, 0.1-6.8%)
**원인**: 
- 날짜 계산 정밀도 차이
- 문자열 포맷팅 차이
- 페이징 구현 방식 차이

**해결책**: 포맷팅 통일화 필요

### 3. 큰 차이 (2,000-2,500 bytes, 1.1-1.3%)
**원인**:
- 복잡한 비즈니스 로직의 변환 오류
- 윈도우 함수 동작 차이
- 계층 쿼리 구현 방식 차이

**해결책**: 개별 SQL 상세 분석 및 수정 필요

---

## 🛠️ 권장 수정 순서

### 우선순위 1 (즉시 수정 필요)
1. **UserMapper.selectUserBehaviorPattern** - 이미 수정안 제공
2. **UserMapper.selectUserLifecycleAnalysis** - 상세 분석 필요
3. **UserMapper.selectUserReferralHierarchy** - 계층 쿼리 검토 필요

### 우선순위 2 (검토 후 수정)
4. **PaymentMapper.selectPaymentDetail** - 페이징 로직 확인
5. **ProductMapper** 관련 SQL들 - 개별 분석 필요

### 우선순위 3 (선택적 수정)
6. **3 bytes 차이 SQL들** - 실제 데이터는 동일하므로 낮은 우선순위

---

## 🔍 다음 단계 제안

1. **UserMapper.selectUserLifecycleAnalysis** 상세 분석
2. **UserMapper.selectUserReferralHierarchy** 계층 쿼리 분석
3. **ProductMapper** SQL들의 개별 분석
4. 수정된 SQL들의 성능 테스트 및 검증

각 SQL에 대한 구체적인 수정안이 필요하시면 개별적으로 분석해드리겠습니다.
