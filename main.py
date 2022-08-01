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


class LineData:
    def __init__(self, line: int | None, catch: int | None, catchtype: str | None, rarity: str | None):
        self.line = line
        self.catch = catch
        self.catchtype = catchtype
        self.rarity = rarity


def getRarityName(color) -> str:
    def a(cl1, cl2) -> int:
        return sum([abs(c1 - c2) for c1, c2 in zip(cl1, cl2)])

    differences = [
        [a(color, known_color), known_name]
        for known_name, known_color in RARITY_COLORS.items()
    ]
    differences.sort()
    return differences[0][1]


def locateFishAndLinePoints() -> LineData:
    line, c, ct, r = None, None, None, None
    pic = pyautogui.screenshot(region=Region)
    for x in range(0, pic.width):
        color = pic.getpixel((x, 0))
        if line is None and color == LINE_COLOR:
            line = x
        elif c is None and color == FISH_COLOR:
            c = x
            ct = "treasure" if pic.getpixel((x + 4, 0)) != FISH_COLOR else "fish"
            r = getRarityName(pic.getpixel((x - 5, 0)))
        if c is not None and line is not None:
            break
    return LineData(line, c, ct, r)


def castRod() -> None:
    pyautogui.sleep(0.3)
    pyautogui.mouseDown()
    pyautogui.sleep(0.3)
    pyautogui.mouseUp()
    pyautogui.sleep(1.5)


def castRodAgain(rodhotkey) -> None:
    for index in range(2):
        pyautogui.sleep(0.5)
        Keyboard().tap(rodhotkey)
    castRod()


def preventKickAFK(toggler) -> None:
    pyautogui.moveTo(x=Region[0] if toggler else Region[0] + Region[2], y=Region[1], duration=1,
                     tween=pyautogui.easeOutQuad)
    pyautogui.sleep(0.1)


def calibrate() -> bool:
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


class BackendThread(Thread):

    def __init__(self):
        super(BackendThread, self).__init__(daemon=True)
        self._stop_event = Event()
        self._time_started = datetime.now()
        print(OutputValues.keys())

    def terminate(self): self._stop_event.set()

    def isTerminated(self): return self._stop_event.is_set()

    def run(self) -> None:
        def updateStatus(value):
            if not self.isTerminated(): OutputValues["status"].set(value)

        def updateTime():
            if thM is not None and thM.is_alive():
                s = (datetime.now() - self._time_started).seconds
                OutputValues["time_elapsed"].set('{:02}h {:02}m {:02}s'.format(s // 3600, s % 3600 // 60, s % 60))
                win.after(1000, updateTime)

        global Region
        updateStatus("Waiting for first catch to appear for calibration...")
        calibrationStart = datetime.now()
        while not calibrate():
            if self.isTerminated(): return
            if (datetime.now() - calibrationStart).total_seconds() >= 30:
                updateStatus("Error: Could not calibrate because bar was not found, script stopped!")
                toggleButton(True)
                return
        updateTime()
        pyautogui.moveTo(Region[0], Region[1])
        lastTriggerTime = datetime.now()
        while True:
            if self.isTerminated(): return
            updateStatus("Waiting for another fish...")
            data = locateFishAndLinePoints()
            sR, sCt = data.rarity, data.catchtype
            if (data.line, data.catch) != (None, None):
                updateStatus(f"Fishing {data.rarity} {data.catchtype}...")
                lastTriggerTime = datetime.now()
                while True:
                    if self.isTerminated(): return
                    data = locateFishAndLinePoints()
                    if data.line is None:
                        break
                    elif data.catch is not None and data.line < data.catch:
                        pyautogui.mouseDown()
                    else:
                        pyautogui.mouseUp()
                pyautogui.mouseUp()
                OutputValues["total_catch_amount"].set(OutputValues["total_catch_amount"].get() + 1)
                OutputValues[f"{sR}_{sCt}"].set(OutputValues[f"{sR}_{sCt}"].get() + 1)
                updateStatus("Preventick AFK-Kick...")
                preventKickAFK(OutputValues["total_catch_amount"].get() % 2 == 0)
                updateStatus("Casting fishing rod...")
                castRod()
            if (datetime.now() - lastTriggerTime).total_seconds() >= 30:
                lastTriggerTime = datetime.now()
                updateStatus("No fish for a long time, casting fishing rod again...")
                castRodAgain(OutputValues["settings_rod_key"].get())
            pyautogui.sleep(0.1)


if __name__ == '__main__':

    win = Tk()
    win.title("FishBot")
    win.geometry(f"425x{pyautogui.size().height - 75}+{pyautogui.size().width - 425}+0")
    win.iconbitmap("icon.ico")
    win.minsize(400, 640)

    thM: None | BackendThread = None
    OutputValues: dict[str, Variable] = {}


    def regVar(name, defaultval):
        val = Variable(master=win, value=defaultval)
        OutputValues[name] = val
        return val


    def toggleButton(state: bool) -> None:
        startBtn["text"] = "Start" if state else "Stop"
        startBtn["bg"] = "#00ff00" if state else "#ff0000"
        for child in settingsFrame.winfo_children():
            child["state"] = "normal" if state else "disabled"


    def startBTNClick():
        global thM
        if thM is None or not thM.is_alive():
            OutputValues["total_catch_amount"].set(0)
            thM = BackendThread()
            thM.start()
            toggleButton(False)
        else:
            thM.terminate()
            toggleButton(True)
            OutputValues["status"].set("Script stopped!")


    def checkLen(*args):
        value = rodKeyValue.get()
        if len(value) > 1:
            rodKeyValue.set(value[:1])


    Label(win, text="FishBot", font=("Segoe UI", 50)).pack()
    Label(win, text="Made by Kr4zyM4nJ", font=("Segoe UI", 10)).pack(pady=(0, 10))

    settingsFrame = LabelFrame(win, text="Settings (Hover for description)", labelanchor="n")
    for i in range(2): settingsFrame.grid_columnconfigure(i, weight=1)
    settingsFrame.pack(fill="x", padx=10, pady=(0, 10), ipady=5)

    rodKeyLabel = Label(settingsFrame, text="Fishing rod slot: ")
    rodKeyLabel.grid(row=0, column=0)
    rodKeyValue = regVar("settings_rod_key", "+")
    rodKeyValue.trace('w', checkLen)
    rodKey = Entry(settingsFrame, width=10, justify="center", textvariable=rodKeyValue)
    rodKey.grid(row=0, column=1)
    rodKeyTip = Hovertip(rodKeyLabel, """
    When fish didn't appear for while (usually it is because of lag and
character somehow didn't cast a fishing rod), character will automatically
try to re-switch tool.
        """.strip())

    startBtn = Button(win, text="Start", font=("Segoe UI", 20), bg="#00ff00", command=startBTNClick)
    startBtn.pack(fill="x", padx=10, pady=(0, 5))

    statusFrame = LabelFrame(win, text="Status", labelanchor="n")
    statusFrame.pack(fill="x", padx=10, ipady=5)
    statusText = Label(statusFrame, textvariable=regVar("status", ""), font=("Segoe UI", 10))
    statusText.pack()

    statisticsFrame = LabelFrame(win, text="Statistics", labelanchor="n")
    statisticsFrame.pack(fill="x", padx=10, ipady=5)
    for i in range(4): statisticsFrame.grid_columnconfigure(i, weight=1)

    Label(statisticsFrame, text="Time Elapsed:").grid(row=0, column=0)
    timeElapsed = Label(statisticsFrame, textvariable=regVar("time_elapsed", "00h 00m 00s"))
    timeElapsed.grid(row=0, column=1)

    Label(statisticsFrame, text="Catch amount:").grid(row=0, column=2)
    catchAmount = Label(statisticsFrame, textvariable=regVar("total_catch_amount", 0))
    catchAmount.grid(row=0, column=3)

    for caType in ["fish", "treasure"]:
        tempLF = LabelFrame(statisticsFrame, text=caType.title())
        tempLF.grid(columnspan=4, sticky="NESW", padx=10, ipady=5)
        for i in range(2): tempLF.grid_columnconfigure(i, weight=1)
        for i in range(0, RARITY_COLORS.keys().__len__()):
            caRar = list(RARITY_COLORS.keys()).__getitem__(i)
            Label(tempLF, text=caRar.title()).grid(row=i, column=0)
            tempLB = Label(tempLF, textvariable=regVar(f"{caRar}_{caType}", 0))
            tempLB.grid(row=i, column=1)

    win.protocol("WM_DELETE_WINDOW", lambda: win.destroy())
    win.mainloop()
