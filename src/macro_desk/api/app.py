from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI

from macro_desk.api.routes import router
from macro_desk.config import Settings, load_settings
from macro_desk.db.repository import connect, initialize

logger = logging.getLogger(__name__)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or load_settings()

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
    app.include_router(router)
    return app
