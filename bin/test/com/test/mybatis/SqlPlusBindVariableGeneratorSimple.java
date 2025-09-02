package com.test.mybatis;

import java.io.*;
import java.sql.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * 간단한 Q Chat 기반 바인드 변수 생성기
 */
public class SqlPlusBindVariableGeneratorSimple {
    
    // Q Chat 설정 (빠른 응답 최적화)
    private static final int Q_CHAT_TIMEOUT = Integer.parseInt(System.getenv().getOrDefault("Q_CHAT_TIMEOUT", "3"));
    
    // Oracle 연결 정보
    private static final String ORACLE_HOST = System.getenv("ORACLE_HOST");
    private static final String ORACLE_PORT = System.getenv().getOrDefault("ORACLE_PORT", "1521");
    private static final String ORACLE_SVC_USER = System.getenv("ORACLE_SVC_USER");
    private static final String ORACLE_SVC_PASSWORD = System.getenv("ORACLE_SVC_PASSWORD");
    private static final String ORACLE_SID = System.getenv("ORACLE_SID");
    
    // Fallback 값들
    private static final String FALLBACK_DATE = "2025-08-24";
    private static final String FALLBACK_TIMESTAMP = "2025-08-24 10:30:00";
    private static final int FALLBACK_ID = 1;
    private static final int FALLBACK_AMOUNT = 1000;
    private static final int FALLBACK_DAYS = 30;
    
    private Map<String, String> bindVariables = new HashMap<>();
    
    public static void main(String[] args) {
        new SqlPlusBindVariableGeneratorSimple().run();
    }
    
    private void run() {
        System.out.println("=== 간단한 Q Chat 기반 바인드 변수 생성기 ===\n");
        
        try {
            // 1. 바인드 변수 추출
            extractBindVariables();
            
            // 2. Q Chat으로 값 생성
            generateValues();
            
            // 3. 파일 생성
            generatePropertiesFile();
            
            System.out.println("✓ 완료!");
            
        } catch (Exception e) {
            System.err.println("오류: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private void extractBindVariables() {
        System.out.println("1단계: 바인드 변수 추출...");
        
        // 하드코딩된 테스트 변수들 (실제로는 XML에서 추출)
        bindVariables.put("year", null);
        bindVariables.put("minReactivationProbability", null);
        bindVariables.put("userId", null);
        bindVariables.put("status", null);
        bindVariables.put("email", null);
        
        System.out.printf("✓ %d개 변수 추출 완료\n\n", bindVariables.size());
    }
    
    private void generateValues() {
        System.out.println("2단계: Q Chat 기반 값 생성...");
        
        for (String varName : bindVariables.keySet()) {
            System.out.printf("=== 변수: %s ===\n", varName);
            
            try {
                String value = callQChatForValue(varName);
                if (value != null && !value.trim().isEmpty()) {
                    bindVariables.put(varName, value.trim());
                    System.out.printf("✓ Q Chat 성공: %s\n", value.trim());
                } else {
                    String fallback = generateFallbackValue(varName);
                    bindVariables.put(varName, fallback);
                    System.out.printf("✓ Fallback 사용: %s\n", fallback);
                }
            } catch (Exception e) {
                String fallback = generateFallbackValue(varName);
                bindVariables.put(varName, fallback);
                System.out.printf("✓ Q Chat 실패, Fallback 사용: %s\n", fallback);
            }
            
            System.out.println();
        }
    }
    
    private String callQChatForValue(String varName) throws Exception {
        // 간단한 프롬프트
        String prompt = String.format(
            "SQL 바인드 변수 #{%s}에 적합한 값을 생성해주세요.\n" +
            "변수명의 의미를 파악하여 적절한 값을 반환하세요.\n" +
            "숫자는 숫자만, 문자열은 작은따옴표로 감싸서 반환하세요.\n" +
            "값만 반환하고 설명은 하지 마세요.",
            varName
        );
        
        System.out.println("🤖 Q Chat 프롬프트:");
        System.out.println(prompt);
        System.out.println("-".repeat(40));
        
        // Q Chat 실행
        ProcessBuilder pb = new ProcessBuilder("q", "chat", prompt);
        Process process = pb.start();
        
        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
            }
        }
        
        boolean finished = process.waitFor(Q_CHAT_TIMEOUT, TimeUnit.SECONDS);
        if (!finished) {
            process.destroyForcibly();
            throw new Exception("Q Chat 타임아웃");
        }
        
        if (process.exitValue() != 0) {
            throw new Exception("Q Chat 실행 실패");
        }
        
        String response = output.toString().trim();
        System.out.println("🤖 Q Chat 응답:");
        System.out.println(response);
        System.out.println("-".repeat(40));
        
        return parseResponse(response);
    }
    
    private String parseResponse(String response) {
        if (response == null || response.trim().isEmpty()) {
            return null;
        }
        
        // ANSI 색상 코드 제거
        String clean = response.replaceAll("\\u001B\\[[;\\d]*m", "").trim();
        
        // 라인별로 확인하여 마지막 유효한 값 찾기
        String[] lines = clean.split("\n");
        for (int i = lines.length - 1; i >= 0; i--) {
            String line = lines[i].trim();
            
            if (line.isEmpty() || line.length() > 50) {
                continue;
            }
            
            // 숫자 값
            if (line.matches("^\\d+$")) {
                return line;
            }
            
            // 따옴표로 감싸진 값
            if (line.matches("^'[^']*'$")) {
                return line;
            }
            
            // 간단한 단어
            if (line.matches("^[A-Za-z0-9_-]+$") && line.length() <= 20) {
                return line;
            }
        }
        
        return null;
    }
    
    private String generateFallbackValue(String varName) {
        String lower = varName.toLowerCase();
        
        if (lower.contains("id")) return String.valueOf(FALLBACK_ID);
        if (lower.contains("year")) return "2025";
        if (lower.contains("amount") || lower.contains("price")) return String.valueOf(FALLBACK_AMOUNT);
        if (lower.contains("days")) return String.valueOf(FALLBACK_DAYS);
        if (lower.contains("probability") || lower.contains("score")) return "75";
        if (lower.contains("status")) return "'ACTIVE'";
        if (lower.contains("email")) return "'test@example.com'";
        if (lower.contains("name")) return "'TEST_" + varName.toUpperCase() + "'";
        if (lower.contains("date")) return "'" + FALLBACK_DATE + "'";
        
        return "'DEFAULT_" + varName.toUpperCase() + "'";
    }
    
    private void generatePropertiesFile() throws IOException {
        System.out.println("3단계: parameters.properties 파일 생성...");
        
        try (PrintWriter writer = new PrintWriter(new FileWriter("parameters.properties"))) {
            writer.println("# Q Chat 기반 바인드 변수 매개변수 파일");
            writer.println("# 생성일시: " + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
            writer.println();
            
            List<String> sortedVars = new ArrayList<>(bindVariables.keySet());
            Collections.sort(sortedVars);
            
            for (String varName : sortedVars) {
                String value = bindVariables.get(varName);
                writer.println("# 변수: " + varName);
                writer.println(varName + "=" + value);
                writer.println();
            }
        }
        
        System.out.printf("✓ parameters.properties 파일 생성 완료 (%d개 변수)\n", bindVariables.size());
    }
}
