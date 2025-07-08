-- 사용자 실행 SQL을 Alert Log에 기록하는 방법

-- 방법 1: Event 10928 사용 (가장 직접적인 방법)
-- 모든 SQL 문장을 Alert Log에 기록
ALTER SYSTEM SET EVENTS '10928 trace name context forever, level 1';

-- 비활성화
-- ALTER SYSTEM SET EVENTS '10928 trace name context off';

-- 방법 2: Event 10046과 함께 Alert Log 리다이렉션
-- SQL 추적을 Alert Log로 보내기
ALTER SYSTEM SET EVENTS '10046 trace name context forever, level 1';
ALTER SYSTEM SET "_trace_files_public" = TRUE;

-- 방법 3: Logon Trigger + DBMS_SYSTEM.KSDWRT 사용
CREATE OR REPLACE TRIGGER log_sql_to_alert
  AFTER LOGON ON DATABASE
DECLARE
  v_sql VARCHAR2(4000);
BEGIN
  -- 현재 세션에서 SQL 추적 활성화
  EXECUTE IMMEDIATE 'ALTER SESSION SET EVENTS ''10928 trace name context forever, level 1''';
EXCEPTION
  WHEN OTHERS THEN
    NULL;
END;
/

-- 방법 4: Fine Grained Auditing (FGA) 사용
-- 모든 테이블에 대한 SELECT/INSERT/UPDATE/DELETE 감사
BEGIN
  FOR rec IN (SELECT table_name FROM user_tables) LOOP
    BEGIN
      DBMS_FGA.ADD_POLICY(
        object_schema   => USER,
        object_name     => rec.table_name,
        policy_name     => 'AUDIT_' || rec.table_name,
        audit_condition => NULL,
        audit_column    => NULL,
        handler_schema  => NULL,
        handler_module  => NULL,
        enable          => TRUE,
        statement_types => 'SELECT,INSERT,UPDATE,DELETE',
        audit_trail     => DBMS_FGA.DB + DBMS_FGA.EXTENDED
      );
    EXCEPTION
      WHEN OTHERS THEN
        NULL; -- 이미 존재하는 정책 무시
    END;
  END LOOP;
END;
/
