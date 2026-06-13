"""Task modules for the slide and infographic generation pipelines."""

from .task_01_genre import run_task_01
from .task_02_analysis import run_task_02
from .task_03_structure import run_task_03
from .task_04_content import run_task_04
from .task_05_design import run_task_05
from .task_06_slides import run_task_06
from .task_07_prompts import run_task_07, run_task_07_single_slide

# Infographic pipeline tasks
from .task_i0_analysis import run_task_i0
from .task_i1_design import run_task_i1
from .task_i2_prompts import run_task_i2
from .task_i2_critique import run_task_i2_critique, run_task_i2_refine

__all__ = [
    "run_task_01",
    "run_task_02",
    "run_task_03",
    "run_task_04",
    "run_task_05",
    "run_task_06",
    "run_task_07",
    "run_task_07_single_slide",
    # Infographic pipeline
    "run_task_i0",
    "run_task_i1",
    "run_task_i2",
    "run_task_i2_critique",
    "run_task_i2_refine",
]
