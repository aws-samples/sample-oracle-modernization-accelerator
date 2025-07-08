-- Alert Log SQL 로깅 상태 확인 및 관리

-- 1. 현재 Event 설정 확인
SELECT name, value 
FROM v$parameter 
WHERE name LIKE '%event%' OR name LIKE '%trace%';

-- 2. Alert Log 위치 확인
SELECT value 
FROM v$parameter 
WHERE name = 'background_dump_dest'
UNION ALL
SELECT value 
FROM v$diag_info 
WHERE name = 'Diag Alert';

-- 3. 현재 활성화된 Events 확인
SELECT * FROM v$event_name WHERE name LIKE '%10928%' OR name LIKE '%10046%';

-- 4. SQL 로깅 비활성화 (필요시)
-- ALTER SYSTEM SET EVENTS '10928 trace name context off';

-- 5. Alert Log에서 SQL 확인하는 방법
-- tail -f $ORACLE_BASE/diag/rdbms/[db_name]/[instance_name]/trace/alert_[instance_name].log

-- 6. 특정 사용자만 SQL 로깅하는 Trigger
CREATE OR REPLACE TRIGGER selective_sql_logging
  AFTER LOGON ON DATABASE
BEGIN
  -- 특정 사용자나 프로그램에 대해서만 SQL 로깅 활성화
  IF USER IN ('TARGET_USER1', 'TARGET_USER2') 
     OR SYS_CONTEXT('USERENV', 'MODULE') LIKE '%MyApp%' THEN
    EXECUTE IMMEDIATE 'ALTER SESSION SET EVENTS ''10928 trace name context forever, level 1''';
  END IF;
EXCEPTION
  WHEN OTHERS THEN
    NULL;
END;
/

-- 7. 로깅 상태 모니터링
SELECT 
  sid,
  serial#,
  username,
  program,
  module,
  action,
  sql_id,
  prev_sql_id
FROM v$session 
WHERE username IS NOT NULL
  AND status = 'ACTIVE';

-- 8. Alert Log 크기 모니터링 (로깅으로 인한 크기 증가 확인)
SELECT 
  'Alert Log Size: ' || ROUND(bytes/1024/1024, 2) || ' MB' as alert_log_info
FROM v$diag_info di, 
     (SELECT SUM(bytes) bytes FROM v$log_history WHERE first_time > SYSDATE - 1);
