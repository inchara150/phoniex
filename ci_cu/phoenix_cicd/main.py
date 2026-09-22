"""Production entrypoint.

    export PHOENIX_WEBHOOK_SECRET=...  GITHUB_TOKEN=...
    export PHOENIX_DRY_RUN=1                       # default; set 0 only when ready
    export PHOENIX_FIXER=brain:run_fix             # "module:callable" (state dict -> dict)
    uvicorn phoenix_cicd.main:app_factory --factory --port 8080
"""
from __future__ import annotations

import importlib
import logging
import os

from .app import create_app
from .github_client import PyGithubClient
from .pipeline import FixPipeline, noop_fixer


def load_fixer(spec: str | None):
    if not spec:
        return noop_fixer
    mod, _, attr = spec.partition(":")
    return getattr(importlib.import_module(mod), attr)


def app_factory():
    logging.basicConfig(level=logging.INFO)
    dry = os.environ.get("PHOENIX_DRY_RUN", "1") != "0"
    client = PyGithubClient(os.environ["GITHUB_TOKEN"], dry_run=dry)
    pipeline = FixPipeline(client, fixer=load_fixer(os.environ.get("PHOENIX_FIXER")),
                           telemetry_path=os.environ.get("PHOENIX_TELEMETRY_PATH", "telemetry.jsonl"))
    logging.getLogger("phoenix").info("starting, dry_run=%s", dry)
    return create_app(secret=os.environ["PHOENIX_WEBHOOK_SECRET"], pipeline=pipeline)
