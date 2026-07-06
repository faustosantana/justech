# -*- coding: utf-8 -*-
"""HTML renderer for Justech Control Center enterprise UI."""


def status_class(status):
    mapping = {
        "active": "justech-cc-green",
        "ok": "justech-cc-green",
        "pass": "justech-cc-green",
        "partial": "justech-cc-yellow",
        "warn": "justech-cc-yellow",
        "warning": "justech-cc-yellow",
        "inactive": "justech-cc-red",
        "fail": "justech-cc-red",
        "error": "justech-cc-red",
        "unavailable": "justech-cc-gray",
    }
    return mapping.get((status or "").lower(), "justech-cc-gray")


def card(title, value, subtitle="", status="ok", icon="fa-circle"):
    cls = status_class(status)
    return f"""
    <div class="justech-cc-card {cls}">
        <div class="justech-cc-card-icon"><i class="fa {icon}"></i></div>
        <div class="justech-cc-card-title">{title}</div>
        <div class="justech-cc-card-value">{value}</div>
        <div class="justech-cc-card-sub">{subtitle}</div>
    </div>
    """


def grid(*cards_html):
    return f'<div class="justech-cc-grid">{"".join(cards_html)}</div>'


def section(title, body):
    return f"""
    <div class="justech-cc-section">
        <h2 class="justech-cc-section-title">{title}</h2>
        {body}
    </div>
    """
