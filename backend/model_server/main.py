import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
import torch
import uvicorn
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from transformers import logging as transformer_logging

from model_server.encoders import router as encoders_router
from model_server.management_endpoints import router as management_router
from model_server.utils import get_gpu_type
from onyx import __version__
from onyx.utils.logger import setup_logger
from onyx.utils.logger import setup_uvicorn_logger
from onyx.utils.middleware import add_onyx_request_id_middleware
from onyx.utils.middleware import add_onyx_tenant_id_middleware
from shared_configs.configs import INDEXING_ONLY
from shared_configs.configs import MIN_THREADS_ML_MODELS
from shared_configs.configs import MODEL_SERVER_ALLOWED_HOST
from shared_configs.configs import MODEL_SERVER_PORT
from shared_configs.configs import SENTRY_DSN

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

HF_HOME = os.environ.get("HF_HOME", "/usr/share/huggingface")
HF_CACHE_PATH = Path(HF_HOME)

transformer_logging.set_verbosity_error()

logger = setup_logger()

file_handlers = [
    h for h in logger.logger.handlers if isinstance(h, logging.FileHandler)
]

setup_uvicorn_logger(shared_file_handlers=file_handlers)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    gpu_type = get_gpu_type()
    logger.notice(f"Torch GPU Detection: gpu_type={gpu_type}")

    app.state.gpu_type = gpu_type

    torch.set_num_threads(max(MIN_THREADS_ML_MODELS, torch.get_num_threads()))
    logger.notice(f"Torch Threads: {torch.get_num_threads()}")

    yield


def get_model_app() -> FastAPI:
    application = FastAPI(
        title="Onyx Model Server", version=__version__, lifespan=lifespan
    )
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[StarletteIntegration(), FastApiIntegration()],
            traces_sample_rate=0.1,
            release=__version__,
        )
        logger.info("Sentry initialized")
    else:
        logger.debug("Sentry DSN not provided, skipping Sentry initialization")

    application.include_router(management_router)
    application.include_router(encoders_router)

    request_id_prefix = "INF"
    if INDEXING_ONLY:
        request_id_prefix = "IDX"

    add_onyx_tenant_id_middleware(application, logger)
    add_onyx_request_id_middleware(application, request_id_prefix, logger)

    # Initialize and instrument the app
    Instrumentator().instrument(application).expose(application)

    return application


app = get_model_app()


if __name__ == "__main__":
    logger.notice(
        f"Starting Onyx Model Server on http://{MODEL_SERVER_ALLOWED_HOST}:{str(MODEL_SERVER_PORT)}/"
    )
    logger.notice(f"Model Server Version: {__version__}")
    uvicorn.run(app, host=MODEL_SERVER_ALLOWED_HOST, port=MODEL_SERVER_PORT)
