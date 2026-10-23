# In the name of God, the Most Gracious, the Most Merciful
"""Tests for the MCP client name shown during a live GUI session."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from mcp.server.session import ServerSession

from qspice_mcp.infra import mcp_client_name
from qspice_mcp.infra.mcp_client_name import (
    clear_mcp_client_name,
    current_mcp_client_name,
    install_initialize_client_hook,
    record_client_name_from_session,
    record_mcp_client_name,
    show_mcp_client_name,
)


@pytest.fixture(autouse=True)
def _reset_client_name():
    clear_mcp_client_name()
    mcp_client_name._STATE.initialized = None
    yield
    clear_mcp_client_name()
    mcp_client_name._STATE.initialized = None


def test_blank_client_name_is_ignored_and_visibility_follows_the_session() -> None:
    record_mcp_client_name("   ")
    assert show_mcp_client_name() is None

    record_mcp_client_name(" Cursor ")
    assert show_mcp_client_name() == "Cursor"
    assert current_mcp_client_name() == "Cursor"
    clear_mcp_client_name()
    assert current_mcp_client_name() is None


def test_session_client_info_records_only_a_string_name() -> None:
    record_client_name_from_session(None)
    record_client_name_from_session(SimpleNamespace())
    record_client_name_from_session(
        SimpleNamespace(client_params=SimpleNamespace(clientInfo=SimpleNamespace(name=7)))
    )
    assert show_mcp_client_name() is None

    record_client_name_from_session(
        SimpleNamespace(client_params=SimpleNamespace(clientInfo=SimpleNamespace(name="Codex")))
    )
    assert show_mcp_client_name() == "Codex"


def test_initialize_hook_records_the_client_and_still_calls_the_session() -> None:
    seen: list[object] = []

    async def original(_self: object, responder: object) -> None:
        seen.append(responder)

    saved_method = ServerSession._received_request
    saved_flag = mcp_client_name._STATE.hook_installed
    ServerSession._received_request = original  # type: ignore[method-assign]
    mcp_client_name._STATE.hook_installed = False
    try:
        install_initialize_client_hook()
        install_initialize_client_hook()
        ignored = SimpleNamespace(
            request=SimpleNamespace(root=SimpleNamespace(method="tools/list"))
        )
        initialize = SimpleNamespace(
            request=SimpleNamespace(
                root=SimpleNamespace(
                    method="initialize",
                    params=SimpleNamespace(clientInfo=SimpleNamespace(name="ChatGPT")),
                )
            )
        )
        unnamed = SimpleNamespace(
            request=SimpleNamespace(
                root=SimpleNamespace(
                    method="initialize",
                    params=SimpleNamespace(clientInfo=SimpleNamespace(name=None)),
                )
            )
        )
        asyncio.run(ServerSession._received_request(ServerSession, ignored))  # type: ignore[arg-type]
        asyncio.run(ServerSession._received_request(ServerSession, unnamed))  # type: ignore[arg-type]
        asyncio.run(ServerSession._received_request(ServerSession, initialize))  # type: ignore[arg-type]
    finally:
        ServerSession._received_request = saved_method
        mcp_client_name._STATE.hook_installed = saved_flag

    assert seen == [ignored, unnamed, initialize]
    assert show_mcp_client_name() == "ChatGPT"
