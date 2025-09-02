# 🔄 유연한 데이터 검증 방법 제안

## 🚨 현재 방식의 문제점

### 단순 문자열 비교의 한계
```sql
-- 현재 방식
UPDATE sqllist SET same = CASE WHEN src_result = tgt_result THEN 'Y' ELSE 'N' END;
```

**문제점들:**
1. **컬럼명 차이**: `count(*)` vs `count` → 실제 데이터는 동일하지만 다르다고 판단
2. **포맷팅 차이**: 공백, 줄바꿈, 들여쓰기 차이
3. **정렬 순서**: 동일한 데이터지만 ORDER BY 없는 경우 순서 차이
4. **숫자 정밀도**: `1.0` vs `1.00` vs `1`
5. **날짜 포맷**: `2025-01-01` vs `2025/01/01` vs `01-JAN-25`
6. **NULL 표현**: `null` vs `NULL` vs 빈 문자열

---

## 💡 개선된 검증 방법들

### 1. 📊 JSON 구조 기반 비교

#### A. 실제 데이터만 비교
```sql
-- PostgreSQL JSON 함수 활용
CREATE OR REPLACE FUNCTION compare_json_data(src_json TEXT, tgt_json TEXT) 
RETURNS BOOLEAN AS $$
DECLARE
    src_data JSONB;
    tgt_data JSONB;
BEGIN
    -- results 배열만 추출하여 비교
    src_data := (src_json::JSONB -> 'results');
    tgt_data := (tgt_json::JSONB -> 'results');
    
    -- 배열 길이 비교
    IF jsonb_array_length(src_data) != jsonb_array_length(tgt_data) THEN
        RETURN FALSE;
    END IF;
    
    -- 각 행의 값들만 비교 (컬럼명 무시)
    FOR i IN 0..jsonb_array_length(src_data)-1 LOOP
        IF NOT compare_row_values(src_data->i, tgt_data->i) THEN
            RETURN FALSE;
        END IF;
    END LOOP;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
```

#### B. 컬럼명 정규화 비교
```sql
CREATE OR REPLACE FUNCTION normalize_column_names(json_text TEXT) 
RETURNS TEXT AS $$
BEGIN
    -- count(*) -> count 정규화
    json_text := REPLACE(json_text, '"count(*)"', '"count"');
    -- sum(*) -> sum 정규화  
    json_text := REPLACE(json_text, '"sum(*)"', '"sum"');
    -- 기타 집계함수 정규화...
    
    RETURN json_text;
END;
$$ LANGUAGE plpgsql;
```

### 2. 🔢 수치 데이터 허용 오차 비교

```sql
CREATE OR REPLACE FUNCTION compare_with_tolerance(
    src_json TEXT, 
    tgt_json TEXT,
    numeric_tolerance DECIMAL DEFAULT 0.01,
    percentage_tolerance DECIMAL DEFAULT 0.001
) RETURNS BOOLEAN AS $$
DECLARE
    src_data JSONB;
    tgt_data JSONB;
BEGIN
    src_data := src_json::JSONB -> 'results';
    tgt_data := tgt_json::JSONB -> 'results';
    
    -- 수치 비교 시 허용 오차 적용
    -- 예: 1000.00 vs 1000.01 → 허용
    -- 예: 99.999% vs 100.000% → 허용
    
    RETURN compare_numeric_arrays(src_data, tgt_data, numeric_tolerance);
END;
$$ LANGUAGE plpgsql;
```

### 3. 📋 정렬 무관 비교

```sql
CREATE OR REPLACE FUNCTION compare_unordered_results(src_json TEXT, tgt_json TEXT) 
RETURNS BOOLEAN AS $$
DECLARE
    src_sorted JSONB;
    tgt_sorted JSONB;
BEGIN
    -- JSON 배열을 정렬하여 비교
    src_sorted := sort_json_array(src_json::JSONB -> 'results');
    tgt_sorted := sort_json_array(tgt_json::JSONB -> 'results');
    
    RETURN src_sorted = tgt_sorted;
END;
$$ LANGUAGE plpgsql;
```

### 4. 🎯 다단계 검증 시스템

```sql
-- sqllist 테이블에 상세 검증 컬럼 추가
ALTER TABLE sqllist ADD COLUMN validation_level INTEGER DEFAULT 0;
ALTER TABLE sqllist ADD COLUMN validation_details JSONB;

-- 검증 레벨 정의:
-- 0: 완전 동일 (문자열 일치)
-- 1: 구조적 동일 (컬럼명 정규화 후 일치)  
-- 2: 데이터 동일 (값만 비교, 순서/포맷 무시)
-- 3: 근사 동일 (허용 오차 내 일치)
-- 4: 의미적 동일 (비즈니스 로직상 동일)
-- -1: 완전 다름
```

---

## 🛠️ 구현 방안

### Phase 1: 즉시 적용 가능한 개선

#### A. 컬럼명 정규화 함수
```sql
CREATE OR REPLACE FUNCTION normalize_result_json(json_text TEXT) 
RETURNS TEXT AS $$
BEGIN
    -- 집계 함수 컬럼명 정규화
    json_text := REGEXP_REPLACE(json_text, '"(count|sum|avg|min|max)\([^)]*\)"', '"\1"', 'g');
    
    -- 공백 정규화
    json_text := REGEXP_REPLACE(json_text, '\s+', ' ', 'g');
    
    -- 숫자 정규화 (소수점 뒤 0 제거)
    json_text := REGEXP_REPLACE(json_text, '(\d+)\.0+([,\]}])', '\1\2', 'g');
    
    RETURN TRIM(json_text);
END;
$$ LANGUAGE plpgsql;
```

#### B. 개선된 same 컬럼 업데이트
```sql
UPDATE sqllist SET 
    same = CASE 
        WHEN src_result = tgt_result THEN 'Y'
        WHEN normalize_result_json(src_result) = normalize_result_json(tgt_result) THEN 'Y'
        ELSE 'N' 
    END,
    validation_level = CASE 
        WHEN src_result = tgt_result THEN 0
        WHEN normalize_result_json(src_result) = normalize_result_json(tgt_result) THEN 1
        ELSE -1
    END;
```

### Phase 2: 고도화된 검증 시스템

#### A. 검증 설정 테이블
```sql
CREATE TABLE validation_config (
    sql_type CHAR(1),
    validation_method VARCHAR(50),
    tolerance_config JSONB,
    ignore_columns TEXT[],
    sort_columns TEXT[]
);

-- 예시 설정
INSERT INTO validation_config VALUES 
('S', 'count_queries', '{"numeric_tolerance": 0}', '{}', '{}'),
('S', 'analytical_queries', '{"numeric_tolerance": 0.01, "percentage_tolerance": 0.001}', '{}', '{"created_at", "updated_at"}');
```

#### B. 동적 검증 함수
```sql
CREATE OR REPLACE FUNCTION smart_compare_results(
    sql_id TEXT,
    src_result TEXT, 
    tgt_result TEXT
) RETURNS JSONB AS $$
DECLARE
    config RECORD;
    result JSONB;
BEGIN
    -- SQL 타입별 설정 조회
    SELECT * INTO config FROM validation_config 
    WHERE sql_type = (SELECT sql_type FROM sqllist WHERE sqllist.sql_id = smart_compare_results.sql_id);
    
    -- 설정에 따른 동적 검증
    result := jsonb_build_object(
        'exact_match', src_result = tgt_result,
        'normalized_match', normalize_result_json(src_result) = normalize_result_json(tgt_result),
        'data_match', compare_data_only(src_result, tgt_result),
        'tolerance_match', compare_with_tolerance(src_result, tgt_result, config.tolerance_config)
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;
```

---

## 🎯 권장 구현 순서

### 1단계 (즉시): 컬럼명 정규화
- `count(*)` → `count` 변환
- 공백/포맷 정규화
- **효과**: 3 bytes 차이 문제 해결

### 2단계 (단기): 수치 허용오차
- 소수점 정밀도 차이 허용
- 퍼센트 계산 오차 허용  
- **효과**: 73 bytes 차이 등 해결

### 3단계 (중기): 정렬 무관 비교
- ORDER BY 없는 쿼리 대응
- **효과**: 정렬 차이만 있는 SQL 해결

### 4단계 (장기): AI 기반 의미 비교
- 비즈니스 로직 기반 검증
- **효과**: 복잡한 분석 쿼리 검증

---

## 💻 즉시 적용 가능한 스크립트

```bash
#!/bin/bash
# flexible_validation.sh

# 1. 정규화 함수 생성
psql -c "$(cat normalize_functions.sql)"

# 2. 검증 레벨 컬럼 추가
psql -c "
ALTER TABLE sqllist ADD COLUMN IF NOT EXISTS validation_level INTEGER DEFAULT 0;
ALTER TABLE sqllist ADD COLUMN IF NOT EXISTS validation_details JSONB;
"

# 3. 개선된 검증 실행
psql -c "
UPDATE sqllist SET 
    validation_level = CASE 
        WHEN src_result = tgt_result THEN 0
        WHEN normalize_result_json(src_result) = normalize_result_json(tgt_result) THEN 1
        ELSE -1
    END,
    same = CASE WHEN validation_level >= 0 THEN 'Y' ELSE 'N' END;
"

# 4. 결과 리포트
psql -c "
SELECT 
    validation_level,
    COUNT(*) as count,
    CASE validation_level
        WHEN 0 THEN 'Exact Match'
        WHEN 1 THEN 'Normalized Match'  
        WHEN -1 THEN 'Different'
    END as description
FROM sqllist 
GROUP BY validation_level 
ORDER BY validation_level;
"
```

이런 방식으로 단계적으로 개선하면 더 정확하고 유연한 검증이 가능합니다!
