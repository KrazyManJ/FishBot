import os
import sys
import pyautogui
from idlelib.tooltip import Hovertip
from threading import Thread, Event
from tkinter import Tk, Label, LabelFrame, Entry, Button, Variable
from datetime import datetime
from pynput.keyboard import Controller as Keyboard

LINE_COLOR: tuple[int, int, int] = (255, 105, 105)
FISH_COLOR: tuple[int, int, int] = (255, 255, 255)

Region: tuple[int, int, int, int] | None = None

RARITY_COLORS = {
    "common": (109, 127, 144),
    "uncommon": (52, 148, 89),
    "rare": (53, 91, 137),
    "mythic": (162, 95, 170),
    "legendary": (129, 150, 65),
}


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
        self._time_started = datetime.now()
        self.start()

    def terminate(self) -> None:
        self._stop_event.set()

    def isTerminated(self) -> bool:
        return self._stop_event.is_set()

    @staticmethod
    def __scanData() -> FishBotScanData:
        line, c, ct, r = None, None, None, None
        pic = pyautogui.screenshot(region=Region)
        for x in range(0, pic.width):
            color = pic.getpixel((x, 0))
            if line is None and color == LINE_COLOR:
                line = x
            elif c is None and color == FISH_COLOR:
                c = x
                ct = "treasure" if pic.getpixel((x + 4, 0)) != FISH_COLOR else "fish"
                r = FishBotThread.__getRarityName(pic.getpixel((x - 5, 0)))
            if c is not None and line is not None:
                break
        return FishBotScanData(line, c, ct, r)

    @staticmethod
    def __calibrate() -> bool:
        global Region
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
                Region = (lx, linemiddle, x - lx, 1)
                break
        return Region is not None

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
    def __castRodAgain(rodhotkey) -> None:
        for index in range(2):
            pyautogui.sleep(0.5)
            Keyboard().tap(rodhotkey)
        FishBotThread.__castRod()

    @staticmethod
    def __preventAFKKick(toggler) -> None:
        pyautogui.moveTo(x=Region[0] if toggler else Region[0] + Region[2], y=Region[1], duration=1,
                         tween=pyautogui.easeOutQuad)
        pyautogui.sleep(0.1)

    def __run(self) -> None:
        def updateStatus(value):
            if not self.isTerminated(): GUI.Vars["status"].set(value)

        def updateTime():
            if self.is_alive():
                s = (datetime.now() - self._time_started).seconds
                GUI.Vars["time_elapsed"].set('{:02}h {:02}m {:02}s'.format(s // 3600, s % 3600 // 60, s % 60))
                GUI.win.after(1000, updateTime)

        global Region
        updateStatus("Waiting for first catch to appear for calibration...")
        calibrationStart = datetime.now()
        while not self.__calibrate():
            if self.isTerminated(): return
            if (datetime.now() - calibrationStart).total_seconds() >= 30:
                updateStatus("Error: Could not calibrate because bar was not found, script stopped!")
                GUI.toggleButton(True)
                return
        updateTime()
        pyautogui.moveTo(Region[0], Region[1])
        lastTriggerTime = datetime.now()
        while True:
            if self.isTerminated(): return
            updateStatus("Waiting for another fish...")
            data = self.__scanData()
            sR, sCt = data.rarity, data.catchtype
            if (data.line, data.catch) != (None, None):
                updateStatus(f"Fishing {data.rarity} {data.catchtype}...")
                lastTriggerTime = datetime.now()
                while True:
                    if self.isTerminated(): return
                    data = self.__scanData()
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
                self.__preventAFKKick(GUI.Vars["total_catch_amount"].get() % 2 == 0)
                updateStatus("Casting fishing rod...")
                self.__castRod()
            if (datetime.now() - lastTriggerTime).total_seconds() >= 30:
                lastTriggerTime = datetime.now()
                updateStatus("No fish for a long time, casting fishing rod again...")
                self.__castRodAgain(GUI.Vars["settings_rod_key"].get())
            pyautogui.sleep(0.1)


class GUI:

    Vars: dict[str, Variable] = {}
    thread: None | FishBotThread = None
    win = Tk()
    Elems: dict[str, Button|LabelFrame] = {}
    optionBefore = "+"

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
        for i in range(2): settingsFrame.grid_columnconfigure(i, weight=1)
        settingsFrame.pack(fill="x", padx=10, pady=(0, 10), ipady=5)
        GUI.Elems["settings_frame"] = settingsFrame

        rodKeyLabel = Label(settingsFrame, text="Fishing rod slot: ")
        rodKeyLabel.grid(row=0, column=0)
        rodKeyValue = GUI.__regVar("settings_rod_key", "+")
        rodKeyValue.trace('w', GUI.__checkLen)
        rodKey = Entry(settingsFrame, width=10, justify="center", textvariable=rodKeyValue)
        rodKey.grid(row=0, column=1)
        rodKeyTip = Hovertip(rodKeyLabel, """
            When fish didn't appear for while (usually it is because of lag and
        character somehow didn't cast a fishing rod), character will automatically
        try to re-switch tool.
                """.strip())

        startBtn = Button(win, text="Start", font=("Segoe UI", 20), bg="#00ff00", command=GUI.__btnClick)
        startBtn.pack(fill="x", padx=10, pady=(0, 5))
        GUI.Elems["start_button"] = startBtn

        statusFrame = LabelFrame(win, text="Status", labelanchor="n")
        statusFrame.pack(fill="x", padx=10, ipady=5)
        Label(statusFrame, textvariable=GUI.__regVar("status", ""), font=("Segoe UI", 10)).pack()

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
                Label(tempLF, text=caRar.title()).grid(row=i, column=0)
                Label(tempLF, textvariable=GUI.__regVar(f"{caRar}_{caType}", 0)).grid(row=i, column=1)
        win.protocol("WM_DELETE_WINDOW", lambda: win.destroy())
        win.mainloop()

    @staticmethod
    def toggleButton(state: bool) -> None:
        GUI.Elems["start_button"].__setitem__("text","Start" if state else "Stop")
        GUI.Elems["start_button"].__setitem__("bg","#00ff00" if state else "#ff0000")
        for child in GUI.Elems["settings_frame"].winfo_children():
            child["state"] = "normal" if state else "disabled"

    @staticmethod
    def __btnClick():
        if GUI.thread is None or not GUI.thread.is_alive():
            GUI.Vars["total_catch_amount"].set(0)
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
    def __checkLen(*args):
        value = GUI.Vars["settings_rod_key"].get()
        if len(value) > 1:
            GUI.Vars["settings_rod_key"].set(value[1])
            GUI.optionBefore = value[1]
        else:
            GUI.Vars["settings_rod_key"].set(GUI.optionBefore)

    @staticmethod
    def __regVar(name, defaultval):
        val = Variable(master=GUI.win, value=defaultval)
        GUI.Vars[name] = val
        return val


if __name__ == '__main__':
    GUI.drawAndOpen()
