package com.example;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springaicommunity.mcp.annotation.McpTool;
import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class OracleMcpTools {

    private static final Logger logger = LoggerFactory.getLogger(OracleMcpTools.class);

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private DataSource dataSource;

    @McpTool(name = "oracle_execute_sql", description = "Execute SQL statements and return results for Oracle database operations")
    public Map<String, Object> executeSql(String sql) {
        logger.info("Executing SQL: {}", sql);
        Map<String, Object> result = new HashMap<>();
        
        try (Connection conn = dataSource.getConnection();
             Statement stmt = conn.createStatement()) {
            
            boolean hasResultSet = stmt.execute(sql);
            if (hasResultSet) {
                try (var rs = stmt.getResultSet()) {
                    List<Map<String, Object>> rows = jdbcTemplate.queryForList(sql);
                    result.put("success", true);
                    result.put("data", rows);
                    result.put("rowCount", rows.size());
                    logger.info("SQL query executed successfully, returned {} rows", rows.size());
                }
            } else {
                int updateCount = stmt.getUpdateCount();
                result.put("success", true);
                result.put("updateCount", updateCount);
                logger.info("SQL update executed successfully, affected {} rows", updateCount);
            }
            
        } catch (Exception e) {
            logger.error("SQL execution failed: {}", e.getMessage());
            result.put("success", false);
            result.put("error", e.getMessage());
        }
        
        return result;
    }

    @McpTool(name = "oracle_execute_testcase_readonly", description = "Execute test case SQL statements with execution timing and guaranteed no side effects through read-only connections")
    public Map<String, Object> executeTestCaseReadOnly(String sql) {
        logger.info("Executing read-only test case SQL: {}", sql);
        Map<String, Object> result = new HashMap<>();
        long startTime = System.currentTimeMillis();
        
        try {
            executeTestCaseReadOnly(sql, result);
            
            long duration = System.currentTimeMillis() - startTime;
            result.put("success", true);
            result.put("executionTimeMs", duration);
            logger.info("Read-only test case executed successfully in {} ms", duration);
            
        } catch (Exception e) {
            long duration = System.currentTimeMillis() - startTime;
            logger.error("Read-only test case execution failed: {}", e.getMessage());
            result.put("success", false);
            result.put("error", e.getMessage());
            result.put("executionTimeMs", duration);
        }
        
        return result;
    }

    @McpTool(name = "oracle_execute_testcase_rollback", description = "Execute test case SQL statements with execution timing and guaranteed no side effects through transactional rollback")
    public Map<String, Object> executeTestCaseRollback(String sql) {
        logger.info("Executing rollback test case SQL: {}", sql);
        Map<String, Object> result = new HashMap<>();
        long startTime = System.currentTimeMillis();
        
        try {
            executeTestCaseWithRollback(sql, result);
            
            long duration = System.currentTimeMillis() - startTime;
            result.put("success", true);
            result.put("executionTimeMs", duration);
            logger.info("Rollback test case executed successfully in {} ms", duration);
            
        } catch (Exception e) {
            long duration = System.currentTimeMillis() - startTime;
            logger.error("Rollback test case execution failed: {}", e.getMessage());
            result.put("success", false);
            result.put("error", e.getMessage());
            result.put("executionTimeMs", duration);
        }
        
        return result;
    }

    private void executeTestCaseReadOnly(String sql, Map<String, Object> result) throws Exception {
        try (Connection conn = dataSource.getConnection()) {
            conn.setReadOnly(true);
            conn.setAutoCommit(false);
            try (Statement stmt = conn.createStatement()) {
                
                boolean hasResultSet = stmt.execute(sql);
                if (hasResultSet) {
                    try (var rs = stmt.getResultSet()) {
                        List<Map<String, Object>> rows = jdbcTemplate.queryForList(sql);
                        result.put("data", rows);
                        result.put("rowCount", rows.size());
                    }
                } else {
                    result.put("updateCount", stmt.getUpdateCount());
                }
            } finally {
                conn.rollback();
                conn.setAutoCommit(true);
                conn.setReadOnly(false);
            }
        }
    }

    private void executeTestCaseWithRollback(String sql, Map<String, Object> result) throws Exception {
        try (Connection conn = dataSource.getConnection()) {
            conn.setAutoCommit(false);
            try (Statement stmt = conn.createStatement()) {
                boolean hasResultSet = stmt.execute(sql);
                if (hasResultSet) {
                    try (var rs = stmt.getResultSet()) {
                        List<Map<String, Object>> rows = new ArrayList<>();
                        var metaData = rs.getMetaData();
                        int columnCount = metaData.getColumnCount();
                        
                        while (rs.next()) {
                            Map<String, Object> row = new HashMap<>();
                            for (int i = 1; i <= columnCount; i++) {
                                row.put(metaData.getColumnName(i), rs.getObject(i));
                            }
                            rows.add(row);
                        }
                        result.put("data", rows);
                        result.put("rowCount", rows.size());
                    }
                } else {
                    result.put("updateCount", stmt.getUpdateCount());
                }
            } finally {
                conn.rollback();
                conn.setAutoCommit(true);
            }
        }
    }


}
