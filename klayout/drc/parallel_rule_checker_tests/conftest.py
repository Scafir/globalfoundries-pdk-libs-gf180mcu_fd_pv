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
Pytest configuration for parallel rule checker tests.
"""

import pytest
import klayout.rdb as rdb
import tempfile
import os
import subprocess
from pathlib import Path


@pytest.fixture(scope="session")
def klayout_base_dir():
    """Get base directory for scripts."""
    return Path(__file__).parent.parent


@pytest.fixture
def create_database():
    """Return function to create test databases."""
    def _create(name, top_cell="TOP"):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = rdb.ReportDatabase.new(name)
            db.top_cell_name = top_cell
            
            cell = db.create_cell(top_cell)
            cat = db.create_category("TEST_CAT")
            cat.description = "Category description"
            
            item = db.create_item(cell, cat)
            
            file_path = os.path.join(tmpdir, f"{name}.lyrdb")
            db.save(file_path)
            return file_path
    return _create


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def merge_helper_script(klayout_base_dir):
    """Get absolute path to merge_helper.rb script."""
    return str(klayout_base_dir / "merge_helper.rb")


def run_merge_helper(input1: str, input2: str, output: str, script: str) -> tuple:
    """Invoke merge_helper.rb via klayout binary.
    
    Args:
        input1: Absolute path to first database file
        input2: Absolute path to second database file  
        output: Absolute path for merged output file
        script: Absolute path to merge_helper.rb script
        
    Returns:
        tuple: (subprocess.CompletedProcess, Path to output file)
    """
    result = subprocess.run(
        [
            "klayout",
            "-b",
            "-r", script,
            "-rd", f"input1={input1}",
            "-rd", f"input2={input2}",
            "-rd", f"output={output}",
        ],
        capture_output=True,
        text=True,
    )
    return result, Path(output)


def load_report_database(db_path: str):
    """Load a ReportDatabase file and return the database object.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        rdb.ReportDatabase: Loaded database instance
    """
    db = rdb.ReportDatabase.new("loaded_db")
    db.load(db_path)
    return db


def assert_merged_file_exists(output_path: Path):
    """Assert merged output file was created.
    
    Args:
        output_path: Path to the merged output file
    """
    assert output_path.exists(), \
        f"Merged file not created: {output_path}"


def assert_category_item_count(db_path: str, category_name: str, expected_count: int):
    """Assert a category has expected number of items.
    
    Args:
        db_path: Path to merged database file
        category_name: Name of category to check
        expected_count: Expected number of items in category
    """
    db = load_report_database(db_path)
    cat = db.category_by_path(category_name)
    if cat is None:
        raise AssertionError(f"Category '{category_name}' not found in database")
    item_count = sum(1 for _ in cat.each_item())
    assert item_count == expected_count, \
        f"Category '{category_name}' has {item_count} items, expected {expected_count}"


def assert_db_top_cell(db_path: str, expected_name: str):
    """Assert database has expected top cell name.
    
    Args:
        db_path: Path to database file
        expected_name: Expected top cell name
    """
    db = load_report_database(db_path)
    actual_name = db.top_cell_name
    assert actual_name == expected_name, \
        f"Top cell is '{actual_name}', expected '{expected_name}'"



