import importlib.util
from pathlib import Path
import unittest


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "weekly_update_pipeline_v3.py"
    spec = importlib.util.spec_from_file_location("weekly_update_pipeline_v3", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestWeeklyUpdatePipelineV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mod = load_module()

    def test_normalizer_output_paths_matches_get_output_paths(self):
        # Must stay identical to normalize_aircraft_v5.get_output_paths() -
        # that's the whole point of importing it instead of re-deriving the
        # suffix convention here.
        plane_file = Path("data/aircraft-taxonomy-db.csv")
        normalized, review = self.mod._normalizer_output_paths(plane_file)
        self.assertEqual(normalized, Path("data/aircraft-taxonomy-db_normalized.csv"))
        self.assertEqual(review, Path("data/aircraft-taxonomy-db_review.csv"))


if __name__ == "__main__":
    unittest.main()
