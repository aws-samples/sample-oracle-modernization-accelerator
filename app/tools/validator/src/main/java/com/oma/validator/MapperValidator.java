package com.oma.validator;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Collectors;
import java.util.concurrent.*;

/**
 * MyBatis Mapper Validator
 * Compares Oracle vs Aurora mapper execution results
 */
public class MapperValidator {

    private static final int MAX_RETRIES = 3;
    private static final ObjectMapper objectMapper = new ObjectMapper()
            .enable(SerializationFeature.INDENT_OUTPUT)
            .enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS);

    private static final Map<String, Map<String, Long>> performanceData = new ConcurrentHashMap<>();
    private static Extension extension;

    public static void main(String[] args) {
        if (args.length < 3) {
            System.out.println("Usage: java -jar mapper-validator.jar <oracle-mapper-dir> <target-mapper-dir> <tc-dir> [target-db-type]");
            System.out.println("");
            System.out.println("Arguments:");
            System.out.println("  target-db-type: postgres (default) or mysql");
            System.out.println("");
            System.out.println("Example:");
            System.out.println("  java -jar mapper-validator.jar \\");
            System.out.println("    /path/to/oracle/mappers \\");
            System.out.println("    /path/to/postgres/mappers \\");
            System.out.println("    ./mappers/daiso-oms/target \\");
            System.out.println("    postgres");
            System.exit(1);
        }

        // Convert to absolute paths
        File oracleMapperDirFile = new File(args[0]).getAbsoluteFile();
        File targetMapperDirFile = new File(args[1]).getAbsoluteFile();
        File tcDirFile = new File(args[2]).getAbsoluteFile();
        String targetDbType = args.length > 3 ? args[3] : "postgres";

        // Validate directories
        if (!oracleMapperDirFile.exists()) {
            System.err.println("✗ Oracle mapper directory not found: " + oracleMapperDirFile.getAbsolutePath());
            System.exit(1);
        }
        if (!targetMapperDirFile.exists()) {
            System.err.println("✗ Target mapper directory not found: " + targetMapperDirFile.getAbsolutePath());
            System.exit(1);
        }
        if (!tcDirFile.exists()) {
            System.err.println("✗ Test case directory not found: " + tcDirFile.getAbsolutePath());
            System.exit(1);
        }

        String oracleMapperDir = oracleMapperDirFile.getAbsolutePath();
        String targetMapperDir = targetMapperDirFile.getAbsolutePath();
        String tcDir = tcDirFile.getAbsolutePath();

        System.out.println("=== MyBatis Mapper Validator ===\n");
        System.out.println("Oracle Mappers:  " + oracleMapperDir);
        System.out.println("Target DB Type:  " + targetDbType.toUpperCase());
        System.out.println("Target Mappers:  " + targetMapperDir);
        System.out.println("Test Cases:      " + tcDir);
        System.out.println("");

        // Load Extension configuration
        try {
            String extensionConfigPath = "extensions/extension.json";
            extension = Extension.load(extensionConfigPath);
        } catch (Exception e) {
            System.out.println("⚠ Extension load failed: " + e.getMessage());
            extension = Extension.createDisabled();
        }

        try {
            MapperValidator validator = new MapperValidator();
            ValidationReport report = validator.validate(oracleMapperDir, targetMapperDir, tcDir, targetDbType);

            // Create output directory
            File outputDir = new File("output");
            if (!outputDir.exists()) {
                outputDir.mkdirs();
            }

            // Save report
            String reportPath = "output/validation-report.json";
            objectMapper.writeValue(new File(reportPath), report);

            // Save performance data
            String perfPath = "output/validation-performance.json";
            objectMapper.writeValue(new File(perfPath), performanceData);

            // Print summary
            report.printSummary();
            System.out.println("\n✓ Report saved to: " + reportPath);
            System.out.println("✓ Performance data saved to: " + perfPath);

            // Exit code
            System.exit(report.hasFailed() ? 1 : 0);

        } catch (Exception e) {
            System.err.println("✗ Validation failed: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }

    public ValidationReport validate(String oracleMapperDir, String targetMapperDir,
                                     String tcDir, String targetDbType) throws Exception {
        ValidationReport report = new ValidationReport();

        // Find all TC files
        List<Path> tcFiles = Files.walk(Paths.get(tcDir))
                .filter(p -> p.toString().endsWith(".tc.json"))
                .collect(Collectors.toList());

        System.out.println("Found " + tcFiles.size() + " test case files\n");

        // Initialize executors
        DatabaseExecutor oracleExecutor = new OracleExecutor(oracleMapperDir);
        DatabaseExecutor targetExecutor;

        if ("mysql".equalsIgnoreCase(targetDbType)) {
            targetExecutor = new MySQLExecutor(targetMapperDir);
        } else {
            targetExecutor = new PostgresExecutor(targetMapperDir);
        }

        // Set Extension for both executors
        if (extension != null && extension.isEnabled()) {
            oracleExecutor.setExtension(extension, "oracle");
            targetExecutor.setExtension(extension, targetDbType);
        }

        // Create thread pool for parallel execution
        int parallelism = 5;
        ExecutorService executor = Executors.newFixedThreadPool(parallelism);

        try {
            // Process each TC file in parallel
            List<Future<?>> futures = new ArrayList<>();

            for (Path tcFile : tcFiles) {
                Future<?> future = executor.submit(() -> {
                    try {
                        processTcFile(tcFile, oracleExecutor, targetExecutor, report);
                    } catch (Exception e) {
                        System.err.println("Error processing " + tcFile.getFileName() + ": " + e.getMessage());
                    }
                });
                futures.add(future);
            }

            // Wait for all tasks to complete
            for (Future<?> future : futures) {
                try {
                    future.get();
                } catch (Exception e) {
                    System.err.println("Task execution error: " + e.getMessage());
                }
            }
        } finally {
            executor.shutdown();
            try {
                if (!executor.awaitTermination(60, TimeUnit.SECONDS)) {
                    executor.shutdownNow();
                }
            } catch (InterruptedException e) {
                executor.shutdownNow();
            }
            oracleExecutor.close();
            targetExecutor.close();
        }

        return report;
    }

    private void processTcFile(Path tcFile, DatabaseExecutor oracleExec,
                               DatabaseExecutor postgresExec, ValidationReport report) throws Exception {

        // Parse TC file
        @SuppressWarnings("unchecked")
        Map<String, Object> tcData = objectMapper.readValue(tcFile.toFile(), Map.class);

        String mapperFile = (String) tcData.get("file");
        String sqlId = extractSqlId(mapperFile, tcFile.getFileName().toString());

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> testCases = (List<Map<String, Object>>) tcData.get("test_cases");

        if (testCases == null || testCases.isEmpty()) {
            report.addSkipped(sqlId, "No test cases");
            return;
        }

        System.out.println("Testing: " + sqlId);

        // Use first test case
        Map<String, Object> params = (Map<String, Object>) testCases.get(0).get("parameters");

        boolean passed = false;
        int retryCount = 0;

        for (int attempt = 0; attempt <= MAX_RETRIES; attempt++) {
            try {
                // Execute on Oracle and measure time
                long oracleStart = System.currentTimeMillis();
                String oracleResult = oracleExec.execute(sqlId, params);
                long oracleTime = System.currentTimeMillis() - oracleStart;

                // Execute on PostgreSQL and measure time
                long postgresStart = System.currentTimeMillis();
                String postgresResult = postgresExec.execute(sqlId, params);
                long postgresTime = System.currentTimeMillis() - postgresStart;

                // Record performance data
                Map<String, Long> timings = new HashMap<>();
                timings.put("oracle_ms", oracleTime);
                timings.put("postgres_ms", postgresTime);
                performanceData.put(sqlId, timings);

                // Compare results
                if (oracleResult.equals(postgresResult)) {
                    passed = true;
                    report.addPassed(sqlId, retryCount);
                    if (retryCount > 0) {
                        System.out.println("  ✓ PASS (after " + retryCount + " retries)");
                    } else {
                        System.out.println("  ✓ PASS");
                    }
                    break;
                } else {
                    if (attempt < MAX_RETRIES) {
                        System.out.println("  ✗ Results differ, retrying... (" + (attempt + 1) + "/" + MAX_RETRIES + ")");
                        retryCount++;
                        // TODO: Trigger reconversion
                        Thread.sleep(1000); // Wait before retry
                    } else {
                        report.addFailed(sqlId, retryCount, oracleResult, postgresResult);
                        System.out.println("  ✗ FAIL (after " + MAX_RETRIES + " retries)");
                    }
                }
            } catch (Exception e) {
                report.addError(sqlId, e.getMessage());
                System.out.println("  ✗ ERROR: " + e.getMessage());
                break;
            }
        }
    }

    private String extractSqlId(String mapperFile, String tcFileName) {
        // Extract SQL ID from TC filename: {mapper}_{sqlId}.tc.json
        // Example: oms-common-sql-oracle_selectTAdminMstOw.tc.json -> selectTAdminMstOw
        String withoutExtension = tcFileName.replace(".tc.json", "");
        int lastUnderscore = withoutExtension.lastIndexOf('_');
        if (lastUnderscore > 0) {
            return withoutExtension.substring(lastUnderscore + 1);
        }
        return withoutExtension;
    }
}
