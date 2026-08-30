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
- **Queued** — The experiment has an ID, baseline configuration, and database
  record but has not entered the runner.
- **Running** — One of the batch's simulations owns the active in-memory state.
- **Completed** — All 135 simulations reached a terminal state.
- **Failed** — Execution ended with a recorded error.
- **Cancelled** — A stop request ended execution cleanly.
- **Interrupted** — The service restarted while the experiment was queued or
  running.

Terminal states are `completed`, `failed`, `cancelled`, and `interrupted`.

## Start boundary

Starting an experiment must:

1. Confirm that no experiment is active.
2. Validate the submitted learning rate, initial epsilon, and epsilon decay.
3. Expand them into 27 nearby hyperparameter configurations.
4. Assign the five fixed seeds to every configuration.
5. Create the experiment record and start sequential simulation execution.

Start requests are never queued. Repeated requests received while the service
is not ready must be rejected.

## Configuration boundary

Every simulation runs for exactly 1,500 epochs. Each submitted hyperparameter
is varied by five percent into three values; bounded values shift inward when
necessary. Epsilon decay varies its decay amount (`1 - epsilon_decay`).

## Running boundary

The simulation hot loop uses only process memory. Game state, model weights,
replay memory, current score, and highscore are not read from or written to
MariaDB between or within epochs.

Each epoch publishes non-blocking telemetry over ZMQ. Telemetry is transient
and is not itself an experiment result.

## Result boundary

A completed simulation stores one versioned raw result document linked to its
parent experiment ID. It contains:

- The assigned seed and resolved configuration.
- The runner's score, loss, move, and replay metrics.
- Start, completion, and elapsed timing.
- Final lifecycle status.

Failed, cancelled, and interrupted experiments store their terminal status and
error or stop reason, but do not manufacture a completed result.

Akbar discovers the schema and issues arbitrary read-only SQL to retrieve,
filter, join, group, aggregate, or order these rows. The persistence layer does
not decide which results are best and does not pre-aggregate the evidence.

## Invariants

- At most one experiment is queued or running.
- Every accepted experiment has a durable ID and baseline configuration before
  execution begins.
- Every simulation has its own durable ID, full effective configuration, fixed
  seed, status, and raw result or error.
- Every configuration change is validated and persisted before it becomes
  active.
- Database access never enters the simulation hot loop.
- A result is factual runner output; evaluation is outside the current ELC.
- Full experiment IDs remain internal to the CLI, which displays four-character
  suffixes and rejects ambiguous historical matches.
