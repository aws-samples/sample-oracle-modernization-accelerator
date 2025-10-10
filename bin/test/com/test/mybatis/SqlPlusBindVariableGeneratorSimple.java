package com.test.mybatis;

import java.io.*;
import java.sql.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Simple Q Chat-based bind variable generator
 */
public class SqlPlusBindVariableGeneratorSimple {
    
    // Q Chat settings (optimized for fast response)
    private static final int Q_CHAT_TIMEOUT = Integer.parseInt(System.getenv().getOrDefault("Q_CHAT_TIMEOUT", "3"));
    
    // Oracle connection information
    private static final String ORACLE_HOST = System.getenv("ORACLE_HOST");
    private static final String ORACLE_PORT = System.getenv().getOrDefault("ORACLE_PORT", "1521");
    private static final String ORACLE_SVC_USER = System.getenv("ORACLE_SVC_USER");
    private static final String ORACLE_SVC_PASSWORD = System.getenv("ORACLE_SVC_PASSWORD");
    private static final String ORACLE_SID = System.getenv("ORACLE_SID");
    
    // Fallback values
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
        System.out.println("=== Simple Q Chat-based Bind Variable Generator ===\n");
        
        try {
            // 1. Extract bind variables
            extractBindVariables();
            
            // 2. Generate values with Q Chat
            generateValues();
            
            // 3. Generate file
            generatePropertiesFile();
            
            System.out.println("✓ Completed!");
            
        } catch (Exception e) {
            System.err.println("error: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private void extractBindVariables() {
        System.out.println("Step 1: Extracting bind variables...");
        
        // Hardcoded test variables (in practice, extracted from XML)
        bindVariables.put("year", null);
        bindVariables.put("minReactivationProbability", null);
        bindVariables.put("userId", null);
        bindVariables.put("status", null);
        bindVariables.put("email", null);
        
        System.out.printf("✓ %d variables extraction completed\n\n", bindVariables.size());
    }
    
    private void generateValues() {
        System.out.println("Step 2: Q Chat-based value generation...");
        
        for (String varName : bindVariables.keySet()) {
            System.out.printf("=== Variable: %s ===\n", varName);
            
            try {
                String value = callQChatForValue(varName);
                if (value != null && !value.trim().isEmpty()) {
                    bindVariables.put(varName, value.trim());
                    System.out.printf("✓ Q Chat Success: %s\n", value.trim());
                } else {
                    String fallback = generateFallbackValue(varName);
                    bindVariables.put(varName, fallback);
                    System.out.printf("✓ Using fallback: %s\n", fallback);
                }
            } catch (Exception e) {
                String fallback = generateFallbackValue(varName);
                bindVariables.put(varName, fallback);
                System.out.printf("✓ Q Chat failed, using fallback: %s\n", fallback);
            }
            
            System.out.println();
        }
    }
    
    private String callQChatForValue(String varName) throws Exception {
        // Simple prompt
        String prompt = String.format(
            "Generate an appropriate value for SQL bind variable #{%s}.\n" +
            "Understand the meaning of the variable name and return an appropriate value.\n" +
            "Return only numbers for numeric values, and wrap strings in single quotes.\n" +
            "Return only the value without explanation.",
            varName
        );
        
        System.out.println("🤖 Q Chat prompt:");
        System.out.println(prompt);
        System.out.println("-".repeat(40));
        
        // Execute Q Chat
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
            throw new Exception("Q Chat timeout");
        }
        
        if (process.exitValue() != 0) {
            throw new Exception("Q Chat execution failed");
        }
        
        String response = output.toString().trim();
        System.out.println("🤖 Q Chat response:");
        System.out.println(response);
        System.out.println("-".repeat(40));
        
        return parseResponse(response);
    }
    
    private String parseResponse(String response) {
        if (response == null || response.trim().isEmpty()) {
            return null;
        }
        
        // Remove ANSI color codes
        String clean = response.replaceAll("\\u001B\\[[;\\d]*m", "").trim();
        
        // Check line by line to find the last valid value
        String[] lines = clean.split("\n");
        for (int i = lines.length - 1; i >= 0; i--) {
            String line = lines[i].trim();
            
            if (line.isEmpty() || line.length() > 50) {
                continue;
            }
            
            // Numeric value
            if (line.matches("^\\d+$")) {
                return line;
            }
            
            // Value wrapped in quotes
            if (line.matches("^'[^']*'$")) {
                return line;
            }
            
            // Simple word
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
        System.out.println("Step 3: Generating parameters.properties file...");
        
        try (PrintWriter writer = new PrintWriter(new FileWriter("parameters.properties"))) {
            writer.println("# Q Chat-based bind variable parameter file");
            writer.println("# Generated: " + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
            writer.println();
            
            List<String> sortedVars = new ArrayList<>(bindVariables.keySet());
            Collections.sort(sortedVars);
            
            for (String varName : sortedVars) {
                String value = bindVariables.get(varName);
                writer.println("# Variable: " + varName);
                writer.println(varName + "=" + value);
                writer.println();
            }
        }
        
        System.out.printf("✓ parameters.properties file generation completed (%d variables)\n", bindVariables.size());
    }
}
