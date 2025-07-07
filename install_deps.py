#!/usr/bin/env python3

import subprocess
import sys
import os

def install_with_uv():
    """Try installing packages directly with UV"""
    packages = ["pyrogram==1.4.16", "tgcrypto==1.2.5", "motor==3.3.2", "apscheduler==3.10.4"]
    
    for package in packages:
        try:
            result = subprocess.run([
                "uv", "add", package, "--no-sync"
            ], capture_output=True, text=True, cwd="/home/runner/workspace")
            
            if result.returncode == 0:
                print(f"✓ Successfully installed {package}")
            else:
                print(f"✗ Failed to install {package}: {result.stderr}")
        except Exception as e:
            print(f"✗ Error installing {package}: {e}")

def check_imports():
    """Check if packages can be imported"""
    packages = ["pyrogram", "tgcrypto", "motor", "apscheduler"]
    
    for package in packages:
        try:
            __import__(package)
            print(f"✓ {package} is available")
        except ImportError:
            print(f"✗ {package} is not available")

if __name__ == "__main__":
    print("Attempting to install packages...")
    install_with_uv()
    print("\nChecking imports...")
    check_imports()