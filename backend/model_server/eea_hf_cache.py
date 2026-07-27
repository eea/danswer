"""EEA-only: sanity-check the baked-in HuggingFace cache at startup.

Kept in its own module (rather than inline in `main.py`) so upstream merges never
have a reason to touch it - `main.py` only needs a single import line to wire this
in. See plans/hf-cache-eea-overlay.md for the full story.

The actual cache population happens at image-build time in the `*.eea` Dockerfile
overlays (`backend/Dockerfile.eea`, `backend/Dockerfile.model_server.eea`), which
bake models directly into `HF_HOME` (`/usr/share/huggingface`). The prod Helm chart's
`hfCache` init container then copies that baked-in directory into a writable emptyDir
mounted at the same path before this container starts. This check just confirms, at
process startup, that the expected content actually made it through that chain -
if it's empty, `HF_HUB_OFFLINE=1` will make every embedding/tokenizer call fail, so
better to log it loudly here than let the first request surface a confusing error.
"""

import os
from pathlib import Path

from onyx.utils.logger import setup_logger

logger = setup_logger()


def check_hf_cache_populated() -> None:
    hf_home = os.environ.get("HF_HOME")
    if not hf_home:
        return

    cache_path = Path(hf_home)
    if not cache_path.is_dir() or not any(cache_path.iterdir()):
        logger.warning(
            "HF_HOME (%s) is missing or empty at startup. If HF_HUB_OFFLINE is set, "
            "model/tokenizer loads will fail. Check that the image baked models into "
            "this path and that the hfCache init container populated the mounted "
            "volume correctly.",
            hf_home,
        )
        return

    logger.notice("HF_HOME (%s) is populated.", hf_home)
