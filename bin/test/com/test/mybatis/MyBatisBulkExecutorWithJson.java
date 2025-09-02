package com.test.mybatis;

import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.databind.JsonSerializer;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializerProvider;
import com.fasterxml.jackson.databind.module.SimpleModule;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.apache.ibatis.io.Resources;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.apache.ibatis.session.SqlSessionFactoryBuilder;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import java.io.*;
import java.math.BigDecimal;
import java.nio.file.*;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * MyBatis XML 파일들을 재귀적으로 검색하여 모든 SQL ID를 자동으로 테스트하는 프로그램 (개선된 버전)
 * 
 * 개선사항:
 * 1. 리소스 관리 개선 (try-with-resources, 명시적 임시 파일 삭제)
 * 2. JSON 라이브러리 사용 (Jackson)
 * 3. XML 파싱 개선 (DOM 파서 사용)
 * 4. 설정 파일 외부화
 */
public class MyBatisBulkExecutorWithJson {
    
    private static final String PARAMETERS_FILE = "parameters.properties";
    private static final String CONFIG_FILE = "mybatis-bulk-executor.properties";
    
    private Properties config;
    private Pattern sqlIdPattern;
    private Set<String> examplePatterns;
    private ObjectMapper objectMapper;
    
    public MyBatisBulkExecutorWithJson() {
        loadConfiguration();
        this.objectMapper = new ObjectMapper();
        
        // BigDecimal 정밀도 제어 설정
        SimpleModule module = new SimpleModule();
        module.addSerializer(BigDecimal.class, new JsonSerializer<BigDecimal>() {
            @Override
            public void serialize(BigDecimal value, JsonGenerator gen, SerializerProvider serializers) 
                    throws IOException {
                if (value != null) {
                    // stripTrailingZeros()로 불필요한 0 제거
                    gen.writeNumber(value.stripTrailingZeros());
                } else {
                    gen.writeNull();
                }
            }
        });
        this.objectMapper.registerModule(module);
    }
    
    private void loadConfiguration() {
        config = new Properties();
        try (InputStream is = getClass().getClassLoader().getResourceAsStream(CONFIG_FILE)) {
            if (is != null) {
                config.load(is);
            } else {
                // 파일이 없으면 현재 디렉토리에서 로드 시도
                try (FileInputStream fis = new FileInputStream(CONFIG_FILE)) {
                    config.load(fis);
                }
            }
            System.out.println("설정 파일 로드 완료: " + CONFIG_FILE);
        } catch (IOException e) {
            System.out.println("설정 파일을 찾을 수 없습니다: " + CONFIG_FILE);
            System.out.println("기본 설정으로 실행합니다.");
            loadDefaultConfiguration();
        }
        
        // 패턴 초기화
        String patternStr = config.getProperty("sql.pattern.regex", "<(select|insert|update|delete)\\s+id=\"([^\"]+)\"");
        sqlIdPattern = Pattern.compile(patternStr);
        
        String examplePatternsStr = config.getProperty("example.patterns", "byexample,example,selectByExample,selectByExampleWithRowbounds");
        examplePatterns = new HashSet<>(Arrays.asList(examplePatternsStr.split(",")));
    }
    
    private void loadDefaultConfiguration() {
        // 기본 설정값들
        config.setProperty("temp.config.prefix", "mybatis-config-");
        config.setProperty("temp.mapper.prefix", "mapper-");
        config.setProperty("temp.file.suffix", ".xml");
        config.setProperty("sql.pattern.regex", "<(select|insert|update|delete)\\s+id=\"([^\"]+)\"");
        config.setProperty("example.patterns", "byexample,example,selectByExample,selectByExampleWithRowbounds");
        config.setProperty("mybatis.mapUnderscoreToCamelCase", "true");
        config.setProperty("mybatis.transactionManager", "JDBC");
        config.setProperty("mybatis.dataSource", "POOLED");
        config.setProperty("output.json.prefix", "bulk_test_result_");
        config.setProperty("output.json.suffix", ".json");
        config.setProperty("output.timestamp.format", "yyyyMMdd_HHmmss");
        config.setProperty("output.datetime.format", "yyyy-MM-dd HH:mm:ss");
        config.setProperty("db.oracle.driver", "oracle.jdbc.driver.OracleDriver");
        config.setProperty("db.mysql.driver", "com.mysql.cj.jdbc.Driver");
        config.setProperty("db.postgresql.driver", "org.postgresql.Driver");
        config.setProperty("mysql.default.options", "useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC");
        config.setProperty("oracle.default.service", "orcl");
        config.setProperty("mysql.default.host", "localhost");
        config.setProperty("mysql.default.port", "3306");
        config.setProperty("mysql.default.database", "test");
        config.setProperty("postgresql.default.host", "localhost");
        config.setProperty("postgresql.default.port", "5432");
        config.setProperty("postgresql.default.database", "postgres");
    }
    
    public static void main(String[] args) {
        if (args.length < 1) {
            printUsage();
            return;
        }
        
        String inputPath = args[0];
        String dbType = null;
        boolean selectOnly = true;
        boolean summaryOnly = false;
        boolean verbose = false;
        boolean generateJson = false;
        String customJsonFileName = null;
        String includePattern = null;
        boolean enableCompare = false;
        boolean showData = false;
        
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
                case "--include":
                    if (i + 1 < args.length) {
                        includePattern = args[++i];
                    } else {
                        System.err.println("오류: --include 옵션에 포함할 폴더명 패턴을 지정해주세요.");
                        return;
                    }
                    break;
                case "--all":
                    selectOnly = false;
                    break;
                case "--summary":
                    summaryOnly = true;
                    break;
                case "--verbose":
                    verbose = true;
                    break;
                case "--json":
                    generateJson = true;
                    break;
                case "--json-file":
                    if (i + 1 < args.length) {
                        generateJson = true;
                        customJsonFileName = args[++i];
                    } else {
                        System.err.println("오류: --json-file 옵션에 파일명을 지정해주세요.");
                        return;
                    }
                    break;
                case "--compare":
                    enableCompare = true;
                    break;
                case "--show-data":
                    showData = true;
                    break;
            }
        }
        
        if (dbType == null) {
            System.err.println("오류: --db 옵션으로 데이터베이스 타입을 지정해주세요. (oracle, mysql, postgres)");
            return;
        }
        
        // 입력 경로가 파일인지 폴더인지 확인
        Path path = Paths.get(inputPath);
        if (!Files.exists(path)) {
            System.err.println("오류: 지정된 경로가 존재하지 않습니다: " + inputPath);
            return;
        }
        
        MyBatisBulkExecutorWithJson executor = new MyBatisBulkExecutorWithJson();
        executor.executeSqls(inputPath, dbType, selectOnly, summaryOnly, verbose, generateJson, customJsonFileName, includePattern, enableCompare, showData);
    }
    
    private static void printUsage() {
        System.out.println("사용법: java MyBatisBulkExecutorWithJson <경로> [옵션]");
        System.out.println("경로: MyBatis XML 파일이 있는 디렉토리 또는 개별 XML 파일");
        System.out.println("옵션:");
        System.out.println("  --db <type>     데이터베이스 타입 (oracle, mysql, postgres) - 필수");
        System.out.println("  --include <pattern>  지정된 패턴이 포함된 폴더만 탐색 (디렉토리 모드에서만)");
        System.out.println("  --select-only   SELECT 구문만 실행 (기본값)");
        System.out.println("  --all          모든 SQL 구문 실행 (INSERT/UPDATE/DELETE 포함)");
        System.out.println("  --summary      요약 정보만 출력");
        System.out.println("  --verbose      상세 정보 출력");
        System.out.println("  --show-data    SQL 결과 데이터 출력");
        System.out.println("  --json         JSON 결과 파일 생성 (자동 파일명)");
        System.out.println("  --json-file <filename>  JSON 결과 파일 생성 (파일명 지정)");
        System.out.println("  --compare      SQL 결과 비교 기능 활성화 (Oracle ↔ PostgreSQL/MySQL)");
        System.out.println();
        System.out.println("환경변수 설정:");
        System.out.println("  Oracle: ORACLE_SVC_CONNECT_STRING, ORACLE_SVC_USER, ORACLE_SVC_PASSWORD, ORACLE_HOME");
        System.out.println("  MySQL: MYSQL_HOST, MYSQL_TCP_PORT, MYSQL_DB, MYSQL_ADM_USER, MYSQL_PASSWORD");
        System.out.println("  PostgreSQL: PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD");
        System.out.println("  비교 기능: TARGET_DBMS_TYPE (mysql 또는 postgresql)");
        System.out.println();
        System.out.println("예시:");
        System.out.println("  # 디렉토리 모드");
        System.out.println("  java MyBatisBulkExecutorWithJson /path/to/mappers --db oracle --json");
        System.out.println("  java MyBatisBulkExecutorWithJson /path/to/mappers --db mysql --json-file my_result.json");
        System.out.println("  java MyBatisBulkExecutorWithJson /path/to/mappers --db postgres --include transform");
        System.out.println("  java MyBatisBulkExecutorWithJson /path/to/mappers --db oracle --compare");
        System.out.println();
        System.out.println("  # 파일 모드");
        System.out.println("  java MyBatisBulkExecutorWithJson /path/to/UserMapper.xml --db oracle --verbose");
        System.out.println("  java MyBatisBulkExecutorWithJson /path/to/OrderMapper.xml --db mysql --all");
    }
    
    public void executeSqls(String inputPath, String dbType, boolean selectOnly, boolean summaryOnly, boolean verbose, boolean generateJson, String customJsonFileName, String includePattern, boolean enableCompare, boolean showData) {
        SqlListRepository repository = null;
        
        try {
            System.out.println("=== MyBatis 대량 SQL 실행 테스트 (개선된 버전) ===");
            
            Path path = Paths.get(inputPath);
            boolean isFile = Files.isRegularFile(path);
            boolean isDirectory = Files.isDirectory(path);
            
            if (isFile) {
                System.out.println("입력 파일: " + inputPath);
                if (!inputPath.toLowerCase().endsWith(".xml")) {
                    System.err.println("경고: 입력 파일이 XML 파일이 아닙니다.");
                }
            } else if (isDirectory) {
                System.out.println("검색 디렉토리: " + inputPath);
            } else {
                System.err.println("오류: 지정된 경로가 파일도 디렉토리도 아닙니다: " + inputPath);
                return;
            }
            
            System.out.println("데이터베이스 타입: " + dbType.toUpperCase());
            System.out.println("실행 모드: " + (selectOnly ? "SELECT만" : "모든 SQL"));
            System.out.println("출력 모드: " + (summaryOnly ? "요약만" : verbose ? "상세" : "일반"));
            System.out.println("비교 기능: " + (enableCompare ? "활성화" : "비활성화"));
            
            if (isDirectory && includePattern != null) {
                System.out.println("폴더 필터: '" + includePattern + "' 포함된 폴더만");
            }
            if (generateJson) {
                System.out.println("JSON 출력: 활성화");
            }
            System.out.println();
            
            // 0. SqlListRepository 초기화 및 테이블 생성 (--compare 옵션이 있을 때만)
            if (enableCompare) {
                try {
                    repository = new SqlListRepository();
                    repository.ensureTargetTableExists();
                    System.out.println("SQL 비교 검증 시스템 초기화 완료");
                    System.out.println();
                } catch (Exception e) {
                    System.err.println("SQL 비교 검증 시스템 초기화 실패: " + e.getMessage());
                    System.out.println("검증 기능 없이 계속 진행합니다...");
                    repository = null;
                    System.out.println();
                }
            } else {
                System.out.println("비교 기능이 비활성화되어 있습니다. (--compare 옵션 없음)");
                System.out.println();
            }
            
            // 1. 파라미터 로드
            Properties parameters = loadParameters();
            
            // 2. XML 파일들과 SQL ID들 찾기
            List<SqlTestInfo> sqlTests;
            if (isFile) {
                sqlTests = findSqlTestsInFile(path, selectOnly);
                System.out.println("대상 XML 파일: 1개");
            } else {
                sqlTests = findAllSqlTests(path, selectOnly, includePattern);
                System.out.println("발견된 XML 파일 수: " + sqlTests.stream().map(t -> t.xmlFile).distinct().count());
            }
            
            System.out.println("실행할 SQL 수: " + sqlTests.size());
            System.out.println();
            
            // 2.1. SQL 정보를 DB에 저장 (--compare 옵션이 있고 repository가 있는 경우만)
            if (enableCompare && repository != null) {
                saveSqlInfoToRepository(sqlTests, repository, parameters, dbType);
            }
            
            // 3. 테스트 실행
            TestResults results = executeSqlTests(sqlTests, parameters, dbType, summaryOnly, verbose, enableCompare ? repository : null, showData);
            
            // 4. 결과 출력
            printResults(results, summaryOnly, verbose);
            
            // 5. JSON 파일 생성
            if (generateJson) {
                generateJsonReport(results, inputPath, dbType, customJsonFileName);
            }
            
            // 6. 결과 비교 및 통계 출력 (--compare 옵션이 있고 repository가 있는 경우만)
            if (enableCompare && repository != null) {
                performResultComparison(repository);
            }
            
        } catch (Exception e) {
            System.err.println("오류 발생: " + e.getMessage());
            e.printStackTrace();
        } finally {
            // 7. 리소스 정리
            if (repository != null) {
                try {
                    repository.close();
                } catch (Exception e) {
                    System.err.println("Repository 정리 중 오류: " + e.getMessage());
                }
            }
        }
    }
    
    // 개선된 JSON 생성 메서드 (Jackson 사용)
    private void generateJsonReport(TestResults results, String directoryPath, String dbType, String customJsonFileName) {
        try {
            String jsonFileName;
            
            if (customJsonFileName != null && !customJsonFileName.trim().isEmpty()) {
                // 사용자가 파일명을 지정한 경우
                jsonFileName = customJsonFileName.trim();
                
                // .json 확장자가 없으면 추가
                if (!jsonFileName.toLowerCase().endsWith(".json")) {
                    jsonFileName += ".json";
                }
                
                // 상대 경로인 경우 out 디렉토리에 생성
                if (!jsonFileName.contains("/") && !jsonFileName.contains("\\")) {
                    // out 디렉토리 생성
                    File outDir = new File("out");
                    if (!outDir.exists()) {
                        outDir.mkdirs();
                        System.out.println("📁 출력 디렉토리 생성: " + outDir.getAbsolutePath());
                    }
                    jsonFileName = "out/" + jsonFileName;
                }
            } else {
                // 기존 자동 파일명 생성 로직
                File outDir = new File("out");
                if (!outDir.exists()) {
                    outDir.mkdirs();
                    System.out.println("📁 출력 디렉토리 생성: " + outDir.getAbsolutePath());
                }
                
                String timestampFormat = config.getProperty("output.timestamp.format", "yyyyMMdd_HHmmss");
                String jsonPrefix = config.getProperty("output.json.prefix", "bulk_test_result_");
                String jsonSuffix = config.getProperty("output.json.suffix", ".json");
                
                String timestamp = new SimpleDateFormat(timestampFormat).format(new Date());
                jsonFileName = "out/" + jsonPrefix + timestamp + jsonSuffix;
            }
            
            String datetimeFormat = config.getProperty("output.datetime.format", "yyyy-MM-dd HH:mm:ss");
            
            // Jackson을 사용한 JSON 생성
            ObjectNode rootNode = objectMapper.createObjectNode();
            
            // 테스트 정보
            ObjectNode testInfo = objectMapper.createObjectNode();
            testInfo.put("timestamp", new SimpleDateFormat(datetimeFormat).format(new Date()));
            testInfo.put("directory", directoryPath);
            testInfo.put("databaseType", dbType.toUpperCase());
            testInfo.put("totalTests", results.totalTests);
            testInfo.put("successCount", results.successCount);
            testInfo.put("failureCount", results.failureCount);
            testInfo.put("successRate", String.format("%.1f", results.getSuccessRate()));
            rootNode.set("testInfo", testInfo);
            
            // 성공한 테스트들
            ArrayNode successfulTests = objectMapper.createArrayNode();
            for (TestResult result : results.allResults) {
                if (result.success) {
                    ObjectNode testNode = objectMapper.createObjectNode();
                    testNode.put("xmlFile", result.testInfo.xmlFile.getFileName().toString());
                    testNode.put("sqlId", result.testInfo.sqlId);
                    testNode.put("sqlType", result.testInfo.sqlType);
                    testNode.put("rowCount", result.rowCount);
                    
                    // 결과 데이터가 있는 경우 JSON에 포함
                    if (result.resultData != null) {
                        ObjectNode resultDataNode = objectMapper.createObjectNode();
                        resultDataNode.put("count", result.resultData.size());
                        
                        ArrayNode dataArray = objectMapper.createArrayNode();
                        for (Map<String, Object> row : result.resultData) {
                            ObjectNode rowNode = objectMapper.valueToTree(row);
                            dataArray.add(rowNode);
                        }
                        resultDataNode.set("data", dataArray);
                        testNode.set("resultData", resultDataNode);
                    }
                    
                    successfulTests.add(testNode);
                }
            }
            rootNode.set("successfulTests", successfulTests);
            
            // 실패한 테스트들
            ArrayNode failedTests = objectMapper.createArrayNode();
            for (TestResult result : results.failures) {
                ObjectNode testNode = objectMapper.createObjectNode();
                testNode.put("xmlFile", result.testInfo.xmlFile.getFileName().toString());
                testNode.put("sqlId", result.testInfo.sqlId);
                testNode.put("sqlType", result.testInfo.sqlType);
                testNode.put("errorMessage", result.errorMessage != null ? result.errorMessage : "");
                
                // 실패한 경우에도 결과 데이터가 있으면 JSON에 포함 (에러 정보 등)
                if (result.resultData != null) {
                    ObjectNode resultDataNode = objectMapper.createObjectNode();
                    resultDataNode.put("count", result.resultData.size());
                    
                    ArrayNode dataArray = objectMapper.createArrayNode();
                    for (Map<String, Object> row : result.resultData) {
                        ObjectNode rowNode = objectMapper.valueToTree(row);
                        dataArray.add(rowNode);
                    }
                    resultDataNode.set("data", dataArray);
                    testNode.set("resultData", resultDataNode);
                }
                
                failedTests.add(testNode);
            }
            rootNode.set("failedTests", failedTests);
            
            // 파일별 통계
            ArrayNode fileStatistics = objectMapper.createArrayNode();
            Map<String, FileStats> fileStatsMap = calculateFileStats(results);
            for (Map.Entry<String, FileStats> entry : fileStatsMap.entrySet()) {
                ObjectNode statsNode = objectMapper.createObjectNode();
                FileStats stats = entry.getValue();
                statsNode.put("fileName", entry.getKey());
                statsNode.put("totalTests", stats.total);
                statsNode.put("successCount", stats.success);
                statsNode.put("failureCount", stats.failure);
                statsNode.put("successRate", String.format("%.1f", stats.getSuccessRate()));
                fileStatistics.add(statsNode);
            }
            rootNode.set("fileStatistics", fileStatistics);
            
            // JSON 파일 저장
            try (FileWriter writer = new FileWriter(jsonFileName)) {
                objectMapper.writerWithDefaultPrettyPrinter().writeValue(writer, rootNode);
            }
            
            System.out.println("\n📄 JSON 결과 파일 생성: " + jsonFileName);
            
        } catch (Exception e) {
            System.err.println("JSON 파일 생성 중 오류: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private Properties loadParameters() {
        Properties props = new Properties();
        File paramFile = new File(PARAMETERS_FILE);
        
        if (paramFile.exists()) {
            try (FileInputStream fis = new FileInputStream(PARAMETERS_FILE)) {
                props.load(fis);
                System.out.println("파라미터 파일 로드 완료: " + PARAMETERS_FILE);
            } catch (IOException e) {
                System.err.println("파라미터 파일 로드 실패: " + e.getMessage());
                System.out.println("지능형 바인드 변수 생성기를 실행합니다...");
                generateParametersWithBindVariableGenerator();
                return loadParameters(); // 재귀 호출로 생성된 파일 로드
            }
        } else {
            System.out.println("파라미터 파일을 찾을 수 없습니다: " + PARAMETERS_FILE);
            System.out.println("지능형 바인드 변수 생성기를 실행합니다...");
            generateParametersWithBindVariableGenerator();
            return loadParameters(); // 재귀 호출로 생성된 파일 로드
        }
        return props;
    }
    
    /**
     * 기본 파라미터 파일 생성 (파라미터 파일이 없을 때)
     */
    private void generateParametersWithBindVariableGenerator() {
        System.out.println("\n=== 기본 파라미터 파일 생성 ===");
        System.out.println("parameters.properties 파일이 없어서 기본 파라미터를 생성합니다.");
        System.out.println("더 정확한 파라미터가 필요하면 ./run_bind_generator.sh를 실행하세요.");
        createBasicParametersFile();
    }
    
    /**
     * 기본 파라미터 파일 생성 (fallback)
     */
    private void createBasicParametersFile() {
        try {
            System.out.println("기본 파라미터 파일을 생성합니다...");
            
            Properties defaultProps = new Properties();
            
            // ID 관련 파라미터들 (숫자형)
            defaultProps.setProperty("userId", "1");
            defaultProps.setProperty("productId", "1");
            defaultProps.setProperty("orderId", "1");
            defaultProps.setProperty("customerId", "1");
            defaultProps.setProperty("categoryId", "1");
            defaultProps.setProperty("warehouseId", "1");
            defaultProps.setProperty("sellerId", "1");
            defaultProps.setProperty("paymentId", "1");
            defaultProps.setProperty("shippingId", "1");
            defaultProps.setProperty("id", "1");
            defaultProps.setProperty("itemId", "1");
            defaultProps.setProperty("brandId", "1");
            
            // 상태 관련 파라미터들
            defaultProps.setProperty("status", "ACTIVE");
            defaultProps.setProperty("orderStatus", "COMPLETED");
            defaultProps.setProperty("paymentStatus", "PAID");
            defaultProps.setProperty("grade", "VIP");
            defaultProps.setProperty("country", "USA");
            defaultProps.setProperty("keyword", "TEST");
            defaultProps.setProperty("type", "NORMAL");
            
            // 날짜 관련 파라미터들
            defaultProps.setProperty("startDate", "2025-01-01");
            defaultProps.setProperty("endDate", "2025-12-31");
            defaultProps.setProperty("year", "2025");
            defaultProps.setProperty("month", "1");
            defaultProps.setProperty("day", "1");
            defaultProps.setProperty("createdDate", "2025-01-01");
            defaultProps.setProperty("updatedDate", "2025-01-01");
            
            // 숫자 관련 파라미터들
            defaultProps.setProperty("amount", "1000");
            defaultProps.setProperty("price", "100");
            defaultProps.setProperty("quantity", "1");
            defaultProps.setProperty("limit", "10");
            defaultProps.setProperty("offset", "0");
            defaultProps.setProperty("days", "30");
            defaultProps.setProperty("count", "1");
            defaultProps.setProperty("size", "10");
            defaultProps.setProperty("page", "1");
            
            // 문자열 관련 파라미터들
            defaultProps.setProperty("email", "test@example.com");
            defaultProps.setProperty("phone", "010-1234-5678");
            defaultProps.setProperty("name", "TestUser");
            defaultProps.setProperty("userName", "TestUser");
            defaultProps.setProperty("productName", "TestProduct");
            defaultProps.setProperty("categoryName", "TestCategory");
            defaultProps.setProperty("description", "Test Description");
            
            // 기타 자주 사용되는 파라미터들
            defaultProps.setProperty("enabled", "1");
            defaultProps.setProperty("active", "1");
            defaultProps.setProperty("deleted", "0");
            defaultProps.setProperty("version", "1");
            
            // 파일 저장
            try (FileOutputStream fos = new FileOutputStream(PARAMETERS_FILE)) {
                defaultProps.store(fos, "기본 파라미터 파일 (자동 생성) - null 값 방지를 위한 기본값들");
            }
            
            System.out.println("✅ 기본 파라미터 파일 생성 완료: " + PARAMETERS_FILE);
            System.out.println("   총 " + defaultProps.size() + "개의 기본 파라미터 설정됨");
            
        } catch (Exception e) {
            System.err.println("기본 파라미터 파일 생성 실패: " + e.getMessage());
        }
    }
    
    // 개선된 SQL 검색 메서드 (DOM 파서 사용)
    private List<SqlTestInfo> findAllSqlTests(Path directory, boolean selectOnly, String includePattern) throws IOException {
        List<SqlTestInfo> sqlTests = new ArrayList<>();
        
        Files.walk(directory)
            .filter(path -> path.toString().endsWith(".xml"))
            .filter(path -> {
                // includePattern이 지정된 경우, 경로에 해당 패턴이 포함된 것만 필터링
                if (includePattern != null && !includePattern.trim().isEmpty()) {
                    return path.toString().toLowerCase().contains(includePattern.toLowerCase());
                }
                return true;
            })
            .filter(this::isMyBatisXmlFile)  // MyBatis XML 파일만 필터링
            .forEach(xmlFile -> {
                try {
                    // DOM 파서를 사용한 XML 파싱
                    DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
                    // DTD 검증 비활성화
                    factory.setValidating(false);
                    factory.setNamespaceAware(false);
                    factory.setFeature("http://xml.org/sax/features/namespaces", false);
                    factory.setFeature("http://xml.org/sax/features/validation", false);
                    factory.setFeature("http://apache.org/xml/features/nonvalidating/load-dtd-grammar", false);
                    factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
                    
                    DocumentBuilder builder = factory.newDocumentBuilder();
                    Document doc = builder.parse(xmlFile.toFile());
                    
                    // SQL 요소들 찾기
                    String[] sqlTypes = {"select", "insert", "update", "delete"};
                    for (String sqlType : sqlTypes) {
                        if (selectOnly && !sqlType.equals("select")) {
                            continue;
                        }
                        
                        NodeList nodes = doc.getElementsByTagName(sqlType);
                        for (int i = 0; i < nodes.getLength(); i++) {
                            Element element = (Element) nodes.item(i);
                            String sqlId = element.getAttribute("id");
                            
                            if (sqlId != null && !sqlId.isEmpty()) {
                                SqlTestInfo testInfo = new SqlTestInfo();
                                testInfo.xmlFile = xmlFile;
                                testInfo.sqlId = sqlId;
                                testInfo.sqlType = sqlType.toUpperCase();
                                sqlTests.add(testInfo);
                            }
                        }
                    }
                } catch (Exception e) {
                    // DOM 파싱 실패 시 정규식으로 fallback
                    System.out.println("DOM 파싱 실패, 정규식으로 fallback: " + xmlFile.getFileName());
                    try {
                        String content = Files.readString(xmlFile);
                        Matcher matcher = sqlIdPattern.matcher(content);
                        
                        while (matcher.find()) {
                            String sqlType = matcher.group(1).toUpperCase();
                            String sqlId = matcher.group(2);
                            
                            if (selectOnly && !sqlType.equals("SELECT")) {
                                continue;
                            }
                            
                            SqlTestInfo testInfo = new SqlTestInfo();
                            testInfo.xmlFile = xmlFile;
                            testInfo.sqlId = sqlId;
                            testInfo.sqlType = sqlType;
                            sqlTests.add(testInfo);
                        }
                    } catch (IOException ioException) {
                        System.err.println("XML 파일 읽기 오류: " + xmlFile + " - " + ioException.getMessage());
                    }
                }
            });
        
        return sqlTests;
    }
    
    // 단일 파일에서 SQL 테스트 정보를 찾는 메서드
    private List<SqlTestInfo> findSqlTestsInFile(Path xmlFile, boolean selectOnly) {
        List<SqlTestInfo> sqlTests = new ArrayList<>();
        
        if (!isMyBatisXmlFile(xmlFile)) {
            System.out.println("경고: MyBatis XML 파일이 아닙니다: " + xmlFile.getFileName());
            return sqlTests;
        }
        
        try {
            // DOM 파서를 사용한 XML 파싱
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            // DTD 검증 비활성화
            factory.setValidating(false);
            factory.setNamespaceAware(false);
            factory.setFeature("http://xml.org/sax/features/namespaces", false);
            factory.setFeature("http://xml.org/sax/features/validation", false);
            factory.setFeature("http://apache.org/xml/features/nonvalidating/load-dtd-grammar", false);
            factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
            
            DocumentBuilder builder = factory.newDocumentBuilder();
            Document doc = builder.parse(xmlFile.toFile());
            
            // SQL 요소들 찾기
            String[] sqlTypes = {"select", "insert", "update", "delete"};
            for (String sqlType : sqlTypes) {
                if (selectOnly && !sqlType.equals("select")) {
                    continue;
                }
                
                NodeList nodes = doc.getElementsByTagName(sqlType);
                for (int i = 0; i < nodes.getLength(); i++) {
                    Element element = (Element) nodes.item(i);
                    String sqlId = element.getAttribute("id");
                    
                    if (sqlId != null && !sqlId.isEmpty()) {
                        SqlTestInfo testInfo = new SqlTestInfo();
                        testInfo.xmlFile = xmlFile;
                        testInfo.sqlId = sqlId;
                        testInfo.sqlType = sqlType.toUpperCase();
                        sqlTests.add(testInfo);
                    }
                }
            }
        } catch (Exception e) {
            // DOM 파싱 실패 시 정규식으로 fallback
            System.out.println("DOM 파싱 실패, 정규식으로 fallback: " + xmlFile.getFileName());
            try {
                String content = Files.readString(xmlFile);
                Matcher matcher = sqlIdPattern.matcher(content);
                
                while (matcher.find()) {
                    String sqlType = matcher.group(1).toUpperCase();
                    String sqlId = matcher.group(2);
                    
                    if (selectOnly && !sqlType.equals("SELECT")) {
                        continue;
                    }
                    
                    SqlTestInfo testInfo = new SqlTestInfo();
                    testInfo.xmlFile = xmlFile;
                    testInfo.sqlId = sqlId;
                    testInfo.sqlType = sqlType;
                    sqlTests.add(testInfo);
                }
            } catch (IOException ioException) {
                System.err.println("XML 파일 읽기 오류: " + xmlFile + " - " + ioException.getMessage());
            }
        }
        
        return sqlTests;
    }
    
    private TestResults executeSqlTests(List<SqlTestInfo> sqlTests, Properties parameters, String dbType, boolean summaryOnly, boolean verbose, SqlListRepository repository, boolean showData) {
        TestResults results = new TestResults();
        
        System.out.println("=== SQL 실행 테스트 시작 ===");
        System.out.println();
        
        for (int i = 0; i < sqlTests.size(); i++) {
            SqlTestInfo testInfo = sqlTests.get(i);
            TestResult result = new TestResult();
            result.testInfo = testInfo;
            
            // 진행률 표시 (summary 모드가 아닐 때)
            if (!summaryOnly) {
                double progress = ((double)(i + 1) / sqlTests.size()) * 100;
                System.out.printf("\r진행률: %.1f%% [%d/%d] %s:%s", 
                    progress, i + 1, sqlTests.size(), 
                    testInfo.xmlFile.getFileName(), testInfo.sqlId);
                System.out.flush();
            }
            
            // Example 패턴 SQL 스킵 (설정 파일에서 읽은 패턴 사용)
            String sqlIdLower = testInfo.sqlId.toLowerCase();
            boolean isExamplePattern = examplePatterns.stream()
                .anyMatch(pattern -> sqlIdLower.contains(pattern.toLowerCase()));
            
            if (isExamplePattern) {
                result.success = true;
                result.rowCount = -1; // 스킵 표시용
                
                // Example 패턴도 스킵 정보를 저장 (비교 통계에 포함되도록)
                if (repository != null) {
                    try {
                        Map<String, Object> paramMap = new HashMap<>();
                        for (String key : parameters.stringPropertyNames()) {
                            String value = parameters.getProperty(key);
                            paramMap.put(key, cleanParameterValue(value));
                        }
                        
                        // 스킵된 결과 생성
                        List<Map<String, Object>> skippedResults = new ArrayList<>();
                        Map<String, Object> skipResult = new HashMap<>();
                        skipResult.put("status", "SKIPPED");
                        skipResult.put("reason", "Example pattern");
                        skipResult.put("pattern_matched", true);
                        skippedResults.add(skipResult);
                        
                        // 매퍼명.sql_id 형태로 생성
                        String mapperName = extractMapperName(testInfo.xmlFile);
                        String fullSqlId = mapperName + "." + testInfo.sqlId;
                        
                        if ("oracle".equalsIgnoreCase(dbType)) {
                            repository.saveSourceResult(fullSqlId, skippedResults, paramMap);
                        } else {
                            repository.saveTargetResult(fullSqlId, skippedResults, paramMap);
                        }
                    } catch (Exception repoException) {
                        System.err.println("스킵 결과 저장 실패 (" + testInfo.sqlId + "): " + repoException.getMessage());
                    }
                }
                
                if (verbose) {
                    System.out.printf(" ⏭️  Example 패턴 스킵 (ID: %s)%n", testInfo.sqlId);
                }
            } else {
                // SQL 실행 및 결과 저장
                List<Map<String, Object>> sqlResults = null;
                try {
                    sqlResults = executeSingleSqlWithResults(testInfo, parameters, dbType, verbose);
                    result.rowCount = sqlResults.size();
                    result.success = true;
                    
                    // showData가 활성화된 경우 결과 데이터 저장
                    if (showData && sqlResults != null) {
                        result.resultData = new ArrayList<>(sqlResults);
                    }
                    
                    if (verbose) {
                        System.out.printf(" ✅ %d행%n", result.rowCount);
                    }
                    
                    // 데이터 출력 옵션
                    if (showData && sqlResults != null && !sqlResults.isEmpty()) {
                        System.out.println("    📊 결과 데이터:");
                        for (int idx = 0; idx < Math.min(sqlResults.size(), 5); idx++) {
                            System.out.println("      " + (idx + 1) + ": " + sqlResults.get(idx));
                        }
                        if (sqlResults.size() > 5) {
                            System.out.println("      ... (총 " + sqlResults.size() + "건, 처음 5건만 표시)");
                        }
                    }
                } catch (Exception sqlException) {
                    result.success = false;
                    result.errorMessage = sqlException.getMessage();
                    
                    // 실패한 경우에도 빈 결과로 저장 (비교 통계에 포함되도록)
                    sqlResults = new ArrayList<>();
                    Map<String, Object> errorResult = new HashMap<>();
                    errorResult.put("error", "SQL 실행 실패");
                    errorResult.put("message", sqlException.getMessage());
                    sqlResults.add(errorResult);
                    
                    // showData가 활성화된 경우 에러 결과도 저장
                    if (showData) {
                        result.resultData = new ArrayList<>(sqlResults);
                    }
                    
                    if (!summaryOnly) {
                        System.out.printf(" ❌ 실패: %s%n", sqlException.getMessage());
                    }
                }
                
                // Repository에 실행 결과 저장 (성공/실패 관계없이 저장)
                if (repository != null && sqlResults != null) {
                    try {
                        Map<String, Object> paramMap = new HashMap<>();
                        for (String key : parameters.stringPropertyNames()) {
                            String value = parameters.getProperty(key);
                            // MyBatis 바인드 변수용으로 따옴표 제거
                            paramMap.put(key, cleanParameterValue(value));
                        }
                        
                        // 매퍼명.sql_id 형태로 생성
                        String mapperName = extractMapperName(testInfo.xmlFile);
                        String fullSqlId = mapperName + "." + testInfo.sqlId;
                        
                        if ("oracle".equalsIgnoreCase(dbType)) {
                            repository.saveSourceResult(fullSqlId, sqlResults, paramMap);
                        } else {
                            repository.saveTargetResult(fullSqlId, sqlResults, paramMap);
                        }
                    } catch (Exception repoException) {
                        System.err.println("결과 저장 실패 (" + testInfo.sqlId + "): " + repoException.getMessage());
                    }
                }
            }
            
            results.addResult(result);
        }
        
        // 마지막에 줄바꿈
        if (!summaryOnly) {
            System.out.println();
        }
        
        return results;
    }
    
    // 개선된 단일 SQL 실행 메서드 (리소스 관리 개선)
    private int executeSingleSql(SqlTestInfo testInfo, Properties parameters, String dbType, boolean verbose) throws Exception {
        File tempConfigFile = null;
        File tempMapperFile = null;
        
        try {
            // 임시 설정 파일 생성
            String configPrefix = config.getProperty("temp.config.prefix", "mybatis-config-");
            String mapperPrefix = config.getProperty("temp.mapper.prefix", "mapper-");
            String fileSuffix = config.getProperty("temp.file.suffix", ".xml");
            
            tempConfigFile = File.createTempFile(configPrefix, fileSuffix);
            tempMapperFile = File.createTempFile(mapperPrefix, fileSuffix);
            
            // 임시 매퍼 파일 생성 (아카이브 버전의 정규식 방식 사용)
            String modifiedMapperContent = modifyMapperContentWithRegex(testInfo.xmlFile);
            try (FileWriter writer = new FileWriter(tempMapperFile)) {
                writer.write(modifiedMapperContent);
            }
            
            // MyBatis 설정 파일 생성
            String configContent = createMyBatisConfig(tempMapperFile.getAbsolutePath(), dbType);
            try (FileWriter writer = new FileWriter(tempConfigFile)) {
                writer.write(configContent);
            }
            
            // MyBatis 실행
            try (InputStream inputStream = new FileInputStream(tempConfigFile)) {
                SqlSessionFactory sqlSessionFactory = new SqlSessionFactoryBuilder().build(inputStream);
                
                try (SqlSession session = sqlSessionFactory.openSession(false)) { // autoCommit = false로 설정
                    Map<String, Object> paramMap = new HashMap<>();
                    for (String key : parameters.stringPropertyNames()) {
                        String value = parameters.getProperty(key);
                        // MyBatis 바인드 변수용으로 따옴표 제거
                        paramMap.put(key, cleanParameterValue(value));
                    }
                    
                    int resultCount = 0;
                    
                    try {
                        // SQL 타입에 따라 다른 실행 방법 사용
                        switch (testInfo.sqlType.toUpperCase()) {
                            case "SELECT":
                                List<Map<String, Object>> selectResults = session.selectList(testInfo.sqlId, paramMap);
                                resultCount = selectResults.size();
                                break;
                                
                            case "INSERT":
                                resultCount = session.insert(testInfo.sqlId, paramMap);
                                if (verbose) {
                                    System.out.printf(" 🔄 INSERT 실행 후 롤백 (%d행 영향)%n", resultCount);
                                }
                                break;
                                
                            case "UPDATE":
                                resultCount = session.update(testInfo.sqlId, paramMap);
                                if (verbose) {
                                    System.out.printf(" 🔄 UPDATE 실행 후 롤백 (%d행 영향)%n", resultCount);
                                }
                                break;
                                
                            case "DELETE":
                                resultCount = session.delete(testInfo.sqlId, paramMap);
                                if (verbose) {
                                    System.out.printf(" 🔄 DELETE 실행 후 롤백 (%d행 영향)%n", resultCount);
                                }
                                break;
                                
                            default:
                                // 기타 SQL (CALL 등)은 selectList로 처리
                                List<Map<String, Object>> otherResults = session.selectList(testInfo.sqlId, paramMap);
                                resultCount = otherResults.size();
                                break;
                        }
                        
                        // INSERT/UPDATE/DELETE의 경우 항상 롤백 (테스트 환경이므로)
                        if (!testInfo.sqlType.equalsIgnoreCase("SELECT")) {
                            session.rollback();
                            if (verbose) {
                                System.out.printf(" ✅ 트랜잭션 롤백 완료 (데이터 변경 취소)%n");
                            }
                        }
                        
                    } catch (Exception e) {
                        // 오류 발생 시에도 롤백
                        if (!testInfo.sqlType.equalsIgnoreCase("SELECT")) {
                            try {
                                session.rollback();
                                if (verbose) {
                                    System.out.printf(" 🔄 오류 발생으로 인한 롤백 완료%n");
                                }
                            } catch (Exception rollbackException) {
                                System.err.println("롤백 실패: " + rollbackException.getMessage());
                            }
                        }
                        throw e;
                    }
                    
                    return resultCount;
                }
            }
            
        } finally {
            // 명시적 임시 파일 삭제
            if (tempConfigFile != null && tempConfigFile.exists()) {
                if (!tempConfigFile.delete()) {
                    tempConfigFile.deleteOnExit(); // 삭제 실패 시 JVM 종료 시 삭제
                }
            }
            if (tempMapperFile != null && tempMapperFile.exists()) {
                if (!tempMapperFile.delete()) {
                    tempMapperFile.deleteOnExit(); // 삭제 실패 시 JVM 종료 시 삭제
                }
            }
        }
    }
    
    // 결과를 반환하는 단일 SQL 실행 메서드 (Repository 연동용)
    private List<Map<String, Object>> executeSingleSqlWithResults(SqlTestInfo testInfo, Properties parameters, String dbType, boolean verbose) throws Exception {
        File tempConfigFile = null;
        File tempMapperFile = null;
        
        try {
            // 임시 설정 파일 생성
            String configPrefix = config.getProperty("temp.config.prefix", "mybatis-config-");
            String mapperPrefix = config.getProperty("temp.mapper.prefix", "mapper-");
            String fileSuffix = config.getProperty("temp.file.suffix", ".xml");
            
            tempConfigFile = File.createTempFile(configPrefix, fileSuffix);
            tempMapperFile = File.createTempFile(mapperPrefix, fileSuffix);
            
            // 임시 매퍼 파일 생성 (아카이브 버전의 정규식 방식 사용)
            String modifiedMapperContent = modifyMapperContentWithRegex(testInfo.xmlFile);
            try (FileWriter writer = new FileWriter(tempMapperFile)) {
                writer.write(modifiedMapperContent);
            }
            
            // MyBatis 설정 파일 생성
            String configContent = createMyBatisConfig(tempMapperFile.getAbsolutePath(), dbType);
            try (FileWriter writer = new FileWriter(tempConfigFile)) {
                writer.write(configContent);
            }
            
            // MyBatis 실행
            try (InputStream inputStream = new FileInputStream(tempConfigFile)) {
                SqlSessionFactory sqlSessionFactory = new SqlSessionFactoryBuilder().build(inputStream);
                
                try (SqlSession session = sqlSessionFactory.openSession(false)) { // autoCommit = false로 설정
                    Map<String, Object> paramMap = new HashMap<>();
                    for (String key : parameters.stringPropertyNames()) {
                        String value = parameters.getProperty(key);
                        // MyBatis 바인드 변수용으로 따옴표 제거
                        paramMap.put(key, cleanParameterValue(value));
                    }
                    
                    List<Map<String, Object>> results = new ArrayList<>();
                    
                    try {
                        // SQL 타입에 따라 다른 실행 방법 사용
                        switch (testInfo.sqlType.toUpperCase()) {
                            case "SELECT":
                                results = session.selectList(testInfo.sqlId, paramMap);
                                break;
                                
                            case "INSERT":
                                int insertCount = session.insert(testInfo.sqlId, paramMap);
                                // INSERT 결과를 Map으로 변환하여 반환
                                Map<String, Object> insertResult = new HashMap<>();
                                insertResult.put("affected_rows", insertCount);
                                insertResult.put("operation", "INSERT");
                                results.add(insertResult);
                                if (verbose) {
                                    System.out.printf(" 🔄 INSERT 실행 후 롤백 (%d행 영향)%n", insertCount);
                                }
                                break;
                                
                            case "UPDATE":
                                int updateCount = session.update(testInfo.sqlId, paramMap);
                                // UPDATE 결과를 Map으로 변환하여 반환
                                Map<String, Object> updateResult = new HashMap<>();
                                updateResult.put("affected_rows", updateCount);
                                updateResult.put("operation", "UPDATE");
                                results.add(updateResult);
                                if (verbose) {
                                    System.out.printf(" 🔄 UPDATE 실행 후 롤백 (%d행 영향)%n", updateCount);
                                }
                                break;
                                
                            case "DELETE":
                                int deleteCount = session.delete(testInfo.sqlId, paramMap);
                                // DELETE 결과를 Map으로 변환하여 반환
                                Map<String, Object> deleteResult = new HashMap<>();
                                deleteResult.put("affected_rows", deleteCount);
                                deleteResult.put("operation", "DELETE");
                                results.add(deleteResult);
                                if (verbose) {
                                    System.out.printf(" 🔄 DELETE 실행 후 롤백 (%d행 영향)%n", deleteCount);
                                }
                                break;
                                
                            default:
                                // 기타 SQL (CALL 등)은 selectList로 처리
                                results = session.selectList(testInfo.sqlId, paramMap);
                                break;
                        }
                        
                        // INSERT/UPDATE/DELETE의 경우 항상 롤백 (테스트 환경이므로)
                        if (!testInfo.sqlType.equalsIgnoreCase("SELECT")) {
                            session.rollback();
                            if (verbose) {
                                System.out.printf(" ✅ 트랜잭션 롤백 완료 (데이터 변경 취소)%n");
                            }
                        }
                        
                    } catch (Exception e) {
                        // 오류 발생 시에도 롤백
                        if (!testInfo.sqlType.equalsIgnoreCase("SELECT")) {
                            try {
                                session.rollback();
                                if (verbose) {
                                    System.out.printf(" 🔄 오류 발생으로 인한 롤백 완료%n");
                                }
                            } catch (Exception rollbackException) {
                                System.err.println("롤백 실패: " + rollbackException.getMessage());
                            }
                        }
                        throw e;
                    }
                    
                    // 결과 정규화 - Oracle과 PostgreSQL 간 차이 제거
                    results = ResultNormalizer.normalizeResults(results);
                    
                    return results;
                }
            }
            
        } finally {
            // 명시적 임시 파일 삭제
            if (tempConfigFile != null && tempConfigFile.exists()) {
                if (!tempConfigFile.delete()) {
                    tempConfigFile.deleteOnExit(); // 삭제 실패 시 JVM 종료 시 삭제
                }
            }
            if (tempMapperFile != null && tempMapperFile.exists()) {
                if (!tempMapperFile.delete()) {
                    tempMapperFile.deleteOnExit(); // 삭제 실패 시 JVM 종료 시 삭제
                }
            }
        }
    }
    
    // 개선된 매퍼 파일 수정 메서드 (DOM 파서 사용)
    private String modifyMapperContentWithDOM(Path xmlFile) throws Exception {
        try {
            // 먼저 MyBatis XML 파일인지 확인
            if (!isMyBatisXmlFile(xmlFile)) {
                throw new Exception("Not a MyBatis XML file: " + xmlFile.getFileName());
            }
            
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            // DTD 검증 비활성화
            factory.setValidating(false);
            factory.setNamespaceAware(false);
            factory.setFeature("http://xml.org/sax/features/namespaces", false);
            factory.setFeature("http://xml.org/sax/features/validation", false);
            factory.setFeature("http://apache.org/xml/features/nonvalidating/load-dtd-grammar", false);
            factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
            
            DocumentBuilder builder = factory.newDocumentBuilder();
            Document doc = builder.parse(xmlFile.toFile());
            
            // resultMap 요소들 제거
            NodeList resultMaps = doc.getElementsByTagName("resultMap");
            for (int i = resultMaps.getLength() - 1; i >= 0; i--) {
                Element resultMap = (Element) resultMaps.item(i);
                resultMap.getParentNode().removeChild(resultMap);
            }
            
            // SQL 요소들의 속성 수정
            String[] sqlTypes = {"select", "insert", "update", "delete"};
            for (String sqlType : sqlTypes) {
                NodeList sqlNodes = doc.getElementsByTagName(sqlType);
                for (int i = 0; i < sqlNodes.getLength(); i++) {
                    Element sqlElement = (Element) sqlNodes.item(i);
                    
                    // resultMap 속성을 resultType="map"으로 변경
                    if (sqlElement.hasAttribute("resultMap")) {
                        sqlElement.removeAttribute("resultMap");
                        sqlElement.setAttribute("resultType", "map");
                    }
                    
                    // resultType을 map으로 변경 (기존에 있는 경우)
                    if (sqlElement.hasAttribute("resultType") && !sqlElement.getAttribute("resultType").equals("map")) {
                        sqlElement.setAttribute("resultType", "map");
                    }
                    
                    // parameterType을 map으로 변경
                    if (sqlElement.hasAttribute("parameterType")) {
                        sqlElement.setAttribute("parameterType", "map");
                    }
                    
                    // 불필요한 속성들 제거
                    sqlElement.removeAttribute("typeHandler");
                    sqlElement.removeAttribute("javaType");
                    sqlElement.removeAttribute("jdbcType");
                }
            }
            
            // 모든 요소에서 typeHandler 속성 제거 (parameter, result 등)
            removeTypeHandlerAttributes(doc.getDocumentElement());
            
            // DOM을 문자열로 변환하되, 올바른 DOCTYPE 포함
            TransformerFactory transformerFactory = TransformerFactory.newInstance();
            Transformer transformer = transformerFactory.newTransformer();
            transformer.setOutputProperty("omit-xml-declaration", "no");
            transformer.setOutputProperty("encoding", "UTF-8");
            transformer.setOutputProperty("indent", "yes");
            
            StringWriter writer = new StringWriter();
            transformer.transform(new DOMSource(doc), new StreamResult(writer));
            
            String result = writer.toString();
            
            // DOCTYPE 선언이 없거나 잘못된 경우 올바른 DOCTYPE으로 교체
            if (!result.contains("<!DOCTYPE mapper")) {
                // XML 선언 다음에 올바른 DOCTYPE 삽입
                String xmlDeclaration = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>";
                String doctypeDeclaration = "<!DOCTYPE mapper PUBLIC \"-//mybatis.org//DTD Mapper 3.0//EN\" \"http://mybatis.org/dtd/mybatis-3-mapper.dtd\">";
                
                if (result.startsWith("<?xml")) {
                    int endOfXmlDecl = result.indexOf("?>") + 2;
                    String beforeMapper = result.substring(0, endOfXmlDecl);
                    String afterXmlDecl = result.substring(endOfXmlDecl).trim();
                    result = beforeMapper + "\n" + doctypeDeclaration + "\n" + afterXmlDecl;
                } else {
                    result = xmlDeclaration + "\n" + doctypeDeclaration + "\n" + result;
                }
            }
            
            return result;
            
        } catch (Exception e) {
            // DOM 파싱 실패 시 기존 정규식 방식으로 fallback
            System.out.println("DOM 수정 실패, 정규식으로 fallback: " + xmlFile.getFileName());
            return modifyMapperContentWithRegex(xmlFile);
        }
    }
    
    // 기존 정규식 방식 (fallback용) - 아카이브 버전의 포괄적인 처리 방식 적용
    private String modifyMapperContentWithRegex(Path xmlFile) throws IOException {
        String content = Files.readString(xmlFile);
        
        // 1. resultMap 정의 전체 제거 (정규식으로 한번에 처리)
        content = content.replaceAll("(?s)<resultMap[^>]*>.*?</resultMap>", "");
        content = content.replaceAll("<resultMap[^>]*/\\s*>", "");
        
        // 2. resultMap 참조를 resultType="map"으로 변경 (속성에서)
        content = content.replaceAll("resultMap\\s*=\\s*\"[^\"]*\"", "resultType=\"map\"");
        
        // 3. 중첩된 resultMap 참조 제거 (파라미터 내부에서)
        content = content.replaceAll(",\\s*resultMap\\s*=\\s*[^}]+", "");
        
        // 4. resultType을 map으로 변경
        content = content.replaceAll("resultType\\s*=\\s*\"(?!map\")[^\"]*\"", "resultType=\"map\"");
        
        // 5. parameterType을 map으로 변경
        content = content.replaceAll("parameterType\\s*=\\s*\"[^\"]*\"", "parameterType=\"map\"");
        
        // 6. typeHandler 속성 제거 (따옴표 있음)
        content = content.replaceAll("\\s+typeHandler\\s*=\\s*\"[^\"]*\"", "");
        
        // 7. typeHandler 속성 제거 (따옴표 없음, 파라미터 내부)
        content = content.replaceAll(",\\s*typeHandler\\s*=\\s*[^,}\\s]+", "");
        content = content.replaceAll("\\s+typeHandler\\s*=\\s*[^,}\\s]+", "");
        
        // 8. javaType 속성 제거
        content = content.replaceAll("\\s+javaType\\s*=\\s*\"[^\"]*\"", "");
        content = content.replaceAll(",\\s*javaType\\s*=\\s*[^,}]+", "");
        
        // 9. jdbcType 속성 제거
        content = content.replaceAll("\\s+jdbcType\\s*=\\s*\"[^\"]*\"", "");
        content = content.replaceAll(",\\s*jdbcType\\s*=\\s*[^,}]+", "");
        
        // 10. mode=OUT 파라미터 단순화 (CURSOR 타입 제거)
        content = content.replaceAll("mode\\s*=\\s*OUT\\s*,\\s*jdbcType\\s*=\\s*CURSOR[^}]*", "mode=OUT");
        
        // DOCTYPE 선언 확인 및 수정
        if (!content.contains("<!DOCTYPE mapper")) {
            String xmlDeclaration = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>";
            String doctypeDeclaration = "<!DOCTYPE mapper PUBLIC \"-//mybatis.org//DTD Mapper 3.0//EN\" \"http://mybatis.org/dtd/mybatis-3-mapper.dtd\">";
            
            if (content.startsWith("<?xml")) {
                int endOfXmlDecl = content.indexOf("?>") + 2;
                String beforeMapper = content.substring(0, endOfXmlDecl);
                String afterXmlDecl = content.substring(endOfXmlDecl).trim();
                content = beforeMapper + "\n" + doctypeDeclaration + "\n" + afterXmlDecl;
            } else {
                content = xmlDeclaration + "\n" + doctypeDeclaration + "\n" + content;
            }
        } else {
            // 기존 DOCTYPE이 잘못된 경우 교체
            content = content.replaceAll("<!DOCTYPE\\s+mapper[^>]*>", 
                "<!DOCTYPE mapper PUBLIC \"-//mybatis.org//DTD Mapper 3.0//EN\" \"http://mybatis.org/dtd/mybatis-3-mapper.dtd\">");
        }
        
        return content;
    }
    
    // 모든 요소에서 typeHandler 관련 속성을 재귀적으로 제거하는 메서드
    private void removeTypeHandlerAttributes(Element element) {
        // 현재 요소에서 typeHandler 관련 속성 제거
        element.removeAttribute("typeHandler");
        element.removeAttribute("javaType");
        element.removeAttribute("jdbcType");
        
        // 자식 요소들에 대해 재귀적으로 처리
        NodeList children = element.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            Node child = children.item(i);
            if (child.getNodeType() == Node.ELEMENT_NODE) {
                removeTypeHandlerAttributes((Element) child);
            }
        }
    }
    
    // MyBatis XML 파일인지 확인하는 메서드
    private boolean isMyBatisXmlFile(Path xmlFile) {
        try {
            String content = Files.readString(xmlFile);
            
            // MyBatis XML 파일의 특징들을 확인
            boolean hasMapperTag = content.contains("<mapper") && content.contains("namespace=");
            boolean hasMyBatisDTD = content.contains("mybatis.org//DTD Mapper") || 
                                   content.contains("ibatis.apache.org//DTD Mapper");
            boolean hasSqlTags = content.contains("<select") || content.contains("<insert") || 
                                content.contains("<update") || content.contains("<delete");
            
            // 최소한 mapper 태그와 namespace가 있어야 함
            return hasMapperTag && (hasMyBatisDTD || hasSqlTags);
            
        } catch (Exception e) {
            System.out.println("XML 파일 검증 실패: " + xmlFile.getFileName() + " - " + e.getMessage());
            return false;
        }
    }
    
    private String createMyBatisConfig(String xmlFilePath, String dbType) {
        switch (dbType.toLowerCase()) {
            case "oracle":
                return createOracleConfig(xmlFilePath);
            case "mysql":
                return createMySQLConfig(xmlFilePath);
            case "postgres":
            case "postgresql":
            case "pg":
                return createPostgreSQLConfig(xmlFilePath);
            default:
                throw new RuntimeException("지원하지 않는 데이터베이스 타입: " + dbType + 
                    ". 지원되는 타입: oracle, mysql, postgres");
        }
    }
    
    private String createOracleConfig(String xmlFilePath) {
        String connectString = System.getenv("ORACLE_SVC_CONNECT_STRING");
        String username = System.getenv("ORACLE_SVC_USER");
        String password = System.getenv("ORACLE_SVC_PASSWORD");
        String host = System.getenv("ORACLE_HOST");
        String port = System.getenv("ORACLE_PORT");
        String sid = System.getenv("ORACLE_SID");
        String tnsAdmin = System.getenv("TNS_ADMIN");
        String oracleHome = System.getenv("ORACLE_HOME");
        
        if (username == null || password == null) {
            throw new RuntimeException("Oracle 환경변수가 설정되지 않았습니다. 필요한 변수: ORACLE_SVC_USER, ORACLE_SVC_PASSWORD");
        }
        
        // TNS_ADMIN 자동 설정 (개선된 로직)
        if (tnsAdmin == null && oracleHome != null) {
            tnsAdmin = oracleHome + "/network/admin";
            System.setProperty("oracle.net.tns_admin", tnsAdmin);
            System.out.println("TNS_ADMIN 자동 설정: " + tnsAdmin);
        }
        
        String jdbcUrl;
        
        // Oracle 12c 이후 PDB 환경 지원
        if (host != null && port != null && sid != null) {
            // Service Name 방식 (PDB 환경)
            jdbcUrl = "jdbc:oracle:thin:@//" + host + ":" + port + "/" + sid;
            System.out.println("Oracle PDB 연결 방식 사용: " + jdbcUrl);
        } else if (tnsAdmin != null && connectString != null) {
            // TNS 이름 사용
            jdbcUrl = "jdbc:oracle:thin:@" + connectString;
            System.out.println("Oracle TNS 연결 방식 사용: " + jdbcUrl);
        } else {
            // 기본 연결 방식 (fallback)
            String defaultService = config.getProperty("oracle.default.service", "orcl");
            jdbcUrl = "jdbc:oracle:thin:@" + (connectString != null ? connectString : defaultService);
            System.out.println("Oracle 기본 연결 방식 사용: " + jdbcUrl);
        }
        
        String driverClass = config.getProperty("db.oracle.driver", "oracle.jdbc.driver.OracleDriver");
        return createConfigXml(xmlFilePath, driverClass, jdbcUrl, username, password);
    }
    
    private String createMySQLConfig(String xmlFilePath) {
        String host = System.getenv("MYSQL_HOST");
        String port = System.getenv("MYSQL_TCP_PORT");
        String database = System.getenv("MYSQL_DB");
        String username = System.getenv("MYSQL_ADM_USER");
        String password = System.getenv("MYSQL_PASSWORD");
        
        if (username == null || password == null) {
            throw new RuntimeException("MySQL 환경변수가 설정되지 않았습니다. 필요한 변수: MYSQL_ADM_USER, MYSQL_PASSWORD");
        }
        
        // 기본값 설정 (설정 파일에서 읽기)
        if (host == null) host = config.getProperty("mysql.default.host", "localhost");
        if (port == null) port = config.getProperty("mysql.default.port", "3306");
        if (database == null) database = config.getProperty("mysql.default.database", "test");
        
        String options = config.getProperty("mysql.default.options", "useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC");
        
        // XML에서 & 문자를 &amp;로 인코딩
        String jdbcUrl = String.format("jdbc:mysql://%s:%s/%s?%s", 
            host, port, database, options.replace("&", "&amp;"));
        
        String driverClass = config.getProperty("db.mysql.driver", "com.mysql.cj.jdbc.Driver");
        return createConfigXml(xmlFilePath, driverClass, jdbcUrl, username, password);
    }
    
    private String createPostgreSQLConfig(String xmlFilePath) {
        String host = System.getenv("PGHOST");
        String port = System.getenv("PGPORT");
        String database = System.getenv("PGDATABASE");
        String username = System.getenv("PGUSER");
        String password = System.getenv("PGPASSWORD");
        
        if (username == null || password == null) {
            throw new RuntimeException("PostgreSQL 환경변수가 설정되지 않았습니다. 필요한 변수: PGUSER, PGPASSWORD");
        }
        
        // 기본값 설정 (설정 파일에서 읽기)
        if (host == null) host = config.getProperty("postgresql.default.host", "localhost");
        if (port == null) port = config.getProperty("postgresql.default.port", "5432");
        if (database == null) database = config.getProperty("postgresql.default.database", "postgres");
        
        String jdbcUrl = String.format("jdbc:postgresql://%s:%s/%s", host, port, database);
        
        String driverClass = config.getProperty("db.postgresql.driver", "org.postgresql.Driver");
        return createConfigXml(xmlFilePath, driverClass, jdbcUrl, username, password);
    }
    
    private String createConfigXml(String xmlFilePath, String driverClass, String jdbcUrl, String username, String password) {
        File xmlFile = new File(xmlFilePath);
        String absolutePath = xmlFile.getAbsolutePath();
        
        String mapUnderscoreToCamelCase = config.getProperty("mybatis.mapUnderscoreToCamelCase", "true");
        String transactionManager = config.getProperty("mybatis.transactionManager", "JDBC");
        String dataSource = config.getProperty("mybatis.dataSource", "POOLED");
        
        return "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n" +
               "<!DOCTYPE configuration PUBLIC \"-//mybatis.org//DTD Config 3.0//EN\" \"http://mybatis.org/dtd/mybatis-3-config.dtd\">\n" +
               "<configuration>\n" +
               "  <settings>\n" +
               "    <setting name=\"mapUnderscoreToCamelCase\" value=\"" + mapUnderscoreToCamelCase + "\"/>\n" +
               "    <setting name=\"jdbcTypeForNull\" value=\"VARCHAR\"/>\n" +
               "    <setting name=\"callSettersOnNulls\" value=\"true\"/>\n" +
               "  </settings>\n" +
               "  <environments default=\"development\">\n" +
               "    <environment id=\"development\">\n" +
               "      <transactionManager type=\"" + transactionManager + "\"/>\n" +
               "      <dataSource type=\"" + dataSource + "\">\n" +
               "        <property name=\"driver\" value=\"" + driverClass + "\"/>\n" +
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
    
    private void printResults(TestResults results, boolean summaryOnly, boolean verbose) {
        int actualTests = (int) results.allResults.stream().filter(r -> r.rowCount != -1).count();
        int skippedTests = (int) results.allResults.stream().filter(r -> r.rowCount == -1).count();
        
        System.out.println("=== 실행 결과 요약 ===");
        System.out.println("총 테스트 수: " + results.totalTests);
        System.out.println("실제 실행: " + actualTests + "개");
        System.out.println("스킵됨: " + skippedTests + "개 (Example 패턴)");
        System.out.println("성공: " + results.successCount + "개");
        System.out.println("실패: " + results.failureCount + "개");
        if (actualTests > 0) {
            double actualSuccessRate = (results.successCount * 100.0 / actualTests);
            System.out.printf("실제 성공률: %.1f%% (스킵 제외)%n", actualSuccessRate);
        }
        
        if (!results.failures.isEmpty()) {
            System.out.println();
            System.out.println("=== 실패한 테스트 ===");
            for (TestResult failure : results.failures) {
                System.out.printf("❌ %s:%s - %s%n", 
                    failure.testInfo.xmlFile.getFileName(),
                    failure.testInfo.sqlId,
                    failure.errorMessage);
            }
        }
        
        // 파일별 통계
        System.out.println();
        System.out.println("=== 파일별 통계 ===");
        Map<String, FileStats> fileStats = calculateFileStats(results);
        for (Map.Entry<String, FileStats> entry : fileStats.entrySet()) {
            FileStats stats = entry.getValue();
            System.out.printf("  %s: %d/%d (%.1f%%) [스킵: %d]%n", 
                entry.getKey(), stats.success, stats.total - stats.skipped, 
                stats.getActualSuccessRate(), stats.skipped);
        }
    }
    
    private Map<String, FileStats> calculateFileStats(TestResults results) {
        Map<String, FileStats> statsMap = new HashMap<>();
        
        for (TestResult result : results.allResults) {
            String fileName = result.testInfo.xmlFile.getFileName().toString();
            FileStats stats = statsMap.computeIfAbsent(fileName, k -> new FileStats());
            stats.total++;
            
            if (result.rowCount == -1) {
                // 스킵된 경우
                stats.skipped++;
            } else if (result.success) {
                stats.success++;
            } else {
                stats.failure++;
            }
        }
        
        return statsMap;
    }
    
    /**
     * SQL 정보를 Repository에 저장
     */
    private void saveSqlInfoToRepository(List<SqlTestInfo> sqlTests, SqlListRepository repository, Properties parameters, String dbType) {
        System.out.println("=== SQL 정보 저장 시작 ===");
        
        for (SqlTestInfo testInfo : sqlTests) {
            try {
                // 파라미터 추출
                String sqlContent = extractSqlContent(testInfo.xmlFile, testInfo.sqlId);
                Set<String> paramSet = extractParametersFromSql(sqlContent);
                String paramList = repository.formatParameterList(paramSet);
                
                // 매퍼명 추출
                String mapperName = extractMapperName(testInfo.xmlFile);
                String fullSqlId = mapperName + "." + testInfo.sqlId;
                
                // 실제 매퍼 파일 경로 사용
                String actualFilePath = testInfo.xmlFile.toString();
                
                if ("oracle".equalsIgnoreCase(dbType)) {
                    // Oracle인 경우 소스 정보 저장
                    repository.saveSqlInfo(
                        fullSqlId,
                        testInfo.sqlType,
                        actualFilePath != null ? actualFilePath : testInfo.xmlFile.toString(),
                        sqlContent,
                        paramList
                    );
                } else {
                    // PostgreSQL/MySQL인 경우 타겟 정보 업데이트
                    repository.updateTargetInfo(
                        fullSqlId,
                        actualFilePath != null ? actualFilePath : testInfo.xmlFile.toString(),
                        sqlContent,
                        paramList
                    );
                }
                
            } catch (Exception e) {
                System.err.println("SQL 정보 저장 실패 (" + testInfo.sqlId + "): " + e.getMessage());
            }
        }
        
        System.out.println("SQL 정보 저장 완료: " + sqlTests.size() + "건");
        System.out.println();
    }
    
    /**
     * 파일 경로에서 매퍼명 추출
     */
    private String extractMapperName(Path xmlFile) {
        try {
            String fileName = xmlFile.getFileName().toString();
            
            // .xml 확장자 제거
            if (fileName.endsWith(".xml")) {
                fileName = fileName.substring(0, fileName.length() - 4);
            }
            
            return fileName;
        } catch (Exception e) {
            return "Unknown";
        }
    }
    
    /**
     * XML 파일에서 특정 SQL ID의 내용 추출
     */
    private String extractSqlContent(Path xmlFile, String sqlId) {
        try {
            String content = Files.readString(xmlFile);
            
            // 정규식으로 해당 SQL ID의 내용 추출
            String pattern = "<(select|insert|update|delete)\\s+id=\"" + sqlId + "\"[^>]*>(.*?)</(select|insert|update|delete)>";
            java.util.regex.Pattern p = java.util.regex.Pattern.compile(pattern, java.util.regex.Pattern.DOTALL | java.util.regex.Pattern.CASE_INSENSITIVE);
            java.util.regex.Matcher m = p.matcher(content);
            
            if (m.find()) {
                return m.group(2).trim();
            }
            
            return "SQL 내용 추출 실패";
            
        } catch (Exception e) {
            return "SQL 내용 추출 오류: " + e.getMessage();
        }
    }
    
    /**
     * SQL에서 파라미터 추출
     */
    private Set<String> extractParametersFromSql(String sqlContent) {
        Set<String> parameters = new HashSet<>();
        
        // #{} 파라미터 추출
        java.util.regex.Pattern paramPattern = java.util.regex.Pattern.compile("#\\{([^}]+)\\}");
        java.util.regex.Matcher matcher = paramPattern.matcher(sqlContent);
        while (matcher.find()) {
            String param = matcher.group(1);
            // 복합 파라미터 처리 (user.name -> user)
            if (param.contains(".")) {
                param = param.substring(0, param.indexOf("."));
            }
            if (param.contains("[")) {
                param = param.substring(0, param.indexOf("["));
            }
            parameters.add(param.trim());
        }
        
        // ${} 파라미터 추출
        java.util.regex.Pattern dollarPattern = java.util.regex.Pattern.compile("\\$\\{([^}]+)\\}");
        java.util.regex.Matcher dollarMatcher = dollarPattern.matcher(sqlContent);
        while (dollarMatcher.find()) {
            String param = dollarMatcher.group(1);
            // 복합 파라미터 처리
            if (param.contains(".")) {
                param = param.substring(0, param.indexOf("."));
            }
            if (param.contains("[")) {
                param = param.substring(0, param.indexOf("["));
            }
            parameters.add(param.trim());
        }
        
        return parameters;
    }
    
    /**
     * 결과 비교 및 통계 출력
     */
    private void performResultComparison(SqlListRepository repository) {
        System.out.println("=== SQL 결과 비교 시작 ===");
        
        try {
            // 결과 비교 수행
            repository.compareAndUpdateResults();
            
            // 통계 출력
            Map<String, Integer> stats = repository.getComparisonStatistics();
            
            System.out.println();
            System.out.println("=== SQL 비교 검증 최종 통계 ===");
            System.out.println("총 SQL 수: " + stats.getOrDefault("total", 0));
            System.out.println("결과 동일: " + stats.getOrDefault("same", 0) + "건");
            System.out.println("결과 상이: " + stats.getOrDefault("different", 0) + "건");
            System.out.println("비교 대기: " + stats.getOrDefault("pending", 0) + "건");
            System.out.println("소스 결과 없음: " + stats.getOrDefault("missing_src", 0) + "건");
            System.out.println("타겟 결과 없음: " + stats.getOrDefault("missing_tgt", 0) + "건");
            System.out.println("양쪽 결과 있음: " + stats.getOrDefault("both_results", 0) + "건");
            
            int total = stats.getOrDefault("total", 0);
            int same = stats.getOrDefault("same", 0);
            if (total > 0) {
                double successRate = (same * 100.0) / total;
                System.out.printf("성공률: %.1f%%\n", successRate);
            }
            
            // 누락된 결과가 있는 경우 상세 정보 출력
            int missingSrc = stats.getOrDefault("missing_src", 0);
            int missingTgt = stats.getOrDefault("missing_tgt", 0);
            if (missingSrc > 0 || missingTgt > 0) {
                System.out.println();
                System.out.println("=== 누락된 결과 상세 분석 ===");
                printMissingResults(repository);
            }
            
        } catch (Exception e) {
            System.err.println("결과 비교 중 오류 발생: " + e.getMessage());
        }
        
        System.out.println();
    }
    
    /**
     * 누락된 결과 상세 분석
     */
    private void printMissingResults(SqlListRepository repository) {
        try (Connection conn = repository.getTargetConnection()) {
            // 소스 결과가 없는 SQL들
            String missingSrcSql = "SELECT sql_id, sql_type FROM sqllist WHERE src_result IS NULL ORDER BY sql_id";
            try (PreparedStatement pstmt = conn.prepareStatement(missingSrcSql);
                 ResultSet rs = pstmt.executeQuery()) {
                
                System.out.println("소스 결과가 없는 SQL:");
                while (rs.next()) {
                    System.out.println("  - " + rs.getString("sql_id") + " (" + rs.getString("sql_type") + ")");
                }
            }
            
            // 타겟 결과가 없는 SQL들
            String missingTgtSql = "SELECT sql_id, sql_type FROM sqllist WHERE tgt_result IS NULL ORDER BY sql_id";
            try (PreparedStatement pstmt = conn.prepareStatement(missingTgtSql);
                 ResultSet rs = pstmt.executeQuery()) {
                
                System.out.println("타겟 결과가 없는 SQL:");
                while (rs.next()) {
                    System.out.println("  - " + rs.getString("sql_id") + " (" + rs.getString("sql_type") + ")");
                }
            }
            
        } catch (Exception e) {
            System.err.println("누락 결과 분석 실패: " + e.getMessage());
        }
    }
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
        List<Map<String, Object>> resultData;
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
    
    /**
     * 파라미터 값을 적절한 타입으로 변환
     */
    private Object convertParameterValue(String key, String value) {
        if (value == null || value.trim().isEmpty()) {
            return "1"; // 기본값
        }
        
        String lowerKey = key.toLowerCase();
        
        // ID 관련 파라미터는 숫자로 변환 시도
        if (lowerKey.endsWith("id") || lowerKey.equals("limit") || lowerKey.equals("offset") || 
            lowerKey.equals("page") || lowerKey.equals("size") || lowerKey.equals("count") ||
            lowerKey.equals("quantity") || lowerKey.equals("amount") || lowerKey.equals("price") ||
            lowerKey.equals("year") || lowerKey.equals("month") || lowerKey.equals("day") ||
            lowerKey.equals("days") || lowerKey.equals("version") || lowerKey.equals("enabled") ||
            lowerKey.equals("active") || lowerKey.equals("deleted")) {
            
            try {
                return Long.parseLong(value);
            } catch (NumberFormatException e) {
                // 숫자 변환 실패 시 문자열 그대로 반환
                return value;
            }
        }
        
        // 날짜 관련 파라미터는 문자열로 유지
        if (lowerKey.contains("date") || lowerKey.contains("time")) {
            return value;
        }
        
        // 기본적으로 문자열로 반환
        return value;
    }
    
    /**
     * MyBatis 바인드 변수용으로 파라미터 값 정리
     * properties 파일의 따옴표를 제거하여 MyBatis가 올바르게 처리할 수 있도록 함
     */
    private String cleanParameterValue(String value) {
        if (value == null || value.trim().isEmpty()) {
            return "1"; // null이나 빈 값은 기본값 "1"로 설정
        }
        
        String cleanValue = value.trim();
        
        // 작은따옴표로 감싸져 있으면 제거
        if (cleanValue.startsWith("'") && cleanValue.endsWith("'") && cleanValue.length() > 1) {
            cleanValue = cleanValue.substring(1, cleanValue.length() - 1);
        }
        
        // 여전히 빈 값이면 기본값 설정
        if (cleanValue.isEmpty()) {
            cleanValue = "1";
        }
        
        return cleanValue;
    }
    
    private static class FileStats {
        int total = 0;
        int success = 0;
        int failure = 0;
        int skipped = 0;
        
        double getSuccessRate() {
            return total > 0 ? (success * 100.0 / total) : 0;
        }
        
        double getActualSuccessRate() {
            int actualTests = total - skipped;
            return actualTests > 0 ? (success * 100.0 / actualTests) : 0;
        }
    }
}
