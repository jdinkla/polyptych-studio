"""Slide generation pipeline using Gemini API."""

from .models import (
    Task1Output,
    Task2Output,
    Task3Output,
    Task4Output,
    Task5Output,
    Task6Output,
    Task7Output,
)
from .client import TextClient, GeminiTextClient
from .pipeline import SlidePipeline

__all__ = [
    "Task1Output",
    "Task2Output",
    "Task3Output",
    "Task4Output",
    "Task5Output",
    "Task6Output",
    "Task7Output",
    "TextClient",
    "GeminiTextClient",
    "SlidePipeline",
]
