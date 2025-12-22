import os

from dataclasses import dataclass


@dataclass
class GraphConfig:
    max_iterations: int = int(os.getenv("MAX_ITERATIONS", "3"))