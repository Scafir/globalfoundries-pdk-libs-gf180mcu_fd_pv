#!/usr/bin/env python3
# Copyright 2026 GlobalFoundries PDK Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Test runner for ParallelRuleChecker merge_databases tests.

Usage:
    python -m pytest klayout/drc/parallel_rule_checker_tests/

Options:
    -v, --verbose: Show verbose output
    -k EXPRESSION: Only run tests matching expression
    -m MARKER: Run tests with marker
"""

import subprocess
import sys
import os


def run_tests():
    """Run all tests with pytest."""
    test_dir = os.path.join(
        os.path.dirname(__file__),
        '..', '..', 'klayout', 'drc', 'parallel_rule_checker_tests'
    )
    
    cmd = [
        sys.executable,
        '-m', 'pytest',
        test_dir,
        '-v',
    ]
    
    result = subprocess.run(cmd, cwd=os.path.dirname(__file__))
    return result.returncode


if __name__ == '__main__':
    sys.exit(run_tests())
