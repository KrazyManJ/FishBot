from datetime import datetime
import pyautogui
import time
from pynput.keyboard import Controller

OPTIONS = {
    "fishing_rod_hotkey": "+",
}

LINE_COLOR = (255, 105, 105)
FISH_COLOR = (255, 255, 255)

Region = None
Count = 0
kboard = Controller()


def locateFishAndLinePoints():
    line, catch = None, None
    pic = pyautogui.screenshot(region=Region)
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
    pyautogui.sleep(0.3)
    pyautogui.mouseDown()
    pyautogui.sleep(0.3)
    pyautogui.mouseUp()
    pyautogui.sleep(1.5)


def rethrowBait():
    pyautogui.sleep(0.5)
    kboard.tap(OPTIONS["fishing_rod_hotkey"])
    pyautogui.sleep(0.5)
    kboard.tap(OPTIONS["fishing_rod_hotkey"])
    throwBait()


def preventKickAFK():
    global Count
    pyautogui.move(100 if Count % 2 == 0 else -100, 0, 1, pyautogui.easeOutQuad)
    pyautogui.sleep(0.1)


def log(value) -> None:
    print(f"({time.strftime('%H:%M:%S')}) {value}")


def main():
    global Count, Region
    calibrate()
    if Region is None:
        log("COULD NOT CALIBRATE, BAR WAS NOT FOUND!")
        return
    log("SUCCESSFULLY CALIBRATED!")
    lastTriggerTime = datetime.now()
    log("SCRIPT INITIALIZED, WAITING FOR FIRST CATCH TO APPEAR!")
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
        pyautogui.sleep(0.1)


def calibrate():
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
        return
    for y in range(ly, s.height):
        if s.getpixel((lx, y)) != LINE_COLOR:
            linemiddle = ly + (y-ly) // 2.7
            break
    for x in range(lx, s.width):
        if s.getpixel((x, ly)) == (255, 255, 255):
            Region = (lx, linemiddle, x - lx, 1)
            break


if __name__ == '__main__':
    main()
    # debugPhoto()
