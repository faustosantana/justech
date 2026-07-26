"""Motor access to official results — never query tables directly.

Re-exports LotteryResultService for Complete Analysis / prospective consumers.
Does not alter ranking, tables, or tiebreak.
"""

from __future__ import annotations

from app.services.lottery_result_service import LotteryResultService, flatten_draw

__all__ = ["LotteryResultService", "flatten_draw"]
