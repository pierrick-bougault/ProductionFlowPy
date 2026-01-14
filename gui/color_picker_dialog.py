"""Sélecteur de couleur utilisant l'API Windows native via ctypes
Color picker using native Windows API via ctypes"""
import tkinter as tk
import ctypes
from ctypes import wintypes

# Structure CHOOSECOLOR pour l'API Windows
class CHOOSECOLOR(ctypes.Structure):
    _fields_ = [
        ("lStructSize", wintypes.DWORD),
        ("hwndOwner", wintypes.HWND),
        ("hInstance", wintypes.HWND),
        ("rgbResult", wintypes.COLORREF),
        ("lpCustColors", ctypes.POINTER(wintypes.COLORREF)),
        ("Flags", wintypes.DWORD),
        ("lCustData", wintypes.LPARAM),
        ("lpfnHook", wintypes.LPARAM),
        ("lpTemplateName", wintypes.LPCWSTR),
    ]

# Flags
CC_RGBINIT = 0x00000001
CC_FULLOPEN = 0x00000002
CC_ANYCOLOR = 0x00000100

def askcolor(initialcolor="#FF0000", parent=None, title="Choisir une couleur"):
    """Ouvre le sélecteur de couleur Windows natif via ctypes
    Opens the native Windows color picker via ctypes
    
    Returns: tuple ((r, g, b), '#rrggbb') or (None, None) if cancelled
    """
    # Convertir la couleur initiale hex en RGB puis en COLORREF (BGR)
    if initialcolor.startswith('#'):
        initialcolor = initialcolor[1:]
    r = int(initialcolor[0:2], 16)
    g = int(initialcolor[2:4], 16)
    b = int(initialcolor[4:6], 16)
    
    # COLORREF est en format BGR
    colorref = r | (g << 8) | (b << 16)
    
    # Tableau de couleurs personnalisées (16 couleurs)
    custom_colors = (wintypes.COLORREF * 16)()
    
    # Obtenir le handle de la fenêtre parent
    hwnd = 0
    if parent is not None:
        try:
            hwnd = int(parent.winfo_id())
        except:
            hwnd = 0
    
    # Configurer la structure
    cc = CHOOSECOLOR()
    cc.lStructSize = ctypes.sizeof(CHOOSECOLOR)
    cc.hwndOwner = hwnd
    cc.rgbResult = colorref
    cc.lpCustColors = custom_colors
    cc.Flags = CC_RGBINIT | CC_FULLOPEN | CC_ANYCOLOR
    
    # Appeler l'API Windows
    comdlg32 = ctypes.windll.comdlg32
    if comdlg32.ChooseColorW(ctypes.byref(cc)):
        # Extraire RGB depuis COLORREF (BGR)
        result_colorref = cc.rgbResult
        r = result_colorref & 0xFF
        g = (result_colorref >> 8) & 0xFF
        b = (result_colorref >> 16) & 0xFF
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        return ((r, g, b), hex_color)
    else:
        return (None, None)
