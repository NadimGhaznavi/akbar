from __future__ import annotations

import unittest

import tools.__main__  # noqa: F401 -- imports register the complete tool set
from tools.server import mcp


class ToolCompositionTest(unittest.IsolatedAsyncioTestCase):
    async def test_split_modules_register_the_complete_tool_set(self) -> None:
        names = {tool.name for tool in await mcp.list_tools()}
        self.assertEqual(
            names,
            {
                "doc_00_intro",
                "doc_01_overview",
                "doc_02_configure_experiment",
                "doc_03_run_experiment",
                "doc_04_review_results",
                "doc_05_design_next_experiment",
                "doc_06_architecture",
                "get_current_highscore",
                "get_experiment_config",
                "get_experiment_count",
                "get_experiment_database_schema",
                "get_experiment_status",
                "get_project_info",
                "get_project_version",
                "ping_experiment_service",
                "query_experiment_database",
                "set_experiment_learning_rate",
                "start_experiment",
                "stop_experiment",
            },
        )


if __name__ == "__main__":
    unittest.main()
