"""Backward-compatible module for old `paperwise.api.main:app` entrypoints."""

from paperwise.server.main import app, create_app

__all__ = ["app", "create_app"]
