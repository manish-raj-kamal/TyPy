# TyPy (Portable Auto-Typer)

TyPy is a smart, low-level, **fully portable** auto-typing utility built in Python. Because it is a portable `.exe`, **no installation is required**—simply download it and run! It simulates real keystrokes using the native Windows API, allowing you to bypass typical copy-paste blocks. It features a modern dark/light mode UI, global hotkeys, and seamless system tray minimization.

## Features
- **Low-Level Simulation**: Directly uses Windows `SendInput` to type characters just like a real keyboard.
- **Global Hotkeys**: Control typing even when the app is minimized (`Alt+V`, `Alt+B`, `Alt+N`, `Alt+C`).
- **Human-like Typing**: Supports randomizing keystroke delays to look natural.
- **Smart Formatting**: Defeats IDE auto-indentation bugs by selectively clearing lines.
- **System Tray**: Minimizes cleanly out of your way.

## Screenshots

<img src="https://github.com/user-attachments/assets/e529c474-9f88-4af2-9065-a8d6d220e67e" width="60%" alt="TyPy UI 1">

<img src="https://github.com/user-attachments/assets/a86ba888-920b-4947-b649-517ebb46ec46" width="60%" alt="TyPy UI 2">

## Developer Setup & Building From Source

If you want to clone this repository, run the code yourself, or build your own `.exe`, follow these exact steps to avoid environment issues.

**1. Open your terminal inside the project folder**
Make sure your terminal is opened directly in the root `TyPy` directory (the folder containing `Typy.py`).

**2. Create a Virtual Environment**
It is highly recommended to create an isolated Python environment so your global Python installation doesn't get cluttered. Run this command:
```bash
python -m venv .venv
```

**3. Activate the Virtual Environment**
You **must** activate the environment before installing dependencies or running PyInstaller.
- On **Windows (PowerShell)**:
  ```bash
  .\.venv\Scripts\activate
  ```
- On **Windows (Command Prompt)**:
  ```bash
  .venv\Scripts\activate.bat
  ```
- On **Mac/Linux**:
  ```bash
  source .venv/bin/activate
  ```
*(You'll know it worked if you see `(.venv)` at the very beginning of your terminal prompt!)*

**4. Install Dependencies**
With the environment activated, install all required packages:
```bash
pip install Pillow pystray sv-ttk pyinstaller
```

**5. Running from Source**
If you just want to run the python script directly without building an `.exe`:
```bash
python Typy.py
```

**6. Building the Executable (.exe)**
To package the application into a single, portable Windows executable with the custom UI theme and system tray components, run the following command. 

*(Note: We explicitly use `python -m PyInstaller` instead of just `pyinstaller` to ensure it grabs the exact PyInstaller module installed safely inside your activated virtual environment!)*

```bash
python -m PyInstaller --clean --onefile --noconsole --collect-all sv_ttk --hidden-import pystray --hidden-import PIL --icon="assets/Typy Logo.ico" --add-data="assets/Typy Logo.png;assets" --version-file="assets/version_info.txt" Typy.py
```

Once the build finishes, you will find your freshly compiled `TyPy.exe` waiting inside the newly generated `dist` folder!

## Keywords & Search Tags
If you're looking for an **AutoTyper for Python**, you've found it! This repository is highly relevant for anyone searching for:
* AutoTyper for python
* Python auto typer script
* Windows human-like typing bot
* Copy paste block bypass tool
* SendInput keystroke simulator
* Auto typing utility
