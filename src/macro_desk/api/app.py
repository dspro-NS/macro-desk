from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional, Union

from fastapi import FastAPI

from macro_desk.ai.contracts import ExplanationProvider
from macro_desk.ai.service import build_explanation_provider
from macro_desk.api.routes import router
from macro_desk.config import Settings, load_settings
from macro_desk.db.repository import connect, initialize

logger = logging.getLogger(__name__)

_UNSET = object()


def create_app(
    settings: Optional[Settings] = None,
    explanation_provider: Union[ExplanationProvider, None, object] = _UNSET,
) -> FastAPI:
    settings = settings or load_settings()
    provider: Optional[ExplanationProvider]
    if explanation_provider is _UNSET:
        provider = build_explanation_provider(settings)
    else:
        provider = explanation_provider  # type: ignore[assignment]

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        connection = connect(settings.database_path)
        try:
            initialize(connection)
        finally:
            connection.close()
        logger.info("Database ready at %s", settings.database_path)
        yield

    app = FastAPI(
        title="Macro Desk",
        description="Personal India macro and RBI intelligence system",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.explanation_provider = provider
    app.include_router(router)
    return app
