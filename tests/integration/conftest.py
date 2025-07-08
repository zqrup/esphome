"""Common fixtures for integration tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
import logging
import os
from pathlib import Path
import platform
import signal
import socket
import sys
import tempfile
from typing import TextIO

from aioesphomeapi import APIClient, APIConnectionError, LogParser, ReconnectLogic
import pytest
import pytest_asyncio

import esphome.config
from esphome.core import CORE
from esphome.platformio_api import get_idedata

from .const import (
    API_CONNECTION_TIMEOUT,
    DEFAULT_API_PORT,
    LOCALHOST,
    PORT_POLL_INTERVAL,
    PORT_WAIT_TIMEOUT,
    SIGINT_TIMEOUT,
    SIGTERM_TIMEOUT,
)
from .types import (
    APIClientConnectedFactory,
    APIClientFactory,
    CompileFunction,
    ConfigWriter,
    RunCompiledFunction,
)

# Skip all integration tests on Windows
if platform.system() == "Windows":
    pytest.skip(
        "Integration tests are not supported on Windows", allow_module_level=True
    )

import pty  # not available on Windows


@pytest.fixture(scope="module", autouse=True)
def enable_aioesphomeapi_debug_logging():
    """Enable debug logging for aioesphomeapi to help diagnose connection issues."""
    # Get the aioesphomeapi logger
    logger = logging.getLogger("aioesphomeapi")
    # Save the original level
    original_level = logger.level
    # Set to DEBUG level
    logger.setLevel(logging.DEBUG)
    # Also ensure we have a handler that outputs to console
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    yield
    # Restore original level
    logger.setLevel(original_level)


@pytest.fixture
def integration_test_dir() -> Generator[Path]:
    """Create a temporary directory for integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def reserved_tcp_port() -> Generator[tuple[int, socket.socket]]:
    """Reserve an unused TCP port by holding the socket open."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", 0))
    port = s.getsockname()[1]
    try:
        yield port, s
    finally:
        s.close()


@pytest.fixture
def unused_tcp_port(reserved_tcp_port: tuple[int, socket.socket]) -> int:
    """Get the reserved TCP port number."""
    return reserved_tcp_port[0]


@pytest_asyncio.fixture
async def yaml_config(request: pytest.FixtureRequest, unused_tcp_port: int) -> str:
    """Load YAML configuration based on test name."""
    # Get the test function name
    test_name: str = request.node.name
    # Extract the base test name (remove test_ prefix and any parametrization)
    base_name = test_name.replace("test_", "").partition("[")[0]

    # Load the fixture file
    fixture_path = Path(__file__).parent / "fixtures" / f"{base_name}.yaml"
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture file not found: {fixture_path}")

    loop = asyncio.get_running_loop()
    content = await loop.run_in_executor(None, fixture_path.read_text)

    # Replace the port in the config if it contains api section
    if "api:" in content:
        # Add port configuration after api:
        content = content.replace("api:", f"api:\n  port: {unused_tcp_port}")

    # Add debug build flags for integration tests to enable assertions
    if "esphome:" in content:
        # Check if platformio_options already exists
        if "platformio_options:" not in content:
            # Add platformio_options with debug flags after esphome:
            content = content.replace(
                "esphome:",
                "esphome:\n"
                "  # Enable assertions for integration tests\n"
                "  platformio_options:\n"
                "    build_flags:\n"
                '      - "-DDEBUG"  # Enable assert() statements\n'
                '      - "-g"       # Add debug symbols',
            )

    return content


@pytest_asyncio.fixture
async def write_yaml_config(
    integration_test_dir: Path, request: pytest.FixtureRequest
) -> AsyncGenerator[ConfigWriter]:
    """Write YAML configuration to a file."""
    # Get the test name for default filename
    test_name = request.node.name
    base_name = test_name.replace("test_", "").split("[")[0]

    async def _write_config(content: str, filename: str | None = None) -> Path:
        if filename is None:
            filename = f"{base_name}.yaml"
        config_path = integration_test_dir / filename
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, config_path.write_text, content)
        return config_path

    yield _write_config


@pytest_asyncio.fixture
async def compile_esphome(
    integration_test_dir: Path,
) -> AsyncGenerator[CompileFunction]:
    """Compile an ESPHome configuration and return the binary path."""

    async def _compile(config_path: Path) -> Path:
        # Retry compilation up to 3 times if we get a segfault
        max_retries = 3
        for attempt in range(max_retries):
            # Compile using subprocess, inheriting stdout/stderr to show progress
            proc = await asyncio.create_subprocess_exec(
                "esphome",
                "compile",
                str(config_path),
                cwd=integration_test_dir,
                stdout=None,  # Inherit stdout
                stderr=None,  # Inherit stderr
                stdin=asyncio.subprocess.DEVNULL,
                # Start in a new process group to isolate signal handling
                start_new_session=True,
            )
            await proc.wait()

            if proc.returncode == 0:
                # Success!
                break
            elif proc.returncode == -11 and attempt < max_retries - 1:
                # Segfault (-11 = SIGSEGV), retry
                print(
                    f"Compilation segfaulted (attempt {attempt + 1}/{max_retries}), retrying..."
                )
                await asyncio.sleep(1)  # Brief pause before retry
                continue
            else:
                # Other error or final retry
                raise RuntimeError(
                    f"Failed to compile {config_path}, return code: {proc.returncode}. "
                    f"Run with 'pytest -s' to see compilation output."
                )

        # Load the config to get idedata (blocking call, must use executor)
        loop = asyncio.get_running_loop()

        def _read_config_and_get_binary():
            CORE.config_path = str(config_path)
            config = esphome.config.read_config(
                {"command": "compile", "config": str(config_path)}
            )
            if config is None:
                raise RuntimeError(f"Failed to read config from {config_path}")

            # Get the compiled binary path
            idedata = get_idedata(config)
            return Path(idedata.firmware_elf_path)

        binary_path = await loop.run_in_executor(None, _read_config_and_get_binary)

        if not binary_path.exists():
            raise RuntimeError(f"Compiled binary not found at {binary_path}")

        return binary_path

    yield _compile


@asynccontextmanager
async def create_api_client(
    address: str = LOCALHOST,
    port: int = DEFAULT_API_PORT,
    password: str = "",
    noise_psk: str | None = None,
    client_info: str = "integration-test",
) -> AsyncGenerator[APIClient]:
    """Create an API client context manager."""
    client = APIClient(
        address=address,
        port=port,
        password=password,
        noise_psk=noise_psk,
        client_info=client_info,
    )
    try:
        yield client
    finally:
        await client.disconnect()


@pytest_asyncio.fixture
async def api_client_factory(
    unused_tcp_port: int,
) -> AsyncGenerator[APIClientFactory]:
    """Factory for creating API client context managers."""

    def _create_client(
        address: str = LOCALHOST,
        port: int | None = None,
        password: str = "",
        noise_psk: str | None = None,
        client_info: str = "integration-test",
    ) -> AbstractAsyncContextManager[APIClient]:
        return create_api_client(
            address=address,
            port=port if port is not None else unused_tcp_port,
            password=password,
            noise_psk=noise_psk,
            client_info=client_info,
        )

    yield _create_client


@asynccontextmanager
async def wait_and_connect_api_client(
    address: str = LOCALHOST,
    port: int = DEFAULT_API_PORT,
    password: str = "",
    noise_psk: str | None = None,
    client_info: str = "integration-test",
    timeout: float = API_CONNECTION_TIMEOUT,
) -> AsyncGenerator[APIClient]:
    """Wait for API to be available and connect."""
    client = APIClient(
        address=address,
        port=port,
        password=password,
        noise_psk=noise_psk,
        client_info=client_info,
    )

    # Create a future to signal when connected
    loop = asyncio.get_running_loop()
    connected_future: asyncio.Future[None] = loop.create_future()

    async def on_connect() -> None:
        """Called when successfully connected."""
        if not connected_future.done():
            connected_future.set_result(None)

    async def on_disconnect(expected_disconnect: bool) -> None:
        """Called when disconnected."""
        if not connected_future.done() and not expected_disconnect:
            connected_future.set_exception(
                APIConnectionError("Disconnected before fully connected")
            )

    async def on_connect_error(err: Exception) -> None:
        """Called when connection fails."""
        if not connected_future.done():
            connected_future.set_exception(err)

    # Create and start the reconnect logic
    reconnect_logic = ReconnectLogic(
        client=client,
        on_connect=on_connect,
        on_disconnect=on_disconnect,
        zeroconf_instance=None,  # Not using zeroconf for integration tests
        name=f"{address}:{port}",
        on_connect_error=on_connect_error,
    )

    try:
        # Start the connection
        await reconnect_logic.start()

        # Wait for connection with timeout
        try:
            await asyncio.wait_for(connected_future, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Failed to connect to API after {timeout} seconds")

        yield client
    finally:
        # Stop reconnect logic and disconnect
        await reconnect_logic.stop()
        await client.disconnect()


@pytest_asyncio.fixture
async def api_client_connected(
    unused_tcp_port: int,
) -> AsyncGenerator[APIClientConnectedFactory]:
    """Factory for creating connected API client context managers."""

    def _connect_client(
        address: str = LOCALHOST,
        port: int | None = None,
        password: str = "",
        noise_psk: str | None = None,
        client_info: str = "integration-test",
        timeout: float = API_CONNECTION_TIMEOUT,
    ) -> AbstractAsyncContextManager[APIClient]:
        return wait_and_connect_api_client(
            address=address,
            port=port if port is not None else unused_tcp_port,
            password=password,
            noise_psk=noise_psk,
            client_info=client_info,
            timeout=timeout,
        )

    yield _connect_client


async def _read_stream_lines(
    stream: asyncio.StreamReader, lines: list[str], output_stream: TextIO
) -> None:
    """Read lines from a stream, append to list, and echo to output stream."""
    log_parser = LogParser()
    while line := await stream.readline():
        decoded_line = (
            line.replace(b"\r", b"")
            .replace(b"\n", b"")
            .decode("utf8", "backslashreplace")
        )
        lines.append(decoded_line.rstrip())
        # Echo to stdout/stderr in real-time
        # Print without newline to avoid double newlines
        print(
            log_parser.parse_line(decoded_line, timestamp=""),
            file=output_stream,
            flush=True,
        )


@asynccontextmanager
async def run_binary_and_wait_for_port(
    binary_path: Path,
    host: str,
    port: int,
    timeout: float = PORT_WAIT_TIMEOUT,
) -> AsyncGenerator[None]:
    """Run a binary, wait for it to open a port, and clean up on exit."""
    # Create a pseudo-terminal to make the binary think it's running interactively
    # This is needed because the ESPHome host logger checks isatty()
    controller_fd, device_fd = pty.openpty()

    # Run the compiled binary with PTY
    process = await asyncio.create_subprocess_exec(
        str(binary_path),
        stdout=device_fd,
        stderr=device_fd,
        stdin=asyncio.subprocess.DEVNULL,
        # Start in a new process group to isolate signal handling
        start_new_session=True,
        pass_fds=(device_fd,),
    )

    # Close the device end in the parent process
    os.close(device_fd)

    # Convert controller_fd to async streams for reading
    loop = asyncio.get_running_loop()
    controller_reader = asyncio.StreamReader()
    controller_protocol = asyncio.StreamReaderProtocol(controller_reader)
    controller_transport, _ = await loop.connect_read_pipe(
        lambda: controller_protocol, os.fdopen(controller_fd, "rb", 0)
    )
    output_reader = controller_reader

    if process.returncode is not None:
        raise RuntimeError(
            f"Process died immediately with return code {process.returncode}. "
            "Ensure the binary is valid and can run successfully."
        )

    # Wait for the API server to start listening
    loop = asyncio.get_running_loop()
    start_time = loop.time()

    # Start collecting output
    stdout_lines: list[str] = []
    output_tasks: list[asyncio.Task] = []

    try:
        # Read from output stream
        output_tasks = [
            asyncio.create_task(
                _read_stream_lines(output_reader, stdout_lines, sys.stdout)
            )
        ]

        # Small yield to ensure the process has a chance to start
        await asyncio.sleep(0)

        while loop.time() - start_time < timeout:
            try:
                # Try to connect to the port
                _, writer = await asyncio.open_connection(host, port)
                writer.close()
                await writer.wait_closed()
                # Port is open, yield control
                yield
                return
            except (ConnectionRefusedError, OSError):
                # Check if process died
                if process.returncode is not None:
                    break
                # Port not open yet, wait a bit and try again
                await asyncio.sleep(PORT_POLL_INTERVAL)

        # Timeout or process died - build error message
        error_msg = f"Port {port} on {host} did not open within {timeout} seconds"

        if process.returncode is not None:
            error_msg += f"\nProcess exited with code: {process.returncode}"

        # Include any output collected so far
        if stdout_lines:
            error_msg += "\n\n--- Process Output ---\n"
            error_msg += "\n".join(stdout_lines[-100:])  # Last 100 lines

        raise TimeoutError(error_msg)

    finally:
        # Cancel output collection tasks
        for task in output_tasks:
            task.cancel()
        # Wait for tasks to complete and check for exceptions
        results = await asyncio.gather(*output_tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception) and not isinstance(
                result, asyncio.CancelledError
            ):
                print(
                    f"Error reading from PTY: {result}",
                    file=sys.stderr,
                )

        # Close the PTY transport (Unix only)
        if controller_transport is not None:
            controller_transport.close()

        # Cleanup: terminate the process gracefully
        if process.returncode is None:
            # Send SIGINT (Ctrl+C) for graceful shutdown
            process.send_signal(signal.SIGINT)
            try:
                await asyncio.wait_for(process.wait(), timeout=SIGINT_TIMEOUT)
            except asyncio.TimeoutError:
                # If SIGINT didn't work, try SIGTERM
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=SIGTERM_TIMEOUT)
                except asyncio.TimeoutError:
                    # Last resort: SIGKILL
                    process.kill()
                    await process.wait()


@asynccontextmanager
async def run_compiled_context(
    yaml_content: str,
    filename: str | None,
    write_yaml_config: ConfigWriter,
    compile_esphome: CompileFunction,
    port: int,
    port_socket: socket.socket | None = None,
) -> AsyncGenerator[None]:
    """Context manager to write, compile and run an ESPHome configuration."""
    # Write the YAML config
    config_path = await write_yaml_config(yaml_content, filename)

    # Compile the configuration and get binary path
    binary_path = await compile_esphome(config_path)

    # Close the port socket right before running to release the port
    if port_socket is not None:
        port_socket.close()

    # Run the binary and wait for the API server to start
    async with run_binary_and_wait_for_port(binary_path, LOCALHOST, port):
        yield


@pytest_asyncio.fixture
async def run_compiled(
    write_yaml_config: ConfigWriter,
    compile_esphome: CompileFunction,
    reserved_tcp_port: tuple[int, socket.socket],
) -> AsyncGenerator[RunCompiledFunction]:
    """Write, compile and run an ESPHome configuration."""
    port, port_socket = reserved_tcp_port

    def _run_compiled(
        yaml_content: str, filename: str | None = None
    ) -> AbstractAsyncContextManager[asyncio.subprocess.Process]:
        return run_compiled_context(
            yaml_content,
            filename,
            write_yaml_config,
            compile_esphome,
            port,
            port_socket,
        )

    yield _run_compiled
