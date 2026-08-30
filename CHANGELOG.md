# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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
