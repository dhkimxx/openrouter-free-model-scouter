from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from openrouter_free_model_scouter.config import load_simple_dotenv_mapping


class TestConfigLoader(unittest.TestCase):
    def test_load_simple_dotenv_mapping_parses_key_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / ".env"
            file_path.write_text(
                "OPENROUTER_SCOUT_TIMEOUT_SECONDS=15\n# comment\nexport OPENROUTER_SCOUT_CONCURRENCY=4\n",
                encoding="utf-8",
            )

            mapping = load_simple_dotenv_mapping(file_path)
            self.assertEqual(mapping["OPENROUTER_SCOUT_TIMEOUT_SECONDS"], "15")
            self.assertEqual(mapping["OPENROUTER_SCOUT_CONCURRENCY"], "4")


if __name__ == "__main__":
    unittest.main()
