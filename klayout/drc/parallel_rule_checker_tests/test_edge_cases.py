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
Test cases for edge cases in parallel rule checker merge.
"""

import pytest
import klayout.rdb as rdb
import os
from pathlib import Path
from .conftest import run_merge_helper, assert_merged_file_exists, load_report_database


def _create_basic_tmp(tmp_path, name, top_cell="TOP"):
    """Create a basic database."""
    db = rdb.ReportDatabase.new(name)
    db.top_cell_name = top_cell
    cell = db.create_cell(top_cell)
    cat = db.create_category("CAT")
    db.create_item(cell, cat)
    
    filepath = tmp_path / f"{name}.lyrdb"
    db.save(str(filepath))
    return str(filepath)


class TestEmptyDatabases:
    """Test merging with empty or minimal databases."""
    
    def test_merge_handles_both_empty(self, tmp_path, merge_helper_script):
        """Merging empty top cells should work if same."""
        db1 = _create_basic_tmp(tmp_path, "empty1", "")
        db2 = _create_basic_tmp(tmp_path, "empty2", "")
        output_path = tmp_path / "merged.lyrdb"

        result, output_file = run_merge_helper(
            str(db1), str(db2), str(output_path), merge_helper_script
        )

        assert output_file.exists()
        assert result.returncode == 0

        # Verify empty top cell is preserved
        db = load_report_database(str(output_path))
        assert db.top_cell_name == "", "Empty top cell name should be preserved"
        cell = db.cell_by_qname("")
        assert cell is not None, "Empty cell should be present"


class TestMismatchedTopCells:
    """Test handling of mismatched cell names."""
    
    def test_different_top_cells_fail(self, tmp_path, merge_helper_script):
        """Different top cells should cause failure."""
        db1 = _create_basic_tmp(tmp_path, "db1", "TOP_A")
        db2 = _create_basic_tmp(tmp_path, "db2", "TOP_B")
        output_path = tmp_path / "merged.lyrdb"

        result, output_file = run_merge_helper(
            str(db1), str(db2), str(output_path), merge_helper_script
        )

        assert result.returncode != 0
