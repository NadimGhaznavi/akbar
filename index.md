---
title: Akbar
author_profile: true
layout: single
---

![Akbar]({{ '/pages/images/akbar.png' | relative_url }})

# Akbar

Akbar is an AI agent backed by a locally hosted large language model. This project is about exploring what is possible.

---

# Runtime Harness

After downloading the [LLM Model]([Qwen3.5-4B](https://qwen.readthedocs.io/en/latest/) from [HuggingFace](https://huggingface.co/) and all of the software required to run it I was faced with the choice of **how** to run it.

I settled on [LLaMA.cpp](https://github.com/ggml-org/llama.cpp/tree/master/tools/server) which provides a *fast, lightweight, pure C/C++ HTTP server*. This game me a slick web interface where I can chat with the LLM directly.

I run the llama server from a Python program that in turn is being run as a Linux systemd service. Basically, the LLM runs as a Linux service locally on my machine.

---

# Scheduling Service




## Setup guides

- Akbar uses the [Qwen3.5-4B](https://qwen.readthedocs.io/en/latest/) model.
- [GPU driver and llama.cpp setup]({{ '/pages/driver-setup.html' | relative_url }})
- [Model setup]({{ '/pages/model-setup.html' | relative_url }})
- [Akbar installation and service management]({{ '/pages/installation.html' | relative_url }})
- [Architecture and experiment control plane]({{ '/pages/architecture.html' | relative_url }})
- [Experiment Life Cycle]({{ '/pages/elc.html' | relative_url }})
- [Interactive CLI]({{ '/pages/interactive-cli.html' | relative_url }})
