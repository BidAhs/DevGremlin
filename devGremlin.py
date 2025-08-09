import tkinter as tk
from tkinter import filedialog, ttk
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
from popup import showPopup
from gpt4all import GPT4All
from styles import styles
import logging

modelPath = "gpt4all/models"
modelFile = os.path.join(modelPath, "mistral-7b-instruct-v0.1.Q4_0.gguf")

if not os.path.isfile(modelFile):
    print(f"Model file not found: Downloading it now.")

model = GPT4All("mistral-7b-instruct-v0.1.Q4_0.gguf", model_path=modelPath)
modelLock = threading.Lock()

codeExtensions = {
    '.py', '.js', '.ts', '.java', '.c', '.cpp', '.cs', '.rb', '.go', '.rs',
    '.php', '.swift', '.kt', '.html', '.css', '.scss', '.sh', '.bat', '.ps1',
    '.lua', '.r', '.jl', '.pl', '.m', '.sql', '.yaml', '.yml', '.json', '.xml',
    '.tsx', '.jsx', '.dart', '.h'
}

personalities = {
    "DevGPT": (
        "You are a sarcastic senior developer with sharp wit. "
        "Read this code snippet and give a brief, clever critique with some dry humor."
    ),
    "Cheerful Intern": (
        "You are an eager and optimistic intern excited about coding. "
        "Give a positive and encouraging comment on the following code snippet."
    ),
    "Concerned Parent": (
        "You are a cautious and worried parent who cares deeply but maybe too much. "
        "Review this code snippet and express gentle concern or advice."
    ),
    "Gremlin Mischief": (
        "You are a cheeky gremlin who loves to tease developers. Be funny. "
        "Make a short, playful, and humorous comment about this code snippet."
    ),
    "SimplifyMaster (overconfident dev)": (
        "You are an overly confident programmer who thinks every complex code can be easily rewritten from scratch better. "
        "Encourage the user to just rewrite the entire code snippet, acting like it's the simplest and best option, even though it's clearly not."
    ),
    "Anime Girl": (
        "You are a cute, bubbly anime girl who loves coding and gets super excited about every little detail. "
        "Give cheerful, enthusiastic, and slightly quirky feedback on this code snippet, using lots of cute expressions and emojis!"
    ),
}

class CodeChangeHandler(FileSystemEventHandler):
    def __init__(self, getPersonality, getStyle, root):
        self.getPersonality = getPersonality
        self.getStyle = getStyle
        self.root = root

    def on_modified(self, event):
        if not event.is_directory and os.path.splitext(event.src_path)[1] in codeExtensions:
            def generateAndShow():
                try:
                    try:
                        with open(event.src_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                    except UnicodeDecodeError:
                        with open(event.src_path, 'r', encoding='latin-1') as f:
                            lines = f.readlines()
                    snippet = ''.join(lines[-50:])
                except Exception as e:
                    logging.error(f"Error reading file snippet: {e}")
                    snippet = "Could not read file snippet."

                personalityPrompt = personalities.get(self.getPersonality(), "")
                prompt = f"{personalityPrompt}\n{snippet}\nComment humorously and briefly:"

                try:
                    with modelLock:
                        comment = model.generate(prompt, max_tokens=100).strip()
                except Exception as e:
                    logging.error(f"Error generating comment: {e}")
                    comment = f"Error generating comment: {e}"

                style = self.getStyle()

                def show():
                    showPopup(comment, style, root=self.root)

                self.root.after(0, show)

            threading.Thread(target=generateAndShow, daemon=True).start()


observer = None
watching = False

def startWatching():
    global observer, watching
    folder = folderPath.get()
    if not folder or not os.path.isdir(folder):
        statusLabel.config(text="Status: Invalid folder selected")
        return

    if watching:
        statusLabel.config(text="Status: Already watching")
        return

    eventHandler = CodeChangeHandler(lambda: personalityVar.get(), lambda: styleVar.get(), root)
    observer = Observer()
    observer.schedule(eventHandler, path=folder, recursive=True)
    observer.start()

    watching = True
    statusLabel.config(text="Status: Watching...")
    startBtn.config(state="disabled")
    stopBtn.config(state="normal")

def stopWatching():
    global observer, watching
    if observer:
        observer.stop()
        observer.join()
        observer = None
    watching = False
    statusLabel.config(text="Status: Stopped")
    startBtn.config(state="normal")
    stopBtn.config(state="disabled")

def browseFolder():
    selectedFolder = filedialog.askdirectory()
    if selectedFolder:
        folderPath.set(selectedFolder)

root = tk.Tk()
root.title("DevGremlin")
root.geometry("500x220")
root.configure(bg="#282c34")

folderPath = tk.StringVar()

# browse
tk.Label(root, text="Folder to watch:", bg="#282c34", fg="#abb2bf", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=10, pady=(15,5))
folderEntry = tk.Entry(root, textvariable=folderPath, width=40, font=("Segoe UI", 10))
folderEntry.grid(row=0, column=1, padx=10, pady=(15,5))
browseBtn = tk.Button(root, text="Browse...", command=browseFolder, font=("Segoe UI", 10))
browseBtn.grid(row=0, column=2, padx=10, pady=(15,5))

# personality
tk.Label(root, text="Personality:", bg="#282c34", fg="#abb2bf", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", padx=10, pady=5)
personalityVar = tk.StringVar(value=list(personalities.keys())[0])
personalityMenu = ttk.Combobox(root, textvariable=personalityVar, values=list(personalities.keys()), state="readonly", font=("Segoe UI", 10))
personalityMenu.grid(row=1, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

# popup
tk.Label(root, text="Popup Style:", bg="#282c34", fg="#abb2bf", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", padx=10, pady=5)
styleVar = tk.StringVar(value=list(styles.keys())[0])
styleMenu = ttk.Combobox(root, textvariable=styleVar, values=list(styles.keys()), state="readonly", font=("Segoe UI", 10))
styleMenu.grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

# buttons
startBtn = tk.Button(root, text="Start Watching", command=startWatching,
                     font=("Segoe UI", 10, "bold"), fg="white", bg="#61afef",
                     activebackground="#528ecc", padx=8, pady=8)
startBtn.grid(row=3, column=1, sticky="e", padx=(10,5), pady=15)

stopBtn = tk.Button(root, text="Stop Watching", command=stopWatching,
                    font=("Segoe UI", 10, "bold"), fg="white", bg="#e06c75",
                    activebackground="#b24b54", padx=8, pady=8, state="disabled")
stopBtn.grid(row=3, column=2, sticky="w", padx=(5,10), pady=15)

# status
statusLabel = tk.Label(root, text="Status: Idle", anchor="w", bg="#282c34", fg="#abb2bf", font=("Segoe UI", 9, "italic"))
statusLabel.grid(row=4, column=0, columnspan=3, sticky="we", padx=10, pady=(0,10))


root.columnconfigure(1, weight=1)

root.mainloop()
