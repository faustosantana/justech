"""Teams Graph — sin $top en joinedTeams."""

from __future__ import annotations

import pytest

from integrations.microsoft365.graph_helpers import graph_list


class _FakeGraph:
    def __init__(self):
        self.last_params: dict | None = None

    @property
    def connected(self):
        return True

    def graph(self):
        return self

    async def request(self, method, path, params=None, headers=None):
        self.last_params = params
        return {"value": [{"id": "t1", "displayName": "Team A"}]}


class _FakeClient:
    def __init__(self):
        self._g = _FakeGraph()

    def graph(self):
        return self._g


@pytest.mark.asyncio
async def test_graph_list_can_skip_top():
    client = _FakeClient()
    await graph_list(client, "/me/joinedTeams", limit=10, use_top=False, map_row=lambda r: r)
    assert "$top" not in (client._g.last_params or {})


@pytest.mark.asyncio
async def test_graph_list_uses_top_by_default():
    client = _FakeClient()
    await graph_list(client, "/me/messages", limit=10, map_row=lambda r: r)
    assert client._g.last_params.get("$top") == "10"
