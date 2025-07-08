"""Type definitions for integration tests."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Protocol

from aioesphomeapi import APIClient

ConfigWriter = Callable[[str, str | None], Awaitable[Path]]
CompileFunction = Callable[[Path], Awaitable[Path]]
RunFunction = Callable[[Path], Awaitable[asyncio.subprocess.Process]]
RunCompiledFunction = Callable[[str, str | None], AbstractAsyncContextManager[None]]
WaitFunction = Callable[[APIClient, float], Awaitable[bool]]


class APIClientFactory(Protocol):
    """Protocol for API client factory."""

    def __call__(  # noqa: E704
        self,
        address: str = "localhost",
        port: int | None = None,
        password: str = "",
        noise_psk: str | None = None,
        client_info: str = "integration-test",
    ) -> AbstractAsyncContextManager[APIClient]: ...


class APIClientConnectedFactory(Protocol):
    """Protocol for connected API client factory."""

    def __call__(  # noqa: E704
        self,
        address: str = "localhost",
        port: int | None = None,
        password: str = "",
        noise_psk: str | None = None,
        client_info: str = "integration-test",
        timeout: float = 30,
    ) -> AbstractAsyncContextManager[APIClient]: ...
