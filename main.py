from datetime import datetime
import pyautogui
import time
from pynput.keyboard import Controller

OPTIONS = {
    "fishing_rod_hotkey": "+",
}

# REGION = (494, 860, 532, 1)
REGION = (520, 848, 556, 1)
LINE_COLOR = (255, 105, 105)
FISH_COLOR = (255, 255, 255)

Count = 0
kboard = Controller()


def locateFishAndLinePoints():
    line, catch = None, None
    pic = pyautogui.screenshot(region=REGION)
    for x in range(0, pic.width):
        color = pic.getpixel((x, 0))
        if line is None and color == LINE_COLOR:
            line = x
        elif catch is None and color == FISH_COLOR:
            catch = x
        if catch is not None and line is not None:
            break
    return line, catch


def throwBait():
    time.sleep(0.3)
    pyautogui.mouseDown()
    time.sleep(0.3)
    pyautogui.mouseUp()
    time.sleep(1.5)


def rethrowBait():
    time.sleep(0.5)
    kboard.tap(OPTIONS["fishing_rod_hotkey"])
    time.sleep(0.5)
    kboard.tap(OPTIONS["fishing_rod_hotkey"])
    throwBait()


def preventKickAFK():
    global Count
    pyautogui.move(100 if Count % 2 == 0 else -100, 0, 1, pyautogui.easeOutQuad)
    time.sleep(0.1)


def log(value) -> None:
    print(f"({time.strftime('%H:%M:%S')}) {value}")


def main():
    global Count
    lastTriggerTime = datetime.now()
    log("INITIALIZED SCRIPT, WAITING FOR FIRST CATCH TO APPEAR!")
    while True:
        line, catch = locateFishAndLinePoints()
        if (line, catch) != (None, None):
            log(f"STARTED FISHING!")
            lastTriggerTime = datetime.now()
            while True:
                line, catch = locateFishAndLinePoints()
                if line is None:
                    break
                elif catch is not None and line < catch:
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
        time.sleep(0.1)


if __name__ == '__main__':
    main()
    # debugPhoto()
