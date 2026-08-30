# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.5.1] - 2026-08-30 @ 01:33

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
- Headless deterministic Snake gameplay with an in-memory NumPy Q-model,
  bounded replay training, and real per-epoch score and loss telemetry.
- MCP experiment-count tool backed by persisted MariaDB experiment records.

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
