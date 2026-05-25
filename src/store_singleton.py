"""Module-level singleton for the CanvasStore — components import this."""

from .config import settings
from .storage import CanvasStore

store = CanvasStore(settings.canvas_db_path)
