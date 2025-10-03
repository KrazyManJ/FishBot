from threading import Thread, Event
from .model import FishBotScanData, OnCatchProtocol
from .constants import *
from .utils import dict_key_from_value
import pyautogui
import autoit
from datetime import datetime, timedelta
from typing import Callable

class FishBotThread(Thread):

    def __init__(self,
        rod_key: str,
        use_bait1: bool,
        bait1_key: str,
        use_bait2: bool,
        bait2_key: str,
        
        update_status: Callable[[str], None],
        start_timer: Callable[[], None],
        on_catch: OnCatchProtocol,
        on_terminate: Callable[[], None]
    ):
        super(FishBotThread, self).__init__(target=self.__run, daemon=True)

        self.rod_key = rod_key

        self.use_bait1 = use_bait1
        self.bait1_key = bait1_key

        self.use_bait2 = use_bait2
        self.bait2_key = bait2_key

        self.update_status = update_status
        self.start_timer = start_timer
        self.on_catch = on_catch
        self.on_terminate = on_terminate

        self._stop_event = Event()
        self._region: tuple[int, int, int, int] | None = None

        self.start()

    def terminate(self) -> None:
        self._stop_event.set()
        self.on_terminate()

    def is_terminated(self) -> bool:
        return self._stop_event.is_set()

    def __scan_data(self,includeLootData) -> FishBotScanData:
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
                                r = dict_key_from_value(RARITY_COLORS, col)
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
            if s.getpixel((x, ly)) == WHITE_COLOR:
                self._region = (lx, linemiddle, x - lx, 1)
                break
        return self._region is not None

    def __cast_rod(self) -> None:
        pyautogui.sleep(0.3)
        autoit.mouse_down()
        pyautogui.sleep(0.3)
        autoit.mouse_up()
        pyautogui.sleep(1.5)

    def __re_cast_rod(self):
        for _ in range(2):
            pyautogui.sleep(0.5)
            autoit.send(self.rod_key)
        self.__cast_rod()

    def __move_mouse_to_catch_bar_side(self,toggler) -> None:
        autoit.mouse_move(
            x=self._region[0] if toggler else self._region[0] + self._region[2], 
            y=self._region[1],
        )
        pyautogui.sleep(0.1)

    def __use_bait(self, bait_type):
        self.update_status(f"Using tier {bait_type} bait...")
        bait_key = self.bait1_key if bait_type == 1 else self.bait2_key

        autoit.send(bait_key)
        autoit.mouse_down()
        pyautogui.sleep(1.5)
        autoit.mouse_up()
        pyautogui.sleep(0.2)
        autoit.send(self.rod_key)

    def __run(self) -> None:
        self.update_status("Waiting for first catch to appear for calibration...")
        calibration_start = datetime.now()
        while not self.__calibrate():
            if self.is_terminated(): return
            if (datetime.now() - calibration_start).total_seconds() >= CANCEL_CALIBRATION_AFTER_UNSUCCESS_SECONDS:
                self.update_status("Error: Could not calibrate because bar was not found, script stopped!")
                self.terminate()
                return
        self.start_timer()
        autoit.mouse_move(self._region[0], self._region[1])
        last_catch_trigger_time, last_bait_usage_time = datetime.now(),(datetime.now()-timedelta(minutes=2))
        cursor_afk_side = False
        while True:
            if self.is_terminated(): return
            self.update_status("Waiting for another fish...")
            data = self.__scan_data(True)
            sR, sCt = data.catch_rarity, data.catch_type
            if (data.red_line_x, data.catch_area_x) != (None, None):
                self.update_status(f"Fishing {data.catch_rarity} {data.catch_type}...")
                last_catch_trigger_time = datetime.now()
                while True:
                    if self.is_terminated(): return
                    data = self.__scan_data(False)
                    if data.red_line_x is None:
                        break
                    elif data.catch_area_x is not None and data.red_line_x < data.catch_area_x:
                        autoit.mouse_down()
                    else:
                        autoit.mouse_up()
                autoit.mouse_up()
                self.on_catch(sCt, sR)
                self.update_status("Preventick AFK-Kick...")
                if self.is_terminated(): return
                self.__move_mouse_to_catch_bar_side(cursor_afk_side := not cursor_afk_side)
                if self.is_terminated(): return
                if self.use_bait1 or self.use_bait2:
                    if (datetime.now() - last_bait_usage_time).total_seconds() >= BAIT_EFFECT_DURATION_SECONDS:
                        if self.use_bait1:
                            self.__use_bait(1)
                        if self.is_terminated(): return
                        if self.use_bait2:
                            self.__use_bait(2)
                        if self.is_terminated(): return
                        last_bait_usage_time = datetime.now()
                self.update_status("Casting fishing rod...")
                self.__cast_rod()
                if self.is_terminated(): return
                pyautogui.sleep(1)
            if (datetime.now() - last_catch_trigger_time).total_seconds() >= ATTEMPT_RECAST_AFTER_SECONDS:
                last_catch_trigger_time = datetime.now()
                self.update_status("No fish for a long time, casting fishing rod again...")
                self.__re_cast_rod()
            pyautogui.sleep(0.1)