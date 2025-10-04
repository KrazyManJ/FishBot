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

        self.calibration_start = datetime.now()
        self.last_catch_trigger_time = datetime.now()
        self.last_bait_usage_time = datetime.now() - timedelta(minutes=2)

        self.start()

    def terminate(self) -> None:
        self._stop_event.set()
        self.on_terminate()

    def is_terminated(self) -> bool:
        return self._stop_event.is_set()
    
    def cancel_if_terminated(fct):
        def wrapper(self, *args, **kwargs):
            if self.is_terminated(): return
            return fct(self, *args, **kwargs)
        return wrapper

    def __scan_data(self,include_catch_data) -> FishBotScanData:
        data = FishBotScanData()
        pic = pyautogui.screenshot(region=self._region)
        for x in range(0, pic.width):
            color = pic.getpixel((x, 0))
            if data.red_line_x is None and color == LINE_COLOR:
                data.red_line_x = x
            elif data.catch_area_x is None and color == FISH_COLOR:
                data.catch_area_x = x
                if include_catch_data:
                    data.catch_type = "treasure" if pic.getpixel((x + 4, 0)) != FISH_COLOR else "fish"
                    if data.red_line_x is not None:
                        for bc in range(x,data.red_line_x,-1):
                            col = pic.getpixel((bc,0))
                            if col in RARITY_COLORS.values():
                                data.catch_rarity = dict_key_from_value(RARITY_COLORS, col)
            if data.catch_area_x is not None and data.red_line_x is not None:
                break
        return data

    def __is_calibrated(self) -> bool:
        return self._region is not None

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
        return self.__is_calibrated()
    

    @cancel_if_terminated
    def __sleep(self, seconds: float):
        pyautogui.sleep(seconds)


    @cancel_if_terminated
    def __cast_rod(self) -> None:
        self.update_status("Casting fishing rod...")
        self.__sleep(0.3)
        autoit.mouse_down()
        self.__sleep(0.3)
        autoit.mouse_up()
        self.__sleep(1.5)


    @cancel_if_terminated
    def __re_cast_rod(self):
        for _ in range(2):
            self.__sleep(0.5)
            autoit.send(self.rod_key)
        self.__cast_rod()


    @cancel_if_terminated
    def __prevent_afk_kick_with_mouse_mov(self, toggler: bool) -> None:
        self.update_status("Preventick AFK-Kick...")
        autoit.mouse_move(
            x=self._region[0] if toggler else self._region[0] + self._region[2], 
            y=self._region[1],
        )
        self.__sleep(0.1)


    @cancel_if_terminated
    def __use_bait(self, bait_type):
        self.update_status(f"Using tier {bait_type} bait...")
        bait_key = self.bait1_key if bait_type == 1 else self.bait2_key

        autoit.send(bait_key)
        autoit.mouse_down()
        self.__sleep(1.5)
        autoit.mouse_up()

        if self.is_terminated(): return
        self.__sleep(0.2)
        autoit.send(self.rod_key)


    @cancel_if_terminated
    def __calibrate_until_success(self):
        self.update_status("Waiting for first catch to appear for calibration...")
        self.calibration_start = datetime.now()
        while not self.__is_calibrated():
            self.__calibrate()
            if self.is_terminated(): return
            if (datetime.now() - self.calibration_start).total_seconds() >= CANCEL_CALIBRATION_AFTER_UNSUCCESS_SECONDS:
                self.update_status("Error: Could not calibrate because bar was not found, script stopped!")
                self.terminate()
                return


    @cancel_if_terminated
    def __move_to_catch_bar(self):
        autoit.mouse_move(self._region[0], self._region[1])


    @cancel_if_terminated
    def __attempt_use_baits(self):
        if self.use_bait1 or self.use_bait2:
            if (datetime.now() - self.last_bait_usage_time).total_seconds() >= BAIT_EFFECT_DURATION_SECONDS:
                if self.use_bait1:
                    self.__use_bait(1)
                if self.use_bait2:
                    self.__use_bait(2)
                self.last_bait_usage_time = datetime.now()


    @cancel_if_terminated
    def __wait_until_catch_bar_else_re_cast(self) -> FishBotScanData:
        data = FishBotScanData()

        while not data.is_catch_bar_visible():
            if self.is_terminated(): return
            data = self.__scan_data(include_catch_data=True)

            if (datetime.now() - self.last_catch_trigger_time).total_seconds() >= ATTEMPT_RECAST_AFTER_SECONDS:
                self.last_catch_trigger_time = datetime.now()
                self.update_status("No fish for a long time, casting fishing rod again...")
                self.__re_cast_rod()

            if not data.is_catch_bar_visible():
                self.update_status("Waiting for another fish...")

            self.__sleep(0.1)

        return data
    

    @cancel_if_terminated
    def __catch(self, data: FishBotScanData):
        catch_rarity, catch_type = data.catch_rarity, data.catch_type
            
        self.update_status(f"Fishing {data.catch_rarity} {data.catch_type}...")
        self.last_catch_trigger_time = datetime.now()

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
        self.on_catch(catch_type, catch_rarity)


    def __run(self) -> None:
        self.__calibrate_until_success()
        if not self.__is_calibrated():
            return
        
        self.start_timer()
        self.__move_to_catch_bar()

        cursor_afk_side = False
        while not self.is_terminated():
            data = self.__wait_until_catch_bar_else_re_cast()

            if data is None:
                return
            
            self.__catch(data)

            self.__prevent_afk_kick_with_mouse_mov(cursor_afk_side := not cursor_afk_side)
            
            self.__attempt_use_baits()
            
            self.__cast_rod()

            self.__sleep(1)