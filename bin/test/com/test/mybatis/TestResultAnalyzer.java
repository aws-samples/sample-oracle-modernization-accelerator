package com.test.mybatis;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.*;
import java.nio.file.*;
import java.sql.*;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Oracle vs PostgreSQL test result analysis program
 * 
 * Features:
 * 1. Analyze PostgreSQL Execute SQL Failed SQL errors
 * 2. Analyze sqllist table same='N' cases
 *    - Different lengths: 'Results differ'
 *    - Same length: Compare after JSON sorting to distinguish 'Sorting difference' vs 'Results differ'
 */
public class TestResultAnalyzer {
    
    // Read PostgreSQL connection information from environment variables
    private static final String POSTGRES_HOST = System.getenv("PGHOST") != null ? System.getenv("PGHOST") : "localhost";
    private static final String POSTGRES_PORT = System.getenv("PGPORT") != null ? System.getenv("PGPORT") : "5432";
    private static final String POSTGRES_DATABASE = System.getenv("PGDATABASE") != null ? System.getenv("PGDATABASE") : "oma";
    private static final String POSTGRES_USER = System.getenv("PGUSER") != null ? System.getenv("PGUSER") : "oma";
    private static final String POSTGRES_PASSWORD = System.getenv("PGPASSWORD") != null ? System.getenv("PGPASSWORD") : "";
    private static final String POSTGRES_URL = "jdbc:postgresql://" + POSTGRES_HOST + ":" + POSTGRES_PORT + "/" + POSTGRES_DATABASE;
    
    private ObjectMapper objectMapper;
    
    public TestResultAnalyzer() {
        this.objectMapper = new ObjectMapper();
        this.objectMapper.configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);
        this.objectMapper.configure(SerializationFeature.INDENT_OUTPUT, false);
    }
    
    public static void main(String[] args) {
        TestResultAnalyzer analyzer = new TestResultAnalyzer();
        
        try {
            if (args.length > 0 && "--fix-sorting".equals(args[0])) {
                // Automatic sorting difference fix mode
                analyzer.fixSortingDifferences();
            } else {
                // Normal analysis mode
                System.out.println("=== Oracle vs PostgreSQL Test Result Analysis ===\n");
                
                // 1. PostgreSQL Execute SQL Failed analysis
                analyzer.analyzePostgreSQLErrors();
                
                System.out.println("\n" + "=".repeat(80) + "\n");
                
                // 2. sqllist table same='N' case analysis
                analyzer.analyzeSqlListDifferences();
            }
        } catch (Exception e) {
            System.err.println("Error occurred during analysis: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    /**
     * 1. PostgreSQL SQL execution failure error analysis
     */
    private void analyzePostgreSQLErrors() throws Exception {
        System.out.println("📊 1. PostgreSQL SQL execution failure error analysis");
        System.out.println("-".repeat(50));
        
        // Find latest PostgreSQL result file
        String resultFile = findLatestPostgreSQLResultFile();
        if (resultFile == null) {
            System.out.println("✅ No PostgreSQL SQL execution failures. (All SQL executed successfully)");
            return;
        }
        
        System.out.println("📄 Analysis file: " + resultFile);
        
        // Parse JSON file
        JsonNode rootNode = objectMapper.readTree(new File(resultFile));
        JsonNode failedTests = rootNode.get("failedTests");
        
        if (failedTests == null || !failedTests.isArray() || failedTests.size() == 0) {
            System.out.println("✅ No PostgreSQL SQL execution failures.");
            return;
        }
        
        // Classify by error type
        Map<String, List<FailedTest>> errorTypeMap = new LinkedHashMap<>();
        
        for (JsonNode failedTest : failedTests) {
            String xmlFile = failedTest.get("xmlFile").asText();
            String sqlId = failedTest.get("sqlId").asText();
            String errorMessage = failedTest.get("errorMessage").asText();
            
            String errorType = categorizeError(errorMessage);
            
            errorTypeMap.computeIfAbsent(errorType, k -> new ArrayList<>())
                       .add(new FailedTest(xmlFile, sqlId, errorMessage));
        }
        
        // Output results
        System.out.println("\n🔍 Error type analysis results:");
        System.out.println("Total failed SQL count: " + failedTests.size() + "\n");
        
        int typeIndex = 1;
        for (Map.Entry<String, List<FailedTest>> entry : errorTypeMap.entrySet()) {
            String errorType = entry.getKey();
            List<FailedTest> tests = entry.getValue();
            
            System.out.println(typeIndex + ". " + errorType + " (" + tests.size() + ")");
            System.out.println("   " + "-".repeat(40));
            
            for (FailedTest test : tests) {
                System.out.println("   📁 " + test.xmlFile + " → " + test.sqlId);
                System.out.println("      💬 " + extractErrorSummary(test.errorMessage));
                System.out.println();
            }
            typeIndex++;
        }
        
        // Q Chat analysis request removed (unnecessary)
    }
    
    /**
     * 2. sqllist table same='N' case analysis
     */
    private void analyzeSqlListDifferences() throws Exception {
        System.out.println("📊 2. sqllist table same='N' case analysis");
        System.out.println("-".repeat(50));
        
        // Read DB type from environment variables
        String srcDbType = System.getenv("SOURCE_DBMS_TYPE");
        String tgtDbType = System.getenv("TARGET_DBMS_TYPE");
        
        if (srcDbType == null) srcDbType = "Source";
        if (tgtDbType == null) tgtDbType = "Target";
        
        System.out.println("🔍 DB type: " + srcDbType + " vs " + tgtDbType + "\n");
        
        try (Connection conn = DriverManager.getConnection(POSTGRES_URL, POSTGRES_USER, POSTGRES_PASSWORD)) {
            
            // Query same='N' cases
            String sql = """
                SELECT sql_id, src_result, tgt_result, src_path, tgt_path,
                       LENGTH(src_result) as src_length,
                       LENGTH(tgt_result) as tgt_length
                FROM oma.sqllist 
                WHERE same = 'N' 
                AND src_result IS NOT NULL 
                AND tgt_result IS NOT NULL
                ORDER BY sql_id
                """;
            
            List<SqlDifference> lengthDifferent = new ArrayList<>();
            List<SqlDifference> sortingDifferent = new ArrayList<>();
            List<SqlDifference> contentDifferent = new ArrayList<>();
            
            try (PreparedStatement pstmt = conn.prepareStatement(sql);
                 ResultSet rs = pstmt.executeQuery()) {
                
                while (rs.next()) {
                    String sqlId = rs.getString("sql_id");
                    String srcResult = rs.getString("src_result");
                    String tgtResult = rs.getString("tgt_result");
                    String srcPath = rs.getString("src_path");
                    String tgtPath = rs.getString("tgt_path");
                    int srcLength = rs.getInt("src_length");
                    int tgtLength = rs.getInt("tgt_length");
                    
                    SqlDifference diff = new SqlDifference(sqlId, srcResult, tgtResult, srcLength, tgtLength, srcPath, tgtPath);
                    
                    if (srcLength != tgtLength) {
                        // Different lengths: Results differ
                        lengthDifferent.add(diff);
                    } else {
                        // Same length: Compare after JSON sorting
                        if (compareJsonAfterSorting(srcResult, tgtResult)) {
                            sortingDifferent.add(diff);
                        } else {
                            contentDifferent.add(diff);
                        }
                    }
                }
            }
            
            // Output results
            System.out.println("\n🔍 same='N' case analysis results:");
            System.out.println("Total analysis targets: " + (lengthDifferent.size() + sortingDifferent.size() + contentDifferent.size()) + "\n");
            
            // 1. Results differ (length difference + content difference)
            List<SqlDifference> allDifferent = new ArrayList<>();
            allDifferent.addAll(lengthDifferent);
            allDifferent.addAll(contentDifferent);
            
            System.out.println("1. Results differ - " + allDifferent.size());
            System.out.println("   " + "-".repeat(50));
            for (SqlDifference diff : allDifferent) {
                String[] parts = diff.sqlId.split("\\.");
                String mapper = parts.length > 1 ? parts[0] : "Unknown";
                String sqlIdOnly = parts.length > 1 ? parts[1] : diff.sqlId;
                
                if (diff.srcLength != diff.tgtLength) {
                    System.out.println("   📁 " + mapper + " → " + sqlIdOnly + 
                                     " (length difference: " + srcDbType + " " + diff.srcLength + " bytes, " + tgtDbType + " " + diff.tgtLength + " bytes)");
                } else {
                    System.out.println("   📁 " + mapper + " → " + sqlIdOnly + " (content difference)");
                }
                System.out.println("      📂 " + srcDbType + ": " + (diff.srcPath != null ? diff.srcPath : "N/A"));
                System.out.println("      📂 " + tgtDbType + ": " + (diff.tgtPath != null ? diff.tgtPath : "N/A"));
                System.out.println();
            }
            
            // 2. Sorting difference
            System.out.println("2. Sorting difference - " + sortingDifferent.size());
            System.out.println("   " + "-".repeat(50));
            for (SqlDifference diff : sortingDifferent) {
                String[] parts = diff.sqlId.split("\\.");
                String mapper = parts.length > 1 ? parts[0] : "Unknown";
                String sqlIdOnly = parts.length > 1 ? parts[1] : diff.sqlId;
                System.out.println("   📁 " + mapper + " → " + sqlIdOnly);
                System.out.println("      📂 " + srcDbType + ": " + (diff.srcPath != null ? diff.srcPath : "N/A"));
                System.out.println("      📂 " + tgtDbType + ": " + (diff.tgtPath != null ? diff.tgtPath : "N/A"));
                System.out.println();
            }
            
            // Summary statistics
            System.out.println("\n📈 Analysis summary:");
            System.out.println("   • Results differ: " + allDifferent.size() + " (length difference: " + lengthDifferent.size() + ", content difference: " + contentDifferent.size() + ")");
            System.out.println("   • Sorting difference (actually identical): " + sortingDifferent.size());
            if (sortingDifferent.size() > 0) {
                System.out.println("   • Potential success rate improvement: +" + sortingDifferent.size());
            }
        }
    }
    
    /**
     * Compare after JSON sorting - sort only results array
     */
    private boolean compareJsonAfterSorting(String json1, String json2) {
        try {
            JsonNode node1 = objectMapper.readTree(json1);
            JsonNode node2 = objectMapper.readTree(json2);
            
            // Extract results array
            JsonNode results1 = node1.get("results");
            JsonNode results2 = node2.get("results");
            
            if (results1 == null || results2 == null) {
                return false; // Treat as different if results are missing
            }
            
            if (!results1.isArray() || !results2.isArray()) {
                return false; // Treat as different if not arrays
            }
            
            // Sort and compare only results arrays
            ArrayNode sortedResults1 = sortJsonArray((ArrayNode) results1);
            ArrayNode sortedResults2 = sortJsonArray((ArrayNode) results2);
            
            // Convert sorted results arrays to strings and compare
            String sortedStr1 = objectMapper.writeValueAsString(sortedResults1);
            String sortedStr2 = objectMapper.writeValueAsString(sortedResults2);
            
            return sortedStr1.equals(sortedStr2);
            
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * Sort JSON array - convert each object to normalized string and sort
     */
    private ArrayNode sortJsonArray(ArrayNode arrayNode) {
        List<JsonNode> nodeList = new ArrayList<>();
        arrayNode.forEach(nodeList::add);
        
        // Sort by converting each JSON object to normalized string
        nodeList.sort((a, b) -> {
            try {
                // Normalize by sorting keys within objects
                String strA = objectMapper.writeValueAsString(a);
                String strB = objectMapper.writeValueAsString(b);
                return strA.compareTo(strB);
            } catch (Exception e) {
                return 0;
            }
        });
        
        ArrayNode sortedArray = objectMapper.createArrayNode();
        nodeList.forEach(sortedArray::add);
        return sortedArray;
    }
    
    /**
     * Compare after sorting entire JSON
     */
    private boolean sortJsonAndCompare(JsonNode node1, JsonNode node2) {
        try {
            String sorted1 = objectMapper.writeValueAsString(node1);
            String sorted2 = objectMapper.writeValueAsString(node2);
            return sorted1.equals(sorted2);
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * Categorize error types
     */
    private String categorizeError(String errorMessage) {
        if (errorMessage.contains("operator does not exist")) {
            return "Data type casting error";
        } else if (errorMessage.contains("cannot cast type integer to interval")) {
            return "Date/time processing error (INTERVAL casting)";
        } else if (errorMessage.contains("invalid input syntax for type integer")) {
            return "Data type input error";
        } else if (errorMessage.contains("recursive reference to query")) {
            return "Recursive query syntax error";
        } else if (errorMessage.contains("relation") && errorMessage.contains("does not exist")) {
            return "Table/view does not exist";
        } else if (errorMessage.contains("function") && errorMessage.contains("does not exist")) {
            return "Function does not exist";
        } else {
            return "Other errors";
        }
    }
    
    /**
     * Automatic fix for sorting differences
     */
    private void fixSortingDifferences() throws Exception {
        System.out.println("🔧 Automatic sorting difference fix started...");
        
        try (Connection conn = DriverManager.getConnection(POSTGRES_URL, POSTGRES_USER, POSTGRES_PASSWORD)) {
            
            // Query sorting difference cases (same length but different content)
            String sql = """
                SELECT sql_id, src_result, tgt_result, tgt_path
                FROM oma.sqllist 
                WHERE same = 'N' 
                AND src_result IS NOT NULL 
                AND tgt_result IS NOT NULL
                AND LENGTH(src_result) = LENGTH(tgt_result)
                ORDER BY sql_id
                """;
            
            int fixedCount = 0;
            
            try (PreparedStatement pstmt = conn.prepareStatement(sql);
                 ResultSet rs = pstmt.executeQuery()) {
                
                while (rs.next()) {
                    String sqlId = rs.getString("sql_id");
                    String srcResult = rs.getString("src_result");
                    String tgtResult = rs.getString("tgt_result");
                    String tgtPath = rs.getString("tgt_path");
                    
                    // Check if it's a sorting difference by comparing after JSON sorting
                    if (compareJsonAfterSorting(srcResult, tgtResult)) {
                        System.out.println("📝 Fixing sorting difference: " + sqlId);
                        
                        if (addOrderByToSql(tgtPath, sqlId)) {
                            fixedCount++;
                            System.out.println("   ✅ ORDER BY addition completed");
                        } else {
                            System.out.println("   ❌ Fix failed");
                        }
                    }
                }
            }
            
            System.out.println("\n✅ Automatic sorting difference fix completed: " + fixedCount + " fixed");
        }
    }
    
    /**
     * Add ORDER BY to corresponding SQL in XML file
     */
    private boolean addOrderByToSql(String xmlPath, String fullSqlId) {
        try {
            String[] parts = fullSqlId.split("\\.");
            if (parts.length < 2) return false;
            
            String sqlIdOnly = parts[1];
            
            // Read XML file
            String content = Files.readString(Paths.get(xmlPath));
            
            // Find SQL tag
            String pattern = "(<(select|insert|update|delete)[^>]*id\\s*=\\s*[\"']" + sqlIdOnly + "[\"'][^>]*>)(.*?)(</\\2>)";
            java.util.regex.Pattern p = java.util.regex.Pattern.compile(pattern, java.util.regex.Pattern.CASE_INSENSITIVE | java.util.regex.Pattern.DOTALL);
            java.util.regex.Matcher m = p.matcher(content);
            
            if (m.find()) {
                String openTag = m.group(1);
                String sqlContent = m.group(3);
                String closeTag = m.group(4);
                
                // Check if it's a SELECT statement
                if (openTag.toLowerCase().contains("<select")) {
                    // More accurately check if ORDER BY already exists (considering CDATA, comments, etc.)
                    String cleanSqlContent = sqlContent.replaceAll("<!\\[CDATA\\[.*?\\]\\]>", "")
                                                      .replaceAll("<!--.*?-->", "");
                    
                    if (!cleanSqlContent.toLowerCase().matches(".*\\border\\s+by\\b.*")) {
                        // Add ORDER BY 1 at the very end
                        sqlContent = sqlContent.trim();
                        if (sqlContent.endsWith(";")) {
                            sqlContent = sqlContent.substring(0, sqlContent.length() - 1) + "\n        ORDER BY 1;";
                        } else {
                            sqlContent = sqlContent + "\n        ORDER BY 1";
                        }
                        
                        String newContent = content.replace(m.group(0), openTag + sqlContent + closeTag);
                        Files.writeString(Paths.get(xmlPath), newContent);
                        return true;
                    } else {
                        System.out.println("   ⚠️  ORDER BY already exists");
                        return false;
                    }
                }
            }
            
            return false;
            
        } catch (Exception e) {
            System.err.println("ORDER BY addition failed: " + e.getMessage());
            return false;
        }
    }
    
    /**
     * Extract error message summary
     */
    private String extractErrorSummary(String errorMessage) {
        String[] lines = errorMessage.split("\n");
        for (String line : lines) {
            if (line.contains("ERROR:")) {
                return line.trim();
            }
        }
        return "No error information";
    }
    
    /**
     * Find latest PostgreSQL result file
     */
    private String findLatestPostgreSQLResultFile() {
        try {
            Path currentDir = Paths.get(".");
            return Files.list(currentDir)
                    .filter(path -> path.getFileName().toString().startsWith("bulk_test_result_"))
                    .filter(path -> path.getFileName().toString().endsWith(".json"))
                    .max(Comparator.comparing(path -> path.getFileName().toString()))
                    .map(Path::toString)
                    .orElse(null);
        } catch (Exception e) {
            return null;
        }
    }
    
    // generateQChatAnalysisRequest 메서드 제거됨
    
    // Inner classes
    static class FailedTest {
        String xmlFile;
        String sqlId;
        String errorMessage;
        
        FailedTest(String xmlFile, String sqlId, String errorMessage) {
            this.xmlFile = xmlFile;
            this.sqlId = sqlId;
            this.errorMessage = errorMessage;
        }
    }
    
    static class SqlDifference {
        String sqlId;
        String srcResult;
        String tgtResult;
        int srcLength;
        int tgtLength;
        String srcPath;
        String tgtPath;
        
        SqlDifference(String sqlId, String srcResult, String tgtResult, int srcLength, int tgtLength, String srcPath, String tgtPath) {
            this.sqlId = sqlId;
            this.srcResult = srcResult;
            this.tgtResult = tgtResult;
            this.srcLength = srcLength;
            this.tgtLength = tgtLength;
            this.srcPath = srcPath;
            this.tgtPath = tgtPath;
        }
    }
}
