from typing import List
import os

def get_subdirectories(directory: str) -> List[str]:
    """Return a list of subdirectory names in the given directory."""
    return [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))]
