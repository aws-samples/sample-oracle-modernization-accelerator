# 🔢 부동소수점 자릿수 차이 근본 해결 방안

## 🚨 현재 문제 상황

### 발견된 차이 예시
```json
// Oracle
"monetary_value": 1513.42

// PostgreSQL  
"monetary_value": 1513.420000
```

**문제점:**
- 같은 값이지만 표현 방식이 다름
- JSON 직렬화 시 자릿수 차이
- 테스트 검증에서 다른 값으로 판단

---

## 💡 근본 해결 방안들

### 1. 🎯 데이터베이스 레벨 해결

#### A. 데이터 타입 통일
```sql
-- Oracle & PostgreSQL 공통
-- DECIMAL(10,2) 또는 NUMERIC(10,2) 사용
ALTER TABLE orders MODIFY total_amount DECIMAL(10,2);
ALTER TABLE payments MODIFY amount DECIMAL(10,2);

-- 부동소수점(FLOAT, DOUBLE) 사용 금지
-- → 고정소수점(DECIMAL, NUMERIC) 사용
```

#### B. SQL에서 명시적 반올림
```sql
-- Oracle
SELECT ROUND(monetary_value, 2) as monetary_value
FROM rfm_analysis;

-- PostgreSQL  
SELECT ROUND(monetary_value::numeric, 2) as monetary_value
FROM rfm_analysis;
```

#### C. 포맷팅 함수 사용
```sql
-- Oracle
SELECT TO_CHAR(monetary_value, 'FM999999990.00') as monetary_value
FROM rfm_analysis;

-- PostgreSQL
SELECT TO_CHAR(monetary_value, 'FM999999990.00') as monetary_value  
FROM rfm_analysis;
```

### 2. 🏗️ 애플리케이션 레벨 해결

#### A. MyBatis TypeHandler 구현
```java
@MappedTypes(BigDecimal.class)
@MappedJdbcTypes({JdbcType.DECIMAL, JdbcType.NUMERIC})
public class StandardizedDecimalTypeHandler extends BaseTypeHandler<BigDecimal> {
    
    private static final int SCALE = 2; // 소수점 2자리로 통일
    
    @Override
    public void setNonNullParameter(PreparedStatement ps, int i, 
                                   BigDecimal parameter, JdbcType jdbcType) throws SQLException {
        ps.setBigDecimal(i, parameter.setScale(SCALE, RoundingMode.HALF_UP));
    }
    
    @Override
    public BigDecimal getNullableResult(ResultSet rs, String columnName) throws SQLException {
        BigDecimal result = rs.getBigDecimal(columnName);
        return result != null ? result.setScale(SCALE, RoundingMode.HALF_UP) : null;
    }
}
```

#### B. JSON 직렬화 커스터마이징
```java
// Jackson 설정
@JsonSerialize(using = StandardizedDecimalSerializer.class)
public class StandardizedDecimalSerializer extends JsonSerializer<BigDecimal> {
    @Override
    public void serialize(BigDecimal value, JsonGenerator gen, SerializerProvider serializers) 
            throws IOException {
        if (value != null) {
            gen.writeNumber(value.setScale(2, RoundingMode.HALF_UP));
        }
    }
}
```

#### C. DTO에서 표준화
```java
public class RFMAnalysisDto {
    private BigDecimal monetaryValue;
    
    public void setMonetaryValue(BigDecimal monetaryValue) {
        this.monetaryValue = monetaryValue != null ? 
            monetaryValue.setScale(2, RoundingMode.HALF_UP) : null;
    }
    
    @JsonSerialize(using = ToStringSerializer.class)
    public BigDecimal getMonetaryValue() {
        return monetaryValue;
    }
}
```

### 3. 🔧 테스트 프레임워크 레벨 해결

#### A. 결과 정규화 함수 (즉시 적용 가능)
```sql
CREATE OR REPLACE FUNCTION normalize_decimal_precision(json_text TEXT) 
RETURNS TEXT AS $$
BEGIN
    -- 소수점 뒤 불필요한 0 제거
    json_text := REGEXP_REPLACE(json_text, '(\d+)\.0+([,\]}])', '\1.0\2', 'g');
    
    -- 소수점 2자리로 통일 (3자리 이상인 경우)
    json_text := REGEXP_REPLACE(json_text, '(\d+\.\d{2})\d+([,\]}])', '\1\2', 'g');
    
    -- 소수점 1자리를 2자리로 확장
    json_text := REGEXP_REPLACE(json_text, '(\d+\.)(\d)([,\]}])', '\1\20\3', 'g');
    
    RETURN json_text;
END;
$$ LANGUAGE plpgsql;
```

#### B. 수치 허용 오차 비교
```sql
CREATE OR REPLACE FUNCTION compare_with_decimal_tolerance(
    src_json TEXT, 
    tgt_json TEXT,
    tolerance DECIMAL DEFAULT 0.01
) RETURNS BOOLEAN AS $$
DECLARE
    src_data JSONB;
    tgt_data JSONB;
    src_key TEXT;
    src_val NUMERIC;
    tgt_val NUMERIC;
BEGIN
    src_data := src_json::JSONB -> 'results' -> 0;
    tgt_data := tgt_json::JSONB -> 'results' -> 0;
    
    -- 각 숫자 필드 비교
    FOR src_key IN SELECT jsonb_object_keys(src_data) LOOP
        IF jsonb_typeof(src_data -> src_key) = 'number' THEN
            src_val := (src_data ->> src_key)::NUMERIC;
            tgt_val := (tgt_data ->> src_key)::NUMERIC;
            
            IF ABS(src_val - tgt_val) > tolerance THEN
                RETURN FALSE;
            END IF;
        END IF;
    END LOOP;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
```

### 4. 🏛️ 아키텍처 레벨 해결

#### A. 데이터베이스 설계 표준화
```sql
-- 금액 관련 컬럼 표준
CREATE DOMAIN money_amount AS DECIMAL(15,2);
CREATE DOMAIN percentage AS DECIMAL(5,2);
CREATE DOMAIN rate AS DECIMAL(8,4);

-- 테이블 생성 시 도메인 사용
CREATE TABLE orders (
    order_id BIGINT PRIMARY KEY,
    total_amount money_amount,
    tax_rate rate,
    discount_percentage percentage
);
```

#### B. 설정 기반 정밀도 관리
```yaml
# application.yml
database:
  precision:
    money: 2
    percentage: 2  
    rate: 4
    default: 2
```

---

## 🛠️ 즉시 적용 가능한 해결책

### 1단계: SQL 레벨 수정 (가장 확실한 방법)
```sql
-- RFM Analysis SQL 수정
SELECT 
    u.USER_ID,
    u.EMAIL,
    ROUND(COALESCE(rfm_data.RECENCY_DAYS, 999), 0) as RECENCY_DAYS,
    ROUND(COALESCE(rfm_data.FREQUENCY_ORDERS, 0), 0) as FREQUENCY_ORDERS,
    ROUND(COALESCE(rfm_data.MONETARY_VALUE, 0), 2) as MONETARY_VALUE,  -- 소수점 2자리로 통일
    -- ... 나머지 컬럼들
```

### 2단계: 테스트 검증 개선
```sql
-- sqllist 테이블에 정규화 비교 추가
UPDATE sqllist SET 
    same = CASE 
        WHEN src_result = tgt_result THEN 'Y'
        WHEN normalize_decimal_precision(src_result) = normalize_decimal_precision(tgt_result) THEN 'Y'
        ELSE 'N' 
    END;
```

### 3단계: 장기적 데이터 타입 통일
```sql
-- 모든 금액 관련 컬럼을 DECIMAL로 변경
ALTER TABLE orders ALTER COLUMN total_amount TYPE DECIMAL(15,2);
ALTER TABLE payments ALTER COLUMN amount TYPE DECIMAL(15,2);
-- ... 기타 테이블들
```

---

## 🎯 권장 접근 방식

### 즉시 (1주일 내)
1. **SQL에서 ROUND() 함수 추가** - 가장 확실하고 빠른 해결
2. **테스트 검증에 정규화 함수 적용**

### 단기 (1개월 내)  
3. **MyBatis TypeHandler 구현**
4. **JSON 직렬화 표준화**

### 장기 (3개월 내)
5. **데이터베이스 스키마 표준화**
6. **도메인 기반 데이터 타입 적용**

---

## 📊 예상 효과

### 즉시 효과
- **73 bytes 차이 해결**
- **테스트 정확도 향상**
- **false positive 감소**

### 장기 효과  
- **데이터 일관성 보장**
- **부동소수점 오차 근본 해결**
- **유지보수성 향상**

가장 **즉시 적용 가능하고 효과적인 방법**은 **SQL에서 ROUND() 함수를 사용**하는 것입니다!
