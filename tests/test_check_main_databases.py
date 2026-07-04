import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "check_main_databases.py"
    spec = importlib.util.spec_from_file_location("check_main_databases", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestCheckMainDatabases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mod = load_module()

    def test_contains_duplicate_ICAOs_clean(self):
        df = pd.DataFrame({"$ICAO": ["ABC123", "DEF456"]})
        self.assertEqual(self.mod.contains_duplicate_ICAOs(df), [])

    def test_contains_duplicate_ICAOs_reports_duplicates(self):
        df = pd.DataFrame({"$ICAO": ["ABC123", "ABC123", "DEF456"]})
        violations = self.mod.contains_duplicate_ICAOs(df)
        self.assertEqual(len(violations), 1)
        self.assertIn("2 duplicate ICAO codes", violations[0])

    def test_contains_valid_ICAO_hexes_reports_invalid(self):
        df = pd.DataFrame({"$ICAO": ["ABC123", "ZZZZZZ"]})
        violations = self.mod.contains_valid_ICAO_hexes(df)
        self.assertEqual(len(violations), 1)
        self.assertIn("1 '$ICAO' value that is not hexadecimal", violations[0])

    def test_contains_duplicate_regs_reports_duplicates_but_is_not_called_by_main(self):
        df = pd.DataFrame({"$ICAO": ["A1", "A2"], "$Registration": ["N1", "N1"]})
        violations = self.mod.contains_duplicate_regs(df)
        self.assertEqual(len(violations), 1)
        self.assertIn("2 duplicate registration numbers", violations[0])

    def test_main_reports_all_violations_in_one_pass(self):
        # Both a duplicate ICAO AND an invalid hex, in the same file - the old
        # sys.exit()-per-check version would abort on the first and never
        # report the second. Both must show up in a single run now.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "db.csv"
            pd.DataFrame({
                "$ICAO": ["ABC123", "ABC123", "ZZZZZZ"],
                "$Registration": ["N1", "N2", "N3"],
            }).to_csv(path, index=False)

            original = self.mod.MAIN_DATABASE_NAME
            self.mod.MAIN_DATABASE_NAME = str(path)
            try:
                buf = io.StringIO()
                with redirect_stdout(buf):
                    result = self.mod.main()
            finally:
                self.mod.MAIN_DATABASE_NAME = original

        self.assertEqual(result, 1)
        output = buf.getvalue()
        self.assertIn("duplicate ICAO codes", output)
        self.assertIn("not hexadecimal", output)

    def test_main_passes_clean_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "db.csv"
            pd.DataFrame({
                "$ICAO": ["ABC123", "DEF456"],
                "$Registration": ["N1", "N2"],
            }).to_csv(path, index=False)

            original = self.mod.MAIN_DATABASE_NAME
            self.mod.MAIN_DATABASE_NAME = str(path)
            try:
                result = self.mod.main()
            finally:
                self.mod.MAIN_DATABASE_NAME = original

        self.assertEqual(result, 0)

    def test_main_returns_error_for_missing_file(self):
        original = self.mod.MAIN_DATABASE_NAME
        self.mod.MAIN_DATABASE_NAME = "does/not/exist.csv"
        try:
            result = self.mod.main()
        finally:
            self.mod.MAIN_DATABASE_NAME = original
        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
