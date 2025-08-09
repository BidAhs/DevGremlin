import tkinter as tk

def showPopup(message, styleName="Classic Terminal", root=None):
    from styles import styles

    style = styles.get(styleName, styles["Classic Terminal"])

    if root is None:
        raise ValueError("You gotta pass the main Tk root to showPopup")

    popup = tk.Toplevel(root)
    popup.overrideredirect(True)
    popup.attributes("-topmost", True)
    popup.configure(bg=style["bg"])

    label = tk.Label(
        popup,
        text=message,
        fg=style["fg"],
        bg=style["bg"],
        font=style["font"],
        padx=style["padx"],
        pady=style["pady"],
        wraplength=style["wraplength"]
    )
    label.pack()

    def close(event=None):
        popup.destroy()

    popup.bind("<Button-1>", close)

    popup.update_idletasks()
    width = popup.winfo_width()
    height = popup.winfo_height()
    screenWidth = popup.winfo_screenwidth()
    screenHeight = popup.winfo_screenheight()
    x = screenWidth - width - 20
    y = screenHeight - height - 50
    popup.geometry(f"{width}x{height}+{x}+{y}")
