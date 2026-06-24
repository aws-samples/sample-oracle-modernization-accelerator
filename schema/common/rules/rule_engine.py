"""
Oracle to PostgreSQL Rule Application Engine

This module applies static transformation rules to convert Oracle SQL to PostgreSQL.
It implements the conversion methodology from postgreRules.md with strict ordering:

1. DECODE → CASE WHEN conversion (parenthesis-aware)
2. Oracle function conversions
3. Syntax conversions (including PL/SQL patterns)
4. Parameter casting (metadata-driven)

NOTE: PostgreSQL natively supports || for string concatenation, so NO conversion needed.
"""

import re
from enum import Enum
from typing import List, Tuple, Dict, Optional, Set
from dataclasses import dataclass

# Try to import from postgresql/mysql specific rules, fallback to None
try:
    from postgresql.rules.static_rules import (
        FUNCTION_MAPPINGS,
        DATA_TYPE_MAPPINGS,
        SYNTAX_RULES,
        JDBC_TYPE_MAPPINGS,
        MYBATIS_TYPE_MAPPINGS,
        get_pg_cast_syntax,
    )
except ImportError:
    try:
        from mysql.rules.static_rules import (
            FUNCTION_MAPPINGS,
            DATA_TYPE_MAPPINGS,
            SYNTAX_RULES,
            JDBC_TYPE_MAPPINGS,
            MYBATIS_TYPE_MAPPINGS,
            get_pg_cast_syntax,
        )
    except ImportError:
        # Fallback: empty mappings
        FUNCTION_MAPPINGS = {}
        DATA_TYPE_MAPPINGS = {}
        SYNTAX_RULES = []
        JDBC_TYPE_MAPPINGS = {}
        MYBATIS_TYPE_MAPPINGS = {}
        def get_pg_cast_syntax(x): return x

from .patterns import OraclePatternDetector, PatternComplexity

# Try to import oracle_compat_library
try:
    from postgresql.rules.oracle_compat_library import CALL_MAPPINGS
except ImportError:
    try:
        from mysql.rules.oracle_compat_library import CALL_MAPPINGS
    except ImportError:
        CALL_MAPPINGS = {}


class Complexity(Enum):
    """Overall SQL complexity assessment."""
    SIMPLE = "SIMPLE"      # Static rules only
    MODERATE = "MODERATE"  # Needs LLM
    COMPLEX = "COMPLEX"    # Needs Swarm


@dataclass
class AppliedRule:
    """Record of a rule application."""
    rule_name: str
    rule_type: str
    original: str
    transformed: str
    line_number: Optional[int] = None


class RuleEngine:
    """Engine for applying Oracle to PostgreSQL/MySQL conversion rules."""

    def __init__(self, metadata_path: Optional[str] = None, target_db: str = "pg"):
        """
        Initialize the rule engine.

        Args:
            metadata_path: Path to oma_metadata.txt for parameter casting
            target_db: Target database type - 'pg' for PostgreSQL, 'mysql' for MySQL
        """
        self.metadata_path = metadata_path
        self.metadata: Dict[str, str] = {}
        self.pattern_detector = OraclePatternDetector()
        self.target_db = target_db  # 'pg' or 'mysql'

        if metadata_path:
            self._load_metadata()

    def _load_metadata(self) -> None:
        """Load metadata from file for parameter casting."""
        if not self.metadata_path:
            return

        try:
            with open(self.metadata_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split('|')
                    if len(parts) >= 4:
                        schema = parts[0].strip().lower()
                        table = parts[1].strip().lower()
                        column = parts[2].strip().lower()
                        data_type = parts[3].strip().lower()

                        # Store as table.column -> data_type
                        key = f"{table}.{column}"
                        self.metadata[key] = data_type
        except FileNotFoundError:
            print(f"Warning: Metadata file not found: {self.metadata_path}")
        except Exception as e:
            print(f"Warning: Failed to load metadata: {e}")

    def apply_static_rules(self, sql: str) -> Tuple[str, List[AppliedRule]]:
        """
        Apply all static transformation rules to SQL.

        Follows strict ordering from postgreRules.md:
        1. String concatenation (PRIORITY 1)
        2. Oracle function conversions
        3. Syntax conversions
        4. Parameter casting (if metadata available)

        Args:
            sql: Original Oracle SQL

        Returns:
            Tuple of (transformed_sql, list_of_applied_rules)
        """
        transformed = sql
        applied_rules: List[AppliedRule] = []

        # STEP 1: DECODE → CASE WHEN (parenthesis-aware, must run before function replacements)
        transformed, decode_rules = self._convert_decode(transformed)
        applied_rules.extend(decode_rules)

        # STEP 2: Oracle function conversions
        transformed, func_rules = self._convert_functions(transformed)
        applied_rules.extend(func_rules)

        # STEP 3: CONNECT BY → WITH RECURSIVE
        transformed, hier_rules = self._convert_connect_by(transformed)
        applied_rules.extend(hier_rules)

        # STEP 4: Syntax conversions (including PL/SQL patterns)
        transformed, syntax_rules = self._convert_syntax(transformed)
        applied_rules.extend(syntax_rules)

        # STEP 5: PL/SQL specific conversions
        transformed, plsql_rules = self._convert_plsql_patterns(transformed)
        applied_rules.extend(plsql_rules)

        # STEP 6: Oracle package call replacements (DBMS_*, UTL_*, etc.)
        transformed, pkg_rules = self._convert_oracle_package_calls(transformed)
        applied_rules.extend(pkg_rules)

        # STEP 7: Parameter casting (if metadata available)
        if self.metadata:
            transformed, cast_rules = self._apply_parameter_casts(transformed)
            applied_rules.extend(cast_rules)

        return transformed, applied_rules

    def _find_matching_paren(self, sql: str, start: int) -> int:
        """Find the matching closing parenthesis, handling nesting and strings.

        Args:
            sql: Full SQL text
            start: Position of the opening parenthesis

        Returns:
            Position of the matching closing parenthesis, or -1 if not found
        """
        depth = 0
        in_string = False
        i = start
        while i < len(sql):
            ch = sql[i]
            if ch == "'" and not in_string:
                in_string = True
            elif ch == "'" and in_string:
                # Handle escaped quotes ''
                if i + 1 < len(sql) and sql[i + 1] == "'":
                    i += 1
                else:
                    in_string = False
            elif not in_string:
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0:
                        return i
            i += 1
        return -1

    def _split_decode_args(self, args_str: str) -> List[str]:
        """Split DECODE arguments respecting nested parentheses and strings.

        Args:
            args_str: The content between DECODE( and matching )

        Returns:
            List of argument strings
        """
        args = []
        depth = 0
        in_string = False
        current = []
        i = 0
        while i < len(args_str):
            ch = args_str[i]
            if ch == "'" and not in_string:
                in_string = True
                current.append(ch)
            elif ch == "'" and in_string:
                if i + 1 < len(args_str) and args_str[i + 1] == "'":
                    current.append("''")
                    i += 1
                else:
                    in_string = False
                    current.append(ch)
            elif not in_string:
                if ch == '(':
                    depth += 1
                    current.append(ch)
                elif ch == ')':
                    depth -= 1
                    current.append(ch)
                elif ch == ',' and depth == 0:
                    args.append(''.join(current).strip())
                    current = []
                else:
                    current.append(ch)
            else:
                current.append(ch)
            i += 1
        if current:
            args.append(''.join(current).strip())
        return args

    def _convert_decode(self, sql: str) -> Tuple[str, List[AppliedRule]]:
        """
        Convert DECODE(expr, search1, result1, ..., default) to CASE WHEN expressions.

        Uses parenthesis-aware parsing to handle nested function calls.

        Args:
            sql: SQL text

        Returns:
            Tuple of (transformed_sql, applied_rules)
        """
        applied_rules = []
        transformed = sql

        decode_re = re.compile(r'\bDECODE\s*\(', re.IGNORECASE)

        iteration = 0
        while iteration < 50:
            iteration += 1
            match = decode_re.search(transformed)
            if not match:
                break

            # Find opening paren
            paren_start = match.end() - 1  # position of '('
            paren_end = self._find_matching_paren(transformed, paren_start)
            if paren_end == -1:
                break  # Unbalanced parens, let LLM handle

            # Extract arguments
            args_str = transformed[paren_start + 1:paren_end]
            args = self._split_decode_args(args_str)

            if len(args) < 3:
                break  # Not enough args for DECODE

            expr = args[0]
            pairs = args[1:]

            # Build CASE WHEN
            case_parts = [f"CASE"]
            i = 0
            while i + 1 < len(pairs):
                search_val = pairs[i]
                result_val = pairs[i + 1]
                if search_val.strip().upper() == 'NULL':
                    case_parts.append(f" WHEN {expr} IS NULL THEN {result_val}")
                else:
                    case_parts.append(f" WHEN {expr} = {search_val} THEN {result_val}")
                i += 2

            # If odd number of remaining args, last one is the default
            if i < len(pairs):
                case_parts.append(f" ELSE {pairs[i]}")

            case_parts.append(" END")
            case_expr = ''.join(case_parts)

            original = transformed[match.start():paren_end + 1]
            transformed = transformed[:match.start()] + case_expr + transformed[paren_end + 1:]

            applied_rules.append(AppliedRule(
                rule_name="decode_to_case",
                rule_type="function",
                original=original,
                transformed=case_expr
            ))

        return transformed, applied_rules

    def _convert_connect_by(self, sql: str) -> Tuple[str, List[AppliedRule]]:
        """
        Convert Oracle CONNECT BY hierarchical queries to PostgreSQL WITH RECURSIVE.

        Handles the standard pattern:
            SELECT cols FROM table
            START WITH condition
            CONNECT BY [NOCYCLE] PRIOR parent = child
            [ORDER SIBLINGS BY col]

        Converts to:
            WITH RECURSIVE cte AS (
                SELECT cols, 1 AS level FROM table WHERE condition      -- anchor
                UNION ALL
                SELECT cols, cte.level + 1 FROM table t
                JOIN cte ON t.child = cte.parent                        -- recursive
            )
            SELECT * FROM cte [ORDER BY col]

        Also handles:
        - LEVEL pseudo-column → cte.level
        - SYS_CONNECT_BY_PATH → recursive string concatenation
        - CONNECT_BY_ROOT → anchor value carried through recursion
        - CONNECT_BY_ISLEAF → NOT EXISTS check
        - NOCYCLE → CYCLE detection clause (PG14+)
        - ORDER SIBLINGS BY → lateral ordering

        Args:
            sql: SQL text

        Returns:
            Tuple of (transformed_sql, applied_rules)
        """
        applied_rules = []
        transformed = sql

        # Detect CONNECT BY presence
        connect_by_re = re.compile(
            r'\bCONNECT\s+BY\b', re.IGNORECASE
        )
        if not connect_by_re.search(transformed):
            return transformed, applied_rules

        # Full pattern: SELECT ... FROM ... [START WITH ...] CONNECT BY [NOCYCLE] [PRIOR] ...
        # We parse the query into its component clauses
        pattern = re.compile(
            r'(?P<select>SELECT\s+.*?)'
            r'(?P<from>\bFROM\s+.*?)'
            r'(?:\bWHERE\s+(?P<where>.*?))?'
            r'(?:\bSTART\s+WITH\s+(?P<start_with>.*?))?'
            r'\bCONNECT\s+BY\s+(?P<nocycle>NOCYCLE\s+)?(?P<connect_by>.*?)'
            r'(?:\bORDER\s+SIBLINGS\s+BY\s+(?P<order_siblings>.*?))?'
            r'(?:\bORDER\s+BY\s+(?P<order_by>.*?))?'
            r'\s*$',
            re.IGNORECASE | re.DOTALL
        )

        match = pattern.match(transformed.strip())
        if not match:
            # Try simpler detection — CONNECT BY might be in the middle with WHERE after
            # Fall back to a more lenient parser
            return self._convert_connect_by_lenient(transformed)

        select_clause = match.group('select').strip()
        from_clause = match.group('from').strip()
        where_clause = (match.group('where') or '').strip()
        start_with = (match.group('start_with') or '').strip()
        nocycle = bool(match.group('nocycle'))
        connect_by = match.group('connect_by').strip()
        order_siblings = (match.group('order_siblings') or '').strip()
        order_by = (match.group('order_by') or '').strip()

        result = self._build_recursive_cte(
            select_clause, from_clause, where_clause,
            start_with, connect_by, nocycle,
            order_siblings, order_by, transformed
        )
        if result:
            transformed, rule = result
            applied_rules.append(rule)

        return transformed, applied_rules

    def _convert_connect_by_lenient(self, sql: str) -> Tuple[str, List[AppliedRule]]:
        """Lenient CONNECT BY parser for non-standard clause ordering."""
        applied_rules = []

        # Extract clauses by keyword boundaries
        upper = sql.upper()

        def find_clause(keyword: str) -> int:
            return upper.find(keyword)

        select_pos = find_clause('SELECT ')
        from_pos = find_clause(' FROM ')
        where_pos = find_clause(' WHERE ')
        start_pos = find_clause(' START WITH ')
        connect_pos = find_clause(' CONNECT BY ')
        order_sib_pos = find_clause(' ORDER SIBLINGS BY ')
        order_pos = -1
        # Find ORDER BY that isn't ORDER SIBLINGS BY
        for m in re.finditer(r'\bORDER\s+BY\b', upper):
            if m.start() != order_sib_pos + 1:
                order_pos = m.start()

        if select_pos == -1 or from_pos == -1 or connect_pos == -1:
            return sql, applied_rules

        # Build boundary list for slicing
        boundaries = sorted([
            (pos, name) for pos, name in [
                (select_pos, 'select'), (from_pos + 1, 'from'),
                (where_pos + 1, 'where'), (start_pos + 1, 'start_with'),
                (connect_pos + 1, 'connect_by'),
                (order_sib_pos + 1, 'order_siblings'),
                (order_pos, 'order_by'),
            ] if pos > 0
        ])

        clauses = {}
        for i, (pos, name) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(sql)
            raw = sql[pos:end].strip()
            # Remove the keyword prefix
            keyword_map = {
                'select': r'^SELECT\s+',
                'from': r'^FROM\s+',
                'where': r'^WHERE\s+',
                'start_with': r'^START\s+WITH\s+',
                'connect_by': r'^CONNECT\s+BY\s+(?:NOCYCLE\s+)?',
                'order_siblings': r'^ORDER\s+SIBLINGS\s+BY\s+',
                'order_by': r'^ORDER\s+BY\s+',
            }
            if name in keyword_map:
                raw = re.sub(keyword_map[name], '', raw, flags=re.IGNORECASE).strip()
            clauses[name] = raw

        select_clause = 'SELECT ' + clauses.get('select', '*')
        from_clause = 'FROM ' + clauses.get('from', '')
        where_clause = clauses.get('where', '')
        start_with = clauses.get('start_with', '')
        connect_by_raw = clauses.get('connect_by', '')
        nocycle = bool(re.search(r'\bNOCYCLE\b', sql[connect_pos:connect_pos + 30], re.IGNORECASE))
        connect_by = re.sub(r'^NOCYCLE\s+', '', connect_by_raw, flags=re.IGNORECASE).strip()
        order_siblings = clauses.get('order_siblings', '')
        order_by = clauses.get('order_by', '')

        result = self._build_recursive_cte(
            select_clause, from_clause, where_clause,
            start_with, connect_by, nocycle,
            order_siblings, order_by, sql
        )
        if result:
            sql, rule = result
            applied_rules.append(rule)

        return sql, applied_rules

    def _build_recursive_cte(
        self,
        select_clause: str,
        from_clause: str,
        where_clause: str,
        start_with: str,
        connect_by: str,
        nocycle: bool,
        order_siblings: str,
        order_by: str,
        original_sql: str,
    ) -> Optional[Tuple[str, AppliedRule]]:
        """Build WITH RECURSIVE CTE from parsed CONNECT BY components.

        Returns:
            Tuple of (new_sql, AppliedRule) or None if parsing fails.
        """
        # Parse CONNECT BY clause to extract join condition
        # Common patterns:
        #   PRIOR parent_col = child_col
        #   child_col = PRIOR parent_col
        prior_match = re.search(
            r'PRIOR\s+(\w+(?:\.\w+)?)\s*=\s*(\w+(?:\.\w+)?)',
            connect_by, re.IGNORECASE
        )
        if not prior_match:
            # Try reverse: child = PRIOR parent
            prior_match = re.search(
                r'(\w+(?:\.\w+)?)\s*=\s*PRIOR\s+(\w+(?:\.\w+)?)',
                connect_by, re.IGNORECASE
            )
            if not prior_match:
                return None  # Cannot parse CONNECT BY condition
            # In reverse form: child = PRIOR parent → parent is group(2), child is group(1)
            parent_col = self._strip_table_alias(prior_match.group(2))
            child_col = self._strip_table_alias(prior_match.group(1))
        else:
            # PRIOR parent = child → parent is group(1), child is group(2)
            parent_col = self._strip_table_alias(prior_match.group(1))
            child_col = self._strip_table_alias(prior_match.group(2))

        # Extract table name from FROM clause
        table_match = re.search(r'FROM\s+(\w+(?:\.\w+)?)\s*(\w+)?', from_clause, re.IGNORECASE)
        if not table_match:
            return None
        table_name = table_match.group(1)
        table_alias = table_match.group(2) or table_name

        # Extract column list from SELECT (clean up LEVEL, SYS_CONNECT_BY_PATH, etc.)
        col_part = re.sub(r'^SELECT\s+', '', select_clause, flags=re.IGNORECASE).strip()

        # Handle LEVEL pseudo-column
        has_level = bool(re.search(r'\bLEVEL\b', col_part, re.IGNORECASE))
        # Handle SYS_CONNECT_BY_PATH
        sys_path_match = re.search(
            r'SYS_CONNECT_BY_PATH\s*\(\s*(\w+)\s*,\s*\'([^\']*)\'\s*\)',
            col_part, re.IGNORECASE
        )
        # Handle CONNECT_BY_ROOT
        root_match = re.search(
            r'CONNECT_BY_ROOT\s+(\w+)',
            col_part, re.IGNORECASE
        )
        # Handle CONNECT_BY_ISLEAF
        has_isleaf = bool(re.search(r'\bCONNECT_BY_ISLEAF\b', col_part, re.IGNORECASE))

        # Build anchor column list
        anchor_cols = col_part
        recursive_cols = col_part

        # Replace LEVEL
        if has_level:
            anchor_cols = re.sub(r'\bLEVEL\b', '1 AS lvl', anchor_cols, flags=re.IGNORECASE)
            recursive_cols = re.sub(r'\bLEVEL\b', 'cte.lvl + 1', recursive_cols, flags=re.IGNORECASE)

        # Replace SYS_CONNECT_BY_PATH
        if sys_path_match:
            path_col = sys_path_match.group(1)
            path_sep = sys_path_match.group(2)
            anchor_path = f"'{path_sep}' || {path_col} AS path"
            recursive_path = f"cte.path || '{path_sep}' || t.{path_col}"
            anchor_cols = re.sub(
                r'SYS_CONNECT_BY_PATH\s*\([^)]+\)',
                anchor_path, anchor_cols, flags=re.IGNORECASE
            )
            recursive_cols = re.sub(
                r'SYS_CONNECT_BY_PATH\s*\([^)]+\)',
                recursive_path, recursive_cols, flags=re.IGNORECASE
            )

        # Replace CONNECT_BY_ROOT
        if root_match:
            root_col = root_match.group(1)
            anchor_cols = re.sub(
                r'CONNECT_BY_ROOT\s+\w+',
                f'{root_col} AS root_{root_col}', anchor_cols, flags=re.IGNORECASE
            )
            recursive_cols = re.sub(
                r'CONNECT_BY_ROOT\s+\w+',
                f'cte.root_{root_col}', recursive_cols, flags=re.IGNORECASE
            )

        # Replace CONNECT_BY_ISLEAF
        if has_isleaf:
            anchor_cols = re.sub(
                r'\bCONNECT_BY_ISLEAF\b',
                '0 AS is_leaf', anchor_cols, flags=re.IGNORECASE
            )
            recursive_cols = re.sub(
                r'\bCONNECT_BY_ISLEAF\b',
                '0 AS is_leaf', recursive_cols, flags=re.IGNORECASE
            )

        # Prefix recursive column references with t. for the table
        # (simple heuristic: bare column names that match aren't already qualified)
        recursive_cols_prefixed = recursive_cols
        for col_ref_m in re.finditer(r'\b(' + re.escape(table_alias) + r')\.(\w+)', recursive_cols):
            pass  # already qualified, fine
        # Replace bare table_alias references with t.
        if table_alias != table_name:
            recursive_cols_prefixed = re.sub(
                r'\b' + re.escape(table_alias) + r'\.',
                't.', recursive_cols_prefixed
            )

        # Build the anchor query (START WITH condition or all roots)
        anchor_where = start_with if start_with else f"{child_col} IS NULL"
        if where_clause:
            anchor_where = f"{anchor_where} AND {where_clause}"

        # Build the recursive join condition
        join_cond = f"t.{child_col} = cte.{parent_col}"

        # NOCYCLE support (PostgreSQL 14+)
        cycle_clause = ""
        if nocycle:
            cycle_clause = f"\nCYCLE {parent_col} SET is_cycle USING cycle_path"

        # Build final CTE
        parts = [
            f"WITH RECURSIVE cte AS (",
            f"  -- Anchor: root rows",
            f"  SELECT {anchor_cols}",
            f"  FROM {table_name} {table_alias}",
            f"  WHERE {anchor_where}",
            f"  UNION ALL",
            f"  -- Recursive: children",
            f"  SELECT {recursive_cols_prefixed}",
            f"  FROM {table_name} t",
            f"  JOIN cte ON {join_cond}",
        ]

        if where_clause:
            parts.append(f"  WHERE {where_clause}")

        parts.append(f"){cycle_clause}")

        # Final SELECT
        parts.append(f"SELECT * FROM cte")

        if order_siblings:
            parts.append(f"ORDER BY {order_siblings}")
        elif order_by:
            parts.append(f"ORDER BY {order_by}")

        new_sql = '\n'.join(parts)

        return new_sql, AppliedRule(
            rule_name="connect_by_to_recursive",
            rule_type="hierarchical",
            original=original_sql[:80] + '...' if len(original_sql) > 80 else original_sql,
            transformed=new_sql[:80] + '...' if len(new_sql) > 80 else new_sql,
        )

    @staticmethod
    def _strip_table_alias(col_ref: str) -> str:
        """Strip table alias from column reference: 'alias.col' → 'col'."""
        parts = col_ref.split('.')
        return parts[-1]

    def _convert_functions(self, sql: str) -> Tuple[str, List[AppliedRule]]:
        """
        Convert Oracle functions to PostgreSQL equivalents.

        Args:
            sql: SQL text

        Returns:
            Tuple of (transformed_sql, applied_rules)
        """
        applied_rules = []
        transformed = sql

        # Sort by priority (complex functions first to avoid partial replacements)
        function_order = [
            # Date/Time functions
            "SYSDATE", "SYSTIMESTAMP", "USER", "SYS_GUID",
            # String functions
            "NVL2", "NVL", "SUBSTR", "INSTR", "LENGTHB", "LENGTH",
            "LPAD", "RPAD", "LISTAGG", "WM_CONCAT",
            # Date arithmetic
            "ADD_MONTHS", "LAST_DAY",
            "TRUNC_DATE", "TRUNC_MONTH", "TRUNC_YEAR",
            # Sequences
            "NEXTVAL", "CURRVAL",
            # Analytical (no change but validate)
            "ROW_NUMBER", "RANK", "DENSE_RANK", "LAG", "LEAD",
        ]

        for func_name in function_order:
            if func_name not in FUNCTION_MAPPINGS:
                continue

            mapping = FUNCTION_MAPPINGS[func_name]
            func_type = mapping.get("type", "simple_replace")

            if func_type == "simple_replace":
                transformed, rules = self._apply_simple_replace(
                    transformed,
                    func_name,
                    mapping["oracle"],
                    mapping.get(self.target_db, mapping.get("pg", ""))
                )
                applied_rules.extend(rules)

            elif func_type == "regex_replace":
                transformed, rules = self._apply_regex_replace(
                    transformed,
                    func_name,
                    mapping["oracle"],
                    mapping.get(self.target_db, mapping.get("pg", ""))
                )
                applied_rules.extend(rules)

        return transformed, applied_rules

    def _convert_syntax(self, sql: str) -> Tuple[str, List[AppliedRule]]:
        """
        Convert Oracle syntax to PostgreSQL.

        Args:
            sql: SQL text

        Returns:
            Tuple of (transformed_sql, applied_rules)
        """
        applied_rules = []
        transformed = sql

        # Apply syntax rules in priority order
        syntax_order = [
            "dual_removal",
            "hint_removal",
            "procedure_call",
            "sysdate_arithmetic",
        ]

        for rule_name in syntax_order:
            if rule_name not in SYNTAX_RULES:
                continue

            rule = SYNTAX_RULES[rule_name]
            rule_type = rule.get("type", "simple_replace")

            if rule_type == "regex_replace":
                transformed, rules = self._apply_regex_replace(
                    transformed,
                    rule_name,
                    rule["oracle"],
                    rule.get(self.target_db, rule.get("pg", ""))
                )
                applied_rules.extend(rules)

        # ROWNUM → LIMIT (needs special handling to move clause)
        transformed, rownum_rules = self._convert_rownum(transformed)
        applied_rules.extend(rownum_rules)

        # Subquery alias enforcement (complex - requires parsing)
        transformed, alias_rules = self._ensure_subquery_aliases(transformed)
        applied_rules.extend(alias_rules)

        return transformed, applied_rules

    def _convert_rownum(self, sql: str) -> Tuple[str, List[AppliedRule]]:
        """Convert WHERE ROWNUM <= N to LIMIT N, properly relocating the clause."""
        applied_rules = []
        transformed = sql

        # Pattern: WHERE ROWNUM <= N (only condition)
        pattern1 = re.compile(
            r'\bWHERE\s+ROWNUM\s*<=\s*(\d+)\s*$',
            re.IGNORECASE | re.MULTILINE
        )
        m = pattern1.search(transformed)
        if m:
            limit_val = m.group(1)
            transformed = transformed[:m.start()].rstrip() + f'\nLIMIT {limit_val}'
            applied_rules.append(AppliedRule(
                rule_name="rownum_limit", rule_type="syntax",
                original=m.group(0), transformed=f"LIMIT {limit_val}"
            ))
            return transformed, applied_rules

        # Pattern: WHERE ROWNUM = 1 (only condition)
        pattern1b = re.compile(
            r'\bWHERE\s+ROWNUM\s*=\s*1\s*$',
            re.IGNORECASE | re.MULTILINE
        )
        m = pattern1b.search(transformed)
        if m:
            transformed = transformed[:m.start()].rstrip() + '\nLIMIT 1'
            applied_rules.append(AppliedRule(
                rule_name="rownum_equal", rule_type="syntax",
                original=m.group(0), transformed="LIMIT 1"
            ))
            return transformed, applied_rules

        # Pattern: WHERE ... AND ROWNUM <= N
        pattern2 = re.compile(
            r'\bAND\s+ROWNUM\s*<=\s*(\d+)',
            re.IGNORECASE
        )
        m = pattern2.search(transformed)
        if m:
            limit_val = m.group(1)
            transformed = transformed[:m.start()].rstrip() + transformed[m.end():]
            transformed = transformed.rstrip() + f'\nLIMIT {limit_val}'
            applied_rules.append(AppliedRule(
                rule_name="rownum_limit", rule_type="syntax",
                original=m.group(0), transformed=f"LIMIT {limit_val}"
            ))
            return transformed, applied_rules

        # Pattern: WHERE ROWNUM <= N AND ...
        pattern3 = re.compile(
            r'\bWHERE\s+ROWNUM\s*<=\s*(\d+)\s+AND\s+',
            re.IGNORECASE
        )
        m = pattern3.search(transformed)
        if m:
            limit_val = m.group(1)
            transformed = transformed[:m.start()] + 'WHERE ' + transformed[m.end():]
            transformed = transformed.rstrip() + f'\nLIMIT {limit_val}'
            applied_rules.append(AppliedRule(
                rule_name="rownum_limit", rule_type="syntax",
                original=m.group(0), transformed=f"LIMIT {limit_val}"
            ))

        return transformed, applied_rules

    def _apply_simple_replace(
        self,
        sql: str,
        rule_name: str,
        oracle_pattern: str,
        pg_replacement: str
    ) -> Tuple[str, List[AppliedRule]]:
        """Apply a simple string replacement rule."""
        applied_rules = []

        # Use regex for case-insensitive matching
        regex = re.compile(oracle_pattern, re.IGNORECASE)
        matches = list(regex.finditer(sql))

        if matches:
            transformed = regex.sub(pg_replacement, sql)

            for match in matches:
                applied_rules.append(AppliedRule(
                    rule_name=rule_name,
                    rule_type="simple_replace",
                    original=match.group(0),
                    transformed=pg_replacement
                ))

            return transformed, applied_rules

        return sql, applied_rules

    def _apply_regex_replace(
        self,
        sql: str,
        rule_name: str,
        oracle_pattern: str,
        pg_replacement: str
    ) -> Tuple[str, List[AppliedRule]]:
        """Apply a regex replacement rule with capture groups."""
        applied_rules = []

        regex = re.compile(oracle_pattern, re.IGNORECASE)
        matches = list(regex.finditer(sql))

        if matches:
            transformed = regex.sub(pg_replacement, sql)

            for match in matches:
                # Calculate what the replacement would be
                replaced = regex.sub(pg_replacement, match.group(0))

                applied_rules.append(AppliedRule(
                    rule_name=rule_name,
                    rule_type="regex_replace",
                    original=match.group(0),
                    transformed=replaced
                ))

            return transformed, applied_rules

        return sql, applied_rules

    def _ensure_subquery_aliases(self, sql: str) -> Tuple[str, List[AppliedRule]]:
        """
        Ensure all subqueries in FROM/JOIN clauses have aliases.

        This is MANDATORY in PostgreSQL.

        Args:
            sql: SQL text

        Returns:
            Tuple of (transformed_sql, applied_rules)
        """
        applied_rules = []
        transformed = sql

        # Pattern to match subqueries without aliases
        # This is a simplified version - production needs full SQL parser
        pattern = r'(FROM|JOIN)\s*(\([^)]+\))\s+(?!AS\s+\w+)'

        alias_counter = 1
        while True:
            match = re.search(pattern, transformed, re.IGNORECASE | re.DOTALL)
            if not match:
                break

            subquery = match.group(2)
            alias_name = f"sub{alias_counter}"
            alias_counter += 1

            # Add alias
            replacement = f"{match.group(1)} {subquery} AS {alias_name}"
            transformed = transformed[:match.start()] + replacement + transformed[match.end():]

            applied_rules.append(AppliedRule(
                rule_name="subquery_alias",
                rule_type="syntax",
                original=match.group(0),
                transformed=replacement
            ))

        return transformed, applied_rules

    def _convert_plsql_patterns(self, sql: str) -> Tuple[str, List[AppliedRule]]:
        """
        Convert common PL/SQL patterns to PostgreSQL equivalents.

        Handles:
        - RAISE_APPLICATION_ERROR → RAISE EXCEPTION
        - EMPTY_CLOB()/EMPTY_BLOB() → '' / '\\x'
        - EXECUTE IMMEDIATE → EXECUTE
        - RETURNING INTO → RETURNING ... INTO
        - DBMS_OUTPUT.PUT_LINE → RAISE NOTICE

        Args:
            sql: SQL text

        Returns:
            Tuple of (transformed_sql, applied_rules)
        """
        applied_rules = []
        transformed = sql

        plsql_rules = [
            # RAISE_APPLICATION_ERROR(-20001, 'msg') → RAISE EXCEPTION 'msg'
            (
                r"RAISE_APPLICATION_ERROR\s*\(\s*-?\d+\s*,\s*('(?:[^']|'')*')\s*\)",
                r"RAISE EXCEPTION \1",
                "raise_application_error"
            ),
            # EMPTY_CLOB() → ''
            (
                r"\bEMPTY_CLOB\s*\(\s*\)",
                "''",
                "empty_clob"
            ),
            # EMPTY_BLOB() → '\x'
            (
                r"\bEMPTY_BLOB\s*\(\s*\)",
                "'\\\\x'",
                "empty_blob"
            ),
            # EXECUTE IMMEDIATE 'sql' → EXECUTE 'sql'
            (
                r"\bEXECUTE\s+IMMEDIATE\b",
                "EXECUTE",
                "execute_immediate"
            ),
            # DBMS_OUTPUT.PUT_LINE('msg') → RAISE NOTICE '%', 'msg'
            (
                r"DBMS_OUTPUT\.PUT_LINE\s*\(\s*([^)]+)\s*\)",
                r"RAISE NOTICE '%', \1",
                "dbms_output_put_line"
            ),
        ]

        for pattern, replacement, rule_name in plsql_rules:
            regex = re.compile(pattern, re.IGNORECASE)
            matches = list(regex.finditer(transformed))
            if matches:
                transformed = regex.sub(replacement, transformed)
                for m in matches:
                    replaced = regex.sub(replacement, m.group(0))
                    applied_rules.append(AppliedRule(
                        rule_name=rule_name,
                        rule_type="plsql",
                        original=m.group(0),
                        transformed=replaced
                    ))

        return transformed, applied_rules

    def _convert_oracle_package_calls(self, sql: str) -> Tuple[str, List[AppliedRule]]:
        """
        Replace Oracle package.procedure calls with oracle_compat schema equivalents.

        Uses CALL_MAPPINGS from oracle_compat_library to replace:
        - DBMS_LOB.SUBSTR → oracle_compat.dbms_lob_substr
        - DBMS_RANDOM.VALUE → oracle_compat.dbms_random_value
        - UTL_RAW.CAST_TO_VARCHAR2 → oracle_compat.utl_raw_cast_to_varchar2
        - SYS_CONTEXT → oracle_compat.sys_context
        - MONTHS_BETWEEN → oracle_compat.months_between
        - etc.

        Args:
            sql: SQL text

        Returns:
            Tuple of (transformed_sql, applied_rules)
        """
        applied_rules = []
        transformed = sql

        # Sort by length descending to avoid partial matches
        # e.g., DBMS_OUTPUT.PUT_LINE before DBMS_OUTPUT.PUT
        sorted_calls = sorted(CALL_MAPPINGS.items(), key=lambda x: len(x[0]), reverse=True)

        for oracle_call, pg_func in sorted_calls:
            # Build regex: case-insensitive, word boundary aware
            # Handle both DBMS_LOB.SUBSTR and standalone functions like MONTHS_BETWEEN
            escaped = re.escape(oracle_call)
            pattern = re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)
            matches = list(pattern.finditer(transformed))
            if matches:
                transformed = pattern.sub(pg_func, transformed)
                for m in matches:
                    applied_rules.append(AppliedRule(
                        rule_name="oracle_package_call",
                        rule_type="package_compat",
                        original=m.group(0),
                        transformed=pg_func,
                    ))

        return transformed, applied_rules

    def _apply_parameter_casts(self, sql: str) -> Tuple[str, List[AppliedRule]]:
        """
        Apply PostgreSQL type casts to MyBatis parameters based on metadata.

        This is STEP 4 and requires metadata lookup.

        Args:
            sql: SQL text

        Returns:
            Tuple of (transformed_sql, applied_rules)
        """
        applied_rules = []
        transformed = sql

        # Find all MyBatis parameters: #{paramName}
        param_pattern = r'#\{([^}]+)\}'

        for match in re.finditer(param_pattern, sql):
            param = match.group(1)

            # Try to determine the column this parameter is being compared to
            # Look backward for column reference
            context_start = max(0, match.start() - 100)
            context = sql[context_start:match.start()]

            # Extract column name (simplified - needs better parsing)
            col_match = re.search(r'(\w+\.\w+)\s*[=<>!]+\s*$', context)
            if not col_match:
                continue

            col_ref = col_match.group(1).lower()

            # Look up data type in metadata
            if col_ref in self.metadata:
                pg_type = self.metadata[col_ref]
                cast_syntax = get_pg_cast_syntax(pg_type)

                if cast_syntax:
                    # Apply cast
                    original = match.group(0)
                    casted = f"{original}{cast_syntax}"

                    transformed = transformed.replace(original, casted, 1)

                    applied_rules.append(AppliedRule(
                        rule_name="parameter_cast",
                        rule_type="cast",
                        original=original,
                        transformed=casted
                    ))

        return transformed, applied_rules

    def assess_complexity(self, sql: str) -> Complexity:
        """
        Assess the complexity of SQL conversion.

        Args:
            sql: SQL text to analyze

        Returns:
            Complexity level (SIMPLE, MODERATE, or COMPLEX)
        """
        # Use pattern detector
        pattern_complexity = self.pattern_detector.assess_complexity(sql)

        if pattern_complexity == PatternComplexity.COMPLEX:
            return Complexity.COMPLEX
        elif pattern_complexity == PatternComplexity.MODERATE:
            return Complexity.MODERATE
        else:
            return Complexity.SIMPLE

    def detect_remaining_oracle_patterns(self, sql: str) -> List[str]:
        """
        Detect Oracle patterns that remain after static conversion.

        These patterns need LLM or Swarm conversion.

        Args:
            sql: SQL text (after static conversion)

        Returns:
            List of remaining Oracle pattern names
        """
        patterns = self.pattern_detector.detect_patterns(sql)
        return [p.name for p in patterns]

    def get_conversion_report(self, original: str, transformed: str) -> Dict:
        """
        Generate a comprehensive conversion report.

        Args:
            original: Original Oracle SQL
            transformed: Transformed PostgreSQL SQL

        Returns:
            Dictionary with conversion details
        """
        # Detect patterns in original
        original_patterns = self.pattern_detector.detect_patterns(original)

        # Detect remaining patterns after transformation
        remaining_patterns = self.detect_remaining_oracle_patterns(transformed)

        # Assess complexity
        complexity = self.assess_complexity(original)

        return {
            "complexity": complexity.value,
            "original_patterns": len(original_patterns),
            "remaining_patterns": len(remaining_patterns),
            "conversion_complete": len(remaining_patterns) == 0,
            "needs_llm": complexity in [Complexity.MODERATE, Complexity.COMPLEX],
            "needs_swarm": complexity == Complexity.COMPLEX,
            "patterns_detected": [p.name for p in original_patterns],
            "patterns_remaining": remaining_patterns,
        }
