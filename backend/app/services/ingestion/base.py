from abc import ABC, abstractmethod
from typing import Any


class IngestionAdapter(ABC):
    name: str
    description: str = "Ingestion adapter"

    @abstractmethod
    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Return normalized opportunity dictionaries ready for persistence."""
