---
title: Architecture
author_profile: true
layout: single
---

# Architecture

Akbar is a set of independent systemd processes coordinated through durable
MariaDB state and narrow local protocols. No process owns another process's
lifecycle or relies on shared in-memory orchestration state.

## Services

- **`akbar.service`** runs inference-only `llama-server`. It accepts
  OpenAI-compatible chat-completion requests and does not execute tools.
- **`akbar-agentd.service`** polls MariaDB for queued agent turns. It claims one
  turn, runs the bounded model/function-calling loop, and persists the outcome.
- **`akbar-scheduler.service`** periodically attempts to enqueue a continuation
  prompt. It does not invoke, monitor, or restart the agent worker.
- **`akbar-experimentd.service`** owns experiment execution and live telemetry.
  It accepts at most one active experiment.

## Supporting components

- **MariaDB** is the durable coordination boundary. It stores agent turns,
  experiment configuration, lifecycle records, results, and the seed sequence.
- **MCP tool package (`tools`)** exposes project information, operating
  guidance, and experiment controls. The agent worker discovers its schemas and
  invokes it over stdio.
- **ZMQ control plane** carries versioned requests from MCP tools and the
  administrative CLI to the experiment service.
- **ZMQ telemetry** publishes non-blocking per-epoch updates from the experiment
  service.
- **Snake runner (`snake_lab`)** keeps the game, model, replay memory, and
  training loop in memory.
- **Administrative CLI (`scripts/akbar-cli.py`)** queries the authoritative
  experiment control plane without involving the language model.

## Scheduled agent turn

```text
Scheduler ── enqueue ──> MariaDB <── poll/claim ── Agent worker
                                                   │
                                         run bounded agent loop
                                                   │
                                        persist outcome to MariaDB
```

A transactional database gate permits at most one `queued` or `running` agent
turn. A scheduler tick is skipped when active work already exists. The worker
records the prompt, source, response or error, timestamps, and final status. A
turn left running by a worker restart becomes `interrupted`.

## Function-calling loop

```text
Agent worker ── discover schemas ──> MCP tools
     │
     ├── messages + schemas ───────> llama.cpp
     │                                  │
     │<──────────── tool calls ─────────┘
     ├── validate and execute ─────> MCP tools ──> ZMQ ──> Experiment service
     ├── append tool results
     └── repeat until final text or a configured limit
```

The worker accepts only discovered tool names and JSON-object arguments. It
bounds both tool-call rounds and total calls, and gives the complete agent turn
a deadline. Tool failures are returned to the model through MCP results; invalid
model output or exhausted limits fail the durable turn.

## State ownership

| State | Authority | Lifetime |
|---|---|---|
| Agent turn queue and outcomes | MariaDB | Durable |
| Experiment configuration and results | MariaDB | Durable |
| Experiment seed sequence | MariaDB | Durable |
| Active experiment and current metrics | Experiment service | Process lifetime |
| Snake model and replay memory | Snake runner | One experiment |
| Per-epoch telemetry | ZMQ PUB socket | Ephemeral |

## Boundaries

- Scheduler and agent polling is bounded and occurs outside simulation work.
- MariaDB is accessed at experiment lifecycle boundaries and for explicit
  historical queries, never within or between simulation epochs.
- The model service performs inference only; the agent worker owns tool
  orchestration.
- The scheduler and agent worker communicate only through MariaDB.
- No checkpoints, snapshots, CSV files, or per-epoch logs are written to disk.

See the [Experiment Life Cycle]({{ '/pages/elc.html' | relative_url }}) for run
states, deliverables, and launch-safety rules.
