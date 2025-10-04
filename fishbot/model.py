from dataclasses import dataclass
from typing import Protocol, Literal

__all__ = ["FishBotScanData", "OnCatchProtocol"]

CatchType = Literal["fish", "treasure"]
CatchRarity = Literal["common", "uncommon", "rare", "mythic", "legendary"]

@dataclass
class FishBotScanData:
    red_line_x: int | None = None
    catch_area_x: int | None = None
    catch_type: CatchType | None = None
    catch_rarity: CatchRarity | Literal["unknown"] = "unknown"
        
    def is_catch_bar_visible(self):
        return self.red_line_x is not None and self.catch_area_x is not None
	
class OnCatchProtocol(Protocol):
    def __call__(self, catch_type: CatchType, catch_rarity: CatchRarity): ...
