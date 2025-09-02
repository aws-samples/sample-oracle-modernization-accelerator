package com.test.mybatis;

import org.apache.ibatis.io.Resources;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;

import java.io.*;
import java.util.*;

/**
 * MyBatis를 사용한 간단한 SQL 실행 프로그램
 * 파라미터 파일만 있으면 동적 조건까지 자동으로 처리됩니다.
 */
public class MyBatisSimpleExecutor {
    
    private static final String PARAMETERS_FILE = "parameters.properties";
    
    public static void main(String[] args) {
        if (args.length < 2) {
            System.out.println("사용법: java MyBatisSimpleExecutor <XML파일경로> <SQLID>");
            System.out.println("예시: java MyBatisSimpleExecutor /path/to/mapper.xml selectInventoryStatusAnalysis");
            System.out.println("Oracle 환경변수가 설정되어 있어야 합니다 (ORACLE_SVC_USER, ORACLE_SVC_PASSWORD).");
            System.out.println("tnsnames에서 orcl로 접속 가능해야 합니다.");
            return;
        }
        
        String xmlFilePath = args[0];
        String sqlId = args[1];
        
        MyBatisSimpleExecutor executor = new MyBatisSimpleExecutor();
        executor.executeWithMyBatis(xmlFilePath, sqlId);
    }
    
    public void executeWithMyBatis(String xmlFilePath, String sqlId) {
        try {
            System.out.println("=== MyBatis 간단 실행 프로그램 ===");
            System.out.println("XML 파일: " + xmlFilePath);
            System.out.println("SQL ID: " + sqlId);
            
            // 1. 파라미터 로드
            Map<String, Object> parameters = loadParameters();
            System.out.println("\n=== 로드된 파라미터 ===");
            parameters.forEach((key, value) -> 
                System.out.println(key + " = " + value));
            
            // 2. MyBatis 설정 생성
            SqlSessionFactory sqlSessionFactory = createSqlSessionFactory(xmlFilePath);
            
            // 3. SQL 실행
            try (SqlSession session = sqlSessionFactory.openSession()) {
                System.out.println("\n=== SQL 실행 ===");
                
                // SQL ID로 직접 실행 (MyBatis가 동적 조건 자동 처리)
                List<Map<String, Object>> results = session.selectList(sqlId, parameters);
                
                System.out.println("실행 결과:");
                if (results.isEmpty()) {
                    System.out.println("결과가 없습니다.");
                } else {
                    // 첫 번째 행의 컬럼명 출력
                    Map<String, Object> firstRow = results.get(0);
                    System.out.println("컬럼: " + String.join(", ", firstRow.keySet()));
                    System.out.println("─".repeat(80));
                    
                    // 데이터 출력 (최대 10행)
                    int count = 0;
                    for (Map<String, Object> row : results) {
                        if (count >= 10) {
                            System.out.println("... (처음 10행만 표시, 총 " + results.size() + "행)");
                            break;
                        }
                        
                        // 각 컬럼 값을 탭으로 구분해서 출력
                        List<String> values = new ArrayList<>();
                        for (Object value : row.values()) {
                            values.add(value != null ? value.toString() : "NULL");
                        }
                        System.out.println(String.join("\t", values));
                        count++;
                    }
                    System.out.println("\n총 " + results.size() + "행이 조회되었습니다.");
                }
            }
            
        } catch (Exception e) {
            System.err.println("오류 발생: " + e.getMessage());
            e.printStackTrace();
        }
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
        // TNS_ADMIN 환경변수 설정
        String oracleHome = System.getenv("ORACLE_HOME");
        if (oracleHome != null) {
            String tnsAdmin = oracleHome + "/network/admin";
            System.setProperty("oracle.net.tns_admin", tnsAdmin);
            System.setProperty("TNS_ADMIN", tnsAdmin);  // 추가 설정
            System.out.println("TNS_ADMIN 설정: " + tnsAdmin);
            
            // tnsnames.ora 파일 존재 확인
            File tnsnamesFile = new File(tnsAdmin + "/tnsnames.ora");
            if (tnsnamesFile.exists()) {
                System.out.println("tnsnames.ora 파일 확인됨: " + tnsnamesFile.getAbsolutePath());
            } else {
                System.out.println("경고: tnsnames.ora 파일을 찾을 수 없습니다: " + tnsnamesFile.getAbsolutePath());
            }
        } else {
            System.out.println("경고: ORACLE_HOME 환경변수가 설정되지 않았습니다.");
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
     * MyBatis 설정 XML 생성 (Oracle 환경변수 사용)
     */
    private String createMyBatisConfig(String xmlFilePath) {
        // Oracle 환경변수에서 연결 정보 구성
        String connectString = System.getenv("ORACLE_SVC_CONNECT_STRING");
        String username = System.getenv("ORACLE_SVC_USER");
        String password = System.getenv("ORACLE_SVC_PASSWORD");
        
        if (username == null || password == null) {
            throw new RuntimeException("Oracle 환경변수가 설정되지 않았습니다. 필요한 변수: ORACLE_SVC_USER, ORACLE_SVC_PASSWORD");
        }
        
        // tnsnames 방식으로 JDBC URL 구성 (TNS_ADMIN이 설정되어 있으므로 가능)
        String jdbcUrl = "jdbc:oracle:thin:@" + (connectString != null ? connectString : "orcl");
        
        System.out.println("Oracle 연결 정보:");
        System.out.println("  JDBC URL: " + jdbcUrl);
        System.out.println("  사용자: " + username);
        
        // 절대 경로로 변환
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
