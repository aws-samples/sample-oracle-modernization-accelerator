package com.test.mybatis;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.sql.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * Repository class for SQL comparison verification
 * Compare and store SQL execution results between Oracle(source) ↔ MySQL/PostgreSQL(target)
 */
public class SqlListRepository {
    
    private String sourceJdbcUrl;
    private String sourceUsername;
    private String sourcePassword;
    private String sourceDriverClass;
    
    private String targetJdbcUrl;
    private String targetUsername;
    private String targetPassword;
    private String targetDriverClass;
    
    private String targetDbType;           // "mysql" or "postgresql"
    private ObjectMapper objectMapper;
    
    private static final String TABLE_NAME = "sqllist";
    
    /**
     * Constructor - Determine target DB by environment variable TARGET_DBMS_TYPE
     */
    public SqlListRepository() {
        this.objectMapper = new ObjectMapper();
        this.targetDbType = getTargetDbType();
        
        System.out.println("=== SqlListRepository Initialization ===");
        System.out.println("Target DB type: " + targetDbType);
        
        try {
            initializeSourceConnection();
            initializeTargetConnection();
            System.out.println("Database connection information initialization completed");
        } catch (Exception e) {
            System.err.println("Database connection information initialization failed: " + e.getMessage());
            throw new RuntimeException("SqlListRepository initialization failed", e);
        }
    }
    
    /**
     * Get target DB type from environment variable
     */
    private String getTargetDbType() {
        String dbType = System.getenv("TARGET_DBMS_TYPE");
        if (dbType == null || dbType.trim().isEmpty()) {
            throw new IllegalStateException("Environment variable TARGET_DBMS_TYPE not set. (mysql, postgresql, postgres)");
        }
        
        dbType = dbType.toLowerCase().trim();
        
        // Normalize postgres to postgresql
        if (dbType.equals("postgres")) {
            dbType = "postgresql";
        }
        
        if (!dbType.equals("mysql") && !dbType.equals("postgresql")) {
            throw new IllegalArgumentException("Unsupported DB type: " + dbType + " (only mysql, postgresql, postgres supported)");
        }
        
        return dbType;
    }
    
    /**
     * Initialize Oracle source connection information
     */
    private void initializeSourceConnection() {
        // Check Oracle environment variables
        String user = System.getenv("ORACLE_SVC_USER");
        String password = System.getenv("ORACLE_SVC_PASSWORD");
        String connectString = System.getenv("ORACLE_SVC_CONNECT_STRING");
        
        if (user == null || password == null) {
            throw new IllegalStateException("Oracle environment variables not set: ORACLE_SVC_USER, ORACLE_SVC_PASSWORD");
        }
        
        // Configure JDBC URL
        if (connectString != null && !connectString.trim().isEmpty()) {
            sourceJdbcUrl = "jdbc:oracle:thin:@" + connectString;
        } else {
            // Use basic connection information
            String host = System.getenv("ORACLE_HOST");
            String port = System.getenv("ORACLE_PORT");
            String sid = System.getenv("ORACLE_SID");
            
            if (host == null) host = "localhost";
            if (port == null) port = "1521";
            if (sid == null) sid = "orcl";
            
            sourceJdbcUrl = "jdbc:oracle:thin:@" + host + ":" + port + ":" + sid;
        }
        
        sourceUsername = user;
        sourcePassword = password;
        sourceDriverClass = "oracle.jdbc.driver.OracleDriver";
        
        System.out.println("Oracle connection setup: " + sourceJdbcUrl);
    }
    
    /**
     * Initialize target DB connection information (MySQL or PostgreSQL)
     */
    private void initializeTargetConnection() {
        switch (targetDbType) {
            case "mysql":
                initializeMySQLConnection();
                break;
            case "postgresql":
                initializePostgreSQLConnection();
                break;
            default:
                throw new IllegalArgumentException("Unsupported DB type: " + targetDbType);
        }
    }
    
    /**
     * Initialize MySQL connection information
     */
    private void initializeMySQLConnection() {
        String host = System.getenv("MYSQL_HOST");
        String port = System.getenv("MYSQL_TCP_PORT");
        String database = System.getenv("MYSQL_DATABASE");
        String user = System.getenv("MYSQL_USER");
        String password = System.getenv("MYSQL_PASSWORD");
        
        if (user == null || password == null) {
            throw new IllegalStateException("MySQL environment variables not set: MYSQL_USER, MYSQL_PASSWORD");
        }
        
        if (host == null) host = "localhost";
        if (port == null) port = "3306";
        if (database == null) database = "test";
        
        targetJdbcUrl = "jdbc:mysql://" + host + ":" + port + "/" + database + 
                       "?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC";
        targetUsername = user;
        targetPassword = password;
        targetDriverClass = "com.mysql.cj.jdbc.Driver";
        
        System.out.println("MySQL connection setup: " + targetJdbcUrl);
    }
    
    /**
     * Initialize PostgreSQL connection information
     */
    private void initializePostgreSQLConnection() {
        String host = System.getenv("PGHOST");
        String port = System.getenv("PGPORT");
        String database = System.getenv("PGDATABASE");
        String user = System.getenv("PGUSER");
        String password = System.getenv("PGPASSWORD");
        
        if (user == null || password == null) {
            throw new IllegalStateException("PostgreSQL environment variables not set: PGUSER, PGPASSWORD");
        }
        
        if (host == null) host = "localhost";
        if (port == null) port = "5432";
        if (database == null) database = "postgres";
        
        targetJdbcUrl = "jdbc:postgresql://" + host + ":" + port + "/" + database;
        targetUsername = user;
        targetPassword = password;
        targetDriverClass = "org.postgresql.Driver";
        
        System.out.println("PostgreSQL connection setup: " + targetJdbcUrl);
    }
    
    /**
     * Create source DB connection
     */
    private Connection getSourceConnection() throws SQLException {
        try {
            Class.forName(sourceDriverClass);
            return DriverManager.getConnection(sourceJdbcUrl, sourceUsername, sourcePassword);
        } catch (ClassNotFoundException e) {
            throw new SQLException("Oracle JDBC driver not found: " + sourceDriverClass, e);
        }
    }
    
    /**
     * Create target DB connection (for external access)
     */
    public Connection getTargetConnection() throws SQLException {
        try {
            Class.forName(targetDriverClass);
            return DriverManager.getConnection(targetJdbcUrl, targetUsername, targetPassword);
        } catch (ClassNotFoundException e) {
            throw new SQLException("Target DB JDBC driver not found: " + targetDriverClass, e);
        }
    }
    
    /**
     * Create target DB connection (for internal use)
     */
    private Connection getTargetConnectionInternal() throws SQLException {
        return getTargetConnection();
    }
    
    /**
     * Create sqllist table in target DB (if not exists)
     */
    public void ensureTargetTableExists() {
        try (Connection conn = getTargetConnection()) {
            if (!tableExists(conn, TABLE_NAME)) {
                System.out.println("sqllist table does not exist. Creating...");
                createTable(conn);
                createIndexes(conn);
                System.out.println("sqllist table creation completed");
            } else {
                System.out.println("sqllist table already exists.");
            }
        } catch (SQLException e) {
            System.err.println("Table creation check failed: " + e.getMessage());
            throw new RuntimeException("Table creation failed", e);
        }
    }
    
    /**
     * Check if table exists
     */
    private boolean tableExists(Connection conn, String tableName) throws SQLException {
        DatabaseMetaData metaData = conn.getMetaData();
        try (ResultSet rs = metaData.getTables(null, null, tableName.toUpperCase(), new String[]{"TABLE"})) {
            if (rs.next()) return true;
        }
        
        // Check with lowercase as well
        try (ResultSet rs = metaData.getTables(null, null, tableName.toLowerCase(), new String[]{"TABLE"})) {
            return rs.next();
        }
    }
    
    /**
     * Create sqllist table
     */
    private void createTable(Connection conn) throws SQLException {
        String ddl = getTargetDdl();
        try (Statement stmt = conn.createStatement()) {
            stmt.execute(ddl);
        }
    }
    
    /**
     * Create indexes
     */
    private void createIndexes(Connection conn) throws SQLException {
        String[] indexes = {
            "CREATE INDEX idx_sqllist_sql_type ON " + TABLE_NAME + "(sql_type)",
            "CREATE INDEX idx_sqllist_same ON " + TABLE_NAME + "(same)"
        };
        
        try (Statement stmt = conn.createStatement()) {
            for (String indexSql : indexes) {
                try {
                    stmt.execute(indexSql);
                } catch (SQLException e) {
                    // Ignore if index already exists
                    if (!e.getMessage().contains("already exists") && 
                        !e.getMessage().contains("Duplicate key name")) {
                        throw e;
                    }
                }
            }
        }
    }
    
    /**
     * Return DDL based on target DB type
     */
    private String getTargetDdl() {
        switch (targetDbType) {
            case "mysql":
                return getMySQLDdl();
            case "postgresql":
                return getPostgreSQLDdl();
            default:
                throw new IllegalArgumentException("Unsupported DB type: " + targetDbType);
        }
    }
    
    /**
     * MySQL DDL
     */
    private String getMySQLDdl() {
        return "CREATE TABLE sqllist (" +
               "sql_id VARCHAR(100) NOT NULL COMMENT 'SQL ID'," +
               "sql_type CHAR(1) NOT NULL CHECK (sql_type IN ('S', 'I', 'U', 'D', 'P', 'O')) " +
               "COMMENT 'SQL type code (S:SELECT, I:INSERT, U:UPDATE, D:DELETE, P:PL/SQL, O:OTHERS)'," +
               "src_path TEXT COMMENT 'Source DB mapper file path'," +
               "src_stmt LONGTEXT COMMENT 'SQL statement extracted from Source DB mapper file'," +
               "src_params TEXT COMMENT 'Source SQL parameter list (comma separated)'," +
               "src_result LONGTEXT COMMENT 'Source DB SQL execution result'," +
               "tgt_path TEXT COMMENT 'Target DB mapper file path'," +
               "tgt_stmt LONGTEXT COMMENT 'SQL statement extracted from Target DB mapper file'," +
               "tgt_params TEXT COMMENT 'Target SQL parameter list (comma separated)'," +
               "tgt_result LONGTEXT COMMENT 'Target DB SQL execution result'," +
               "same CHAR(1) CHECK (same IN ('Y', 'N')) COMMENT 'Whether execution results are identical (Y/N)'," +
               "PRIMARY KEY (sql_id)" +
               ") COMMENT='Source/Target DB SQL comparison verification table'";
    }
    
    /**
     * PostgreSQL DDL
     */
    private String getPostgreSQLDdl() {
        return "CREATE TABLE sqllist (" +
               "sql_id VARCHAR(100) NOT NULL," +
               "sql_type CHAR(1) NOT NULL CHECK (sql_type IN ('S', 'I', 'U', 'D', 'P', 'O'))," +
               "src_path TEXT," +
               "src_stmt TEXT," +
               "src_params TEXT," +
               "src_result TEXT," +
               "tgt_path TEXT," +
               "tgt_stmt TEXT," +
               "tgt_params TEXT," +
               "tgt_result TEXT," +
               "same CHAR(1) CHECK (same IN ('Y', 'N'))," +
               "PRIMARY KEY (sql_id)" +
               ")";
    }
    
    /**
     * Save source SQL information (initial save)
     */
    public void saveSqlInfo(String sqlId, String sqlType, String srcPath, String srcStmt, String srcParams) {
        String sql = getUpsertSql("src");
        
        try (Connection conn = getTargetConnection();
             PreparedStatement pstmt = conn.prepareStatement(sql)) {
            
            pstmt.setString(1, sqlId);
            pstmt.setString(2, getSqlTypeCode(sqlType));
            pstmt.setString(3, srcPath);
            pstmt.setString(4, srcStmt);
            pstmt.setString(5, srcParams);
            
            int result = pstmt.executeUpdate();
            System.out.println("Source SQL information saved: " + sqlId + " (" + result + " records)");
            
        } catch (SQLException e) {
            System.err.println("Source SQL information save failed: " + sqlId + " - " + e.getMessage());
            throw new RuntimeException("SQL information save failed", e);
        }
    }
    
    /**
     * Update target SQL information
     */
    public void updateTargetInfo(String sqlId, String tgtPath, String tgtStmt, String tgtParams) {
        String sql = "UPDATE " + TABLE_NAME + " SET tgt_path = ?, tgt_stmt = ?, tgt_params = ? WHERE sql_id = ?";
        
        try (Connection conn = getTargetConnection();
             PreparedStatement pstmt = conn.prepareStatement(sql)) {
            
            pstmt.setString(1, tgtPath);
            pstmt.setString(2, tgtStmt);
            pstmt.setString(3, tgtParams);
            pstmt.setString(4, sqlId);
            
            int result = pstmt.executeUpdate();
            if (result > 0) {
                System.out.println("Target SQL information updated: " + sqlId);
            } else {
                System.out.println("Target SQL information update failed - SQL ID not found: " + sqlId);
            }
            
        } catch (SQLException e) {
            System.err.println("Target SQL information update failed: " + sqlId + " - " + e.getMessage());
            throw new RuntimeException("Target SQL information update failed", e);
        }
    }
    
    /**
     * Generate UPSERT SQL
     */
    private String getUpsertSql(String type) {
        switch (targetDbType) {
            case "mysql":
                if ("src".equals(type)) {
                    return "INSERT INTO sqllist (sql_id, sql_type, src_path, src_stmt, src_params) " +
                           "VALUES (?, ?, ?, ?, ?) " +
                           "ON DUPLICATE KEY UPDATE " +
                           "sql_type = VALUES(sql_type), " +
                           "src_path = VALUES(src_path), " +
                           "src_stmt = VALUES(src_stmt), " +
                           "src_params = VALUES(src_params)";
                }
                break;
            case "postgresql":
                if ("src".equals(type)) {
                    return "INSERT INTO sqllist (sql_id, sql_type, src_path, src_stmt, src_params) " +
                           "VALUES (?, ?, ?, ?, ?) " +
                           "ON CONFLICT (sql_id) DO UPDATE SET " +
                           "sql_type = EXCLUDED.sql_type, " +
                           "src_path = EXCLUDED.src_path, " +
                           "src_stmt = EXCLUDED.src_stmt, " +
                           "src_params = EXCLUDED.src_params";
                }
                break;
        }
        throw new IllegalArgumentException("Unsupported UPSERT type: " + type + ", DB: " + targetDbType);
    }
    
    /**
     * Save source DB execution result
     */
    public void saveSourceResult(String sqlId, List<Map<String, Object>> results, Map<String, Object> parameters) {
        String resultJson = convertResultSetToJson(results, sqlId, "oracle", parameters);
        String sql = "UPDATE " + TABLE_NAME + " SET src_result = ? WHERE sql_id = ?";
        
        try (Connection conn = getTargetConnection();
             PreparedStatement pstmt = conn.prepareStatement(sql)) {
            
            pstmt.setString(1, resultJson);
            pstmt.setString(2, sqlId);
            
            int result = pstmt.executeUpdate();
            if (result > 0) {
                System.out.println("Source execution result saved: " + sqlId + " (" + results.size() + " records)");
            } else {
                System.out.println("Source execution result save failed - SQL ID not found: " + sqlId);
            }
            
        } catch (SQLException e) {
            System.err.println("Source execution result save failed: " + sqlId + " - " + e.getMessage());
            throw new RuntimeException("Source execution result save failed", e);
        }
    }
    
    /**
     * Save target DB execution result
     */
    public void saveTargetResult(String sqlId, List<Map<String, Object>> results, Map<String, Object> parameters) {
        String resultJson = convertResultSetToJson(results, sqlId, targetDbType, parameters);
        String sql = "UPDATE " + TABLE_NAME + " SET tgt_result = ? WHERE sql_id = ?";
        
        try (Connection conn = getTargetConnection();
             PreparedStatement pstmt = conn.prepareStatement(sql)) {
            
            pstmt.setString(1, resultJson);
            pstmt.setString(2, sqlId);
            
            int result = pstmt.executeUpdate();
            if (result > 0) {
                System.out.println("Target execution result saved: " + sqlId + " (" + results.size() + " records)");
            } else {
                System.out.println("Target execution result save failed - SQL ID not found: " + sqlId);
            }
            
        } catch (SQLException e) {
            System.err.println("Target execution result save failed: " + sqlId + " - " + e.getMessage());
            throw new RuntimeException("Target execution result save failed", e);
        }
    }
    
    /**
     * Convert ResultSet to normalized JSON format
     * - sqlId uses pure ID only, removing mapper name
     * - timestamp uses fixed value (remove differences during comparison)
     * - column names unified to lowercase
     * - data types converted appropriately
     */
    public String convertResultSetToJson(List<Map<String, Object>> results, String sqlId, String database, Map<String, Object> parameters) {
        try {
            ObjectNode root = objectMapper.createObjectNode();
            
            // testInfo section - normalization
            ObjectNode testInfo = objectMapper.createObjectNode();
            
            // sqlId normalization: remove mapper name and use pure ID only
            String normalizedSqlId = sqlId;
            if (sqlId.contains(".")) {
                normalizedSqlId = sqlId.substring(sqlId.lastIndexOf(".") + 1);
            }
            testInfo.put("sqlId", normalizedSqlId);
            
            // database uses fixed value (remove differences during comparison)
            testInfo.put("database", "normalized");
            
            // timestamp uses fixed value (remove differences during comparison)
            testInfo.put("timestamp", "2025-01-01T00:00:00Z");
            
            // parameters section - normalization
            ObjectNode paramsNode = objectMapper.createObjectNode();
            if (parameters != null) {
                // Sort parameters alphabetically
                Map<String, Object> sortedParams = new TreeMap<>(parameters);
                for (Map.Entry<String, Object> entry : sortedParams.entrySet()) {
                    Object value = entry.getValue();
                    if (value == null) {
                        paramsNode.putNull(entry.getKey());
                    } else {
                        // Unify all parameter values to strings
                        paramsNode.put(entry.getKey(), value.toString());
                    }
                }
            }
            testInfo.set("parameters", paramsNode);
            root.set("testInfo", testInfo);
            
            // results section - normalization
            ArrayNode resultsArray = objectMapper.createArrayNode();
            
            // Convert results to sortable format
            List<Map<String, Object>> normalizedResults = new ArrayList<>();
            for (Map<String, Object> row : results) {
                Map<String, Object> normalizedRow = new TreeMap<>(); // Sort column order
                
                for (Map.Entry<String, Object> entry : row.entrySet()) {
                    // Normalize column names to lowercase
                    String normalizedKey = entry.getKey().toLowerCase();
                    Object value = entry.getValue();
                    
                    // Normalize values
                    Object normalizedValue = normalizeValue(value);
                    normalizedRow.put(normalizedKey, normalizedValue);
                }
                normalizedResults.add(normalizedRow);
            }
            
            // Sort results (stable sorting based on all column values)
            normalizedResults.sort((row1, row2) -> {
                if (row1.isEmpty() && row2.isEmpty()) return 0;
                if (row1.isEmpty()) return -1;
                if (row2.isEmpty()) return 1;
                
                // Compare by concatenating all column values as strings
                String str1 = row1.values().stream()
                    .map(v -> v == null ? "null" : v.toString())
                    .sorted()
                    .reduce("", (a, b) -> a + "|" + b);
                    
                String str2 = row2.values().stream()
                    .map(v -> v == null ? "null" : v.toString())
                    .sorted()
                    .reduce("", (a, b) -> a + "|" + b);
                
                return str1.compareTo(str2);
            });
            
            // Create JSON array
            for (Map<String, Object> row : normalizedResults) {
                ObjectNode rowNode = objectMapper.createObjectNode();
                for (Map.Entry<String, Object> entry : row.entrySet()) {
                    Object value = entry.getValue();
                    if (value == null) {
                        rowNode.putNull(entry.getKey());
                    } else if (value instanceof String) {
                        rowNode.put(entry.getKey(), (String) value);
                    } else if (value instanceof Integer) {
                        rowNode.put(entry.getKey(), (Integer) value);
                    } else if (value instanceof Long) {
                        rowNode.put(entry.getKey(), (Long) value);
                    } else if (value instanceof Double) {
                        rowNode.put(entry.getKey(), (Double) value);
                    } else if (value instanceof Boolean) {
                        rowNode.put(entry.getKey(), (Boolean) value);
                    } else {
                        rowNode.put(entry.getKey(), value.toString());
                    }
                }
                resultsArray.add(rowNode);
            }
            root.set("results", resultsArray);
            
            // metadata section - normalization
            ObjectNode metadata = objectMapper.createObjectNode();
            metadata.put("rowCount", results.size());
            metadata.put("columnCount", results.isEmpty() ? 0 : results.get(0).size());
            metadata.put("executionTimeMs", 0); // Execution time fixed to 0 (remove differences during comparison)
            root.set("metadata", metadata);
            
            return objectMapper.writeValueAsString(root);
            
        } catch (Exception e) {
            System.err.println("JSON conversion failed: " + e.getMessage());
            return "{\"error\":\"JSON conversion failed: " + e.getMessage() + "\"}";
        }
    }
    
    /**
     * Value normalization method
     * - Convert string numbers to actual numbers
     * - Unify date/time formats
     */
    private Object normalizeValue(Object value) {
        if (value == null) {
            return null;
        }
        
        // Try number conversion for strings
        if (value instanceof String) {
            String strValue = (String) value;
            
            // Handle empty strings
            if (strValue.trim().isEmpty()) {
                return strValue;
            }
            
            // Try converting numeric strings
            try {
                if (strValue.contains(".")) {
                    return Double.parseDouble(strValue);
                } else {
                    return Long.parseLong(strValue);
                }
            } catch (NumberFormatException e) {
                // Return as string if not a number
                return strValue;
            }
        }
        
        // Return numbers as is
        if (value instanceof Number) {
            return value;
        }
        
        // Handle date/time types
        if (value instanceof java.sql.Timestamp || value instanceof java.sql.Date) {
            return value.toString();
        }
        
        // Convert other types to string
        return value.toString();
    }
    
    /**
     * Compare source/target results for all records and update same column
     */
    public void compareAndUpdateResults() {
        String selectSql = "SELECT sql_id, src_result, tgt_result FROM " + TABLE_NAME + 
                          " WHERE src_result IS NOT NULL AND tgt_result IS NOT NULL";
        
        try (Connection conn = getTargetConnection();
             PreparedStatement selectStmt = conn.prepareStatement(selectSql);
             ResultSet rs = selectStmt.executeQuery()) {
            
            int totalCount = 0;
            int sameCount = 0;
            int differentCount = 0;
            
            while (rs.next()) {
                String sqlId = rs.getString("sql_id");
                String srcResult = rs.getString("src_result");
                String tgtResult = rs.getString("tgt_result");
                
                boolean isSame = compareJsonResults(srcResult, tgtResult);
                updateSameColumn(sqlId, isSame);
                
                totalCount++;
                if (isSame) {
                    sameCount++;
                } else {
                    differentCount++;
                }
            }
            
            System.out.println("=== Result Comparison Completed ===");
            System.out.println("Total comparisons: " + totalCount);
            System.out.println("Identical results: " + sameCount + " records");
            System.out.println("Different results: " + differentCount + " records");
            
        } catch (SQLException e) {
            System.err.println("Result comparison failed: " + e.getMessage());
            throw new RuntimeException("Result comparison failed", e);
        }
    }
    
    /**
     * Update same column for specific SQL ID
     */
    private void updateSameColumn(String sqlId, boolean isSame) {
        String sql = "UPDATE " + TABLE_NAME + " SET same = ? WHERE sql_id = ?";
        
        try (Connection conn = getTargetConnection();
             PreparedStatement pstmt = conn.prepareStatement(sql)) {
            
            pstmt.setString(1, isSame ? "Y" : "N");
            pstmt.setString(2, sqlId);
            
            pstmt.executeUpdate();
            
        } catch (SQLException e) {
            System.err.println("same column update failed: " + sqlId + " - " + e.getMessage());
        }
    }
    
    /**
     * Compare two JSON results (string comparison since JSON is normalized)
     */
    public boolean compareJsonResults(String srcJson, String tgtJson) {
        try {
            if (srcJson == null && tgtJson == null) return true;
            if (srcJson == null || tgtJson == null) return false;
            
            // String comparison is sufficient since JSON is normalized
            return srcJson.equals(tgtJson);
            
        } catch (Exception e) {
            System.err.println("Error occurred during JSON comparison: " + e.getMessage());
            return false;
        }
    }
    
    /**
     * Convert SQL type name to code
     */
    public String getSqlTypeCode(String sqlType) {
        if (sqlType == null) return "O";
        
        switch (sqlType.toUpperCase()) {
            case "SELECT": return "S";
            case "INSERT": return "I";
            case "UPDATE": return "U";
            case "DELETE": return "D";
            case "CALL": return "P";  // PL/SQL procedure call
            default: return "O";      // Others
        }
    }
    
    /**
     * Convert parameter Set to comma-separated string
     */
    public String formatParameterList(Set<String> parameters) {
        if (parameters == null || parameters.isEmpty()) {
            return "";
        }
        
        List<String> sortedParams = new ArrayList<>(parameters);
        Collections.sort(sortedParams);
        return String.join(",", sortedParams);
    }
    
    /**
     * Get comparison statistics
     */
    public Map<String, Integer> getComparisonStatistics() {
        Map<String, Integer> stats = new HashMap<>();
        
        String sql = "SELECT " +
                    "COUNT(*) as total, " +
                    "COUNT(CASE WHEN same = 'Y' THEN 1 END) as same_count, " +
                    "COUNT(CASE WHEN same = 'N' THEN 1 END) as different_count, " +
                    "COUNT(CASE WHEN src_result IS NOT NULL AND tgt_result IS NOT NULL AND same IS NULL THEN 1 END) as pending_count, " +
                    "COUNT(CASE WHEN src_result IS NULL THEN 1 END) as missing_src, " +
                    "COUNT(CASE WHEN tgt_result IS NULL THEN 1 END) as missing_tgt, " +
                    "COUNT(CASE WHEN src_result IS NOT NULL AND tgt_result IS NOT NULL THEN 1 END) as both_results " +
                    "FROM " + TABLE_NAME;
        
        try (Connection conn = getTargetConnection();
             PreparedStatement pstmt = conn.prepareStatement(sql);
             ResultSet rs = pstmt.executeQuery()) {
            
            if (rs.next()) {
                stats.put("total", rs.getInt("total"));
                stats.put("same", rs.getInt("same_count"));
                stats.put("different", rs.getInt("different_count"));
                stats.put("pending", rs.getInt("pending_count"));
                stats.put("missing_src", rs.getInt("missing_src"));
                stats.put("missing_tgt", rs.getInt("missing_tgt"));
                stats.put("both_results", rs.getInt("both_results"));
            }
            
        } catch (SQLException e) {
            System.err.println("Statistics query failed: " + e.getMessage());
        }
        
        return stats;
    }
    
    /**
     * Resource cleanup
     */
    public void close() {
        System.out.println("SqlListRepository resource cleanup completed");
    }
    
    /**
     * Inner class to hold SQL information
     */
    public static class SqlInfo {
        public String sqlId;
        public String sqlType;
        public String srcPath;
        public String srcStmt;
        public String srcParams;
        public String srcResult;
        public String tgtPath;
        public String tgtStmt;
        public String tgtParams;
        public String tgtResult;
        public String same;
        
        @Override
        public String toString() {
            return "SqlInfo{" +
                    "sqlId='" + sqlId + '\'' +
                    ", sqlType='" + sqlType + '\'' +
                    ", same='" + same + '\'' +
                    '}';
        }
    }
}
