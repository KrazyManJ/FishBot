from array import array

import pyautogui
from idlelib.tooltip import Hovertip
from multiprocessing import Process, Manager
from tkinter import Tk, Label, LabelFrame, Entry, Button, StringVar
from datetime import datetime
from pynput.keyboard import Controller as Keyboard

LINE_COLOR: tuple[int, int, int] = (255, 105, 105)
FISH_COLOR: tuple[int, int, int] = (255, 255, 255)
CATCH_TYPES = ["fish", "treasure"]

Region: tuple[int, int, int, int] | None = None

# RARITY_COLORS = {
#     "common": (109, 127, 144),
#     "uncommon": (52, 148, 89),
#     "rare": (53, 91, 137),
#     "mythic": (162, 95, 170),
#     "legendary": (129, 150, 65),
# }
RARITY_COLORS = {
    "common": (120, 120, 120),
    "uncommon": (52, 148, 89),
    "rare": (53, 91, 137),
    "mythic": (158, 52, 235),
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
    line, catch, catchtype, rarity = None, None, None, None
    pic = pyautogui.screenshot(region=Region)
    for x in range(0, pic.width):
        color = pic.getpixel((x, 0))
        if line is None and color == LINE_COLOR:
            line = x
        elif catch is None and color == FISH_COLOR:
            catch = x
            catchtype = "treasure" if pic.getpixel((x + 4, 0)) != FISH_COLOR else "fish"
            rarity = getRarityName(pic.getpixel((x - 5, 0)))
        if catch is not None and line is not None:
            break
    return LineData(line, catch, catchtype, rarity)


def castRod() -> None:
    pyautogui.sleep(0.3)
    pyautogui.mouseDown()
    pyautogui.sleep(0.3)
    pyautogui.mouseUp()
    pyautogui.sleep(1.5)


def castRodAgain(rodhotkey) -> None:
    for [] in range(2):
        pyautogui.sleep(0.5)
        Keyboard().tap(rodhotkey)
    castRod()


def preventKickAFK(toggler) -> None:
    pyautogui.moveTo(x=Region[0] if toggler else Region[0] + Region[2], y=Region[1], duration=1,
                     tween=pyautogui.easeOutQuad)
    pyautogui.sleep(0.1)


def main(processdata) -> None:
    def updateStatus(value):
        processdata["status"] = value

    global Region
    updateStatus("Waiting for first catch to appear for calibration...")
    timeStarted = datetime.now()
    while not calibrate():
        if (datetime.now() - timeStarted).total_seconds() >= 30:
            updateStatus("Error: Could not calibrate because bar was not found, script stopped!")
            return
    pyautogui.moveTo(Region[0], Region[1])
    lastTriggerTime = datetime.now()
    while True:
        updateStatus("Waiting for another fish...")
        data = locateFishAndLinePoints()
        rarity,catchtype = data.rarity,data.catchtype
        if (data.line, data.catch) != (None, None):
            updateStatus(f"Fishing {data.rarity} {data.catchtype}...")
            lastTriggerTime = datetime.now()
            while True:
                data = locateFishAndLinePoints()
                if data.line is None:
                    break
                elif data.catch is not None and data.line < data.catch:
                    pyautogui.mouseDown()
                else:
                    pyautogui.mouseUp()
            pyautogui.mouseUp()
            processdata["catchamount"] += 1
            processdata[f"{rarity}_{catchtype}"] += 1
            updateStatus("Preventick AFK-Kick...")
            preventKickAFK(processdata["catchamount"] % 2 == 0)
            updateStatus("Casting fishing rod...")
            castRod()
        if (datetime.now() - lastTriggerTime).total_seconds() >= 30:
            lastTriggerTime = datetime.now()
            updateStatus("No fish for a long time, casting fishing rod again...")
            castRodAgain(processdata["rod_key"])
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


if __name__ == '__main__':

    win = Tk()
    win.title("FishBot")
    win.geometry(f"425x{pyautogui.size().height - 75}+{pyautogui.size().width - 425}+0")
    win.iconbitmap("icon.ico")
    win.minsize(400, 400)

    thM: None | Process = None
    manager = Manager()
    MPData = manager.dict()
    MPData["status"] = ""
    MPData["timeelapsed"] = "00:00:00"
    MPData["catchamount"] = 0
    MPData["catches"] = {}
    for catchtype in CATCH_TYPES:
        for rarity in RARITY_COLORS.keys():
            MPData[f"{rarity}_{catchtype}"] = 0

    timeStarted: None | datetime = None

    OutputValues = {}


    def updateValues():
        for key in OutputValues.keys():
            if OutputValues.get(key) is not None:
                OutputValues[key]["text"] = MPData[key]
        if timeStarted is not None:
            s = (datetime.now() - timeStarted).seconds
            timeElapsed["text"] = '{:02}h {:02}m {:02}s'.format(s // 3600, s % 3600 // 60, s % 60)


    def toggleButton(state: bool) -> None:
        startBtn["text"] = "Start" if state else "Stop"
        startBtn["bg"] = "#00ff00" if state else "#ff0000"
        for child in settingsFrame.winfo_children():
            child["state"] = "normal" if state else "disabled"


    def startBTNClick():
        global thM, timeStarted
        if thM is None or not thM.is_alive():
            MPData["rod_key"] = rodKeyValue.get()
            MPData["catchamount"] = 0
            thM = Process(target=main, args=(MPData,), daemon=True)
            thM.start()
            toggleButton(False)
            timeStarted = datetime.now()
        else:
            thM.terminate()
            thM = None
            toggleButton(True)
            MPData["status"] = "Script stopped!"
            timeStarted = None


    def checkLen(*args):
        value = rodKeyValue.get()
        if len(value) > 1:
            rodKeyValue.set(value[:1])


    Label(win, text="FishBot", font=("Segoe UI", 50)).pack()
    Label(win, text="Made by Kr4zyM4nJ", font=("Segoe UI", 10)).pack(pady=(0, 10))

    settingsFrame = LabelFrame(win, text="Settings (Hover for description)", labelanchor="n")
    for i in range(2):
        settingsFrame.grid_columnconfigure(i, weight=1)
    settingsFrame.pack(fill="x", padx=10, pady=(0, 10), ipady=5)

    rodKeyLabel = Label(settingsFrame, text="Fishing rod slot: ")
    rodKeyLabel.grid(row=0, column=0)
    rodKeyValue = StringVar(value="ě")
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
    statusText = Label(statusFrame, text=MPData["status"], font=("Segoe UI", 10))
    statusText.pack()
    OutputValues["status"] = statusText

    statisticsFrame = LabelFrame(win, text="Statistics", labelanchor="n")
    statisticsFrame.pack(fill="x", padx=10, ipady=5)
    for i in range(4):
        statisticsFrame.grid_columnconfigure(i, weight=1)

    timeElapsedLabel = Label(statisticsFrame, text="Time Elapsed:")
    timeElapsedLabel.grid(row=0, column=0)
    timeElapsed = Label(statisticsFrame, text="00h 00m 00s")
    timeElapsed.grid(row=0, column=1)

    catchAmountLabel = Label(statisticsFrame, text="Catch amount:")
    catchAmountLabel.grid(row=0, column=2)
    catchAmount = Label(statisticsFrame, text="0")
    catchAmount.grid(row=0, column=3)
    OutputValues["catchamount"] = catchAmount

    for caType in CATCH_TYPES:
        tempLF = LabelFrame(statisticsFrame, text=caType.title())
        tempLF.grid(columnspan=4,sticky="NESW",padx=10, ipady=5)
        for i in range(2):
            tempLF.grid_columnconfigure(i, weight=1)
        for i in range(0,RARITY_COLORS.keys().__len__()):
            caRar = list(RARITY_COLORS.keys()).__getitem__(i)
            Label(tempLF, text=caRar.title()).grid(row=i,column=0)
            tempLB = Label(tempLF,text=0)
            tempLB.grid(row=i,column=1)
            OutputValues[f"{caRar}_{caType}"] = tempLB

    while 1:
        updateValues()
        if thM is None or not thM.is_alive():
            if startBtn["text"] == "Stop":
                toggleButton(True)
        win.update()
