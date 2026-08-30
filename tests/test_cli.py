from __future__ import annotations

import importlib.util
import unittest
from io import StringIO
from pathlib import Path

from constants.DAkbar import DAkbar
from experiment.ExperimentProtocol import MessageType


CLI_PATH = Path(__file__).resolve().parent.parent / "scripts" / "akbar-cli.py"
CLI_SPEC = importlib.util.spec_from_file_location("akbar_cli", CLI_PATH)
if CLI_SPEC is None or CLI_SPEC.loader is None:
    raise RuntimeError(f"unable to load CLI module: {CLI_PATH}")
CLI_MODULE = importlib.util.module_from_spec(CLI_SPEC)
CLI_SPEC.loader.exec_module(CLI_MODULE)

AkbarCLI = CLI_MODULE.AkbarCLI
safe_for_display = CLI_MODULE.safe_for_display
short_id = CLI_MODULE.short_id

EXPERIMENT_ID = "12345678-1234-1234-1234-12345678a9f0"


class FakeClient:
    def __init__(self) -> None:
        self.requests = []

    def request(self, message_type, payload=None, experiment_id=None):
        self.requests.append((message_type, payload, experiment_id))
        if message_type is MessageType.PING:
            return {"service": "akbar-experimentd", "version": DAkbar.VERSION}
        if message_type is MessageType.GET_EXPERIMENT_COUNT:
            return {"experiment_count": 12}
        if message_type is MessageType.START_EXPERIMENT:
            return {"experiment_id": EXPERIMENT_ID, "status": "queued"}
        if message_type is MessageType.RESOLVE_EXPERIMENT_ID:
            return {"experiment_id": EXPERIMENT_ID}
        return {"experiment_id": experiment_id, "status": "completed"}


class CLIFormattingTest(unittest.TestCase):
    def test_full_ids_are_removed_from_nested_display_data(self) -> None:
        displayed = safe_for_display(
            {
                "experiment_id": EXPERIMENT_ID,
                "nested": [{"experiment_id": EXPERIMENT_ID}],
            }
        )
        self.assertEqual(displayed["experiment_id"], "[a9f0]")
        self.assertEqual(displayed["nested"][0]["experiment_id"], "[a9f0]")
        self.assertNotIn(EXPERIMENT_ID, str(displayed))
        self.assertEqual(short_id(EXPERIMENT_ID), "[a9f0]")

    def test_menu_starts_and_counts_without_printing_full_id(self) -> None:
        answers = iter(["2", "3", "8"])
        output = StringIO()
        client = FakeClient()
        status = AkbarCLI(
            client=client,
            input_function=lambda _prompt: next(answers),
            output=output,
        ).run()
        rendered = output.getvalue()
        self.assertEqual(status, 0)
        self.assertIn('"experiment_count": 12', rendered)
        self.assertIn('"experiment_id": "[a9f0]"', rendered)
        self.assertNotIn(EXPERIMENT_ID, rendered)

    def test_four_character_input_is_resolved_internally(self) -> None:
        answers = iter(["a9f0"])
        client = FakeClient()
        cli = AkbarCLI(client=client, input_function=lambda _prompt: next(answers))
        resolved = cli._select_id(required=True)
        self.assertEqual(resolved, EXPERIMENT_ID)
        self.assertEqual(
            client.requests[0],
            (MessageType.RESOLVE_EXPERIMENT_ID, {"suffix": "a9f0"}, None),
        )


if __name__ == "__main__":
    unittest.main()
