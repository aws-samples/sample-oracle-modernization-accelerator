-- 현재 세션에서 SQL Trace 활성화
ALTER SESSION SET SQL_TRACE = TRUE;

-- 또는 10046 이벤트 사용 (더 상세한 정보)
-- Level 1: 기본 SQL Trace
-- Level 4: Bind 변수 포함
-- Level 8: Wait 이벤트 포함  
-- Level 12: Bind 변수 + Wait 이벤트
ALTER SESSION SET EVENTS '10046 trace name context forever, level 12';

-- 특정 세션의 Trace 활성화 (DBA 권한 필요)
-- SELECT sid, serial# FROM v$session WHERE username = 'TARGET_USER';
-- EXEC DBMS_SYSTEM.SET_SQL_TRACE_IN_SESSION(sid, serial#, TRUE);

-- Trace 비활성화
ALTER SESSION SET SQL_TRACE = FALSE;
-- 또는
ALTER SESSION SET EVENTS '10046 trace name context off';

-- 현재 Trace 상태 확인
SELECT name, value 
FROM v$parameter 
WHERE name = 'sql_trace';
