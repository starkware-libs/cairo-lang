import pytest

# Instruct pytest to print full information (e.g., the values on both sides of the equality)
# about asserts that failed in the module below.
# Normally, pytest prints full information only for test files (according to their name).
pytest.register_assert_rewrite("starkware.cairo.lang.compiler.preprocessor.preprocessor_test_utils")
