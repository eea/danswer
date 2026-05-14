import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import config and page_objects
sys.path.insert(0, str(Path(__file__).parent.parent))
