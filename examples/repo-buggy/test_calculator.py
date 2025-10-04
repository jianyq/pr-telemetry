"""Tests for calculator module."""

import pytest
from calculator import add, subtract, multiply, divide


def test_add():
    """Test addition."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0


def test_subtract():
    """Test subtraction."""
    assert subtract(5, 3) == 2
    assert subtract(0, 5) == -5


def test_multiply():
    """Test multiplication - this will fail due to bug."""
    assert multiply(2, 3) == 6
    assert multiply(4, 5) == 20
    assert multiply(-2, 3) == -6


def test_divide():
    """Test division."""
    assert divide(6, 2) == 3
    assert divide(5, 2) == 2.5


def test_divide_by_zero():
    """Test division by zero raises error."""
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide(5, 0)

