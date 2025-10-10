package com.test.mybatis;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

/**
 * Utility class to normalize Oracle and PostgreSQL result differences
 */
public class ResultNormalizer {
    
    /**
     * Normalize SQL execution results to remove differences between Oracle and PostgreSQL
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
     * Normalize individual values
     */
    private static Object normalizeValue(Object value) {
        if (value == null) {
            return ""; // Unify NULL to empty string
        }
        
        // Handle number types
        if (value instanceof Number) {
            return normalizeNumber((Number) value);
        }
        
        // Handle string types
        if (value instanceof String) {
            return normalizeString((String) value);
        }
        
        // Convert other types to string
        return value.toString();
    }
    
    /**
     * Normalize numeric values
     */
    private static String normalizeNumber(Number number) {
        if (number instanceof BigDecimal) {
            BigDecimal bd = (BigDecimal) number;
            
            // Handle values close to 0 as "0"
            if (bd.compareTo(BigDecimal.ZERO) == 0 || 
                bd.abs().compareTo(new BigDecimal("0.000001")) < 0) {
                return "0";
            }
            
            // Check if it's an integer
            if (bd.scale() <= 0 || bd.remainder(BigDecimal.ONE).compareTo(BigDecimal.ZERO) == 0) {
                return bd.toBigInteger().toString();
            }
            
            // For decimal values - remove unnecessary zeros
            return bd.stripTrailingZeros().toPlainString();
        }
        
        // Other number types
        if (number instanceof Integer || number instanceof Long) {
            return number.toString();
        }
        
        if (number instanceof Float || number instanceof Double) {
            double d = number.doubleValue();
            
            // Handle values close to 0
            if (Math.abs(d) < 0.000001) {
                return "0";
            }
            
            // Check if it's an integer
            if (d == Math.floor(d)) {
                return String.valueOf((long) d);
            }
            
            // Handle decimals - convert to BigDecimal for accurate representation
            BigDecimal bd = BigDecimal.valueOf(d);
            return bd.stripTrailingZeros().toPlainString();
        }
        
        return number.toString();
    }
    
    /**
     * Normalize string values
     */
    private static String normalizeString(String str) {
        if (str == null || str.trim().isEmpty()) {
            return "";
        }
        
        // Handle scientific notation (e.g., "0E-20" → "0")
        if (str.matches("^-?\\d+(\\.\\d+)?[Ee][+-]?\\d+$")) {
            try {
                BigDecimal bd = new BigDecimal(str);
                
                // Handle values close to 0 as "0"
                if (bd.abs().compareTo(new BigDecimal("0.000001")) < 0) {
                    return "0";
                }
                
                return bd.stripTrailingZeros().toPlainString();
            } catch (NumberFormatException e) {
                // Return original if conversion fails
                return str;
            }
        }
        
        // Check if it's a numeric string and normalize
        if (str.matches("^-?\\d+(\\.\\d+)?$")) {
            try {
                BigDecimal bd = new BigDecimal(str);
                return normalizeNumber(bd);
            } catch (NumberFormatException e) {
                // Return original if conversion fails
                return str;
            }
        }
        
        return str;
    }
}
