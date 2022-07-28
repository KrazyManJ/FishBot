from datetime import datetime
import pyautogui
from pynput.keyboard import Controller as Keyboard

# TODO: Detection of rarity and type of catch
# TODO: Display of statistics, runtime and loot count (rarity + type)
# TODO: settings in external json file
# TODO: Make it look pretty in console

OPTIONS: dict[str, str] = {
    "fishing_rod_hotkey": "+",
}

LINE_COLOR: tuple[int, int, int] = (255, 105, 105)
FISH_COLOR: tuple[int, int, int] = (255, 255, 255)

Region: tuple[int, int, int, int] | None = None
Count: int = 0
kboard: Keyboard = Keyboard()

RARITY_COLORS = {
    "legendary": (129, 150, 65),
    "mythic": (162, 95, 170),
    "rare": (53, 91, 137),
    "uncommon": (52, 148, 89),
    "common": (109, 127, 144)
}


def getRarityName(color) -> str:
    def color_difference(color1, color2) -> int:
        return sum([abs(component1-component2) for component1, component2 in zip(color1, color2)])
    differences = [
        [color_difference(color, known_color), known_name]
        for known_name, known_color in RARITY_COLORS.items()
    ]
    differences.sort()
    return differences[0][1]


def locateFishAndLinePoints():
    line, catch, catchtype, rarity = None, None, None, None
    pic = pyautogui.screenshot(region=Region)
    for x in range(0, pic.width):
        color = pic.getpixel((x, 0))
        if line is None and color == LINE_COLOR:
            line = x
        elif catch is None and color == FISH_COLOR:
            catch = x
            catchtype = "treasure" if pic.getpixel((x + 4, 0)) != FISH_COLOR else "fish"
            rarity = getRarityName(pic.getpixel((x-5,0)))
        if catch is not None and line is not None:
            break
    return line, catch, catchtype, rarity


def throwBait() -> None:
    pyautogui.sleep(0.3)
    pyautogui.mouseDown()
    pyautogui.sleep(0.3)
    pyautogui.mouseUp()
    pyautogui.sleep(1.5)


def rethrowBait() -> None:
    pyautogui.sleep(0.5)
    kboard.tap(OPTIONS["fishing_rod_hotkey"])
    pyautogui.sleep(0.5)
    kboard.tap(OPTIONS["fishing_rod_hotkey"])
    throwBait()


def preventKickAFK() -> None:
    global Count
    pyautogui.move(100 if Count % 2 == 0 else -100, 0, 1, pyautogui.easeOutQuad)
    pyautogui.sleep(0.1)


def log(value) -> None:
    print(f"({datetime.now().strftime('%H:%M:%S')}) {value}")


def ansiRGB(rgb) -> str:
    return f"\033[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m"


ANSI_RESET = "\033[0m"


def main() -> None:
    global Count, Region
    calibrate()
    if Region is None:
        log("COULD NOT CALIBRATE, BAR WAS NOT FOUND!")
        return
    log("SUCCESSFULLY CALIBRATED!")
    lastTriggerTime = datetime.now()
    log("SCRIPT INITIALIZED, WAITING FOR FIRST CATCH TO APPEAR!")
    while True:
        line, catch, catchtype, rarity = locateFishAndLinePoints()
        if (line, catch) != (None, None):
            log(f"STARTED FISHING {ansiRGB(RARITY_COLORS[rarity])}{rarity}{ANSI_RESET} {catchtype}!")
            lastTriggerTime = datetime.now()
            while True:
                line, catch, catchtype, rarity = locateFishAndLinePoints()
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


def calibrate() -> None:
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
            linemiddle = ly + (y - ly) // 2.7
            break
    for x in range(lx, s.width):
        if s.getpixel((x, ly)) == (255, 255, 255):
            Region = (lx, linemiddle, x - lx, 1)
            break


if __name__ == '__main__':
    main()
