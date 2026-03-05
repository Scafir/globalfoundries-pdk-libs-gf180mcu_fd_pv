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
Test cases for category merging in parallel rule checker.
"""

import pytest
import klayout.rdb as rdb
import os
from pathlib import Path
from .conftest import run_merge_helper, assert_merged_file_exists, load_report_database


def _create_category_db(tmp_path, name, num_cats=1, nested=False):
    """Create database with categories."""
    db = rdb.ReportDatabase.new(name)
    db.top_cell_name = "TOP"
    cell = db.create_cell("TOP")
    
    for i in range(num_cats):
        cat = db.create_category(f"CAT{i+1}")
        cat.description = f"Category description {i+1}"
        db.create_item(cell, cat)
    
    filepath = tmp_path / f"{name}.lyrdb"
    db.save(str(filepath))
    return str(filepath)


class TestCategoryPreservation:
    """Tests for category preservation."""
    
    def test_categories_from_db1_preserved(self, tmp_path, merge_helper_script):
        """Categories from db1 should be preserved."""
        db1 = _create_category_db(tmp_path, "db1", num_cats=2)
        db2 = _create_category_db(tmp_path, "db2", num_cats=1)
        output_path = tmp_path / "merged.lyrdb"

        result, output_file = run_merge_helper(
            str(db1), str(db2), str(output_path), merge_helper_script
        )

        assert output_file.exists()
        assert result.returncode == 0

        # Verify categories in merged database
        db = load_report_database(str(output_path))
        
        # Check that db1 categories are preserved with db1's descriptions
        cat1 = db.category_by_path("CAT1")
        assert cat1 is not None, "Category CAT1 should be present"
        assert cat1.description == "Category description 1", \
            f"Category CAT1 description should be preserved from db1"
        
        cat2 = db.category_by_path("CAT2")
        assert cat2 is not None, "Category CAT2 should be present"
        assert cat2.description == "Category description 2", \
            f"Category CAT2 description should be preserved from db1"


class TestNestedCategories:
    """Tests for nested category handling."""
    
    def test_merge_nested_categories(self, tmp_path, merge_helper_script):
        """Nested category hierarchies should merge."""
        db1 = _create_category_db(tmp_path, "db1", num_cats=1)
        db2 = _create_category_db(tmp_path, "db2", num_cats=1)
        output_path = tmp_path / "merged.lyrdb"

        result, output_file = run_merge_helper(
            str(db1), str(db2), str(output_path), merge_helper_script
        )

        assert output_file.exists()
        assert result.returncode == 0

        # Verify merged categories - db2 category should be merged with same path
        # (db1's category has priority for description)
        db = load_report_database(str(output_path))
        
        cat1 = db.category_by_path("CAT1")
        assert cat1 is not None, "Category CAT1 from db1 should be present"
        assert cat1.description == "Category description 1", \
            f"Category CAT1 description should be from db1"


class TestCategoryDescriptions:
    """Tests for category descriptions."""
    
    def test_merge_preserves_descriptions(self, tmp_path, merge_helper_script):
        """Category descriptions should be preserved."""
        db1 = _create_category_db(tmp_path, "db1", num_cats=2)
        db2 = _create_category_db(tmp_path, "db2", num_cats=2)
        output_path = tmp_path / "merged.lyrdb"

        result, output_file = run_merge_helper(
            str(db1), str(db2), str(output_path), merge_helper_script
        )

        assert output_file.exists()
        assert result.returncode == 0

        # Verify merged database structure
        db = load_report_database(str(output_path))
        
        # db1 categories should be preserved with db1's descriptions
        cat1 = db.category_by_path("CAT1")
        assert cat1 is not None, "CAT1 should be present"
        assert cat1.description == "Category description 1", \
            f"Description mismatch: expected 'Category description 1', got '{cat1.description}'"
        
        cat2 = db.category_by_path("CAT2")
        assert cat2 is not None, "CAT2 should be present"
        assert cat2.description == "Category description 2", \
            f"Description mismatch: expected 'Category description 2', got '{cat2.description}'"
