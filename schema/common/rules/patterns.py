"""
Oracle Pattern Detection and Complexity Assessment

This module detects Oracle-specific patterns in SQL and assesses their
complexity to determine the appropriate conversion strategy.

Complexity Levels:
- SIMPLE: Static rules only (direct text replacement)
- MODERATE: Needs LLM assistance (context-aware conversion)
- COMPLEX: Needs Swarm (multi-step reasoning, architectural changes)
"""

import re
from enum import Enum
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# Try to import from postgresql/mysql specific rules, fallback to empty
try:
    from postgresql.rules.static_rules import COMPLEX_PATTERNS
except ImportError:
    try:
        from mysql.rules.static_rules import COMPLEX_PATTERNS
    except ImportError:
        COMPLEX_PATTERNS = {}


class PatternComplexity(Enum):
    """Complexity levels for Oracle patterns."""
    SIMPLE = "SIMPLE"      # Static rules only
    MODERATE = "MODERATE"  # LLM assistance needed
    COMPLEX = "COMPLEX"    # Swarm needed


@dataclass
class DetectedPattern:
    """A detected Oracle pattern."""
    name: str
    pattern: str
    complexity: PatternComplexity
    line_number: Optional[int] = None
    matched_text: Optional[str] = None
    context: Optional[str] = None


class OraclePatternDetector:
    """Detects Oracle-specific patterns in SQL."""

    def __init__(self):
        """Initialize the pattern detector."""
        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> List[Tuple[re.Pattern, str, PatternComplexity]]:
        """Compile all Oracle patterns."""
        compiled = []
        for pattern_str, name, complexity in COMPLEX_PATTERNS:
            try:
                regex = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
                complexity_enum = PatternComplexity[complexity]
                compiled.append((regex, name, complexity_enum))
            except Exception as e:
                print(f"Warning: Failed to compile pattern '{name}': {e}")
        return compiled

    def detect_patterns(self, sql: str) -> List[DetectedPattern]:
        """
        Detect all Oracle patterns in SQL.

        Args:
            sql: SQL text to analyze

        Returns:
            List of detected patterns with their complexity
        """
        detected = []
        lines = sql.split('\n')

        for regex, name, complexity in self.patterns:
            for match in regex.finditer(sql):
                # Find line number
                line_num = sql[:match.start()].count('\n') + 1

                # Extract context (surrounding text)
                start = max(0, match.start() - 50)
                end = min(len(sql), match.end() + 50)
                context = sql[start:end]

                detected.append(DetectedPattern(
                    name=name,
                    pattern=match.group(0),
                    complexity=complexity,
                    line_number=line_num,
                    matched_text=match.group(0),
                    context=context
                ))

        return detected

    def assess_complexity(self, sql: str) -> PatternComplexity:
        """
        Assess overall complexity of SQL conversion.

        Args:
            sql: SQL text to analyze

        Returns:
            Overall complexity level
        """
        patterns = self.detect_patterns(sql)

        if not patterns:
            return PatternComplexity.SIMPLE

        # Return highest complexity found
        complexities = [p.complexity for p in patterns]

        if PatternComplexity.COMPLEX in complexities:
            return PatternComplexity.COMPLEX
        elif PatternComplexity.MODERATE in complexities:
            return PatternComplexity.MODERATE
        else:
            return PatternComplexity.SIMPLE

    def detect_plsql_blocks(self, sql: str) -> List[DetectedPattern]:
        """
        Detect PL/SQL blocks and assess their complexity.

        Args:
            sql: SQL text to analyze

        Returns:
            List of detected PL/SQL blocks
        """
        detected = []

        # Package definitions
        if re.search(r'CREATE\s+OR\s+REPLACE\s+PACKAGE', sql, re.IGNORECASE):
            detected.append(DetectedPattern(
                name="PL/SQL Package",
                pattern="CREATE OR REPLACE PACKAGE",
                complexity=PatternComplexity.COMPLEX
            ))

        # Package bodies
        if re.search(r'CREATE\s+OR\s+REPLACE\s+PACKAGE\s+BODY', sql, re.IGNORECASE):
            detected.append(DetectedPattern(
                name="PL/SQL Package Body",
                pattern="CREATE OR REPLACE PACKAGE BODY",
                complexity=PatternComplexity.COMPLEX
            ))

        # Functions
        func_match = re.search(
            r'CREATE\s+OR\s+REPLACE\s+FUNCTION\s+(\w+)',
            sql,
            re.IGNORECASE
        )
        if func_match:
            # Assess function complexity by size
            func_lines = sql.count('\n')
            complexity = (
                PatternComplexity.COMPLEX if func_lines > 100
                else PatternComplexity.MODERATE if func_lines > 20
                else PatternComplexity.SIMPLE
            )
            detected.append(DetectedPattern(
                name=f"PL/SQL Function ({func_match.group(1)})",
                pattern="CREATE OR REPLACE FUNCTION",
                complexity=complexity
            ))

        # Procedures
        proc_match = re.search(
            r'CREATE\s+OR\s+REPLACE\s+PROCEDURE\s+(\w+)',
            sql,
            re.IGNORECASE
        )
        if proc_match:
            # Assess procedure complexity by size
            proc_lines = sql.count('\n')
            complexity = (
                PatternComplexity.COMPLEX if proc_lines > 100
                else PatternComplexity.MODERATE if proc_lines > 20
                else PatternComplexity.SIMPLE
            )
            detected.append(DetectedPattern(
                name=f"PL/SQL Procedure ({proc_match.group(1)})",
                pattern="CREATE OR REPLACE PROCEDURE",
                complexity=complexity
            ))

        # Triggers
        if re.search(r'CREATE\s+OR\s+REPLACE\s+TRIGGER', sql, re.IGNORECASE):
            detected.append(DetectedPattern(
                name="PL/SQL Trigger",
                pattern="CREATE OR REPLACE TRIGGER",
                complexity=PatternComplexity.COMPLEX
            ))

        # Anonymous blocks
        if re.search(r'DECLARE\s+.*BEGIN', sql, re.IGNORECASE | re.DOTALL):
            detected.append(DetectedPattern(
                name="Anonymous PL/SQL Block",
                pattern="DECLARE ... BEGIN",
                complexity=PatternComplexity.MODERATE
            ))

        return detected

    def detect_bulk_operations(self, sql: str) -> List[DetectedPattern]:
        """
        Detect Oracle bulk operations.

        Args:
            sql: SQL text to analyze

        Returns:
            List of detected bulk operations
        """
        detected = []

        if re.search(r'\bBULK\s+COLLECT\b', sql, re.IGNORECASE):
            detected.append(DetectedPattern(
                name="BULK COLLECT",
                pattern="BULK COLLECT",
                complexity=PatternComplexity.COMPLEX
            ))

        if re.search(r'\bFORALL\b', sql, re.IGNORECASE):
            detected.append(DetectedPattern(
                name="FORALL",
                pattern="FORALL",
                complexity=PatternComplexity.COMPLEX
            ))

        return detected

    def detect_hierarchical_queries(self, sql: str) -> List[DetectedPattern]:
        """
        Detect hierarchical queries (CONNECT BY).

        Args:
            sql: SQL text to analyze

        Returns:
            List of detected hierarchical queries
        """
        detected = []

        if re.search(r'\bCONNECT\s+BY\b', sql, re.IGNORECASE):
            detected.append(DetectedPattern(
                name="CONNECT BY",
                pattern="CONNECT BY",
                complexity=PatternComplexity.COMPLEX
            ))

        if re.search(r'\bSTART\s+WITH\b', sql, re.IGNORECASE):
            detected.append(DetectedPattern(
                name="START WITH",
                pattern="START WITH",
                complexity=PatternComplexity.COMPLEX
            ))

        return detected

    def detect_oracle_packages(self, sql: str) -> List[DetectedPattern]:
        """
        Detect Oracle package usage.

        Args:
            sql: SQL text to analyze

        Returns:
            List of detected package usage
        """
        detected = []

        # DBMS packages + custom packages
        dbms_packages = [
            'DBMS_OUTPUT', 'DBMS_SQL', 'DBMS_LOB', 'DBMS_RANDOM',
            'DBMS_CRYPTO', 'DBMS_LOCK', 'DBMS_SESSION', 'DBMS_UTILITY',
            'DBMS_JOB', 'DBMS_SCHEDULER', 'DBMS_STATS', 'DBMS_METADATA',
            'PKG_CRYPTO',  # custom encryption package
        ]

        for pkg in dbms_packages:
            if re.search(rf'\b{pkg}\s*\.', sql, re.IGNORECASE):
                detected.append(DetectedPattern(
                    name=f"{pkg} Package",
                    pattern=f"{pkg}.",
                    complexity=PatternComplexity.COMPLEX
                ))

        # UTL packages
        utl_packages = [
            'UTL_FILE', 'UTL_HTTP', 'UTL_SMTP', 'UTL_TCP',
            'UTL_MAIL', 'UTL_RAW', 'UTL_ENCODE', 'UTL_COMPRESS'
        ]

        for pkg in utl_packages:
            if re.search(rf'\b{pkg}\s*\.', sql, re.IGNORECASE):
                detected.append(DetectedPattern(
                    name=f"{pkg} Package",
                    pattern=f"{pkg}.",
                    complexity=PatternComplexity.COMPLEX
                ))

        return detected

    def detect_dynamic_sql(self, sql: str) -> List[DetectedPattern]:
        """
        Detect dynamic SQL patterns.

        Args:
            sql: SQL text to analyze

        Returns:
            List of detected dynamic SQL
        """
        detected = []

        if re.search(r'\bEXECUTE\s+IMMEDIATE\b', sql, re.IGNORECASE):
            detected.append(DetectedPattern(
                name="EXECUTE IMMEDIATE",
                pattern="EXECUTE IMMEDIATE",
                complexity=PatternComplexity.MODERATE
            ))

        return detected

    def detect_rownum_patterns(self, sql: str) -> List[DetectedPattern]:
        """
        Detect ROWNUM usage patterns.

        Args:
            sql: SQL text to analyze

        Returns:
            List of detected ROWNUM patterns
        """
        detected = []

        # Simple ROWNUM <= N or ROWNUM = 1 (SIMPLE)
        if re.search(r'\bROWNUM\s*[<=]\s*\d+', sql, re.IGNORECASE):
            detected.append(DetectedPattern(
                name="ROWNUM Pagination (Simple)",
                pattern="ROWNUM <= N",
                complexity=PatternComplexity.SIMPLE
            ))

        # Complex ROWNUM in subquery (MODERATE)
        elif re.search(r'\bROWNUM\b', sql, re.IGNORECASE):
            detected.append(DetectedPattern(
                name="ROWNUM Pagination (Complex)",
                pattern="ROWNUM",
                complexity=PatternComplexity.MODERATE
            ))

        return detected

    def detect_outer_join_syntax(self, sql: str) -> List[DetectedPattern]:
        """
        Detect Oracle (+) outer join syntax.

        Args:
            sql: SQL text to analyze

        Returns:
            List of detected outer joins
        """
        detected = []

        if re.search(r'\(\+\)', sql):
            detected.append(DetectedPattern(
                name="Outer Join (+)",
                pattern="(+)",
                complexity=PatternComplexity.MODERATE
            ))

        return detected


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================

def detect_oracle_patterns(sql: str) -> List[DetectedPattern]:
    """
    Detect all Oracle patterns in SQL.

    Args:
        sql: SQL text to analyze

    Returns:
        List of all detected patterns
    """
    detector = OraclePatternDetector()

    patterns = []
    patterns.extend(detector.detect_patterns(sql))
    patterns.extend(detector.detect_plsql_blocks(sql))
    patterns.extend(detector.detect_bulk_operations(sql))
    patterns.extend(detector.detect_hierarchical_queries(sql))
    patterns.extend(detector.detect_oracle_packages(sql))
    patterns.extend(detector.detect_dynamic_sql(sql))
    patterns.extend(detector.detect_rownum_patterns(sql))
    patterns.extend(detector.detect_outer_join_syntax(sql))

    return patterns


def assess_pattern_complexity(sql: str) -> PatternComplexity:
    """
    Assess overall complexity of SQL conversion.

    Args:
        sql: SQL text to analyze

    Returns:
        Overall complexity level
    """
    detector = OraclePatternDetector()
    return detector.assess_complexity(sql)


def get_complexity_report(sql: str) -> Dict[str, any]:
    """
    Generate a comprehensive complexity report.

    Args:
        sql: SQL text to analyze

    Returns:
        Dictionary with complexity analysis
    """
    patterns = detect_oracle_patterns(sql)
    complexity = assess_pattern_complexity(sql)

    # Group by complexity
    simple = [p for p in patterns if p.complexity == PatternComplexity.SIMPLE]
    moderate = [p for p in patterns if p.complexity == PatternComplexity.MODERATE]
    complex_patterns = [p for p in patterns if p.complexity == PatternComplexity.COMPLEX]

    return {
        "overall_complexity": complexity.value,
        "total_patterns": len(patterns),
        "simple_count": len(simple),
        "moderate_count": len(moderate),
        "complex_count": len(complex_patterns),
        "patterns": {
            "simple": [p.name for p in simple],
            "moderate": [p.name for p in moderate],
            "complex": [p.name for p in complex_patterns]
        },
        "all_patterns": patterns
    }
