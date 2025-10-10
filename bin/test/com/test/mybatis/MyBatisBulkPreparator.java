package com.test.mybatis;

import java.io.*;
import java.nio.file.*;
import java.sql.*;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Program to recursively search MyBatis XML files and extract all parameters
 * Added DB sample value collection functionality
 */
public class MyBatisBulkPreparator {
    
    private static final Pattern PARAM_PATTERN = Pattern.compile("(#\\{[^}]+\\}|\\$\\{[^}]+\\})");
    private static final String OUTPUT_FILENAME = "parameters.properties";
    private static final String DEFAULT_PARAMS_FILE = "default.parameters";
    // Set METADATA_FILE path dynamically
    
    private static String getOutputFilePath() {
        String testFolder = System.getenv("TEST_FOLDER");
        return testFolder != null ? testFolder + "/" + OUTPUT_FILENAME : OUTPUT_FILENAME;
    }
    
    public static void main(String[] args) {
        if (args.length < 1) {
            printUsage();
            return;
        }
        
        String directoryPath = args[0];
        String dbType = null;
        String dateFormat = "YYYY-MM-DD";
        
        // Option parsing
        for (int i = 1; i < args.length; i++) {
            switch (args[i]) {
                case "--db":
                    if (i + 1 < args.length) {
                        dbType = args[++i];
                    } else {
                        System.err.println("Error: Please specify database type for --db option.");
                        return;
                    }
                    break;
                case "--date-format":
                    if (i + 1 < args.length) {
                        dateFormat = args[++i];
                    } else {
                        System.err.println("Error: Please specify date format for --date-format option.");
                        return;
                    }
                    break;
            }
        }
        
        MyBatisBulkPreparator preparator = new MyBatisBulkPreparator();
        if (dbType != null) {
            preparator.extractParametersWithDbSamples(directoryPath, dbType, dateFormat);
        } else {
            preparator.extractAllParameters(directoryPath);
        }
    }
    
    private static void printUsage() {
        System.out.println("Usage: java MyBatisBulkPreparator <directory_path> [options]");
        System.out.println("Options:");
        System.out.println("  --db <type>           Database type (oracle, mysql, postgresql)");
        System.out.println("  --date-format <fmt>   Date format (default: YYYY-MM-DD)");
        System.out.println();
        System.out.println("Examples:");
        System.out.println("  java MyBatisBulkPreparator /path/to/mappers");
        System.out.println("  java MyBatisBulkPreparator /path/to/mappers --db postgresql");
        System.out.println("  java MyBatisBulkPreparator /path/to/mappers --db oracle --date-format YYYY/MM/DD");
        System.out.println();
        System.out.println("Environment variable setup:");
        System.out.println("  Oracle: ORACLE_SVC_USER, ORACLE_SVC_PASSWORD, ORACLE_SVC_CONNECT_STRING");
        System.out.println("  MySQL: MYSQL_ADM_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_TCP_PORT, MYSQL_DB");
        System.out.println("  PostgreSQL: PGUSER, PGPASSWORD, PGHOST, PGPORT, PGDATABASE");
    }
    
    /**
     * Extract parameters with DB sample values
     */
    public void extractParametersWithDbSamples(String directoryPath, String dbType, String dateFormat) {
        try {
            System.out.println("=== MyBatis Parameter Extraction + DB Sample Value Collection ===");
            System.out.println("Search directory: " + directoryPath);
            System.out.println("Database type: " + dbType.toUpperCase());
            System.out.println("Date format: " + dateFormat);
            System.out.println();
            
            // 1. Extract parameters
            Set<String> allParameters = extractParametersFromDirectory(directoryPath);
            
            // 2. Load metadata
            List<ColumnInfo> columns = loadMetadata(directoryPath);
            System.out.println("Columns found: " + columns.size());
            
            // 3. Parameter-column matching
            Map<String, List<ColumnInfo>> matches = findMatches(allParameters, columns);
            
            // 4. DB connection and sample value collection (includes default.parameters check)
            Map<String, SampleValue> sampleValues = collectSampleValues(matches, dbType, dateFormat);
            
            // 5. Load default values (for parameter file generation)
            Map<String, String> defaultValues = loadDefaultParameters();
            
            // 6. Generate parameter file (default values + DB sample values)
            generateParameterFileWithSamples(allParameters, defaultValues, sampleValues);
            
            // 7. Output results
            printSummary(allParameters, defaultValues, sampleValues);
            
        } catch (Exception e) {
            System.err.println("Error occurred: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    /**
     * Existing parameter extraction (no DB connection)
     */
    public void extractAllParameters(String directoryPath) {
        try {
            System.out.println("=== MyBatis Bulk Parameter Extraction Started ===");
            System.out.println("Search directory: " + directoryPath);
            
            Set<String> allParameters = extractParametersFromDirectory(directoryPath);
            generateParameterFile(allParameters);
            
            System.out.println("\n=== Completed ===");
            System.out.println("Parameter file: " + getOutputFilePath());
            System.out.println("Edit the file and then run with MyBatisBulkExecutor.");
            
        } catch (Exception e) {
            System.err.println("Error occurred: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    /**
     * Extract all parameters from directory
     */
    private Set<String> extractParametersFromDirectory(String directoryPath) throws IOException {
        // 1. Find XML files recursively
        List<Path> xmlFiles = findXmlFiles(Paths.get(directoryPath));
        System.out.println("XML files found: " + xmlFiles.size());
        
        // 2. Collect all parameters (remove duplicates, automatic sorting)
        Set<String> allParameters = new TreeSet<>();
        int totalSqlCount = 0;
        
        for (Path xmlFile : xmlFiles) {
            System.out.println("Processing: " + xmlFile.getFileName());
            int sqlCount = processXmlFile(xmlFile, allParameters);
            totalSqlCount += sqlCount;
        }
        
        // 3. Output results
        System.out.println("\n=== Extraction Results ===");
        System.out.println("Processed XML files: " + xmlFiles.size());
        System.out.println("Processed SQL statements: " + totalSqlCount);
        System.out.println("Unique parameters found: " + allParameters.size());
        
        if (!allParameters.isEmpty()) {
            System.out.println("\n=== Found Parameters (alphabetical order) ===");
            allParameters.forEach(param -> System.out.println("#{" + param + "}"));
        }
        
        return allParameters;
    }
    
    /**
     * Load metadata file
     */
    private List<ColumnInfo> loadMetadata(String mapperPath) throws IOException {
        List<ColumnInfo> columns = new ArrayList<>();
        
        // Find oma_metadata.txt file in APP_TRANSFORM_FOLDER
        String transformFolder = System.getenv("APP_TRANSFORM_FOLDER");
        String metadataFile;
        
        if (transformFolder != null && !transformFolder.isEmpty()) {
            metadataFile = transformFolder + "/oma_metadata.txt";
        } else {
            // If environment variable is not set, find in mapper path (existing method)
            metadataFile = mapperPath + "/oma_metadata.txt";
        }
        
        Path metadataPath = Paths.get(metadataFile);
        
        if (!Files.exists(metadataPath)) {
            System.out.println("⚠️  Metadata file not found: " + metadataFile);
            if (transformFolder != null) {
                System.out.println("   APP_TRANSFORM_FOLDER: " + transformFolder);
            }
            System.out.println("   Skipping DB sample value collection.");
            return columns;
        }
        
        try (BufferedReader reader = Files.newBufferedReader(metadataPath)) {
            String line;
            int lineCount = 0;
            
            while ((line = reader.readLine()) != null) {
                lineCount++;
                if (lineCount <= 2) continue; // Skip header
                
                line = line.trim();
                if (line.isEmpty()) continue;
                
                String[] parts = line.split("\\|");
                if (parts.length >= 4) {
                    ColumnInfo column = new ColumnInfo();
                    column.schema = parts[0].trim();
                    column.table = parts[1].trim();
                    column.column = parts[2].trim();
                    column.dataType = parts[3].trim();
                    
                    if (!column.schema.isEmpty() && !column.table.isEmpty() && 
                        !column.column.isEmpty() && !column.dataType.isEmpty()) {
                        columns.add(column);
                    }
                }
            }
        }
        
        return columns;
    }
    
    /**
     * Load default values from default.parameters file
     */
    private Map<String, String> loadDefaultParameters() {
        Map<String, String> defaultValues = new HashMap<>();
        
        try (BufferedReader reader = Files.newBufferedReader(Paths.get(DEFAULT_PARAMS_FILE))) {
            String line;
            int lineCount = 0;
            
            while ((line = reader.readLine()) != null) {
                lineCount++;
                line = line.trim();
                
                // Skip comments or empty lines
                if (line.isEmpty() || line.startsWith("#")) {
                    continue;
                }
                
                // Parse key=value format
                if (line.contains("=")) {
                    String[] parts = line.split("=", 2);
                    if (parts.length == 2) {
                        String key = parts[0].trim();
                        String value = parts[1].trim();
                        if (!key.isEmpty() && !value.isEmpty()) {
                            defaultValues.put(key, value);
                        }
                    }
                }
            }
            
            if (!defaultValues.isEmpty()) {
                System.out.println("Default values file loaded successfully: " + DEFAULT_PARAMS_FILE + " (" + defaultValues.size() + " values)");
            }
            
        } catch (IOException e) {
            System.out.println("Default values file not found: " + DEFAULT_PARAMS_FILE + " (skipped)");
        }
        
        return defaultValues;
    }
    
    /**
     * Match parameters with columns
     */
    private Map<String, List<ColumnInfo>> findMatches(Set<String> parameters, List<ColumnInfo> columns) {
        Map<String, List<ColumnInfo>> matches = new HashMap<>();
        
        for (String param : parameters) {
            String paramNormalized = normalizeName(param);
            List<ColumnInfo> matchingColumns = new ArrayList<>();
            
            for (ColumnInfo column : columns) {
                String columnNormalized = normalizeName(column.column);
                
                // Exact match
                if (paramNormalized.equals(columnNormalized)) {
                    column.matchType = "exact";
                    column.score = 100;
                    matchingColumns.add(column);
                }
                // Parameter contained in column name
                else if (columnNormalized.contains(paramNormalized)) {
                    ColumnInfo match = new ColumnInfo(column);
                    match.matchType = "param_in_column";
                    match.score = 80;
                    matchingColumns.add(match);
                }
                // Column name contained in parameter
                else if (paramNormalized.contains(columnNormalized)) {
                    ColumnInfo match = new ColumnInfo(column);
                    match.matchType = "column_in_param";
                    match.score = 70;
                    matchingColumns.add(match);
                }
            }
            
            // Sort by score
            matchingColumns.sort((a, b) -> Integer.compare(b.score, a.score));
            matches.put(param, matchingColumns);
        }
        
        return matches;
    }
    
    /**
     * Collect sample values from DB (exclude parameters that already have values in default.parameters)
     */
    private Map<String, SampleValue> collectSampleValues(Map<String, List<ColumnInfo>> matches, String dbType, String dateFormat) {
        Map<String, SampleValue> sampleValues = new HashMap<>();
        
        // Load default values from default.parameters file
        Map<String, String> defaultValues = loadDefaultParameters();
        
        try (Connection conn = createConnection(dbType)) {
            System.out.println("\n=== Collecting Sample Values ===");
            
            int processedCount = 0;
            int skippedCount = 0;
            
            for (Map.Entry<String, List<ColumnInfo>> entry : matches.entrySet()) {
                String param = entry.getKey();
                List<ColumnInfo> matchingColumns = entry.getValue();
                
                // Skip parameters that already have values set in default.parameters
                if (defaultValues.containsKey(param) && !defaultValues.get(param).trim().isEmpty()) {
                    skippedCount++;
                    System.out.printf("SKIP: %s (using default value: %s)%n", param, defaultValues.get(param));
                    continue;
                }
                
                if (!matchingColumns.isEmpty()) {
                    ColumnInfo bestMatch = matchingColumns.get(0);
                    // Process only exact matches or partial matches
                    if (bestMatch.matchType.equals("exact") || 
                        bestMatch.matchType.equals("param_in_column") || 
                        bestMatch.matchType.equals("column_in_param")) {
                        
                        processedCount++;
                        System.out.printf("%d. %s → %s.%s%n", processedCount, param, bestMatch.table, bestMatch.column);
                        
                        String sampleValue = getSampleValue(conn, bestMatch, dateFormat, dbType);
                        if (sampleValue != null) {
                            SampleValue sample = new SampleValue();
                            sample.value = sampleValue;
                            sample.source = bestMatch.table + "." + bestMatch.column;
                            sample.dataType = bestMatch.dataType;
                            sample.matchType = bestMatch.matchType;
                            
                            sampleValues.put(param, sample);
                            System.out.printf("   → Sample value: %s%n", sampleValue);
                        } else {
                            System.out.printf("   → No sample value (NULL or error)%n");
                        }
                    }
                }
            }
            
            if (skippedCount > 0) {
                System.out.printf("\nParameters skipped due to default values: %d%n", skippedCount);
            }
            
        } catch (Exception e) {
            System.err.println("Error during DB connection or sample value collection: " + e.getMessage());
            e.printStackTrace();
        }
        
        return sampleValues;
    }
    
    /**
     * Create DB connection (referenced by MyBatisBulkExecutorWithJson)
     */
    private Connection createConnection(String dbType) throws SQLException {
        switch (dbType.toLowerCase()) {
            case "oracle":
                return createOracleConnection();
            case "mysql":
                return createMySQLConnection();
            case "postgresql":
            case "pg":
                return createPostgreSQLConnection();
            default:
                throw new SQLException("Unsupported database type: " + dbType);
        }
    }
    
    private Connection createOracleConnection() throws SQLException {
        String connectString = System.getenv("ORACLE_SVC_CONNECT_STRING");
        String username = System.getenv("ORACLE_SVC_USER");
        String password = System.getenv("ORACLE_SVC_PASSWORD");
        String tnsAdmin = System.getenv("TNS_ADMIN");
        String oracleHome = System.getenv("ORACLE_HOME");
        
        if (username == null || password == null) {
            throw new SQLException("Oracle environment variables not set. Required variables: ORACLE_SVC_USER, ORACLE_SVC_PASSWORD");
        }
        
        // Automatic TNS_ADMIN setup (improved logic)
        if (tnsAdmin == null && oracleHome != null) {
            tnsAdmin = oracleHome + "/network/admin";
            System.setProperty("oracle.net.tns_admin", tnsAdmin);
            System.out.println("TNS_ADMIN automatically set: " + tnsAdmin);
        }
        
        String jdbcUrl;
        if (tnsAdmin != null && connectString != null) {
            // Use TNS name
            jdbcUrl = "jdbc:oracle:thin:@" + connectString;
        } else {
            // Basic connection method
            String defaultService = "orcl";
            jdbcUrl = "jdbc:oracle:thin:@" + (connectString != null ? connectString : defaultService);
        }
        
        System.out.println("Oracle connection info: " + username + "@" + jdbcUrl);
        
        return DriverManager.getConnection(jdbcUrl, username, password);
    }
    
    private Connection createMySQLConnection() throws SQLException {
        String host = System.getenv("MYSQL_HOST");
        String port = System.getenv("MYSQL_TCP_PORT");
        String database = System.getenv("MYSQL_DB");
        String username = System.getenv("MYSQL_ADM_USER");
        String password = System.getenv("MYSQL_PASSWORD");
        
        if (username == null || password == null) {
            throw new SQLException("MySQL environment variables not set. Required variables: MYSQL_ADM_USER, MYSQL_PASSWORD");
        }
        
        if (host == null) host = "localhost";
        if (port == null) port = "3306";
        if (database == null) database = "test";
        
        String jdbcUrl = String.format("jdbc:mysql://%s:%s/%s?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC", 
            host, port, database);
        System.out.println("MySQL connection info: " + username + "@" + jdbcUrl);
        
        return DriverManager.getConnection(jdbcUrl, username, password);
    }
    
    private Connection createPostgreSQLConnection() throws SQLException {
        String host = System.getenv("PGHOST");
        String port = System.getenv("PGPORT");
        String database = System.getenv("PGDATABASE");
        String username = System.getenv("PGUSER");
        String password = System.getenv("PGPASSWORD");
        
        if (username == null || password == null) {
            throw new SQLException("PostgreSQL environment variables not set. Required variables: PGUSER, PGPASSWORD");
        }
        
        if (host == null) host = "localhost";
        if (port == null) port = "5432";
        if (database == null) database = "postgres";
        
        String jdbcUrl = String.format("jdbc:postgresql://%s:%s/%s", host, port, database);
        System.out.println("PostgreSQL connection info: " + username + "@" + jdbcUrl);
        
        return DriverManager.getConnection(jdbcUrl, username, password);
    }
    
    /**
     * Get sample value from DB
     */
    private String getSampleValue(Connection conn, ColumnInfo column, String dateFormat, String dbType) {
        try {
            String query;
            
            // Apply format for date types
            if (isDateType(column.dataType)) {
                if (dbType.equalsIgnoreCase("postgresql")) {
                    query = String.format("SELECT TO_CHAR(%s, ?) as formatted_value FROM %s.%s WHERE %s IS NOT NULL LIMIT 1",
                        column.column, column.schema, column.table, column.column);
                } else if (dbType.equalsIgnoreCase("oracle")) {
                    query = String.format("SELECT TO_CHAR(%s, ?) as formatted_value FROM %s.%s WHERE %s IS NOT NULL AND ROWNUM <= 1",
                        column.column, column.schema, column.table, column.column);
                } else { // MySQL
                    query = String.format("SELECT DATE_FORMAT(%s, ?) as formatted_value FROM %s.%s WHERE %s IS NOT NULL LIMIT 1",
                        column.column, column.schema, column.table, column.column);
                }
                
                try (PreparedStatement stmt = conn.prepareStatement(query)) {
                    stmt.setString(1, convertDateFormat(dateFormat, dbType));
                    try (ResultSet rs = stmt.executeQuery()) {
                        if (rs.next()) {
                            return rs.getString(1);
                        }
                    }
                }
            } else {
                if (dbType.equalsIgnoreCase("postgresql")) {
                    query = String.format("SELECT %s FROM %s.%s WHERE %s IS NOT NULL LIMIT 1",
                        column.column, column.schema, column.table, column.column);
                } else if (dbType.equalsIgnoreCase("oracle")) {
                    query = String.format("SELECT %s FROM %s.%s WHERE %s IS NOT NULL AND ROWNUM <= 1",
                        column.column, column.schema, column.table, column.column);
                } else { // MySQL
                    query = String.format("SELECT %s FROM %s.%s WHERE %s IS NOT NULL LIMIT 1",
                        column.column, column.schema, column.table, column.column);
                }
                
                try (PreparedStatement stmt = conn.prepareStatement(query);
                     ResultSet rs = stmt.executeQuery()) {
                    if (rs.next()) {
                        Object value = rs.getObject(1);
                        return value != null ? value.toString().trim() : null;
                    }
                }
            }
            
        } catch (SQLException e) {
            System.out.printf("  error: %s.%s.%s - %s%n", column.schema, column.table, column.column, e.getMessage());
        }
        
        return null;
    }
    
    /**
     * Convert date format (by DB type)
     */
    private String convertDateFormat(String format, String dbType) {
        if (dbType.equalsIgnoreCase("mysql")) {
            // Convert to MySQL DATE_FORMAT format
            return format.replace("YYYY", "%Y")
                        .replace("MM", "%m")
                        .replace("DD", "%d")
                        .replace("HH24", "%H")
                        .replace("MI", "%i")
                        .replace("SS", "%s");
        }
        // PostgreSQL and Oracle use the same format
        return format;
    }
    
    /**
     * Check date/time type
     */
    private boolean isDateType(String dataType) {
        String lowerType = dataType.toLowerCase();
        return lowerType.contains("timestamp") || lowerType.contains("date") || lowerType.contains("time");
    }
    
    /**
     * Normalize name
     */
    private String normalizeName(String name) {
        return name.toLowerCase().replaceAll("[_\\s]", "");
    }
    
    /**
     * Generate parameter file with sample values
     */
    private void generateParameterFileWithSamples(Set<String> parameters, Map<String, String> defaultValues, Map<String, SampleValue> sampleValues) throws IOException {
        try (PrintWriter writer = new PrintWriter(new FileWriter(getOutputFilePath()))) {
            writer.println("# MyBatis parameter configuration file (includes default values + DB sample values)");
            writer.println("# Generated: " + new java.util.Date());
            writer.println("# Priority: DB sample values > default values > empty values");
            writer.println();
            
            // Output unmatched parameters first
            writer.println("# No match - default or manual setting");
            boolean hasUnmatched = false;
            for (String param : parameters) {
                if (!sampleValues.containsKey(param)) {
                    // Use default value if available, otherwise use estimated value
                    String value = defaultValues.getOrDefault(param, suggestDefaultValue(param));
                    writer.println(param + "=" + value);
                    hasUnmatched = true;
                }
            }
            
            if (hasUnmatched) {
                writer.println();
            }
            
            // Output matched parameters (DB sample values)
            for (String param : parameters) {
                SampleValue sample = sampleValues.get(param);
                if (sample != null) {
                    writer.printf("# %s (%s) - %s match%n", sample.source, sample.dataType, sample.matchType);
                    writer.println(param + "=" + sample.value);
                    writer.println();
                }
            }
        }
    }
    
    /**
     * Print results summary
     */
    private void printSummary(Set<String> parameters, Map<String, String> defaultValues, Map<String, SampleValue> sampleValues) {
        int totalParams = parameters.size();
        int dbSampleCount = sampleValues.size();
        int defaultValueCount = 0;
        int emptyCount = 0;
        
        // Distinguish between unmatched parameters with and without default values
        for (String param : parameters) {
            if (!sampleValues.containsKey(param)) {
                if (defaultValues.containsKey(param) && !defaultValues.get(param).isEmpty()) {
                    defaultValueCount++;
                } else {
                    emptyCount++;
                }
            }
        }
        
        System.out.println("\n=== Final Statistics ===");
        System.out.println("Total parameters: " + totalParams);
        System.out.println("DB sample values: " + dbSampleCount);
        System.out.println("Default values used: " + defaultValueCount);
        System.out.println("Manual setting required: " + emptyCount);
        System.out.printf("Auto-configuration rate: %.1f%% (DB samples + default values)%n", 
            ((dbSampleCount + defaultValueCount) * 100.0 / totalParams));
        System.out.println("\n" + getOutputFilePath() + " file has been generated.");
        
        // List of parameters requiring manual setting
        Set<String> manualParams = new TreeSet<>();
        for (String param : parameters) {
            if (!sampleValues.containsKey(param) && 
                (!defaultValues.containsKey(param) || defaultValues.get(param).isEmpty())) {
                manualParams.add(param);
            }
        }
        
        if (!manualParams.isEmpty()) {
            System.out.println("\nParameters requiring manual setting:");
            manualParams.forEach(param -> System.out.println("  - " + param));
        }
        
        if (defaultValueCount > 0) {
            System.out.println("\nParameters with default values applied:");
            for (String param : parameters) {
                if (!sampleValues.containsKey(param) && 
                    defaultValues.containsKey(param) && !defaultValues.get(param).isEmpty()) {
                    System.out.println("  - " + param + " = " + defaultValues.get(param));
                }
            }
        }
    }
    
    // Existing methods...
    
    /**
     * Find XML files recursively in directory
     */
    private List<Path> findXmlFiles(Path directory) throws IOException {
        List<Path> xmlFiles = new ArrayList<>();
        
        Files.walk(directory)
            .filter(path -> path.toString().toLowerCase().endsWith(".xml"))
            .filter(Files::isRegularFile)
            .forEach(xmlFiles::add);
        
        return xmlFiles;
    }
    
    /**
     * Extract all parameters from XML file
     */
    private int processXmlFile(Path xmlFile, Set<String> allParameters) {
        try {
            String content = Files.readString(xmlFile);
            
            // Count SQL tags
            int sqlCount = countSqlTags(content);
            
            // Extract parameters
            Set<String> fileParameters = extractParameters(content);
            allParameters.addAll(fileParameters);
            
            if (!fileParameters.isEmpty()) {
                System.out.println("  -> " + fileParameters.size() + " parameters, " + sqlCount + " SQL");
            }
            
            return sqlCount;
            
        } catch (IOException e) {
            System.err.println("File read error: " + xmlFile + " - " + e.getMessage());
            return 0;
        }
    }
    
    /**
     * Count SQL tags
     */
    private int countSqlTags(String content) {
        Pattern sqlTagPattern = Pattern.compile("<(select|insert|update|delete)\\s+[^>]*id=\"[^\"]+\"");
        Matcher matcher = sqlTagPattern.matcher(content);
        int count = 0;
        while (matcher.find()) {
            count++;
        }
        return count;
    }
    
    /**
     * Extract parameters (remove JDBC type, typeHandler and all attributes)
     */
    private Set<String> extractParameters(String content) {
        Set<String> parameters = new TreeSet<>();
        Matcher matcher = PARAM_PATTERN.matcher(content);
        
        while (matcher.find()) {
            String param = matcher.group(1);
            // Extract only paramName from #{paramName} or ${paramName}
            String paramContent = param.substring(2, param.length() - 1);
            
            // Remove all attributes like JDBC type, typeHandler, mode (use only part before comma)
            String paramName = paramContent;
            if (paramContent.contains(",")) {
                paramName = paramContent.split(",")[0];
            }
            
            // Use only first part if dot or bracket exists (e.g., user.name -> user)
            if (paramName.contains(".")) {
                paramName = paramName.split("\\.")[0];
            }
            if (paramName.contains("[")) {
                paramName = paramName.split("\\[")[0];
            }
            
            // Remove spaces, tabs, special characters
            paramName = paramName.trim();
            paramName = paramName.replaceAll("[\\s\\t]+", "");
            
            // Exclude invalid parameters
            if (!paramName.isEmpty() && 
                !paramName.equals("sys:topas") && 
                !paramName.startsWith("topas_") &&
                !paramName.startsWith("zk8_")) {
                parameters.add(paramName);
            }
        }
        
        return parameters;
    }
    
    /**
     * Suggest default value based on parameter name (dtm only)
     */
    private String suggestDefaultValue(String paramName) {
        String lowerName = paramName.toLowerCase();
        
        // Suggest default value only when dtm is included
        if (lowerName.contains("dtm")) {
            return "20250801";
        }
        
        // Empty value for others
        return "";
    }
    
    /**
     * Generate parameter file (alphabetically sorted)
     */
    private void generateParameterFile(Set<String> parameters) throws IOException {
        try (PrintWriter writer = new PrintWriter(new FileWriter(getOutputFilePath()))) {
            writer.println("# MyBatis parameter configuration file (bulk extraction)");
            writer.println("# Generated: " + new java.util.Date());
            writer.println("# Usage: Set test values for each parameter.");
            writer.println("# Empty values are treated as null.");
            writer.println();
            
            // TreeSet을 사용했으므로 이미 알파벳순으로 정렬됨
            for (String param : parameters) {
                String defaultValue = suggestDefaultValue(param);
                writer.println(param + "=" + defaultValue);
            }
        }
    }
    
    // Inner classes
    private static class ColumnInfo {
        String schema;
        String table;
        String column;
        String dataType;
        String matchType;
        int score;
        
        public ColumnInfo() {}
        
        public ColumnInfo(ColumnInfo other) {
            this.schema = other.schema;
            this.table = other.table;
            this.column = other.column;
            this.dataType = other.dataType;
            this.matchType = other.matchType;
            this.score = other.score;
        }
    }
    
    private static class SampleValue {
        String value;
        String source;
        String dataType;
        String matchType;
    }
}
