# Buggy Calculator

A simple calculator with a bug in the `multiply` function.

## Bug

The `multiply` function incorrectly adds numbers instead of multiplying them.

## Running Tests

```bash
pytest test_calculator.py
```

## Fix

Change line in `calculator.py`:
```python
return a + b  # Wrong
```

To:
```python
return a * b  # Correct
```

