import sys
import os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def dict_key_from_value(dict: dict, val):
    return (list(dict.keys())[list(dict.values()).index(val)])