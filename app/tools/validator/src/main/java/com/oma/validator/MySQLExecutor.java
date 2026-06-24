package com.oma.validator;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.apache.ibatis.io.Resources;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Collectors;

/**
 * MySQL/Aurora MySQL Database Executor
 */
public class MySQLExecutor implements DatabaseExecutor {

    private SqlSessionFactory sessionFactory;
    private ObjectMapper objectMapper;

    public MySQLExecutor(String mapperDir) throws Exception {
        this.objectMapper = new ObjectMapper()
                .enable(SerializationFeature.INDENT_OUTPUT)
                .enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS);

        // Build MyBatis configuration
        String config = buildMyBatisConfig(mapperDir);
        InputStream is = new ByteArrayInputStream(config.getBytes("UTF-8"));
        this.sessionFactory = new SqlSessionFactoryBuilder().build(is);

        System.out.println("✓ MySQL executor initialized");
    }

    private String buildMyBatisConfig(String mapperDir) throws Exception {
        // Get MySQL connection info from environment
        String host = getEnv("MYSQL_HOST", "localhost");
        String port = getEnv("MYSQL_PORT", "3306");
        String database = getEnv("MYSQL_DATABASE", "test");
        String user = getEnv("MYSQL_USER", "root");
        String password = getEnv("MYSQL_PASSWORD", "");

        // Find all mapper XML files
        List<Path> mapperFiles = Files.walk(Paths.get(mapperDir))
                .filter(p -> p.toString().endsWith(".xml"))
                .collect(Collectors.toList());

        System.out.println("  Found " + mapperFiles.size() + " mapper files in " + mapperDir);

        // Build MyBatis configuration XML
        StringBuilder config = new StringBuilder();
        config.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
        config.append("<!DOCTYPE configuration PUBLIC \"-//mybatis.org//DTD Config 3.0//EN\" ");
        config.append("\"http://mybatis.org/dtd/mybatis-3-config.dtd\">\n");
        config.append("<configuration>\n");

        // Settings
        config.append("  <settings>\n");
        config.append("    <setting name=\"mapUnderscoreToCamelCase\" value=\"false\"/>\n");
        config.append("    <setting name=\"defaultStatementTimeout\" value=\"30\"/>\n");
        config.append("  </settings>\n");
        config.append("  <typeAliases>\n");
        config.append("    <typeAlias type=\"java.util.HashMap\" alias=\"camelMap\"/>\n");
        config.append("  </typeAliases>\n");

        // Environment
        config.append("  <environments default=\"mysql\">\n");
        config.append("    <environment id=\"mysql\">\n");
        config.append("      <transactionManager type=\"JDBC\"/>\n");
        config.append("      <dataSource type=\"POOLED\">\n");
        config.append("        <property name=\"driver\" value=\"software.amazon.jdbc.Driver\"/>\n");

        // MySQL JDBC URL
        String jdbcUrl = String.format(
            "jdbc:mysql:aws://%s:%s/%s?useSSL=false&allowPublicKeyRetrieval=true",
            host, port, database
        );
        config.append("        <property name=\"url\" value=\"" + jdbcUrl + "\"/>\n");
        config.append("        <property name=\"username\" value=\"" + user + "\"/>\n");
        config.append("        <property name=\"password\" value=\"" + password + "\"/>\n");
        config.append("      </dataSource>\n");
        config.append("    </environment>\n");
        config.append("  </environments>\n");

        // Mappers
        config.append("  <mappers>\n");
        for (Path mapperFile : mapperFiles) {
            String absolutePath = mapperFile.toAbsolutePath().toString();
            config.append("    <mapper url=\"file:///" + absolutePath.replace("\\", "/") + "\"/>\n");
        }
        config.append("  </mappers>\n");
        config.append("</configuration>\n");

        return config.toString();
    }

    @Override
    public String execute(String sqlId, Map<String, Object> params) throws Exception {
        SqlSession session = sessionFactory.openSession(false); // autoCommit = false
        try {
            // Determine statement type from SQL ID
            String statementType = detectStatementType(sqlId);

            Object result;
            switch (statementType) {
                case "SELECT":
                    // Execute SELECT
                    result = session.selectList(sqlId, params);
                    break;

                case "INSERT":
                    // Execute INSERT
                    int inserted = session.insert(sqlId, params);
                    result = Collections.singletonMap("affected_rows", inserted);
                    break;

                case "UPDATE":
                    // Execute UPDATE
                    int updated = session.update(sqlId, params);
                    result = Collections.singletonMap("affected_rows", updated);
                    break;

                case "DELETE":
                    // Execute DELETE
                    int deleted = session.delete(sqlId, params);
                    result = Collections.singletonMap("affected_rows", deleted);
                    break;

                default:
                    throw new IllegalArgumentException("Unknown statement type for: " + sqlId);
            }

            // Always rollback to prevent database changes
            session.rollback();

            // Convert to JSON
            return objectMapper.writeValueAsString(result);

        } finally {
            session.close();
        }
    }

    private String detectStatementType(String sqlId) {
        String lowerSqlId = sqlId.toLowerCase();

        if (lowerSqlId.contains("select") || lowerSqlId.contains("get") ||
            lowerSqlId.contains("find") || lowerSqlId.contains("query") ||
            lowerSqlId.contains("list") || lowerSqlId.contains("search")) {
            return "SELECT";
        } else if (lowerSqlId.contains("insert") || lowerSqlId.contains("create") ||
                   lowerSqlId.contains("add")) {
            return "INSERT";
        } else if (lowerSqlId.contains("update") || lowerSqlId.contains("modify") ||
                   lowerSqlId.contains("change") || lowerSqlId.contains("set")) {
            return "UPDATE";
        } else if (lowerSqlId.contains("delete") || lowerSqlId.contains("remove") ||
                   lowerSqlId.contains("drop")) {
            return "DELETE";
        }

        // Default to SELECT if can't determine
        return "SELECT";
    }

    public void setExtension(Extension extension, String dbType) {
        // MySQL not implemented yet - Extension support can be added later if needed
    }

    @Override
    public void close() {
        // SqlSessionFactory doesn't need explicit closing
        System.out.println("✓ MySQL executor closed");
    }

    private String getEnv(String key, String defaultValue) {
        String value = System.getenv(key);
        return (value != null && !value.isEmpty()) ? value : defaultValue;
    }
}
