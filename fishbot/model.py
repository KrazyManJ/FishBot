from dataclasses import dataclass

__all__ = ["FishBotScanData"]

@dataclass
class FishBotScanData:
	line: int
	catch: int
	catchtype: str
	rarity: str