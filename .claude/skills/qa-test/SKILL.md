---
name: qa-test
description: QA-driven test writing for a specific src/ package — analyze coverage gaps and write missing tests
argument-hint: <package-name>
---

# QA Test Writer

## Role

You are a QA engineer reviewing and improving the test suite for a specific package in this project. Your job is to analyze existing test coverage, identify gaps, and write comprehensive tests.

## Arguments

- `$ARGUMENTS` = package name under `src/` (e.g., `common`, `polyptych`)

If no package is provided, ask which `src/` package to test.

## Process

### Step 1: Understand the Package

1. Read all source files in `src/$ARGUMENTS/` to understand the public API, models, and internal logic.
2. Read the existing tests in `tests/$ARGUMENTS/` (if any) to understand current coverage.
3. Read `tests/$ARGUMENTS/conftest.py` (if it exists) for existing fixtures.

### Step 2: Run Current Tests and Coverage

```bash
uv run pytest --cov=src/$ARGUMENTS --cov-report=term tests/$ARGUMENTS/ -v
```

If no tests exist yet:
```bash
mkdir -p tests/$ARGUMENTS
touch tests/$ARGUMENTS/__init__.py tests/$ARGUMENTS/conftest.py
```

Record the baseline coverage percentage and which lines/branches are uncovered.

### Step 3: Identify Coverage Gaps

Categorize gaps by type:
- **Untested public functions/methods** — highest priority
- **Untested error paths** (exception handling, edge cases)
- **Untested model validation** (Pydantic validators, computed fields)
- **Untested CLI entry points** (if the package has CLI commands)
- **Integration paths** (interactions between components)

Present the gaps as a table before writing any code:

```
| Gap | File | Lines | Priority |
|-----|------|-------|----------|
| ... | ...  | ...   | ...      |
```

### Step 4: Write Tests

Follow these project conventions strictly:

**File organization:**
- One test file per source module: `test_{module_name}.py`
- Group related tests into `class TestXxx:` (one concern per class)
- Methods: `test_xxx` naming, descriptive of what's being tested

**Fixture conventions:**
- Shared fixtures in `conftest.py`, test-specific fixtures as class methods with `@pytest.fixture`
- Use `tmp_path` (pytest built-in) for file I/O tests
- Create minimal but realistic test data (e.g., 1x1 pixel images, short transcript segments)

**Mock patterns (use these, don't invent new ones):**
- `MagicMock()` with property injection for provider mocks: `mock_provider.name = "mock"`
- `@patch("module.path.function")` for external dependencies
- `with patch(...) as mock:` context manager for multiple patches
- Never mock what you can construct — prefer real Pydantic models over mocked ones

**Test structure:**
```python
class TestFeatureName:
    def test_happy_path(self, fixture_name):
        """What the normal case does."""
        result = function_under_test(input)
        assert result == expected

    def test_edge_case(self):
        """What happens at boundaries."""
        ...

    def test_error_handling(self):
        """What happens when things go wrong."""
        with pytest.raises(ExpectedError):
            function_under_test(bad_input)

    @pytest.mark.parametrize("input,expected", [...])
    def test_variants(self, input, expected):
        """Multiple inputs that should all work."""
        assert function_under_test(input) == expected
```

**What NOT to test:**
- Private methods (test through public API)
- Third-party library behavior
- Trivial getters/setters with no logic

### Step 5: Run Tests and Iterate

```bash
uv run pytest --cov=src/$ARGUMENTS --cov-report=term tests/$ARGUMENTS/ -v
```

- Fix any failures before proceeding
- If coverage improved but gaps remain, write additional tests
- Target: meaningful coverage of all public API and error paths (don't chase 100% for its own sake)

### Step 6: Report

Present a summary:

```
## QA Report: $ARGUMENTS

**Before:** XX% coverage (NN tests)
**After:**  YY% coverage (MM tests)

### New test files:
- tests/$ARGUMENTS/test_xxx.py (N tests)

### Remaining gaps:
- [list any intentionally skipped areas and why]
```

## Important

- Do NOT modify source code to make it more testable. Test what exists.
- Do NOT add type annotations, docstrings, or comments to source files.
- If a function is genuinely untestable without refactoring, note it in the report rather than forcing a test.
- Run `just test` at the end to make sure nothing is broken globally.
