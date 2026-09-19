from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EntropySample:
    method_name: str
    data: bytes
    bits_claimed: float
    metadata: dict = field(default_factory=dict)
    error: Optional[str] = None


class EntropyMethod(ABC):
    name: str = "unnamed"
    category: str = "computational"
    is_deterministic: bool = False
    theoretical_bits_per_unit: Optional[float] = None
    unit_description: str = "byte"

    @abstractmethod
    def generate(self, nbytes: int) -> EntropySample:
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}' cat='{self.category}'>"
