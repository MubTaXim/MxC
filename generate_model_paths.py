#!/usr/bin/env python3
"""
Generate extra_model_paths.yaml from config.ini

This script reads configuration from config.ini and generates the YAML file
that ComfyUI uses to locate models, custom nodes, and other resources.
"""

import configparser
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys


class ModelPathsGenerator:
    """Generate extra_model_paths.yaml from config.ini"""

    def __init__(self, config_file: str = "config.ini", output_file: str = "extra_model_paths.yaml"):
        """
        Initialize the generator.

        Args:
            config_file: Path to config.ini
            output_file: Path to output YAML file
        """
        self.config_file = Path(config_file)
        self.output_file = Path(output_file)
        self.config = configparser.ConfigParser()

    def load_config(self) -> bool:
        """
        Load configuration from config.ini.

        Returns:
            True if successful, False otherwise
        """
        if not self.config_file.exists():
            print(f"✗ Error: {self.config_file} not found!")
            return False

        try:
            self.config.read(self.config_file)
            print(f"✓ Configuration loaded from {self.config_file}")
            return True
        except configparser.Error as e:
            print(f"✗ Error reading config file: {e}")
            return False

    @staticmethod
    def parse_multiline_config(value: str) -> List[str]:
        """
        Parse multiline config values and return a list of paths.

        Removes empty lines and strips whitespace.

        Args:
            value: Multiline string from config file

        Returns:
            List of paths
        """
        paths = [line.strip() for line in value.split('\n') if line.strip()]
        return paths

    def get_filesystem_config(self) -> Optional[Dict[str, str]]:
        """
        Extract filesystem configuration from config.ini.

        Returns:
            Dictionary with filesystem settings or None if error
        """
        try:
            config = {
                "comfyui_dir": self.config.get("FILESYSTEM", "comfyui_dir", fallback="/root/comfy/ComfyUI"),
                "volume_mount_location": self.config.get("FILESYSTEM", "volume_mount_location", fallback="/root/per_comfy-storage"),
                "custom_nodes_dir_name": self.config.get("FILESYSTEM", "custom_nodes_dir_name", fallback="custom_nodes"),
                "custom_output_dir_name": self.config.get("FILESYSTEM", "custom_output_dir_name", fallback="output"),
            }
            return config
        except configparser.NoSectionError as e:
            print(f"✗ Error: Missing [FILESYSTEM] section in config.ini - {e}")
            return None
        except configparser.NoOptionError as e:
            print(f"✗ Error: Missing option in [FILESYSTEM] section - {e}")
            return None

    def get_model_paths(self) -> Dict[str, str]:
        """
        Extract model paths from [MODEL_PATHS] section.

        Returns:
            Dictionary with model paths
        """
        model_paths_dict: Dict[str, str] = {}

        if not self.config.has_section("MODEL_PATHS"):
            print("⚠ Warning: [MODEL_PATHS] section not found in config.ini")
            print("  Using default model paths...")
            return self._get_default_model_paths()

        try:
            for key in self.config.options("MODEL_PATHS"):
                value = self.config.get("MODEL_PATHS", key)
                paths = self.parse_multiline_config(value)
                # Join paths with newline for YAML literal block style
                model_paths_dict[key] = "\n".join(paths)

            print(f"✓ Loaded {len(model_paths_dict)} model path configurations")
            return model_paths_dict
        except Exception as e:
            print(f"✗ Error reading model paths: {e}")
            return self._get_default_model_paths()

    def _get_default_model_paths(self) -> Dict[str, str]:
        """
        Get default model paths if [MODEL_PATHS] section is missing.

        Returns:
            Dictionary with default model paths
        """
        fs_config = self.get_filesystem_config()
        if not fs_config:
            return {}

        comfyui = fs_config["comfyui_dir"]
        volume = fs_config["volume_mount_location"]

        return {
            "checkpoints": f"{comfyui}/models/checkpoints\n{volume}/checkpoints",
            "clip": f"{comfyui}/models/clip\n{volume}/text_encoders",
            "clip_vision": f"{comfyui}/models/clip_vision",
            "configs": f"{comfyui}/models/configs",
            "controlnet": f"{comfyui}/models/controlnet",
            "diffusion_models": f"{comfyui}/models/diffusion_models\n{volume}/diffusion_models",
            "embeddings": f"{comfyui}/models/embeddings",
            "gligen": f"{comfyui}/models/gligen",
            "hypernetworks": f"{comfyui}/models/hypernetworks",
            "inpaint": f"{comfyui}/models/inpaint",
            "loras": f"{comfyui}/models/loras\n{volume}/loras",
            "sampling": f"{comfyui}/models/sampling",
            "upscale_models": f"{comfyui}/models/upscale_models",
            "vae": f"{comfyui}/models/vae\n{volume}/vae",
            "vae_approx": f"{comfyui}/models/vae_approx",
        }

    def generate(self) -> bool:
        """
        Generate the extra_model_paths.yaml file.

        Returns:
            True if successful, False otherwise
        """
        # Load configuration
        if not self.load_config():
            return False

        # Get filesystem config
        fs_config = self.get_filesystem_config()
        if not fs_config:
            return False

        # Get model paths
        model_paths = self.get_model_paths()

        try:
            # Build the extra_model_paths structure
            extra_model_paths: Dict[str, Any] = {
                "comfyui": {
                    "base_path": fs_config["comfyui_dir"],
                }
            }

            # Add model paths to comfyui section
            extra_model_paths["comfyui"].update(model_paths)

            # Add custom nodes path
            custom_nodes_path = f"{fs_config['volume_mount_location']}/{fs_config['custom_nodes_dir_name']}"
            extra_model_paths["comfyui"]["custom_nodes"] = custom_nodes_path

            # Write to YAML file
            with open(self.output_file, 'w') as yaml_file:
                yaml.dump(
                    extra_model_paths,
                    yaml_file,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                    width=1000  # Prevent line wrapping
                )

            print(f"✓ Generated {self.output_file} successfully!")
            self._print_summary(fs_config, model_paths)
            return True

        except Exception as e:
            print(f"✗ Error generating YAML file: {e}")
            return False

    def _print_summary(self, fs_config: Dict[str, str], model_paths: Dict[str, str]):
        """
        Print a summary of the generated configuration.

        Args:
            fs_config: Filesystem configuration
            model_paths: Model paths configuration
        """
        print("\n" + "=" * 60)
        print("📊 CONFIGURATION SUMMARY")
        print("=" * 60)

        print("\n📂 Filesystem Configuration:")
        print(f"  Base Path (ComfyUI): {fs_config['comfyui_dir']}")
        print(f"  Volume Mount: {fs_config['volume_mount_location']}")
        print(f"  Custom Nodes Directory: {fs_config['custom_nodes_dir_name']}")
        print(f"  Output Directory: {fs_config['custom_output_dir_name']}")

        print(f"\n🤖 Model Paths Configured: {len(model_paths)}")
        for key in sorted(model_paths.keys()):
            path_count = len(model_paths[key].split('\n'))
            print(f"  ✓ {key}: {path_count} path(s)")

        print(f"\n📝 Output File: {self.output_file.resolve()}")

    def validate(self) -> bool:
        """
        Validate the generated YAML file.

        Returns:
            True if valid, False otherwise
        """
        if not self.output_file.exists():
            print(f"✗ Output file {self.output_file} does not exist!")
            return False

        try:
            with open(self.output_file, 'r') as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                print("✗ Invalid YAML structure!")
                return False

            if "comfyui" not in data:
                print("✗ Missing 'comfyui' section in generated YAML!")
                return False

            if "base_path" not in data["comfyui"]:
                print("✗ Missing 'base_path' in comfyui section!")
                return False

            print("✓ YAML file validation successful!")
            return True

        except yaml.YAMLError as e:
            print(f"✗ Invalid YAML syntax: {e}")
            return False
        except Exception as e:
            print(f"✗ Validation error: {e}")
            return False


def generate_extra_model_paths(config_file: str = "config.ini", output_file: str = "extra_model_paths.yaml"):
    """Main entry point."""
    print("\n" + "=" * 60)
    print("🔧 ComfyUI Model Paths Generator")
    print("=" * 60 + "\n")

    generator = ModelPathsGenerator(config_file=config_file, output_file=output_file)

    # Generate the file
    if not generator.generate():
        sys.exit(1)

    # Validate the generated file
    print()
    if not generator.validate():
        print("\n⚠️ Generated file may have issues. Please review manually.")
        sys.exit(1)

    print("\n✅ Setup complete! You can now use extra_model_paths.yaml with ComfyUI")


if __name__ == "__main__":
    generate_extra_model_paths()