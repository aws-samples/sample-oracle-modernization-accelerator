package com.test.mybatis;

import java.io.*;
import java.sql.*;
import java.util.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.regex.Pattern;
import java.util.regex.Matcher;

/**
 * 간단하고 확실한 바인드 변수 생성기
 * Oracle 딕셔너리 + 매퍼 바인드 변수 추출 + 매칭 + mismatch.lst 생성
 */
public class SimpleBindVariableGenerator {
    
    // Oracle 연결 정보
    // Oracle 연결 정보
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
        new SimpleBindVariableGenerator().run(mapperDir);
    }
    
    private void run(String mapperDir) {
        System.out.println("=== 간단한 바인드 변수 생성기 ===\n");
        
        try {
            // 1. Oracle 딕셔너리 수집
            collectOracleDictionary();
            
            // 2. 매퍼에서 바인드 변수 추출
            extractBindVariables(mapperDir);
            
            // 3. 딕셔너리와 매칭
            matchWithDictionary();
            
            // 4. 파일 생성
            generateFiles();
            
            System.out.println("✓ 완료!");
            
        } catch (Exception e) {
            System.err.println("오류: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private void collectOracleDictionary() throws Exception {
        System.out.println("1단계: Oracle 딕셔너리 수집...");
        
        try {
            // SERVICE_NAME 환경변수 사용
            String url = String.format("jdbc:oracle:thin:@%s:%s/%s", ORACLE_HOST, ORACLE_PORT, SERVICE_NAME);
            System.out.println("Oracle 연결 시도: " + url);
            
            try (Connection conn = DriverManager.getConnection(url, ORACLE_SVC_USER, ORACLE_SVC_PASSWORD)) {
                System.out.println("✓ Oracle DB 접속 성공");
                
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
                        
                        System.out.printf("✓ Oracle 딕셔너리 수집 완료 (%d개 컬럼)\n\n", count);
                    }
                }
            }
        } catch (Exception e) {
            System.out.println("❌ Oracle 딕셔너리 수집 실패: " + e.getMessage());
            System.out.println("Oracle 연결 정보를 확인해주세요.");
            throw e;
        }
    }
    
    private void extractBindVariables(String mapperDir) throws Exception {
        System.out.println("2단계: 매퍼에서 바인드 변수 추출...");
        
        File dir = new File(mapperDir);
        if (!dir.exists()) {
            throw new Exception("매퍼 디렉토리를 찾을 수 없습니다: " + mapperDir);
        }
        
        List<File> xmlFiles = findXmlFiles(dir);
        System.out.printf("발견된 XML 파일: %d개\n", xmlFiles.size());
        
        Pattern bindPattern = Pattern.compile("#\\{([^}]+)\\}|\\$\\{([^}]+)\\}");
        
        for (File xmlFile : xmlFiles) {
            try (BufferedReader reader = new BufferedReader(new FileReader(xmlFile))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    Matcher matcher = bindPattern.matcher(line);
                    while (matcher.find()) {
                        String varName = matcher.group(1) != null ? matcher.group(1) : matcher.group(2);
                        
                        // 복합 변수명 처리 (user.name -> user)
                        if (varName.contains(".")) {
                            varName = varName.split("\\.")[0];
                        }
                        
                        bindVariables.computeIfAbsent(varName, k -> new BindVariable(k))
                                    .addFile(xmlFile.getAbsolutePath());
                    }
                }
            }
        }
        
        System.out.printf("✓ 바인드 변수 추출 완료 (%d개)\n\n", bindVariables.size());
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
        System.out.println("3단계: 딕셔너리와 매칭...");
        
        int matchedCount = 0;
        
        for (BindVariable bindVar : bindVariables.values()) {
            String varName = bindVar.getName().toLowerCase();
            
            // 딕셔너리에서 매칭되는 컬럼 찾기
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
            
            // 매칭되지 않은 경우 기본값 생성
            if (bindVar.getMatchedColumn() == null) {
                bindVar.setValue(generateDefaultValue(varName));
            }
        }
        
        System.out.printf("✓ 매칭 완료 (매칭: %d개, 매칭 없음: %d개)\n\n", 
                         matchedCount, bindVariables.size() - matchedCount);
    }
    
    private boolean isMatch(String varName, String columnName) {
        // 정확한 매칭
        if (varName.equals(columnName)) return true;
        
        // 부분 매칭
        if (varName.contains(columnName) || columnName.contains(varName)) return true;
        
        // ID 매칭
        if (varName.endsWith("id") && columnName.endsWith("_id")) return true;
        if (varName.contains("id") && columnName.contains("id")) return true;
        
        return false;
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
    
    private void generateFiles() throws Exception {
        System.out.println("4단계: 파일 생성...");
        
        // 매칭된 변수와 매칭되지 않은 변수 분리
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
        
        // parameters.properties 파일 생성
        try (PrintWriter writer = new PrintWriter(new FileWriter("parameters.properties"))) {
            writer.println("# 바인드 변수 매개변수 파일");
            writer.println("# 생성일시: " + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
            writer.println("# 총 변수: " + bindVariables.size() + "개 (매칭: " + matchedVars.size() + "개, 매칭 없음: " + unmatchedVars.size() + "개)");
            writer.println();
            
            // 매칭된 변수들
            if (!matchedVars.isEmpty()) {
                writer.println("# =============================================================================");
                writer.println("# 매칭된 변수들 (Oracle DB 컬럼과 매칭됨)");
                writer.println("# =============================================================================");
                writer.println();
                
                for (String varName : matchedVars) {
                    BindVariable bindVar = bindVariables.get(varName);
                    writer.println("# " + bindVar.getMatchedColumn());
                    writer.println(varName + "=" + bindVar.getValue());
                    writer.println();
                }
            }
            
            // 매칭되지 않은 변수들
            if (!unmatchedVars.isEmpty()) {
                writer.println("# =============================================================================");
                writer.println("# 매칭되지 않은 변수들 (수동으로 값을 설정해주세요)");
                writer.println("# =============================================================================");
                writer.println();
                
                for (String varName : unmatchedVars) {
                    BindVariable bindVar = bindVariables.get(varName);
                    writer.println("# 매칭 없음");
                    writer.println(varName + "=" + bindVar.getValue());
                    writer.println();
                }
            }
        }
        
        // mismatch.lst 파일 생성
        if (!unmatchedVars.isEmpty()) {
            new File("out").mkdirs();
            
            try (PrintWriter writer = new PrintWriter(new FileWriter("out/mismatch.lst"))) {
                writer.println("# 매칭되지 않은 바인드 변수 위치 정보");
                writer.println("# 생성일시: " + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
                writer.println("# 형식: 변수명 | 매퍼파일 | 라인번호 | SQL 컨텍스트");
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
        
        System.out.printf("✓ parameters.properties 생성 완료 (%d개 변수)\n", bindVariables.size());
        System.out.printf("  - 매칭됨: %d개\n", matchedVars.size());
        System.out.printf("  - 매칭 없음: %d개\n", unmatchedVars.size());
        
        if (!unmatchedVars.isEmpty()) {
            System.out.println("✓ out/mismatch.lst 생성 완료");
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
                    
                    writer.printf("%s | %s | 라인 %d | %s%n", 
                                varName, relativePath, lineNumber, context);
                }
            }
        } catch (Exception e) {
            // 무시
        }
    }
    
    private String getRelativePath(String absolutePath) {
        int workspaceIndex = absolutePath.indexOf("workspace/");
        if (workspaceIndex >= 0) {
            return absolutePath.substring(workspaceIndex);
        }
        return new File(absolutePath).getName();
    }
    
    // 내부 클래스들
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
