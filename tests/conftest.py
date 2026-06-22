"""Shared fixtures for the Lab 10 autograder.

Per the Autograder Test Path Rule, `..` (not `../starter/`) is the
correct insertion: in a learner's accepted repo, `api/` lives at the
repo root and `tests/` is a sibling. The `starter/` directory exists
only in this staging layout.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
