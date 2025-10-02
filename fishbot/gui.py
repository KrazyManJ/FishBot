from tkinter import *
from .thread import FishBotThread
from .utils import resource_path
from tkextrafont import Font
import os
from idlelib.tooltip import Hovertip
from .constants import *
from pynput.keyboard import Key, Listener

class GUI:

    Vars: dict[str, Variable] = {}
    thread: None | FishBotThread = None
    win = Tk()
    Elems: dict[str, Button|LabelFrame|Entry] = {}

    @staticmethod
    def drawAndOpen():
        win = GUI.win
        win.configure(background="#FEFEFD")
        win.title("FishBot")
        win.geometry("400x730")
        #win.geometry(f"425x{pyautogui.size().height - 75}+{pyautogui.size().width - 425}+0")
        win.iconbitmap(resource_path("icon.ico"))
        win.minsize(400, 730)

        titleFont = "Hiruko Pro"
        textFont = "Magdelin Text"
        for font in [titleFont, textFont]:
            Font(file=resource_path(os.path.join("fonts",f"{font}.otf")), family = font)

        Label(win,text="FishBot",bg="#FEFEFD",font=(titleFont, 50)).pack()
        Label(win,text="Made by Kr4zyM4nJ",bg="#FEFEFD",font=(textFont, 15)).pack(pady=(0, 10))

        settingsFrame = LabelFrame(win,
                                   text="Settings (Hover for description)",
                                   font=(titleFont,15),
                                   labelanchor="n",
                                   background="#EFE6D3",
                                   borderwidth=0
                                   )
        for i in range(3): settingsFrame.grid_columnconfigure(i, weight=1)
        settingsFrame.pack(fill="x", padx=10, pady=(0, 10), ipady=10)
        GUI.Elems["settings_frame"] = settingsFrame

        rodKeyLabel = Label(settingsFrame,
                            text="Fishing rod slot keybind: ",
                            font=(textFont, 13),
                            bg="#EFE6D3"
                            )
        rodKeyLabel.grid(row=0, column=0, columnspan=2)
        Entry(settingsFrame,
              width=5,
              justify="center",
              textvariable=GUI.__regVar("settings_rod_key", "1", GUI.__charBinding),
              background="#C8BAA3",
              font=(textFont, 13),
              borderwidth=0
              ).grid(row=0, column=2)
        Hovertip(rodKeyLabel, """
When fish didn't appear for while (usually it is because of lag and
character somehow didn't cast a fishing rod), character will automatically
try to re-switch tool.
                """.strip())



        for data in [("1","2",2),("2","3",3)]:
            lab = Label(settingsFrame,
                        text=f"Tier {data[0]} bait:",
                        font=(textFont, 13),
                        bg="#EFE6D3"
                        )
            lab.grid(row=data[2], column=0)
            Checkbutton(settingsFrame,
                        variable=GUI.__regVar(f"settings_use_bait{data[0]}", False, GUI.__baitCheckBox),
                        bg="#EFE6D3",
                        selectcolor="#C8BAA3",
                        activebackground="#EFE6D3",

                        ).grid(
                row=data[2], column=1)
            GUI.Elems[f"settings_bait{data[0]}_key"] = Entry(settingsFrame,
                                                             width=5,
                                                             justify="center",
                                                             state="disabled",
                                                             textvariable=GUI.__regVar(f"settings_bait{data[0]}_key", data[1], GUI.__charBinding),
                                                             background="#C8BAA3",
                                                             disabledbackground="#C8BAA3",
                                                             font=(textFont, 13),
                                                             borderwidth=0,

                                                             )
            GUI.Elems[f"settings_bait{data[0]}_key"].grid(row=data[2], column=2)
            Hovertip(lab,f"""
If enabled, character will always try to use Tier {data[0]} bait before casting fishing rod in
interval of 2 minutes (this is how long Tier {data[0]} bait lasts).
            """.strip())



        GUI.Elems["start_button"] = Button(win,
                                           font=(titleFont, 25),
                                           fg="white",
                                           command=GUI.__btnClick,
                                           borderwidth=0,
                                           )
        GUI.Elems["start_button"].pack(fill="x", padx=10, pady=(0, 10))
        GUI.toggleButton(True)

        statusFrame = LabelFrame(win,
                                 background="#EFE6D3",
                                 text="Status",
                                 labelanchor="n",
                                 borderwidth=0,
                                 font=(titleFont, 15),
                                 )
        statusFrame.pack(fill="x", padx=10, ipady=5, pady=(0, 10))
        Label(statusFrame,
              background="#EFE6D3",
              textvariable=GUI.__regVar("status", "Ready to use! Hit \"Start\" to begin!"),
              font=(textFont, 12),
              ).pack()

        statsFrame = LabelFrame(win,
                                background="#F5F5F4",
                                text="Statistics",
                                labelanchor="n",
                                font=(titleFont, 15),
                                borderwidth=0
                                )
        statsFrame.pack(fill="x", padx=10, ipady=5)
        for i in range(4): statsFrame.grid_columnconfigure(i, weight=1)

        Label(statsFrame, background="#F5F5F4", font=(textFont, 11), text="Time Elapsed:").grid(row=0, column=0)
        Label(statsFrame, background="#F5F5F4", font=(textFont, 11), textvariable=GUI.__regVar("time_elapsed", "00h 00m 00s")).grid(row=0, column=1)
        Label(statsFrame, background="#F5F5F4", font=(textFont, 11), text="Catch amount:").grid(row=0, column=2)
        Label(statsFrame, background="#F5F5F4", font=(textFont, 11), textvariable=GUI.__regVar("total_catch_amount", 0)).grid(row=0, column=3)

        for caType in ["fish", "treasure"]:
            tempLF = LabelFrame(statsFrame, text=caType.title(),background="#EFE6D3",labelanchor="n",borderwidth=0,font=(titleFont, 13))
            tempLF.grid(columnspan=4, sticky="NESW", padx=10, ipady=5, pady=(10,0))
            for i in range(2): tempLF.grid_columnconfigure(i, weight=1)
            for i in range(0, RARITY_COLORS.keys().__len__()):
                caRar = list(RARITY_COLORS.keys()).__getitem__(i)
                if f"{caRar}_{caType}" not in LOOT_TYPE_BLACKLIST:
                    Label(tempLF, text=caRar.title(),background="#EFE6D3",font=(textFont, 11)).grid(row=i, column=0)
                    Label(tempLF, textvariable=GUI.__regVar(f"{caRar}_{caType}", 0),background="#EFE6D3",font=(textFont, 11)).grid(row=i, column=1)
        win.protocol("WM_DELETE_WINDOW", lambda: win.destroy())
        Listener(on_press=GUI.__keyboardHandle).start()
        win.mainloop()

    @staticmethod
    def toggleButton(state: bool) -> None:
        GUI.Elems["start_button"].__setitem__("text","Start" if state else "Stop (End)")
        GUI.Elems["start_button"].__setitem__("bg","#0BB41C" if state else "#DC3545")
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
    def __charBinding(var, *args):
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