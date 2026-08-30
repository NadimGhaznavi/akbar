from __future__ import annotations

import unittest

from constants.DAkbar import DAkbar
from server.AkbarServer import build_command


class AkbarServerCommandTest(unittest.TestCase):
    def test_context_and_reasoning_limits_come_from_constants(self) -> None:
        command = build_command()
        context_index = command.index("--ctx-size")
        reasoning_index = command.index("--reasoning-budget")
        self.assertEqual(command[context_index + 1], str(DAkbar.CONTEXT_SIZE))
        self.assertEqual(
            command[reasoning_index + 1],
            str(DAkbar.REASONING_BUDGET),
        )
        self.assertNotIn("--mcp-servers-config", command)


if __name__ == "__main__":
    unittest.main()
