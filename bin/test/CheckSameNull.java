import java.sql.*;
import java.util.*;

public class CheckSameNull {
    public static void main(String[] args) {
        try {
            // PostgreSQL 연결 정보
            String host = System.getenv("PGHOST");
            String port = System.getenv("PGPORT");
            String database = System.getenv("PGDATABASE");
            String user = System.getenv("PGUSER");
            String password = System.getenv("PGPASSWORD");
            
            String url = "jdbc:postgresql://" + host + ":" + port + "/" + database;
            
            System.out.println("=== PostgreSQL 연결 정보 ===");
            System.out.println("Host: " + host);
            System.out.println("Port: " + port);
            System.out.println("Database: " + database);
            System.out.println("User: " + user);
            System.out.println();
            
            try (Connection conn = DriverManager.getConnection(url, user, password)) {
                System.out.println("✅ DB 연결 성공");
                System.out.println();
                
                // 전체 통계 먼저 확인
                String statsSql = "SELECT " +
                    "COUNT(*) as total, " +
                    "COUNT(CASE WHEN src_result IS NOT NULL THEN 1 END) as has_src, " +
                    "COUNT(CASE WHEN tgt_result IS NOT NULL THEN 1 END) as has_tgt, " +
                    "COUNT(CASE WHEN src_result IS NOT NULL AND tgt_result IS NOT NULL THEN 1 END) as both_results, " +
                    "COUNT(CASE WHEN same = 'Y' THEN 1 END) as same_y, " +
                    "COUNT(CASE WHEN same = 'N' THEN 1 END) as same_n, " +
                    "COUNT(CASE WHEN same IS NULL THEN 1 END) as same_null " +
                    "FROM sqllist";
                
                try (PreparedStatement pstmt = conn.prepareStatement(statsSql);
                     ResultSet rs = pstmt.executeQuery()) {
                    
                    if (rs.next()) {
                        System.out.println("=== SQLLIST 테이블 전체 통계 ===");
                        System.out.println("총 SQL 수: " + rs.getInt("total"));
                        System.out.println("소스 결과 있음: " + rs.getInt("has_src"));
                        System.out.println("타겟 결과 있음: " + rs.getInt("has_tgt"));
                        System.out.println("양쪽 결과 있음: " + rs.getInt("both_results"));
                        System.out.println("same = 'Y': " + rs.getInt("same_y"));
                        System.out.println("same = 'N': " + rs.getInt("same_n"));
                        System.out.println("same IS NULL: " + rs.getInt("same_null"));
                        System.out.println();
                    }
                }
                
                // same IS NULL인 레코드들 상세 조회
                String nullSql = "SELECT sql_id, sql_type, " +
                    "CASE WHEN src_result IS NULL THEN 'NO' ELSE 'YES' END as has_src_result, " +
                    "CASE WHEN tgt_result IS NULL THEN 'NO' ELSE 'YES' END as has_tgt_result " +
                    "FROM sqllist WHERE same IS NULL ORDER BY sql_id";
                
                try (PreparedStatement pstmt = conn.prepareStatement(nullSql);
                     ResultSet rs = pstmt.executeQuery()) {
                    
                    System.out.println("=== same IS NULL인 SQL 목록 ===");
                    int count = 0;
                    while (rs.next()) {
                        count++;
                        System.out.printf("%2d. %-50s [%s] SRC:%s TGT:%s%n", 
                            count,
                            rs.getString("sql_id"),
                            rs.getString("sql_type"),
                            rs.getString("has_src_result"),
                            rs.getString("has_tgt_result")
                        );
                    }
                    
                    if (count == 0) {
                        System.out.println("  (없음 - 모든 SQL이 비교 완료됨)");
                    } else {
                        System.out.println();
                        System.out.println("총 " + count + "건의 SQL이 비교되지 않았습니다.");
                    }
                }
                
                // 소스 결과만 없는 경우
                System.out.println();
                String missingSrcSql = "SELECT sql_id FROM sqllist WHERE src_result IS NULL ORDER BY sql_id";
                try (PreparedStatement pstmt = conn.prepareStatement(missingSrcSql);
                     ResultSet rs = pstmt.executeQuery()) {
                    
                    System.out.println("=== 소스 결과가 없는 SQL ===");
                    int count = 0;
                    while (rs.next()) {
                        System.out.println("  " + (++count) + ". " + rs.getString("sql_id"));
                    }
                    if (count == 0) {
                        System.out.println("  (없음)");
                    }
                }
                
                // 타겟 결과만 없는 경우
                System.out.println();
                String missingTgtSql = "SELECT sql_id FROM sqllist WHERE tgt_result IS NULL ORDER BY sql_id";
                try (PreparedStatement pstmt = conn.prepareStatement(missingTgtSql);
                     ResultSet rs = pstmt.executeQuery()) {
                    
                    System.out.println("=== 타겟 결과가 없는 SQL ===");
                    int count = 0;
                    while (rs.next()) {
                        System.out.println("  " + (++count) + ". " + rs.getString("sql_id"));
                    }
                    if (count == 0) {
                        System.out.println("  (없음)");
                    }
                }
                
            }
            
        } catch (Exception e) {
            System.err.println("오류 발생: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
