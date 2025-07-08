from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any

from aioesphomeapi import APIClient, parse_log_message
from aioesphomeapi.log_runner import async_run

from esphome.const import CONF_KEY, CONF_PASSWORD, CONF_PORT, __version__
from esphome.core import CORE

from . import CONF_ENCRYPTION

if TYPE_CHECKING:
    from aioesphomeapi.api_pb2 import (
        SubscribeLogsResponse,  # pylint: disable=no-name-in-module
    )


_LOGGER = logging.getLogger(__name__)


async def async_run_logs(config: dict[str, Any], address: str) -> None:
    """Run the logs command in the event loop."""
    conf = config["api"]
    name = config["esphome"]["name"]
    port: int = int(conf[CONF_PORT])
    password: str = conf[CONF_PASSWORD]
    noise_psk: str | None = None
    if (encryption := conf.get(CONF_ENCRYPTION)) and (key := encryption.get(CONF_KEY)):
        noise_psk = key
    _LOGGER.info("Starting log output from %s using esphome API", address)
    cli = APIClient(
        address,
        port,
        password,
        client_info=f"ESPHome Logs {__version__}",
        noise_psk=noise_psk,
    )
    dashboard = CORE.dashboard

    def on_log(msg: SubscribeLogsResponse) -> None:
        """Handle a new log message."""
        time_ = datetime.now()
        message: bytes = msg.message
        text = message.decode("utf8", "backslashreplace")
        for parsed_msg in parse_log_message(
            text, f"[{time_.hour:02}:{time_.minute:02}:{time_.second:02}]"
        ):
            print(parsed_msg.replace("\033", "\\033") if dashboard else parsed_msg)

    stop = await async_run(cli, on_log, name=name)
    try:
        await asyncio.Event().wait()
    finally:
        await stop()


def run_logs(config: dict[str, Any], address: str) -> None:
    """Run the logs command."""
    try:
        asyncio.run(async_run_logs(config, address))
    except KeyboardInterrupt:
        pass
