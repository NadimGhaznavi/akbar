---
title: Architecture
author_profile: true
layout: single
---

# Architecture

## Components

- **Model service (`akbar.service`)** — Runs `llama-server`, the local language
  model, and Akbar's MCP tools.
- **Experiment service (`akbar-experimentd.service`)** — Owns experiment
  execution, cancellation, and live state. It permits one active run.
- **MCP tools (`tools.py`)** — Let the model control and inspect experiments.
- **Administrative CLI (`scripts/akbar-cli.py`)** — Displays authoritative
  service data without involving the language model.
- **ZMQ control plane** — Carries versioned requests from MCP tools and the CLI
  to the experiment service using ROUTER/DEALER sockets.
- **ZMQ telemetry** — Publishes non-blocking per-epoch data from a PUB socket.
- **MariaDB** — Stores experiment lifecycle records and completed, versioned
  results by experiment ID. It also atomically assigns an incrementing seed to
  each new experiment.
- **Snake runner (`snake_lab`)** — Runs the headless game, NumPy Q-model, and
  bounded replay training entirely in memory with a persisted, bounded
  configuration.

## Boundaries

MariaDB is accessed only at lifecycle boundaries and for explicit historical
queries—never within or between simulation epochs. Live state, model weights,
replay memory, and telemetry remain in memory. No checkpoints, snapshots, CSV
files, or per-epoch logs are written to disk.

See the [Experiment Life Cycle]({{ '/pages/elc.html' | relative_url }}) for run
states, deliverables, and launch-safety rules.
