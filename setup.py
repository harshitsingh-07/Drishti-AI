"""
AI Eye — one-shot setup script
Run this once after cloning the repo:

    python setup.py

It will:
  1. Install all Python packages from requirements.txt
  2. Install Ollama (runs OllamaSetup.exe if not already installed)
  3. Pull the qwen2.5:0.5b language model
  4. Confirm everything is ready
"""

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def step(msg: str):
    print(f"\n{'─' * 50}")
    print(f"  {msg}")
    print(f"{'─' * 50}")

def ok(msg: str):
    print(f"  ✓  {msg}")

def warn(msg: str):
    print(f"  ⚠  {msg}")

def fail(msg: str):
    print(f"  ✗  {msg}")


# ---------------------------------------------------------------------------
# Step 1 — Python packages
# ---------------------------------------------------------------------------

def install_packages():
    step("Installing Python packages")
    req = Path(__file__).parent / "requirements.txt"
    if not req.exists():
        fail("requirements.txt not found — make sure you're running this from the AI-Eye folder.")
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req)],
        capture_output=False,
    )
    if result.returncode != 0:
        fail("pip install failed. Check the error above.")
        sys.exit(1)
    ok("All Python packages installed.")


# ---------------------------------------------------------------------------
# Step 2 — Ollama application
# ---------------------------------------------------------------------------

def ollama_in_path() -> bool:
    return shutil.which("ollama") is not None


def ollama_api_running() -> bool:
    try:
        import ollama as _ol
        _ol.list()
        return True
    except Exception:
        return False


OLLAMA_DOWNLOAD_URL = "https://ollama.com/download/OllamaSetup.exe"


def install_ollama():
    step("Checking Ollama installation")

    if ollama_in_path():
        ok("Ollama is already installed.")
        return

    # Download the installer from the official site
    import urllib.request

    installer = Path(__file__).parent / "_OllamaSetup_temp.exe"
    print(f"  Downloading Ollama installer from {OLLAMA_DOWNLOAD_URL}")
    print("  This is a ~300 MB download, please wait...")

    try:
        def _progress(count, block_size, total):
            if total > 0:
                pct = min(100, count * block_size * 100 // total)
                bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                print(f"\r  [{bar}] {pct}%", end="", flush=True)

        urllib.request.urlretrieve(OLLAMA_DOWNLOAD_URL, installer, reporthook=_progress)
        print()  # newline after progress bar
        ok("Download complete.")
    except Exception as err:
        print()
        fail(f"Download failed: {err}")
        print()
        print("  Install Ollama manually from:  https://ollama.com/download")
        print("  Then run this script again.")
        sys.exit(1)

    print("  Running installer — follow the on-screen prompts...")
    subprocess.run([str(installer)], check=False)
    installer.unlink(missing_ok=True)   # clean up temp file

    # Wait for ollama to appear on PATH
    print("  Waiting for Ollama to become available", end="", flush=True)
    for _ in range(30):
        time.sleep(1)
        print(".", end="", flush=True)
        if ollama_in_path():
            print()
            ok("Ollama installed successfully.")
            return

    print()
    warn("Ollama not detected on PATH yet — you may need to restart your terminal.")
    warn("After restarting, run:  python setup.py  again.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 3 — Start Ollama server if needed
# ---------------------------------------------------------------------------

_OLLAMA_EXE_PATHS = (
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
    os.path.join(os.environ.get("ProgramFiles",  ""), "Ollama", "ollama.exe"),
)


def ensure_server_running():
    step("Starting Ollama server")

    if ollama_api_running():
        ok("Ollama server is already running.")
        return

    # Try to launch it
    exe = next((p for p in _OLLAMA_EXE_PATHS if p and os.path.isfile(p)), None)
    if exe:
        subprocess.Popen(
            [exe, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    elif shutil.which("ollama"):
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        warn("Could not find ollama executable to start the server.")
        return

    print("  Waiting for server to start", end="", flush=True)
    for _ in range(20):
        time.sleep(0.5)
        print(".", end="", flush=True)
        if ollama_api_running():
            print()
            ok("Server is up.")
            return

    print()
    warn("Server did not respond in time. It may still be starting — try running main.py.")


# ---------------------------------------------------------------------------
# Step 4 — Pull the language model
# ---------------------------------------------------------------------------

MODEL = "qwen2.5:0.5b"


def pull_model():
    step(f"Downloading language model: {MODEL}")

    try:
        import ollama as _ol
        listed = _ol.list()
        names = {m.model.split(":")[0] for m in listed.models}
        if MODEL.split(":")[0] in names:
            ok(f"{MODEL} is already downloaded.")
            return
    except Exception:
        pass  # will try to pull anyway

    print(f"  Pulling {MODEL} — this is a one-time ~400 MB download...")
    try:
        import ollama as _ol
        _ol.pull(MODEL)
        ok(f"{MODEL} ready.")
    except Exception as err:
        fail(f"Could not pull model: {err}")
        print("  You can do it manually later:  ollama pull qwen2.5:0.5b")


# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

def print_summary():
    step("Setup complete — you're ready to go!")
    print()
    print("  Run the app with:")
    print()
    print("      python main.py")
    print()
    print("  Press Q in the video window to quit.")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════╗")
    print("║        AI Eye — Setup Script         ║")
    print("╚══════════════════════════════════════╝")

    install_packages()
    install_ollama()
    ensure_server_running()
    pull_model()
    print_summary()
