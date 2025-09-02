import java.sql.*;
import java.util.*;

public class CheckDbStatus {
    public static void main(String[] args) {
        try {
            // PostgreSQL 연결 (TARGET_DBMS_TYPE=postgresql로 가정)
            String url = "jdbc:postgresql://localhost:5432/postgres";
            String user = System.getenv("PGUSER");
            String password = System.getenv("PGPASSWORD");
            
            if (user == null || password == null) {
                System.err.println("PostgreSQL 환경변수가 설정되지 않았습니다.");
                System.err.println("PGUSER, PGPASSWORD를 설정해주세요.");
                return;
            }
            
            try (Connection conn = DriverManager.getConnection(url, user, password)) {
                System.out.println("=== SQLLIST 테이블 상태 분석 ===");
                
                // 전체 통계
                String statsSql = "SELECT " +
                    "COUNT(*) as total, " +
                    "COUNT(CASE WHEN src_result IS NOT NULL THEN 1 END) as has_src, " +
                    "COUNT(CASE WHEN tgt_result IS NOT NULL THEN 1 END) as has_tgt, " +
                    "COUNT(CASE WHEN src_result IS NOT NULL AND tgt_result IS NOT NULL THEN 1 END) as both_results, " +
                    "COUNT(CASE WHEN same = 'Y' THEN 1 END) as same_count, " +
                    "COUNT(CASE WHEN same = 'N' THEN 1 END) as different_count " +
                    "FROM sqllist";
                
                try (PreparedStatement pstmt = conn.prepareStatement(statsSql);
                     ResultSet rs = pstmt.executeQuery()) {
                    
                    if (rs.next()) {
                        System.out.println("총 SQL 수: " + rs.getInt("total"));
                        System.out.println("소스 결과 있음: " + rs.getInt("has_src"));
                        System.out.println("타겟 결과 있음: " + rs.getInt("has_tgt"));
                        System.out.println("양쪽 결과 있음: " + rs.getInt("both_results"));
                        System.out.println("결과 동일: " + rs.getInt("same_count"));
                        System.out.println("결과 상이: " + rs.getInt("different_count"));
                    }
                }
                
                System.out.println();
                
                // 소스 결과가 없는 SQL들
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
                
                System.out.println();
                
                // 타겟 결과가 없는 SQL들
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
                
                System.out.println();
                
                // 결과가 다른 SQL들
                String differentSql = "SELECT sql_id FROM sqllist WHERE same = 'N' ORDER BY sql_id";
                try (PreparedStatement pstmt = conn.prepareStatement(differentSql);
                     ResultSet rs = pstmt.executeQuery()) {
                    
                    System.out.println("=== 결과가 다른 SQL ===");
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
