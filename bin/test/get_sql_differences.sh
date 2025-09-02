#!/bin/bash

# SQL 차이점 조회 스크립트
# Usage: ./get_sql_differences.sh [--next] [--current <sql_id>]

POSTGRES_URL="jdbc:postgresql://omabox-stack-aurora-cluster.cluster-c12esi0ewdyz.ap-northeast-2.rds.amazonaws.com:5432/oma"
POSTGRES_USER="oma"
POSTGRES_PASSWORD="welcome1"

# 현재 처리 중인 SQL ID 저장 파일
CURRENT_SQL_FILE=".current_sql_id"

if [ "$1" = "--next" ]; then
    # 다음 SQL 가져오기
    if [ -f "$CURRENT_SQL_FILE" ]; then
        CURRENT_SQL=$(cat "$CURRENT_SQL_FILE")
        CONDITION="AND sql_id > '$CURRENT_SQL'"
    else
        CONDITION=""
    fi
    
    SQL="SELECT sql_id, src_path, tgt_path, src_result, tgt_result 
         FROM oma.sqllist 
         WHERE same = 'N' 
         AND src_result IS NOT NULL 
         AND tgt_result IS NOT NULL 
         $CONDITION
         ORDER BY sql_id 
         LIMIT 1"
         
elif [ "$1" = "--current" ] && [ -n "$2" ]; then
    # 특정 SQL ID 조회
    echo "$2" > "$CURRENT_SQL_FILE"
    SQL="SELECT sql_id, src_path, tgt_path, src_result, tgt_result 
         FROM oma.sqllist 
         WHERE sql_id = '$2'"
         
elif [ "$1" = "--list" ]; then
    # 모든 차이점 SQL 목록
    SQL="SELECT sql_id, src_path, tgt_path,
                LENGTH(src_result) as src_length,
                LENGTH(tgt_result) as tgt_length
         FROM oma.sqllist 
         WHERE same = 'N' 
         AND src_result IS NOT NULL 
         AND tgt_result IS NOT NULL
         ORDER BY sql_id"
         
else
    # 첫 번째 SQL 가져오기
    SQL="SELECT sql_id, src_path, tgt_path, src_result, tgt_result 
         FROM oma.sqllist 
         WHERE same = 'N' 
         AND src_result IS NOT NULL 
         AND tgt_result IS NOT NULL
         ORDER BY sql_id 
         LIMIT 1"
fi

# PostgreSQL 쿼리 실행
java -cp ".:lib/*" -Duser.timezone=UTC << 'EOF'
import java.sql.*;
import java.util.Properties;

public class QuerySqlDifferences {
    public static void main(String[] args) {
        String url = System.getenv().getOrDefault("POSTGRES_URL", 
            "jdbc:postgresql://omabox-stack-aurora-cluster.cluster-c12esi0ewdyz.ap-northeast-2.rds.amazonaws.com:5432/oma");
        String user = System.getenv().getOrDefault("POSTGRES_USER", "oma");
        String password = System.getenv().getOrDefault("POSTGRES_PASSWORD", "welcome1");
        
        String sql = System.getProperty("sql.query");
        
        try (Connection conn = DriverManager.getConnection(url, user, password);
             PreparedStatement pstmt = conn.prepareStatement(sql);
             ResultSet rs = pstmt.executeQuery()) {
            
            ResultSetMetaData metaData = rs.getMetaData();
            int columnCount = metaData.getColumnCount();
            
            // 헤더 출력
            for (int i = 1; i <= columnCount; i++) {
                System.out.print(metaData.getColumnName(i));
                if (i < columnCount) System.out.print("\t");
            }
            System.out.println();
            
            // 데이터 출력
            while (rs.next()) {
                for (int i = 1; i <= columnCount; i++) {
                    String value = rs.getString(i);
                    if (value != null && value.length() > 100) {
                        value = value.substring(0, 100) + "...";
                    }
                    System.out.print(value != null ? value : "NULL");
                    if (i < columnCount) System.out.print("\t");
                }
                System.out.println();
                
                // 현재 SQL ID 저장
                if (metaData.getColumnName(1).equals("sql_id")) {
                    try (java.io.FileWriter fw = new java.io.FileWriter(".current_sql_id")) {
                        fw.write(rs.getString(1));
                    } catch (Exception e) {
                        // 무시
                    }
                }
            }
            
        } catch (Exception e) {
            System.err.println("쿼리 실행 오류: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
EOF

# Java 컴파일 및 실행
echo "import java.sql.*; import java.util.Properties; public class QuerySqlDifferences { public static void main(String[] args) { String url = System.getenv().getOrDefault(\"POSTGRES_URL\", \"jdbc:postgresql://omabox-stack-aurora-cluster.cluster-c12esi0ewdyz.ap-northeast-2.rds.amazonaws.com:5432/oma\"); String user = System.getenv().getOrDefault(\"POSTGRES_USER\", \"oma\"); String password = System.getenv().getOrDefault(\"POSTGRES_PASSWORD\", \"welcome1\"); String sql = \"$SQL\"; try (Connection conn = DriverManager.getConnection(url, user, password); PreparedStatement pstmt = conn.prepareStatement(sql); ResultSet rs = pstmt.executeQuery()) { ResultSetMetaData metaData = rs.getMetaData(); int columnCount = metaData.getColumnCount(); for (int i = 1; i <= columnCount; i++) { System.out.print(metaData.getColumnName(i)); if (i < columnCount) System.out.print(\"\t\"); } System.out.println(); while (rs.next()) { for (int i = 1; i <= columnCount; i++) { String value = rs.getString(i); if (value != null && value.length() > 100) { value = value.substring(0, 100) + \"...\"; } System.out.print(value != null ? value : \"NULL\"); if (i < columnCount) System.out.print(\"\t\"); } System.out.println(); if (metaData.getColumnName(1).equals(\"sql_id\")) { try (java.io.FileWriter fw = new java.io.FileWriter(\".current_sql_id\")) { fw.write(rs.getString(1)); } catch (Exception e) {} } } } catch (Exception e) { System.err.println(\"쿼리 실행 오류: \" + e.getMessage()); e.printStackTrace(); } } }" > QuerySqlDifferences.java

javac -cp ".:lib/*" QuerySqlDifferences.java 2>/dev/null
java -cp ".:lib/*" QuerySqlDifferences

# 임시 파일 정리
rm -f QuerySqlDifferences.java QuerySqlDifferences.class
