"""EEA-only: sanity-check the baked-in HuggingFace cache at process startup, and
fall back to online mode if it's missing rather than let every model/tokenizer
load fail hard.

Wired in from `model_server/__init__.py` (a single import line there - see that
file) rather than from `main.py`, and runs as an import-time side effect rather
than a function some other module has to remember to call. Both choices matter for
the same reason: this MUST execute before `transformers`/`huggingface_hub` get
imported anywhere in the process, because `HF_HUB_OFFLINE` is read into a frozen
module-level constant the moment `huggingface_hub.constants` is first imported -
mutating `os.environ` after that point is a silent no-op. `main.py` imports
`transformers` at module level, so by the time any code running inside it (e.g. its
`lifespan` hook) could call us, it would already be too late. Python guarantees
`model_server/__init__.py` runs in full before `model_server/main.py`'s body does,
which is what makes this timing work.

The actual cache population happens at image-build time in the `*.eea` Dockerfile
overlays (`backend/Dockerfile.eea`, `backend/Dockerfile.model_server.eea`), which
bake models directly into `HF_HOME` (`/usr/share/huggingface`). The prod Helm chart's
`hfCache` init container then copies that baked-in directory into a writable emptyDir
mounted at the same path before this container starts. This check confirms, at
process startup, that the expected content actually made it through that chain. If
it didn't (init container failed, volume mount misconfigured, whatever), `HF_HUB_OFFLINE=1`
baked into the image would otherwise make every embedding/tokenizer call fail hard for
the pod's whole lifetime with no way to recover. Rather than let a broken cache take
the deployment down, fall back to online mode for this process - the network policy
already allowlists huggingface.co egress for exactly this case - and log loudly so the
underlying cache problem still gets noticed and fixed.
"""

import os
from pathlib import Path

from onyx.utils.logger import setup_logger

logger = setup_logger()


def _check_hf_cache_populated() -> None:
    hf_home = os.environ.get("HF_HOME")
    if not hf_home:
        return

    cache_path = Path(hf_home)
    if cache_path.is_dir() and any(cache_path.iterdir()):
        logger.notice("HF_HOME (%s) is populated.", hf_home)
        return

    if os.environ.get("HF_HUB_OFFLINE") == "1":
        logger.warning(
            "HF_HOME (%s) is missing or empty at startup, but HF_HUB_OFFLINE=1 is "
            "baked into this image. Falling back to online mode for this process so "
            "model/tokenizer loads pull over the network instead of failing outright. "
            "This is a safety net, not a fix - check that the image baked models into "
            "this path and that the hfCache init container populated the mounted "
            "volume correctly.",
            hf_home,
        )
        os.environ["HF_HUB_OFFLINE"] = "0"
    else:
        logger.warning(
            "HF_HOME (%s) is missing or empty at startup.",
            hf_home,
        )


_check_hf_cache_populated()
