package com.test.mybatis;

import org.apache.ibatis.io.Resources;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;

import java.io.*;
import java.util.*;

/**
 * Simple SQL execution program using MyBatis
 * Automatically handles dynamic conditions with just a parameter file.
 */
public class MyBatisSimpleExecutor {
    
    private static final String PARAMETERS_FILE = "parameters.properties";
    
    public static void main(String[] args) {
        if (args.length < 2) {
            System.out.println("Usage: java MyBatisSimpleExecutor <XML_file_path> <SQL_ID>");
            System.out.println("Example: java MyBatisSimpleExecutor /path/to/mapper.xml selectInventoryStatusAnalysis");
            System.out.println("Oracle environment variables must be set (ORACLE_SVC_USER, ORACLE_SVC_PASSWORD).");
            System.out.println("Must be able to connect to orcl from tnsnames.");
            return;
        }
        
        String xmlFilePath = args[0];
        String sqlId = args[1];
        
        MyBatisSimpleExecutor executor = new MyBatisSimpleExecutor();
        executor.executeWithMyBatis(xmlFilePath, sqlId);
    }
    
    public void executeWithMyBatis(String xmlFilePath, String sqlId) {
        try {
            System.out.println("=== MyBatis Simple Execution Program ===");
            System.out.println("XML file: " + xmlFilePath);
            System.out.println("SQL ID: " + sqlId);
            
            // 1. Parameter loading
            Map<String, Object> parameters = loadParameters();
            System.out.println("\n=== Loaded parameters ===");
            parameters.forEach((key, value) -> 
                System.out.println(key + " = " + value));
            
            // 2. Create MyBatis configuration
            SqlSessionFactory sqlSessionFactory = createSqlSessionFactory(xmlFilePath);
            
            // 3. Execute SQL
            try (SqlSession session = sqlSessionFactory.openSession()) {
                System.out.println("\n=== Execute SQL ===");
                
                // Execute directly with SQL ID (MyBatis automatically handles dynamic conditions)
                List<Map<String, Object>> results = session.selectList(sqlId, parameters);
                
                System.out.println("Execution result:");
                if (results.isEmpty()) {
                    System.out.println("No results found.");
                } else {
                    // Output column names from first row
                    Map<String, Object> firstRow = results.get(0);
                    System.out.println("Columns: " + String.join(", ", firstRow.keySet()));
                    System.out.println("─".repeat(80));
                    
                    // Output data (maximum 10 rows)
                    int count = 0;
                    for (Map<String, Object> row : results) {
                        if (count >= 10) {
                            System.out.println("... (showing first 10 rows only, total " + results.size() + " rows)");
                            break;
                        }
                        
                        // Output each column value separated by tabs
                        List<String> values = new ArrayList<>();
                        for (Object value : row.values()) {
                            values.add(value != null ? value.toString() : "NULL");
                        }
                        System.out.println(String.join("\t", values));
                        count++;
                    }
                    System.out.println("\nTotal " + results.size() + " rows retrieved.");
                }
            }
            
        } catch (Exception e) {
            System.err.println("Error occurred: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    /**
     * Load parameter file
     */
    private Map<String, Object> loadParameters() throws IOException {
        Map<String, Object> paramMap = new HashMap<>();
        Properties props = new Properties();
        
        File file = new File(PARAMETERS_FILE);
        if (!file.exists()) {
            System.out.println("Parameter file not found: " + PARAMETERS_FILE);
            return paramMap;
        }
        
        try (FileInputStream fis = new FileInputStream(file)) {
            props.load(fis);
        }
        
        // Convert Properties to Map with type conversion
        for (String key : props.stringPropertyNames()) {
            String value = props.getProperty(key);
            if (value == null || value.trim().isEmpty()) {
                paramMap.put(key, null);
            } else {
                // Check if it's a number
                if (isNumeric(value)) {
                    try {
                        if (value.contains(".")) {
                            paramMap.put(key, Double.parseDouble(value));
                        } else {
                            paramMap.put(key, Long.parseLong(value));
                        }
                    } catch (NumberFormatException e) {
                        paramMap.put(key, value);
                    }
                } else {
                    paramMap.put(key, value);
                }
            }
        }
        
        return paramMap;
    }
    
    /**
     * Check if string is numeric
     */
    private boolean isNumeric(String str) {
        try {
            Double.parseDouble(str);
            return true;
        } catch (NumberFormatException e) {
            return false;
        }
    }
    
    /**
     * Create MyBatis SqlSessionFactory
     */
    private SqlSessionFactory createSqlSessionFactory(String xmlFilePath) throws IOException {
        // Set TNS_ADMIN environment variable
        String oracleHome = System.getenv("ORACLE_HOME");
        if (oracleHome != null) {
            String tnsAdmin = oracleHome + "/network/admin";
            System.setProperty("oracle.net.tns_admin", tnsAdmin);
            System.setProperty("TNS_ADMIN", tnsAdmin);  // Additional setting
            System.out.println("TNS_ADMIN set: " + tnsAdmin);
            
            // Check if tnsnames.ora file exists
            File tnsnamesFile = new File(tnsAdmin + "/tnsnames.ora");
            if (tnsnamesFile.exists()) {
                System.out.println("tnsnames.ora file confirmed: " + tnsnamesFile.getAbsolutePath());
            } else {
                System.out.println("Warning: tnsnames.ora file not found: " + tnsnamesFile.getAbsolutePath());
            }
        } else {
            System.out.println("Warning: ORACLE_HOME environment variable not set.");
        }
        
        // 1. Read original XML file and change resultType to map
        String modifiedXmlContent = modifyXmlForTesting(xmlFilePath);
        
        // 2. Save modified XML as temporary file
        File tempXmlFile = File.createTempFile("mapper", ".xml");
        tempXmlFile.deleteOnExit();
        
        try (FileWriter writer = new FileWriter(tempXmlFile)) {
            writer.write(modifiedXmlContent);
        }
        
        // 3. Generate MyBatis configuration XML
        String configXml = createMyBatisConfig(tempXmlFile.getAbsolutePath());
        
        // 4. Generate temporary configuration file
        File tempConfigFile = File.createTempFile("mybatis-config", ".xml");
        tempConfigFile.deleteOnExit();
        
        try (FileWriter writer = new FileWriter(tempConfigFile)) {
            writer.write(configXml);
        }
        
        // 5. Create SqlSessionFactory
        try (InputStream inputStream = new FileInputStream(tempConfigFile)) {
            return new SqlSessionFactoryBuilder().build(inputStream);
        }
    }
    
    /**
     * Modify XML file's resultType for testing
     */
    private String modifyXmlForTesting(String xmlFilePath) throws IOException {
        StringBuilder content = new StringBuilder();
        
        try (BufferedReader reader = new BufferedReader(new FileReader(xmlFilePath))) {
            String line;
            while ((line = reader.readLine()) != null) {
                // Change resultType to map
                if (line.contains("resultType=")) {
                    line = line.replaceAll("resultType=\"[^\"]*\"", "resultType=\"map\"");
                }
                // Change parameterType to map as well
                if (line.contains("parameterType=")) {
                    line = line.replaceAll("parameterType=\"[^\"]*\"", "parameterType=\"map\"");
                }
                content.append(line).append("\n");
            }
        }
        
        return content.toString();
    }
    
    /**
     * Generate MyBatis configuration XML (using Oracle environment variables)
     */
    private String createMyBatisConfig(String xmlFilePath) {
        // Configure connection info from Oracle environment variables
        String connectString = System.getenv("ORACLE_SVC_CONNECT_STRING");
        String username = System.getenv("ORACLE_SVC_USER");
        String password = System.getenv("ORACLE_SVC_PASSWORD");
        
        if (username == null || password == null) {
            throw new RuntimeException("Oracle environment variables not set. Required variables: ORACLE_SVC_USER, ORACLE_SVC_PASSWORD");
        }
        
        // Configure JDBC URL using tnsnames method (possible since TNS_ADMIN is set)
        String jdbcUrl = "jdbc:oracle:thin:@" + (connectString != null ? connectString : "orcl");
        
        System.out.println("Oracle connection info:");
        System.out.println("  JDBC URL: " + jdbcUrl);
        System.out.println("  User: " + username);
        
        // Convert to absolute path
        File xmlFile = new File(xmlFilePath);
        String absolutePath = xmlFile.getAbsolutePath();
        
        return "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n" +
               "<!DOCTYPE configuration PUBLIC \"-//mybatis.org//DTD Config 3.0//EN\" \"http://mybatis.org/dtd/mybatis-3-config.dtd\">\n" +
               "<configuration>\n" +
               "  <settings>\n" +
               "    <setting name=\"mapUnderscoreToCamelCase\" value=\"true\"/>\n" +
               "  </settings>\n" +
               "  <environments default=\"development\">\n" +
               "    <environment id=\"development\">\n" +
               "      <transactionManager type=\"JDBC\"/>\n" +
               "      <dataSource type=\"POOLED\">\n" +
               "        <property name=\"driver\" value=\"oracle.jdbc.driver.OracleDriver\"/>\n" +
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
}
