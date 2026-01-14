"""
SimPy GUI - Interface graphique pour modéliser et visualiser des flux de production
SimPy GUI - Graphical interface to model and visualize production flows
"""
import tkinter as tk
from tkinter import ttk
from gui.main_window import MainWindow, load_user_config
from gui.translations import tr, set_language

def main():
    # Charger la langue sauvegardée avant de créer la fenêtre
    # Load saved language before creating window
    user_config = load_user_config()
    if 'language' in user_config:
        set_language(user_config['language'])
    
    root = tk.Tk()
    root.title(tr('app_title'))
    # Charger l'icône de l'application / Load application icon
    try:
        import os
        # Chemin relatif au fichier main.py / Path relative to main.py
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_dir, "logo", "ProductionFlowPy.png")
        icon_image = tk.PhotoImage(file=icon_path)
        root.iconphoto(True, icon_image)
    except Exception as e:
        print(f"Impossible de charger l'icône / Unable to load icon: {e}")
    # Démarrer en plein écran / Start in full screen
    root.state('zoomed')  # Windows: maximiser la fenêtre / maximize window
    # Alternative pour d'autres OS / Alternative for other OS: root.attributes('-zoomed', True)
    
    app = MainWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()

