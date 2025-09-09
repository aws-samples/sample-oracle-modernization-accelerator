package com.test.mybatis;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.*;
import java.nio.file.*;
import java.sql.*;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Oracle vs PostgreSQL 테스트 결과 분석 프로그램
 * 
 * 기능:
 * 1. PostgreSQL 실행 실패 SQL 에러 분석
 * 2. sqllist 테이블의 same='N' 케이스 분석
 *    - 길이 다른 경우: '결과가 다름'
 *    - 길이 같은 경우: JSON 정렬 후 비교하여 '정렬 방식 차이' vs '결과가 다름' 구분
 */
public class TestResultAnalyzer {
    
    // PostgreSQL 접속 정보를 환경변수에서 읽기
    private static final String POSTGRES_HOST = System.getenv("PGHOST") != null ? System.getenv("PGHOST") : "localhost";
    private static final String POSTGRES_PORT = System.getenv("PGPORT") != null ? System.getenv("PGPORT") : "5432";
    private static final String POSTGRES_DATABASE = System.getenv("PGDATABASE") != null ? System.getenv("PGDATABASE") : "oma";
    private static final String POSTGRES_USER = System.getenv("PGUSER") != null ? System.getenv("PGUSER") : "oma";
    private static final String POSTGRES_PASSWORD = System.getenv("PGPASSWORD") != null ? System.getenv("PGPASSWORD") : "";
    private static final String POSTGRES_URL = "jdbc:postgresql://" + POSTGRES_HOST + ":" + POSTGRES_PORT + "/" + POSTGRES_DATABASE;
    
    private ObjectMapper objectMapper;
    
    public TestResultAnalyzer() {
        this.objectMapper = new ObjectMapper();
        this.objectMapper.configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);
        this.objectMapper.configure(SerializationFeature.INDENT_OUTPUT, false);
    }
    
    public static void main(String[] args) {
        TestResultAnalyzer analyzer = new TestResultAnalyzer();
        
        try {
            if (args.length > 0 && "--fix-sorting".equals(args[0])) {
                // 정렬 차이 자동 수정 모드
                analyzer.fixSortingDifferences();
            } else {
                // 일반 분석 모드
                System.out.println("=== Oracle vs PostgreSQL 테스트 결과 분석 ===\n");
                
                // 1. PostgreSQL 실행 실패 분석
                analyzer.analyzePostgreSQLErrors();
                
                System.out.println("\n" + "=".repeat(80) + "\n");
                
                // 2. sqllist 테이블 same='N' 케이스 분석
                analyzer.analyzeSqlListDifferences();
            }
        } catch (Exception e) {
            System.err.println("분석 중 오류 발생: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    /**
     * 1. PostgreSQL 실행 실패 SQL 에러 분석
     */
    private void analyzePostgreSQLErrors() throws Exception {
        System.out.println("📊 1. PostgreSQL 실행 실패 SQL 에러 분석");
        System.out.println("-".repeat(50));
        
        // 최신 PostgreSQL 결과 파일 찾기
        String resultFile = findLatestPostgreSQLResultFile();
        if (resultFile == null) {
            System.out.println("✅ PostgreSQL 실행 실패 SQL이 없습니다. (모든 SQL이 성공적으로 실행됨)");
            return;
        }
        
        System.out.println("📄 분석 파일: " + resultFile);
        
        // JSON 파일 파싱
        JsonNode rootNode = objectMapper.readTree(new File(resultFile));
        JsonNode failedTests = rootNode.get("failedTests");
        
        if (failedTests == null || !failedTests.isArray() || failedTests.size() == 0) {
            System.out.println("✅ PostgreSQL 실행 실패 SQL이 없습니다.");
            return;
        }
        
        // 에러 유형별 분류
        Map<String, List<FailedTest>> errorTypeMap = new LinkedHashMap<>();
        
        for (JsonNode failedTest : failedTests) {
            String xmlFile = failedTest.get("xmlFile").asText();
            String sqlId = failedTest.get("sqlId").asText();
            String errorMessage = failedTest.get("errorMessage").asText();
            
            String errorType = categorizeError(errorMessage);
            
            errorTypeMap.computeIfAbsent(errorType, k -> new ArrayList<>())
                       .add(new FailedTest(xmlFile, sqlId, errorMessage));
        }
        
        // 결과 출력
        System.out.println("\n🔍 에러 유형별 분석 결과:");
        System.out.println("총 실패 SQL 수: " + failedTests.size() + "개\n");
        
        int typeIndex = 1;
        for (Map.Entry<String, List<FailedTest>> entry : errorTypeMap.entrySet()) {
            String errorType = entry.getKey();
            List<FailedTest> tests = entry.getValue();
            
            System.out.println(typeIndex + ". " + errorType + " (" + tests.size() + "개)");
            System.out.println("   " + "-".repeat(40));
            
            for (FailedTest test : tests) {
                System.out.println("   📁 " + test.xmlFile + " → " + test.sqlId);
                System.out.println("      💬 " + extractErrorSummary(test.errorMessage));
                System.out.println();
            }
            typeIndex++;
        }
        
        // Q Chat용 분석 요청은 제거 (불필요)
    }
    
    /**
     * 2. sqllist 테이블 same='N' 케이스 분석
     */
    private void analyzeSqlListDifferences() throws Exception {
        System.out.println("📊 2. sqllist 테이블 same='N' 케이스 분석");
        System.out.println("-".repeat(50));
        
        // 환경변수에서 DB 타입 읽기
        String srcDbType = System.getenv("SOURCE_DBMS_TYPE");
        String tgtDbType = System.getenv("TARGET_DBMS_TYPE");
        
        if (srcDbType == null) srcDbType = "Source";
        if (tgtDbType == null) tgtDbType = "Target";
        
        System.out.println("🔍 DB 타입: " + srcDbType + " vs " + tgtDbType + "\n");
        
        try (Connection conn = DriverManager.getConnection(POSTGRES_URL, POSTGRES_USER, POSTGRES_PASSWORD)) {
            
            // same='N' 케이스 조회
            String sql = """
                SELECT sql_id, src_result, tgt_result, src_path, tgt_path,
                       LENGTH(src_result) as src_length,
                       LENGTH(tgt_result) as tgt_length
                FROM oma.sqllist 
                WHERE same = 'N' 
                AND src_result IS NOT NULL 
                AND tgt_result IS NOT NULL
                ORDER BY sql_id
                """;
            
            List<SqlDifference> lengthDifferent = new ArrayList<>();
            List<SqlDifference> sortingDifferent = new ArrayList<>();
            List<SqlDifference> contentDifferent = new ArrayList<>();
            
            try (PreparedStatement pstmt = conn.prepareStatement(sql);
                 ResultSet rs = pstmt.executeQuery()) {
                
                while (rs.next()) {
                    String sqlId = rs.getString("sql_id");
                    String srcResult = rs.getString("src_result");
                    String tgtResult = rs.getString("tgt_result");
                    String srcPath = rs.getString("src_path");
                    String tgtPath = rs.getString("tgt_path");
                    int srcLength = rs.getInt("src_length");
                    int tgtLength = rs.getInt("tgt_length");
                    
                    SqlDifference diff = new SqlDifference(sqlId, srcResult, tgtResult, srcLength, tgtLength, srcPath, tgtPath);
                    
                    if (srcLength != tgtLength) {
                        // 길이가 다른 경우: 결과가 다름
                        lengthDifferent.add(diff);
                    } else {
                        // 길이가 같은 경우: JSON 정렬 후 비교
                        if (compareJsonAfterSorting(srcResult, tgtResult)) {
                            sortingDifferent.add(diff);
                        } else {
                            contentDifferent.add(diff);
                        }
                    }
                }
            }
            
            // 결과 출력
            System.out.println("\n🔍 same='N' 케이스 분석 결과:");
            System.out.println("총 분석 대상: " + (lengthDifferent.size() + sortingDifferent.size() + contentDifferent.size()) + "개\n");
            
            // 1. 결과가 다름 (길이 차이 + 내용 차이)
            List<SqlDifference> allDifferent = new ArrayList<>();
            allDifferent.addAll(lengthDifferent);
            allDifferent.addAll(contentDifferent);
            
            System.out.println("1. 결과가 다름 - " + allDifferent.size() + "개");
            System.out.println("   " + "-".repeat(50));
            for (SqlDifference diff : allDifferent) {
                String[] parts = diff.sqlId.split("\\.");
                String mapper = parts.length > 1 ? parts[0] : "Unknown";
                String sqlIdOnly = parts.length > 1 ? parts[1] : diff.sqlId;
                
                if (diff.srcLength != diff.tgtLength) {
                    System.out.println("   📁 " + mapper + " → " + sqlIdOnly + 
                                     " (길이 차이: " + srcDbType + " " + diff.srcLength + " bytes, " + tgtDbType + " " + diff.tgtLength + " bytes)");
                } else {
                    System.out.println("   📁 " + mapper + " → " + sqlIdOnly + " (내용 차이)");
                }
                System.out.println("      📂 " + srcDbType + ": " + (diff.srcPath != null ? diff.srcPath : "N/A"));
                System.out.println("      📂 " + tgtDbType + ": " + (diff.tgtPath != null ? diff.tgtPath : "N/A"));
                System.out.println();
            }
            
            // 2. 정렬 방식 차이
            System.out.println("2. 정렬 방식 차이 - " + sortingDifferent.size() + "개");
            System.out.println("   " + "-".repeat(50));
            for (SqlDifference diff : sortingDifferent) {
                String[] parts = diff.sqlId.split("\\.");
                String mapper = parts.length > 1 ? parts[0] : "Unknown";
                String sqlIdOnly = parts.length > 1 ? parts[1] : diff.sqlId;
                System.out.println("   📁 " + mapper + " → " + sqlIdOnly);
                System.out.println("      📂 " + srcDbType + ": " + (diff.srcPath != null ? diff.srcPath : "N/A"));
                System.out.println("      📂 " + tgtDbType + ": " + (diff.tgtPath != null ? diff.tgtPath : "N/A"));
                System.out.println();
            }
            
            // 요약 통계
            System.out.println("\n📈 분석 요약:");
            System.out.println("   • 결과가 다름: " + allDifferent.size() + "개 (길이 차이: " + lengthDifferent.size() + "개, 내용 차이: " + contentDifferent.size() + "개)");
            System.out.println("   • 정렬 방식 차이 (실제로는 동일): " + sortingDifferent.size() + "개");
            if (sortingDifferent.size() > 0) {
                System.out.println("   • 잠재적 성공률 향상: +" + sortingDifferent.size() + "개");
            }
        }
    }
    
    /**
     * JSON 정렬 후 비교 - results 배열만 정렬
     */
    private boolean compareJsonAfterSorting(String json1, String json2) {
        try {
            JsonNode node1 = objectMapper.readTree(json1);
            JsonNode node2 = objectMapper.readTree(json2);
            
            // results 배열 추출
            JsonNode results1 = node1.get("results");
            JsonNode results2 = node2.get("results");
            
            if (results1 == null || results2 == null) {
                return false; // results가 없으면 다른 것으로 처리
            }
            
            if (!results1.isArray() || !results2.isArray()) {
                return false; // 배열이 아니면 다른 것으로 처리
            }
            
            // results 배열만 정렬하여 비교
            ArrayNode sortedResults1 = sortJsonArray((ArrayNode) results1);
            ArrayNode sortedResults2 = sortJsonArray((ArrayNode) results2);
            
            // 정렬된 results 배열을 문자열로 변환하여 비교
            String sortedStr1 = objectMapper.writeValueAsString(sortedResults1);
            String sortedStr2 = objectMapper.writeValueAsString(sortedResults2);
            
            return sortedStr1.equals(sortedStr2);
            
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * JSON 배열 정렬 - 각 객체를 정규화된 문자열로 변환하여 정렬
     */
    private ArrayNode sortJsonArray(ArrayNode arrayNode) {
        List<JsonNode> nodeList = new ArrayList<>();
        arrayNode.forEach(nodeList::add);
        
        // 각 JSON 객체를 정규화된 문자열로 변환하여 정렬
        nodeList.sort((a, b) -> {
            try {
                // 객체 내부 키도 정렬하여 정규화
                String strA = objectMapper.writeValueAsString(a);
                String strB = objectMapper.writeValueAsString(b);
                return strA.compareTo(strB);
            } catch (Exception e) {
                return 0;
            }
        });
        
        ArrayNode sortedArray = objectMapper.createArrayNode();
        nodeList.forEach(sortedArray::add);
        return sortedArray;
    }
    
    /**
     * 전체 JSON 정렬 후 비교
     */
    private boolean sortJsonAndCompare(JsonNode node1, JsonNode node2) {
        try {
            String sorted1 = objectMapper.writeValueAsString(node1);
            String sorted2 = objectMapper.writeValueAsString(node2);
            return sorted1.equals(sorted2);
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * 에러 유형 분류
     */
    private String categorizeError(String errorMessage) {
        if (errorMessage.contains("operator does not exist")) {
            return "데이터 타입 캐스팅 오류";
        } else if (errorMessage.contains("cannot cast type integer to interval")) {
            return "날짜/시간 처리 오류 (INTERVAL 캐스팅)";
        } else if (errorMessage.contains("invalid input syntax for type integer")) {
            return "데이터 타입 입력 오류";
        } else if (errorMessage.contains("recursive reference to query")) {
            return "재귀 쿼리 구문 오류";
        } else if (errorMessage.contains("relation") && errorMessage.contains("does not exist")) {
            return "테이블/뷰 존재하지 않음";
        } else if (errorMessage.contains("function") && errorMessage.contains("does not exist")) {
            return "함수 존재하지 않음";
        } else {
            return "기타 오류";
        }
    }
    
    /**
     * 정렬 방식 차이 자동 수정
     */
    private void fixSortingDifferences() throws Exception {
        System.out.println("🔧 정렬 방식 차이 자동 수정 시작...");
        
        try (Connection conn = DriverManager.getConnection(POSTGRES_URL, POSTGRES_USER, POSTGRES_PASSWORD)) {
            
            // 정렬 차이 케이스 조회 (길이는 같지만 내용이 다른 경우)
            String sql = """
                SELECT sql_id, src_result, tgt_result, tgt_path
                FROM oma.sqllist 
                WHERE same = 'N' 
                AND src_result IS NOT NULL 
                AND tgt_result IS NOT NULL
                AND LENGTH(src_result) = LENGTH(tgt_result)
                ORDER BY sql_id
                """;
            
            int fixedCount = 0;
            
            try (PreparedStatement pstmt = conn.prepareStatement(sql);
                 ResultSet rs = pstmt.executeQuery()) {
                
                while (rs.next()) {
                    String sqlId = rs.getString("sql_id");
                    String srcResult = rs.getString("src_result");
                    String tgtResult = rs.getString("tgt_result");
                    String tgtPath = rs.getString("tgt_path");
                    
                    // JSON 정렬 후 비교하여 정렬 차이인지 확인
                    if (compareJsonAfterSorting(srcResult, tgtResult)) {
                        System.out.println("📝 정렬 차이 수정: " + sqlId);
                        
                        if (addOrderByToSql(tgtPath, sqlId)) {
                            fixedCount++;
                            System.out.println("   ✅ ORDER BY 추가 완료");
                        } else {
                            System.out.println("   ❌ 수정 실패");
                        }
                    }
                }
            }
            
            System.out.println("\n✅ 정렬 차이 자동 수정 완료: " + fixedCount + "개 수정됨");
        }
    }
    
    /**
     * XML 파일에서 해당 SQL에 ORDER BY 추가
     */
    private boolean addOrderByToSql(String xmlPath, String fullSqlId) {
        try {
            String[] parts = fullSqlId.split("\\.");
            if (parts.length < 2) return false;
            
            String sqlIdOnly = parts[1];
            
            // XML 파일 읽기
            String content = Files.readString(Paths.get(xmlPath));
            
            // SQL 태그 찾기
            String pattern = "(<(select|insert|update|delete)[^>]*id\\s*=\\s*[\"']" + sqlIdOnly + "[\"'][^>]*>)(.*?)(</\\2>)";
            java.util.regex.Pattern p = java.util.regex.Pattern.compile(pattern, java.util.regex.Pattern.CASE_INSENSITIVE | java.util.regex.Pattern.DOTALL);
            java.util.regex.Matcher m = p.matcher(content);
            
            if (m.find()) {
                String openTag = m.group(1);
                String sqlContent = m.group(3);
                String closeTag = m.group(4);
                
                // SELECT 문인지 확인
                if (openTag.toLowerCase().contains("<select")) {
                    // 이미 ORDER BY가 있는지 더 정확하게 확인 (CDATA, 주석 등 고려)
                    String cleanSqlContent = sqlContent.replaceAll("<!\\[CDATA\\[.*?\\]\\]>", "")
                                                      .replaceAll("<!--.*?-->", "");
                    
                    if (!cleanSqlContent.toLowerCase().matches(".*\\border\\s+by\\b.*")) {
                        // 가장 마지막 부분에 ORDER BY 1 추가
                        sqlContent = sqlContent.trim();
                        if (sqlContent.endsWith(";")) {
                            sqlContent = sqlContent.substring(0, sqlContent.length() - 1) + "\n        ORDER BY 1;";
                        } else {
                            sqlContent = sqlContent + "\n        ORDER BY 1";
                        }
                        
                        String newContent = content.replace(m.group(0), openTag + sqlContent + closeTag);
                        Files.writeString(Paths.get(xmlPath), newContent);
                        return true;
                    } else {
                        System.out.println("   ⚠️  이미 ORDER BY가 존재합니다");
                        return false;
                    }
                }
            }
            
            return false;
            
        } catch (Exception e) {
            System.err.println("ORDER BY 추가 실패: " + e.getMessage());
            return false;
        }
    }
    
    /**
     * 에러 메시지 요약 추출
     */
    private String extractErrorSummary(String errorMessage) {
        String[] lines = errorMessage.split("\n");
        for (String line : lines) {
            if (line.contains("ERROR:")) {
                return line.trim();
            }
        }
        return "오류 정보 없음";
    }
    
    /**
     * 최신 PostgreSQL 결과 파일 찾기
     */
    private String findLatestPostgreSQLResultFile() {
        try {
            Path currentDir = Paths.get(".");
            return Files.list(currentDir)
                    .filter(path -> path.getFileName().toString().startsWith("bulk_test_result_"))
                    .filter(path -> path.getFileName().toString().endsWith(".json"))
                    .max(Comparator.comparing(path -> path.getFileName().toString()))
                    .map(Path::toString)
                    .orElse(null);
        } catch (Exception e) {
            return null;
        }
    }
    
    // generateQChatAnalysisRequest 메서드 제거됨
    
    // 내부 클래스들
    static class FailedTest {
        String xmlFile;
        String sqlId;
        String errorMessage;
        
        FailedTest(String xmlFile, String sqlId, String errorMessage) {
            this.xmlFile = xmlFile;
            this.sqlId = sqlId;
            this.errorMessage = errorMessage;
        }
    }
    
    static class SqlDifference {
        String sqlId;
        String srcResult;
        String tgtResult;
        int srcLength;
        int tgtLength;
        String srcPath;
        String tgtPath;
        
        SqlDifference(String sqlId, String srcResult, String tgtResult, int srcLength, int tgtLength, String srcPath, String tgtPath) {
            this.sqlId = sqlId;
            this.srcResult = srcResult;
            this.tgtResult = tgtResult;
            this.srcLength = srcLength;
            this.tgtLength = tgtLength;
            this.srcPath = srcPath;
            this.tgtPath = tgtPath;
        }
    }
}
