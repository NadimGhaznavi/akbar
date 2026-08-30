---
title: Experiment Life Cycle
author_profile: true
layout: single
---

# Experiment Life Cycle

The Experiment Life Cycle (ELC) defines how Akbar prepares, runs, records, and
closes one experiment. Its purpose is to make every run deliberate, observable,
and reproducible.

## States

```text
ready → queued → running → completed
                    ├──→ failed
                    └──→ cancelled

queued/running → interrupted    (service restart)
```

- **Ready** — The service may accept one new experiment.
- **Queued** — The experiment has an ID, seed, configuration, and database
  record but has not entered the runner.
- **Running** — The simulation owns the active in-memory state.
- **Completed** — The final versioned result has been stored.
- **Failed** — Execution ended with a recorded error.
- **Cancelled** — A stop request ended execution cleanly.
- **Interrupted** — The service restarted while the experiment was queued or
  running.

Terminal states are `completed`, `failed`, `cancelled`, and `interrupted`.

## Start boundary

Starting an experiment must:

1. Confirm that no experiment is active.
2. Confirm that the previous terminal experiment has been acknowledged.
3. Atomically reserve the next seed from MariaDB.
4. Resolve the fixed experiment configuration with that seed.
5. Create the experiment record and assign its ID.
6. Start the in-memory runner.

Start requests are never queued. Repeated requests received while the service
is not ready must be rejected.

## Running boundary

The simulation hot loop uses only process memory. Game state, model weights,
replay memory, current score, and highscore are not read from or written to
MariaDB between or within epochs.

Each epoch publishes non-blocking telemetry over ZMQ. Telemetry is transient
and is not itself an experiment result.

## Result boundary

A completed experiment stores one versioned result document under its full
experiment ID. It contains:

- The assigned seed and resolved configuration.
- Aggregate score, loss, move, and replay metrics.
- Start, completion, and elapsed timing.
- Final lifecycle status.

Failed, cancelled, and interrupted experiments store their terminal status and
error or stop reason, but do not manufacture a completed result.

## Acknowledgement interlock

A terminal experiment must be explicitly acknowledged before the service
returns to `ready`. Completion alone does not authorize another run. This stops
bursts of stale or repeated start requests from launching experiments after a
fast run finishes.

The acknowledgement operation and whether it is available through MCP or only
through the administrative CLI remain to be implemented.

## Invariants

- At most one experiment is queued or running.
- Every accepted experiment has a durable ID, unique assigned seed, and
  configuration record before execution begins.
- Database access never enters the simulation hot loop.
- A result is factual runner output; evaluation is outside the current ELC.
- Full experiment IDs remain internal to the CLI, which displays four-character
  suffixes and rejects ambiguous historical matches.
