import subprocess
from pathlib import Path
import modal
from loaders import ConfigLoader

# ===========================
# Global Configuration
# ===========================

# Modal app name
APP_NAME = "comfyui-app"

# Absolute path of current working directory
CURRENT_DIR = Path(__file__).parent.resolve()

# Load configurations from config.ini
cfg = ConfigLoader(config_path="config.ini", env_path=".env").load_configs()
HF_TOKEN = str(cfg["tokens"]["hf_token"])
CIVITAI_API_TOKEN = str(cfg["tokens"]["civitai_api_token"])
WEB_SERVER_HOST = str(cfg["web"]["host"])
WEB_SERVER_PORT = cfg["web"]["port"]
VOLUME_NAME = str(cfg["filesystem"]["volume_name"])
VOLUME_MOUNT_LOCATION = str(cfg["filesystem"]["volume_mount_location"])
COMFYUI_DIR = str(cfg["filesystem"]["comfyui_dir"])
CUSTOM_NODES_DIR = str(cfg["filesystem"]["custom_nodes_dir"])
CUSTOM_OUTPUT_DIR = str(cfg["filesystem"]["custom_output_dir"]) # "/root/per_comfy-storage/output"
GPU_TYPE = str(cfg["resources"]["gpu_type"]) or None
CPU = cfg["resources"]["cpu"]
MEMORY = cfg["resources"]["memory"]
MAX_CONTAINERS = cfg["resources"]["max_containers"]
SCALEDOWN_WINDOW = cfg["resources"]["scaledown_window"]
TIMEOUT = cfg["resources"]["timeout"]
MAX_INPUTS = cfg["resources"]["max_inputs"]

def debug_print_config_and_exit():
    """Utility function to print configuration and exit."""
    # Debug prints
    # Print all of the above variables and exit
    print("Configuration Loaded:")
    print(f"APP_NAME: {APP_NAME}")
    print(f"CURRENT_DIR: {CURRENT_DIR}")
    print(f"HF_TOKEN: {HF_TOKEN}")
    print(f"CIVITAI_API_TOKEN: {CIVITAI_API_TOKEN}")
    print(f"WEB_SERVER_HOST: {WEB_SERVER_HOST}")
    print(f"WEB_SERVER_PORT: {WEB_SERVER_PORT}")
    print(f"VOLUME_NAME: {VOLUME_NAME}")
    print(f"VOLUME_MOUNT_LOCATION: {VOLUME_MOUNT_LOCATION}")
    print(f"COMFYUI_DIR: {COMFYUI_DIR}")
    print(f"CUSTOM_NODES_DIR: {CUSTOM_NODES_DIR}")
    print(f"GPU_TYPE: {GPU_TYPE}")
    print(f"CPU: {CPU}")
    print(f"MEMORY: {MEMORY}")
    print(f"MAX_CONTAINERS: {MAX_CONTAINERS}")
    print(f"SCALEDOWN_WINDOW: {SCALEDOWN_WINDOW}")
    print(f"TIMEOUT: {TIMEOUT}")
    print(f"MAX_INPUTS: {MAX_INPUTS}")
    exit(1)

# debug_print_config_and_exit()

# ===========================
# Modal Image Configuration
# ===========================

# Define the Modal image
comfy_image = (
    modal.Image.debian_slim(python_version="3.11")
    .env({"HF_TOKEN": HF_TOKEN, "CIVITAI_API_TOKEN": CIVITAI_API_TOKEN})
    .apt_install(
        "git", "nano",
        "libgl1", "libglib2.0-0", "libsm6", "libxext6", "libxrender1"  # OpenCV dependencies
    )
    .pip_install(
        "comfy-cli", "gguf", "sentencepiece", "opencv-python-headless",
        "transformers", "accelerate", "safetensors",  # For FLUX models
        "timm", "einops",  # For SAM2/Florence2
        "huggingface-hub",  # For model downloads
    )
    .run_commands("comfy --skip-prompt install --nvidia")
    .run_commands(
        # Core Custom Nodes
        "comfy node install ComfyUI-Crystools",  # Resource monitor
        "comfy node install comfyui-easy-use",
        "comfy node install comfyui-kjnodes",
        "comfy node install comfyui_ultimatesdupscale",
        "comfy node install comfyui_essentials",
        "comfy node install comfyui-detail-daemon",
        "comfy node install seedvarianceenhancer",
        "comfy node install comfyui_controlnet_aux",
    )
    .run_commands(
        # FLUX.2 Klein + LanPaint Inpainting Stack
        "comfy node install ComfyUI-GGUF",              # GGUF model support for Klein
        "comfy node install ComfyUI-LanPaint",          # LanPaint inpainting (TMLR peer-reviewed)
        "comfy node install ComfyUI-BRIA_AI-RMBG",      # RMBG 2.0 background removal
        "comfy node install ComfyUI-segment-anything-2", # SAM2 segmentation
        "comfy node install ComfyUI-Florence2",         # Florence2 for auto-captioning
        "comfy node install ComfyUI-KJNodes",           # Additional utilities
        "comfy node install rgthree-comfy",             # UI nodes (Image Comparer, Labels, etc.)
        "comfy node install comfyui-image-compare",     # ImageCompareNode for inpainting workflow
    )
    # Add loaders.py file for configuration loading inside the container
    .add_local_python_source("loaders", copy=False)
    .add_local_file(str(CURRENT_DIR / "config.ini"), remote_path="/root/config.ini")
    .add_local_file(str(CURRENT_DIR / ".env"), remote_path="/root/.env")
    # Persistent comfyui settings and workflows
    # v0.3.76+ (with System User API) # https://github.com/Comfy-Org/ComfyUI-Manager#paths
    .add_local_file(str(CURRENT_DIR / "extra_model_paths.yaml"), remote_path=str(COMFYUI_DIR + "/extra_model_paths.yaml"))
    .add_local_file(str(CURRENT_DIR / "config_comfyui.ini"), remote_path=str(COMFYUI_DIR + "/user/__manager/config.ini"))
    .add_local_file(str(CURRENT_DIR / "comfy.settings.json"), remote_path=str(COMFYUI_DIR + "/user/default/comfy.settings.json"))
    # Copy local workflows to a temp location in image (will be moved to volume at startup)
    .add_local_dir(str(CURRENT_DIR / "workflows/"), remote_path="/tmp/workflows_template/")
)

# ===========================
# Modal App Configuration
# ===========================

app = modal.App(name=APP_NAME, image=comfy_image)

# Create a persistent volume
model_volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

# Prepare the container arguments dynamically
container_kwargs = {
    "max_containers": MAX_CONTAINERS,
    "scaledown_window": SCALEDOWN_WINDOW,
    "timeout": TIMEOUT,
    "gpu": GPU_TYPE,
    "volumes": {VOLUME_MOUNT_LOCATION: model_volume},
}

# Only add CPU and Memory if they actually have values
if CPU is not None:
    container_kwargs["cpu"] = CPU

if MEMORY is not None:
    container_kwargs["memory"] = MEMORY

# Use dictionary unpacking (**) to pass the arguments
@app.cls(**container_kwargs)
@modal.concurrent(max_inputs=MAX_INPUTS)

class ComfyUIContainer:
    @modal.enter()
    def setup_dependencies(self):
        """
        Sets up writable user data directory on volume and installs custom node dependencies.
        """
        import shutil
        
        # === Setup writable user/default directory on volume ===
        # ComfyUI stores workflows, settings, and cache in user/default
        # Modal's filesystem is read-only, so we symlink the entire directory to the volume
        
        user_data_volume = Path(VOLUME_MOUNT_LOCATION) / "user_data"
        workflows_volume = user_data_volume / "workflows"
        comfy_user_default = Path(COMFYUI_DIR) / "user/default"
        workflows_template = Path("/tmp/workflows_template")
        
        # Create user_data directory structure on volume
        user_data_volume.mkdir(parents=True, exist_ok=True)
        workflows_volume.mkdir(parents=True, exist_ok=True)
        
        # Copy template workflows to volume (only if they don't already exist)
        if workflows_template.exists():
            print(f"--- Syncing template workflows to volume ---")
            for workflow_file in workflows_template.glob("*.json"):
                dest_file = workflows_volume / workflow_file.name
                if not dest_file.exists():
                    shutil.copy2(workflow_file, dest_file)
                    print(f"  Copied: {workflow_file.name}")
        
        # Copy template comfy.settings.json if it doesn't exist on volume
        settings_template = Path("/root/comfy/ComfyUI/user/default/comfy.settings.json")
        settings_dest = user_data_volume / "comfy.settings.json"
        if settings_template.exists() and not settings_dest.exists():
            shutil.copy2(settings_template, settings_dest)
            print(f"  Copied: comfy.settings.json")
        
        # Symlink ComfyUI's user/default to the writable volume location
        comfy_user_default.parent.mkdir(parents=True, exist_ok=True)
        if comfy_user_default.exists() and comfy_user_default.is_symlink():
            comfy_user_default.unlink()
        elif comfy_user_default.exists():
            shutil.rmtree(comfy_user_default)
        comfy_user_default.symlink_to(user_data_volume)
        print(f"✅ User data directory linked: {comfy_user_default} -> {user_data_volume}")
        
        # Install custom node dependencies
        nodes_path = Path(CUSTOM_NODES_DIR)

        if not nodes_path.exists():
            print(f"Creating missing custom_nodes directory: {nodes_path}")
            nodes_path.mkdir(parents=True, exist_ok=True)

        print("--- Checking for custom node requirements ---")
        for node_dir in nodes_path.iterdir():
            if node_dir.is_dir():
                req_file = node_dir / "requirements.txt"
                if req_file.exists():
                    print(f"Installing requirements for: {node_dir.name}")
                    # Install dependencies for each node
                    subprocess.run(
                        ["pip", "install", "-r", str(req_file)], check=False)
        print("--- Dependency check complete ---")

    @modal.method()
    def download_model(self, repo_id: str, local_dir: str, patterns: list = None):
        """
        Download a model from HuggingFace to the persistent volume.
        
        Args:
            repo_id: HuggingFace repo ID (e.g., "black-forest-labs/FLUX.2-klein-9B")
            local_dir: Directory inside volume to save to (e.g., "/root/per_comfy-storage/diffusion_models/FLUX.2-klein-9B")
            patterns: Optional list of file patterns to download (e.g., ["*.safetensors"])
        """
        from huggingface_hub import snapshot_download
        
        print(f"📥 Downloading {repo_id} to {local_dir}...")
        
        download_kwargs = {
            "repo_id": repo_id,
            "local_dir": local_dir,
            "token": HF_TOKEN,
            "resume_download": True,
        }
        
        if patterns:
            download_kwargs["allow_patterns"] = patterns
        
        try:
            snapshot_download(**download_kwargs)
            print(f"✅ Successfully downloaded {repo_id}")
        except Exception as e:
            print(f"❌ Error downloading {repo_id}: {e}")

    @modal.web_server(WEB_SERVER_PORT, startup_timeout=60)
    def ui(self):
        """
        Launches the ComfyUI web server.
        """
        print(f"Starting ComfyUI on  {WEB_SERVER_HOST}:{WEB_SERVER_PORT}...")
        subprocess.Popen(
            f"comfy launch -- --output-directory {CUSTOM_OUTPUT_DIR} --listen {WEB_SERVER_HOST} --port {WEB_SERVER_PORT}",
            shell=True
        )
