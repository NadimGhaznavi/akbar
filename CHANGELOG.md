# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.11.4] - 2026-08-30 @ 07:08

## [0.11.3] - 2026-08-30 @ 06:49

### Changed

- Replaced the ineffective OpenAI request-level reasoning budget with Qwen's
  supported `enable_thinking=false` chat-template control for scheduled
  schema-only planning responses.

---

## [0.11.2] - 2026-08-30 @ 06:45

### Changed

- Disabled reasoning for the schema-constrained scheduler request so Qwen
  reserves its completion allowance for final proposal JSON, restored strict
  JSON decoding, and added structural diagnostics for contract errors.

---

## [0.11.1] - 2026-08-30 @ 06:39

### Changed

- Made scheduled proposal decoding accept plain, fenced, text-part, or
  prose-wrapped JSON from llama.cpp, with a bounded response preview in error
  logs when no proposal object can be recovered.

---

## [0.11.0] - 2026-08-30 @ 06:33

### Added

- MariaDB-backed experiment planning records containing each structured
  proposal, rationale, supporting result summaries, and launched experiment ID.

### Changed

- Replaced agent-managed scheduling with a deterministic thin slice that checks
  experiment state, loads the active configuration and recent results, asks the
  LLM once for a schema-constrained proposal, validates and persists it, and
  starts exactly one experiment.

### Removed

- The autonomous agent-worker service, general-purpose function-calling loop,
  durable agent-turn queue and tables, and their installation and systemd
  artifacts.

---

## [0.10.6] - 2026-08-30 @ 06:14

### Changed

- Limited scheduled investigation to three capped model responses before the
  worker performs its own authoritative status check and starts one experiment
  when idle, preventing model deliberation from monopolizing the scheduler.

---

## [0.10.5] - 2026-08-30 @ 06:04

### Changed

- Required scheduled agent turns to confirm active work or successfully start an
  experiment before they can complete, with corrective continuation and visible
  MCP tool-call logging when Akbar tries to stop prematurely.

---

## [0.10.4] - 2026-08-30 @ 05:46

### Changed

- Made an empty experiment service report authoritative `ready` status instead
  of raising a tool error during Akbar's initial state check.

---

## [0.10.3] - 2026-08-30 @ 05:38

### Changed

- Made the administrative CLI a strictly read-only observability interface and
  added active-configuration and recent-result views.

---

## [0.10.2] - 2026-08-30 @ 05:31

### Changed

- Set scheduler startup and recurring continuation checks to 15 seconds, with
  MariaDB duplicate suppression preventing queued agent-turn buildup.

---

## [0.10.1] - 2026-08-30 @ 05:21

### Changed

- Restored llama-server MCP access for interactive web chat while retaining the
  independent agent worker for scheduled MCP orchestration.

---

## [0.10.0] - 2026-08-30 @ 05:14

### Added

- Independent scheduler and agent-worker services coordinated through a durable
  MariaDB turn queue, with atomic duplicate suppression, bounded polling and
  execution, clean interruption, and persisted outcomes.
- An explicit bounded function-calling loop that discovers MCP tools, sends
  their schemas to llama.cpp, validates model tool calls, executes them through
  MCP, and returns tool results to the model until a final response.

### Changed

- Split the monolithic MCP tool file into project, documentation, experiment,
  and server modules with a package-based launch entry point.
- Moved scheduled MCP orchestration into the independent agent worker.
- Centralized MariaDB connection construction for experiment persistence and
  durable process coordination.
- Encoded an evidence-driven scheduled workflow that checks active work,
  reviews historical results, justifies configuration changes, starts at most
  one experiment, and persists the decision rationale with the agent turn.
- Exposed a concise operational architecture guide through Akbar's numbered MCP
  self-documentation tools.

### Removed

- The installed top-level `tools.py` compatibility entry point.

---

## [0.9.0] - 2026-08-30 @ 04:11

### Added

- Bounded MCP result-history listing with compact summaries of the most recent
  completed experiments and their IDs, configuration, and score metrics,
  accompanied by numbered self-documentation for Akbar.

---

## [0.8.1] - 2026-08-30 @ 04:03

### Changed

- Increased the llama.cpp context window to 32,768 tokens and capped Qwen's
  reasoning phase at 2,048 tokens to preserve room for conversation, tool calls,
  and final responses.

---

## [0.8.0] - 2026-08-30 @ 03:39

### Changed

- Replaced the fixed epoch and learning-rate settings with a validated active
  configuration persisted in MariaDB and loaded at service startup.
- Set the minimum and default experiment length to 50 epochs while retaining
  the working `0.001` learning-rate default; older lower persisted values are
  promoted on startup.

### Added

- Experiment Life Cycle specification covering states, persistence boundaries,
  result deliverables, invariants, and the planned acknowledgement interlock.
- MCP tools to inspect the active experiment configuration and independently set
  epochs or learning rate within enforced bounds.
- Numbered MCP self-documentation tools that explain Akbar's experiment,
  configuration, and run workflow to the model.

---

## [0.7.1] - 2026-08-30 @ 02:52

### Changed

- Made experiment seeds database-assigned, durable, and automatically
  incrementing so consecutive runs are unique by default.

---

## [0.7.0] - 2026-08-30 @ 02:30

### Changed

- Condensed the architecture guide into a component and boundary reference.
- Made `scripts/akbar-cli.py` the canonical CLI source and installed path.
- Added the CLI, installer, and upgrade entry points to the installed
  application manifest under `/opt/akbar/scripts`.

### Removed

- The indirect `tools/cli.py` source location.

---

## [0.6.0] - 2026-08-30 @ 02:14

### Changed

- Replaced destructive reinstallation with a dedicated upgrade workflow that
  preserves MariaDB data, experiment history, database credentials, service
  identity, virtual environment, and service enablement state.

### Added

- Trusted menu-driven experiment CLI with direct control-plane access,
  four-character ID display, safe suffix resolution, and DB-backed count and
  result views.

### Removed

- Unused runtime-configuration parsing, duplicate endpoint constants, and an
  unreferenced state-store accessor.

---

## [0.5.2] - 2026-08-30 @ 01:55

### Changed

- Made installation, reinstallation, and uninstallation explicitly destructive:
  existing application files, services, credentials, and MariaDB data are
  removed rather than preserved.

---

## [0.5.1] - 2026-08-30 @ 01:48

### Added

- MCP experiment-count tool backed by persisted MariaDB experiment records.

---

## [0.5.0] - 2026-08-30 @ 01:33

### Added

- Headless deterministic Snake gameplay with an in-memory NumPy Q-model,
  bounded replay training, and real per-epoch score and loss telemetry.

---

## [0.4.0] - 2026-08-30 @ 01:13

### Changed

- Moved MariaDB settings into a dedicated database constants class.
- Replaced the experiment-service stub with an end-to-end, versioned ZMQ control
  plane and a deterministic first experiment runner.
- Limited experiment starts to the service-owned fixed default configuration;
  runtime configuration loading is intentionally deferred.
- Kept live experiment state and per-epoch telemetry in memory, with MariaDB
  persistence confined to lifecycle boundaries outside the simulation hot loop.

### Added

- MCP tools to start, inspect, stop, and health-check experiments, including a
  database-free current-highscore query.
- MariaDB experiment lifecycle records, non-blocking ZMQ PUB telemetry, service
  integration tests, and experiment architecture documentation.
- Versioned run-result documents stored and retrieved by experiment ID, with
  resolved configuration, aggregate metrics, and timing information.

---

## [0.3.0] - 2026-08-30 @ 00:24

### Added

- MCP project-information tool providing Akbar's purpose, version, and
  administrator name.

---

## [0.2.3] - 2026-08-30 @ 00:19

### Added

- Initial systemd-managed experiment service with a stubbed Python server and
  clean process lifecycle.

---

## [0.2.2] - 2026-08-29 @ 23:16

### Changed

- Release usage now suggests the next logical `feat/maint-X.Y.Z` branch.

### Added

- MariaDB provisioning with a dedicated database, scoped database account, and
  protected service credentials.

---

## [0.2.1] - 2026-08-29 @ 23:12

### Changed

- Connected `llama-server` to Akbar's installed MCP configuration so the model
  server can discover and expose Akbar's MCP tools.
- Release headings now include the local release time.

---

## [0.2.0] - 2026-08-30

- Release script enhancements

---

## [0.1.0] - 2026-08-30

### Added

- Initial Akbar server for running the configured Qwen model through
  `llama-server`.
- Systemd service running Akbar from a dedicated virtual environment and
  unprivileged service account.
- Python installation, update, and removal tools for managing the complete
  service lifecycle under `/opt/akbar`.
- MCP configuration and an initial tool for reporting the installed Akbar
  version.
- Automated semantic-version release workflow with changelog promotion and Git
  tagging.
- Setup and architecture documentation for the GPU, model, interactive CLI,
  and planned experiment harness.

### Changed

- Centralized installation, model-server, network, and version settings in the
  shared Akbar constants.
