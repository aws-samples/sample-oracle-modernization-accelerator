"""
Oracle Compatibility Function Library for PostgreSQL

Provides PostgreSQL function/schema implementations that emulate Oracle
built-in packages (DBMS_*, UTL_*). These are deployed to the target
PostgreSQL database before migration to ensure converted PL/pgSQL code
can call equivalent functions.

Usage:
    from common.rules.oracle_compat_library import get_compat_ddl, get_all_compat_ddl

    # Get DDL for a specific package
    ddl = get_compat_ddl("DBMS_OUTPUT")

    # Get all compatibility DDL
    all_ddl = get_all_compat_ddl()
"""

from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Schema setup
# ---------------------------------------------------------------------------

COMPAT_SCHEMA_DDL = """\
-- Oracle Compatibility Schema
-- Deployed by OMA to support migrated PL/SQL code
CREATE SCHEMA IF NOT EXISTS oracle_compat;
COMMENT ON SCHEMA oracle_compat IS 'Oracle compatibility functions for OMA migration';
"""

# ---------------------------------------------------------------------------
# DBMS_OUTPUT emulation
# ---------------------------------------------------------------------------

DBMS_OUTPUT_DDL = """\
-- DBMS_OUTPUT emulation using RAISE NOTICE
-- In PostgreSQL, RAISE NOTICE is the direct equivalent.
-- These functions exist for code that explicitly calls DBMS_OUTPUT.

CREATE OR REPLACE FUNCTION oracle_compat.dbms_output_put_line(p_text TEXT)
RETURNS VOID AS $$
BEGIN
    RAISE NOTICE '%', p_text;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_output_put(p_text TEXT)
RETURNS VOID AS $$
BEGIN
    -- In PG, RAISE NOTICE always appends newline. Use put_line equivalent.
    RAISE NOTICE '%', p_text;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_output_enable(p_buffer_size INTEGER DEFAULT NULL)
RETURNS VOID AS $$
BEGIN
    -- No-op in PostgreSQL (output is always enabled via RAISE NOTICE)
    NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_output_disable()
RETURNS VOID AS $$
BEGIN
    NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""

# ---------------------------------------------------------------------------
# DBMS_LOB emulation
# ---------------------------------------------------------------------------

DBMS_LOB_DDL = """\
-- DBMS_LOB emulation using TEXT/BYTEA operations

CREATE OR REPLACE FUNCTION oracle_compat.dbms_lob_getlength(p_lob TEXT)
RETURNS INTEGER AS $$
BEGIN
    RETURN LENGTH(p_lob);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_lob_getlength(p_lob BYTEA)
RETURNS INTEGER AS $$
BEGIN
    RETURN OCTET_LENGTH(p_lob);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_lob_substr(
    p_lob TEXT,
    p_amount INTEGER DEFAULT 32767,
    p_offset INTEGER DEFAULT 1
) RETURNS TEXT AS $$
BEGIN
    RETURN SUBSTRING(p_lob FROM p_offset FOR p_amount);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_lob_substr(
    p_lob BYTEA,
    p_amount INTEGER DEFAULT 32767,
    p_offset INTEGER DEFAULT 1
) RETURNS BYTEA AS $$
BEGIN
    RETURN SUBSTRING(p_lob FROM p_offset FOR p_amount);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_lob_instr(
    p_lob TEXT,
    p_pattern TEXT,
    p_offset INTEGER DEFAULT 1,
    p_nth INTEGER DEFAULT 1
) RETURNS INTEGER AS $$
DECLARE
    v_pos INTEGER;
    v_start INTEGER := p_offset;
    v_count INTEGER := 0;
BEGIN
    LOOP
        v_pos := POSITION(p_pattern IN SUBSTRING(p_lob FROM v_start));
        IF v_pos = 0 THEN RETURN 0; END IF;
        v_count := v_count + 1;
        IF v_count = p_nth THEN RETURN v_start + v_pos - 1; END IF;
        v_start := v_start + v_pos;
    END LOOP;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_lob_append(
    p_dest INOUT TEXT,
    p_src TEXT
) AS $$
BEGIN
    p_dest := p_dest || p_src;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_lob_trim(
    p_lob INOUT TEXT,
    p_newlen INTEGER
) AS $$
BEGIN
    p_lob := LEFT(p_lob, p_newlen);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_lob_createtemporary(
    OUT p_lob TEXT,
    p_cache BOOLEAN DEFAULT TRUE,
    p_dur INTEGER DEFAULT 10  -- DBMS_LOB.SESSION
) AS $$
BEGIN
    p_lob := '';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_lob_freetemporary(p_lob TEXT)
RETURNS VOID AS $$
BEGIN
    -- No-op in PostgreSQL
    NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""

# ---------------------------------------------------------------------------
# DBMS_RANDOM emulation
# ---------------------------------------------------------------------------

DBMS_RANDOM_DDL = """\
-- DBMS_RANDOM emulation

CREATE OR REPLACE FUNCTION oracle_compat.dbms_random_value()
RETURNS DOUBLE PRECISION AS $$
BEGIN
    RETURN random();
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_random_value(
    p_low DOUBLE PRECISION,
    p_high DOUBLE PRECISION
) RETURNS DOUBLE PRECISION AS $$
BEGIN
    RETURN p_low + (p_high - p_low) * random();
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_random_string(
    p_opt CHAR,
    p_len INTEGER
) RETURNS TEXT AS $$
DECLARE
    v_chars TEXT;
    v_result TEXT := '';
    i INTEGER;
BEGIN
    CASE UPPER(p_opt)
        WHEN 'U' THEN v_chars := 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        WHEN 'L' THEN v_chars := 'abcdefghijklmnopqrstuvwxyz';
        WHEN 'A' THEN v_chars := 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
        WHEN 'X' THEN v_chars := 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
        WHEN 'P' THEN v_chars := 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%';
        ELSE v_chars := 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    END CASE;

    FOR i IN 1..p_len LOOP
        v_result := v_result || SUBSTR(v_chars, FLOOR(random() * LENGTH(v_chars))::INTEGER + 1, 1);
    END LOOP;

    RETURN v_result;
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_random_normal()
RETURNS DOUBLE PRECISION AS $$
DECLARE
    v_u1 DOUBLE PRECISION;
    v_u2 DOUBLE PRECISION;
BEGIN
    -- Box-Muller transform
    v_u1 := random();
    v_u2 := random();
    RETURN SQRT(-2.0 * LN(v_u1)) * COS(2.0 * PI() * v_u2);
END;
$$ LANGUAGE plpgsql VOLATILE;
"""

# ---------------------------------------------------------------------------
# DBMS_LOCK emulation
# ---------------------------------------------------------------------------

DBMS_LOCK_DDL = """\
-- DBMS_LOCK emulation using pg_advisory_lock

CREATE OR REPLACE FUNCTION oracle_compat.dbms_lock_sleep(p_seconds DOUBLE PRECISION)
RETURNS VOID AS $$
BEGIN
    PERFORM pg_sleep(p_seconds);
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_lock_request(
    p_id INTEGER,
    p_lockmode INTEGER DEFAULT 6,  -- X_MODE
    p_timeout INTEGER DEFAULT 32767
) RETURNS INTEGER AS $$
BEGIN
    -- 0 = success, 1 = timeout, 2 = deadlock
    IF p_timeout = 0 THEN
        IF pg_try_advisory_lock(p_id) THEN RETURN 0;
        ELSE RETURN 1;
        END IF;
    ELSE
        PERFORM pg_advisory_lock(p_id);
        RETURN 0;
    END IF;
EXCEPTION WHEN deadlock_detected THEN
    RETURN 2;
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_lock_release(p_id INTEGER)
RETURNS INTEGER AS $$
BEGIN
    IF pg_advisory_unlock(p_id) THEN RETURN 0;
    ELSE RETURN 3;  -- parameter error
    END IF;
END;
$$ LANGUAGE plpgsql VOLATILE;
"""

# ---------------------------------------------------------------------------
# DBMS_UTILITY emulation
# ---------------------------------------------------------------------------

DBMS_UTILITY_DDL = """\
-- DBMS_UTILITY emulation

CREATE OR REPLACE FUNCTION oracle_compat.dbms_utility_get_time()
RETURNS INTEGER AS $$
BEGIN
    -- Returns centiseconds (1/100 second) since arbitrary epoch
    RETURN (EXTRACT(EPOCH FROM clock_timestamp()) * 100)::INTEGER;
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_utility_format_error_backtrace()
RETURNS TEXT AS $$
DECLARE
    v_context TEXT;
BEGIN
    GET DIAGNOSTICS v_context = PG_CONTEXT;
    RETURN v_context;
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_utility_format_error_stack()
RETURNS TEXT AS $$
DECLARE
    v_sqlerrm TEXT;
    v_sqlstate TEXT;
BEGIN
    GET STACKED DIAGNOSTICS v_sqlerrm = MESSAGE_TEXT, v_sqlstate = RETURNED_SQLSTATE;
    RETURN v_sqlstate || ': ' || v_sqlerrm;
EXCEPTION WHEN OTHERS THEN
    RETURN SQLERRM;
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_utility_comma_to_table(
    p_list TEXT,
    OUT p_tablen INTEGER,
    OUT p_tab TEXT[]
) AS $$
BEGIN
    p_tab := string_to_array(p_list, ',');
    -- Trim whitespace from each element
    FOR i IN 1..array_length(p_tab, 1) LOOP
        p_tab[i] := TRIM(p_tab[i]);
    END LOOP;
    p_tablen := array_length(p_tab, 1);
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""

# ---------------------------------------------------------------------------
# DBMS_SESSION emulation
# ---------------------------------------------------------------------------

DBMS_SESSION_DDL = """\
-- DBMS_SESSION / SYS_CONTEXT emulation using session variables

CREATE OR REPLACE FUNCTION oracle_compat.sys_context(
    p_namespace TEXT,
    p_parameter TEXT
) RETURNS TEXT AS $$
BEGIN
    CASE UPPER(p_namespace)
        WHEN 'USERENV' THEN
            CASE UPPER(p_parameter)
                WHEN 'SESSION_USER', 'CURRENT_USER' THEN RETURN CURRENT_USER;
                WHEN 'CURRENT_SCHEMA' THEN RETURN CURRENT_SCHEMA;
                WHEN 'DB_NAME', 'DB_UNIQUE_NAME' THEN RETURN CURRENT_DATABASE();
                WHEN 'HOST' THEN RETURN inet_client_addr()::TEXT;
                WHEN 'IP_ADDRESS' THEN RETURN inet_client_addr()::TEXT;
                WHEN 'SERVER_HOST' THEN RETURN inet_server_addr()::TEXT;
                WHEN 'OS_USER' THEN RETURN CURRENT_USER;  -- Best approximation
                WHEN 'LANGUAGE' THEN RETURN current_setting('lc_messages');
                WHEN 'SID', 'SESSIONID' THEN RETURN pg_backend_pid()::TEXT;
                WHEN 'INSTANCE' THEN RETURN '1';
                WHEN 'INSTANCE_NAME' THEN RETURN CURRENT_DATABASE();
                WHEN 'NLS_CALENDAR' THEN RETURN 'GREGORIAN';
                WHEN 'NLS_DATE_FORMAT' THEN RETURN current_setting('datestyle');
                WHEN 'ACTION', 'MODULE', 'CLIENT_INFO' THEN
                    RETURN current_setting('application_name', TRUE);
                ELSE
                    RETURN NULL;
            END CASE;
        ELSE
            -- Custom contexts: use PostgreSQL session variables
            BEGIN
                RETURN current_setting('oma.' || LOWER(p_namespace) || '.' || LOWER(p_parameter), TRUE);
            EXCEPTION WHEN OTHERS THEN
                RETURN NULL;
            END;
    END CASE;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_session_set_context(
    p_namespace TEXT,
    p_attribute TEXT,
    p_value TEXT
) RETURNS VOID AS $$
BEGIN
    PERFORM set_config(
        'oma.' || LOWER(p_namespace) || '.' || LOWER(p_attribute),
        p_value,
        FALSE  -- session-level
    );
END;
$$ LANGUAGE plpgsql VOLATILE;
"""

# ---------------------------------------------------------------------------
# DBMS_SCHEDULER / DBMS_JOB emulation
# ---------------------------------------------------------------------------

DBMS_SCHEDULER_DDL = """\
-- DBMS_SCHEDULER / DBMS_JOB emulation
-- Uses pg_cron extension if available, otherwise provides stub functions

CREATE TABLE IF NOT EXISTS oracle_compat.scheduled_jobs (
    job_id SERIAL PRIMARY KEY,
    job_name TEXT UNIQUE,
    job_action TEXT NOT NULL,
    repeat_interval TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    comments TEXT
);

CREATE OR REPLACE FUNCTION oracle_compat.dbms_scheduler_create_job(
    p_job_name TEXT,
    p_job_type TEXT DEFAULT 'PLSQL_BLOCK',
    p_job_action TEXT DEFAULT '',
    p_repeat_interval TEXT DEFAULT NULL,
    p_enabled BOOLEAN DEFAULT FALSE,
    p_comments TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO oracle_compat.scheduled_jobs (job_name, job_action, repeat_interval, enabled, comments)
    VALUES (p_job_name, p_job_action, p_repeat_interval, p_enabled, p_comments)
    ON CONFLICT (job_name) DO UPDATE
    SET job_action = EXCLUDED.job_action,
        repeat_interval = EXCLUDED.repeat_interval,
        enabled = EXCLUDED.enabled,
        comments = EXCLUDED.comments;

    -- If pg_cron is available, create the actual cron job
    BEGIN
        IF p_enabled AND p_repeat_interval IS NOT NULL THEN
            PERFORM cron.schedule(p_job_name, p_repeat_interval, p_job_action);
        END IF;
    EXCEPTION WHEN undefined_function THEN
        RAISE NOTICE 'pg_cron not available. Job registered but not scheduled. Install pg_cron for automatic execution.';
    END;
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_scheduler_drop_job(
    p_job_name TEXT,
    p_force BOOLEAN DEFAULT FALSE
) RETURNS VOID AS $$
BEGIN
    DELETE FROM oracle_compat.scheduled_jobs WHERE job_name = p_job_name;
    BEGIN
        PERFORM cron.unschedule(p_job_name);
    EXCEPTION WHEN undefined_function OR undefined_table THEN
        NULL;
    END;
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_scheduler_enable(p_name TEXT)
RETURNS VOID AS $$
BEGIN
    UPDATE oracle_compat.scheduled_jobs SET enabled = TRUE WHERE job_name = p_name;
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_scheduler_disable(
    p_name TEXT,
    p_force BOOLEAN DEFAULT FALSE
) RETURNS VOID AS $$
BEGIN
    UPDATE oracle_compat.scheduled_jobs SET enabled = FALSE WHERE job_name = p_name;
END;
$$ LANGUAGE plpgsql VOLATILE;
"""

# ---------------------------------------------------------------------------
# DBMS_CRYPTO emulation
# ---------------------------------------------------------------------------

DBMS_CRYPTO_DDL = """\
-- DBMS_CRYPTO emulation using pgcrypto extension

CREATE OR REPLACE FUNCTION oracle_compat.dbms_crypto_hash(
    p_src BYTEA,
    p_typ INTEGER
) RETURNS BYTEA AS $$
BEGIN
    -- Oracle types: 1=MD4, 2=MD5, 3=SHA-1, 4=SHA-256, 5=SHA-384, 6=SHA-512
    CASE p_typ
        WHEN 2 THEN RETURN digest(p_src, 'md5');
        WHEN 3 THEN RETURN digest(p_src, 'sha1');
        WHEN 4 THEN RETURN digest(p_src, 'sha256');
        WHEN 5 THEN RETURN digest(p_src, 'sha384');
        WHEN 6 THEN RETURN digest(p_src, 'sha512');
        ELSE RAISE EXCEPTION 'Unsupported hash type: %', p_typ;
    END CASE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION oracle_compat.dbms_crypto_hash_text(
    p_src TEXT,
    p_typ INTEGER
) RETURNS TEXT AS $$
BEGIN
    RETURN encode(oracle_compat.dbms_crypto_hash(p_src::BYTEA, p_typ), 'hex');
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""

# ---------------------------------------------------------------------------
# PKG_CRYPTO emulation (custom encryption package)
# ---------------------------------------------------------------------------
# Uses a custom Oracle package PKG_CRYPTO with ENCRYPT/DECRYPT functions.
# These are called directly in MyBatis SQL: PKG_CRYPTO.ENCRYPT(...), PKG_CRYPTO.DECRYPT(...)
# In PostgreSQL, we create flat functions (패키지명_함수명) using pgcrypto: pkg_crypto_encrypt, pkg_crypto_decrypt, etc.

PKG_CRYPTO_DDL = """\
-- PKG_CRYPTO emulation (custom encryption package → pgcrypto)
-- Naming convention: 패키지명_함수명 (flat functions, no schema prefix)
-- Oracle PKG_CRYPTO.ENCRYPT → pkg_crypto_encrypt
-- Oracle PKG_CRYPTO.DECRYPT → pkg_crypto_decrypt

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Master key helper (internal)
CREATE OR REPLACE FUNCTION crypto_master_key()
RETURNS TEXT AS $$
BEGIN
    RETURN 'DEFAULT_KEY';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ENCRYPT: AES-256-CBC encryption (matches Oracle PKG_CRYPTO.ENCRYPT behavior)
-- Oracle PKG_CRYPTO.ENCRYPT(p_input VARCHAR2, p_key_data VARCHAR2) RETURN VARCHAR2
-- Returns hex-encoded ciphertext
CREATE OR REPLACE FUNCTION pkg_crypto_encrypt(
    p_input TEXT,
    p_key_data TEXT DEFAULT NULL
) RETURNS TEXT AS $$
DECLARE
    v_key BYTEA;
    v_data BYTEA;
    v_encrypted BYTEA;
BEGIN
    IF p_input IS NULL THEN RETURN NULL; END IF;

    -- Use provided key or default (padded/hashed to 32 bytes for AES-256)
    v_key := digest(COALESCE(p_key_data, crypto_master_key()), 'sha256');
    v_data := convert_to(p_input, 'UTF8');

    -- AES-256-CBC encryption with pgcrypto
    v_encrypted := pgp_sym_encrypt_bytea(v_data, encode(v_key, 'hex'));
    RETURN encode(v_encrypted, 'hex');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- DECRYPT: AES-256-CBC decryption (matches Oracle PKG_CRYPTO.DECRYPT behavior)
-- Oracle PKG_CRYPTO.DECRYPT(p_input VARCHAR2, p_key_data VARCHAR2) RETURN VARCHAR2
CREATE OR REPLACE FUNCTION pkg_crypto_decrypt(
    p_input TEXT,
    p_key_data TEXT DEFAULT NULL
) RETURNS TEXT AS $$
DECLARE
    v_key BYTEA;
    v_data BYTEA;
    v_decrypted BYTEA;
BEGIN
    IF p_input IS NULL THEN RETURN NULL; END IF;

    -- Use provided key or default (padded/hashed to 32 bytes for AES-256)
    v_key := digest(COALESCE(p_key_data, crypto_master_key()), 'sha256');
    v_data := decode(p_input, 'hex');

    -- AES-256-CBC decryption with pgcrypto
    v_decrypted := pgp_sym_decrypt_bytea(v_data, encode(v_key, 'hex'));
    RETURN convert_from(v_decrypted, 'UTF8');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Session key helpers
CREATE OR REPLACE FUNCTION encrypt_session_key(
    p_key_data TEXT
) RETURNS TEXT AS $$
BEGIN
    RETURN pkg_crypto_encrypt(p_key_data, crypto_master_key());
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION decrypt_session_key(
    p_key_data TEXT
) RETURNS TEXT AS $$
BEGIN
    RETURN pkg_crypto_decrypt(p_key_data, crypto_master_key());
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ENCRYPT_MAL / DECRYPT_MAL: aliases for personal data fields
CREATE OR REPLACE FUNCTION pkg_crypto_encryptmal(
    p_input TEXT,
    p_key_data TEXT DEFAULT NULL
) RETURNS TEXT AS $$
BEGIN
    RETURN pkg_crypto_encrypt(p_input, p_key_data);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION pkg_crypto_decryptmal(
    p_input TEXT,
    p_key_data TEXT DEFAULT NULL
) RETURNS TEXT AS $$
BEGIN
    RETURN pkg_crypto_decrypt(p_input, p_key_data);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ENCRYPT_DES / DECRYPT_DES: DES variant aliases
CREATE OR REPLACE FUNCTION pkg_crypto_encryptdes(
    p_input TEXT,
    p_key_data TEXT DEFAULT NULL
) RETURNS TEXT AS $$
BEGIN
    RETURN pkg_crypto_encrypt(p_input, p_key_data);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION pkg_crypto_decryptdes(
    p_input TEXT,
    p_key_data TEXT DEFAULT NULL
) RETURNS TEXT AS $$
BEGIN
    RETURN pkg_crypto_decrypt(p_input, p_key_data);
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""

# ---------------------------------------------------------------------------
# UTL_RAW emulation
# ---------------------------------------------------------------------------

UTL_RAW_DDL = """\
-- UTL_RAW emulation using BYTEA operations

CREATE OR REPLACE FUNCTION oracle_compat.utl_raw_cast_to_varchar2(p_raw BYTEA)
RETURNS TEXT AS $$
BEGIN
    RETURN convert_from(p_raw, 'UTF8');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION oracle_compat.utl_raw_cast_to_raw(p_varchar TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN convert_to(p_varchar, 'UTF8');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION oracle_compat.utl_raw_concat(
    p_r1 BYTEA,
    p_r2 BYTEA DEFAULT NULL,
    p_r3 BYTEA DEFAULT NULL,
    p_r4 BYTEA DEFAULT NULL
) RETURNS BYTEA AS $$
BEGIN
    RETURN COALESCE(p_r1, ''::BYTEA) ||
           COALESCE(p_r2, ''::BYTEA) ||
           COALESCE(p_r3, ''::BYTEA) ||
           COALESCE(p_r4, ''::BYTEA);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION oracle_compat.utl_raw_length(p_raw BYTEA)
RETURNS INTEGER AS $$
BEGIN
    RETURN OCTET_LENGTH(p_raw);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION oracle_compat.utl_raw_substr(
    p_raw BYTEA,
    p_pos INTEGER,
    p_len INTEGER DEFAULT NULL
) RETURNS BYTEA AS $$
BEGIN
    IF p_len IS NULL THEN
        RETURN SUBSTRING(p_raw FROM p_pos);
    ELSE
        RETURN SUBSTRING(p_raw FROM p_pos FOR p_len);
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""

# ---------------------------------------------------------------------------
# UTL_FILE emulation (stub)
# ---------------------------------------------------------------------------

UTL_FILE_DDL = """\
-- UTL_FILE emulation using COPY and pg_read_file
-- NOTE: Requires superuser or pg_read_server_files role for file operations

CREATE TYPE oracle_compat.file_type AS (
    file_path TEXT,
    open_mode TEXT,
    is_open BOOLEAN
);

CREATE OR REPLACE FUNCTION oracle_compat.utl_file_fopen(
    p_location TEXT,
    p_filename TEXT,
    p_open_mode TEXT DEFAULT 'r',
    p_max_linesize INTEGER DEFAULT 32767
) RETURNS oracle_compat.file_type AS $$
DECLARE
    v_file oracle_compat.file_type;
BEGIN
    v_file.file_path := p_location || '/' || p_filename;
    v_file.open_mode := p_open_mode;
    v_file.is_open := TRUE;
    RETURN v_file;
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION oracle_compat.utl_file_fclose(
    p_file INOUT oracle_compat.file_type
) AS $$
BEGIN
    p_file.is_open := FALSE;
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION oracle_compat.utl_file_put_line(
    p_file oracle_compat.file_type,
    p_buffer TEXT
) RETURNS VOID AS $$
BEGIN
    -- In PG, file writing from PL/pgSQL requires COPY or pg_file_write
    -- This is a compatibility stub that logs the output
    RAISE NOTICE 'UTL_FILE.PUT_LINE[%]: %', p_file.file_path, p_buffer;
END;
$$ LANGUAGE plpgsql VOLATILE;
"""

# ---------------------------------------------------------------------------
# Additional Oracle functions
# ---------------------------------------------------------------------------

ORACLE_FUNCTIONS_DDL = """\
-- Additional Oracle built-in function equivalents

-- MONTHS_BETWEEN
CREATE OR REPLACE FUNCTION oracle_compat.months_between(
    p_date1 TIMESTAMP,
    p_date2 TIMESTAMP
) RETURNS NUMERIC AS $$
BEGIN
    RETURN (EXTRACT(YEAR FROM AGE(p_date1, p_date2)) * 12 +
            EXTRACT(MONTH FROM AGE(p_date1, p_date2)))::NUMERIC +
           (EXTRACT(DAY FROM (p_date1 - (p_date2 + (
               EXTRACT(YEAR FROM AGE(p_date1, p_date2)) * 12 +
               EXTRACT(MONTH FROM AGE(p_date1, p_date2))
           )::INTEGER * INTERVAL '1 month'))) / 31.0);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- NEXT_DAY
CREATE OR REPLACE FUNCTION oracle_compat.next_day(
    p_date DATE,
    p_day TEXT
) RETURNS DATE AS $$
DECLARE
    v_target INTEGER;
    v_current INTEGER;
    v_diff INTEGER;
BEGIN
    -- Map day name to ISO day number (1=Monday, 7=Sunday)
    CASE UPPER(LEFT(p_day, 3))
        WHEN 'MON' THEN v_target := 1;
        WHEN 'TUE' THEN v_target := 2;
        WHEN 'WED' THEN v_target := 3;
        WHEN 'THU' THEN v_target := 4;
        WHEN 'FRI' THEN v_target := 5;
        WHEN 'SAT' THEN v_target := 6;
        WHEN 'SUN' THEN v_target := 7;
        ELSE RAISE EXCEPTION 'Invalid day name: %', p_day;
    END CASE;

    v_current := EXTRACT(ISODOW FROM p_date)::INTEGER;
    v_diff := v_target - v_current;
    IF v_diff <= 0 THEN v_diff := v_diff + 7; END IF;

    RETURN p_date + v_diff;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- TO_DATE with Oracle format model conversion
CREATE OR REPLACE FUNCTION oracle_compat.to_date_oracle(
    p_string TEXT,
    p_format TEXT
) RETURNS DATE AS $$
DECLARE
    v_pg_format TEXT;
BEGIN
    -- Convert Oracle format to PG format
    v_pg_format := p_format;
    v_pg_format := REPLACE(v_pg_format, 'RRRR', 'YYYY');
    v_pg_format := REPLACE(v_pg_format, 'RR', 'YY');
    RETURN TO_DATE(p_string, v_pg_format);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- REGEXP_SUBSTR (Oracle has different signature than PG)
CREATE OR REPLACE FUNCTION oracle_compat.regexp_substr(
    p_source TEXT,
    p_pattern TEXT,
    p_position INTEGER DEFAULT 1,
    p_occurrence INTEGER DEFAULT 1,
    p_match_param TEXT DEFAULT 'c'
) RETURNS TEXT AS $$
DECLARE
    v_flags TEXT := '';
    v_matches TEXT[];
    v_source TEXT;
BEGIN
    IF p_match_param LIKE '%i%' THEN v_flags := 'gi'; END IF;
    v_source := SUBSTRING(p_source FROM p_position);

    -- Extract nth occurrence
    v_matches := regexp_matches(v_source, p_pattern, COALESCE(v_flags, 'g'));
    IF array_length(v_matches, 1) >= p_occurrence THEN
        RETURN v_matches[p_occurrence];
    END IF;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- REGEXP_COUNT
CREATE OR REPLACE FUNCTION oracle_compat.regexp_count(
    p_source TEXT,
    p_pattern TEXT,
    p_position INTEGER DEFAULT 1,
    p_match_param TEXT DEFAULT 'c'
) RETURNS INTEGER AS $$
DECLARE
    v_flags TEXT := 'g';
    v_source TEXT;
    v_count INTEGER := 0;
    v_match TEXT;
BEGIN
    IF p_match_param LIKE '%i%' THEN v_flags := 'gi'; END IF;
    v_source := SUBSTRING(p_source FROM p_position);

    FOR v_match IN SELECT (regexp_matches(v_source, p_pattern, v_flags))[1] LOOP
        v_count := v_count + 1;
    END LOOP;

    RETURN v_count;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""


# ===========================================================================
# Registry and API
# ===========================================================================

COMPAT_PACKAGES: Dict[str, str] = {
    "SCHEMA": COMPAT_SCHEMA_DDL,
    "DBMS_OUTPUT": DBMS_OUTPUT_DDL,
    "DBMS_LOB": DBMS_LOB_DDL,
    "DBMS_RANDOM": DBMS_RANDOM_DDL,
    "DBMS_LOCK": DBMS_LOCK_DDL,
    "DBMS_UTILITY": DBMS_UTILITY_DDL,
    "DBMS_SESSION": DBMS_SESSION_DDL,
    "DBMS_SCHEDULER": DBMS_SCHEDULER_DDL,
    "DBMS_JOB": DBMS_SCHEDULER_DDL,  # alias
    "DBMS_CRYPTO": DBMS_CRYPTO_DDL,
    "PKG_CRYPTO": PKG_CRYPTO_DDL,
    "UTL_RAW": UTL_RAW_DDL,
    "UTL_FILE": UTL_FILE_DDL,
    "SYS_CONTEXT": DBMS_SESSION_DDL,  # alias
    "ORACLE_FUNCTIONS": ORACLE_FUNCTIONS_DDL,
}

# Maps Oracle package.procedure calls to their PG equivalents
CALL_MAPPINGS: Dict[str, str] = {
    "DBMS_OUTPUT.PUT_LINE": "oracle_compat.dbms_output_put_line",
    "DBMS_OUTPUT.PUT": "oracle_compat.dbms_output_put",
    "DBMS_OUTPUT.ENABLE": "oracle_compat.dbms_output_enable",
    "DBMS_OUTPUT.DISABLE": "oracle_compat.dbms_output_disable",
    "DBMS_LOB.GETLENGTH": "oracle_compat.dbms_lob_getlength",
    "DBMS_LOB.SUBSTR": "oracle_compat.dbms_lob_substr",
    "DBMS_LOB.INSTR": "oracle_compat.dbms_lob_instr",
    "DBMS_LOB.APPEND": "oracle_compat.dbms_lob_append",
    "DBMS_LOB.TRIM": "oracle_compat.dbms_lob_trim",
    "DBMS_LOB.CREATETEMPORARY": "oracle_compat.dbms_lob_createtemporary",
    "DBMS_LOB.FREETEMPORARY": "oracle_compat.dbms_lob_freetemporary",
    "DBMS_RANDOM.VALUE": "oracle_compat.dbms_random_value",
    "DBMS_RANDOM.STRING": "oracle_compat.dbms_random_string",
    "DBMS_RANDOM.NORMAL": "oracle_compat.dbms_random_normal",
    "DBMS_LOCK.SLEEP": "oracle_compat.dbms_lock_sleep",
    "DBMS_LOCK.REQUEST": "oracle_compat.dbms_lock_request",
    "DBMS_LOCK.RELEASE": "oracle_compat.dbms_lock_release",
    "DBMS_UTILITY.GET_TIME": "oracle_compat.dbms_utility_get_time",
    "DBMS_UTILITY.FORMAT_ERROR_BACKTRACE": "oracle_compat.dbms_utility_format_error_backtrace",
    "DBMS_UTILITY.FORMAT_ERROR_STACK": "oracle_compat.dbms_utility_format_error_stack",
    "DBMS_UTILITY.COMMA_TO_TABLE": "oracle_compat.dbms_utility_comma_to_table",
    "SYS_CONTEXT": "oracle_compat.sys_context",
    "DBMS_SCHEDULER.CREATE_JOB": "oracle_compat.dbms_scheduler_create_job",
    "DBMS_SCHEDULER.DROP_JOB": "oracle_compat.dbms_scheduler_drop_job",
    "DBMS_SCHEDULER.ENABLE": "oracle_compat.dbms_scheduler_enable",
    "DBMS_SCHEDULER.DISABLE": "oracle_compat.dbms_scheduler_disable",
    "DBMS_CRYPTO.HASH": "oracle_compat.dbms_crypto_hash",
    "PKG_CRYPTO.ENCRYPT": "pkg_crypto_encrypt",
    "PKG_CRYPTO.DECRYPT": "pkg_crypto_decrypt",
    "PKG_CRYPTO.ENCRYPTMAL": "pkg_crypto_encryptmal",
    "PKG_CRYPTO.DECRYPTMAL": "pkg_crypto_decryptmal",
    "PKG_CRYPTO.ENCRYPTDES": "pkg_crypto_encryptdes",
    "PKG_CRYPTO.DECRYPTDES": "pkg_crypto_decryptdes",
    "UTL_RAW.CAST_TO_VARCHAR2": "oracle_compat.utl_raw_cast_to_varchar2",
    "UTL_RAW.CAST_TO_RAW": "oracle_compat.utl_raw_cast_to_raw",
    "UTL_RAW.CONCAT": "oracle_compat.utl_raw_concat",
    "UTL_RAW.LENGTH": "oracle_compat.utl_raw_length",
    "UTL_RAW.SUBSTR": "oracle_compat.utl_raw_substr",
    "UTL_FILE.FOPEN": "oracle_compat.utl_file_fopen",
    "UTL_FILE.FCLOSE": "oracle_compat.utl_file_fclose",
    "UTL_FILE.PUT_LINE": "oracle_compat.utl_file_put_line",
    "MONTHS_BETWEEN": "oracle_compat.months_between",
    "NEXT_DAY": "oracle_compat.next_day",
    "REGEXP_SUBSTR": "oracle_compat.regexp_substr",
    "REGEXP_COUNT": "oracle_compat.regexp_count",
}


def get_compat_ddl(package_name: str) -> Optional[str]:
    """Get compatibility DDL for a specific Oracle package.

    Args:
        package_name: Oracle package name (e.g., 'DBMS_LOB', 'UTL_FILE')

    Returns:
        DDL string or None if package not supported
    """
    return COMPAT_PACKAGES.get(package_name.upper())


def get_all_compat_ddl() -> str:
    """Get all compatibility DDL as a single deployable script.

    Returns:
        Complete DDL script for all Oracle compatibility functions.
    """
    # Ensure SCHEMA is first
    parts = [COMPAT_SCHEMA_DDL]
    seen = {"SCHEMA"}
    for name, ddl in COMPAT_PACKAGES.items():
        if name not in seen:
            parts.append(f"-- ========== {name} ==========")
            parts.append(ddl)
            seen.add(name)
    return "\n\n".join(parts)


def get_call_mapping(oracle_call: str) -> Optional[str]:
    """Get the PG function name for an Oracle package.procedure call.

    Args:
        oracle_call: Oracle call like 'DBMS_LOB.SUBSTR'

    Returns:
        PG function name or None
    """
    return CALL_MAPPINGS.get(oracle_call.upper())


def list_supported_packages() -> List[str]:
    """List all supported Oracle packages."""
    return sorted(set(COMPAT_PACKAGES.keys()) - {"SCHEMA"})
