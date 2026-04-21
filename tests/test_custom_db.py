import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


def load_module(name: str):
    module_path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HEADER = [
    "$ICAO", "$Registration", "$Operator", "$Type", "$ICAO Type",
    "#CMPG", "$Tag 1", "$#Tag 2", "$#Tag 3", "Category",
]


def write_csv(path: Path, rows: list[dict], fieldnames=None):
    fieldnames = fieldnames or HEADER
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


class TestCheckCustomDb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mod = load_module("check_custom_db")

    def _run(self, path: Path) -> int:
        """Patch CUSTOM_DB and run main()."""
        original = self.mod.CUSTOM_DB
        self.mod.CUSTOM_DB = path
        try:
            return self.mod.main()
        finally:
            self.mod.CUSTOM_DB = original

    def test_header_only_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom.csv"
            write_csv(path, [])
            self.assertEqual(self._run(path), 0)

    def test_valid_row_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom.csv"
            write_csv(path, [{
                "$ICAO": "ABCDEF", "$Registration": "N1", "$Operator": "Test",
                "$Type": "Boeing 737", "$ICAO Type": "B737", "#CMPG": "Civ",
                "$Tag 1": "", "$#Tag 2": "", "$#Tag 3": "", "Category": "Passenger - Narrowbody",
            }])
            self.assertEqual(self._run(path), 0)

    def test_invalid_icao_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom.csv"
            write_csv(path, [{
                "$ICAO": "ZZZZZZ", "$Registration": "N1", "$Operator": "Test",
                "$Type": "Cessna", "$ICAO Type": "C172", "#CMPG": "Civ",
                "$Tag 1": "", "$#Tag 2": "", "$#Tag 3": "", "Category": "",
            }])
            self.assertEqual(self._run(path), 1)

    def test_duplicate_icao_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom.csv"
            row = {
                "$ICAO": "ABCDEF", "$Registration": "N1", "$Operator": "Test",
                "$Type": "Boeing 737", "$ICAO Type": "B737", "#CMPG": "Civ",
                "$Tag 1": "", "$#Tag 2": "", "$#Tag 3": "", "Category": "Passenger - Narrowbody",
            }
            write_csv(path, [row, row])
            self.assertEqual(self._run(path), 1)

    def test_invalid_category_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom.csv"
            write_csv(path, [{
                "$ICAO": "ABCDEF", "$Registration": "N1", "$Operator": "Test",
                "$Type": "Boeing 737", "$ICAO Type": "B737", "#CMPG": "Civ",
                "$Tag 1": "", "$#Tag 2": "", "$#Tag 3": "", "Category": "NOT A REAL CATEGORY",
            }])
            self.assertEqual(self._run(path), 1)

    def test_empty_category_allowed(self):
        """An empty Category must not fail — the normaliser fills it from the lookup."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom.csv"
            write_csv(path, [{
                "$ICAO": "ABCDEF", "$Registration": "N1", "$Operator": "Test",
                "$Type": "Boeing 737", "$ICAO Type": "B737", "#CMPG": "Civ",
                "$Tag 1": "", "$#Tag 2": "", "$#Tag 3": "", "Category": "",
            }])
            self.assertEqual(self._run(path), 0)

    def test_missing_required_column_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom.csv"
            # Write without the $ICAO column
            bad_header = [c for c in HEADER if c != "$ICAO"]
            write_csv(path, [], fieldnames=bad_header)
            self.assertEqual(self._run(path), 1)


class TestImportCustomDb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mod = load_module("import_custom_db")

    def test_header_only_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            custom = tmp_path / "custom.csv"
            main_db = tmp_path / "main.csv"
            write_csv(custom, [])
            write_csv(main_db, [])
            result = self.mod.main([
                "--custom-db", str(custom),
                "--main-db", str(main_db),
                "--lookup", "taxonomy/aircraft_type_lookup.csv",
                "--aliases", "taxonomy/aircraft_type_aliases.csv",
                "--review-dir", str(tmp_path / "review"),
            ])
            self.assertEqual(result, 0)
            # custom-db unchanged (still header-only)
            self.assertEqual(self.mod._count_data_rows(custom), 0)
            # main db unchanged
            self.assertEqual(self.mod._count_data_rows(main_db), 0)

    def test_missing_main_db_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            custom = tmp_path / "custom.csv"
            write_csv(custom, [{
                "$ICAO": "ABCDEF", "$Registration": "N1", "$Operator": "Test",
                "$Type": "Boeing 737", "$ICAO Type": "B737", "#CMPG": "Civ",
                "$Tag 1": "", "$#Tag 2": "", "$#Tag 3": "", "Category": "Passenger - Narrowbody",
            }])
            result = self.mod.main([
                "--custom-db", str(custom),
                "--main-db", str(tmp_path / "does_not_exist.csv"),
                "--lookup", "taxonomy/aircraft_type_lookup.csv",
                "--aliases", "taxonomy/aircraft_type_aliases.csv",
                "--review-dir", str(tmp_path / "review"),
            ])
            self.assertEqual(result, 1)

    def test_reset_to_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom.csv"
            write_csv(path, [{
                "$ICAO": "ABCDEF", "$Registration": "N1", "$Operator": "Test",
                "$Type": "Boeing 737", "$ICAO Type": "B737", "#CMPG": "Civ",
                "$Tag 1": "", "$#Tag 2": "", "$#Tag 3": "", "Category": "",
            }])
            # Confirm file has a data row before calling reset
            self.assertEqual(self.mod._count_data_rows(path), 1)
            self.mod._reset_to_header(path)
            self.assertEqual(self.mod._count_data_rows(path), 0)

    def test_unique_dest_increments(self):
        with tempfile.TemporaryDirectory() as tmp:
            review_dir = Path(tmp)
            # First call — file free, returns original name
            dest1 = self.mod._unique_dest(review_dir, "review.csv")
            self.assertEqual(dest1.name, "review.csv")
            # Create the file so the next call must use a suffix
            dest1.write_text("")
            dest2 = self.mod._unique_dest(review_dir, "review.csv")
            self.assertEqual(dest2.name, "review-1.csv")
            dest2.write_text("")
            dest3 = self.mod._unique_dest(review_dir, "review.csv")
            self.assertEqual(dest3.name, "review-2.csv")

    def test_load_existing_icaos(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "main.csv"
            write_csv(path, [
                {"$ICAO": "aAbBcC", "$Registration": "", "$Operator": "", "$Type": "",
                 "$ICAO Type": "", "#CMPG": "", "$Tag 1": "", "$#Tag 2": "", "$#Tag 3": "",
                 "Category": ""},
                {"$ICAO": "123456", "$Registration": "", "$Operator": "", "$Type": "",
                 "$ICAO Type": "", "#CMPG": "", "$Tag 1": "", "$#Tag 2": "", "$#Tag 3": "",
                 "Category": ""},
            ])
            icaos = self.mod._load_existing_icaos(path)
            self.assertIn("AABBCC", icaos)
            self.assertIn("123456", icaos)


if __name__ == "__main__":
    unittest.main()
