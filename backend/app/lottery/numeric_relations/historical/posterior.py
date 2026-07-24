"""Seguimiento posterior del candidato fortalecido (ciclos + censura)."""

from __future__ import annotations

from app.lottery.numeric_relations.historical.models import DrawRef, LotteryScope, PosteriorOutcome
from app.lottery.numeric_relations.historical.universe import InMemoryDrawUniverse


def compute_posterior(
    *,
    candidate: int,
    anchor: DrawRef,
    confirmation_draw_ids: list[str],
    scope: LotteryScope,
    universe: InMemoryDrawUniverse,
    max_horizon: int = 10,
    tz_name: str = "America/Santo_Domingo",
) -> PosteriorOutcome:
    """
    Busca reaparición de `candidate` en sorteos posteriores de follow-up lotteries.
    CENSORED: no hay suficientes sorteos posteriores para el horizonte máximo.
    No cuenta censurado como fallo definitivo.
    """
    follow_ids = list(scope.follow_up_lottery_ids)
    # Merge sequences: take chronological union across follow-up lotteries
    # Policy: for each follow-up lottery, get next max_horizon draws; then find earliest hit
    # Evaluable horizon H requires at least H posterior draws available in the merged sequence
    # used for that lottery. Default: evaluate per primary follow lottery sequence separately
    # and take the minimum draws_until_response across lotteries (first response).

    best_offset: int | None = None
    best_draw_id: str | None = None
    examined: list[str] = []
    max_available = 0

    for lid in follow_ids:
        seq = universe.draws_after(lid, after=anchor, k=max_horizon, tz_name=tz_name)
        max_available = max(max_available, len(seq))
        for idx, d in enumerate(seq, start=1):
            examined.append(str(d.draw_id))
            if int(candidate) in d.numbers_1_to_100():
                if best_offset is None or idx < best_offset:
                    best_offset = idx
                    best_draw_id = str(d.draw_id)
                break

    censored = max_available < max_horizon
    censored_horizons: list[str] = []

    def flag(h: int) -> bool | None:
        if max_available < h:
            censored_horizons.append(f"within_{h}" if h > 1 else "next_1")
            return None  # not evaluable
        if best_offset is None:
            return False
        return best_offset <= h

    responded_next = flag(1)
    responded_2 = flag(2)
    responded_3 = flag(3)
    responded_5 = flag(5)
    responded_10 = flag(10)

    return PosteriorOutcome(
        candidate=int(candidate),
        anchor_draw_id=str(anchor.draw_id),
        confirmation_draw_ids=list(confirmation_draw_ids),
        follow_up_lottery_ids=follow_ids,
        first_response_draw_id=best_draw_id,
        draws_until_response=best_offset,
        responded_next_draw=responded_next,
        responded_within_2=responded_2,
        responded_within_3=responded_3,
        responded_within_5=responded_5,
        responded_within_10=responded_10,
        censored=censored,
        censored_horizons=sorted(set(censored_horizons)),
        draws_examined=examined,
        max_horizon=max_horizon,
    )
