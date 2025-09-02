package com.test.mybatis;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

/**
 * Oracle과 PostgreSQL 결과 차이를 정규화하는 유틸리티 클래스
 */
public class ResultNormalizer {
    
    /**
     * SQL 실행 결과를 정규화하여 Oracle과 PostgreSQL 간 차이를 제거
     */
    public static List<Map<String, Object>> normalizeResults(List<Map<String, Object>> results) {
        if (results == null || results.isEmpty()) {
            return results;
        }
        
        List<Map<String, Object>> normalizedResults = new ArrayList<>();
        
        for (Map<String, Object> row : results) {
            Map<String, Object> normalizedRow = new LinkedHashMap<>();
            
            for (Map.Entry<String, Object> entry : row.entrySet()) {
                String key = entry.getKey();
                Object value = entry.getValue();
                
                normalizedRow.put(key, normalizeValue(value));
            }
            
            normalizedResults.add(normalizedRow);
        }
        
        return normalizedResults;
    }
    
    /**
     * 개별 값을 정규화
     */
    private static Object normalizeValue(Object value) {
        if (value == null) {
            return ""; // NULL을 빈 문자열로 통일
        }
        
        // 숫자 타입 처리
        if (value instanceof Number) {
            return normalizeNumber((Number) value);
        }
        
        // 문자열 타입 처리
        if (value instanceof String) {
            return normalizeString((String) value);
        }
        
        // 기타 타입은 문자열로 변환
        return value.toString();
    }
    
    /**
     * 숫자 값 정규화
     */
    private static String normalizeNumber(Number number) {
        if (number instanceof BigDecimal) {
            BigDecimal bd = (BigDecimal) number;
            
            // 0에 가까운 값은 "0"으로 처리
            if (bd.compareTo(BigDecimal.ZERO) == 0 || 
                bd.abs().compareTo(new BigDecimal("0.000001")) < 0) {
                return "0";
            }
            
            // 정수인지 확인
            if (bd.scale() <= 0 || bd.remainder(BigDecimal.ONE).compareTo(BigDecimal.ZERO) == 0) {
                return bd.toBigInteger().toString();
            }
            
            // 소수점이 있는 경우 - 불필요한 0 제거
            return bd.stripTrailingZeros().toPlainString();
        }
        
        // 다른 숫자 타입들
        if (number instanceof Integer || number instanceof Long) {
            return number.toString();
        }
        
        if (number instanceof Float || number instanceof Double) {
            double d = number.doubleValue();
            
            // 0에 가까운 값 처리
            if (Math.abs(d) < 0.000001) {
                return "0";
            }
            
            // 정수인지 확인
            if (d == Math.floor(d)) {
                return String.valueOf((long) d);
            }
            
            // 소수점 처리 - BigDecimal로 변환하여 정확한 표현
            BigDecimal bd = BigDecimal.valueOf(d);
            return bd.stripTrailingZeros().toPlainString();
        }
        
        return number.toString();
    }
    
    /**
     * 문자열 값 정규화
     */
    private static String normalizeString(String str) {
        if (str == null || str.trim().isEmpty()) {
            return "";
        }
        
        // 과학적 표기법 처리 (예: "0E-20" → "0")
        if (str.matches("^-?\\d+(\\.\\d+)?[Ee][+-]?\\d+$")) {
            try {
                BigDecimal bd = new BigDecimal(str);
                
                // 0에 가까운 값은 "0"으로 처리
                if (bd.abs().compareTo(new BigDecimal("0.000001")) < 0) {
                    return "0";
                }
                
                return bd.stripTrailingZeros().toPlainString();
            } catch (NumberFormatException e) {
                // 변환 실패 시 원본 반환
                return str;
            }
        }
        
        // 숫자 문자열인지 확인하고 정규화
        if (str.matches("^-?\\d+(\\.\\d+)?$")) {
            try {
                BigDecimal bd = new BigDecimal(str);
                return normalizeNumber(bd);
            } catch (NumberFormatException e) {
                // 변환 실패 시 원본 반환
                return str;
            }
        }
        
        return str;
    }
}
