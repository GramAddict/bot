"""
GramAddict Health Check - System Verification
Checks all requirements and dependencies for GramAddict.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from colorama import Fore, Style, init

init(autoreset=True)


class HealthCheck:
    """System health checker for GramAddict."""

    def __init__(self):
        self.checks = []
        self.passed = 0
        self.failed = 0

    def check(self, name: str, func):
        """Run a health check."""
        try:
            result, message = func()
            if result:
                print(f"{Fore.GREEN}✓ {name}: {message}")
                self.passed += 1
            else:
                print(f"{Fore.RED}✗ {name}: {message}")
                self.failed += 1
            return result
        except Exception as e:
            print(f"{Fore.RED}✗ {name}: Error - {e}")
            self.failed += 1
            return False

    def check_python_version(self):
        """Check Python version."""
        version = sys.version_info
        if version.major == 3 and version.minor >= 6:
            return True, f"Python {version.major}.{version.minor}.{version.micro}"
        else:
            return (
                False,
                f"Python 3.6+ required (found {version.major}.{version.minor})",
            )

    def check_dependencies(self):
        """Check if required dependencies are installed."""
        required = [
            "colorama",
            "configargparse",
            "yaml",
            "uiautomator2",
            "emoji",
            "requests",
        ]
        missing = []

        for module in required:
            try:
                __import__(module)
            except ImportError:
                missing.append(module)

        if not missing:
            return True, f"All {len(required)} required packages installed"
        else:
            return False, f"Missing packages: {', '.join(missing)}"

    def check_adb(self):
        """Check if ADB is available."""
        adb_path = shutil.which("adb")
        if adb_path:
            try:
                result = subprocess.run(
                    ["adb", "version"], capture_output=True, text=True, timeout=5
                )
                version_line = result.stdout.split("\n")[0]
                return True, f"Found at {adb_path} ({version_line})"
            except Exception:
                return True, f"Found at {adb_path}"
        else:
            # Check in .gramaddict directory
            gramaddict_adb = (
                Path.home() / ".gramaddict" / "platform-tools" / "platform-tools" / "adb"
            )
            if gramaddict_adb.exists():
                return True, f"Found at {gramaddict_adb}"
            return False, "Not found in PATH or ~/.gramaddict"

    def check_device_connection(self):
        """Check if Android device is connected."""
        try:
            result = subprocess.run(
                ["adb", "devices"], capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split("\n")[1:]
            devices = [line.split()[0] for line in lines if line.strip()]

            if devices:
                return True, f"{len(devices)} device(s) connected: {', '.join(devices)}"
            else:
                return False, "No devices connected"
        except FileNotFoundError:
            return False, "Cannot run 'adb devices' (ADB not found)"
        except Exception as e:
            return False, f"Error: {e}"

    def check_uiautomator2(self):
        """Check if UIAutomator2 is installed."""
        try:
            import uiautomator2 as u2

            # Try to connect to device
            try:
                d = u2.connect()
                info = d.info
                return True, f"Installed and working (Device: {info.get('productName', 'Unknown')})"
            except Exception:
                return True, "Installed (device not connected or not initialized)"
        except ImportError:
            return False, "Package not installed"

    def check_config_exists(self):
        """Check if any config files exist."""
        accounts_dir = Path("accounts")
        if not accounts_dir.exists():
            return False, "No accounts directory found"

        configs = list(accounts_dir.glob("*/config.yml"))
        if configs:
            return True, f"Found {len(configs)} account(s) configured"
        else:
            return False, "No config files found in accounts/"

    def check_instagram_app(self):
        """Check if Instagram app is installed on device."""
        try:
            result = subprocess.run(
                ["adb", "shell", "pm", "list", "packages", "instagram"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            packages = [
                line.split(":")[-1]
                for line in result.stdout.split("\n")
                if "instagram" in line.lower()
            ]

            if "com.instagram.android" in packages:
                return True, "Instagram app found on device"
            elif packages:
                return True, f"Instagram-like apps found: {', '.join(packages)}"
            else:
                return False, "Instagram app not found on device"
        except FileNotFoundError:
            return False, "Cannot check (ADB not available)"
        except Exception as e:
            return False, f"Error: {e}"

    def check_write_permissions(self):
        """Check if we have write permissions."""
        test_dir = Path("accounts")
        try:
            test_dir.mkdir(exist_ok=True)
            test_file = test_dir / ".health_check_test"
            test_file.write_text("test")
            test_file.unlink()
            return True, "Can write to accounts directory"
        except Exception as e:
            return False, f"Cannot write to accounts directory: {e}"

    def run(self):
        """Run all health checks."""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'=' * 60}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'GramAddict Health Check'.center(60)}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 60}\n")

        print(f"{Fore.YELLOW}System Requirements:")
        self.check("Python Version", self.check_python_version)
        self.check("Required Packages", self.check_dependencies)
        self.check("Write Permissions", self.check_write_permissions)

        print(f"\n{Fore.YELLOW}Android Setup:")
        self.check("ADB Installed", self.check_adb)
        self.check("Device Connected", self.check_device_connection)
        self.check("UIAutomator2", self.check_uiautomator2)
        self.check("Instagram App", self.check_instagram_app)

        print(f"\n{Fore.YELLOW}Configuration:")
        self.check("Config Files", self.check_config_exists)

        # Summary
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'=' * 60}")
        total = self.passed + self.failed
        if self.failed == 0:
            print(f"{Fore.GREEN}{Style.BRIGHT}All {total} checks passed! ✓")
            print(f"{Fore.GREEN}GramAddict is ready to use!")
            print(
                f"\n{Fore.WHITE}Run: {Fore.YELLOW}gramaddict run --config accounts/<username>/config.yml"
            )
        else:
            print(
                f"{Fore.YELLOW}{Style.BRIGHT}{self.passed}/{total} checks passed, {self.failed} failed"
            )
            if self.failed > 0:
                print(f"\n{Fore.RED}Please fix the failed checks above.")
                print(
                    f"{Fore.WHITE}Tip: Run {Fore.YELLOW}'gramaddict setup'{Fore.WHITE} to configure GramAddict automatically"
                )

        print(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 60}\n")

        return 0 if self.failed == 0 else 1


def run_health_check():
    """Entry point for health check."""
    checker = HealthCheck()
    return checker.run()


if __name__ == "__main__":
    sys.exit(run_health_check())
