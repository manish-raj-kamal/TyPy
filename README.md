# TyPy

TyPy is a smart, low-level auto-typing utility built in Python. It simulates real keystrokes using the native Windows API, allowing you to bypass typical copy-paste blocks. It features a modern dark/light mode UI, global hotkeys, and seamless system tray minimization.

## Features
- **Low-Level Simulation**: Directly uses Windows `SendInput` to type characters just like a real keyboard.
- **Global Hotkeys**: Control typing even when the app is minimized (`Alt+V`, `Alt+B`, `Alt+N`, `Alt+C`).
- **Human-like Typing**: Supports randomizing keystroke delays to look natural.
- **Smart Formatting**: Defeats IDE auto-indentation bugs by selectively clearing lines.
- **System Tray**: Minimizes cleanly out of your way.

## Screenshots

![TyPy UI 1](https://github.com/user-attachments/assets/e529c474-9f88-4af2-9065-a8d6d220e67e)

![TyPy UI 2](https://github.com/user-attachments/assets/a86ba888-920b-4947-b649-517ebb46ec46)

## Installation & Dependencies

To run or build the source code yourself, you will need Python 3.x installed. Then, install the required dependencies:

```bash
pip install Pillow pystray sv-ttk pyinstaller
```

## Running from Source

You can run the app directly via Python using:

```bash
python Typy.py
```

## Building the Executable (.exe)

To package the application into a single, portable Windows executable, run the following PyInstaller command. This will bundle the UI theme, system tray components, and embed your custom multi-resolution logo.

```bash
pyinstaller --clean --onefile --noconsole --collect-all sv_ttk --hidden-import pystray --hidden-import PIL --icon="assets/Typy Logo.ico" --add-data="assets/Typy Logo.png;assets" --version-file="assets/version_info.txt" Typy.py
```

Once the build finishes, you'll find your brand new `Typy.exe` ready to use inside the `dist` folder!

## Keywords & Search Tags
If you're looking for an **AutoTyper for Python**, you've found it! This repository is highly relevant for anyone searching for:
* AutoTyper for python
* Python auto typer script
* Windows human-like typing bot
* Copy paste block bypass tool
* SendInput keystroke simulator
* Auto typing utility
