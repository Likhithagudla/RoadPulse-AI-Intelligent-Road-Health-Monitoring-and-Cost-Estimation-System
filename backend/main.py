"""
RoadPulse AI - Main Application Entrypoint
Delegates to modular backend.app package while maintaining complete backward compatibility.
"""

import sys
from pathlib import Path

# Ensure backend root is on sys.path
BACKEND_ROOT = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.main import app, create_app

__all__ = ["app", "create_app"]

if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings

    cwd = Path.cwd().resolve()
    if cwd == BACKEND_ROOT:
        target = "app.main:app"
    else:
        target = "backend.app.main:app"

    uvicorn.run(
        target,
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
