"""
Download ALL models for FLUX.2 Klein 9B to Modal volume

🌩️  THIS RUNS IN MODAL CLOUD - NOT ON YOUR LOCAL MACHINE
📥 Downloads happen in Modal's infrastructure directly to your volume
💾 Uses ZERO local disk space
⚡ Uses aria2 with 16 parallel connections for FAST downloads

Downloads:
  - flux-2-klein-9b.safetensors (~18GB) - Main diffusion model (requires HF license)
  - qwen_3_8b_fp8mixed.safetensors (~8GB) - Text encoder (FP8 mixed precision)
  - flux2-vae.safetensors (~335MB) - VAE

Run: modal run download_flux_klein.py
"""
import modal
import os

# Hardcode values
VOLUME_NAME = "my-comfy-models"
VOLUME_MOUNT = "/root/per_comfy-storage"

# Models to download
MODELS = {
    # FLUX.2 Klein 9B - Main model (REQUIRES HF LICENSE)
    "flux-2-klein-9b.safetensors": {
        "url": "https://huggingface.co/black-forest-labs/FLUX.2-klein-9B/resolve/main/flux-2-klein-9b.safetensors",
        "dir": "diffusion_models",
        "requires_auth": True,
        "size": "~18GB"
    },
    # Qwen 3.8B FP8 Mixed Text Encoder (public) - Recommended for FLUX.2 Klein
    "qwen_3_8b_fp8mixed.safetensors": {
        "url": "https://huggingface.co/Comfy-Org/vae-text-encorder-for-flux-klein-9b/resolve/main/split_files/text_encoders/qwen_3_8b_fp8mixed.safetensors",
        "dir": "text_encoders",
        "requires_auth": False,
        "size": "~8GB"
    },
    # FLUX2 VAE (public)
    "flux2-vae.safetensors": {
        "url": "https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors",
        "dir": "vae",
        "requires_auth": False,
        "size": "~335MB"
    },
}

# Read HF token from .env file locally (only runs on your machine, not in Modal)
def get_hf_token():
    from pathlib import Path
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("HF_TOKEN"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.getenv("HF_TOKEN")

# Create app with volume
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("wget", "curl", "aria2")
)

app = modal.App(name="flux-klein-downloader")
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)


@app.function(
    image=image,
    volumes={VOLUME_MOUNT: volume},
    timeout=7200  # 2 hours for large downloads
)
def download_all_models(hf_token: str):
    """Download all FLUX.2 Klein 9B models with aria2 parallel downloads"""
    import subprocess
    
    print("=" * 70)
    print("🚀 FLUX.2 KLEIN 9B - COMPLETE MODEL DOWNLOAD")
    print("=" * 70)
    print()
    print("📦 Models to download:")
    for name, info in MODELS.items():
        auth = "🔐 (requires HF token)" if info["requires_auth"] else "🌐 (public)"
        print(f"   • {name} ({info['size']}) {auth}")
    print()
    print("=" * 70)
    
    failed = []
    
    for filename, info in MODELS.items():
        local_dir = f"{VOLUME_MOUNT}/{info['dir']}"
        output_path = f"{local_dir}/{filename}"
        
        # Skip if already exists
        if os.path.exists(output_path):
            size_gb = os.path.getsize(output_path) / (1024**3)
            print(f"⏭️  Skipping {filename} (already exists, {size_gb:.2f} GB)")
            continue
        
        print()
        print(f"📥 Downloading: {filename}")
        print(f"   Size: {info['size']}")
        print(f"   Destination: {output_path}")
        
        os.makedirs(local_dir, exist_ok=True)
        
        # Build aria2c command
        cmd = [
            "aria2c",
            "-x", "16",
            "-s", "16",
            "-k", "1M",
            "-c",
            "--file-allocation=none",
            "-d", local_dir,
            "-o", filename,
        ]
        
        # Add auth header if required
        if info["requires_auth"]:
            cmd.append(f"--header=Authorization: Bearer {hf_token}")
        
        cmd.append(info["url"])
        
        result = subprocess.run(cmd, capture_output=False)
        
        if result.returncode == 0:
            print(f"   ✅ {filename} downloaded successfully!")
        else:
            print(f"   ❌ {filename} download failed!")
            if info["requires_auth"]:
                print(f"   💡 Make sure you accepted the license:")
                print(f"      https://huggingface.co/black-forest-labs/FLUX.2-klein-9B")
            failed.append(filename)
    
    # Commit volume
    volume.commit()
    
    print()
    print("=" * 70)
    if failed:
        print(f"⚠️  COMPLETED WITH ERRORS")
        print(f"   Failed: {', '.join(failed)}")
    else:
        print("✅ ALL MODELS DOWNLOADED SUCCESSFULLY!")
    print()
    print("📂 Models saved to Modal volume:")
    print(f"   • {VOLUME_MOUNT}/diffusion_models/flux-2-klein-9b.safetensors")
    print(f"   • {VOLUME_MOUNT}/text_encoders/qwen_3_8b_fp8mixed.safetensors")
    print(f"   • {VOLUME_MOUNT}/vae/flux2-vae.safetensors")
    print("=" * 70)
    
    if failed:
        raise Exception(f"Failed to download: {', '.join(failed)}")


@app.local_entrypoint()
def main():
    print()
    print("🚀 FLUX.2 Klein 9B - Complete Model Download")
    print("=" * 50)
    
    hf_token = get_hf_token()
    if not hf_token:
        print("❌ HF_TOKEN not found!")
        print("   Add it to your .env file: HF_TOKEN=hf_xxx...")
        print()
        print("💡 Get your token from: https://huggingface.co/settings/tokens")
        print("💡 Accept FLUX license: https://huggingface.co/black-forest-labs/FLUX.2-klein-9B")
        return
    
    print("✅ HF Token found")
    print("📦 Building image and starting download...")
    print()
    
    download_all_models.remote(hf_token)
    
    print()
    print("✨ Done! All models saved to Modal volume.")
    print("   Run 'modal serve main.py' to start ComfyUI!")
