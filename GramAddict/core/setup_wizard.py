"""
GramAddict Setup Wizard - Plug and Play Configuration
Makes GramAddict easy to use with minimal configuration.
"""

import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

import yaml
from colorama import Fore, Style, init

init(autoreset=True)


class SetupWizard:
    """Interactive setup wizard for GramAddict plug-and-play experience."""

    def __init__(self):
        self.system = platform.system()
        self.adb_path = None
        self.username = None
        self.preset = "balanced"
        self.accounts_dir = Path("accounts")

    def print_header(self, text: str):
        """Print a formatted header."""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'=' * 60}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{text.center(60)}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 60}\n")

    def print_success(self, text: str):
        """Print a success message."""
        print(f"{Fore.GREEN}✓ {text}")

    def print_error(self, text: str):
        """Print an error message."""
        print(f"{Fore.RED}✗ {text}")

    def print_info(self, text: str):
        """Print an info message."""
        print(f"{Fore.YELLOW}ℹ {text}")

    def run(self):
        """Run the complete setup wizard."""
        self.print_header("GramAddict Plug & Play Setup")
        print(f"{Fore.WHITE}Welcome! This wizard will configure GramAddict in minutes.")
        print(f"{Fore.WHITE}Let's get started!\n")

        # Step 1: Check Python version
        if not self.check_python_version():
            return False

        # Step 2: Check/Install ADB
        if not self.setup_adb():
            return False

        # Step 3: Check device connection
        if not self.check_device():
            return False

        # Step 4: Setup UIAutomator2
        if not self.setup_uiautomator2():
            return False

        # Step 5: Get account name
        self.username = self.get_username()

        # Step 6: Choose preset
        self.preset = self.choose_preset()

        # Step 7: Generate config
        if not self.generate_config():
            return False

        # Step 8: Success!
        self.print_success_message()
        return True

    def check_python_version(self) -> bool:
        """Check if Python version is compatible."""
        self.print_header("Step 1: Checking Python Version")
        version = sys.version_info
        if version.major == 3 and version.minor >= 6:
            self.print_success(
                f"Python {version.major}.{version.minor}.{version.micro} detected"
            )
            return True
        else:
            self.print_error(
                f"Python 3.6+ required, but {version.major}.{version.minor} found"
            )
            return False

    def find_adb(self) -> Optional[str]:
        """Try to find ADB in system PATH."""
        adb_executable = "adb.exe" if self.system == "Windows" else "adb"
        adb_path = shutil.which(adb_executable)
        return adb_path

    def download_adb(self) -> bool:
        """Download and setup ADB platform tools."""
        self.print_info("Downloading Android Platform Tools...")

        # Determine download URL based on OS
        urls = {
            "Windows": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
            "Darwin": "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip",
            "Linux": "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
        }

        url = urls.get(self.system)
        if not url:
            self.print_error(f"Unsupported operating system: {self.system}")
            return False

        try:
            # Download to temporary location
            tools_dir = Path.home() / ".gramaddict" / "platform-tools"
            tools_dir.mkdir(parents=True, exist_ok=True)
            zip_path = tools_dir / "platform-tools.zip"

            self.print_info(f"Downloading to {tools_dir}...")
            urllib.request.urlretrieve(url, zip_path)

            # Extract
            self.print_info("Extracting...")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tools_dir)

            # Clean up zip
            zip_path.unlink()

            # Set ADB path
            adb_dir = tools_dir / "platform-tools"
            self.adb_path = str(
                adb_dir / ("adb.exe" if self.system == "Windows" else "adb")
            )

            # Make executable on Unix systems
            if self.system != "Windows":
                os.chmod(self.adb_path, 0o755)

            self.print_success(f"ADB installed to {self.adb_path}")

            # Add to PATH for current session
            os.environ["PATH"] = f"{adb_dir}{os.pathsep}{os.environ['PATH']}"

            return True

        except Exception as e:
            self.print_error(f"Failed to download ADB: {e}")
            return False

    def setup_adb(self) -> bool:
        """Check for ADB and install if needed."""
        self.print_header("Step 2: Setting up ADB")

        # Try to find ADB
        self.adb_path = self.find_adb()

        if self.adb_path:
            self.print_success(f"ADB found: {self.adb_path}")
            return True
        else:
            self.print_info("ADB not found in system PATH")
            response = (
                input(
                    f"{Fore.YELLOW}Would you like to download ADB automatically? (y/n): "
                )
                .strip()
                .lower()
            )

            if response == "y":
                return self.download_adb()
            else:
                self.print_error(
                    "ADB is required. Please install it manually and try again."
                )
                return False

    def check_device(self) -> bool:
        """Check if Android device is connected."""
        self.print_header("Step 3: Checking Device Connection")

        try:
            result = subprocess.run(
                [self.adb_path or "adb", "devices"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Parse output
            lines = result.stdout.strip().split("\n")[1:]  # Skip header
            devices = [line.split()[0] for line in lines if line.strip()]

            if not devices:
                self.print_error("No devices connected")
                self.print_info("Please connect your Android device with USB debugging enabled")
                self.print_info("Then press Enter to retry...")
                input()
                return self.check_device()

            self.print_success(f"Device connected: {devices[0]}")
            return True

        except subprocess.TimeoutExpired:
            self.print_error("ADB command timed out")
            return False
        except FileNotFoundError:
            self.print_error("ADB not found")
            return False
        except Exception as e:
            self.print_error(f"Error checking device: {e}")
            return False

    def setup_uiautomator2(self) -> bool:
        """Setup UIAutomator2 on the device."""
        self.print_header("Step 4: Setting up UIAutomator2")

        try:
            self.print_info("Installing UIAutomator2 on device (this may take a minute)...")
            result = subprocess.run(
                [sys.executable, "-m", "uiautomator2", "init"],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                self.print_success("UIAutomator2 installed successfully")
                return True
            else:
                self.print_error(f"Failed to install UIAutomator2: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.print_error("UIAutomator2 installation timed out")
            return False
        except Exception as e:
            self.print_error(f"Error installing UIAutomator2: {e}")
            return False

    def get_username(self) -> str:
        """Get Instagram username from user."""
        self.print_header("Step 5: Account Configuration")
        while True:
            username = input(f"{Fore.YELLOW}Enter your Instagram username: ").strip()
            if username:
                return username
            self.print_error("Username cannot be empty")

    def choose_preset(self) -> str:
        """Let user choose a configuration preset."""
        self.print_header("Step 6: Choose Bot Behavior")

        print(f"{Fore.WHITE}Choose how aggressive the bot should be:\n")
        print(f"{Fore.GREEN}1. Conservative (Safest, slower growth)")
        print(f"   • 10-20 interactions per hour")
        print(f"   • Long delays between actions")
        print(f"   • Best for new accounts or avoiding detection\n")

        print(f"{Fore.CYAN}2. Balanced (Recommended)")
        print(f"   • 30-40 interactions per hour")
        print(f"   • Natural delays")
        print(f"   • Good balance of growth and safety\n")

        print(f"{Fore.RED}3. Aggressive (Faster growth, higher risk)")
        print(f"   • 50-70 interactions per hour")
        print(f"   • Shorter delays")
        print(f"   • Not recommended for new accounts\n")

        while True:
            choice = input(f"{Fore.YELLOW}Select option (1-3) [2]: ").strip() or "2"
            if choice in ["1", "2", "3"]:
                presets = {"1": "conservative", "2": "balanced", "3": "aggressive"}
                selected = presets[choice]
                self.print_success(f"Selected: {selected.capitalize()} preset")
                return selected
            self.print_error("Please enter 1, 2, or 3")

    def get_preset_config(self) -> dict:
        """Get configuration based on preset."""
        presets = {
            "conservative": {
                "speed": 1,
                "total_likes_limit": 50,
                "total_follows_limit": 30,
                "total_unfollows_limit": 30,
                "total_comments_limit": 15,
                "total_pm_limit": 10,
                "interaction_likers_min": 1,
                "interaction_likers_max": 3,
                "interaction_followers_min": 1,
                "interaction_followers_max": 3,
                "interaction_posts_min": 1,
                "interaction_posts_max": 2,
                "like_percentage": 50,
                "follow_percentage": 40,
                "comment_percentage": 20,
            },
            "balanced": {
                "speed": 2,
                "total_likes_limit": 150,
                "total_follows_limit": 100,
                "total_unfollows_limit": 100,
                "total_comments_limit": 30,
                "total_pm_limit": 20,
                "interaction_likers_min": 2,
                "interaction_likers_max": 4,
                "interaction_followers_min": 2,
                "interaction_followers_max": 4,
                "interaction_posts_min": 2,
                "interaction_posts_max": 4,
                "like_percentage": 70,
                "follow_percentage": 50,
                "comment_percentage": 30,
            },
            "aggressive": {
                "speed": 3,
                "total_likes_limit": 300,
                "total_follows_limit": 200,
                "total_unfollows_limit": 200,
                "total_comments_limit": 50,
                "total_pm_limit": 30,
                "interaction_likers_min": 3,
                "interaction_likers_max": 6,
                "interaction_followers_min": 3,
                "interaction_followers_max": 6,
                "interaction_posts_min": 3,
                "interaction_posts_max": 5,
                "like_percentage": 80,
                "follow_percentage": 60,
                "comment_percentage": 40,
            },
        }
        return presets.get(self.preset, presets["balanced"])

    def generate_config(self) -> bool:
        """Generate configuration files."""
        self.print_header("Step 7: Generating Configuration")

        try:
            # Create accounts directory
            account_dir = self.accounts_dir / self.username
            account_dir.mkdir(parents=True, exist_ok=True)

            # Get preset config
            preset_cfg = self.get_preset_config()

            # Generate minimal config.yml
            config = {
                "username": self.username,
                "app_id": "com.instagram.android",
                "speed": preset_cfg["speed"],
                "debug": False,
                "close_apps": True,
                "screen_sleep": False,
                "disable_block_detection": False,
                # Session limits
                "total_likes_limit": preset_cfg["total_likes_limit"],
                "total_follows_limit": preset_cfg["total_follows_limit"],
                "total_unfollows_limit": preset_cfg["total_unfollows_limit"],
                "total_comments_limit": preset_cfg["total_comments_limit"],
                "total_pm_limit": preset_cfg["total_pm_limit"],
                # Interaction settings
                "like_percentage": preset_cfg["like_percentage"],
                "follow_percentage": preset_cfg["follow_percentage"],
                "comment_percentage": preset_cfg["comment_percentage"],
                # Default interaction
                "interact_from_profile_percentage": 100,
            }

            config_path = account_dir / "config.yml"
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(f"# GramAddict Config - {self.preset.capitalize()} Preset\n")
                f.write(f"# Auto-generated by Setup Wizard\n\n")
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            self.print_success(f"Config saved: {config_path}")

            # Generate minimal filters.yml
            filters = {
                "skip_business": False,
                "skip_non_business": False,
                "skip_following": True,
                "skip_follower": False,
                "min_followers": 50,
                "max_followers": 10000,
                "min_followings": 50,
                "max_followings": 5000,
                "min_potency_ratio": 0.5,
                "follow_private_or_empty": False,
            }

            filters_path = account_dir / "filters.yml"
            with open(filters_path, "w", encoding="utf-8") as f:
                f.write("# GramAddict Filters\n")
                f.write("# Auto-generated by Setup Wizard\n\n")
                yaml.dump(filters, f, default_flow_style=False, sort_keys=False)

            self.print_success(f"Filters saved: {filters_path}")

            # Create empty list files
            for filename in ["whitelist.txt", "blacklist.txt", "comments_list.txt"]:
                filepath = account_dir / filename
                filepath.touch()

            self.print_success("Created list files (whitelist, blacklist, comments)")

            return True

        except Exception as e:
            self.print_error(f"Failed to generate config: {e}")
            return False

    def print_success_message(self):
        """Print final success message with next steps."""
        self.print_header("Setup Complete!")

        print(f"{Fore.GREEN}{Style.BRIGHT}✓ GramAddict is ready to use!\n")

        print(f"{Fore.CYAN}Next Steps:")
        print(f"{Fore.WHITE}1. Start the bot:")
        print(
            f"   {Fore.YELLOW}gramaddict run --config accounts/{self.username}/config.yml\n"
        )

        print(f"{Fore.WHITE}2. Optional: Customize your configuration:")
        print(f"   {Fore.YELLOW}accounts/{self.username}/config.yml")
        print(f"   {Fore.YELLOW}accounts/{self.username}/filters.yml\n")

        print(f"{Fore.WHITE}3. Add interactions (example):")
        print(
            f"   {Fore.YELLOW}gramaddict run --config accounts/{self.username}/config.yml --interact @instagram\n"
        )

        print(f"{Fore.CYAN}Tip: Run 'gramaddict health-check' to verify everything is working!\n")


def run_setup_wizard():
    """Entry point for setup wizard."""
    wizard = SetupWizard()
    success = wizard.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(run_setup_wizard())
