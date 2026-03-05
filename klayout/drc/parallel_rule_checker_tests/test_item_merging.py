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
Test cases for item merging in parallel rule checker.
"""

import pytest
import klayout.rdb as rdb
import os
from pathlib import Path
from .conftest import run_merge_helper, assert_merged_file_exists, load_report_database


def _create_db_with_items(tmp_path, name, cat_name, num_items):
    """Create database with items."""
    db = rdb.ReportDatabase.new(name)
    db.top_cell_name = "TOP"
    cell = db.create_cell("TOP")
    cat = db.create_category(cat_name)

    for _ in range(num_items):
        db.create_item(cell, cat)

    filepath = tmp_path / f"{name}.lyrdb"
    db.save(str(filepath))
    return str(filepath)


class TestItemTransfer:
    """Test that error items are transferred correctly."""

    def test_merge_transfers_items(self, tmp_path, merge_helper_script):
        """Items from db2 should be in merge result."""
        db1 = _create_db_with_items(tmp_path, "db1", "CAT1", 1)
        db2 = _create_db_with_items(tmp_path, "db2", "CAT2", 3)
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
        
        # Both categories should be present after merge
        cat1 = db.category_by_path("CAT1")
        cat2 = db.category_by_path("CAT2")
        assert cat1 is not None, "Category CAT1 should be present"
        assert cat2 is not None, "Category CAT2 should be present"
        
        # CAT1 should have 1 item (from db1)
        # CAT2 should have 3 items (from db2)
        cat1_count = sum(1 for _ in cat1.each_item())
        cat2_count = sum(1 for _ in cat2.each_item())
        assert cat1_count == 1, f"CAT1 should have 1 item, got {cat1_count}"
        assert cat2_count == 3, f"CAT2 should have 3 items, got {cat2_count}"

    def test_merge_valid_top_cells(self, tmp_path, merge_helper_script):
        """Merge completes with valid top cells."""
        db1 = _create_db_with_items(tmp_path, "db1", "CAT1", 1)
        db2 = _create_db_with_items(tmp_path, "db2", "CAT2", 2)
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
        
        cat1 = db.category_by_path("CAT1")
        cat2 = db.category_by_path("CAT2")
        assert cat1 is not None, "Category CAT1 should be present"
        assert cat2 is not None, "Category CAT2 should be present"
        
        cat1_count = sum(1 for _ in cat1.each_item())
        cat2_count = sum(1 for _ in cat2.each_item())
        assert cat1_count == 1, f"CAT1 should have 1 item, got {cat1_count}"
        assert cat2_count == 2, f"CAT2 should have 2 items, got {cat2_count}"
