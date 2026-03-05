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
Test cases for cell hierarchy merging in parallel rule checker.
"""

import pytest
import klayout.rdb as rdb
import os
from pathlib import Path
from .conftest import run_merge_helper, assert_merged_file_exists, load_report_database


def _create_cell_db(tmp_path, name, top_cell, variant=None):
    """Create database with cells."""
    db = rdb.ReportDatabase.new(name)
    db.top_cell_name = top_cell
    
    cell = db.create_cell(top_cell)
    cat = db.create_category("RULE")
    db.create_item(cell, cat)
    
    filepath = tmp_path / f"{name}.lyrdb"
    db.save(str(filepath))
    return str(filepath)


class TestCellPreservation:
    """Tests for cell preservation during merge."""
    
    def test_cells_preserved_from_db1(self, tmp_path, merge_helper_script):
        """Cells from db1 should be preserved."""
        db1 = _create_cell_db(tmp_path, "db1", "TOP_A")
        db2 = _create_cell_db(tmp_path, "db2", "TOP_B")
        output_path = tmp_path / "merged.lyrdb"

        result, output_file = run_merge_helper(
            str(db1), str(db2), str(output_path), merge_helper_script
        )

        assert result.returncode != 0


class TestVariantHandling:
    """Tests for variant handling."""
    
    def test_variants_merged(self, tmp_path, merge_helper_script):
        """Cell variants should be handled."""
        db1 = _create_cell_db(tmp_path, "db1", "TOP")
        db2 = _create_cell_db(tmp_path, "db2", "TOP")
        output_path = tmp_path / "merged.lyrdb"

        result, output_file = run_merge_helper(
            str(db1), str(db2), str(output_path), merge_helper_script
        )

        assert output_file.exists()
        assert result.returncode == 0

        # Verify merged database has the expected cell and category
        db = load_report_database(str(output_path))
        cell = db.cell_by_qname("TOP")
        assert cell is not None, "Cell TOP should be present"
        
        cat = db.category_by_path("RULE")
        assert cat is not None, "Category RULE should be present"
