package com.oma.validator;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * PostgreSQL database executor
 * Executes MyBatis mappers against PostgreSQL database with auto-rollback
 */
public class PostgresExecutor implements DatabaseExecutor {

    private final SqlSessionFactory sqlSessionFactory;
    private final ObjectMapper objectMapper;
    private final String mapperDir;
    private Extension extension;
    private String dbType;

    public PostgresExecutor(String mapperDir) throws Exception {
        this.mapperDir = mapperDir;
        this.objectMapper = new ObjectMapper()
                .enable(SerializationFeature.INDENT_OUTPUT)
                .enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS);

        // Create MyBatis configuration
        this.sqlSessionFactory = createSqlSessionFactory();
    }

    private SqlSessionFactory createSqlSessionFactory() throws Exception {
        // Process mapper files with Extension variable substitution if enabled
        String actualMapperDir = mapperDir;
        if (extension != null && extension.isEnabled()) {
            actualMapperDir = processMapperFilesWithExtension();
        }

        // Get PostgreSQL connection parameters from environment (using standard PostgreSQL variable names)
        String host = getEnvOrDefault("PGHOST", "localhost");
        String port = getEnvOrDefault("PGPORT", "5432");
        String database = getEnvOrDefault("PGDATABASE", "postgres");
        String username = getEnvOrDefault("PGUSER", "postgres");
        String password = getEnvOrDefault("PGPASSWORD", "postgres");

        String jdbcUrl = String.format("jdbc:postgresql://%s:%s/%s", host, port, database);

        // Create temporary MyBatis config file
        String configXml = createMyBatisConfig(jdbcUrl, username, password, "org.postgresql.Driver", actualMapperDir);
        File tempConfig = File.createTempFile("mybatis-config-postgres-", ".xml");
        tempConfig.deleteOnExit();

        try (FileWriter writer = new FileWriter(tempConfig)) {
            writer.write(configXml);
        }

        // Build SqlSessionFactory
        try (InputStream inputStream = new java.io.FileInputStream(tempConfig)) {
            return new SqlSessionFactoryBuilder().build(inputStream);
        }
    }

    private String createMyBatisConfig(String jdbcUrl, String username, String password, String driver, String mapperDirectory) {
        StringBuilder xml = new StringBuilder();
        xml.append("<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n");
        xml.append("<!DOCTYPE configuration PUBLIC \"-//mybatis.org//DTD Config 3.0//EN\" ");
        xml.append("\"http://mybatis.org/dtd/mybatis-3-config.dtd\">\n");
        xml.append("<configuration>\n");
        xml.append("  <settings>\n");
        xml.append("    <setting name=\"mapUnderscoreToCamelCase\" value=\"true\"/>\n");
        xml.append("    <setting name=\"callSettersOnNulls\" value=\"true\"/>\n");
        xml.append("    <setting name=\"jdbcTypeForNull\" value=\"NULL\"/>\n");
        xml.append("  </settings>\n");

        // TypeAliases - camelMap is always needed
        xml.append("  <typeAliases>\n");
        xml.append("    <typeAlias type=\"java.util.HashMap\" alias=\"camelMap\"/>\n");
        xml.append("  </typeAliases>\n");
        xml.append("  <environments default=\"development\">\n");
        xml.append("    <environment id=\"development\">\n");
        xml.append("      <transactionManager type=\"JDBC\"/>\n");
        xml.append("      <dataSource type=\"POOLED\">\n");
        xml.append("        <property name=\"driver\" value=\"").append(driver).append("\"/>\n");
        xml.append("        <property name=\"url\" value=\"").append(jdbcUrl).append("\"/>\n");
        xml.append("        <property name=\"username\" value=\"").append(username).append("\"/>\n");
        xml.append("        <property name=\"password\" value=\"").append(password).append("\"/>\n");
        xml.append("      </dataSource>\n");
        xml.append("    </environment>\n");
        xml.append("  </environments>\n");
        xml.append("  <mappers>\n");

        // Add all mapper XML files from directory
        File mapperDirFile = new File(mapperDirectory);
        if (mapperDirFile.exists() && mapperDirFile.isDirectory()) {
            addMapperFiles(xml, mapperDirFile, mapperDirFile);
        }

        xml.append("  </mappers>\n");
        xml.append("</configuration>");

        return xml.toString();
    }

    private void addMapperFiles(StringBuilder xml, File directory, File baseDir) {
        File[] files = directory.listFiles();
        if (files != null) {
            for (File file : files) {
                if (file.isDirectory()) {
                    addMapperFiles(xml, file, baseDir);
                } else if (file.getName().endsWith(".xml")) {
                    String absolutePath = file.getAbsolutePath().replace("\\", "/");
                    xml.append("    <mapper url=\"file:///").append(absolutePath).append("\"/>\n");
                }
            }
        }
    }

    @Override
    public void setExtension(Extension extension, String dbType) {
        this.extension = extension;
        this.dbType = dbType;
    }

    public String execute(String sqlId, Map<String, Object> params) throws Exception {
        // Apply Extension variable substitution
        if (extension != null && extension.isEnabled()) {
            params = applyExtension(params);
        }

        // Open session with autoCommit=false
        try (SqlSession session = sqlSessionFactory.openSession(false)) {
            Object result;

            try {
                // Determine statement type from SQL ID
                String statementType = determineStatementType(sqlId);

                switch (statementType) {
                    case "select":
                        // SELECT statements return List<Map>
                        List<?> selectResult = session.selectList(sqlId, params);
                        result = selectResult;
                        break;

                    case "insert":
                        // INSERT returns affected row count
                        int insertCount = session.insert(sqlId, params);
                        result = Collections.singletonMap("affected_rows", insertCount);
                        break;

                    case "update":
                        // UPDATE returns affected row count
                        int updateCount = session.update(sqlId, params);
                        result = Collections.singletonMap("affected_rows", updateCount);
                        break;

                    case "delete":
                        // DELETE returns affected row count
                        int deleteCount = session.delete(sqlId, params);
                        result = Collections.singletonMap("affected_rows", deleteCount);
                        break;

                    default:
                        // Try selectOne for other types
                        result = session.selectOne(sqlId, params);
                        break;
                }

                // Always rollback to ensure no data changes
                session.rollback();

                // Convert result to JSON
                return objectMapper.writeValueAsString(result);

            } catch (Exception e) {
                // Ensure rollback on error
                session.rollback();
                throw new Exception("PostgreSQL execution failed for " + sqlId + ": " + e.getMessage(), e);
            }
        }
    }

    private String determineStatementType(String sqlId) {
        // Extract statement type from SQL ID or mapper configuration
        // This is a simple heuristic - in production, you'd inspect the mapper XML
        String lowerSqlId = sqlId.toLowerCase();

        if (lowerSqlId.contains("select") || lowerSqlId.contains("get") ||
            lowerSqlId.contains("find") || lowerSqlId.contains("list")) {
            return "select";
        } else if (lowerSqlId.contains("insert") || lowerSqlId.contains("create")) {
            return "insert";
        } else if (lowerSqlId.contains("update") || lowerSqlId.contains("modify")) {
            return "update";
        } else if (lowerSqlId.contains("delete") || lowerSqlId.contains("remove")) {
            return "delete";
        }

        // Default to select
        return "select";
    }

    /**
     * Process mapper XML files with Extension variable substitution
     * Creates temporary directory with modified mapper files
     * @return Path to temporary mapper directory
     */
    private String processMapperFilesWithExtension() throws IOException {
        // Create temporary directory for processed mappers
        File tempDir = Files.createTempDirectory("mappers-postgres-").toFile();
        tempDir.deleteOnExit();

        // Process all XML files in mapper directory
        File sourceDir = new File(mapperDir);
        processMapperDirectory(sourceDir, tempDir, sourceDir);

        return tempDir.getAbsolutePath();
    }

    /**
     * Recursively process mapper directory
     */
    private void processMapperDirectory(File sourceDir, File targetDir, File baseDir) throws IOException {
        File[] files = sourceDir.listFiles();
        if (files == null) return;

        for (File file : files) {
            if (file.isDirectory()) {
                File newTargetDir = new File(targetDir, file.getName());
                newTargetDir.mkdir();
                processMapperDirectory(file, newTargetDir, baseDir);
            } else if (file.getName().endsWith(".xml")) {
                // Process mapper XML file
                String content = new String(Files.readAllBytes(file.toPath()), "UTF-8");

                // Substitute Extension variables (String values only for XML substitution)
                for (String varName : extension.getVariableNames()) {
                    Object value = extension.getValue(varName, dbType);
                    if (value != null && value instanceof String) {
                        // Replace #{varName} with actual SQL fragment (String only)
                        content = content.replace("#{" + varName + "}", (String) value);
                    }
                    // List values are not substituted in XML, they are passed as parameters
                }

                // Write to temporary file
                File targetFile = new File(targetDir, file.getName());
                targetFile.deleteOnExit();
                Files.write(targetFile.toPath(), content.getBytes("UTF-8"));
            }
        }
    }

    /**
     * Apply Extension variable substitution to parameters
     */
    private Map<String, Object> applyExtension(Map<String, Object> params) {
        if (params == null) {
            params = new HashMap<>();
        } else {
            // Create mutable copy
            params = new HashMap<>(params);
        }

        // Substitute Extension variables with DB-specific values
        for (String varName : extension.getVariableNames()) {
            Object value = extension.getValue(varName, dbType);
            if (value != null) {
                params.put(varName, value);
            }
        }

        return params;
    }

    @Override
    public void close() {
        // SqlSessionFactory doesn't need explicit closing
        // Connection pool will be cleaned up automatically
    }

    private String getEnvOrDefault(String key, String defaultValue) {
        String value = System.getenv(key);
        return value != null ? value : defaultValue;
    }
}
