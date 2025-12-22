import os

from dataclasses import dataclass


@dataclass
class GraphConfig:
    max_iterations: int = int(os.getenv("AGENT_MAX_ITERATIONS", "5"))