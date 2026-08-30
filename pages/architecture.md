---
title: Architecture
author_profile: true
layout: single
---

# Architecture

Akbar has two long-running systemd services:

- `akbar.service` hosts the language model and MCP tools.
- `akbar-experimentd.service` owns experiment execution and live state.

The MCP tools send versioned requests to the experiment service over a local
ZeroMQ ROUTER/DEALER control channel. The service accepts one experiment at a
time and publishes non-blocking per-epoch telemetry on a separate PUB socket.

MariaDB records the durable experiment lifecycle and final result. Database
access is restricted to lifecycle boundaries—creation, start, completion,
failure, cancellation, and explicit historical lookups. The runner never reads
or writes MariaDB between or within epochs. Current status and highscore data
are served from memory, keeping database latency out of the simulation hot loop.

Each completed run stores a versioned result document under its `experiment_id`.
The document contains the resolved configuration, aggregate metrics, and timing
information. Raw per-epoch telemetry is not written to the result record.

The runner uses one fixed, deterministic, bounded configuration owned by the
experiment service. `start_experiment` accepts no configuration input. A
headless Snake game, linear NumPy Q-model, and bounded replay memory execute
entirely in process memory. No model checkpoints, replay snapshots, CSV files,
or per-epoch logs are written to disk.
