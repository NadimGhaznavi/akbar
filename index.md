---
title: Akbar
author_profile: true
layout: single
---

![Akbar]({{ '/pages/images/akbar.png' | relative_url }})

# The Project

Akbar is a locally hosted AI research system built to do more than chat. It turns
a compact language model running on modest hardware into the reasoning component
of a controlled, repeatable experimentation platform. The model studies the
project's accumulated results, forms an evidence-backed hypothesis, and proposes
the next experiment while conventional software enforces the rules and owns the
workflow.

At the centre of the system is a deterministic scheduler that coordinates the
LLM, a durable MariaDB experiment history, and an independent experiment
service. It gives Akbar bounded, read-only access to the evidence, validates each
structured proposal, prevents accidental duplicate work, records the rationale
and success criteria, and launches one experiment at a time. This separation
lets the model exercise judgment without giving up reproducibility, operational
safety, or a clear audit trail.

The proving ground is **Snake Lab**, a headless reinforcement-learning sandbox
built from the game, a NumPy Q-learning agent, replay memory, and a training
loop. Each proposal expands into a controlled 27-simulation hyperparameter
study, with fixed methodology, live ZMQ telemetry, and raw results persisted for
future analysis. Around that core we built systemd-managed services, a trusted
administrative CLI, MCP tools, installation and upgrade tooling, and Aknet —a
read-only project intranet the agent can consult. Together, these pieces form a
complete closed loop: investigate, hypothesize, run, measure, learn, and repeat,
entirely on local infrastructure.

---

# Runtime Harness

After downloading the [LLM Model]([Qwen3.5-4B](https://qwen.readthedocs.io/en/latest/) from [HuggingFace](https://huggingface.co/) and all of the software required to run it I was faced with the choice of **how** to run it.

I settled on [LLaMA.cpp](https://github.com/ggml-org/llama.cpp/tree/master/tools/server) which provides a *fast, lightweight, pure C/C++ HTTP server*. This game me a slick web interface where I can chat with the LLM directly.

I run the llama server from a Python program that in turn is being run as a Linux systemd service. Basically, the LLM runs as a Linux service locally on my machine.

---

# Setup guides

- Akbar uses the [Qwen3.5-4B](https://qwen.readthedocs.io/en/latest/) model.
- [GPU driver and llama.cpp setup]({{ '/pages/driver-setup.html' | relative_url }})
- [Model setup]({{ '/pages/model-setup.html' | relative_url }})
- [Akbar installation and service management]({{ '/pages/installation.html' | relative_url }})
- [Architecture and experiment control plane]({{ '/pages/architecture.html' | relative_url }})
- [Experiment Life Cycle]({{ '/pages/elc.html' | relative_url }})
- [Interactive CLI]({{ '/pages/interactive-cli.html' | relative_url }})
