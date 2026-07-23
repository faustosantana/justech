"""Compatibility re-export — continuous detector lives in services.lottery_ai_alert_detector."""

from app.services.lottery_ai_alert_detector import (
    DetectedFinding,
    DetectorRunResult,
    LotteryAiAlertDetector,
    maybe_run_detector_tick,
)

__all__ = [
    "DetectedFinding",
    "DetectorRunResult",
    "LotteryAiAlertDetector",
    "maybe_run_detector_tick",
]
