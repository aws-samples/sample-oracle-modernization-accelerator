package com.test.mybatis;

import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.databind.JsonSerializer;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializerProvider;
import com.fasterxml.jackson.databind.module.SimpleModule;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.apache.ibatis.io.Resources;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import java.io.*;
import java.math.BigDecimal;
import java.nio.file.*;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Program to recursively search MyBatis XML files and automatically test all SQL IDs (improved version)
 * 
 * Improvements:
 * 1. Improved resource management (try-with-resources, explicit temporary file deletion)
 * 2. JSON library usage (Jackson)
 * 3. Improved XML parsing (DOM parser usage)
 * 4. Externalized configuration files
 */
public class MyBatisBulkExecutorWithJson {
    
    private static final String PARAMETERS_FILE = "parameters.properties";
    private static final String CONFIG_FILE = "mybatis-bulk-executor.properties";
    
    private Properties config;
    private Pattern sqlIdPattern;
    private Set<String> examplePatterns;
    private ObjectMapper objectMapper;
    
    public MyBatisBulkExecutorWithJson() {
        loadConfiguration();
        this.objectMapper = new ObjectMapper();
        
        // BigDecimal precision control settings
        SimpleModule module = new SimpleModule();
        module.addSerializer(BigDecimal.class, new JsonSerializer<BigDecimal>() {
            @Override
            public void serialize(BigDecimal value, JsonGenerator gen, SerializerProvider serializers) 
                    throws IOException {
                if (value != null) {
                    // Remove unnecessary zeros with stripTrailingZeros()
                    gen.writeNumber(value.stripTrailingZeros());
                } else {
                    gen.writeNull();
                }
            }
        });
        this.objectMapper.registerModule(module);
    }
    
    private void loadConfiguration() {
        config = new Properties();
        try (InputStream is = getClass().getClassLoader().getResourceAsStream(CONFIG_FILE)) {
            if (is != null) {
                config.load(is);
            } else {
                // If file not found, try loading from current directory
                try (FileInputStream fis = new FileInputStream(CONFIG_FILE)) {
                    config.load(fis);
                }
            }
            System.out.println("Configuration file loaded: " + CONFIG_FILE);
        } catch (IOException e) {
            System.out.println("Configuration file not found: " + CONFIG_FILE);
            System.out.println("Running with default configuration.");
            loadDefaultConfiguration();
        }
        
        // Initialize patterns
        String patternStr = config.getProperty("sql.pattern.regex", "<(select|insert|update|delete)\\s+id=\"([^\"]+)\"");
        sqlIdPattern = Pattern.compile(patternStr);
        
        String examplePatternsStr = config.getProperty("example.patterns", "byexample,example,selectByExample,selectByExampleWithRowbounds");
        examplePatterns = new HashSet<>(Arrays.asList(examplePatternsStr.split(",")));
    }
    
    private void loadDefaultConfiguration() {
        // Default configuration values
        config.setProperty("temp.config.prefix", "mybatis-config-");
        config.setProperty("temp.mapper.prefix", "mapper-");
        config.setProperty("temp.file.suffix", ".xml");
        config.setProperty("sql.pattern.regex", "<(select|insert|update|delete)\\s+id=\"([^\"]+)\"");
        config.setProperty("example.patterns", "byexample,example,selectByExample,selectByExampleWithRowbounds");
        config.setProperty("mybatis.mapUnderscoreToCamelCase", "true");
        config.setProperty("mybatis.transactionManager", "JDBC");
        config.setProperty("mybatis.dataSource", "POOLED");
        config.setProperty("output.json.prefix", "bulk_test_result_");
        config.setProperty("output.json.suffix", ".json");
        config.setProperty("output.timestamp.format", "yyyyMMdd_HHmmss");
        config.setProperty("output.datetime.format", "yyyy-MM-dd HH:mm:ss");
        config.setProperty("db.oracle.driver", "oracle.jdbc.driver.OracleDriver");
        config.setProperty("db.mysql.driver", "com.mysql.cj.jdbc.Driver");
        config.setProperty("db.postgresql.driver", "org.postgresql.Driver");
        config.setProperty("mysql.default.options", "useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC");
        config.setProperty("oracle.default.service", "orcl");
        config.setProperty("mysql.default.host", "localhost");
        config.setProperty("mysql.default.port", "3306");
        config.setProperty("mysql.default.database", "test");
        config.setProperty("postgresql.default.host", "localhost");
        config.setProperty("postgresql.default.port", "5432");
        config.setProperty("postgresql.default.database", "postgres");
    }
    
    public static void main(String[] args) {
        if (args.length < 1) {
            printUsage();
            return;
        }
        
        String inputPath = args[0];
        String dbType = null;
        boolean selectOnly = true;
        boolean summaryOnly = false;
        boolean verbose = false;
        boolean generateJson = false;
        String customJsonFileName = null;
        String includePattern = null;
        boolean enableCompare = false;
        boolean showData = false;
        
        // Option parsing
        for (int i = 1; i < args.length; i++) {
            switch (args[i]) {
                case "--db":
                    if (i + 1 < args.length) {
                        dbType = args[++i];
                    } else {
                        System.err.println("error: Please specify database type for --db option.");
                        return;
                    }
                    break;
                case "--include":
                    if (i + 1 < args.length) {
                        includePattern = args[++i];
                    } else {
                        System.err.println("error: Please specify folder name pattern to include for --include option.");
                        return;
                    }
                    break;
                case "--all":
                    selectOnly = false;
                    break;
                case "--summary":
                    summaryOnly = true;
                    break;
                case "--verbose":
                    verbose = true;
                    break;
                case "--json":
                    generateJson = true;
                    break;
                case "--json-file":
                    if (i + 1 < args.length) {
                        generateJson = true;
                        customJsonFileName = args[++i];
                    } else {
                        System.err.println("error: Please specify filename for --json-file option.");
                        return;
                    }
                    break;
                case "--compare":
                    enableCompare = true;
                    break;
                case "--show-data":
                    showData = true;
                    break;
            }
        }
        
        if (dbType == null) {
            System.err.println("error: Please specify database type with --db option. (oracle, mysql, postgres)");
            return;
        }
        
        // Check if input path is file or folder
        Path path = Paths.get(inputPath);
        if (!Files.exists(path)) {
            System.err.println("Error: Specified path does not exist: " + inputPath);
            return;
        }
        
        MyBatisBulkExecutorWithJson executor = new MyBatisBulkExecutorWithJson();
        executor.executeSqls(inputPath, dbType, selectOnly, summaryOnly, verbose, generateJson, customJsonFileName, includePattern, enableCompare, showData);
    }
    
    private static void printUsage() {
        System.out.println("Usage: java MyBatisBulkExecutorWithJson <path> [options]");
        System.out.println("Path: Directory containing MyBatis XML files or individual XML file");
        System.out.println("Options:");
        System.out.println("  --db <type>     Database type (oracle, mysql, postgres) - required");
        System.out.println("  --include <pattern>  Search only folders containing specified pattern (directory mode only)");
        System.out.println("  --select-only   Execute SELECT statements only (default)");
        System.out.println("  --all          Execute all SQL statements (including INSERT/UPDATE/DELETE)");
        System.out.println("  --summary      Output summary information only");
        System.out.println("  --verbose      Output detailed information");
        System.out.println("  --show-data    Output SQL result data");
        System.out.println("  --json         Generate JSON result file (automatic filename)");
        System.out.println("  --json-file <filename>  Generate JSON result file (specify filename)");
        System.out.println("  --compare      Enable SQL result comparison (Oracle ↔ PostgreSQL/MySQL)");
        System.out.println();
        System.out.println("Environment variable setup:");
        System.out.println("  Oracle: ORACLE_SVC_CONNECT_STRING, ORACLE_SVC_USER, ORACLE_SVC_PASSWORD, ORACLE_HOME");
        System.out.println("  MySQL: MYSQL_HOST, MYSQL_TCP_PORT, MYSQL_DB, MYSQL_ADM_USER, MYSQL_PASSWORD");
        System.out.println("  PostgreSQL: PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD");
        System.out.println("  Comparison feature: TARGET_DBMS_TYPE (mysql or postgresql)");
        System.out.println();
        System.out.println("Examples:");
        System.out.println("  # Directory mode");
        System.out.println("  java MyBatisBulkExecutorWithJson /path/to/mappers --db oracle --json");
        System.out.println("  java MyBatisBulkExecutorWithJson /path/to/mappers --db mysql --json-file my_result.json");
        System.out.println("  java MyBatisBulkExecutorWithJson /path/to/mappers --db postgres --include transform");
        System.out.println("  java MyBatisBulkExecutorWithJson /path/to/mappers --db oracle --compare");
        System.out.println();
        System.out.println("  # File mode");
        System.out.println("  java MyBatisBulkExecutorWithJson /path/to/UserMapper.xml --db oracle --verbose");
        System.out.println("  java MyBatisBulkExecutorWithJson /path/to/OrderMapper.xml --db mysql --all");
    }
    
    public void executeSqls(String inputPath, String dbType, boolean selectOnly, boolean summaryOnly, boolean verbose, boolean generateJson, String customJsonFileName, String includePattern, boolean enableCompare, boolean showData) {
        SqlListRepository repository = null;
        
        try {
            System.out.println("=== MyBatis Bulk SQL Execution Test (improved version) ===");
            
            Path path = Paths.get(inputPath);
            boolean isFile = Files.isRegularFile(path);
            boolean isDirectory = Files.isDirectory(path);
            
            if (isFile) {
                System.out.println("Input file: " + inputPath);
                if (!inputPath.toLowerCase().endsWith(".xml")) {
                    System.err.println("Warning: Input file is not an XML file.");
                }
            } else if (isDirectory) {
                System.out.println("Search directory: " + inputPath);
            } else {
                System.err.println("Error: Specified path is neither file nor directory: " + inputPath);
                return;
            }
            
            System.out.println("Database type: " + dbType.toUpperCase());
            System.out.println("Execution mode: " + (selectOnly ? "SELECT only" : "All SQL"));
            System.out.println("Output mode: " + (summaryOnly ? "Summary only" : verbose ? "Detailed" : "Normal"));
            System.out.println("Comparison feature: " + (enableCompare ? "Enabled" : "Disabled"));
            
            if (isDirectory && includePattern != null) {
                System.out.println("Folder filter: Only folders containing '" + includePattern + "'");
            }
            if (generateJson) {
                System.out.println("JSON output: Enabled");
            }
            System.out.println();
            
            // 0. Initialize SqlListRepository and create table (only when --compare option is present)
            if (enableCompare) {
                try {
                    repository = new SqlListRepository();
                    repository.ensureTargetTableExists();
                    System.out.println("SQL comparison verification system initialization completed");
                    System.out.println();
                } catch (Exception e) {
                    System.err.println("SQL comparison verification system initialization failed: " + e.getMessage());
                    System.out.println("Continuing without verification feature...");
                    repository = null;
                    System.out.println();
                }
            } else {
                System.out.println("Comparison feature is disabled. (no --compare option)");
                System.out.println();
            }
            
            // 1. Parameter loading
            Properties parameters = loadParameters();
            
            // 2. Find XML files and SQL IDs
            List<SqlTestInfo> sqlTests;
            if (isFile) {
                sqlTests = findSqlTestsInFile(path, selectOnly);
                System.out.println("Target XML files: 1");
            } else {
                sqlTests = findAllSqlTests(path, selectOnly, includePattern);
                System.out.println("XML files found: " + sqlTests.stream().map(t -> t.xmlFile).distinct().count());
            }
            
            System.out.println("SQL count to execute: " + sqlTests.size());
            System.out.println();
            
            // 2.1. Save SQL information to DB (only when --compare option is present and repository exists)
            if (enableCompare && repository != null) {
                saveSqlInfoToRepository(sqlTests, repository, parameters, dbType);
            }
            
            // 3. Execute tests
            TestResults results = executeSqlTests(sqlTests, parameters, dbType, summaryOnly, verbose, enableCompare ? repository : null, showData);
            
            // 4. Output results
            printResults(results, summaryOnly, verbose);
            
            // 5. Generate JSON file
            if (generateJson) {
                generateJsonReport(results, inputPath, dbType, customJsonFileName);
            }
            
            // 6. Compare results and output statistics (only when --compare option is present and repository exists)
            if (enableCompare && repository != null) {
                performResultComparison(repository);
            }
            
        } catch (Exception e) {
            System.err.println("Error occurred: " + e.getMessage());
            e.printStackTrace();
        } finally {
            // 7. Clean up resources
            if (repository != null) {
                try {
                    repository.close();
                } catch (Exception e) {
                    System.err.println("Error during repository cleanup: " + e.getMessage());
                }
            }
        }
    }
    
    // Improved JSON generation method (using Jackson)
    private void generateJsonReport(TestResults results, String directoryPath, String dbType, String customJsonFileName) {
        try {
            String jsonFileName;
            
            if (customJsonFileName != null && !customJsonFileName.trim().isEmpty()) {
                // When user specifies filename
                jsonFileName = customJsonFileName.trim();
                
                // Add .json extension if not present
                if (!jsonFileName.toLowerCase().endsWith(".json")) {
                    jsonFileName += ".json";
                }
                
                // Create in out directory if relative path
                if (!jsonFileName.contains("/") && !jsonFileName.contains("\\")) {
                    // Create out directory
                    File outDir = new File("out");
                    if (!outDir.exists()) {
                        outDir.mkdirs();
                        System.out.println("📁 Output directory created: " + outDir.getAbsolutePath());
                    }
                    jsonFileName = "out/" + jsonFileName;
                }
            } else {
                // Existing automatic filename generation logic
                File outDir = new File("out");
                if (!outDir.exists()) {
                    outDir.mkdirs();
                    System.out.println("📁 Output directory created: " + outDir.getAbsolutePath());
                }
                
                String timestampFormat = config.getProperty("output.timestamp.format", "yyyyMMdd_HHmmss");
                String jsonPrefix = config.getProperty("output.json.prefix", "bulk_test_result_");
                String jsonSuffix = config.getProperty("output.json.suffix", ".json");
                
                String timestamp = new SimpleDateFormat(timestampFormat).format(new Date());
                jsonFileName = "out/" + jsonPrefix + timestamp + jsonSuffix;
            }
            
            String datetimeFormat = config.getProperty("output.datetime.format", "yyyy-MM-dd HH:mm:ss");
            
            // Generate JSON using Jackson
            ObjectNode rootNode = objectMapper.createObjectNode();
            
            // Test information
            ObjectNode testInfo = objectMapper.createObjectNode();
            testInfo.put("timestamp", new SimpleDateFormat(datetimeFormat).format(new Date()));
            testInfo.put("directory", directoryPath);
            testInfo.put("databaseType", dbType.toUpperCase());
            testInfo.put("totalTests", results.totalTests);
            testInfo.put("successCount", results.successCount);
            testInfo.put("failureCount", results.failureCount);
            testInfo.put("successRate", String.format("%.1f", results.getSuccessRate()));
            rootNode.set("testInfo", testInfo);
            
            // Success한 테스트들
            ArrayNode successfulTests = objectMapper.createArrayNode();
            for (TestResult result : results.allResults) {
                if (result.success) {
                    ObjectNode testNode = objectMapper.createObjectNode();
                    testNode.put("xmlFile", result.testInfo.xmlFile.getFileName().toString());
                    testNode.put("sqlId", result.testInfo.sqlId);
                    testNode.put("sqlType", result.testInfo.sqlType);
                    testNode.put("rowCount", result.rowCount);
                    
                    // Include result data in JSON if available
                    if (result.resultData != null) {
                        ObjectNode resultDataNode = objectMapper.createObjectNode();
                        resultDataNode.put("count", result.resultData.size());
                        
                        ArrayNode dataArray = objectMapper.createArrayNode();
                        for (Map<String, Object> row : result.resultData) {
                            ObjectNode rowNode = objectMapper.valueToTree(row);
                            dataArray.add(rowNode);
                        }
                        resultDataNode.set("data", dataArray);
                        testNode.set("resultData", resultDataNode);
                    }
                    
                    successfulTests.add(testNode);
                }
            }
            rootNode.set("successfulTests", successfulTests);
            
            // Failed한 테스트들
            ArrayNode failedTests = objectMapper.createArrayNode();
            for (TestResult result : results.failures) {
                ObjectNode testNode = objectMapper.createObjectNode();
                testNode.put("xmlFile", result.testInfo.xmlFile.getFileName().toString());
                testNode.put("sqlId", result.testInfo.sqlId);
                testNode.put("sqlType", result.testInfo.sqlType);
                testNode.put("errorMessage", result.errorMessage != null ? result.errorMessage : "");
                
                // Include result data in JSON even for failed cases (error information etc.)
                if (result.resultData != null) {
                    ObjectNode resultDataNode = objectMapper.createObjectNode();
                    resultDataNode.put("count", result.resultData.size());
                    
                    ArrayNode dataArray = objectMapper.createArrayNode();
                    for (Map<String, Object> row : result.resultData) {
                        ObjectNode rowNode = objectMapper.valueToTree(row);
                        dataArray.add(rowNode);
                    }
                    resultDataNode.set("data", dataArray);
                    testNode.set("resultData", resultDataNode);
                }
                
                failedTests.add(testNode);
            }
            rootNode.set("failedTests", failedTests);
            
            // File statistics
            ArrayNode fileStatistics = objectMapper.createArrayNode();
            Map<String, FileStats> fileStatsMap = calculateFileStats(results);
            for (Map.Entry<String, FileStats> entry : fileStatsMap.entrySet()) {
                ObjectNode statsNode = objectMapper.createObjectNode();
                FileStats stats = entry.getValue();
                statsNode.put("fileName", entry.getKey());
                statsNode.put("totalTests", stats.total);
                statsNode.put("successCount", stats.success);
                statsNode.put("failureCount", stats.failure);
                statsNode.put("successRate", String.format("%.1f", stats.getSuccessRate()));
                fileStatistics.add(statsNode);
            }
            rootNode.set("fileStatistics", fileStatistics);
            
            // Save JSON file
            try (FileWriter writer = new FileWriter(jsonFileName)) {
                objectMapper.writerWithDefaultPrettyPrinter().writeValue(writer, rootNode);
            }
            
            System.out.println("\n📄 JSON result file generated: " + jsonFileName);
            
        } catch (Exception e) {
            System.err.println("Error during JSON file generation: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private Properties loadParameters() {
        Properties props = new Properties();
        String testFolder = System.getenv("TEST_FOLDER");
        String paramFilePath = testFolder != null ? testFolder + "/" + PARAMETERS_FILE : PARAMETERS_FILE;
        File paramFile = new File(paramFilePath);
        
        if (paramFile.exists()) {
            try (FileInputStream fis = new FileInputStream(paramFilePath)) {
                props.load(fis);
                System.out.println("Parameter file loaded successfully: " + paramFilePath);
            } catch (IOException e) {
                System.err.println("Parameter file load failed: " + e.getMessage());
                System.out.println("Running intelligent bind variable generator...");
                generateParametersWithBindVariableGenerator();
                return loadParameters(); // Recursive call to load generated file
            }
        } else {
            System.out.println("Parameter file not found: " + paramFilePath);
            System.out.println("Running intelligent bind variable generator...");
            generateParametersWithBindVariableGenerator();
            return loadParameters(); // Recursive call to load generated file
        }
        return props;
    }
    
    /**
     * Generate basic parameter file (when parameter file is missing)
     */
    private void generateParametersWithBindVariableGenerator() {
        System.out.println("\n=== Basic Parameter File Generation ===");
        System.out.println("Generating basic parameters because parameters.properties file is missing.");
        System.out.println("For more accurate parameters, run ./run_bind_generator.sh.");
        createBasicParametersFile();
    }
    
    /**
     * Generate basic parameter file (fallback)
     */
    private void createBasicParametersFile() {
        try {
            System.out.println("Generating basic parameter file...");
            
            Properties defaultProps = new Properties();
            
            // ID related parameters (numeric)
            defaultProps.setProperty("userId", "1");
            defaultProps.setProperty("productId", "1");
            defaultProps.setProperty("orderId", "1");
            defaultProps.setProperty("customerId", "1");
            defaultProps.setProperty("categoryId", "1");
            defaultProps.setProperty("warehouseId", "1");
            defaultProps.setProperty("sellerId", "1");
            defaultProps.setProperty("paymentId", "1");
            defaultProps.setProperty("shippingId", "1");
            defaultProps.setProperty("id", "1");
            defaultProps.setProperty("itemId", "1");
            defaultProps.setProperty("brandId", "1");
            
            // Status related parameters
            defaultProps.setProperty("status", "ACTIVE");
            defaultProps.setProperty("orderStatus", "COMPLETED");
            defaultProps.setProperty("paymentStatus", "PAID");
            defaultProps.setProperty("grade", "VIP");
            defaultProps.setProperty("country", "USA");
            defaultProps.setProperty("keyword", "TEST");
            defaultProps.setProperty("type", "NORMAL");
            
            // Date related parameters
            defaultProps.setProperty("startDate", "2025-01-01");
            defaultProps.setProperty("endDate", "2025-12-31");
            defaultProps.setProperty("year", "2025");
            defaultProps.setProperty("month", "1");
            defaultProps.setProperty("day", "1");
            defaultProps.setProperty("createdDate", "2025-01-01");
            defaultProps.setProperty("updatedDate", "2025-01-01");
            
            // Numeric related parameters
            defaultProps.setProperty("amount", "1000");
            defaultProps.setProperty("price", "100");
            defaultProps.setProperty("quantity", "1");
            defaultProps.setProperty("limit", "10");
            defaultProps.setProperty("offset", "0");
            defaultProps.setProperty("days", "30");
            defaultProps.setProperty("count", "1");
            defaultProps.setProperty("size", "10");
            defaultProps.setProperty("page", "1");
            
            // String related parameters
            defaultProps.setProperty("email", "test@example.com");
            defaultProps.setProperty("phone", "010-1234-5678");
            defaultProps.setProperty("name", "TestUser");
            defaultProps.setProperty("userName", "TestUser");
            defaultProps.setProperty("productName", "TestProduct");
            defaultProps.setProperty("categoryName", "TestCategory");
            defaultProps.setProperty("description", "Test Description");
            
            // Other frequently used parameters
            defaultProps.setProperty("enabled", "1");
            defaultProps.setProperty("active", "1");
            defaultProps.setProperty("deleted", "0");
            defaultProps.setProperty("version", "1");
            
            // Save file
            String testFolder = System.getenv("TEST_FOLDER");
            String paramFilePath = testFolder != null ? testFolder + "/" + PARAMETERS_FILE : PARAMETERS_FILE;
            try (FileOutputStream fos = new FileOutputStream(paramFilePath)) {
                defaultProps.store(fos, "Basic parameter file (auto-generated) - Basic values to prevent null values");
            }
            
            System.out.println("✅ Basic parameter file generated successfully: " + paramFilePath);
            System.out.println("   Total " + defaultProps.size() + " basic parameters configured");
            
        } catch (Exception e) {
            System.err.println("Basic parameter file generation failed: " + e.getMessage());
        }
    }
    
    // Improved SQL search method (using DOM parser)
    private List<SqlTestInfo> findAllSqlTests(Path directory, boolean selectOnly, String includePattern) throws IOException {
        List<SqlTestInfo> sqlTests = new ArrayList<>();
        
        Files.walk(directory)
            .filter(path -> path.toString().endsWith(".xml"))
            .filter(path -> {
                // When includePattern is specified, filter only paths containing that pattern
                if (includePattern != null && !includePattern.trim().isEmpty()) {
                    return path.toString().toLowerCase().contains(includePattern.toLowerCase());
                }
                return true;
            })
            .filter(this::isMyBatisXmlFile)  // Filter only MyBatis XML files
            .forEach(xmlFile -> {
                try {
                    // XML parsing using DOM parser
                    DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
                    // Disable DTD validation
                    factory.setValidating(false);
                    factory.setNamespaceAware(false);
                    factory.setFeature("http://xml.org/sax/features/namespaces", false);
                    factory.setFeature("http://xml.org/sax/features/validation", false);
                    factory.setFeature("http://apache.org/xml/features/nonvalidating/load-dtd-grammar", false);
                    factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
                    
                    DocumentBuilder builder = factory.newDocumentBuilder();
                    Document doc = builder.parse(xmlFile.toFile());
                    
                    // Find SQL elements
                    String[] sqlTypes = {"select", "insert", "update", "delete"};
                    for (String sqlType : sqlTypes) {
                        if (selectOnly && !sqlType.equals("select")) {
                            continue;
                        }
                        
                        NodeList nodes = doc.getElementsByTagName(sqlType);
                        for (int i = 0; i < nodes.getLength(); i++) {
                            Element element = (Element) nodes.item(i);
                            String sqlId = element.getAttribute("id");
                            
                            if (sqlId != null && !sqlId.isEmpty()) {
                                SqlTestInfo testInfo = new SqlTestInfo();
                                testInfo.xmlFile = xmlFile;
                                testInfo.sqlId = sqlId;
                                testInfo.sqlType = sqlType.toUpperCase();
                                sqlTests.add(testInfo);
                            }
                        }
                    }
                } catch (Exception e) {
                    // Fallback to regex when DOM parsing fails
                    System.out.println("DOM parsing failed, fallback to regex: " + xmlFile.getFileName());
                    try {
                        String content = Files.readString(xmlFile);
                        Matcher matcher = sqlIdPattern.matcher(content);
                        
                        while (matcher.find()) {
                            String sqlType = matcher.group(1).toUpperCase();
                            String sqlId = matcher.group(2);
                            
                            if (selectOnly && !sqlType.equals("SELECT")) {
                                continue;
                            }
                            
                            SqlTestInfo testInfo = new SqlTestInfo();
                            testInfo.xmlFile = xmlFile;
                            testInfo.sqlId = sqlId;
                            testInfo.sqlType = sqlType;
                            sqlTests.add(testInfo);
                        }
                    } catch (IOException ioException) {
                        System.err.println("XML file read error: " + xmlFile + " - " + ioException.getMessage());
                    }
                }
            });
        
        return sqlTests;
    }
    
    // Method to find SQL test information from single file
    private List<SqlTestInfo> findSqlTestsInFile(Path xmlFile, boolean selectOnly) {
        List<SqlTestInfo> sqlTests = new ArrayList<>();
        
        if (!isMyBatisXmlFile(xmlFile)) {
            System.out.println("Warning: Not a MyBatis XML file: " + xmlFile.getFileName());
            return sqlTests;
        }
        
        try {
            // DOM 파서를 사용한 XML 파싱
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            // DTD 검증 비활성화
            factory.setValidating(false);
            factory.setNamespaceAware(false);
            factory.setFeature("http://xml.org/sax/features/namespaces", false);
            factory.setFeature("http://xml.org/sax/features/validation", false);
            factory.setFeature("http://apache.org/xml/features/nonvalidating/load-dtd-grammar", false);
            factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
            
            DocumentBuilder builder = factory.newDocumentBuilder();
            Document doc = builder.parse(xmlFile.toFile());
            
            // Find SQL elements
            String[] sqlTypes = {"select", "insert", "update", "delete"};
            for (String sqlType : sqlTypes) {
                if (selectOnly && !sqlType.equals("select")) {
                    continue;
                }
                
                NodeList nodes = doc.getElementsByTagName(sqlType);
                for (int i = 0; i < nodes.getLength(); i++) {
                    Element element = (Element) nodes.item(i);
                    String sqlId = element.getAttribute("id");
                    
                    if (sqlId != null && !sqlId.isEmpty()) {
                        SqlTestInfo testInfo = new SqlTestInfo();
                        testInfo.xmlFile = xmlFile;
                        testInfo.sqlId = sqlId;
                        testInfo.sqlType = sqlType.toUpperCase();
                        sqlTests.add(testInfo);
                    }
                }
            }
        } catch (Exception e) {
            // Fallback to regex when DOM parsing fails
            System.out.println("DOM parsing failed, fallback to regex: " + xmlFile.getFileName());
            try {
                String content = Files.readString(xmlFile);
                Matcher matcher = sqlIdPattern.matcher(content);
                
                while (matcher.find()) {
                    String sqlType = matcher.group(1).toUpperCase();
                    String sqlId = matcher.group(2);
                    
                    if (selectOnly && !sqlType.equals("SELECT")) {
                        continue;
                    }
                    
                    SqlTestInfo testInfo = new SqlTestInfo();
                    testInfo.xmlFile = xmlFile;
                    testInfo.sqlId = sqlId;
                    testInfo.sqlType = sqlType;
                    sqlTests.add(testInfo);
                }
            } catch (IOException ioException) {
                System.err.println("XML 파일 read error: " + xmlFile + " - " + ioException.getMessage());
            }
        }
        
        return sqlTests;
    }
    
    private TestResults executeSqlTests(List<SqlTestInfo> sqlTests, Properties parameters, String dbType, boolean summaryOnly, boolean verbose, SqlListRepository repository, boolean showData) {
        TestResults results = new TestResults();
        
        System.out.println("=== SQL Test Execution Started ===");
        System.out.println();
        
        for (int i = 0; i < sqlTests.size(); i++) {
            SqlTestInfo testInfo = sqlTests.get(i);
            TestResult result = new TestResult();
            result.testInfo = testInfo;
            
            // Progress display (when not in summary mode)
            if (!summaryOnly) {
                double progress = ((double)(i + 1) / sqlTests.size()) * 100;
                System.out.printf("\rProgress: %.1f%% [%d/%d] %s:%s", 
                    progress, i + 1, sqlTests.size(), 
                    testInfo.xmlFile.getFileName(), testInfo.sqlId);
                System.out.flush();
            }
            
            // Skip Example pattern SQL (using patterns read from configuration file)
            String sqlIdLower = testInfo.sqlId.toLowerCase();
            boolean isExamplePattern = examplePatterns.stream()
                .anyMatch(pattern -> sqlIdLower.contains(pattern.toLowerCase()));
            
            if (isExamplePattern) {
                result.success = true;
                result.rowCount = -1; // For skip indication
                
                // Save skip information for Example patterns too (to be included in comparison statistics)
                if (repository != null) {
                    try {
                        Map<String, Object> paramMap = new HashMap<>();
                        for (String key : parameters.stringPropertyNames()) {
                            String value = parameters.getProperty(key);
                            paramMap.put(key, cleanParameterValue(value));
                        }
                        
                        // Generate skipped results
                        List<Map<String, Object>> skippedResults = new ArrayList<>();
                        Map<String, Object> skipResult = new HashMap<>();
                        skipResult.put("status", "SKIPPED");
                        skipResult.put("reason", "Example pattern");
                        skipResult.put("pattern_matched", true);
                        skippedResults.add(skipResult);
                        
                        // Generate in mapper_name.sql_id format
                        String mapperName = extractMapperName(testInfo.xmlFile);
                        String fullSqlId = mapperName + "." + testInfo.sqlId;
                        
                        if ("oracle".equalsIgnoreCase(dbType)) {
                            repository.saveSourceResult(fullSqlId, skippedResults, paramMap);
                        } else {
                            repository.saveTargetResult(fullSqlId, skippedResults, paramMap);
                        }
                    } catch (Exception repoException) {
                        System.err.println("Skip result save failed (" + testInfo.sqlId + "): " + repoException.getMessage());
                    }
                }
                
                if (verbose) {
                    System.out.printf(" ⏭️  Example pattern skipped (ID: %s)%n", testInfo.sqlId);
                }
            } else {
                // Execute SQL and save results
                List<Map<String, Object>> sqlResults = null;
                try {
                    sqlResults = executeSingleSqlWithResults(testInfo, parameters, dbType, verbose);
                    result.rowCount = sqlResults.size();
                    result.success = true;
                    
                    // Save result data when showData is enabled
                    if (showData && sqlResults != null) {
                        result.resultData = new ArrayList<>(sqlResults);
                    }
                    
                    if (verbose) {
                        System.out.printf(" ✅ %d rows%n", result.rowCount);
                    }
                    
                    // Data output option
                    if (showData && sqlResults != null && !sqlResults.isEmpty()) {
                        System.out.println("    📊 Result data:");
                        for (int idx = 0; idx < Math.min(sqlResults.size(), 5); idx++) {
                            System.out.println("      " + (idx + 1) + ": " + sqlResults.get(idx));
                        }
                        if (sqlResults.size() > 5) {
                            System.out.println("      ... (total " + sqlResults.size() + " records, showing first 5 only)");
                        }
                    }
                } catch (Exception sqlException) {
                    result.success = false;
                    result.errorMessage = sqlException.getMessage();
                    
                    // Save as empty result even for failed cases (to be included in comparison statistics)
                    sqlResults = new ArrayList<>();
                    Map<String, Object> errorResult = new HashMap<>();
                    errorResult.put("error", "SQL Execution Failed");
                    errorResult.put("message", sqlException.getMessage());
                    sqlResults.add(errorResult);
                    
                    // Save error results when showData is enabled
                    if (showData) {
                        result.resultData = new ArrayList<>(sqlResults);
                    }
                    
                    if (!summaryOnly) {
                        System.out.printf(" ❌ Failed: %s%n", sqlException.getMessage());
                    }
                }
                
                // Save execution results to Repository (save regardless of Success/Failed)
                if (repository != null && sqlResults != null) {
                    try {
                        Map<String, Object> paramMap = new HashMap<>();
                        for (String key : parameters.stringPropertyNames()) {
                            String value = parameters.getProperty(key);
                            // Remove quotes for MyBatis bind variables
                            paramMap.put(key, cleanParameterValue(value));
                        }
                        
                        // Generate in mapper_name.sql_id format
                        String mapperName = extractMapperName(testInfo.xmlFile);
                        String fullSqlId = mapperName + "." + testInfo.sqlId;
                        
                        if ("oracle".equalsIgnoreCase(dbType)) {
                            repository.saveSourceResult(fullSqlId, sqlResults, paramMap);
                        } else {
                            repository.saveTargetResult(fullSqlId, sqlResults, paramMap);
                        }
                    } catch (Exception repoException) {
                        System.err.println("Result save failed (" + testInfo.sqlId + "): " + repoException.getMessage());
                    }
                }
            }
            
            results.addResult(result);
        }
        
        // Line break at the end
        if (!summaryOnly) {
            System.out.println();
        }
        
        return results;
    }
    
    // Improved single SQL execution method (Improved resource management)
    private int executeSingleSql(SqlTestInfo testInfo, Properties parameters, String dbType, boolean verbose) throws Exception {
        File tempConfigFile = null;
        File tempMapperFile = null;
        
        try {
            // Generate temporary configuration file
            String configPrefix = config.getProperty("temp.config.prefix", "mybatis-config-");
            String mapperPrefix = config.getProperty("temp.mapper.prefix", "mapper-");
            String fileSuffix = config.getProperty("temp.file.suffix", ".xml");
            
            tempConfigFile = File.createTempFile(configPrefix, fileSuffix);
            tempMapperFile = File.createTempFile(mapperPrefix, fileSuffix);
            
            // Generate temporary mapper file (using archived version's regex method)
            String modifiedMapperContent = modifyMapperContentWithRegex(testInfo.xmlFile);
            try (FileWriter writer = new FileWriter(tempMapperFile)) {
                writer.write(modifiedMapperContent);
            }
            
            // Generate MyBatis configuration file
            String configContent = createMyBatisConfig(tempMapperFile.getAbsolutePath(), dbType);
            try (FileWriter writer = new FileWriter(tempConfigFile)) {
                writer.write(configContent);
            }
            
            // Execute MyBatis
            try (InputStream inputStream = new FileInputStream(tempConfigFile)) {
                SqlSessionFactory sqlSessionFactory = new SqlSessionFactoryBuilder().build(inputStream);
                
                try (SqlSession session = sqlSessionFactory.openSession(false)) { // Set autoCommit = false
                    Map<String, Object> paramMap = new HashMap<>();
                    for (String key : parameters.stringPropertyNames()) {
                        String value = parameters.getProperty(key);
                        // Remove quotes for MyBatis bind variables
                        paramMap.put(key, cleanParameterValue(value));
                    }
                    
                    int resultCount = 0;
                    
                    try {
                        // Use different execution methods based on SQL type
                        switch (testInfo.sqlType.toUpperCase()) {
                            case "SELECT":
                                List<Map<String, Object>> selectResults = session.selectList(testInfo.sqlId, paramMap);
                                resultCount = selectResults.size();
                                break;
                                
                            case "INSERT":
                                resultCount = session.insert(testInfo.sqlId, paramMap);
                                if (verbose) {
                                    System.out.printf(" 🔄 INSERT executed then rolled back (%d rows affected)%n", resultCount);
                                }
                                break;
                                
                            case "UPDATE":
                                resultCount = session.update(testInfo.sqlId, paramMap);
                                if (verbose) {
                                    System.out.printf(" 🔄 UPDATE executed then rolled back (%d rows affected)%n", resultCount);
                                }
                                break;
                                
                            case "DELETE":
                                resultCount = session.delete(testInfo.sqlId, paramMap);
                                if (verbose) {
                                    System.out.printf(" 🔄 DELETE executed then rolled back (%d rows affected)%n", resultCount);
                                }
                                break;
                                
                            default:
                                // Other SQL (CALL etc.) handled with selectList
                                List<Map<String, Object>> otherResults = session.selectList(testInfo.sqlId, paramMap);
                                resultCount = otherResults.size();
                                break;
                        }
                        
                        // Always rollback for INSERT/UPDATE/DELETE (since this is test environment)
                        if (!testInfo.sqlType.equalsIgnoreCase("SELECT")) {
                            session.rollback();
                            if (verbose) {
                                System.out.printf(" ✅ Transaction rollback completed (data changes cancelled)%n");
                            }
                        }
                        
                    } catch (Exception e) {
                        // Rollback even when error occurs
                        if (!testInfo.sqlType.equalsIgnoreCase("SELECT")) {
                            try {
                                session.rollback();
                                if (verbose) {
                                    System.out.printf(" 🔄 Rollback completed due to error%n");
                                }
                            } catch (Exception rollbackException) {
                                System.err.println("Rollback failed: " + rollbackException.getMessage());
                            }
                        }
                        throw e;
                    }
                    
                    return resultCount;
                }
            }
            
        } finally {
            // Explicit temporary file deletion
            if (tempConfigFile != null && tempConfigFile.exists()) {
                if (!tempConfigFile.delete()) {
                    tempConfigFile.deleteOnExit(); // Delete on JVM exit if deletion fails
                }
            }
            if (tempMapperFile != null && tempMapperFile.exists()) {
                if (!tempMapperFile.delete()) {
                    tempMapperFile.deleteOnExit(); // Delete on JVM exit if deletion fails
                }
            }
        }
    }
    
    // Single SQL execution method that returns results (for Repository integration)
    private List<Map<String, Object>> executeSingleSqlWithResults(SqlTestInfo testInfo, Properties parameters, String dbType, boolean verbose) throws Exception {
        File tempConfigFile = null;
        File tempMapperFile = null;
        
        try {
            // Generate temporary configuration file
            String configPrefix = config.getProperty("temp.config.prefix", "mybatis-config-");
            String mapperPrefix = config.getProperty("temp.mapper.prefix", "mapper-");
            String fileSuffix = config.getProperty("temp.file.suffix", ".xml");
            
            tempConfigFile = File.createTempFile(configPrefix, fileSuffix);
            tempMapperFile = File.createTempFile(mapperPrefix, fileSuffix);
            
            // Generate temporary mapper file (using archived version's regex method)
            String modifiedMapperContent = modifyMapperContentWithRegex(testInfo.xmlFile);
            try (FileWriter writer = new FileWriter(tempMapperFile)) {
                writer.write(modifiedMapperContent);
            }
            
            // Generate MyBatis configuration file
            String configContent = createMyBatisConfig(tempMapperFile.getAbsolutePath(), dbType);
            try (FileWriter writer = new FileWriter(tempConfigFile)) {
                writer.write(configContent);
            }
            
            // Execute MyBatis
            try (InputStream inputStream = new FileInputStream(tempConfigFile)) {
                SqlSessionFactory sqlSessionFactory = new SqlSessionFactoryBuilder().build(inputStream);
                
                try (SqlSession session = sqlSessionFactory.openSession(false)) { // Set autoCommit = false
                    Map<String, Object> paramMap = new HashMap<>();
                    for (String key : parameters.stringPropertyNames()) {
                        String value = parameters.getProperty(key);
                        // Remove quotes for MyBatis bind variables
                        paramMap.put(key, cleanParameterValue(value));
                    }
                    
                    List<Map<String, Object>> results = new ArrayList<>();
                    
                    try {
                        // Use different execution methods based on SQL type
                        switch (testInfo.sqlType.toUpperCase()) {
                            case "SELECT":
                                results = session.selectList(testInfo.sqlId, paramMap);
                                break;
                                
                            case "INSERT":
                                int insertCount = session.insert(testInfo.sqlId, paramMap);
                                // Convert INSERT result to Map and return
                                Map<String, Object> insertResult = new HashMap<>();
                                insertResult.put("affected_rows", insertCount);
                                insertResult.put("operation", "INSERT");
                                results.add(insertResult);
                                if (verbose) {
                                    System.out.printf(" 🔄 INSERT executed then rolled back (%d rows affected)%n", insertCount);
                                }
                                break;
                                
                            case "UPDATE":
                                int updateCount = session.update(testInfo.sqlId, paramMap);
                                // Convert UPDATE result to Map and return
                                Map<String, Object> updateResult = new HashMap<>();
                                updateResult.put("affected_rows", updateCount);
                                updateResult.put("operation", "UPDATE");
                                results.add(updateResult);
                                if (verbose) {
                                    System.out.printf(" 🔄 UPDATE executed then rolled back (%d rows affected)%n", updateCount);
                                }
                                break;
                                
                            case "DELETE":
                                int deleteCount = session.delete(testInfo.sqlId, paramMap);
                                // Convert DELETE result to Map and return
                                Map<String, Object> deleteResult = new HashMap<>();
                                deleteResult.put("affected_rows", deleteCount);
                                deleteResult.put("operation", "DELETE");
                                results.add(deleteResult);
                                if (verbose) {
                                    System.out.printf(" 🔄 DELETE executed then rolled back (%d rows affected)%n", deleteCount);
                                }
                                break;
                                
                            default:
                                // Other SQL (CALL etc.) handled with selectList
                                results = session.selectList(testInfo.sqlId, paramMap);
                                break;
                        }
                        
                        // Always rollback for INSERT/UPDATE/DELETE (since this is test environment)
                        if (!testInfo.sqlType.equalsIgnoreCase("SELECT")) {
                            session.rollback();
                            if (verbose) {
                                System.out.printf(" ✅ Transaction rollback completed (data changes cancelled)%n");
                            }
                        }
                        
                    } catch (Exception e) {
                        // Rollback even when error occurs
                        if (!testInfo.sqlType.equalsIgnoreCase("SELECT")) {
                            try {
                                session.rollback();
                                if (verbose) {
                                    System.out.printf(" 🔄 Rollback completed due to error%n");
                                }
                            } catch (Exception rollbackException) {
                                System.err.println("Rollback failed: " + rollbackException.getMessage());
                            }
                        }
                        throw e;
                    }
                    
                    // Normalize results - remove differences between Oracle and PostgreSQL
                    results = ResultNormalizer.normalizeResults(results);
                    
                    return results;
                }
            }
            
        } finally {
            // Explicit temporary file deletion
            if (tempConfigFile != null && tempConfigFile.exists()) {
                if (!tempConfigFile.delete()) {
                    tempConfigFile.deleteOnExit(); // Delete on JVM exit if deletion fails
                }
            }
            if (tempMapperFile != null && tempMapperFile.exists()) {
                if (!tempMapperFile.delete()) {
                    tempMapperFile.deleteOnExit(); // Delete on JVM exit if deletion fails
                }
            }
        }
    }
    
    // Improved mapper file modification method (using DOM parser)
    private String modifyMapperContentWithDOM(Path xmlFile) throws Exception {
        try {
            // First check if it's a MyBatis XML file
            if (!isMyBatisXmlFile(xmlFile)) {
                throw new Exception("Not a MyBatis XML file: " + xmlFile.getFileName());
            }
            
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            // Disable DTD validation
            factory.setValidating(false);
            factory.setNamespaceAware(false);
            factory.setFeature("http://xml.org/sax/features/namespaces", false);
            factory.setFeature("http://xml.org/sax/features/validation", false);
            factory.setFeature("http://apache.org/xml/features/nonvalidating/load-dtd-grammar", false);
            factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
            
            DocumentBuilder builder = factory.newDocumentBuilder();
            Document doc = builder.parse(xmlFile.toFile());
            
            // Remove resultMap elements
            NodeList resultMaps = doc.getElementsByTagName("resultMap");
            for (int i = resultMaps.getLength() - 1; i >= 0; i--) {
                Element resultMap = (Element) resultMaps.item(i);
                resultMap.getParentNode().removeChild(resultMap);
            }
            
            // Modify SQL element attributes
            String[] sqlTypes = {"select", "insert", "update", "delete"};
            for (String sqlType : sqlTypes) {
                NodeList sqlNodes = doc.getElementsByTagName(sqlType);
                for (int i = 0; i < sqlNodes.getLength(); i++) {
                    Element sqlElement = (Element) sqlNodes.item(i);
                    
                    // Change resultMap attribute to resultType="map"
                    if (sqlElement.hasAttribute("resultMap")) {
                        sqlElement.removeAttribute("resultMap");
                        sqlElement.setAttribute("resultType", "map");
                    }
                    
                    // Change resultType to map (if existing)
                    if (sqlElement.hasAttribute("resultType") && !sqlElement.getAttribute("resultType").equals("map")) {
                        sqlElement.setAttribute("resultType", "map");
                    }
                    
                    // Change parameterType to map
                    if (sqlElement.hasAttribute("parameterType")) {
                        sqlElement.setAttribute("parameterType", "map");
                    }
                    
                    // Remove unnecessary attributes
                    sqlElement.removeAttribute("typeHandler");
                    sqlElement.removeAttribute("javaType");
                    sqlElement.removeAttribute("jdbcType");
                }
            }
            
            // Remove typeHandler attributes from all elements (parameter, result etc.)
            removeTypeHandlerAttributes(doc.getDocumentElement());
            
            // Convert DOM to string with proper DOCTYPE
            TransformerFactory transformerFactory = TransformerFactory.newInstance();
            Transformer transformer = transformerFactory.newTransformer();
            transformer.setOutputProperty("omit-xml-declaration", "no");
            transformer.setOutputProperty("encoding", "UTF-8");
            transformer.setOutputProperty("indent", "yes");
            
            StringWriter writer = new StringWriter();
            transformer.transform(new DOMSource(doc), new StreamResult(writer));
            
            String result = writer.toString();
            
            // Replace with correct DOCTYPE if missing or incorrect
            if (!result.contains("<!DOCTYPE mapper")) {
                // Insert correct DOCTYPE after XML declaration
                String xmlDeclaration = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>";
                String doctypeDeclaration = "<!DOCTYPE mapper PUBLIC \"-//mybatis.org//DTD Mapper 3.0//EN\" \"http://mybatis.org/dtd/mybatis-3-mapper.dtd\">";
                
                if (result.startsWith("<?xml")) {
                    int endOfXmlDecl = result.indexOf("?>") + 2;
                    String beforeMapper = result.substring(0, endOfXmlDecl);
                    String afterXmlDecl = result.substring(endOfXmlDecl).trim();
                    result = beforeMapper + "\n" + doctypeDeclaration + "\n" + afterXmlDecl;
                } else {
                    result = xmlDeclaration + "\n" + doctypeDeclaration + "\n" + result;
                }
            }
            
            return result;
            
        } catch (Exception e) {
            // Fallback to existing regex method when DOM parsing fails
            System.out.println("DOM modification failed, fallback to regex: " + xmlFile.getFileName());
            return modifyMapperContentWithRegex(xmlFile);
        }
    }
    
    // Existing regex method (for fallback) - applying comprehensive processing method from archived version
    private String modifyMapperContentWithRegex(Path xmlFile) throws IOException {
        String content = Files.readString(xmlFile);
        
        // 1. Remove entire resultMap definitions (process all at once with regex)
        content = content.replaceAll("(?s)<resultMap[^>]*>.*?</resultMap>", "");
        content = content.replaceAll("<resultMap[^>]*/\\s*>", "");
        
        // 2. Change resultMap references to resultType="map" (in attributes)
        content = content.replaceAll("resultMap\\s*=\\s*\"[^\"]*\"", "resultType=\"map\"");
        
        // 3. Remove nested resultMap references (inside parameters)
        content = content.replaceAll(",\\s*resultMap\\s*=\\s*[^}]+", "");
        
        // 4. Change resultType to map
        content = content.replaceAll("resultType\\s*=\\s*\"(?!map\")[^\"]*\"", "resultType=\"map\"");
        
        // 5. Change parameterType to map
        content = content.replaceAll("parameterType\\s*=\\s*\"[^\"]*\"", "parameterType=\"map\"");
        
        // 6. Remove typeHandler attributes (with quotes)
        content = content.replaceAll("\\s+typeHandler\\s*=\\s*\"[^\"]*\"", "");
        
        // 7. Remove typeHandler attributes (without quotes, inside parameters)
        content = content.replaceAll(",\\s*typeHandler\\s*=\\s*[^,}\\s]+", "");
        content = content.replaceAll("\\s+typeHandler\\s*=\\s*[^,}\\s]+", "");
        
        // 8. Remove javaType attributes
        content = content.replaceAll("\\s+javaType\\s*=\\s*\"[^\"]*\"", "");
        content = content.replaceAll(",\\s*javaType\\s*=\\s*[^,}]+", "");
        
        // 9. Remove jdbcType attributes
        content = content.replaceAll("\\s+jdbcType\\s*=\\s*\"[^\"]*\"", "");
        content = content.replaceAll(",\\s*jdbcType\\s*=\\s*[^,}]+", "");
        
        // 10. Simplify mode=OUT parameters (remove CURSOR type)
        content = content.replaceAll("mode\\s*=\\s*OUT\\s*,\\s*jdbcType\\s*=\\s*CURSOR[^}]*", "mode=OUT");
        
        // Check and fix DOCTYPE declaration
        if (!content.contains("<!DOCTYPE mapper")) {
            String xmlDeclaration = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>";
            String doctypeDeclaration = "<!DOCTYPE mapper PUBLIC \"-//mybatis.org//DTD Mapper 3.0//EN\" \"http://mybatis.org/dtd/mybatis-3-mapper.dtd\">";
            
            if (content.startsWith("<?xml")) {
                int endOfXmlDecl = content.indexOf("?>") + 2;
                String beforeMapper = content.substring(0, endOfXmlDecl);
                String afterXmlDecl = content.substring(endOfXmlDecl).trim();
                content = beforeMapper + "\n" + doctypeDeclaration + "\n" + afterXmlDecl;
            } else {
                content = xmlDeclaration + "\n" + doctypeDeclaration + "\n" + content;
            }
        } else {
            // Replace if existing DOCTYPE is incorrect
            content = content.replaceAll("<!DOCTYPE\\s+mapper[^>]*>", 
                "<!DOCTYPE mapper PUBLIC \"-//mybatis.org//DTD Mapper 3.0//EN\" \"http://mybatis.org/dtd/mybatis-3-mapper.dtd\">");
        }
        
        return content;
    }
    
    // Method to recursively remove typeHandler related attributes from all elements
    private void removeTypeHandlerAttributes(Element element) {
        // Remove typeHandler related attributes from current element
        element.removeAttribute("typeHandler");
        element.removeAttribute("javaType");
        element.removeAttribute("jdbcType");
        
        // Process child elements recursively
        NodeList children = element.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            if (child.getNodeType() == Node.ELEMENT_NODE) {
                removeTypeHandlerAttributes((Element) child);
            }
        }
    }
    
    // Method to check if file is MyBatis XML file
    private boolean isMyBatisXmlFile(Path xmlFile) {
        try {
            String content = Files.readString(xmlFile);
            
            // Check characteristics of MyBatis XML file
            boolean hasMapperTag = content.contains("<mapper") && content.contains("namespace=");
            boolean hasMyBatisDTD = content.contains("mybatis.org//DTD Mapper") || 
                                   content.contains("ibatis.apache.org//DTD Mapper");
            boolean hasSqlTags = content.contains("<select") || content.contains("<insert") || 
                                content.contains("<update") || content.contains("<delete");
            
            // Must have at least mapper tag and namespace
            return hasMapperTag && (hasMyBatisDTD || hasSqlTags);
            
        } catch (Exception e) {
            System.out.println("XML file validation failed: " + xmlFile.getFileName() + " - " + e.getMessage());
            return false;
        }
    }
    
    private String createMyBatisConfig(String xmlFilePath, String dbType) {
        switch (dbType.toLowerCase()) {
            case "oracle":
                return createOracleConfig(xmlFilePath);
            case "mysql":
                return createMySQLConfig(xmlFilePath);
            case "postgres":
            case "postgresql":
            case "pg":
                return createPostgreSQLConfig(xmlFilePath);
            default:
                throw new RuntimeException("Unsupported database type: " + dbType + 
                    ". Supported types: oracle, mysql, postgres");
        }
    }
    
    private String createOracleConfig(String xmlFilePath) {
        String connectString = System.getenv("ORACLE_SVC_CONNECT_STRING");
        String username = System.getenv("ORACLE_SVC_USER");
        String password = System.getenv("ORACLE_SVC_PASSWORD");
        String host = System.getenv("ORACLE_HOST");
        String port = System.getenv("ORACLE_PORT");
        String sid = System.getenv("ORACLE_SID");
        String tnsAdmin = System.getenv("TNS_ADMIN");
        String oracleHome = System.getenv("ORACLE_HOME");
        
        if (username == null || password == null) {
            throw new RuntimeException("Oracle environment variables not set. Required variables: ORACLE_SVC_USER, ORACLE_SVC_PASSWORD");
        }
        
        // Automatic TNS_ADMIN setup (improved logic)
        if (tnsAdmin == null && oracleHome != null) {
            tnsAdmin = oracleHome + "/network/admin";
            System.setProperty("oracle.net.tns_admin", tnsAdmin);
            System.out.println("TNS_ADMIN automatically set: " + tnsAdmin);
        }
        
        String jdbcUrl;
        
        // Support Oracle 12c and later PDB environment
        if (host != null && port != null && sid != null) {
            // Service Name method (PDB environment)
            jdbcUrl = "jdbc:oracle:thin:@//" + host + ":" + port + "/" + sid;
            System.out.println("Using Oracle PDB connection method: " + jdbcUrl);
        } else if (tnsAdmin != null && connectString != null) {
            // Use TNS name
            jdbcUrl = "jdbc:oracle:thin:@" + connectString;
            System.out.println("Using Oracle TNS connection method: " + jdbcUrl);
        } else {
            // Basic connection method (fallback)
            String defaultService = config.getProperty("oracle.default.service", "orcl");
            jdbcUrl = "jdbc:oracle:thin:@" + (connectString != null ? connectString : defaultService);
            System.out.println("Using Oracle basic connection method: " + jdbcUrl);
        }
        
        String driverClass = config.getProperty("db.oracle.driver", "oracle.jdbc.driver.OracleDriver");
        return createConfigXml(xmlFilePath, driverClass, jdbcUrl, username, password);
    }
    
    private String createMySQLConfig(String xmlFilePath) {
        String host = System.getenv("MYSQL_HOST");
        String port = System.getenv("MYSQL_TCP_PORT");
        String database = System.getenv("MYSQL_DB");
        String username = System.getenv("MYSQL_ADM_USER");
        String password = System.getenv("MYSQL_PASSWORD");
        
        if (username == null || password == null) {
            throw new RuntimeException("MySQL environment variables not set. Required variables: MYSQL_ADM_USER, MYSQL_PASSWORD");
        }
        
        // Set default values (read from configuration file)
        if (host == null) host = config.getProperty("mysql.default.host", "localhost");
        if (port == null) port = config.getProperty("mysql.default.port", "3306");
        if (database == null) database = config.getProperty("mysql.default.database", "test");
        
        String options = config.getProperty("mysql.default.options", "useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC");
        
        // Encode & character as &amp; in XML
        String jdbcUrl = String.format("jdbc:mysql://%s:%s/%s?%s", 
            host, port, database, options.replace("&", "&amp;"));
        
        String driverClass = config.getProperty("db.mysql.driver", "com.mysql.cj.jdbc.Driver");
        return createConfigXml(xmlFilePath, driverClass, jdbcUrl, username, password);
    }
    
    private String createPostgreSQLConfig(String xmlFilePath) {
        String host = System.getenv("PGHOST");
        String port = System.getenv("PGPORT");
        String database = System.getenv("PGDATABASE");
        String username = System.getenv("PGUSER");
        String password = System.getenv("PGPASSWORD");
        
        if (username == null || password == null) {
            throw new RuntimeException("PostgreSQL environment variables not set. Required variables: PGUSER, PGPASSWORD");
        }
        
        // Set default values (read from configuration file)
        if (host == null) host = config.getProperty("postgresql.default.host", "localhost");
        if (port == null) port = config.getProperty("postgresql.default.port", "5432");
        if (database == null) database = config.getProperty("postgresql.default.database", "postgres");
        
        String jdbcUrl = String.format("jdbc:postgresql://%s:%s/%s", host, port, database);
        
        String driverClass = config.getProperty("db.postgresql.driver", "org.postgresql.Driver");
        return createConfigXml(xmlFilePath, driverClass, jdbcUrl, username, password);
    }
    
    private String createConfigXml(String xmlFilePath, String driverClass, String jdbcUrl, String username, String password) {
        File xmlFile = new File(xmlFilePath);
        String absolutePath = xmlFile.getAbsolutePath();
        
        String mapUnderscoreToCamelCase = config.getProperty("mybatis.mapUnderscoreToCamelCase", "true");
        String transactionManager = config.getProperty("mybatis.transactionManager", "JDBC");
        String dataSource = config.getProperty("mybatis.dataSource", "POOLED");
        
        return "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n" +
               "<!DOCTYPE configuration PUBLIC \"-//mybatis.org//DTD Config 3.0//EN\" \"http://mybatis.org/dtd/mybatis-3-config.dtd\">\n" +
               "<configuration>\n" +
               "  <settings>\n" +
               "    <setting name=\"mapUnderscoreToCamelCase\" value=\"" + mapUnderscoreToCamelCase + "\"/>\n" +
               "    <setting name=\"jdbcTypeForNull\" value=\"VARCHAR\"/>\n" +
               "    <setting name=\"callSettersOnNulls\" value=\"true\"/>\n" +
               "  </settings>\n" +
               "  <environments default=\"development\">\n" +
               "    <environment id=\"development\">\n" +
               "      <transactionManager type=\"" + transactionManager + "\"/>\n" +
               "      <dataSource type=\"" + dataSource + "\">\n" +
               "        <property name=\"driver\" value=\"" + driverClass + "\"/>\n" +
               "        <property name=\"url\" value=\"" + jdbcUrl + "\"/>\n" +
               "        <property name=\"username\" value=\"" + username + "\"/>\n" +
               "        <property name=\"password\" value=\"" + password + "\"/>\n" +
               "      </dataSource>\n" +
               "    </environment>\n" +
               "  </environments>\n" +
               "  <mappers>\n" +
               "    <mapper url=\"file://" + absolutePath + "\"/>\n" +
               "  </mappers>\n" +
               "</configuration>";
    }
    
    private void printResults(TestResults results, boolean summaryOnly, boolean verbose) {
        int actualTests = (int) results.allResults.stream().filter(r -> r.rowCount != -1).count();
        int skippedTests = (int) results.allResults.stream().filter(r -> r.rowCount == -1).count();
        
        System.out.println("=== Execution Results Summary ===");
        System.out.println("Total tests: " + results.totalTests);
        System.out.println("Actually executed: " + actualTests + " tests");
        System.out.println("Skipped: " + skippedTests + " tests (Example patterns)");
        System.out.println("Success: " + results.successCount + " tests");
        System.out.println("Failed: " + results.failureCount + " tests");
        if (actualTests > 0) {
            double actualSuccessRate = (results.successCount * 100.0 / actualTests);
            System.out.printf("Actual success rate: %.1f%% (excluding skipped)%n", actualSuccessRate);
        }
        
        if (!results.failures.isEmpty()) {
            System.out.println();
            System.out.println("=== Failed Tests ===");
            for (TestResult failure : results.failures) {
                System.out.printf("❌ %s:%s - %s%n", 
                    failure.testInfo.xmlFile.getFileName(),
                    failure.testInfo.sqlId,
                    failure.errorMessage);
            }
        }
        
        // File statistics
        System.out.println();
        System.out.println("=== File Statistics ===");
        Map<String, FileStats> fileStats = calculateFileStats(results);
        for (Map.Entry<String, FileStats> entry : fileStats.entrySet()) {
            FileStats stats = entry.getValue();
            System.out.printf("  %s: %d/%d (%.1f%%) [skipped: %d]%n", 
                entry.getKey(), stats.success, stats.total - stats.skipped, 
                stats.getActualSuccessRate(), stats.skipped);
        }
    }
    
    private Map<String, FileStats> calculateFileStats(TestResults results) {
        Map<String, FileStats> statsMap = new HashMap<>();
        
        for (TestResult result : results.allResults) {
            String fileName = result.testInfo.xmlFile.getFileName().toString();
            FileStats stats = statsMap.computeIfAbsent(fileName, k -> new FileStats());
            stats.total++;
            
            if (result.rowCount == -1) {
                // Skipped case
                stats.skipped++;
            } else if (result.success) {
                stats.success++;
            } else {
                stats.failure++;
            }
        }
        
        return statsMap;
    }
    
    /**
     * Save SQL information to Repository
     */
    private void saveSqlInfoToRepository(List<SqlTestInfo> sqlTests, SqlListRepository repository, Properties parameters, String dbType) {
        System.out.println("=== SQL Information Save Started ===");
        
        for (SqlTestInfo testInfo : sqlTests) {
            try {
                // Extract parameters
                String sqlContent = extractSqlContent(testInfo.xmlFile, testInfo.sqlId);
                Set<String> paramSet = extractParametersFromSql(sqlContent);
                String paramList = repository.formatParameterList(paramSet);
                
                // Extract mapper name
                String mapperName = extractMapperName(testInfo.xmlFile);
                String fullSqlId = mapperName + "." + testInfo.sqlId;
                
                // Use actual mapper file path
                String actualFilePath = testInfo.xmlFile.toString();
                
                if ("oracle".equalsIgnoreCase(dbType)) {
                    // Save source information for Oracle
                    repository.saveSqlInfo(
                        fullSqlId,
                        testInfo.sqlType,
                        actualFilePath != null ? actualFilePath : testInfo.xmlFile.toString(),
                        sqlContent,
                        paramList
                    );
                } else {
                    // Update target information for PostgreSQL/MySQL
                    repository.updateTargetInfo(
                        fullSqlId,
                        actualFilePath != null ? actualFilePath : testInfo.xmlFile.toString(),
                        sqlContent,
                        paramList
                    );
                }
                
            } catch (Exception e) {
                System.err.println("SQL information save failed (" + testInfo.sqlId + "): " + e.getMessage());
            }
        }
        
        System.out.println("SQL information save completed: " + sqlTests.size() + " records");
        System.out.println();
    }
    
    /**
     * Extract mapper name from file path
     */
    private String extractMapperName(Path xmlFile) {
        try {
            String fileName = xmlFile.getFileName().toString();
            
            // Remove .xml extension
            if (fileName.endsWith(".xml")) {
                fileName = fileName.substring(0, fileName.length() - 4);
            }
            
            return fileName;
        } catch (Exception e) {
            return "Unknown";
        }
    }
    
    /**
     * Extract specific SQL ID content from XML file
     */
    private String extractSqlContent(Path xmlFile, String sqlId) {
        try {
            String content = Files.readString(xmlFile);
            
            // Extract content of corresponding SQL ID using regex
            String pattern = "<(select|insert|update|delete)\\s+id=\"" + sqlId + "\"[^>]*>(.*?)</(select|insert|update|delete)>";
            java.util.regex.Pattern p = java.util.regex.Pattern.compile(pattern, java.util.regex.Pattern.DOTALL | java.util.regex.Pattern.CASE_INSENSITIVE);
            java.util.regex.Matcher m = p.matcher(content);
            
            if (m.find()) {
                return m.group(2).trim();
            }
            
            return "SQL content extraction failed";
            
        } catch (Exception e) {
            return "SQL content extraction error: " + e.getMessage();
        }
    }
    
    /**
     * Extract parameters from SQL
     */
    private Set<String> extractParametersFromSql(String sqlContent) {
        Set<String> parameters = new HashSet<>();
        
        // Extract #{} parameters
        java.util.regex.Pattern paramPattern = java.util.regex.Pattern.compile("#\\{([^}]+)\\}");
        java.util.regex.Matcher matcher = paramPattern.matcher(sqlContent);
        while (matcher.find()) {
            String param = matcher.group(1);
            // Handle composite parameters (user.name -> user)
            if (param.contains(".")) {
                param = param.substring(0, param.indexOf("."));
            }
            if (param.contains("[")) {
                param = param.substring(0, param.indexOf("["));
            }
            parameters.add(param.trim());
        }
        
        // Extract ${} parameters
        java.util.regex.Pattern dollarPattern = java.util.regex.Pattern.compile("\\$\\{([^}]+)\\}");
        java.util.regex.Matcher dollarMatcher = dollarPattern.matcher(sqlContent);
        while (dollarMatcher.find()) {
            String param = dollarMatcher.group(1);
            // Handle composite parameters
            if (param.contains(".")) {
                param = param.substring(0, param.indexOf("."));
            }
            if (param.contains("[")) {
                param = param.substring(0, param.indexOf("["));
            }
            parameters.add(param.trim());
        }
        
        return parameters;
    }
    
    /**
     * Perform result comparison and output statistics
     */
    private void performResultComparison(SqlListRepository repository) {
        System.out.println("=== SQL Result Comparison Started ===");
        
        try {
            // Perform result comparison
            repository.compareAndUpdateResults();
            
            // Output statistics
            Map<String, Integer> stats = repository.getComparisonStatistics();
            
            System.out.println();
            System.out.println("=== SQL Comparison Verification Final Statistics ===");
            System.out.println("Total SQL count: " + stats.getOrDefault("total", 0));
            System.out.println("Results identical: " + stats.getOrDefault("same", 0) + " records");
            System.out.println("Results different: " + stats.getOrDefault("different", 0) + " records");
            System.out.println("Comparison pending: " + stats.getOrDefault("pending", 0) + " records");
            System.out.println("Missing source results: " + stats.getOrDefault("missing_src", 0) + " records");
            System.out.println("Missing target results: " + stats.getOrDefault("missing_tgt", 0) + " records");
            System.out.println("Both results available: " + stats.getOrDefault("both_results", 0) + " records");
            
            int total = stats.getOrDefault("total", 0);
            int same = stats.getOrDefault("same", 0);
            if (total > 0) {
                double successRate = (same * 100.0) / total;
                System.out.printf("Success rate: %.1f%%\n", successRate);
            }
            
            // Output detailed information when there are missing results
            int missingSrc = stats.getOrDefault("missing_src", 0);
            int missingTgt = stats.getOrDefault("missing_tgt", 0);
            if (missingSrc > 0 || missingTgt > 0) {
                System.out.println();
                System.out.println("=== Missing Results Detailed Analysis ===");
                printMissingResults(repository);
            }
            
        } catch (Exception e) {
            System.err.println("Error occurred during result comparison: " + e.getMessage());
        }
        
        System.out.println();
    }
    
    /**
     * Detailed analysis of missing results
     */
    private void printMissingResults(SqlListRepository repository) {
        try (Connection conn = repository.getTargetConnection()) {
            // SQLs with missing source results
            String missingSrcSql = "SELECT sql_id, sql_type FROM sqllist WHERE src_result IS NULL ORDER BY sql_id";
            try (PreparedStatement pstmt = conn.prepareStatement(missingSrcSql);
                 ResultSet rs = pstmt.executeQuery()) {
                
                System.out.println("SQLs with missing source results:");
                while (rs.next()) {
                    System.out.println("  - " + rs.getString("sql_id") + " (" + rs.getString("sql_type") + ")");
                }
            }
            
            // SQLs with missing target results
            String missingTgtSql = "SELECT sql_id, sql_type FROM sqllist WHERE tgt_result IS NULL ORDER BY sql_id";
            try (PreparedStatement pstmt = conn.prepareStatement(missingTgtSql);
                 ResultSet rs = pstmt.executeQuery()) {
                
                System.out.println("SQLs with missing target results:");
                while (rs.next()) {
                    System.out.println("  - " + rs.getString("sql_id") + " (" + rs.getString("sql_type") + ")");
                }
            }
            
        } catch (Exception e) {
            System.err.println("Missing results analysis failed: " + e.getMessage());
        }
    }
    private static class SqlTestInfo {
        Path xmlFile;
        String sqlId;
        String sqlType;
    }
    
    private static class TestResult {
        SqlTestInfo testInfo;
        boolean success;
        int rowCount;
        String errorMessage;
        List<Map<String, Object>> resultData;
    }
    
    private static class TestResults {
        List<TestResult> allResults = new ArrayList<>();
        List<TestResult> failures = new ArrayList<>();
        int totalTests = 0;
        int successCount = 0;
        int failureCount = 0;
        
        void addResult(TestResult result) {
            allResults.add(result);
            totalTests++;
            if (result.success) {
                successCount++;
            } else {
                failureCount++;
                failures.add(result);
            }
        }
        
        double getSuccessRate() {
            return totalTests > 0 ? (successCount * 100.0 / totalTests) : 0;
        }
    }
    
    /**
     * Convert parameter value to appropriate type
     */
    private Object convertParameterValue(String key, String value) {
        if (value == null || value.trim().isEmpty()) {
            return "1"; // Default value
        }
        
        String lowerKey = key.toLowerCase();
        
        // Try to convert ID-related parameters to numbers
        if (lowerKey.endsWith("id") || lowerKey.equals("limit") || lowerKey.equals("offset") || 
            lowerKey.equals("page") || lowerKey.equals("size") || lowerKey.equals("count") ||
            lowerKey.equals("quantity") || lowerKey.equals("amount") || lowerKey.equals("price") ||
            lowerKey.equals("year") || lowerKey.equals("month") || lowerKey.equals("day") ||
            lowerKey.equals("days") || lowerKey.equals("version") || lowerKey.equals("enabled") ||
            lowerKey.equals("active") || lowerKey.equals("deleted")) {
            
            try {
                return Long.parseLong(value);
            } catch (NumberFormatException e) {
                // Return as string if number conversion fails
                return value;
            }
        }
        
        // Keep date-related parameters as strings
        if (lowerKey.contains("date") || lowerKey.contains("time")) {
            return value;
        }
        
        // Return as string by default
        return value;
    }
    
    /**
     * Clean parameter values for MyBatis bind variables
     * Remove quotes from properties file so MyBatis can handle them correctly
     */
    private String cleanParameterValue(String value) {
        if (value == null || value.trim().isEmpty()) {
            return "1"; // Set default value "1" for null or empty values
        }
        
        String cleanValue = value.trim();
        
        // Remove if wrapped in single quotes
        if (cleanValue.startsWith("'") && cleanValue.endsWith("'") && cleanValue.length() > 1) {
            cleanValue = cleanValue.substring(1, cleanValue.length() - 1);
        }
        
        // Set default value if still empty
        if (cleanValue.isEmpty()) {
            cleanValue = "1";
        }
        
        return cleanValue;
    }
    
    private static class FileStats {
        int total = 0;
        int success = 0;
        int failure = 0;
        int skipped = 0;
        
        double getSuccessRate() {
            return total > 0 ? (success * 100.0 / total) : 0;
        }
        
        double getActualSuccessRate() {
            int actualTests = total - skipped;
            return actualTests > 0 ? (success * 100.0 / actualTests) : 0;
        }
    }
}
