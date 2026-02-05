# Modal x ComfyUI with FLUX.2 Klein

Run **ComfyUI with FLUX.2 Klein** on Modal's cloud infrastructure. Uses Modal's free $30/month credits.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation) (recommended) or pip
- [Modal account](https://modal.com) (free signup)
- [Hugging Face account](https://huggingface.co) with accepted [FLUX.2-klein-9B license](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B)

## Quick Start

### 1. Clone and Install

```bash
git clone git@github.com:MubTaXim/MxC.git
cd MxC

# Create virtual environment
uv venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
uv pip install -r requirements.txt
```

### 2. Configure Authentication

```bash
# Authenticate with Modal
modal setup
```

Create a `.env` file in the project root:

```env
HF_TOKEN=your_huggingface_token_here
CIVITAI_API_TOKEN=your_civitai_token_here  # Optional
```

### 3. Run Setup

```bash
python setup_modal.py
```

### 4. Download FLUX.2 Klein 9B Models (One Command!)

This downloads **everything needed** to run FLUX.2 Klein 9B (~27GB total):

```bash
modal run download_flux_klein.py
```

**What gets downloaded:**
| Model | Size | Description |
|-------|------|-------------|
| `flux-2-klein-9b.safetensors` | ~18GB | Main diffusion model (best quality) |
| `qwen_3_8b_fp8mixed.safetensors` | ~8GB | Text encoder (FP8 mixed) |
| `flux2-vae.safetensors` | ~335MB | VAE |

> **Important:** You must accept the [FLUX.2-klein-9B license](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) on Hugging Face before downloading.

### 5. Launch ComfyUI

```bash
# Development mode (hot reload)
modal serve main.py

# Production deployment
modal deploy main.py
```

Open the URL provided in the terminal to access ComfyUI.
Load a workflow from `workflows/` folder and start generating!

---

## Downloading Additional Models

Models are stored in Modal's persistent volume. To download additional models:

```bash
# Open a shell in your Modal volume
modal shell --volume my-comfy-models

# Inside the shell, use wget/curl or huggingface-cli
# Example: Download a LoRA
cd /root/per_comfy-storage/loras
wget https://example.com/your-lora.safetensors

# IMPORTANT: Sync before exiting
sync
exit
```

### Model Directory Structure

Models should be placed in these directories inside the volume:

| Model Type | Path |
|------------|------|
| Checkpoints | `/root/per_comfy-storage/checkpoints/` |
| Diffusion Models | `/root/per_comfy-storage/diffusion_models/` |
| VAE | `/root/per_comfy-storage/vae/` |
| LoRAs | `/root/per_comfy-storage/loras/` |
| Text Encoders | `/root/per_comfy-storage/text_encoders/` |
| ControlNet | `/root/per_comfy-storage/controlnet/` |

---

## Included Custom Nodes

The following nodes are **automatically installed**:

| Node | Purpose |
|------|---------|
| ComfyUI-Crystools | Resource monitoring |
| ComfyUI-GGUF | GGUF model support |
| ComfyUI-LanPaint | Advanced inpainting |
| ComfyUI-BRIA_AI-RMBG | Background removal |
| ComfyUI-segment-anything-2 | SAM2 segmentation |
| ComfyUI-Florence2 | Auto-captioning |
| ComfyUI-KJNodes | Utility nodes |
| rgthree-comfy | UI enhancements |
| comfyui-easy-use | Workflow helpers |
| comfyui_essentials | Essential nodes |
| comfyui_controlnet_aux | ControlNet preprocessors |

---

## Included Workflows

Sample workflows are in the `workflows/` folder:

- **Flux Klein Single.json** - Basic single image generation
- **Flux Klein Multi.json** - Multi-image batch generation

Load them in ComfyUI via **Load** button or drag & drop.

---

## Configuration

Edit `config.ini` to customize:

```ini
[RESOURCES]
gpu_type = a10g          # a10g, t4, a100, etc.
max_containers = 1       # Concurrent containers
scaledown_window = 60    # Seconds before scaling down
timeout = 3600           # Max runtime in seconds

[FILESYSTEM]
volume_name = my-comfy-models  # Your Modal volume name
```

---

## Costs

With Modal's free $30/month credits:
- **A10G GPU**: ~$1.10/hour → ~27 hours/month free
- **T4 GPU**: ~$0.59/hour → ~50 hours/month free

The `scaledown_window` setting automatically stops containers when idle.

---

## Troubleshooting

**Model not found:**
- Verify model was downloaded with `modal run download_flux_klein.py`
- Check file paths in `extra_model_paths.yaml`

**Permission denied on Hugging Face:**
- Accept the model license on huggingface.co
- Verify `HF_TOKEN` in `.env` is correct

**Container timeout:**
- Increase `timeout` in `config.ini`

---


## License

MIT
