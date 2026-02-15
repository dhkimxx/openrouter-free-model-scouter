from __future__ import annotations

import unittest

from openrouter_free_model_scouter.cli import _merge_env_with_dotenv


class TestCliEnvMerge(unittest.TestCase):
    def test_empty_runtime_value_does_not_shadow_dotenv_value(self) -> None:
        merged = _merge_env_with_dotenv(
            {"OPENROUTER_API_KEY": "from-dotenv"},
            {"OPENROUTER_API_KEY": ""},
        )
        self.assertEqual(merged["OPENROUTER_API_KEY"], "from-dotenv")

    def test_non_empty_runtime_value_overrides_dotenv_value(self) -> None:
        merged = _merge_env_with_dotenv(
            {"OPENROUTER_API_KEY": "from-dotenv"},
            {"OPENROUTER_API_KEY": "from-env"},
        )
        self.assertEqual(merged["OPENROUTER_API_KEY"], "from-env")


if __name__ == "__main__":
    unittest.main()
