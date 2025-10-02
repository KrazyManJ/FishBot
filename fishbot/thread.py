from threading import Thread, Event
from .model import FishBotScanData
from .constants import *
import pyautogui
import autoit
from datetime import datetime, timedelta

class FishBotThread(Thread):

    def __init__(self):
        super(FishBotThread, self).__init__(target=self.__run, daemon=True)
        self._stop_event = Event()
        self._region: tuple[int, int, int, int] | None = None
        self.start()

    def terminate(self) -> None:
        self._stop_event.set()

    def isTerminated(self) -> bool:
        return self._stop_event.is_set()

    def __scanData(self,includeLootData) -> FishBotScanData:
        line, c, ct, r = None, None, None, "unknown"
        pic = pyautogui.screenshot(region=self._region)
        for x in range(0, pic.width):
            color = pic.getpixel((x, 0))
            if line is None and color == LINE_COLOR:
                line = x
            elif c is None and color == FISH_COLOR:
                c = x
                if includeLootData:
                    ct = "treasure" if pic.getpixel((x + 4, 0)) != FISH_COLOR else "fish"
                    if line is not None:
                        for bc in range(x,line,-1):
                            col = pic.getpixel((bc,0))
                            if col in RARITY_COLORS.values():
                                r = (list(RARITY_COLORS.keys())[list(RARITY_COLORS.values()).index(col)])
            if c is not None and line is not None:
                break
        return FishBotScanData(line, c, ct, r)

    def __calibrate(self) -> bool:
        s = pyautogui.screenshot()
        lx, ly, linemiddle = None, None, None
        for x in range(s.width):
            for y in range(s.height):
                if s.getpixel((x, y)) == LINE_COLOR:
                    lx, ly = x, y
                    break
            if (lx, ly) != (None, None):
                break
        if (lx, ly) == (None, None):
            return False
        for y in range(ly, s.height):
            if s.getpixel((lx, y)) != LINE_COLOR:
                linemiddle = int(ly + (y - ly) // 2.7)
                break
        for x in range(lx, s.width):
            if s.getpixel((x, ly)) == (255, 255, 255):
                self._region = (lx, linemiddle, x - lx, 1)
                break
        return self._region is not None

    @staticmethod
    def __castRod() -> None:
        pyautogui.sleep(0.3)
        autoit.mouse_down()
        pyautogui.sleep(0.3)
        autoit.mouse_up()
        pyautogui.sleep(1.5)

    @staticmethod
    def __castRodAgain() -> None:
        from .gui import GUI
        for _ in range(2):
            pyautogui.sleep(0.5)
            autoit.send(GUI.Vars["settings_rod_key"].get())
        FishBotThread.__castRod()

    def __preventAFKKick(self,toggler) -> None:
        autoit.mouse_move(
            x=self._region[0] if toggler else self._region[0] + self._region[2], 
            y=self._region[1],
        )
        pyautogui.sleep(0.1)

    @staticmethod
    def __useBait(baitType):
        from .gui import GUI
        autoit.send(GUI.Vars[f"settings_bait{baitType}_key"].get())
        autoit.mouse_down()
        pyautogui.sleep(1.5)
        autoit.mouse_up()
        pyautogui.sleep(0.2)
        autoit.send(GUI.Vars["settings_rod_key"].get())

    def __run(self) -> None:
        from .gui import GUI
        def updateStatus(value):
            if not self.isTerminated(): GUI.Vars["status"].set(value)

        def updateTime(start):
            if self.is_alive():
                s = (datetime.now() - start).seconds
                GUI.Vars["time_elapsed"].set('{:02}h {:02}m {:02}s'.format(s // 3600, s % 3600 // 60, s % 60))
                GUI.win.after(1000, lambda: updateTime(start))

        updateStatus("Waiting for first catch to appear for calibration...")
        calibrationStart = datetime.now()
        while not self.__calibrate():
            if self.isTerminated(): return
            if (datetime.now() - calibrationStart).total_seconds() >= 30:
                updateStatus("Error: Could not calibrate because bar was not found, script stopped!")
                GUI.toggleButton(True)
                return
        updateTime(datetime.now())
        autoit.mouse_move(self._region[0], self._region[1])
        lastTriggerTime,lastBaitTime = datetime.now(),(datetime.now()-timedelta(minutes=2))
        while True:
            if self.isTerminated(): return
            updateStatus("Waiting for another fish...")
            data = self.__scanData(True)
            sR, sCt = data.rarity, data.catchtype
            if (data.line, data.catch) != (None, None):
                updateStatus(f"Fishing {data.rarity} {data.catchtype}...")
                lastTriggerTime = datetime.now()
                while True:
                    if self.isTerminated(): return
                    data = self.__scanData(False)
                    if data.line is None:
                        break
                    elif data.catch is not None and data.line < data.catch:
                        autoit.mouse_down()
                    else:
                        autoit.mouse_up()
                autoit.mouse_up()
                GUI.Vars["total_catch_amount"].set(GUI.Vars["total_catch_amount"].get() + 1)
                if f"{sR}_{sCt}" in GUI.Vars.keys():
                    GUI.Vars[f"{sR}_{sCt}"].set(GUI.Vars[f"{sR}_{sCt}"].get() + 1)
                updateStatus("Preventick AFK-Kick...")
                if self.isTerminated(): return
                self.__preventAFKKick(GUI.Vars["total_catch_amount"].get() % 2 == 0)
                if self.isTerminated(): return
                if GUI.Vars["settings_use_bait1"].get() == "1" or GUI.Vars["settings_use_bait2"].get() == "1":
                    if (datetime.now() - lastBaitTime).total_seconds() >= 120:
                        for i in range(1,3):
                            if GUI.Vars[f"settings_use_bait{i}"].get() == "1":
                                updateStatus(f"Using tier {i} bait...")
                                FishBotThread.__useBait(i)
                            if self.isTerminated(): return
                        lastBaitTime = datetime.now()
                updateStatus("Casting fishing rod...")
                self.__castRod()
                if self.isTerminated(): return
            if (datetime.now() - lastTriggerTime).total_seconds() >= 30:
                lastTriggerTime = datetime.now()
                updateStatus("No fish for a long time, casting fishing rod again...")
                self.__castRodAgain()
            pyautogui.sleep(0.1)