-- TRC 파일 위치 확인
SELECT name, value 
FROM v$parameter 
WHERE name IN ('user_dump_dest', 'diagnostic_dest', 'background_dump_dest');

-- 현재 세션의 TRC 파일명 확인
SELECT value 
FROM v$diag_info 
WHERE name = 'Default Trace File';
