"""
SQL Validator Tests
"""
import pytest
from app.utils.validators import SQLValidator


def test_select_only_valid():
    """Test valid SELECT query"""
    sql = "SELECT * FROM users WHERE id = 1"
    is_valid, error = SQLValidator.validate_sql(sql)
    assert is_valid is True
    assert error is None


def test_select_with_join():
    """Test SELECT with JOIN"""
    sql = "SELECT u.*, o.* FROM users u JOIN orders o ON u.id = o.user_id"
    is_valid, error = SQLValidator.validate_sql(sql)
    assert is_valid is True


def test_delete_blocked():
    """Test DELETE query is blocked"""
    sql = "DELETE FROM users WHERE id = 1"
    is_valid, error = SQLValidator.validate_sql(sql)
    assert is_valid is False
    assert "DELETE" in error


def test_drop_blocked():
    """Test DROP query is blocked"""
    sql = "DROP TABLE users"
    is_valid, error = SQLValidator.validate_sql(sql)
    assert is_valid is False
    assert "DROP" in error


def test_update_blocked():
    """Test UPDATE query is blocked"""
    sql = "UPDATE users SET name = 'admin' WHERE id = 1"
    is_valid, error = SQLValidator.validate_sql(sql)
    assert is_valid is False
    assert "UPDATE" in error


def test_sql_injection_or_1_equals_1():
    """Test SQL injection pattern detection"""
    sql = "SELECT * FROM users WHERE id = 1 OR '1'='1'"
    is_valid, error = SQLValidator.validate_sql(sql)
    assert is_valid is False


def test_sql_injection_comment():
    """Test SQL comment injection"""
    sql = "SELECT * FROM users WHERE id = 1; -- DROP TABLE users"
    is_valid, error = SQLValidator.validate_sql(sql)
    assert is_valid is False
    assert "comment" in error.lower() or "multiple" in error.lower()


def test_multiple_statements():
    """Test multiple statements are blocked"""
    sql = "SELECT * FROM users; SELECT * FROM orders"
    is_valid, error = SQLValidator.validate_sql(sql)
    assert is_valid is False


def test_union_select():
    """Test UNION SELECT (legitimate use case)"""
    sql = "SELECT name FROM users UNION SELECT name FROM customers"
    is_valid, error = SQLValidator.validate_sql(sql)
    # Should be valid as UNION is a legitimate SQL operation
    assert is_valid is True


def test_cte_query():
    """Test Common Table Expression (CTE)"""
    sql = """
    WITH sales_summary AS (
        SELECT region, SUM(amount) as total
        FROM sales
        GROUP BY region
    )
    SELECT * FROM sales_summary WHERE total > 1000
    """
    is_valid, error = SQLValidator.validate_sql(sql)
    assert is_valid is True


def test_empty_query():
    """Test empty query"""
    sql = ""
    is_valid, error = SQLValidator.validate_sql(sql)
    assert is_valid is False












