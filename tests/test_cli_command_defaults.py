import json
import sys
import unittest
from pathlib import Path

import click


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cli_ref"))

from get_public_commands import inspect_command


class CliCommandDefaultsTest(unittest.TestCase):
    def test_unset_click_defaults_are_json_serializable(self):
        command = click.Command(
            "example",
            params=[
                click.Option(["--project", "-p"]),
                click.Argument(["path"], required=False),
            ],
        )

        metadata = inspect_command(command)

        self.assertIsNone(metadata["options"][0]["default"])
        self.assertIsNone(metadata["arguments"][0]["default"])
        json.dumps(metadata)


if __name__ == "__main__":
    unittest.main()
