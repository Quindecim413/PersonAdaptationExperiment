from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True, eq=True)
class Material:
    name: str = ''
    Kd: Tuple[float, float, float] = .8, .8, .8