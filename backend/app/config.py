from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BASE_DIR / "workspace"
REPOS_DIR = WORKSPACE_DIR / "repos"

# Ensure runtime directories exist
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
REPOS_DIR.mkdir(parents=True, exist_ok=True)

# Application metadata
APP_TITLE = "Software Forensics & Change Impact Intelligence"
APP_DESCRIPTION = (
    "Evidence-driven code intelligence engine that reconstructs AST, dependencies, "
    "call graphs, tests, and Git history to detect architectural drift and compute change impact & risk."
)
APP_VERSION = "1.0.0"
