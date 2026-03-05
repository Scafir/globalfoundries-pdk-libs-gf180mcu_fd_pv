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
Pytest fixtures for creating test ReportDatabases.
Note: klayout Python bindings don't support all Ruby API's features.
This file provides simple database creation fixtures.
"""

import os
import pytest
import tempfile
import klayout.rdb as rdb


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def _create_basic_db(name, top_cell="TOP"):
    """Create a basic database with one cell and one category."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = rdb.ReportDatabase.new(name)
        db.top_cell_name = top_cell
        
        cell = db.create_cell(top_cell)
        cat = db.create_category("TEST_CAT")
        item = db.create_item(cell, cat)
        
        filepath = os.path.join(tmpdir, f"{name}.lyrdb")
        db.save(filepath)
        return filepath


@pytest.fixture
def sample_db_file(temp_dir):
    """Create a sample .lyrdb file with basic structure."""
    db = rdb.ReportDatabase.new("sample")
    db.top_cell_name = "TOP"
    
    cell = db.create_cell("TOP")
    cat = db.create_category("CAT1")
    cat.description = "Category 1 description"
    item = db.create_item(cell, cat)
    
    filepath = os.path.join(temp_dir, "sample.lyrdb")
    db.save(filepath)
    return filepath


@pytest.fixture
def empty_db_file(temp_dir):
    """Create an empty .lyrdb file."""
    db = rdb.ReportDatabase.new("empty")
    filepath = os.path.join(temp_dir, "empty.lyrdb")
    db.save(filepath)
    return filepath


@pytest.fixture
def metadata_db_file(temp_dir):
    """Create a database with metadata fields."""
    db = rdb.ReportDatabase.new("metadata")
    db.top_cell_name = "TOP_CELL"
    
    cell = db.create_cell("TOP_CELL")
    cat1 = db.create_category("RULES")
    
    filepath = os.path.join(temp_dir, "metadata.lyrdb")
    db.save(filepath)
    return filepath


@pytest.fixture
def nested_cat_db_file(temp_dir):
    """Create a database with nested category hierarchy."""
    db = rdb.ReportDatabase.new("nested")
    db.top_cell_name = "TOP"
    
    cell = db.create_cell("TOP")
    cat_l1 = db.create_category("LEVEL1")
    cat_l2 = db.create_category(cat_l1, "LEVEL2")
    cat_l3 = db.create_category(cat_l2, "LEVEL3")
    
    filepath = os.path.join(temp_dir, "nested.lyrdb")
    db.save(filepath)
    return filepath


@pytest.fixture
def diff_topcell_db_file(temp_dir):
    """Create a database with different top cell for error testing."""
    db = rdb.ReportDatabase.new("diff_tc")
    db.top_cell_name = "DIFFERENT_TOPCELL"
    
    cell = db.create_cell("DIFFERENT_TOPCELL")
    cat = db.create_category("RULE_DIFF")
    
    filepath = os.path.join(temp_dir, "different_topcell.lyrdb")
    db.save(filepath)
    return filepath


@pytest.fixture
def merge_helper_path():
    """Get path to merge helper script."""
    return "klayout/drc/merge_helper.rb"


@pytest.fixture
def test_data_dir(temp_dir):
    """Create a dedicated test data directory."""
    data_dir = os.path.join(temp_dir, "test_data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir
