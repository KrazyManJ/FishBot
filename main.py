import threading
import pyautogui
from datetime import datetime
from pynput.keyboard import Controller as Keyboard, Listener, Key

LINE_COLOR: tuple[int, int, int] = (255, 105, 105)
FISH_COLOR: tuple[int, int, int] = (255, 255, 255)

Region: tuple[int, int, int, int] | None = None
Count: int = 0
KBoard: Keyboard = Keyboard()

RARITY_COLORS = {
    "legendary": (129, 150, 65),
    "mythic": (162, 95, 170),
    "rare": (53, 91, 137),
    "uncommon": (52, 148, 89),
    "common": (109, 127, 144)
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


def throwBait() -> None:
    pyautogui.sleep(0.3)
    pyautogui.mouseDown()
    pyautogui.sleep(0.3)
    pyautogui.mouseUp()
    pyautogui.sleep(1.5)


def rethrowBait() -> None:
    for i in range(2):
        pyautogui.sleep(0.5)
        KBoard.tap("+")
    throwBait()


def preventKickAFK() -> None:
    global Count
    pyautogui.moveTo(x=Region[0] if Count % 2 == 0 else Region[0] + Region[2], y=Region[1], duration=1,
                     tween=pyautogui.easeOutQuad)
    pyautogui.sleep(0.1)


def log(value) -> None:
    print(f"({datetime.now().strftime('%H:%M:%S')}) {value}")


def main() -> None:
    global Count, Region

    log("SCRIPT INITIALIZED, WAITING FOR FIRST CATCH APPEARANCE FOR CALIBRATING!")
    timeStarted = datetime.now()
    while not calibrate():
        if (datetime.now() - timeStarted).total_seconds() >= 5:
            log("COULD NOT CALIBRATE, BAR WAS NOT FOUND!")
            return
    pyautogui.moveTo(Region[0], Region[1])
    log("SUCCESSFULLY CALIBRATED!")
    lastTriggerTime = datetime.now()
    while True:
        data = locateFishAndLinePoints()
        if (data.line, data.catch) != (None, None):
            log(f"STARTED FISHING!")
            log(f"{data.rarity} {data.catchtype}")
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
            Count += 1
            log("FINISHED FISHING!")
            preventKickAFK()
            log("AFK-KICK PREVENTED!")
            throwBait()
            log("BAIT THROWN!")
        if (datetime.now() - lastTriggerTime).total_seconds() >= 30:
            lastTriggerTime = datetime.now()
            log("RE-THROWING BAIT!")
            rethrowBait()
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
    thM = threading.Thread(target=main)
    thM.daemon = True
    thM.start()

    def on_press(key):
        if type(key) == Key:
            if key == Key.end:
                log("PROGRAM ENDED DUE TO PRESSING \"END\" KEY!")
                return False

    thL = Listener(on_press=on_press)
    thL.start()
    while thM.is_alive() and thL.is_alive():
        pyautogui.sleep(0.1)
