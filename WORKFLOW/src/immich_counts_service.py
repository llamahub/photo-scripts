"""Business logic for daily Immich asset update counts."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from immich_client import ImmichClient


@dataclass
class ImmichCountsResult:
    """Summary of daily update counts from Immich."""

    total_assets: int
    total_days: int
    counts_by_day: Dict[str, int]


class ImmichCountsService:
    """Read-only service to group Immich updates by day."""

    def __init__(self, client: ImmichClient, logger: Any):
        self.client = client
        self.logger = logger

    def run(self, options: Dict[str, Any]) -> ImmichCountsResult:
        """Fetch update timestamps and aggregate daily counts."""
        timestamps = self.client.fetch_updated_timestamps(
            before=options.get("before"),
            after=options.get("after"),
            album_name=options.get("album_name"),
        )

        counter = Counter()
        for value in timestamps:
            day = self._to_day(value)
            if day:
                counter[day] += 1

        counts_by_day = dict(sorted(counter.items()))

        for day, count in counts_by_day.items():
            self.logger.info("%s %s", day, count)

        return ImmichCountsResult(
            total_assets=sum(counts_by_day.values()),
            total_days=len(counts_by_day),
            counts_by_day=counts_by_day,
        )

    @staticmethod
    def _to_day(value: str) -> str:
        if not value:
            return ""

        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.date().isoformat()
