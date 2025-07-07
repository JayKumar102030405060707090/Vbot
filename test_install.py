#!/usr/bin/env python3

import sys
import subprocess

def install_package(package):
    """Install a single package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--user"])
        print(f"✓ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install {package}: {e}")
        return False

def main():
    packages = ["pyrogram", "tgcrypto", "motor", "apscheduler"]
    
    print("Attempting to install packages individually...")
    
    for package in packages:
        success = install_package(package)
        if not success:
            print(f"Skipping {package} due to installation failure")
    
    print("Installation attempt complete.")

if __name__ == "__main__":
    main()