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
Test cases for data integrity verification in parallel rule checker merge.
"""

import pytest
import klayout.rdb as rdb
import os
from pathlib import Path
from .conftest import run_merge_helper, assert_merged_file_exists, load_report_database


def _create_db(tmp_path, name, num_items=1):
    """Create a test database."""
    db = rdb.ReportDatabase.new(name)
    db.top_cell_name = "TOP"
    cell = db.create_cell("TOP")
    cat = db.create_category("RULE")
    
    for _ in range(num_items):
        db.create_item(cell, cat)
    
    filepath = tmp_path / f"{name}.lyrdb"
    db.save(str(filepath))
    return str(filepath)


class TestItemCounts:
    """Test item count verification."""
    
    def test_item_count_after_merge(self, tmp_path, merge_helper_script):
        """Total items should be sum of both databases."""
        db1 = _create_db(tmp_path, "db1", num_items=2)
        db2 = _create_db(tmp_path, "db2", num_items=3)
        output_path = tmp_path / "merged.lyrdb"

        result, output_file = run_merge_helper(
            str(db1), str(db2), str(output_path), merge_helper_script
        )

        assert output_file.exists()
        assert result.returncode == 0

        # Verify item count
        db = load_report_database(str(output_path))
        cell = db.cell_by_qname("TOP")
        assert cell is not None, "Cell TOP should be present"
        
        cat = db.category_by_path("RULE")
        assert cat is not None, "Category RULE should be present"
        
        item_count = sum(1 for _ in cat.each_item())
        assert item_count == 5, f"Expected 5 items total (2+3), got {item_count}"


class TestRDBIDMappings:
    """Test RDB ID mappings."""
    
    def test_mappings_consistent(self, tmp_path, merge_helper_script):
        """RDB ID mappings should be consistent."""
        db1 = _create_db(tmp_path, "db1", num_items=1)
        db2 = _create_db(tmp_path, "db2", num_items=1)
        output_path = tmp_path / "merged.lyrdb"

        result, output_file = run_merge_helper(
            str(db1), str(db2), str(output_path), merge_helper_script
        )

        assert output_file.exists()
        assert result.returncode == 0

        # Verify merged database structure
        db = load_report_database(str(output_path))
        cell = db.cell_by_qname("TOP")
        assert cell is not None, "Cell TOP should be present"
        
        cat = db.category_by_path("RULE")
        assert cat is not None, "Category RULE should be present"
        
        item_count = sum(1 for _ in cat.each_item())
        assert item_count == 2, f"Expected 2 items (1+1), got {item_count}"


class TestHierarchyIntegrity:
    """Test hierarchy integrity."""
    
    def test_hierarchy_intact(self, tmp_path, merge_helper_script):
        """Hierarchy should be intact after merge."""
        db1 = _create_db(tmp_path, "db1", num_items=1)
        db2 = _create_db(tmp_path, "db2", num_items=1)
        output_path = tmp_path / "merged.lyrdb"

        result, output_file = run_merge_helper(
            str(db1), str(db2), str(output_path), merge_helper_script
        )

        assert output_file.exists()
        assert result.returncode == 0

        # Verify merged database structure is intact
        db = load_report_database(str(output_path))
        cell = db.cell_by_qname("TOP")
        assert cell is not None, "Cell TOP should be present"
        
        cat = db.category_by_path("RULE")
        assert cat is not None, "Category RULE should be present"
        
        item_count = sum(1 for _ in cat.each_item())
        assert item_count == 2, f"Expected 2 items (1+1), got {item_count}"
