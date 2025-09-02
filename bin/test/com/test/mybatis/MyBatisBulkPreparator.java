package com.test.mybatis;

import java.io.*;
import java.nio.file.*;
import java.sql.*;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * MyBatis XML 파일들을 재귀적으로 검색하여 모든 파라미터를 추출하는 프로그램
 * DB 샘플 값 수집 기능 추가
 */
public class MyBatisBulkPreparator {
    
    private static final Pattern PARAM_PATTERN = Pattern.compile("(#\\{[^}]+\\}|\\$\\{[^}]+\\})");
    private static final String OUTPUT_FILE = "parameters.properties";
    private static final String DEFAULT_PARAMS_FILE = "default.parameters";
    // METADATA_FILE 경로를 동적으로 설정하도록 변경
    
    public static void main(String[] args) {
        if (args.length < 1) {
            printUsage();
            return;
        }
        
        String directoryPath = args[0];
        String dbType = null;
        String dateFormat = "YYYY-MM-DD";
        
        // 옵션 파싱
        for (int i = 1; i < args.length; i++) {
            switch (args[i]) {
                case "--db":
                    if (i + 1 < args.length) {
                        dbType = args[++i];
                    } else {
                        System.err.println("오류: --db 옵션에 데이터베이스 타입을 지정해주세요.");
                        return;
                    }
                    break;
                case "--date-format":
                    if (i + 1 < args.length) {
                        dateFormat = args[++i];
                    } else {
                        System.err.println("오류: --date-format 옵션에 날짜 포맷을 지정해주세요.");
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
        System.out.println("사용법: java MyBatisBulkPreparator <디렉토리경로> [옵션]");
        System.out.println("옵션:");
        System.out.println("  --db <type>           데이터베이스 타입 (oracle, mysql, postgresql)");
        System.out.println("  --date-format <fmt>   날짜 포맷 (기본값: YYYY-MM-DD)");
        System.out.println();
        System.out.println("예시:");
        System.out.println("  java MyBatisBulkPreparator /path/to/mappers");
        System.out.println("  java MyBatisBulkPreparator /path/to/mappers --db postgresql");
        System.out.println("  java MyBatisBulkPreparator /path/to/mappers --db oracle --date-format YYYY/MM/DD");
        System.out.println();
        System.out.println("환경변수 설정:");
        System.out.println("  Oracle: ORACLE_SVC_USER, ORACLE_SVC_PASSWORD, ORACLE_SVC_CONNECT_STRING");
        System.out.println("  MySQL: MYSQL_ADM_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_TCP_PORT, MYSQL_DB");
        System.out.println("  PostgreSQL: PGUSER, PGPASSWORD, PGHOST, PGPORT, PGDATABASE");
    }
    
    /**
     * DB 샘플 값과 함께 파라미터 추출
     */
    public void extractParametersWithDbSamples(String directoryPath, String dbType, String dateFormat) {
        try {
            System.out.println("=== MyBatis 파라미터 추출 + DB 샘플 값 수집 ===");
            System.out.println("검색 디렉토리: " + directoryPath);
            System.out.println("데이터베이스 타입: " + dbType.toUpperCase());
            System.out.println("날짜 포맷: " + dateFormat);
            System.out.println();
            
            // 1. 파라미터 추출
            Set<String> allParameters = extractParametersFromDirectory(directoryPath);
            
            // 2. 메타데이터 로드
            List<ColumnInfo> columns = loadMetadata(directoryPath);
            System.out.println("발견된 컬럼: " + columns.size() + "개");
            
            // 3. 파라미터-컬럼 매칭
            Map<String, List<ColumnInfo>> matches = findMatches(allParameters, columns);
            
            // 4. DB 연결 및 샘플 값 수집 (default.parameters 체크 포함)
            Map<String, SampleValue> sampleValues = collectSampleValues(matches, dbType, dateFormat);
            
            // 5. 기본값 로드 (파라미터 파일 생성용)
            Map<String, String> defaultValues = loadDefaultParameters();
            
            // 6. 파라미터 파일 생성 (기본값 + DB 샘플 값)
            generateParameterFileWithSamples(allParameters, defaultValues, sampleValues);
            
            // 7. 결과 출력
            printSummary(allParameters, defaultValues, sampleValues);
            
        } catch (Exception e) {
            System.err.println("오류 발생: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    /**
     * 기존 파라미터 추출 (DB 연결 없음)
     */
    public void extractAllParameters(String directoryPath) {
        try {
            System.out.println("=== MyBatis 대량 파라미터 추출 시작 ===");
            System.out.println("검색 디렉토리: " + directoryPath);
            
            Set<String> allParameters = extractParametersFromDirectory(directoryPath);
            generateParameterFile(allParameters);
            
            System.out.println("\n=== 완료 ===");
            System.out.println("파라미터 파일: " + OUTPUT_FILE);
            System.out.println("파일을 편집한 후 MyBatisBulkExecutor로 실행하세요.");
            
        } catch (Exception e) {
            System.err.println("오류 발생: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    /**
     * 디렉토리에서 모든 파라미터 추출
     */
    private Set<String> extractParametersFromDirectory(String directoryPath) throws IOException {
        // 1. XML 파일들을 재귀적으로 찾기
        List<Path> xmlFiles = findXmlFiles(Paths.get(directoryPath));
        System.out.println("발견된 XML 파일 수: " + xmlFiles.size());
        
        // 2. 모든 파라미터 수집 (중복 제거, 자동 정렬)
        Set<String> allParameters = new TreeSet<>();
        int totalSqlCount = 0;
        
        for (Path xmlFile : xmlFiles) {
            System.out.println("처리 중: " + xmlFile.getFileName());
            int sqlCount = processXmlFile(xmlFile, allParameters);
            totalSqlCount += sqlCount;
        }
        
        // 3. 결과 출력
        System.out.println("\n=== 추출 결과 ===");
        System.out.println("처리된 XML 파일: " + xmlFiles.size() + "개");
        System.out.println("처리된 SQL 구문: " + totalSqlCount + "개");
        System.out.println("발견된 고유 파라미터: " + allParameters.size() + "개");
        
        if (!allParameters.isEmpty()) {
            System.out.println("\n=== 발견된 파라미터 (알파벳순) ===");
            allParameters.forEach(param -> System.out.println("#{" + param + "}"));
        }
        
        return allParameters;
    }
    
    /**
     * 메타데이터 파일 로드
     */
    private List<ColumnInfo> loadMetadata(String mapperPath) throws IOException {
        List<ColumnInfo> columns = new ArrayList<>();
        
        // 매퍼 경로에서 oma_metadata.txt 파일 찾기
        String metadataFile = mapperPath + "/oma_metadata.txt";
        Path metadataPath = Paths.get(metadataFile);
        
        if (!Files.exists(metadataPath)) {
            System.out.println("⚠️  메타데이터 파일을 찾을 수 없습니다: " + metadataFile);
            System.out.println("   DB 샘플 값 수집을 건너뜁니다.");
            return columns;
        }
        
        try (BufferedReader reader = Files.newBufferedReader(metadataPath)) {
            String line;
            int lineCount = 0;
            
            while ((line = reader.readLine()) != null) {
                lineCount++;
                if (lineCount <= 2) continue; // 헤더 스킵
                
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
     * default.parameters 파일에서 기본값 로드
     */
    private Map<String, String> loadDefaultParameters() {
        Map<String, String> defaultValues = new HashMap<>();
        
        try (BufferedReader reader = Files.newBufferedReader(Paths.get(DEFAULT_PARAMS_FILE))) {
            String line;
            int lineCount = 0;
            
            while ((line = reader.readLine()) != null) {
                lineCount++;
                line = line.trim();
                
                // 주석이나 빈 줄 스킵
                if (line.isEmpty() || line.startsWith("#")) {
                    continue;
                }
                
                // key=value 형태 파싱
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
                System.out.println("기본값 파일 로드 완료: " + DEFAULT_PARAMS_FILE + " (" + defaultValues.size() + "개 값)");
            }
            
        } catch (IOException e) {
            System.out.println("기본값 파일을 찾을 수 없습니다: " + DEFAULT_PARAMS_FILE + " (스킵)");
        }
        
        return defaultValues;
    }
    
    /**
     * 파라미터와 컬럼 매칭
     */
    private Map<String, List<ColumnInfo>> findMatches(Set<String> parameters, List<ColumnInfo> columns) {
        Map<String, List<ColumnInfo>> matches = new HashMap<>();
        
        for (String param : parameters) {
            String paramNormalized = normalizeName(param);
            List<ColumnInfo> matchingColumns = new ArrayList<>();
            
            for (ColumnInfo column : columns) {
                String columnNormalized = normalizeName(column.column);
                
                // 정확한 매치
                if (paramNormalized.equals(columnNormalized)) {
                    column.matchType = "exact";
                    column.score = 100;
                    matchingColumns.add(column);
                }
                // 파라미터가 컬럼명에 포함
                else if (columnNormalized.contains(paramNormalized)) {
                    ColumnInfo match = new ColumnInfo(column);
                    match.matchType = "param_in_column";
                    match.score = 80;
                    matchingColumns.add(match);
                }
                // 컬럼명이 파라미터에 포함
                else if (paramNormalized.contains(columnNormalized)) {
                    ColumnInfo match = new ColumnInfo(column);
                    match.matchType = "column_in_param";
                    match.score = 70;
                    matchingColumns.add(match);
                }
            }
            
            // 점수순으로 정렬
            matchingColumns.sort((a, b) -> Integer.compare(b.score, a.score));
            matches.put(param, matchingColumns);
        }
        
        return matches;
    }
    
    /**
     * DB에서 샘플 값 수집 (default.parameters에 값이 있는 파라미터는 제외)
     */
    private Map<String, SampleValue> collectSampleValues(Map<String, List<ColumnInfo>> matches, String dbType, String dateFormat) {
        Map<String, SampleValue> sampleValues = new HashMap<>();
        
        // default.parameters 파일에서 기본값 로드
        Map<String, String> defaultValues = loadDefaultParameters();
        
        try (Connection conn = createConnection(dbType)) {
            System.out.println("\n=== 샘플 값 수집 중 ===");
            
            int processedCount = 0;
            int skippedCount = 0;
            
            for (Map.Entry<String, List<ColumnInfo>> entry : matches.entrySet()) {
                String param = entry.getKey();
                List<ColumnInfo> matchingColumns = entry.getValue();
                
                // default.parameters에 값이 이미 설정된 파라미터는 스킵
                if (defaultValues.containsKey(param) && !defaultValues.get(param).trim().isEmpty()) {
                    skippedCount++;
                    System.out.printf("SKIP: %s (기본값 사용: %s)%n", param, defaultValues.get(param));
                    continue;
                }
                
                if (!matchingColumns.isEmpty()) {
                    ColumnInfo bestMatch = matchingColumns.get(0);
                    // 정확한 매치 또는 부분 매치만 처리
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
                            System.out.printf("   → 샘플 값: %s%n", sampleValue);
                        } else {
                            System.out.printf("   → 샘플 값 없음 (NULL 또는 오류)%n");
                        }
                    }
                }
            }
            
            if (skippedCount > 0) {
                System.out.printf("\n기본값으로 인해 스킵된 파라미터: %d개%n", skippedCount);
            }
            
        } catch (Exception e) {
            System.err.println("DB 연결 또는 샘플 값 수집 중 오류: " + e.getMessage());
            e.printStackTrace();
        }
        
        return sampleValues;
    }
    
    /**
     * DB 연결 생성 (MyBatisBulkExecutorWithJson에서 참조)
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
                throw new SQLException("지원하지 않는 데이터베이스 타입: " + dbType);
        }
    }
    
    private Connection createOracleConnection() throws SQLException {
        String connectString = System.getenv("ORACLE_SVC_CONNECT_STRING");
        String username = System.getenv("ORACLE_SVC_USER");
        String password = System.getenv("ORACLE_SVC_PASSWORD");
        String tnsAdmin = System.getenv("TNS_ADMIN");
        String oracleHome = System.getenv("ORACLE_HOME");
        
        if (username == null || password == null) {
            throw new SQLException("Oracle 환경변수가 설정되지 않았습니다. 필요한 변수: ORACLE_SVC_USER, ORACLE_SVC_PASSWORD");
        }
        
        // TNS_ADMIN 자동 설정 (개선된 로직)
        if (tnsAdmin == null && oracleHome != null) {
            tnsAdmin = oracleHome + "/network/admin";
            System.setProperty("oracle.net.tns_admin", tnsAdmin);
            System.out.println("TNS_ADMIN 자동 설정: " + tnsAdmin);
        }
        
        String jdbcUrl;
        if (tnsAdmin != null && connectString != null) {
            // TNS 이름 사용
            jdbcUrl = "jdbc:oracle:thin:@" + connectString;
        } else {
            // 기본 연결 방식
            String defaultService = "orcl";
            jdbcUrl = "jdbc:oracle:thin:@" + (connectString != null ? connectString : defaultService);
        }
        
        System.out.println("Oracle 연결 정보: " + username + "@" + jdbcUrl);
        
        return DriverManager.getConnection(jdbcUrl, username, password);
    }
    
    private Connection createMySQLConnection() throws SQLException {
        String host = System.getenv("MYSQL_HOST");
        String port = System.getenv("MYSQL_TCP_PORT");
        String database = System.getenv("MYSQL_DB");
        String username = System.getenv("MYSQL_ADM_USER");
        String password = System.getenv("MYSQL_PASSWORD");
        
        if (username == null || password == null) {
            throw new SQLException("MySQL 환경변수가 설정되지 않았습니다. 필요한 변수: MYSQL_ADM_USER, MYSQL_PASSWORD");
        }
        
        if (host == null) host = "localhost";
        if (port == null) port = "3306";
        if (database == null) database = "test";
        
        String jdbcUrl = String.format("jdbc:mysql://%s:%s/%s?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC", 
            host, port, database);
        System.out.println("MySQL 연결 정보: " + username + "@" + jdbcUrl);
        
        return DriverManager.getConnection(jdbcUrl, username, password);
    }
    
    private Connection createPostgreSQLConnection() throws SQLException {
        String host = System.getenv("PGHOST");
        String port = System.getenv("PGPORT");
        String database = System.getenv("PGDATABASE");
        String username = System.getenv("PGUSER");
        String password = System.getenv("PGPASSWORD");
        
        if (username == null || password == null) {
            throw new SQLException("PostgreSQL 환경변수가 설정되지 않았습니다. 필요한 변수: PGUSER, PGPASSWORD");
        }
        
        if (host == null) host = "localhost";
        if (port == null) port = "5432";
        if (database == null) database = "postgres";
        
        String jdbcUrl = String.format("jdbc:postgresql://%s:%s/%s", host, port, database);
        System.out.println("PostgreSQL 연결 정보: " + username + "@" + jdbcUrl);
        
        return DriverManager.getConnection(jdbcUrl, username, password);
    }
    
    /**
     * DB에서 샘플 값 가져오기
     */
    private String getSampleValue(Connection conn, ColumnInfo column, String dateFormat, String dbType) {
        try {
            String query;
            
            // 날짜 타입인 경우 포맷 적용
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
            System.out.printf("  오류: %s.%s.%s - %s%n", column.schema, column.table, column.column, e.getMessage());
        }
        
        return null;
    }
    
    /**
     * 날짜 포맷 변환 (DB별)
     */
    private String convertDateFormat(String format, String dbType) {
        if (dbType.equalsIgnoreCase("mysql")) {
            // MySQL DATE_FORMAT 포맷으로 변환
            return format.replace("YYYY", "%Y")
                        .replace("MM", "%m")
                        .replace("DD", "%d")
                        .replace("HH24", "%H")
                        .replace("MI", "%i")
                        .replace("SS", "%s");
        }
        // PostgreSQL, Oracle은 동일한 포맷 사용
        return format;
    }
    
    /**
     * 날짜/시간 타입 확인
     */
    private boolean isDateType(String dataType) {
        String lowerType = dataType.toLowerCase();
        return lowerType.contains("timestamp") || lowerType.contains("date") || lowerType.contains("time");
    }
    
    /**
     * 이름 정규화
     */
    private String normalizeName(String name) {
        return name.toLowerCase().replaceAll("[_\\s]", "");
    }
    
    /**
     * 샘플 값이 포함된 파라미터 파일 생성
     */
    private void generateParameterFileWithSamples(Set<String> parameters, Map<String, String> defaultValues, Map<String, SampleValue> sampleValues) throws IOException {
        try (PrintWriter writer = new PrintWriter(new FileWriter(OUTPUT_FILE))) {
            writer.println("# MyBatis 파라미터 설정 파일 (기본값 + DB 샘플 값 포함)");
            writer.println("# 생성일시: " + new java.util.Date());
            writer.println("# 우선순위: DB 샘플 값 > 기본값 > 빈 값");
            writer.println();
            
            // 매치되지 않은 파라미터들을 먼저 출력
            writer.println("# 매치 없음 - 기본값 또는 수동 설정");
            boolean hasUnmatched = false;
            for (String param : parameters) {
                if (!sampleValues.containsKey(param)) {
                    // 기본값이 있으면 사용, 없으면 추정값 사용
                    String value = defaultValues.getOrDefault(param, suggestDefaultValue(param));
                    writer.println(param + "=" + value);
                    hasUnmatched = true;
                }
            }
            
            if (hasUnmatched) {
                writer.println();
            }
            
            // 매치된 파라미터들 출력 (DB 샘플 값)
            for (String param : parameters) {
                SampleValue sample = sampleValues.get(param);
                if (sample != null) {
                    writer.printf("# %s (%s) - %s 매치%n", sample.source, sample.dataType, sample.matchType);
                    writer.println(param + "=" + sample.value);
                    writer.println();
                }
            }
        }
    }
    
    /**
     * 결과 요약 출력
     */
    private void printSummary(Set<String> parameters, Map<String, String> defaultValues, Map<String, SampleValue> sampleValues) {
        int totalParams = parameters.size();
        int dbSampleCount = sampleValues.size();
        int defaultValueCount = 0;
        int emptyCount = 0;
        
        // 매치되지 않은 파라미터들 중 기본값이 있는 것과 없는 것 구분
        for (String param : parameters) {
            if (!sampleValues.containsKey(param)) {
                if (defaultValues.containsKey(param) && !defaultValues.get(param).isEmpty()) {
                    defaultValueCount++;
                } else {
                    emptyCount++;
                }
            }
        }
        
        System.out.println("\n=== 최종 통계 ===");
        System.out.println("총 파라미터: " + totalParams + "개");
        System.out.println("DB 샘플 값: " + dbSampleCount + "개");
        System.out.println("기본값 사용: " + defaultValueCount + "개");
        System.out.println("수동 설정 필요: " + emptyCount + "개");
        System.out.printf("자동 설정률: %.1f%% (DB 샘플 + 기본값)%n", 
            ((dbSampleCount + defaultValueCount) * 100.0 / totalParams));
        System.out.println("\nparameters.properties 파일이 생성되었습니다.");
        
        // 수동 설정이 필요한 파라미터 목록
        Set<String> manualParams = new TreeSet<>();
        for (String param : parameters) {
            if (!sampleValues.containsKey(param) && 
                (!defaultValues.containsKey(param) || defaultValues.get(param).isEmpty())) {
                manualParams.add(param);
            }
        }
        
        if (!manualParams.isEmpty()) {
            System.out.println("\n수동 설정 필요한 파라미터:");
            manualParams.forEach(param -> System.out.println("  - " + param));
        }
        
        if (defaultValueCount > 0) {
            System.out.println("\n기본값이 적용된 파라미터:");
            for (String param : parameters) {
                if (!sampleValues.containsKey(param) && 
                    defaultValues.containsKey(param) && !defaultValues.get(param).isEmpty()) {
                    System.out.println("  - " + param + " = " + defaultValues.get(param));
                }
            }
        }
    }
    
    // 기존 메서드들...
    
    /**
     * 디렉토리에서 XML 파일들을 재귀적으로 찾기
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
     * XML 파일에서 모든 파라미터 추출
     */
    private int processXmlFile(Path xmlFile, Set<String> allParameters) {
        try {
            String content = Files.readString(xmlFile);
            
            // SQL 태그 개수 세기
            int sqlCount = countSqlTags(content);
            
            // 파라미터 추출
            Set<String> fileParameters = extractParameters(content);
            allParameters.addAll(fileParameters);
            
            if (!fileParameters.isEmpty()) {
                System.out.println("  -> " + fileParameters.size() + "개 파라미터, " + sqlCount + "개 SQL");
            }
            
            return sqlCount;
            
        } catch (IOException e) {
            System.err.println("파일 읽기 오류: " + xmlFile + " - " + e.getMessage());
            return 0;
        }
    }
    
    /**
     * SQL 태그 개수 세기
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
     * 파라미터 추출 (JDBC 타입, typeHandler 등 모든 속성 제거)
     */
    private Set<String> extractParameters(String content) {
        Set<String> parameters = new TreeSet<>();
        Matcher matcher = PARAM_PATTERN.matcher(content);
        
        while (matcher.find()) {
            String param = matcher.group(1);
            // #{paramName} 또는 ${paramName}에서 paramName만 추출
            String paramContent = param.substring(2, param.length() - 1);
            
            // JDBC 타입, typeHandler, mode 등 모든 속성 제거 (콤마 앞부분만 사용)
            String paramName = paramContent;
            if (paramContent.contains(",")) {
                paramName = paramContent.split(",")[0];
            }
            
            // 점이나 대괄호가 있는 경우 첫 번째 부분만 사용 (예: user.name -> user)
            if (paramName.contains(".")) {
                paramName = paramName.split("\\.")[0];
            }
            if (paramName.contains("[")) {
                paramName = paramName.split("\\[")[0];
            }
            
            // 공백, 탭, 특수문자 제거
            paramName = paramName.trim();
            paramName = paramName.replaceAll("[\\s\\t]+", "");
            
            // 유효하지 않은 파라미터 제외
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
     * 파라미터명에 따른 기본값 제안 (dtm만)
     */
    private String suggestDefaultValue(String paramName) {
        String lowerName = paramName.toLowerCase();
        
        // dtm이 포함된 경우만 기본값 제안
        if (lowerName.contains("dtm")) {
            return "20250801";
        }
        
        // 나머지는 빈 값
        return "";
    }
    
    /**
     * 파라미터 파일 생성 (알파벳순 정렬)
     */
    private void generateParameterFile(Set<String> parameters) throws IOException {
        try (PrintWriter writer = new PrintWriter(new FileWriter(OUTPUT_FILE))) {
            writer.println("# MyBatis 파라미터 설정 파일 (대량 추출)");
            writer.println("# 생성일시: " + new java.util.Date());
            writer.println("# 사용법: 각 파라미터에 대해 테스트용 값을 설정하세요.");
            writer.println("# 빈 값은 null로 처리됩니다.");
            writer.println();
            
            // TreeSet을 사용했으므로 이미 알파벳순으로 정렬됨
            for (String param : parameters) {
                String defaultValue = suggestDefaultValue(param);
                writer.println(param + "=" + defaultValue);
            }
        }
    }
    
    // 내부 클래스들
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
