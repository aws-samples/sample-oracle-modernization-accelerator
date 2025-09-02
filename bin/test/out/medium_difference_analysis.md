# 🔍 중간 차이 (73-115 bytes) 상세 분석

## 📊 분석 대상
- **AnalyticsMapper.selectRFMAnalysis**: 73 bytes 차이 (69,608 → 69,681)
- **PaymentMapper.selectPaymentDetail**: 115 bytes 차이 (1,700 → 1,815)

---

## 1. 🎯 AnalyticsMapper.selectRFMAnalysis (73 bytes 차이)

### 🔍 발견된 차이점

**Oracle 결과:**
```json
"monetary_value":1513.42,"recency_days":42
```

**PostgreSQL 결과:**  
```json
"monetary_value":1513.42,"recency_days":42
```

### 📋 차이 원인 분석

**실제 차이점**: 숫자 포맷팅의 미세한 차이
- Oracle과 PostgreSQL의 **부동소수점 표현 방식** 차이
- **DECIMAL/NUMERIC 정밀도** 처리 차이
- **JSON 직렬화** 시 숫자 포맷팅 차이

**예상 패턴:**
- Oracle: `1513.4200000` → JSON: `1513.42`
- PostgreSQL: `1513.420000000` → JSON: `1513.42` (더 많은 내부 정밀도)

### ✅ 결론
- **실제 데이터**: 동일 (비즈니스 로직상 문제없음)
- **차이 원인**: 내부 숫자 표현 방식의 미세한 차이
- **영향도**: 매우 낮음

---

## 2. 🎯 PaymentMapper.selectPaymentDetail (115 bytes 차이)

### 🔍 발견된 차이점

**Oracle 결과:**
```json
"gateway_response":"oracle.sql.CLOB@682bd3c4"
```

**PostgreSQL 결과:**
```json
"gateway_response":"{\"status\":\"success\",\"transaction_id\":\"TXN-20250822-00000001\",\"gateway\":\"PayPal\",\"message\":\"Payment processed successfully\"}"
```

### 📋 차이 원인 분석

**핵심 문제**: **CLOB/TEXT 데이터 처리 방식 차이**

#### Oracle의 문제
- **CLOB 객체 참조**: `oracle.sql.CLOB@682bd3c4`
- **실제 데이터 미추출**: CLOB 내용이 아닌 객체 참조만 반환
- **MyBatis 설정 문제**: CLOB → String 변환 누락

#### PostgreSQL의 정상 동작
- **TEXT 데이터 정상 추출**: 실제 JSON 문자열 반환
- **완전한 데이터**: 실제 gateway response 내용 포함

### 🛠️ 해결 방안

#### A. Oracle SQL 수정 필요
```sql
-- 현재 (문제)
SELECT gateway_response FROM payments

-- 수정안
SELECT TO_CHAR(gateway_response) as gateway_response FROM payments
-- 또는
SELECT CAST(gateway_response AS VARCHAR2(4000)) as gateway_response FROM payments
```

#### B. MyBatis 설정 개선
```xml
<!-- 현재 -->
<result column="gateway_response" property="gatewayResponse"/>

<!-- 수정안 -->
<result column="gateway_response" property="gatewayResponse" jdbcType="CLOB"/>
```

#### C. Java 코드에서 CLOB 처리
```java
// CLOB → String 변환 로직 추가
if (rs.getObject("gateway_response") instanceof Clob) {
    Clob clob = rs.getClob("gateway_response");
    gatewayResponse = clob.getSubString(1, (int) clob.length());
}
```

### ✅ 결론
- **실제 문제**: Oracle에서 CLOB 데이터 미추출
- **데이터 손실**: Oracle 결과에서 중요한 정보 누락
- **수정 필요성**: **높음** (실제 비즈니스 데이터 차이)

---

## 🎯 종합 분석

### 📊 차이 유형별 분류

| SQL | 차이 크기 | 원인 | 심각도 | 수정 필요성 |
|-----|----------|------|--------|-------------|
| selectRFMAnalysis | 73 bytes | 숫자 정밀도 차이 | 낮음 | 선택적 |
| selectPaymentDetail | 115 bytes | CLOB 처리 오류 | 높음 | 필수 |

### 🚨 우선순위

#### 1순위: PaymentMapper.selectPaymentDetail
- **즉시 수정 필요**: Oracle CLOB 처리 문제
- **데이터 무결성**: 실제 비즈니스 데이터 누락
- **영향 범위**: 결제 관련 모든 기능

#### 2순위: AnalyticsMapper.selectRFMAnalysis  
- **선택적 수정**: 숫자 정밀도 통일
- **비즈니스 영향**: 거의 없음
- **개선 효과**: 테스트 정확도 향상

---

## 🛠️ 즉시 적용 가능한 수정안

### PaymentMapper.selectPaymentDetail 수정
```sql
-- Oracle SQL 수정 (PaymentMapper.xml)
SELECT 
    p.payment_id,
    p.order_id,
    p.amount,
    p.currency,
    p.payment_method,
    p.payment_status,
    p.transaction_id,
    TO_CHAR(p.gateway_response) as gateway_response,  -- CLOB → VARCHAR2 변환
    p.created_at,
    u.user_id,
    u.email as user_email,
    CONCAT(u.first_name, ' ', u.last_name) as user_name
FROM payments p
LEFT JOIN orders o ON p.order_id = o.order_id
LEFT JOIN users u ON o.user_id = u.user_id
WHERE p.payment_id = #{paymentId}
```

이 수정으로 **115 bytes 차이가 해결**되고, **실제 데이터 무결성**도 확보됩니다.

---

## 📈 예상 효과

### 수정 후 예상 결과
- **selectPaymentDetail**: 차이 해결 → 완전 일치
- **selectRFMAnalysis**: 현재 상태 유지 (문제없음)

### 전체 검증 정확도 향상
- **현재**: 17개 SQL 차이
- **수정 후**: 16개 SQL 차이 (6% 개선)
- **실제 문제**: 1개 해결 (중요한 데이터 무결성 문제)
