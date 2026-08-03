"""Unit tests — Lottery IA Explorer (catalog cards + nav stack)."""

from __future__ import annotations

from app.lottery.ai.explorer.catalog_cards import (
    build_compare_board,
    build_number_card,
    build_table_explorer,
)
from app.lottery.ai.explorer.nav_state import ExplorerNavState


def test_number_card_from_catalog_cache():
    card = build_number_card(57)
    assert card["number"] == 57
    assert card["cached"] is True
    assert "table1" in card and "table2" in card
    assert isinstance(card["table1"]["companions"], list)
    assert isinstance(card["table2"]["neighbors"], list)
    # second call hits lru cache
    assert build_number_card(57)["label"] == card["label"]


def test_table_explorer_interactive_rows():
    t1 = build_table_explorer("1")
    assert t1["table"] == "1"
    assert t1["row_count"] > 0
    assert t1["rows"][0]["interactive"] is True


def test_compare_board_multi():
    board = build_compare_board([57, 35, 81])
    assert board["numbers"] == [57, 35, 81]
    assert len(board["cards"]) == 3


def test_nav_stack_back_forward_breadcrumb():
    nav = ExplorerNavState()
    nav.push(number="57", view="analizar", origin="chat")
    nav.push(number="57", view="tabla1", label="Tabla 1", origin="click")
    nav.push(number="35", view="analizar", origin="click")
    nav.push(number="35", view="vecinos", label="Vecinos", origin="click")
    nav.push(number="81", view="analizar", origin="click")
    assert nav.current and nav.current.number == "81"
    assert nav.can_back()
    nav.back()
    assert nav.current and nav.current.number == "35"
    nav.back()
    assert nav.current and nav.current.view == "analizar"
    crumb_id = nav.stack[0].id
    nav.jump_to(crumb_id)
    assert nav.current and nav.current.number == "57"
    crumbs = nav.breadcrumbs
    assert crumbs[0]["label"] == "Inicio"
    assert any(c["label"] == "57" or c.get("number") == "57" for c in crumbs)


def test_toggle_compare_and_favorites():
    nav = ExplorerNavState()
    nav.toggle_compare("57")
    nav.toggle_compare("35")
    assert nav.compare == ["57", "35"]
    nav.toggle_favorite("57")
    assert "57" in nav.favorites
