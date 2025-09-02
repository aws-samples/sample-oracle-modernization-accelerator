package com.test.mybatis;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.sql.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * SQL 비교 검증을 위한 Repository 클래스
 * Oracle(소스) ↔ MySQL/PostgreSQL(타겟) 간 SQL 실행 결과 비교 및 저장
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
    
    private String targetDbType;           // "mysql" 또는 "postgresql"
    private ObjectMapper objectMapper;
    
    private static final String TABLE_NAME = "sqllist";
    
    /**
     * 생성자 - 환경변수 TARGET_DBMS_TYPE으로 타겟 DB 판단
     */
    public SqlListRepository() {
        this.objectMapper = new ObjectMapper();
        this.targetDbType = getTargetDbType();
        
        System.out.println("=== SqlListRepository 초기화 ===");
        System.out.println("타겟 DB 타입: " + targetDbType);
        
        try {
            initializeSourceConnection();
            initializeTargetConnection();
            System.out.println("데이터베이스 연결 정보 초기화 완료");
        } catch (Exception e) {
            System.err.println("데이터베이스 연결 정보 초기화 실패: " + e.getMessage());
            throw new RuntimeException("SqlListRepository 초기화 실패", e);
        }
    }
    
    /**
     * 환경변수에서 타겟 DB 타입 조회
     */
    private String getTargetDbType() {
        String dbType = System.getenv("TARGET_DBMS_TYPE");
        if (dbType == null || dbType.trim().isEmpty()) {
            throw new IllegalStateException("환경변수 TARGET_DBMS_TYPE이 설정되지 않았습니다. (mysql, postgresql, postgres)");
        }
        
        dbType = dbType.toLowerCase().trim();
        
        // postgres를 postgresql로 정규화
        if (dbType.equals("postgres")) {
            dbType = "postgresql";
        }
        
        if (!dbType.equals("mysql") && !dbType.equals("postgresql")) {
            throw new IllegalArgumentException("지원하지 않는 DB 타입: " + dbType + " (mysql, postgresql, postgres만 지원)");
        }
        
        return dbType;
    }
    
    /**
     * Oracle 소스 연결 정보 초기화
     */
    private void initializeSourceConnection() {
        // Oracle 환경변수 확인
        String user = System.getenv("ORACLE_SVC_USER");
        String password = System.getenv("ORACLE_SVC_PASSWORD");
        String connectString = System.getenv("ORACLE_SVC_CONNECT_STRING");
        
        if (user == null || password == null) {
            throw new IllegalStateException("Oracle 환경변수가 설정되지 않았습니다: ORACLE_SVC_USER, ORACLE_SVC_PASSWORD");
        }
        
        // JDBC URL 구성
        if (connectString != null && !connectString.trim().isEmpty()) {
            sourceJdbcUrl = "jdbc:oracle:thin:@" + connectString;
        } else {
            // 기본 연결 정보 사용
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
        
        System.out.println("Oracle 연결 설정: " + sourceJdbcUrl);
    }
    
    /**
     * 타겟 DB 연결 정보 초기화 (MySQL 또는 PostgreSQL)
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
                throw new IllegalArgumentException("지원하지 않는 DB 타입: " + targetDbType);
        }
    }
    
    /**
     * MySQL 연결 정보 초기화
     */
    private void initializeMySQLConnection() {
        String host = System.getenv("MYSQL_HOST");
        String port = System.getenv("MYSQL_TCP_PORT");
        String database = System.getenv("MYSQL_DATABASE");
        String user = System.getenv("MYSQL_USER");
        String password = System.getenv("MYSQL_PASSWORD");
        
        if (user == null || password == null) {
            throw new IllegalStateException("MySQL 환경변수가 설정되지 않았습니다: MYSQL_USER, MYSQL_PASSWORD");
        }
        
        if (host == null) host = "localhost";
        if (port == null) port = "3306";
        if (database == null) database = "test";
        
        targetJdbcUrl = "jdbc:mysql://" + host + ":" + port + "/" + database + 
                       "?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC";
        targetUsername = user;
        targetPassword = password;
        targetDriverClass = "com.mysql.cj.jdbc.Driver";
        
        System.out.println("MySQL 연결 설정: " + targetJdbcUrl);
    }
    
    /**
     * PostgreSQL 연결 정보 초기화
     */
    private void initializePostgreSQLConnection() {
        String host = System.getenv("PGHOST");
        String port = System.getenv("PGPORT");
        String database = System.getenv("PGDATABASE");
        String user = System.getenv("PGUSER");
        String password = System.getenv("PGPASSWORD");
        
        if (user == null || password == null) {
            throw new IllegalStateException("PostgreSQL 환경변수가 설정되지 않았습니다: PGUSER, PGPASSWORD");
        }
        
        if (host == null) host = "localhost";
        if (port == null) port = "5432";
        if (database == null) database = "postgres";
        
        targetJdbcUrl = "jdbc:postgresql://" + host + ":" + port + "/" + database;
        targetUsername = user;
        targetPassword = password;
        targetDriverClass = "org.postgresql.Driver";
        
        System.out.println("PostgreSQL 연결 설정: " + targetJdbcUrl);
    }
    
    /**
     * 소스 DB 연결 생성
     */
    private Connection getSourceConnection() throws SQLException {
        try {
            Class.forName(sourceDriverClass);
            return DriverManager.getConnection(sourceJdbcUrl, sourceUsername, sourcePassword);
        } catch (ClassNotFoundException e) {
            throw new SQLException("Oracle JDBC 드라이버를 찾을 수 없습니다: " + sourceDriverClass, e);
        }
    }
    
    /**
     * 타겟 DB 연결 생성 (외부 접근용)
     */
    public Connection getTargetConnection() throws SQLException {
        try {
            Class.forName(targetDriverClass);
            return DriverManager.getConnection(targetJdbcUrl, targetUsername, targetPassword);
        } catch (ClassNotFoundException e) {
            throw new SQLException("타겟 DB JDBC 드라이버를 찾을 수 없습니다: " + targetDriverClass, e);
        }
    }
    
    /**
     * 타겟 DB 연결 생성 (내부용)
     */
    private Connection getTargetConnectionInternal() throws SQLException {
        return getTargetConnection();
    }
    
    /**
     * 타겟 DB에 sqllist 테이블 생성 (없는 경우)
     */
    public void ensureTargetTableExists() {
        try (Connection conn = getTargetConnection()) {
            if (!tableExists(conn, TABLE_NAME)) {
                System.out.println("sqllist 테이블이 존재하지 않습니다. 생성합니다...");
                createTable(conn);
                createIndexes(conn);
                System.out.println("sqllist 테이블 생성 완료");
            } else {
                System.out.println("sqllist 테이블이 이미 존재합니다.");
            }
        } catch (SQLException e) {
            System.err.println("테이블 생성 확인 실패: " + e.getMessage());
            throw new RuntimeException("테이블 생성 실패", e);
        }
    }
    
    /**
     * 테이블 존재 여부 확인
     */
    private boolean tableExists(Connection conn, String tableName) throws SQLException {
        DatabaseMetaData metaData = conn.getMetaData();
        try (ResultSet rs = metaData.getTables(null, null, tableName.toUpperCase(), new String[]{"TABLE"})) {
            if (rs.next()) return true;
        }
        
        // 소문자로도 확인
        try (ResultSet rs = metaData.getTables(null, null, tableName.toLowerCase(), new String[]{"TABLE"})) {
            return rs.next();
        }
    }
    
    /**
     * sqllist 테이블 생성
     */
    private void createTable(Connection conn) throws SQLException {
        String ddl = getTargetDdl();
        try (Statement stmt = conn.createStatement()) {
            stmt.execute(ddl);
        }
    }
    
    /**
     * 인덱스 생성
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
                    // 인덱스가 이미 존재하는 경우 무시
                    if (!e.getMessage().contains("already exists") && 
                        !e.getMessage().contains("Duplicate key name")) {
                        throw e;
                    }
                }
            }
        }
    }
    
    /**
     * 타겟 DB 타입에 따른 DDL 반환
     */
    private String getTargetDdl() {
        switch (targetDbType) {
            case "mysql":
                return getMySQLDdl();
            case "postgresql":
                return getPostgreSQLDdl();
            default:
                throw new IllegalArgumentException("지원하지 않는 DB 타입: " + targetDbType);
        }
    }
    
    /**
     * MySQL DDL
     */
    private String getMySQLDdl() {
        return "CREATE TABLE sqllist (" +
               "sql_id VARCHAR(100) NOT NULL COMMENT 'SQL ID'," +
               "sql_type CHAR(1) NOT NULL CHECK (sql_type IN ('S', 'I', 'U', 'D', 'P', 'O')) " +
               "COMMENT 'SQL 타입 코드 (S:SELECT, I:INSERT, U:UPDATE, D:DELETE, P:PL/SQL, O:OTHERS)'," +
               "src_path TEXT COMMENT 'Source DB 매퍼 파일 경로'," +
               "src_stmt LONGTEXT COMMENT 'Source DB 매퍼 파일에서 추출된 SQL 구문'," +
               "src_params TEXT COMMENT 'Source SQL 파라미터 리스트 (콤마구분)'," +
               "src_result LONGTEXT COMMENT 'Source DB SQL 실행 결과'," +
               "tgt_path TEXT COMMENT 'Target DB 매퍼 파일 경로'," +
               "tgt_stmt LONGTEXT COMMENT 'Target DB 매퍼 파일에서 추출된 SQL 구문'," +
               "tgt_params TEXT COMMENT 'Target SQL 파라미터 리스트 (콤마구분)'," +
               "tgt_result LONGTEXT COMMENT 'Target DB SQL 실행 결과'," +
               "same CHAR(1) CHECK (same IN ('Y', 'N')) COMMENT '실행 결과 동일 여부 (Y/N)'," +
               "PRIMARY KEY (sql_id)" +
               ") COMMENT='Source/Target DB SQL 비교 검증 테이블'";
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
     * 소스 SQL 정보 저장 (최초 저장)
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
            System.out.println("소스 SQL 정보 저장: " + sqlId + " (" + result + "건)");
            
        } catch (SQLException e) {
            System.err.println("소스 SQL 정보 저장 실패: " + sqlId + " - " + e.getMessage());
            throw new RuntimeException("SQL 정보 저장 실패", e);
        }
    }
    
    /**
     * 타겟 SQL 정보 업데이트
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
                System.out.println("타겟 SQL 정보 업데이트: " + sqlId);
            } else {
                System.out.println("타겟 SQL 정보 업데이트 실패 - 해당 SQL ID 없음: " + sqlId);
            }
            
        } catch (SQLException e) {
            System.err.println("타겟 SQL 정보 업데이트 실패: " + sqlId + " - " + e.getMessage());
            throw new RuntimeException("타겟 SQL 정보 업데이트 실패", e);
        }
    }
    
    /**
     * UPSERT SQL 생성
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
        throw new IllegalArgumentException("지원하지 않는 UPSERT 타입: " + type + ", DB: " + targetDbType);
    }
    
    /**
     * 소스 DB 실행 결과 저장
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
                System.out.println("소스 실행 결과 저장: " + sqlId + " (" + results.size() + "건)");
            } else {
                System.out.println("소스 실행 결과 저장 실패 - 해당 SQL ID 없음: " + sqlId);
            }
            
        } catch (SQLException e) {
            System.err.println("소스 실행 결과 저장 실패: " + sqlId + " - " + e.getMessage());
            throw new RuntimeException("소스 실행 결과 저장 실패", e);
        }
    }
    
    /**
     * 타겟 DB 실행 결과 저장
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
                System.out.println("타겟 실행 결과 저장: " + sqlId + " (" + results.size() + "건)");
            } else {
                System.out.println("타겟 실행 결과 저장 실패 - 해당 SQL ID 없음: " + sqlId);
            }
            
        } catch (SQLException e) {
            System.err.println("타겟 실행 결과 저장 실패: " + sqlId + " - " + e.getMessage());
            throw new RuntimeException("타겟 실행 결과 저장 실패", e);
        }
    }
    
    /**
     * ResultSet을 정규화된 JSON 형태로 변환
     * - sqlId는 매퍼명 제거하고 순수 ID만 사용
     * - timestamp는 고정값 사용 (비교 시 차이 제거)
     * - 컬럼명은 소문자로 통일
     * - 데이터 타입은 적절히 변환
     */
    public String convertResultSetToJson(List<Map<String, Object>> results, String sqlId, String database, Map<String, Object> parameters) {
        try {
            ObjectNode root = objectMapper.createObjectNode();
            
            // testInfo 섹션 - 정규화
            ObjectNode testInfo = objectMapper.createObjectNode();
            
            // sqlId 정규화: 매퍼명 제거하고 순수 ID만 사용
            String normalizedSqlId = sqlId;
            if (sqlId.contains(".")) {
                normalizedSqlId = sqlId.substring(sqlId.lastIndexOf(".") + 1);
            }
            testInfo.put("sqlId", normalizedSqlId);
            
            // database는 고정값 사용 (비교 시 차이 제거)
            testInfo.put("database", "normalized");
            
            // timestamp는 고정값 사용 (비교 시 차이 제거)
            testInfo.put("timestamp", "2025-01-01T00:00:00Z");
            
            // parameters 섹션 - 정규화
            ObjectNode paramsNode = objectMapper.createObjectNode();
            if (parameters != null) {
                // 파라미터를 알파벳순으로 정렬
                Map<String, Object> sortedParams = new TreeMap<>(parameters);
                for (Map.Entry<String, Object> entry : sortedParams.entrySet()) {
                    Object value = entry.getValue();
                    if (value == null) {
                        paramsNode.putNull(entry.getKey());
                    } else {
                        // 모든 파라미터 값을 문자열로 통일
                        paramsNode.put(entry.getKey(), value.toString());
                    }
                }
            }
            testInfo.set("parameters", paramsNode);
            root.set("testInfo", testInfo);
            
            // results 섹션 - 정규화
            ArrayNode resultsArray = objectMapper.createArrayNode();
            
            // 결과를 정렬 가능한 형태로 변환
            List<Map<String, Object>> normalizedResults = new ArrayList<>();
            for (Map<String, Object> row : results) {
                Map<String, Object> normalizedRow = new TreeMap<>(); // 컬럼 순서 정렬
                
                for (Map.Entry<String, Object> entry : row.entrySet()) {
                    // 컬럼명을 소문자로 정규화
                    String normalizedKey = entry.getKey().toLowerCase();
                    Object value = entry.getValue();
                    
                    // 값 정규화
                    Object normalizedValue = normalizeValue(value);
                    normalizedRow.put(normalizedKey, normalizedValue);
                }
                normalizedResults.add(normalizedRow);
            }
            
            // 결과를 정렬 (모든 컬럼 값 기준으로 안정적 정렬)
            normalizedResults.sort((row1, row2) -> {
                if (row1.isEmpty() && row2.isEmpty()) return 0;
                if (row1.isEmpty()) return -1;
                if (row2.isEmpty()) return 1;
                
                // 모든 컬럼 값을 문자열로 연결해서 비교
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
            
            // JSON 배열 생성
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
            
            // metadata 섹션 - 정규화
            ObjectNode metadata = objectMapper.createObjectNode();
            metadata.put("rowCount", results.size());
            metadata.put("columnCount", results.isEmpty() ? 0 : results.get(0).size());
            metadata.put("executionTimeMs", 0); // 실행 시간은 0으로 고정 (비교 시 차이 제거)
            root.set("metadata", metadata);
            
            return objectMapper.writeValueAsString(root);
            
        } catch (Exception e) {
            System.err.println("JSON 변환 실패: " + e.getMessage());
            return "{\"error\":\"JSON 변환 실패: " + e.getMessage() + "\"}";
        }
    }
    
    /**
     * 값 정규화 메서드
     * - 문자열 숫자를 실제 숫자로 변환
     * - 날짜/시간 형식 통일
     */
    private Object normalizeValue(Object value) {
        if (value == null) {
            return null;
        }
        
        // 문자열인 경우 숫자 변환 시도
        if (value instanceof String) {
            String strValue = (String) value;
            
            // 빈 문자열 처리
            if (strValue.trim().isEmpty()) {
                return strValue;
            }
            
            // 숫자 문자열 변환 시도
            try {
                if (strValue.contains(".")) {
                    return Double.parseDouble(strValue);
                } else {
                    return Long.parseLong(strValue);
                }
            } catch (NumberFormatException e) {
                // 숫자가 아니면 문자열 그대로 반환
                return strValue;
            }
        }
        
        // 이미 숫자인 경우 그대로 반환
        if (value instanceof Number) {
            return value;
        }
        
        // 날짜/시간 타입 처리
        if (value instanceof java.sql.Timestamp || value instanceof java.sql.Date) {
            return value.toString();
        }
        
        // 기타 타입은 문자열로 변환
        return value.toString();
    }
    
    /**
     * 모든 레코드의 소스/타겟 결과 비교 후 same 컬럼 업데이트
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
            
            System.out.println("=== 결과 비교 완료 ===");
            System.out.println("총 비교 건수: " + totalCount);
            System.out.println("동일한 결과: " + sameCount + "건");
            System.out.println("다른 결과: " + differentCount + "건");
            
        } catch (SQLException e) {
            System.err.println("결과 비교 실패: " + e.getMessage());
            throw new RuntimeException("결과 비교 실패", e);
        }
    }
    
    /**
     * 특정 SQL ID의 same 컬럼 업데이트
     */
    private void updateSameColumn(String sqlId, boolean isSame) {
        String sql = "UPDATE " + TABLE_NAME + " SET same = ? WHERE sql_id = ?";
        
        try (Connection conn = getTargetConnection();
             PreparedStatement pstmt = conn.prepareStatement(sql)) {
            
            pstmt.setString(1, isSame ? "Y" : "N");
            pstmt.setString(2, sqlId);
            
            pstmt.executeUpdate();
            
        } catch (SQLException e) {
            System.err.println("same 컬럼 업데이트 실패: " + sqlId + " - " + e.getMessage());
        }
    }
    
    /**
     * 두 JSON 결과 비교 (정규화된 JSON이므로 문자열 비교)
     */
    public boolean compareJsonResults(String srcJson, String tgtJson) {
        try {
            if (srcJson == null && tgtJson == null) return true;
            if (srcJson == null || tgtJson == null) return false;
            
            // 정규화된 JSON이므로 문자열 비교만으로 충분
            return srcJson.equals(tgtJson);
            
        } catch (Exception e) {
            System.err.println("JSON 비교 중 오류 발생: " + e.getMessage());
            return false;
        }
    }
    
    /**
     * SQL 타입명을 코드로 변환
     */
    public String getSqlTypeCode(String sqlType) {
        if (sqlType == null) return "O";
        
        switch (sqlType.toUpperCase()) {
            case "SELECT": return "S";
            case "INSERT": return "I";
            case "UPDATE": return "U";
            case "DELETE": return "D";
            case "CALL": return "P";  // PL/SQL 프로시저 호출
            default: return "O";      // 기타
        }
    }
    
    /**
     * 파라미터 Set을 콤마 구분 문자열로 변환
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
     * 비교 통계 조회
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
            System.err.println("통계 조회 실패: " + e.getMessage());
        }
        
        return stats;
    }
    
    /**
     * 리소스 정리
     */
    public void close() {
        System.out.println("SqlListRepository 리소스 정리 완료");
    }
    
    /**
     * SQL 정보를 담는 내부 클래스
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
