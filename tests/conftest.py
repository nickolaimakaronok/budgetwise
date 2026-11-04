"""
tests/conftest.py
pytest loads this file before any test file.

Points BudgetWise at a throw-away folder, so the tests never create or
touch the real data folder — and never move anything out of ~/Documents.
"""

import atexit
import os
import shutil
import tempfile

_test_dir = tempfile.mkdtemp(prefix="budgetwise-tests-")
os.environ["BUDGETWISE_DATA_DIR"] = _test_dir
atexit.register(shutil.rmtree, _test_dir, True)