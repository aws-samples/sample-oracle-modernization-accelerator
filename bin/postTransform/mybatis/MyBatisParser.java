import org.apache.ibatis.builder.xml.XMLMapperBuilder;
import org.apache.ibatis.session.Configuration;
import org.apache.ibatis.mapping.MappedStatement;
import org.apache.ibatis.mapping.BoundSql;
import org.apache.ibatis.mapping.SqlSource;
import org.apache.ibatis.io.Resources;

import java.io.*;
import java.util.*;

public class MyBatisParser {
    
    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: java MyBatisParser <xml-file-path> [statement-id]");
            System.exit(1);
        }
        
        String xmlFilePath = args[0];
        String targetStatementId = args.length > 1 ? args[1] : null;
        
        try {
            // MyBatis Configuration 생성
            Configuration configuration = new Configuration();
            
            // XML 파일 읽기
            InputStream inputStream = new FileInputStream(xmlFilePath);
            
            // XMLMapperBuilder로 파싱
            XMLMapperBuilder builder = new XMLMapperBuilder(
                inputStream, 
                configuration, 
                xmlFilePath, 
                configuration.getSqlFragments()
            );
            
            builder.parse();
            
            // 파싱된 MappedStatement들 확인
            Collection<MappedStatement> mappedStatements = configuration.getMappedStatements();
            
            for (MappedStatement ms : mappedStatements) {
                String statementId = ms.getId();
                
                // 특정 statement만 처리하거나 모든 statement 처리
                if (targetStatementId == null || statementId.contains(targetStatementId)) {
                    
                    System.out.println("=== Statement: " + statementId + " ===");
                    System.out.println("SQL Command Type: " + ms.getSqlCommandType());
                    
                    // 테스트용 파라미터 생성
                    Map<String, Object> parameters = createTestParameters();
                    
                    // BoundSql 생성 (동적 SQL 처리됨)
                    SqlSource sqlSource = ms.getSqlSource();
                    BoundSql boundSql = sqlSource.getBoundSql(parameters);
                    
                    System.out.println("Generated SQL:");
                    System.out.println(boundSql.getSql());
                    
                    System.out.println("Parameters:");
                    for (Map.Entry<String, Object> entry : parameters.entrySet()) {
                        System.out.println("  " + entry.getKey() + " = " + entry.getValue());
                    }
                    
                    System.out.println();
                }
            }
            
            inputStream.close();
            
        } catch (Exception e) {
            System.err.println("Error parsing MyBatis XML: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private static Map<String, Object> createTestParameters() {
        Map<String, Object> params = new HashMap<>();
        
        // 기본 테스트 파라미터들
        params.put("agtCd", "TEST");
        params.put("diFlag", "Y");
        params.put("saletype", "DEFAULT");
        params.put("virtualrsvno", "DEFAULT");
        params.put("saledeptcd", "TEST");
        params.put("orderby", "A.RSV_DTM DESC");
        params.put("inicisjoinyn", "Y");
        params.put("rsvDtm", "20240101");
        params.put("depDtm", "20240101");
        params.put("arrDtm", "20240101");
        params.put("cancelDtm", "20240101");
        params.put("payTl", "20240101235959");
        params.put("airTtl", "20240101235959");
        params.put("issueDate", "20240101");
        
        // 리스트 파라미터들
        params.put("listAreaRouteCd", Arrays.asList("TEST1", "TEST2"));
        params.put("listStockAirCd", Arrays.asList("OZ", "KE"));
        params.put("listChrgUsrId", Arrays.asList("testuser"));
        
        return params;
    }
}
