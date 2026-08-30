---
title: Architecture
author_profile: true
layout: single
---

# Architecture

Akbar separates deterministic workflow management from experimental judgment.
Python decides when and how work proceeds. The language model reviews evidence
and proposes what experiment to run next.

Independent systemd services coordinate through durable MariaDB state and
narrow local APIs. No service supervises another service or relies on shared
in-memory orchestration state.

## Services

- **`akbar.service`** runs `llama-server` for interactive web chat and
  OpenAI-compatible inference. The scheduler uses its inference API, while MCP
  configuration gives interactive web-chat turns access to Akbar's tools.
- **`akbar-scheduler.service`** owns the experiment workflow. It checks whether
  work is active, loads previous results, requests one structured proposal from
  the language model, validates and persists the decision, and starts exactly
  one experiment.
- **`akbar-experimentd.service`** owns experiment execution and live telemetry.
  It accepts at most one active experiment and runs it entirely in memory.

There is no autonomous agent-worker service or general-purpose agent-turn
queue in the scheduled path.

## Supporting components

- **MariaDB** stores experiment configuration, planning decisions, batch
  lifecycle records, and one raw result per simulation run.
- **MCP tool package (`tools`)** supports interactive web chat and project
  inspection. It is not responsible for scheduled workflow execution.
- **ZMQ control plane** carries versioned experiment requests and replies.
- **ZMQ telemetry** publishes non-blocking per-epoch updates from the experiment
  service.
- **Snake runner (`snake_lab`)** keeps the game, model, replay memory, and
  training loop in memory.
- **Administrative CLI (`scripts/akbar-cli.py`)** queries the authoritative
  experiment control plane without involving the language model.

## Scheduled workflow

```text
wait for scheduler tick
        │
        ▼
check authoritative experiment state
        │
        ├── queued/running ──> wait for next tick
        │
        └── idle/terminal
                │
                ▼
load active config and bounded raw simulation results
                │
                ▼
ask LLM to review old experiments and propose next config
                │
                ▼
parse and validate one structured proposal
                │
                ▼
persist config, rationale, and evidence references
                │
                ▼
start exactly one experiment through ZMQ
                │
                └──> wait for next tick
```

Workflow steps are ordinary Python operations. The language model does not
decide whether to wait, retrieve data through repeated tool calls, or invoke the
experiment service.

## Planning contract

The scheduler gives the language model:

- The active configuration and its enforced limits.
- A bounded set of previous completed experiments.
- Each run's configuration, seed, score metrics, and completion time.
- An instruction to compare the old experiments and design the next deliberate
  experiment.

The language model returns one schema-constrained proposal:

```json
{
  "learning_rate": 0.0008,
  "epsilon_start": 0.9,
  "epsilon_decay": 0.995,
  "rationale": "The previous results justify testing a smaller learning rate."
}
```

Python rejects malformed or out-of-range proposals. A rejected proposal does
not start an experiment and may be retried on a later tick. A valid proposal is
persisted before its experiment is launched.

## Experiment execution

The experiment service snapshots the three submitted hyperparameters and creates
a lifecycle record. It varies each value by five percent to form a 3 x 3 x 3
grid, then runs all 27 configurations with seeds 1970 through 1974. The resulting
135 simulations each run for exactly 1,500 epochs and persist separate raw result
rows. Epsilon decay is perturbed in terms of `1 - epsilon_decay`, preserving
useful resolution near one.

The service publishes transient epoch telemetry over ZMQ and persists each
simulation result only after that simulation leaves its hot loop.

## State ownership

| State | Authority | Lifetime |
|---|---|---|
| Active configuration | MariaDB | Durable |
| Planning proposal and rationale | MariaDB | Durable |
| Experiment batch lifecycle | MariaDB | Durable |
| Individual simulation configurations and results | MariaDB | Durable |
| Active experiment and current metrics | Experiment service | Process lifetime |
| Snake model and replay memory | Snake runner | One experiment |
| Per-epoch telemetry | ZMQ PUB socket | Ephemeral |

## Boundaries

- Scheduler polling and planning occur outside simulation work.
- MariaDB is accessed at experiment lifecycle boundaries and for explicit
  historical queries, never within or between simulation epochs.
- At most one experiment may be queued or running.
- One valid planning proposal launches one 135-simulation experiment.
- Akbar may issue arbitrary single-statement read-only SQL for analysis; the
  experiment layer does not rank or aggregate results for him.
- Interactive chat and scheduled planning share the inference server but have
  independent workflows.
- Interactive MCP tool use cannot become an implicit scheduled-workflow
  dependency.
- No checkpoints, snapshots, CSV files, or per-epoch logs are written to disk.

See the [Experiment Life Cycle]({{ '/pages/elc.html' | relative_url }}) for run
states, deliverables, and launch-safety rules.
