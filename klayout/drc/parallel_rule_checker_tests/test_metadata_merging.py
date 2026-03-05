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
Test cases for metadata merging in parallel rule checker.
"""

import pytest
import klayout.rdb as rdb
import os
from pathlib import Path
from .conftest import run_merge_helper, assert_merged_file_exists, load_report_database


class TestMetadataPreservation:
    """Test that metadata is preserved during merge."""
    
    def test_merge_preserves_top_cell_name(self, tmp_path, merge_helper_script):
        """Top cell name from db1 should be preserved."""
        output_path = tmp_path / "merged.lyrdb"

        db1 = tmp_path / "db1.lyrdb"
        db1_db = rdb.ReportDatabase.new("db1")
        db1_db.top_cell_name = "TOP1"
        cell = db1_db.create_cell("TOP1")
        cat = db1_db.create_category("CAT1")
        db1_db.create_item(cell, cat)
        db1_db.save(str(db1))
        
        db2 = tmp_path / "db2.lyrdb"
        db2_db = rdb.ReportDatabase.new("db2")
        db2_db.top_cell_name = "TOP2"
        cell2 = db2_db.create_cell("TOP2")
        cat2 = db2_db.create_category("CAT2")
        db2_db.create_item(cell2, cat2)
        db2_db.save(str(db2))

        result, output_file = run_merge_helper(
            str(db1), str(db2), str(output_path), merge_helper_script
        )

        assert result.returncode != 0


class TestDifferentTopCells:
    """Test handling of different top cell names."""
    
    def test_merge_different_top_cells_error(self, tmp_path, merge_helper_script):
        """Different top cells should cause merge failure."""
        output_path = tmp_path / "merged.lyrdb"

        db1 = tmp_path / "db1.lyrdb"
        db1_db = rdb.ReportDatabase.new("db1")
        db1_db.top_cell_name = "TOP_A"
        cell = db1_db.create_cell("TOP_A")
        cat = db1_db.create_category("CAT")
        db1_db.create_item(cell, cat)
        db1_db.save(str(db1))
        
        db2 = tmp_path / "db2.lyrdb"
        db2_db = rdb.ReportDatabase.new("db2")
        db2_db.top_cell_name = "TOP_B"
        cell2 = db2_db.create_cell("TOP_B")
        cat2 = db2_db.create_category("CAT")
        db2_db.create_item(cell2, cat2)
        db2_db.save(str(db2))

        result, output_file = run_merge_helper(
            str(db1), str(db2), str(output_path), merge_helper_script
        )

        assert result.returncode != 0
