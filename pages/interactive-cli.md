---
title: Interactive CLI
author_profile: true
layout: single
---

![Akbar](/pages/images/akbar.png)

# Run It

```sh
cd /opt/dev/llama.cpp
./build/bin/llama-cli \
    -m /opt/dev/models/quantized/Qwen3.5-4B-Q4_K_M.gguf \
    -ngl 99 \
    -c 4096 \
    --reasoning-budget 10 
```



