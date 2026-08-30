---
title: Model Setup
author_profile: true
layout: single
---

# Setup a venv environment

```sh
python3 -m venv venv_akbar
. venv_akbar/bin/activate
```

# Install Hugging Face Hub

From within the venv environment:

```sh
pip install huggingface_hub
```

# Download the Model



```sh
git lfs install
git clone --depth 1 https://huggingface.co/Qwen/Qwen3.5-4B
```

This will take a while, it's about 18 Gb. Sanity check git:

```sh
$ git status
On branch main
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean

$ git lfs ls-files
26a93f066e * model.safetensors-00001-of-00002.safetensors
cb544bd9bf * model.safetensors-00002-of-00002.safetensors
5f9e4d4901 * tokenizer.json

$ git rev-parse HEAD
851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a
dan@wintermute:/opt/dev/Qwen3.5-4B$ 
```

# Populate the venv

```sh
$ cd /opt/lamma.cpp
# pip install -r requirements.txt
```

# Create the GGUF

```sh
cd /opt/dev/llama.cpp

python convert_hf_to_gguf.py \
    /opt/dev/Qwen3.5-4B \
    --outfile /opt/dev/models/intermediate/Qwen3.5-4B-BF16.gguf \
    --outtype bf16

    .
    .
    .
INFO:hf-to-gguf:Model successfully exported to /opt/dev/models/intermediate/Qwen3.5-4B-BF16.gguf

```

## Quanize it

```sh
./build/bin/llama-quantize \
    /opt/dev/models/intermediate/Qwen3.5-4B-BF16.gguf \
    /opt/dev/models/Qwen3.5-4B-Q4_K_M.gguf \
    Q4_K_M
```