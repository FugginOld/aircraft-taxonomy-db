import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "taxonomy_constants.py"
    spec = importlib.util.spec_from_file_location("taxonomy_constants", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestTaxonomyConstants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mod = load_module()

    def write(self, tmp: str, name: str, content: str) -> Path:
        path = Path(tmp) / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_detect_delimiter_comma(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "a.csv", "a,b,c\n1,2,3\n")
            self.assertEqual(self.mod.detect_delimiter(path), ",")

    def test_detect_delimiter_tab(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "a.tsv", "a\tb\tc\n1\t2\t3\n")
            self.assertEqual(self.mod.detect_delimiter(path), "\t")

    def test_detect_delimiter_semicolon(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "a.csv", "a;b;c\n1;2;3\n")
            self.assertEqual(self.mod.detect_delimiter(path), ";")

    def test_detect_delimiter_comma_data_with_semicolons_stays_comma(self):
        # A comma-delimited file whose *data* contains semicolons should not
        # be misdetected, as long as commas still outnumber semicolons.
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "a.csv", "raw_value,match_key\n\"A320; A321\",A320\n")
            self.assertEqual(self.mod.detect_delimiter(path), ",")

    def test_is_hex_valid(self):
        self.assertTrue(self.mod.is_hex("A1B2C3"))
        self.assertTrue(self.mod.is_hex("000000"))

    def test_is_hex_invalid(self):
        self.assertFalse(self.mod.is_hex("ZZZZZZ"))
        self.assertFalse(self.mod.is_hex(""))

    def test_norm_lookup_key_casefolds_and_collapses_whitespace(self):
        self.assertEqual(self.mod.norm_lookup_key("  A320   Neo "), "a320 neo")

    def test_norm_match_key_uppercases_and_collapses_whitespace(self):
        self.assertEqual(self.mod.norm_match_key("  a320  "), "A320")

    def test_norm_lookup_key_and_norm_match_key_are_distinct(self):
        # The two must not be reduced to the same operation — see ADR-0001.
        value = "a320"
        self.assertNotEqual(self.mod.norm_lookup_key(value), self.mod.norm_match_key(value))

    def test_matchkey_re_accepts_valid_and_rejects_invalid(self):
        self.assertTrue(self.mod.MATCHKEY_RE.match("A320"))
        self.assertTrue(self.mod.MATCHKEY_RE.match("AB"))
        self.assertFalse(self.mod.MATCHKEY_RE.match("a320"))
        self.assertFalse(self.mod.MATCHKEY_RE.match("TOOLONGKEY"))

    def test_schema_constants_are_ordered_lists(self):
        self.assertEqual(self.mod.DB_COLUMNS[0], "$ICAO")
        self.assertEqual(self.mod.LOOKUP_COLUMNS[0], "match_key")
        self.assertEqual(self.mod.ALIAS_COLUMNS, ["raw_value", "match_key"])


if __name__ == "__main__":
    unittest.main()
