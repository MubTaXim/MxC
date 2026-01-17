import os
import configparser
from pathlib import Path
from dotenv import load_dotenv


class ConfigLoader:
    """
    Handles loading configuration from config.ini with support for 
    secret redirection via .env files for sensitive data.
    """

    def __init__(self, config_path: str = "config.ini", env_path: str = ".env"):
        # Use absolute path relative to the script location
        base_dir = Path(__file__).parent.resolve()
        self.config_path = base_dir / config_path
        self.env_path = base_dir / env_path

        # Initialize parser
        self.config = configparser.ConfigParser()

        # CRITICAL: Prevent configparser from converting keys to lowercase
        self.config.optionxform = str

        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}")
        if not self.env_path.exists():
            raise FileNotFoundError(f".env file not found: {self.env_path}")

        self.config.read(self.config_path)

        # Load .env file if it exists to resolve secret keys
        if self.env_path.exists():
            load_dotenv(self.env_path)

    def _get_secret_or_value(self, section: str, key: str) -> str:
        """
        Retrieves value. If value is '.env', searches env vars in this order:
        1. Exact key (e.g., HF_TOKEN)
        2. Uppercase key
        3. Lowercase key
        4. Returns None
        """
        try:
            val = self.config.get(section, key).strip()

            if val.lower() == ".env":
                # Priority 1: Exact match as written in .ini
                secret = os.getenv(key)

                # Priority 2: Uppercase fallback
                if secret is None:
                    secret = os.getenv(key.upper())

                # Priority 3: Lowercase fallback
                if secret is None:
                    secret = os.getenv(key.lower())

                # Return None if nothing found in .env
                return secret

            return val
        except (configparser.NoSectionError, configparser.NoOptionError):
            return None

    def load_configs(self):
        """Processes the ini file into a structured dictionary."""

        # 1. Load Tokens (Sensitive Data Redirection)
        tokens = {
            key.lower(): self._get_secret_or_value("TOKENS", key)
            for key in self.config.options("TOKENS")
        }

        # 2. Web Settings (Type-casted)
        # # Extract the raw host value first
        raw_host = self.config.get("WEB", "host", fallback="0.0.0.0").strip().lower()
        web = {
            "port": self.config.getint("WEB", "port", fallback=8000),
            # If host is 'localhost', override to '0.0.0.0' for external accessibility
            "host": "0.0.0.0" if raw_host == "localhost" else raw_host,
            "host": self.config.get("WEB", "host"),
            "remote": self.config.getboolean("WEB", "remote", fallback=True)
        }

        # 3. Filesystem Settings
        fs = {
            "volume_name": self.config.get("FILESYSTEM", "volume_name"),
            "volume_mount_location": self.config.get("FILESYSTEM", "volume_mount_location"),
            "comfyui_dir": self.config.get("FILESYSTEM", "comfyui_dir"),
            "custom_nodes_dir_name": self.config.get("FILESYSTEM", "custom_nodes_dir_name", fallback="custom_nodes"),
            "custom_output_dir_name": self.config.get("FILESYSTEM", "custom_output_dir_name", fallback="output")
        }
        # Dynamic path generation based on mount location
        fs["custom_nodes_dir"] = f"{fs['volume_mount_location']}/{fs['custom_nodes_dir_name']}"
        fs["custom_output_dir"] = f"{fs['volume_mount_location']}/{fs['custom_output_dir_name']}"

        # 4. Resources
        resources = {
            "gpu_type": self.config.get("RESOURCES", "gpu_type", fallback="t4"),
            "cpu": self.config.get("RESOURCES", "cpu", fallback=None),
            "memory": self.config.get("RESOURCES", "memory", fallback=None),
            "max_containers": self.config.getint("RESOURCES", "max_containers", fallback=1),
            "scaledown_window": self.config.getint("RESOURCES", "scaledown_window", fallback=30),
            "timeout": self.config.getint("RESOURCES", "timeout", fallback=3200),
            "max_inputs": self.config.getint("RESOURCES", "max_inputs", fallback=10)
            # Additional resource settings can be added here
        }

        return {
            "tokens": tokens,
            "web": web,
            "filesystem": fs,
            "resources": resources
        }


# --- Usage Example ---
if __name__ == "__main__":
    try:
        loader = ConfigLoader()
        data = loader.load_configs()

        # Debugging Output
        print("--- Loaded Configs ---")
        for section, values in data.items():
            print(f"[{section.upper()}]")
            for k, v in values.items():
                # Mask tokens for security in logs
                display_val = "*******" if section == "tokens" and v else v
                print(f"  {k}: {display_val}")

    except Exception as e:
        print(f"Failed to load configuration: {e}")
