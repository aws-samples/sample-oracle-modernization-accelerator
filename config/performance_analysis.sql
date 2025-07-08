-- 현재 실행 중인 SQL 모니터링
SELECT 
    s.sid,
    s.serial#,
    s.username,
    s.program,
    s.machine,
    sq.sql_text,
    s.last_call_et,
    s.status
FROM v$session s, v$sql sq
WHERE s.sql_address = sq.address
  AND s.sql_hash_value = sq.hash_value
  AND s.status = 'ACTIVE'
  AND s.username IS NOT NULL;

-- Top SQL by Elapsed Time
SELECT 
    sql_id,
    child_number,
    executions,
    elapsed_time/1000000 as elapsed_sec,
    cpu_time/1000000 as cpu_sec,
    disk_reads,
    buffer_gets,
    rows_processed,
    SUBSTR(sql_text, 1, 100) as sql_text_preview
FROM v$sql
WHERE elapsed_time > 0
ORDER BY elapsed_time DESC
FETCH FIRST 10 ROWS ONLY;

-- Wait Events 분석
SELECT 
    event,
    total_waits,
    total_timeouts,
    time_waited/100 as time_waited_sec,
    average_wait
FROM v$system_event
WHERE event NOT LIKE 'SQL*Net%'
  AND event NOT LIKE '%timer%'
  AND event NOT LIKE '%idle%'
ORDER BY time_waited DESC
FETCH FIRST 15 ROWS ONLY;
