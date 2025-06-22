# Karakeep Installation Guide

## Overview

Bookmark application

**Environment Details:**
- **Platform**: Proxmox VE with LXC container
- **Container ID**: 619
- **Installation**: [Proxmox Helper Script](https://community-scripts.github.io/ProxmoxVE/scripts?id=karakeep)

## Config

For automatic tagging/summarization use following settings in `/etc/karakeep/karakeep.env`, which enables local Ollama instance utlisation. Leave other environment variables as they were.

```
# If you're planning to use ollama for tagging, uncomment the following lines:
OLLAMA_BASE_URL=http://192.168.60.80:11434
OLLAMA_KEEP_ALIVE="10m"

# You can change the models used by uncommenting the following lines, and changing them according to yo>
INFERENCE_TEXT_MODEL=gemma3:latest
INFERENCE_IMAGE_MODEL=llava:latest

# Additional inference defaults
INFERENCE_CONTEXT_LENGTH="2048"
INFERENCE_ENABLE_AUTO_TAGGING=true
INFERENCE_ENABLE_AUTO_SUMMARIZATION=true

INFERENCE_JOB_TIMEOUT_MS="180000"
```
