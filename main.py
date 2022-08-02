import os
import sys
import pyautogui
from idlelib.tooltip import Hovertip
from threading import Thread, Event
from tkinter import Tk, Label, LabelFrame, Entry, Button, Variable, Checkbutton
from datetime import datetime, timedelta
from pynput.keyboard import Controller as Keyboard, Listener, Key

LINE_COLOR: tuple[int, int, int] = (255, 105, 105)
FISH_COLOR: tuple[int, int, int] = (255, 255, 255)

RARITY_COLORS = {
    "common": (113, 116, 121),
    "uncommon": (33, 131, 36),
    "rare": (39, 89, 142),
    "mythic": (138, 55, 131),
    "legendary": (139, 144, 27),
}

LOOT_TYPE_BLACKLIST = ["legendary_fish","common_treasure","mythic_treasure"]

class FishBotScanData:
    def __init__(self, line: int | None, catch: int | None, catchtype: str | None, rarity: str | None):
        self.line = line
        self.catch = catch
        self.catchtype = catchtype
        self.rarity = rarity


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
                linemiddle = ly + (y - ly) // 2.7
                break
        for x in range(lx, s.width):
            if s.getpixel((x, ly)) == (255, 255, 255):
                self._region = (lx, linemiddle, x - lx, 1)
                break
        return self._region is not None

    @staticmethod
    def __getRarityName(color) -> str:
        def a(cl1, cl2) -> int:
            return sum([abs(c1 - c2) for c1, c2 in zip(cl1, cl2)])

        differences = [
            [a(color, known_color), known_name]
            for known_name, known_color in RARITY_COLORS.items()
        ]
        differences.sort()
        return differences[0][1]

    @staticmethod
    def __castRod() -> None:
        pyautogui.sleep(0.3)
        pyautogui.mouseDown()
        pyautogui.sleep(0.3)
        pyautogui.mouseUp()
        pyautogui.sleep(1.5)

    @staticmethod
    def __castRodAgain() -> None:
        for index in range(2):
            pyautogui.sleep(0.5)
            Keyboard().tap(GUI.Vars["settings_rod_key"].get())
        FishBotThread.__castRod()

    def __preventAFKKick(self,toggler) -> None:
        pyautogui.moveTo(x=self._region[0] if toggler else self._region[0] + self._region[2], y=self._region[1], duration=1,
                         tween=pyautogui.easeOutQuad)
        pyautogui.sleep(0.1)

    @staticmethod
    def __useBait(baitType):
        kboard = Keyboard()
        kboard.tap(GUI.Vars[f"settings_bait{baitType}_key"].get())
        pyautogui.mouseDown()
        pyautogui.sleep(1)
        pyautogui.mouseUp()
        pyautogui.sleep(0.2)
        kboard.tap(GUI.Vars["settings_rod_key"].get())

    def __run(self) -> None:
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
        pyautogui.moveTo(self._region[0], self._region[1])
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
                        pyautogui.mouseDown()
                    else:
                        pyautogui.mouseUp()
                pyautogui.mouseUp()
                GUI.Vars["total_catch_amount"].set(GUI.Vars["total_catch_amount"].get() + 1)
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


class GUI:

    Vars: dict[str, Variable] = {}
    thread: None | FishBotThread = None
    win = Tk()
    Elems: dict[str, Button|LabelFrame|Entry] = {}

    @staticmethod
    def drawAndOpen():
        win = GUI.win
        win.title("FishBot")
        win.geometry(f"425x{pyautogui.size().height - 75}+{pyautogui.size().width - 425}+0")
        win.iconbitmap(GUI.__resourcePath("icon.ico"))
        win.minsize(400, 640)

        Label(win, text="FishBot", font=("Segoe UI", 50)).pack()
        Label(win, text="Made by Kr4zyM4nJ", font=("Segoe UI", 10)).pack(pady=(0, 10))

        settingsFrame = LabelFrame(win, text="Settings (Hover for description)", labelanchor="n")
        for i in range(3): settingsFrame.grid_columnconfigure(i, weight=1)
        settingsFrame.pack(fill="x", padx=10, pady=(0, 10), ipady=5)
        GUI.Elems["settings_frame"] = settingsFrame

        rodKeyLabel = Label(settingsFrame, text="Fishing rod slot keybind: ")
        rodKeyLabel.grid(row=0, column=0, columnspan=2)
        Entry(settingsFrame, width=10, justify="center", textvariable=GUI.__regVar("settings_rod_key", "1", GUI.__charBinding)).grid(row=0, column=2)
        Hovertip(rodKeyLabel, """
When fish didn't appear for while (usually it is because of lag and
character somehow didn't cast a fishing rod), character will automatically
try to re-switch tool.
                """.strip())



        for data in [("1","2",2),("2","3",3)]:
            lab = Label(settingsFrame, text=f"Tier {data[0]} bait:")
            lab.grid(row=data[2], column=0)
            Checkbutton(settingsFrame, variable=GUI.__regVar(f"settings_use_bait{data[0]}", False, GUI.__baitCheckBox)).grid(
                row=data[2], column=1)
            GUI.Elems[f"settings_bait{data[0]}_key"] = Entry(settingsFrame, width=10, justify="center", state="disabled",
                                                    textvariable=GUI.__regVar(f"settings_bait{data[0]}_key", data[1], GUI.__charBinding))
            GUI.Elems[f"settings_bait{data[0]}_key"].grid(row=data[2], column=2)
            Hovertip(lab,f"""
If enabled, character will always try to use Tier {data[0]} bait before casting fishing rod in
interval of 2 minutes (this is how long Tier {data[0]} bait lasts).
            """.strip())



        GUI.Elems["start_button"] = Button(win, text="Start", font=("Segoe UI", 20), bg="#00ff00", command=GUI.__btnClick)
        GUI.Elems["start_button"].pack(fill="x", padx=10, pady=(0, 5))

        statusFrame = LabelFrame(win, text="Status", labelanchor="n")
        statusFrame.pack(fill="x", padx=10, ipady=5)
        Label(statusFrame, textvariable=GUI.__regVar("status", "Ready to use! Hit \"Start\" to begin!"), font=("Segoe UI", 10)).pack()

        statsFrame = LabelFrame(win, text="Statistics", labelanchor="n")
        statsFrame.pack(fill="x", padx=10, ipady=5)
        for i in range(4): statsFrame.grid_columnconfigure(i, weight=1)

        Label(statsFrame, text="Time Elapsed:").grid(row=0, column=0)
        Label(statsFrame, textvariable=GUI.__regVar("time_elapsed", "00h 00m 00s")).grid(row=0, column=1)
        Label(statsFrame, text="Catch amount:").grid(row=0, column=2)
        Label(statsFrame, textvariable=GUI.__regVar("total_catch_amount", 0)).grid(row=0, column=3)

        for caType in ["fish", "treasure"]:
            tempLF = LabelFrame(statsFrame, text=caType.title())
            tempLF.grid(columnspan=4, sticky="NESW", padx=10, ipady=5)
            for i in range(2): tempLF.grid_columnconfigure(i, weight=1)
            for i in range(0, RARITY_COLORS.keys().__len__()):
                caRar = list(RARITY_COLORS.keys()).__getitem__(i)
                if f"{caRar}_{caType}" not in LOOT_TYPE_BLACKLIST:
                    Label(tempLF, text=caRar.title()).grid(row=i, column=0)
                    Label(tempLF, textvariable=GUI.__regVar(f"{caRar}_{caType}", 0)).grid(row=i, column=1)
        win.protocol("WM_DELETE_WINDOW", lambda: win.destroy())
        Listener(on_press=GUI.__keyboardHandle).start()
        win.mainloop()

    @staticmethod
    def toggleButton(state: bool) -> None:
        GUI.Elems["start_button"].__setitem__("text","Start" if state else "Stop (End)")
        GUI.Elems["start_button"].__setitem__("bg","#00ff00" if state else "#ff0000")
        for child in GUI.Elems["settings_frame"].winfo_children():
            child["state"] = "normal" if state else "disabled"
        if state:
            GUI.__baitCheckBox()

    @staticmethod
    def __keyboardHandle(key):
        if GUI.thread is not None and GUI.thread.is_alive():
            if type(key) is Key and key == key.end:
                GUI.thread.terminate()
                GUI.toggleButton(True)
                GUI.Vars["status"].set("Script stopped!")

    @staticmethod
    def __btnClick():
        if GUI.thread is None or not GUI.thread.is_alive():
            GUI.Vars["total_catch_amount"].set(0)
            for ctype in ["fish","treasure"]:
                for rar in RARITY_COLORS.keys():
                    if f"{rar}_{ctype}" not in LOOT_TYPE_BLACKLIST:
                        GUI.Vars[f"{rar}_{ctype}"].set(0)
            GUI.thread = FishBotThread()
            GUI.toggleButton(False)
        else:
            GUI.thread.terminate()
            GUI.toggleButton(True)
            GUI.Vars["status"].set("Script stopped!")

    @staticmethod
    def __resourcePath(relative_path):
        try:
            base_path = sys._MEIPASS
        except:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    @staticmethod
    def __charBinding(var, index, mode):
        value = GUI.Vars[var].get()
        if len(value) > 1:
            GUI.Vars[var].set(value[1])
            GUI.optionBefore = value[1]
        else:
            GUI.Vars[var].set(GUI.optionBefore)

    @staticmethod
    def __baitCheckBox(*args):
        for i in range(1,3):
            GUI.Elems[f"settings_bait{i}_key"]["state"] = "normal" \
                if GUI.Vars[f"settings_use_bait{i}"].get() == "1" \
                else "disabled"

    @staticmethod
    def __regVar(name, defaultval, writeCallback = None):
        val = Variable(master=GUI.win, value=defaultval, name=name)
        GUI.Vars[name] = val
        if writeCallback is not None: val.trace_add("write",writeCallback)
        return val


if __name__ == '__main__':
    GUI.drawAndOpen()
