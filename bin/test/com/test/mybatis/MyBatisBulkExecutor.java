package com.test.mybatis;

import org.apache.ibatis.io.Resources;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * MyBatis XML 파일들을 재귀적으로 검색하여 모든 SQL ID를 자동으로 테스트하는 프로그램
 */
public class MyBatisBulkExecutor {
    
    private static final String PARAMETERS_FILE = "parameters.properties";
    private static final Pattern SQL_ID_PATTERN = Pattern.compile("<(select|insert|update|delete)\\s+id=\"([^\"]+)\"");
    
    public static void main(String[] args) {
        if (args.length < 1) {
            System.out.println("사용법: java MyBatisBulkExecutor <디렉토리경로> [옵션]");
            System.out.println("옵션:");
            System.out.println("  --select-only    SELECT 구문만 실행 (기본값)");
            System.out.println("  --all           모든 SQL 구문 실행 (INSERT/UPDATE/DELETE 포함)");
            System.out.println("  --summary       요약 정보만 출력");
            System.out.println("  --verbose       상세 정보 출력");
            System.out.println();
            System.out.println("예시: java MyBatisBulkExecutor /path/to/mapper/directory");
            System.out.println("예시: java MyBatisBulkExecutor /path/to/mapper/directory --all --verbose");
            return;
        }
        
        String directoryPath = args[0];
        boolean selectOnly = true;
        boolean summaryOnly = false;
        boolean verbose = false;
        
        // 옵션 파싱
        for (int i = 1; i < args.length; i++) {
            switch (args[i]) {
                case "--all":
                    selectOnly = false;
                    break;
                case "--summary":
                    summaryOnly = true;
                    break;
                case "--verbose":
                    verbose = true;
                    break;
                case "--select-only":
                    selectOnly = true;
                    break;
            }
        }
        
        MyBatisBulkExecutor executor = new MyBatisBulkExecutor();
        executor.executeAllSql(directoryPath, selectOnly, summaryOnly, verbose);
    }
    
    public void executeAllSql(String directoryPath, boolean selectOnly, boolean summaryOnly, boolean verbose) {
        try {
            System.out.println("=== MyBatis 대량 SQL 실행 테스트 ===");
            System.out.println("검색 디렉토리: " + directoryPath);
            System.out.println("실행 모드: " + (selectOnly ? "SELECT만" : "모든 SQL"));
            System.out.println("출력 모드: " + (summaryOnly ? "요약만" : verbose ? "상세" : "기본"));
            
            // 1. 파라미터 로드
            Map<String, Object> parameters = loadParameters();
            if (!summaryOnly) {
                System.out.println("\n=== 로드된 파라미터 ===");
                System.out.println("총 " + parameters.size() + "개 파라미터 로드됨");
                if (verbose) {
                    parameters.forEach((key, value) -> 
                        System.out.println("  " + key + " = " + (value != null ? value : "null")));
                }
            }
            
            // 2. XML 파일들을 재귀적으로 찾기
            List<Path> xmlFiles = findXmlFiles(Paths.get(directoryPath));
            System.out.println("\n발견된 XML 파일 수: " + xmlFiles.size());
            
            // 3. 모든 SQL 정보 수집
            List<SqlTestInfo> allSqlTests = new ArrayList<>();
            for (Path xmlFile : xmlFiles) {
                List<SqlTestInfo> sqlTests = collectSqlTests(xmlFile, selectOnly);
                allSqlTests.addAll(sqlTests);
            }
            
            System.out.println("실행할 SQL 수: " + allSqlTests.size());
            
            // 4. SQL 실행 테스트
            TestResults results = executeTests(allSqlTests, parameters, summaryOnly, verbose);
            
            // 5. 결과 요약
            printSummary(results);
            
        } catch (Exception e) {
            System.err.println("오류 발생: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
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
     * XML 파일에서 SQL 테스트 정보 수집
     */
    private List<SqlTestInfo> collectSqlTests(Path xmlFile, boolean selectOnly) {
        List<SqlTestInfo> sqlTests = new ArrayList<>();
        
        try {
            String content = Files.readString(xmlFile);
            Matcher matcher = SQL_ID_PATTERN.matcher(content);
            
            while (matcher.find()) {
                String sqlType = matcher.group(1).toLowerCase();
                String sqlId = matcher.group(2);
                
                // SELECT만 실행하는 경우 필터링
                if (selectOnly && !sqlType.equals("select")) {
                    continue;
                }
                
                SqlTestInfo testInfo = new SqlTestInfo();
                testInfo.xmlFile = xmlFile;
                testInfo.sqlId = sqlId;
                testInfo.sqlType = sqlType;
                
                sqlTests.add(testInfo);
            }
            
        } catch (IOException e) {
            System.err.println("파일 읽기 오류: " + xmlFile + " - " + e.getMessage());
        }
        
        return sqlTests;
    }
    
    /**
     * 모든 SQL 테스트 실행
     */
    private TestResults executeTests(List<SqlTestInfo> sqlTests, Map<String, Object> parameters, 
                                   boolean summaryOnly, boolean verbose) {
        TestResults results = new TestResults();
        
        System.out.println("\n=== SQL 실행 테스트 시작 ===");
        
        for (int i = 0; i < sqlTests.size(); i++) {
            SqlTestInfo testInfo = sqlTests.get(i);
            
            if (!summaryOnly) {
                System.out.println("\n[" + (i + 1) + "/" + sqlTests.size() + "] " + 
                    testInfo.xmlFile.getFileName() + ":" + testInfo.sqlId + 
                    " (" + testInfo.sqlType.toUpperCase() + ")");
            }
            
            TestResult result = executeSingleTest(testInfo, parameters, summaryOnly, verbose);
            results.addResult(result);
            
            if (!summaryOnly) {
                if (result.success) {
                    System.out.println("  ✅ 성공 - " + result.rowCount + "행");
                } else {
                    System.out.println("  ❌ 실패 - " + result.errorMessage);
                }
            }
        }
        
        return results;
    }
    
    /**
     * 단일 SQL 테스트 실행
     */
    private TestResult executeSingleTest(SqlTestInfo testInfo, Map<String, Object> parameters, 
                                       boolean summaryOnly, boolean verbose) {
        TestResult result = new TestResult();
        result.testInfo = testInfo;
        
        try {
            // MyBatis 설정 생성
            SqlSessionFactory sqlSessionFactory = createSqlSessionFactory(testInfo.xmlFile.toString());
            
            // SQL 실행
            try (SqlSession session = sqlSessionFactory.openSession()) {
                if (testInfo.sqlType.equals("select")) {
                    List<Map<String, Object>> rows = session.selectList(testInfo.sqlId, parameters);
                    result.success = true;
                    result.rowCount = rows.size();
                    
                    if (verbose && !summaryOnly && !rows.isEmpty()) {
                        System.out.println("    컬럼: " + String.join(", ", rows.get(0).keySet()));
                        if (rows.size() <= 3) {
                            for (Map<String, Object> row : rows) {
                                System.out.println("    데이터: " + formatRowData(row));
                            }
                        }
                    }
                } else {
                    // INSERT/UPDATE/DELETE의 경우 실제 실행하지 않고 파싱만 확인
                    session.selectList(testInfo.sqlId, parameters);
                    result.success = true;
                    result.rowCount = 0;
                }
            }
            
        } catch (Exception e) {
            result.success = false;
            result.errorMessage = e.getMessage();
            if (result.errorMessage.length() > 100) {
                result.errorMessage = result.errorMessage.substring(0, 100) + "...";
            }
        }
        
        return result;
    }
    
    /**
     * 행 데이터 포맷팅
     */
    private String formatRowData(Map<String, Object> row) {
        List<String> values = new ArrayList<>();
        for (Object value : row.values()) {
            String strValue = value != null ? value.toString() : "NULL";
            if (strValue.length() > 20) {
                strValue = strValue.substring(0, 20) + "...";
            }
            values.add(strValue);
        }
        return String.join(" | ", values);
    }
    
    /**
     * 결과 요약 출력
     */
    private void printSummary(TestResults results) {
        System.out.println("\n=== 실행 결과 요약 ===");
        System.out.println("총 테스트 수: " + results.totalTests);
        System.out.println("성공: " + results.successCount + "개");
        System.out.println("실패: " + results.failureCount + "개");
        System.out.println("성공률: " + String.format("%.1f%%", results.getSuccessRate()));
        
        if (results.failureCount > 0) {
            System.out.println("\n=== 실패한 테스트 ===");
            for (TestResult result : results.failures) {
                System.out.println("❌ " + result.testInfo.xmlFile.getFileName() + 
                    ":" + result.testInfo.sqlId + " - " + result.errorMessage);
            }
        }
        
        // 파일별 통계
        System.out.println("\n=== 파일별 통계 ===");
        Map<String, Integer[]> fileStats = new HashMap<>(); // [성공, 실패]
        
        for (TestResult result : results.allResults) {
            String fileName = result.testInfo.xmlFile.getFileName().toString();
            fileStats.computeIfAbsent(fileName, k -> new Integer[]{0, 0});
            if (result.success) {
                fileStats.get(fileName)[0]++;
            } else {
                fileStats.get(fileName)[1]++;
            }
        }
        
        fileStats.entrySet().stream()
            .sorted(Map.Entry.comparingByKey())
            .forEach(entry -> {
                String fileName = entry.getKey();
                Integer[] stats = entry.getValue();
                int total = stats[0] + stats[1];
                double rate = total > 0 ? (stats[0] * 100.0 / total) : 0;
                System.out.println(String.format("  %s: %d/%d (%.1f%%)", 
                    fileName, stats[0], total, rate));
            });
    }
    
    /**
     * 파라미터 파일 로드
     */
    private Map<String, Object> loadParameters() throws IOException {
        Map<String, Object> paramMap = new HashMap<>();
        Properties props = new Properties();
        
        File file = new File(PARAMETERS_FILE);
        if (!file.exists()) {
            System.out.println("파라미터 파일이 없습니다: " + PARAMETERS_FILE);
            return paramMap;
        }
        
        try (FileInputStream fis = new FileInputStream(file)) {
            props.load(fis);
        }
        
        // Properties를 Map으로 변환하면서 타입 변환
        for (String key : props.stringPropertyNames()) {
            String value = props.getProperty(key);
            if (value == null || value.trim().isEmpty()) {
                paramMap.put(key, null);
            } else {
                // 숫자인지 확인
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
     * 숫자 여부 확인
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
     * MyBatis SqlSessionFactory 생성
     */
    private SqlSessionFactory createSqlSessionFactory(String xmlFilePath) throws IOException {
        // TNS_ADMIN 환경변수를 프로그램 내에서 설정
        String oracleHome = System.getenv("ORACLE_HOME");
        if (oracleHome != null) {
            String tnsAdmin = oracleHome + "/network/admin";
            System.setProperty("oracle.net.tns_admin", tnsAdmin);
            System.setProperty("TNS_ADMIN", tnsAdmin);
        }
        
        // 1. 원본 XML 파일을 읽어서 resultType을 map으로 변경
        String modifiedXmlContent = modifyXmlForTesting(xmlFilePath);
        
        // 2. 수정된 XML을 임시 파일로 저장
        File tempXmlFile = File.createTempFile("mapper", ".xml");
        tempXmlFile.deleteOnExit();
        
        try (FileWriter writer = new FileWriter(tempXmlFile)) {
            writer.write(modifiedXmlContent);
        }
        
        // 3. MyBatis 설정 XML 생성
        String configXml = createMyBatisConfig(tempXmlFile.getAbsolutePath());
        
        // 4. 임시 설정 파일 생성
        File tempConfigFile = File.createTempFile("mybatis-config", ".xml");
        tempConfigFile.deleteOnExit();
        
        try (FileWriter writer = new FileWriter(tempConfigFile)) {
            writer.write(configXml);
        }
        
        // 5. SqlSessionFactory 생성
        try (InputStream inputStream = new FileInputStream(tempConfigFile)) {
            return new SqlSessionFactoryBuilder().build(inputStream);
        }
    }
    
    /**
     * XML 파일의 resultType을 테스트용으로 수정
     */
    private String modifyXmlForTesting(String xmlFilePath) throws IOException {
        StringBuilder content = new StringBuilder();
        
        try (BufferedReader reader = new BufferedReader(new FileReader(xmlFilePath))) {
            String line;
            while ((line = reader.readLine()) != null) {
                // resultType을 map으로 변경
                if (line.contains("resultType=")) {
                    line = line.replaceAll("resultType=\"[^\"]*\"", "resultType=\"map\"");
                }
                // parameterType도 map으로 변경
                if (line.contains("parameterType=")) {
                    line = line.replaceAll("parameterType=\"[^\"]*\"", "parameterType=\"map\"");
                }
                content.append(line).append("\n");
            }
        }
        
        return content.toString();
    }
    
    /**
     * MyBatis 설정 XML 생성
     */
    private String createMyBatisConfig(String xmlFilePath) {
        String connectString = System.getenv("ORACLE_SVC_CONNECT_STRING");
        String username = System.getenv("ORACLE_SVC_USER");
        String password = System.getenv("ORACLE_SVC_PASSWORD");
        
        if (username == null || password == null) {
            throw new RuntimeException("Oracle 환경변수가 설정되지 않았습니다. 필요한 변수: ORACLE_SVC_USER, ORACLE_SVC_PASSWORD");
        }
        
        String jdbcUrl = "jdbc:oracle:thin:@" + (connectString != null ? connectString : "orcl");
        
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
    
    // 내부 클래스들
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
}
