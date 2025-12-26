package com.example;

import java.util.Map;

public class MmaScMcpToolsTest {
    
    public static void main(String[] args) {
        MmaScMcpTools tools = new MmaScMcpTools();
        
        if (args.length == 0) {
            System.out.println("Usage:");
            System.out.println("  java MmaScMcpToolsTest analyze <s3-path>");
            System.out.println("  java MmaScMcpToolsTest cleanup [path]");
            System.out.println("\nExample:");
            System.out.println("  java MmaScMcpToolsTest analyze s3://mma-dms-sc-111709976242/dms-sc-migration-project/");
            System.out.println("  java MmaScMcpToolsTest cleanup");
            return;
        }
        
        String command = args[0];
        
        switch (command) {
            case "analyze" -> {
                if (args.length < 2) {
                    System.err.println("Error: S3 path required");
                    return;
                }
                String s3Path = args[1];
                System.out.println("Analyzing: " + s3Path);
                Map<String, Object> result = tools.analyzeDmsScProject(s3Path);
                printResult(result);
            }
            case "cleanup" -> {
                String path = args.length > 1 ? args[1] : "";
                System.out.println("Cleaning up: " + (path.isEmpty() ? "default cache" : path));
                Map<String, Object> result = tools.cleanupLocalCache(path);
                printResult(result);
            }
            default -> System.err.println("Unknown command: " + command);
        }
    }
    
    private static void printResult(Map<String, Object> result) {
        System.out.println("\n=== Result ===");
        result.forEach((key, value) -> {
            if (value instanceof Map || value instanceof java.util.List) {
                System.out.println(key + ": " + value);
            } else {
                System.out.println(key + ": " + value);
            }
        });
    }
}
