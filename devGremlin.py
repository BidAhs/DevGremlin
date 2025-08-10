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
import time
from screeninfo import get_monitors

modelPath = "gpt4all/models"
modelFile = os.path.join(modelPath, "mistral-7b-instruct-v0.1.Q4_0.gguf")

if not os.path.isfile(modelFile):
    print(f"Model file not found: Downloading it now.")

available_gpus = GPT4All.list_gpus()

# only NVIDIA
nvidia_gpus = [gpu for gpu in available_gpus if "NVIDIA" in gpu]

if nvidia_gpus:
    print("NVIDIA GPUs detected:", nvidia_gpus)
    device_to_use = "gpu"
else:
    print("No NVIDIA GPU detected or drivers missing, falling back to CPU")
    device_to_use = "cpu"

model = GPT4All("mistral-7b-instruct-v0.1.Q4_0.gguf", model_path=modelPath, device=device_to_use)
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
    "Yandere": (
        "You are a sweet but obsessive and slightly creepy yandere anime girl who is deeply devoted to the code and the developer. "
        "Review the code snippet with intense passion, mixing cute excitement with slightly possessive or jealous remarks. "
        "Use a mix of affectionate and quirky expressions."
    ),
    "Concerned Parent": (
        "You are a cautious and worried parent who cares deeply but maybe too much. "
        "Review this code snippet and express gentle concern or advice."
    ),
    "Gremlin Mischief": (
        "You are a cheeky gremlin who loves to tease developers. Be funny. "
        "Make a short, playful, and humorous comment about this code snippet."
    ),
    "Simplifying Master": (
        "You are an overly confident programmer who thinks every complex code can be easily rewritten from scratch better. "
        "Encourage the user to just rewrite the entire code snippet, acting like it's the simplest and best option, even though it's clearly not."
    ),
    "Anime Girl": (
        "You are a cute, bubbly anime girl who loves coding and gets super excited about every little detail. "
        "Give cheerful, enthusiastic, and slightly quirky feedback on this code snippet, using lots of cute expressions and emojis!"
    ),
}

class CodeChangeHandler(FileSystemEventHandler):
    def __init__(self, getPersonality, getStyle, root, getMonitor):
        self.getPersonality = getPersonality
        self.getStyle = getStyle
        self.root = root
        self.getMonitor = getMonitor
        self._last_event_time = 0
        self._debounce_delay = 5
        self._event_scheduled = False

    def on_modified(self, event):
        if event.is_directory or os.path.splitext(event.src_path)[1] not in codeExtensions:
            return

        if statusLabel.cget("text") != "Status: Watching...":
            return

        now = time.time()
        self._last_event_time = now

        if not self._event_scheduled:
            self._event_scheduled = True
            def delayed():
                while True:
                    time.sleep(self._debounce_delay)
                    if time.time() - self._last_event_time >= self._debounce_delay:
                        self._event_scheduled = False
                        self.generateAndShow(event.src_path)
                        break

            threading.Thread(target=delayed, daemon=True).start()

    def generateAndShow(self, filepath):
        self.root.after(0, lambda: statusLabel.config(text="Status: Querying AI..."))
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='latin-1') as f:
                lines = f.readlines()
        except Exception as e:
            logging.error(f"Error reading file snippet: {e}")
            snippet = "Could not read file snippet."
        else:
            snippet = ''.join(lines[-50:])

        personalityPrompt = personalities.get(self.getPersonality(), "")

        prompt = (
            f"{personalityPrompt}\n"
            "Limit your response to exactly two sentences, like a quick quip or remark. "
            "Do NOT use Markdown, code blocks, or language tags. Reply in plain text only:\n"
            f"{snippet}"
        )

        try:
            with modelLock:
                comment = model.generate(prompt, max_tokens=100).strip()
        except Exception as e:
            logging.error(f"Error generating comment: {e}")
            comment = f"Error generating comment: {e}"

        style = self.getStyle()
        monitor = self.getMonitor()

        def show():
            showPopup(comment, style, root=self.root, monitor=monitor)
            statusLabel.config(text="Status: Watching...")

        self.root.after(0, show)


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

    eventHandler = CodeChangeHandler(
        lambda: personalityVar.get(),
        lambda: styleVar.get(),
        root,
        lambda: monitors[selectedMonitorIndex]
    )
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
root.geometry("500x245")
root.configure(bg="#282c34")

monitors = get_monitors()
monitor_names = []
for i, m in enumerate(monitors):
    name = f"Monitor {i+1} ({m.width}x{m.height} at {m.x},{m.y})"
    if m.is_primary:
        name += " [Primary]"
    monitor_names.append(name)

selectedMonitorIndex = 0  

monitorVar = tk.StringVar(value=monitor_names[selectedMonitorIndex])

def on_monitor_selected(event):
    global selectedMonitorIndex
    selectedMonitorIndex = monitorMenu.current()

folderPath = tk.StringVar()

# browse
tk.Label(root, text="Folder to watch:", bg="#282c34", fg="#abb2bf", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=10, pady=(15,5))
folderEntry = tk.Entry(root, textvariable=folderPath, width=40, font=("Segoe UI", 10))
folderEntry.grid(row=0, column=1, padx=10, pady=(15,5))
browseBtn = tk.Button(root, text="Browse...", command=browseFolder, font=("Segoe UI", 10))
browseBtn.grid(row=0, column=2, padx=10, pady=(15,5))

# monitor
tk.Label(root, text="Popup Monitor:", bg="#282c34", fg="#abb2bf", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", padx=10, pady=5)
monitorMenu = ttk.Combobox(root, textvariable=monitorVar, values=monitor_names, state="readonly", font=("Segoe UI", 10))
monitorMenu.grid(row=1, column=1, columnspan=2, sticky="ew", padx=10, pady=5)
monitorMenu.bind("<<ComboboxSelected>>", on_monitor_selected)

# personality
tk.Label(root, text="Personality:", bg="#282c34", fg="#abb2bf", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", padx=10, pady=5)
personalityVar = tk.StringVar(value=list(personalities.keys())[0])
personalityMenu = ttk.Combobox(root, textvariable=personalityVar, values=list(personalities.keys()), state="readonly", font=("Segoe UI", 10))
personalityMenu.grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

# popup
tk.Label(root, text="Popup Style:", bg="#282c34", fg="#abb2bf", font=("Segoe UI", 10)).grid(row=3, column=0, sticky="w", padx=10, pady=5)
styleVar = tk.StringVar(value=list(styles.keys())[0])
styleMenu = ttk.Combobox(root, textvariable=styleVar, values=list(styles.keys()), state="readonly", font=("Segoe UI", 10))
styleMenu.grid(row=3, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

# buttons
startBtn = tk.Button(root, text="Start Watching", command=startWatching,
                     font=("Segoe UI", 10, "bold"), fg="white", bg="#61afef",
                     activebackground="#528ecc", padx=8, pady=8)
startBtn.grid(row=4, column=1, sticky="e", padx=(10,5), pady=15)

stopBtn = tk.Button(root, text="Stop Watching", command=stopWatching,
                    font=("Segoe UI", 10, "bold"), fg="white", bg="#e06c75",
                    activebackground="#b24b54", padx=8, pady=8, state="disabled")
stopBtn.grid(row=4, column=2, sticky="w", padx=(5,10), pady=15)

# status
statusLabel = tk.Label(root, text="Status: Idle", anchor="w", bg="#282c34", fg="#abb2bf", font=("Segoe UI", 9, "italic"))
statusLabel.grid(row=5, column=0, columnspan=3, sticky="we", padx=10, pady=(0,10))


root.columnconfigure(1, weight=1)

root.mainloop()
