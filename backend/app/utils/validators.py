"""
SQL Validation Utilities - SQL Injection Prevention
"""
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Token
from sqlparse.tokens import Keyword, DML
import re
from typing import List, Tuple, Optional


class SQLValidator:
    """SQL query validator to prevent injection and destructive operations"""
    
    # Dangerous SQL keywords that should be blocked
    DANGEROUS_KEYWORDS = {
        "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", 
        "INSERT", "UPDATE", "GRANT", "REVOKE", "EXEC",
        "EXECUTE", "CALL", "MERGE", "REPLACE"
    }
    
    # Allowed DML operations (read-only)
    ALLOWED_DML = {"SELECT", "WITH"}
    
    @staticmethod
    def is_select_only(sql: str) -> bool:
        """
        Check if SQL query is SELECT-only (read-only).
        
        Args:
            sql: SQL query string
            
        Returns:
            bool: True if query is SELECT-only, False otherwise
        """
        # Parse SQL
        parsed = sqlparse.parse(sql)
        if not parsed:
            return False
        
        # Check each statement
        for statement in parsed:
            # Get the first token (should be SELECT or WITH)
            first_token = None
            for token in statement.tokens:
                if not token.is_whitespace:
                    first_token = token
                    break
            
            if not first_token:
                return False
            
            # Check if it's a SELECT or WITH (CTE) statement
            if first_token.ttype is DML:
                if first_token.value.upper() not in SQLValidator.ALLOWED_DML:
                    return False
            elif isinstance(first_token, Identifier):
                # Could be a CTE
                continue
            else:
                return False
        
        return True
    
    @staticmethod
    def contains_dangerous_keywords(sql: str) -> Tuple[bool, List[str]]:
        """
        Check if SQL contains dangerous keywords.
        
        Args:
            sql: SQL query string
            
        Returns:
            Tuple[bool, List[str]]: (contains_dangerous, list_of_dangerous_keywords)
        """
        sql_upper = sql.upper()
        found_dangerous = []
        
        for keyword in SQLValidator.DANGEROUS_KEYWORDS:
            # Use word boundaries to avoid false positives
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                found_dangerous.append(keyword)
        
        return len(found_dangerous) > 0, found_dangerous
    
    @staticmethod
    def has_multiple_statements(sql: str) -> bool:
        """
        Check if SQL contains multiple statements (potential SQL injection).
        
        Args:
            sql: SQL query string
            
        Returns:
            bool: True if multiple statements found, False otherwise
        """
        parsed = sqlparse.parse(sql)
        return len([s for s in parsed if s.get_type() != 'UNKNOWN']) > 1
    
    @staticmethod
    def check_sql_injection_patterns(sql: str) -> Tuple[bool, Optional[str]]:
        """
        Check for common SQL injection patterns.
        
        Args:
            sql: SQL query string
            
        Returns:
            Tuple[bool, Optional[str]]: (is_suspicious, reason)
        """
        sql_lower = sql.lower()
        
        # Check for comment-based injection
        if "--" in sql or "/*" in sql or "*/" in sql:
            return True, "SQL comments detected (potential injection)"
        
        # Check for semicolon (statement terminator)
        if ";" in sql.strip().rstrip(";"):
            return True, "Multiple statements detected (potential injection)"
        
        # Check for UNION-based injection
        if re.search(r'\bUNION\s+(ALL\s+)?SELECT\b', sql_lower):
            # UNION SELECT is allowed for legitimate queries
            # but we'll flag it for extra scrutiny
            pass
        
        # Check for common injection patterns
        injection_patterns = [
            r"'\s*OR\s+'1'\s*=\s*'1",
            r"'\s*OR\s+1\s*=\s*1",
            r"admin'\s*--",
            r"'\s*;\s*DROP\s+TABLE",
            r"'\s*;\s*DELETE\s+FROM",
            r"EXEC\s*\(",
            r"EXECUTE\s*\(",
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                return True, f"SQL injection pattern detected: {pattern}"
        
        return False, None
    
    @staticmethod
    def validate_sql(sql: str) -> Tuple[bool, Optional[str]]:
        """
        Comprehensive SQL validation.
        
        Args:
            sql: SQL query string
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if not sql or not sql.strip():
            return False, "Empty SQL query"
        
        # Check for SQL injection patterns
        is_suspicious, reason = SQLValidator.check_sql_injection_patterns(sql)
        if is_suspicious:
            return False, reason
        
        # Check for multiple statements
        if SQLValidator.has_multiple_statements(sql):
            return False, "Multiple SQL statements not allowed"
        
        # Check for dangerous keywords
        has_dangerous, dangerous_keywords = SQLValidator.contains_dangerous_keywords(sql)
        if has_dangerous:
            return False, f"Dangerous SQL keywords detected: {', '.join(dangerous_keywords)}"
        
        # Check if SELECT-only
        if not SQLValidator.is_select_only(sql):
            return False, "Only SELECT queries are allowed"
        
        # Try to parse SQL
        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                return False, "Unable to parse SQL query"
        except Exception as e:
            return False, f"SQL parsing error: {str(e)}"
        
        return True, None
    
    @staticmethod
    def sanitize_identifier(identifier: str) -> str:
        """
        Sanitize a SQL identifier (table/column name).
        
        Args:
            identifier: SQL identifier
            
        Returns:
            str: Sanitized identifier
        """
        # Remove potentially dangerous characters
        # Allow only alphanumeric, underscore, and dot (for schema.table)
        sanitized = re.sub(r'[^\w\.]', '', identifier)
        return sanitized
    
    @staticmethod
    def format_sql(sql: str) -> str:
        """
        Format SQL query for better readability.
        
        Args:
            sql: SQL query string
            
        Returns:
            str: Formatted SQL
        """
        return sqlparse.format(
            sql,
            reindent=True,
            keyword_case='upper',
            strip_comments=True
        )


# Global validator instance
sql_validator = SQLValidator()






