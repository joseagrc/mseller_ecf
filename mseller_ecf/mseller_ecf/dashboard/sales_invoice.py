from __future__ import annotations

from mseller_ecf.mseller_ecf.dashboard.common import add_mseller_ecf_connection


def get_data(data: dict) -> dict:
    return add_mseller_ecf_connection(data)
