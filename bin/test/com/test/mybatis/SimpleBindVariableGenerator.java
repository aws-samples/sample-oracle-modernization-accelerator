package com.test.mybatis;

import java.io.*;
import java.sql.*;
import java.util.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.regex.Pattern;
import java.util.regex.Matcher;

/**
 * Simple and reliable bind variable generator
 * Oracle Dictionary + Mapper bind variable extraction + Matching + mismatch.lst generation
 */
public class SimpleBindVariableGenerator {
    
    // Oracle connection information
    // Oracle connection information
    private static final String ORACLE_HOST = System.getenv("ORACLE_HOST");
    private static final String ORACLE_PORT = System.getenv().getOrDefault("ORACLE_PORT", "1521");
    private static final String ORACLE_SVC_USER = System.getenv("ORACLE_SVC_USER");
    private static final String ORACLE_SVC_PASSWORD = System.getenv("ORACLE_SVC_PASSWORD");
    private static final String SERVICE_NAME = System.getenv("SERVICE_NAME");
    private static final String ORACLE_SVC_CONNECT_STRING = System.getenv("ORACLE_SVC_CONNECT_STRING");
    
    private Map<String, BindVariable> bindVariables = new HashMap<>();
    private Map<String, Map<String, Map<String, ColumnInfo>>> dictionary = new HashMap<>();
    
    public static void main(String[] args) {
        String mapperDir = args.length > 0 ? args[0] : "/home/ec2-user/workspace/src-orcl/src/main/resources/sqlmap/mapper";
        String testFolder = args.length > 1 ? args[1] : mapperDir;
        new SimpleBindVariableGenerator().run(mapperDir, testFolder);
    }
    
    private void run(String mapperDir, String testFolder) {
        System.out.println("=== Simple Bind Variable Generator ===\n");
        
        try {
            // 1. Collect Oracle dictionary
            collectOracleDictionary();
            
            // 2. Extract bind variables from mappers
            extractBindVariables(mapperDir);
            
            // 3. Match with dictionary
            matchWithDictionary();
            
            // 4. Generate files
            generateFiles(testFolder);
            
            System.out.println("✓ Completed!");
            
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private void collectOracleDictionary() throws Exception {
        System.out.println("Step 1: Collecting Oracle dictionary...");
        
        try {
            // Use SERVICE_NAME environment variable
            String url = String.format("jdbc:oracle:thin:@%s:%s/%s", ORACLE_HOST, ORACLE_PORT, SERVICE_NAME);
            System.out.println("Attempting Oracle connection: " + url);
            
            try (Connection conn = DriverManager.getConnection(url, ORACLE_SVC_USER, ORACLE_SVC_PASSWORD)) {
                System.out.println("✓ Oracle DB connection successful");
                
                String sql = "SELECT OWNER, TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM ALL_TAB_COLUMNS " +
                            "WHERE OWNER = ? ORDER BY OWNER, TABLE_NAME, COLUMN_ID";
                
                try (PreparedStatement pstmt = conn.prepareStatement(sql)) {
                    pstmt.setString(1, ORACLE_SVC_USER);
                    
                    try (ResultSet rs = pstmt.executeQuery()) {
                        int count = 0;
                        while (rs.next()) {
                            String owner = rs.getString("OWNER");
                            String tableName = rs.getString("TABLE_NAME");
                            String columnName = rs.getString("COLUMN_NAME");
                            String dataType = rs.getString("DATA_TYPE");
                            
                            dictionary.computeIfAbsent(owner, k -> new HashMap<>())
                                     .computeIfAbsent(tableName, k -> new HashMap<>())
                                     .put(columnName, new ColumnInfo(dataType, null));
                            count++;
                        }
                        
                        System.out.printf("✓ Oracle dictionary collection completed (%d columns)\n\n", count);
                    }
                }
            }
        } catch (Exception e) {
            System.out.println("❌ Oracle dictionary collection failed: " + e.getMessage());
            System.out.println("Please check Oracle connection information.");
            throw e;
        }
    }
    
    private void extractBindVariables(String mapperDir) throws Exception {
        System.out.println("Step 2: Extracting bind variables from mappers...");
        
        File dir = new File(mapperDir);
        if (!dir.exists()) {
            throw new Exception("Mapper directory not found: " + mapperDir);
        }
        
        List<File> xmlFiles = findXmlFiles(dir);
        System.out.printf("XML files found: %d\n", xmlFiles.size());
        
        Pattern bindPattern = Pattern.compile("#\\{([^}]+)\\}|\\$\\{([^}]+)\\}");
        
        for (File xmlFile : xmlFiles) {
            try (BufferedReader reader = new BufferedReader(new FileReader(xmlFile))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    Matcher matcher = bindPattern.matcher(line);
                    while (matcher.find()) {
                        String varName = matcher.group(1) != null ? matcher.group(1) : matcher.group(2);
                        
                        // Handle composite variable names (user.name -> user)
                        if (varName.contains(".")) {
                            varName = varName.split("\\.")[0];
                        }
                        
                        bindVariables.computeIfAbsent(varName, k -> new BindVariable(k))
                                    .addFile(xmlFile.getAbsolutePath());
                    }
                }
            }
        }
        
        System.out.printf("✓ Bind variable extraction completed (%d variables)\n\n", bindVariables.size());
    }
    
    private List<File> findXmlFiles(File dir) {
        List<File> xmlFiles = new ArrayList<>();
        
        File[] files = dir.listFiles();
        if (files != null) {
            for (File file : files) {
                if (file.isDirectory()) {
                    xmlFiles.addAll(findXmlFiles(file));
                } else if (file.getName().endsWith(".xml")) {
                    xmlFiles.add(file);
                }
            }
        }
        
        return xmlFiles;
    }
    
    private void matchWithDictionary() {
        System.out.println("Step 3: Matching with dictionary...");
        
        int matchedCount = 0;
        
        for (BindVariable bindVar : bindVariables.values()) {
            String varName = bindVar.getName().toLowerCase();
            
            // Find matching columns in dictionary
            for (String schema : dictionary.keySet()) {
                for (String tableName : dictionary.get(schema).keySet()) {
                    for (String columnName : dictionary.get(schema).get(tableName).keySet()) {
                        if (isMatch(varName, columnName.toLowerCase())) {
                            ColumnInfo colInfo = dictionary.get(schema).get(tableName).get(columnName);
                            String matchedColumn = schema + "." + tableName + "." + columnName;
                            bindVar.setMatchedColumn(matchedColumn);
                            bindVar.setValue(generateValueByDataType(colInfo.dataType, varName));
                            matchedCount++;
                            break;
                        }
                    }
                    if (bindVar.getMatchedColumn() != null) break;
                }
                if (bindVar.getMatchedColumn() != null) break;
            }
            
            // Generate default value for unmatched cases
            if (bindVar.getMatchedColumn() == null) {
                bindVar.setValue(generateDefaultValue(varName));
            }
        }
        
        System.out.printf("✓ Matching completed (matched: %d, unmatched: %d)\n\n", 
                         matchedCount, bindVariables.size() - matchedCount);
    }
    
    private boolean isMatch(String varName, String columnName) {
        // Exact matching
        if (varName.equals(columnName)) return true;
        
        // Underscore to camelCase matching
        String camelCaseColumn = underscoreToCamelCase(columnName);
        if (varName.equals(camelCaseColumn.toLowerCase())) return true;
        
        // CamelCase to underscore matching
        String underscoreVar = camelCaseToUnderscore(varName);
        if (underscoreVar.equals(columnName.toUpperCase())) return true;
        
        // Partial matching
        if (varName.contains(columnName) || columnName.contains(varName)) return true;
        
        // ID matching
        if (varName.endsWith("id") && columnName.endsWith("_id")) return true;
        if (varName.contains("id") && columnName.contains("id")) return true;
        
        return false;
    }
    
    private String underscoreToCamelCase(String underscore) {
        StringBuilder result = new StringBuilder();
        boolean capitalizeNext = false;
        
        for (char c : underscore.toLowerCase().toCharArray()) {
            if (c == '_') {
                capitalizeNext = true;
            } else {
                if (capitalizeNext) {
                    result.append(Character.toUpperCase(c));
                    capitalizeNext = false;
                } else {
                    result.append(c);
                }
            }
        }
        
        return result.toString();
    }
    
    private String camelCaseToUnderscore(String camelCase) {
        StringBuilder result = new StringBuilder();
        
        for (char c : camelCase.toCharArray()) {
            if (Character.isUpperCase(c)) {
                if (result.length() > 0) {
                    result.append('_');
                }
                result.append(Character.toLowerCase(c));
            } else {
                result.append(c);
            }
        }
        
        return result.toString().toUpperCase();
    }
    
    private String generateValueByDataType(String dataType, String varName) {
        switch (dataType.toUpperCase()) {
            case "NUMBER":
                if (varName.contains("id")) return "1";
                if (varName.contains("amount") || varName.contains("price")) return "1000";
                if (varName.contains("year")) return "2025";
                return "1";
            case "VARCHAR2":
            case "CHAR":
                if (varName.contains("status")) return "'ACTIVE'";
                if (varName.contains("email")) return "'test@example.com'";
                return "'TEST_" + varName.toUpperCase() + "'";
            case "DATE":
                return "'2025-08-24'";
            case "TIMESTAMP":
                return "'2025-08-24 10:30:00'";
            default:
                return "'DEFAULT_VALUE'";
        }
    }
    
    private String generateDefaultValue(String varName) {
        String lower = varName.toLowerCase();
        
        if (lower.contains("id")) return "1";
        if (lower.contains("year")) return "2025";
        if (lower.contains("amount") || lower.contains("price")) return "1000";
        if (lower.contains("probability") || lower.contains("score")) return "75";
        if (lower.contains("days")) return "30";
        if (lower.contains("limit")) return "10";
        if (lower.contains("offset")) return "0";
        if (lower.contains("status")) return "'ACTIVE'";
        if (lower.contains("email")) return "'test@example.com'";
        if (lower.contains("name")) return "'TEST_" + varName.toUpperCase() + "'";
        if (lower.contains("date")) return "'2025-08-24'";
        
        return "'DEFAULT_" + varName.toUpperCase() + "'";
    }
    
    private void generateFiles(String testFolder) throws Exception {
        System.out.println("Step 4: Generating files...");
        
        // Separate matched and unmatched variables
        List<String> matchedVars = new ArrayList<>();
        List<String> unmatchedVars = new ArrayList<>();
        
        for (String varName : bindVariables.keySet()) {
            if (bindVariables.get(varName).getMatchedColumn() != null) {
                matchedVars.add(varName);
            } else {
                unmatchedVars.add(varName);
            }
        }
        
        Collections.sort(matchedVars);
        Collections.sort(unmatchedVars);
        
        // parameters.properties File generation
        String parametersFile = testFolder + "/parameters.properties";
        try (PrintWriter writer = new PrintWriter(new FileWriter(parametersFile))) {
            writer.println("# Bind variable parameter file");
            writer.println("# Generated: " + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
            writer.println("# Total variables: " + bindVariables.size() + " (matched: " + matchedVars.size() + ", unmatched: " + unmatchedVars.size() + ")");
            writer.println();
            
            // Matched variables
            if (!matchedVars.isEmpty()) {
                writer.println("# =============================================================================");
                writer.println("# Matched variables (matched with Oracle DB columns)");
                writer.println("# =============================================================================");
                writer.println();
                
                for (String varName : matchedVars) {
                    BindVariable bindVar = bindVariables.get(varName);
                    writer.println("# " + bindVar.getMatchedColumn());
                    writer.println(varName + "=" + bindVar.getValue());
                    writer.println();
                }
            }
            
            // Unmatched variables
            if (!unmatchedVars.isEmpty()) {
                writer.println("# =============================================================================");
                writer.println("# Unmatched variables (please set values manually)");
                writer.println("# =============================================================================");
                writer.println();
                
                for (String varName : unmatchedVars) {
                    BindVariable bindVar = bindVariables.get(varName);
                    writer.println(varName + "=" + bindVar.getValue());
                }
            }
        }
        
        // mismatch.lst File generation
        if (!unmatchedVars.isEmpty()) {
            new File("out").mkdirs();
            
            try (PrintWriter writer = new PrintWriter(new FileWriter("out/mismatch.lst"))) {
                writer.println("# Unmatched bind variable location information");
                writer.println("# Generated: " + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
                writer.println("# Format: Variable name | Mapper file | Line number | SQL context");
                writer.println();
                
                for (String varName : unmatchedVars) {
                    BindVariable bindVar = bindVariables.get(varName);
                    writer.println("=== " + varName + " ===");
                    
                    for (String xmlFile : bindVar.getFiles()) {
                        findVariableInFile(xmlFile, varName, writer);
                    }
                    writer.println();
                }
            }
        }
        
        System.out.printf("✓ parameters.properties generation completed (%d variables)\n", bindVariables.size());
        System.out.printf("  - Matched: %d\n", matchedVars.size());
        System.out.printf("  - Unmatched: %d\n", unmatchedVars.size());
        
        if (!unmatchedVars.isEmpty()) {
            System.out.println("✓ out/mismatch.lst generation completed");
        }
    }
    
    private void findVariableInFile(String xmlFile, String varName, PrintWriter writer) {
        try (BufferedReader reader = new BufferedReader(new FileReader(xmlFile))) {
            String line;
            int lineNumber = 0;
            
            while ((line = reader.readLine()) != null) {
                lineNumber++;
                
                if (line.contains("#{" + varName + "}") || line.contains("${" + varName + "}")) {
                    String relativePath = getRelativePath(xmlFile);
                    String context = line.trim();
                    
                    writer.printf("%s | %s | Line %d | %s%n", 
                                varName, relativePath, lineNumber, context);
                }
            }
        } catch (Exception e) {
            // Ignore
        }
    }
    
    private String getRelativePath(String absolutePath) {
        // Return absolute path
        return absolutePath;
    }
    
    // Inner classes
    static class BindVariable {
        private String name;
        private List<String> files = new ArrayList<>();
        private String value;
        private String matchedColumn;
        
        BindVariable(String name) {
            this.name = name;
        }
        
        void addFile(String file) {
            if (!files.contains(file)) {
                files.add(file);
            }
        }
        
        String getName() { return name; }
        List<String> getFiles() { return files; }
        String getValue() { return value; }
        void setValue(String value) { this.value = value; }
        String getMatchedColumn() { return matchedColumn; }
        void setMatchedColumn(String matchedColumn) { this.matchedColumn = matchedColumn; }
    }
    
    static class ColumnInfo {
        String dataType;
        String sampleData;
        
        ColumnInfo(String dataType, String sampleData) {
            this.dataType = dataType;
            this.sampleData = sampleData;
        }
    }
}
