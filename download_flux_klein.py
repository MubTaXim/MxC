"""
Download FLUX.2-klein-9B model to Modal volume

🌩️  THIS RUNS IN MODAL CLOUD - NOT ON YOUR LOCAL MACHINE
📥 Downloads happen in Modal's infrastructure directly to your volume
💾 Uses ZERO local disk space
⚡ Uses aria2 with 16 parallel connections for FAST downloads

Run: modal run download_flux_klein.py
"""
import modal
import os

# Hardcode values
VOLUME_NAME = "my-comfy-models"
VOLUME_MOUNT = "/root/per_comfy-storage"

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

app = modal.App(name="flux-downloader")
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)


@app.function(
    image=image,
    volumes={VOLUME_MOUNT: volume},
    timeout=3600
)
def download_flux_klein(hf_token: str):
    """Download FLUX.2-klein-9B safetensors with aria2 parallel downloads"""
    import subprocess
    
    repo_id = "black-forest-labs/FLUX.2-klein-9B"
    filename = "flux-2-klein-9b.safetensors"
    local_dir = f"{VOLUME_MOUNT}/diffusion_models"
    output_path = f"{local_dir}/{filename}"
    
    # HuggingFace direct download URL
    url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
    
    print("=" * 60)
    print("🚀 FAST PARALLEL DOWNLOAD WITH ARIA2")
    print("=" * 60)
    print(f"📥 File: {filename}")
    print(f"📍 Destination: {output_path}")
    print(f"💾 Volume: {VOLUME_NAME}")
    print("⚡ Using 16 parallel connections")
    print("=" * 60)
    
    os.makedirs(local_dir, exist_ok=True)
    
    # aria2c with 16 parallel connections
    cmd = [
        "aria2c",
        "-x", "16",
        "-s", "16",
        "-k", "1M",
        "-c",
        "--file-allocation=none",
        f"--header=Authorization: Bearer {hf_token}",
        "-d", local_dir,
        "-o", filename,
        url
    ]
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        volume.commit()
        print("=" * 60)
        print("✅ SUCCESS! Download complete!")
        print(f"📂 {output_path}")
        print("=" * 60)
    else:
        print("❌ Download failed!")
        print("💡 Make sure you accepted the license:")
        print("   https://huggingface.co/black-forest-labs/FLUX.2-klein-9B")
        raise Exception("aria2c download failed")


@app.local_entrypoint()
def main():
    print("\n🚀 Starting FAST cloud download...")
    
    hf_token = get_hf_token()
    if not hf_token:
        print("❌ HF_TOKEN not found!")
        print("   Add it to your .env file: HF_TOKEN=hf_xxx...")
        return
    
    print(f"✅ HF Token found")
    print("📦 Building image with aria2...")
    download_flux_klein.remote(hf_token)
    print("\n✨ Done! Model saved to Modal volume.")
