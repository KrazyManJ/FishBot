from dataclasses import dataclass
from typing import Protocol, Literal

__all__ = ["FishBotScanData"]

CatchType = Literal["fish", "treasure"]
CatchRarity = Literal["common", "uncommon", "rare", "mythic", "legendary"]

@dataclass
class FishBotScanData:
	red_line_x: int
	catch_area_x: int
	catch_type: CatchType
	catch_rarity: CatchRarity
	
class OnCatchProtocol(Protocol):
	def __call__(self, catch_type: CatchType, catch_rarity: CatchRarity): ...
