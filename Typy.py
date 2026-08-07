import ctypes
import os
import sys
import random
import threading
import time
import tkinter as tk
from tkinter import ttk
import pystray
from PIL import Image, ImageDraw
import sv_ttk

def resource_path(relative_path):
    """ 
    Get absolute path to a resource. 
    This is super handy for PyInstaller. When we pack this into an .exe, 
    PyInstaller unpacks files into a temporary folder (_MEIPASS). 
    This function makes sure we can find our logo both during dev and in the final .exe!
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# We are tapping into Windows API directly here because we need super low-level control
# over keyboard and mouse inputs. It's a bit hardcore, but it's the only way to bypass 
# certain game/app protections that block normal virtual keystrokes.
if os.name == "nt":
    from ctypes import wintypes

    # Windows API constants for input types and keys
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    VK_BACK = 0x08
    VK_RETURN = 0x0D
    VK_SHIFT = 0x10
    VK_HOME = 0x24

    # These classes are basically C structs translated to Python using ctypes.
    # We have to match the exact memory layout that Windows expects!
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_size_t),
        ]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_size_t),
        ]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [
            ("uMsg", wintypes.DWORD),
            ("wParamL", wintypes.WORD),
            ("wParamH", wintypes.WORD),
        ]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [
            ("ki", KEYBDINPUT),
            ("mi", MOUSEINPUT),
            ("hi", HARDWAREINPUT),
        ]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]

    # Hooking up to the actual SendInput function from user32.dll
    _SEND_INPUT = ctypes.windll.user32.SendInput
    _SEND_INPUT.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    _SEND_INPUT.restype = wintypes.UINT


class WindowsInputController:
    """
    This guy handles all the heavy lifting of sending simulated keystrokes to Windows.
    Instead of using high-level libraries like pyautogui, we do it raw to ensure maximum compatibility.
    """
    def __init__(self):
        self.available = os.name == "nt"  # nt means Windows!

    def _send_inputs(self, inputs):
        # Fire off the inputs to the OS
        if not self.available:
            raise RuntimeError("TyPy currently supports Windows only.")
        input_array = (INPUT * len(inputs))(*inputs)
        sent = _SEND_INPUT(len(inputs), input_array, ctypes.sizeof(INPUT))
        if sent != len(inputs):
            raise OSError("SendInput failed while typing text")

    def _make_key_input(self, vk, key_up=False):
        # Create a standard virtual key event (like pressing 'A' or 'Enter')
        key_input = INPUT(type=INPUT_KEYBOARD)
        key_input.union.ki = KEYBDINPUT(
            vk,
            0,
            KEYEVENTF_KEYUP if key_up else 0,
            0,
            0,
        )
        return key_input

    def _make_unicode_input(self, code_unit, key_up=False):
        # Create a unicode input event. This is awesome because it lets us type 
        # symbols, emojis, or foreign characters that don't exist on a standard keyboard!
        key_input = INPUT(type=INPUT_KEYBOARD)
        key_input.union.ki = KEYBDINPUT(
            0,
            code_unit,
            KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if key_up else 0),
            0,
            0,
        )
        return key_input

    def type_character(self, character):
        # Convert a python string character into utf-16 bytes, then fire it off as a keystroke
        encoded_units = character.encode("utf-16-le")
        code_units = [
            int.from_bytes(encoded_units[index : index + 2], "little")
            for index in range(0, len(encoded_units), 2)
        ]
        inputs = []
        for code_unit in code_units:
            inputs.append(self._make_unicode_input(code_unit))
            inputs.append(self._make_unicode_input(code_unit, key_up=True))
        self._send_inputs(inputs)

    def press_enter(self):
        # Simulates a clean Enter press (down, then up)
        self._send_inputs(
            [self._make_key_input(VK_RETURN), self._make_key_input(VK_RETURN, key_up=True)]
        )

    def clear_line(self):
        # Useful for IDEs. Hits Shift + Home, then deletes everything on the line before typing.
        self._send_inputs([
            self._make_key_input(VK_SHIFT),
            self._make_key_input(VK_HOME),
            self._make_key_input(VK_HOME, key_up=True),
            self._make_key_input(VK_SHIFT, key_up=True)
        ])

    def send_ctrl_c(self):
        # Simulates pressing Ctrl+C. We also release the Alt key first just in case
        # the user fired the shortcut using Alt+C.
        VK_CONTROL = 0x11
        VK_C = 0x43
        VK_MENU = 0x12  # Alt key
        self._send_inputs([
            self._make_key_input(VK_MENU, key_up=True),
            self._make_key_input(VK_CONTROL),
            self._make_key_input(VK_C),
            self._make_key_input(VK_C, key_up=True),
            self._make_key_input(VK_CONTROL, key_up=True)
        ])


class TypyApp:
    """
    The main GUI class for the TyPy app! 
    This manages the Tkinter window, user settings, the system tray icon, and the typing logic.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("TyPy")
        self.root.geometry("350x350")
        self.root.resizable(True, True)
        
        # Try to load our cool custom logo. If it fails, no big deal, we just catch the exception and move on.
        try:
            icon_img = tk.PhotoImage(file=resource_path("assets/Typy Logo.png"))
            self.root.iconphoto(True, icon_img)
        except Exception:
            pass

        # State flags to keep track of what the app is doing
        self.running = False
        self.paused = False
        self.stop_requested = False
        self.thread = None
        self.listener = None
        self.input_controller = WindowsInputController()

        # Build everything!
        self.build_ui()
        self.attach_shortcuts()
        self.root.bind("<Configure>", self.on_resize)
        
        # Start in light mode by default
        sv_ttk.set_theme("light")
        self.set_titlebar_theme(False)
        self.reduce_font_size()

    def reduce_font_size(self):
        # The sv_ttk theme looks great, but its default fonts are huge. 
        # We manually step in here and force everything back down to a crisp Size 9.
        try:
            from tkinter import font as tkfont
            default_font = tkfont.nametofont("TkDefaultFont")
            default_font.configure(size=9)
            
            style = ttk.Style()
            style.configure(".", font=("Segoe UI", 9))
            style.configure("TLabel", font=("Segoe UI", 9))
            style.configure("TButton", font=("Segoe UI", 9))
            style.configure("TCheckbutton", font=("Segoe UI", 9))
            style.configure("TEntry", font=("Segoe UI", 9))
            
            self.code_box.configure(font=("Consolas", 9)) # Consolas is the standard coding font!
        except Exception:
            pass

    def on_resize(self, event):
        # Changes the "Maximize / Small window" button text dynamically based on the window size
        if event.widget == self.root:
            if event.width > 250 or event.height > 160:
                self.resize_btn.config(text="Small window", command=lambda: self.root.geometry("200x90"))
            else:
                self.resize_btn.config(text="Maximize", command=lambda: self.root.geometry("350x350"))

    def set_titlebar_theme(self, dark_mode=True):
        # This uses some obscure Windows DWM calls to actually change the window's title bar color.
        # It makes the dark mode feel fully native instead of having a blinding white title bar!
        if os.name != "nt":
            return
        try:
            self.root.update()
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            get_parent = ctypes.windll.user32.GetParent
            hwnd = get_parent(self.root.winfo_id())
            value = ctypes.c_int(1 if dark_mode else 0)
            set_window_attribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
            set_window_attribute(hwnd, 19, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            pass

    def toggle_theme(self):
        # Flips between light and dark mode, updates the text area colors, and reapplies our font size fix.
        if sv_ttk.get_theme() == "dark":
            sv_ttk.set_theme("light")
            self.set_titlebar_theme(False)
            self.theme_btn.config(text="Dark Mode")
            self.code_box.configure(bg="white", fg="black", insertbackground="black")
        else:
            sv_ttk.set_theme("dark")
            self.set_titlebar_theme(True)
            self.theme_btn.config(text="Light Mode")
            self.code_box.configure(bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        self.reduce_font_size()

    def build_ui(self):
        # This function literally builds all the buttons, text boxes, and checkboxes you see on screen.
        self.status_var = tk.StringVar(value="Ready")
        self.delay_var = tk.DoubleVar(value=0.03)
        self.start_delay_var = tk.DoubleVar(value=3.0)

        main = ttk.Frame(self.root, padding=5)
        main.pack(fill=tk.BOTH, expand=True)

        header_frame = ttk.Frame(main)
        header_frame.pack(fill=tk.X, anchor=tk.W)
        ttk.Label(header_frame, text="Text:").pack(side=tk.LEFT)
        self.resize_btn = ttk.Button(header_frame, text="Maximize", command=lambda: self.root.geometry("350x350"))
        self.resize_btn.pack(side=tk.RIGHT)
        
        self.theme_btn = ttk.Button(header_frame, text="Dark Mode", command=self.toggle_theme)
        self.theme_btn.pack(side=tk.RIGHT, padx=4)
        
        self.code_box = tk.Text(main, height=6, wrap=tk.WORD)
        self.code_box.pack(fill=tk.BOTH, expand=True, pady=(4, 8))
        self.code_box.insert(tk.END, "def greet():\n    print('Hello')")

        settings = ttk.Frame(main)
        settings.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(settings, text="Key delay (s):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(settings, textvariable=self.delay_var, width=8, font=("Segoe UI", 9)).grid(row=0, column=1, padx=(4, 14), sticky=tk.W)

        ttk.Label(settings, text="Start delay (s):").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(settings, textvariable=self.start_delay_var, width=8, font=("Segoe UI", 9)).grid(row=0, column=3, padx=(4, 0), sticky=tk.W)

        self.random_delay_var = tk.BooleanVar(value=False)
        self.min_delay_var = tk.IntVar(value=10)
        self.max_delay_var = tk.IntVar(value=50)

        ttk.Checkbutton(settings, text="Random delay:", variable=self.random_delay_var).grid(row=1, column=0, sticky=tk.W, pady=(4, 0))
        
        delay_range_frame = ttk.Frame(settings)
        delay_range_frame.grid(row=1, column=1, columnspan=3, sticky=tk.W, pady=(4, 0))
        
        ttk.Label(delay_range_frame, text="Min (ms):").pack(side=tk.LEFT)
        ttk.Entry(delay_range_frame, textvariable=self.min_delay_var, width=5, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(2, 8))
        ttk.Label(delay_range_frame, text="Max (ms):").pack(side=tk.LEFT)
        ttk.Entry(delay_range_frame, textvariable=self.max_delay_var, width=5, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(2, 0))

        controls = ttk.Frame(main)
        controls.pack(fill=tk.X)

        ttk.Button(controls, text="Start", command=self.start_typing).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls, text="Pause/Resume", command=self.toggle_pause).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls, text="End", command=self.stop_typing).pack(side=tk.LEFT, padx=2)

        ttk.Label(main, textvariable=self.status_var, foreground="blue").pack(anchor=tk.W, pady=(8, 0))
        ttk.Label(main, text="Shortcuts: Alt+V Start, Alt+B Pause/Resume, Alt+N End, Alt+C Copy", foreground="gray").pack(anchor=tk.W)
        ttk.Label(main, text="Start typing, go to the target before the countdown ends.", foreground="gray").pack(anchor=tk.W)

        self.minimize_on_close_var = tk.BooleanVar(value=True) # Checked by default!
        ttk.Checkbutton(main, text="Minimize to tray on close", variable=self.minimize_on_close_var).pack(anchor=tk.W, pady=(4, 0))

    def attach_shortcuts(self):
        # We start the hotkey listener in a background thread so it doesn't freeze the main UI.
        self.hotkey_thread = threading.Thread(target=self.hotkey_listener, daemon=True)
        self.hotkey_thread.start()

    def hotkey_listener(self):
        """
        This is our global hotkey interceptor! It hooks directly into Windows.
        This allows shortcuts like Alt+V to work EVEN IF the app is minimized and you are 
        in a different window. Pretty neat, right?
        """
        user32 = ctypes.windll.user32
        MOD_ALT = 0x0001
        VK_V = 0x56
        VK_B = 0x42
        VK_N = 0x4E
        VK_C = 0x43

        user32.RegisterHotKey(None, 1, MOD_ALT, VK_V)
        user32.RegisterHotKey(None, 2, MOD_ALT, VK_B)
        user32.RegisterHotKey(None, 3, MOD_ALT, VK_N)
        user32.RegisterHotKey(None, 4, MOD_ALT, VK_C)

        if hasattr(ctypes.wintypes, 'MSG'):
            MSG = ctypes.wintypes.MSG
        else:
            class MSG(ctypes.Structure):
                _fields_ = [
                    ("hwnd", ctypes.wintypes.HWND),
                    ("message", ctypes.wintypes.UINT),
                    ("wParam", ctypes.wintypes.WPARAM),
                    ("lParam", ctypes.wintypes.LPARAM),
                    ("time", ctypes.wintypes.DWORD),
                    ("pt", ctypes.wintypes.POINT),
                ]

        msg = MSG()
        # Message loop listening for hotkeys indefinitely...
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312: # WM_HOTKEY
                if msg.wParam == 1:
                    self.root.after(0, self.start_typing)
                elif msg.wParam == 2:
                    self.root.after(0, self.toggle_pause)
                elif msg.wParam == 3:
                    self.root.after(0, self.stop_typing)
                elif msg.wParam == 4:
                    self.root.after(0, self.copy_to_app)
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def format_code(self, text):
        return format_code(text)

    def _get_delay(self):
        # If random delay is checked, grab a random time between min and max. 
        # This makes the typing look a LOT more human-like to anti-cheat systems.
        if hasattr(self, 'random_delay_var') and self.random_delay_var.get():
            try:
                min_d = int(self.min_delay_var.get())
                max_d = int(self.max_delay_var.get())
                if min_d > max_d:
                    min_d, max_d = max_d, min_d
                return random.randint(min_d, max_d) / 1000.0
            except (tk.TclError, ValueError):
                return 0.05
        # Otherwise, just use the static delay
        try:
            delay = float(self.delay_var.get())
        except (tk.TclError, ValueError):
            return 0.05
        return max(0.0, delay)

    def _get_start_delay(self):
        try:
            delay = float(self.start_delay_var.get())
        except (tk.TclError, ValueError):
            return 0.0
        return max(0.0, delay)

    def _set_status(self, message):
        # A thread-safe way to update the status text at the bottom of the app.
        if not self.root.winfo_exists():
            return
        try:
            self.root.after(0, self.status_var.set, message)
        except tk.TclError:
            pass

    def _sleep_with_stop(self, duration):
        """
        A smart sleep function. Instead of completely freezing the thread for X seconds,
        we sleep in tiny increments and constantly check if the user hit 'End' or 'Pause'.
        This makes the app highly responsive to shortcuts while typing!
        """
        end_time = time.monotonic() + duration
        while time.monotonic() < end_time:
            if self.stop_requested:
                return False
            while self.paused and not self.stop_requested:
                time.sleep(0.1)
            if self.stop_requested:
                return False
            time.sleep(min(0.05, end_time - time.monotonic()))
        return not self.stop_requested

    def _countdown(self, seconds):
        # The countdown before typing actually starts
        remaining = seconds
        while remaining > 0:
            if self.stop_requested:
                return False
            self._set_status(f"Focus the target window in {remaining:.0f} seconds...")
            step = min(1.0, remaining)
            if not self._sleep_with_stop(step):
                return False
            remaining -= step
        return True

    def type_text(self, text):
        """
        The core engine of TyPy! This runs in a background thread and fires off all the keystrokes.
        """
        controller = self.input_controller
        error_message = None
        try:
            # Step 1: Wait for the user to focus their target window
            if not self._countdown(self._get_start_delay()):
                return

            self._set_status("Typing...")
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if self.stop_requested:
                    break
                
                # Check if paused before starting a new line
                while self.paused and not self.stop_requested:
                    time.sleep(0.1)
                if self.stop_requested:
                    break

                # If this isn't the first line, we run the clear_line function.
                # This fixes indentation issues in smart IDEs (like VSCode) that try to auto-indent for you.
                if i > 0:
                    controller.clear_line()
                    if not self._sleep_with_stop(self._get_delay()):
                        break

                # Now type out every character one by one...
                for ch in line:
                    if self.stop_requested:
                        break
                    while self.paused and not self.stop_requested:
                        time.sleep(0.1)
                    controller.type_character(ch)
                    if not self._sleep_with_stop(self._get_delay()):
                        break

                if self.stop_requested:
                    break

                # Hit Enter at the end of the line!
                controller.press_enter()
                if not self._sleep_with_stop(self._get_delay()):
                    break
        except Exception as exc:
            error_message = str(exc)
            self.stop_requested = True
            self._set_status(f"Typing failed: {exc}")
        finally:
            if error_message is None:
                self._set_status("Stopped" if self.stop_requested else "Finished")
            self.running = False
            self.paused = False

    def copy_to_app(self, *args):
        # Fired when the user hits Alt+C. Simulates a Ctrl+C, then pulls the copied 
        # text from the clipboard straight into the app's text area!
        if not self.input_controller.available:
            return
            
        self.status_var.set("Copying text...")
        self.input_controller.send_ctrl_c()
        
        def read_clip():
            try:
                clip_text = self.root.clipboard_get()
                if clip_text:
                    self.code_box.delete("1.0", tk.END)
                    self.code_box.insert(tk.END, clip_text)
                    self.status_var.set("Text copied to TyPy!")
                else:
                    self.status_var.set("Clipboard is empty.")
            except Exception as e:
                self.status_var.set(f"Failed to read clipboard: {e}")
                
        # We wait 200ms before reading the clipboard to give Windows time to actually copy the text
        self.root.after(200, read_clip)

    def start_typing(self, *args):
        # Triggered by hitting "Start" or Alt+V
        if self.thread is not None and self.thread.is_alive():
            self.status_var.set("Typing is already in progress")
            return

        if not self.input_controller.available:
            self.status_var.set("TyPy currently supports Windows only")
            return

        code = self.code_box.get("1.0", tk.END).strip("\n")
        if not code.strip():
            self.status_var.set("Enter some code first")
            return

        # Prep the state flags for action
        self.running = True
        self.paused = False
        self.stop_requested = False
        self.status_var.set("Starting countdown...")

        formatted_code = self.format_code(code)
        
        # Spin up the background thread so the UI doesn't freeze while typing!
        self.thread = threading.Thread(target=self.type_text, args=(formatted_code,), daemon=True)
        self.thread.start()

    def toggle_pause(self, *args):
        if not self.running:
            self.status_var.set("Start typing first")
            return

        self.paused = not self.paused
        self.status_var.set("Paused" if self.paused else "Resumed")

    def stop_typing(self, *args):
        # Flipped when the user hits 'End' or Alt+N. The background thread checks this flag constantly.
        if self.thread is None or not self.thread.is_alive():
            self.status_var.set("Nothing is running")
            return

        self.stop_requested = True
        self.paused = False
        self.running = False
        self.status_var.set("Stopping...")

    def create_image(self):
        # Grabs our custom app logo for the system tray! 
        # If it can't find it, it draws a blue box with yellow text instead.
        try:
            image = Image.open(resource_path("assets/Typy Logo.png"))
        except Exception:
            image = Image.new('RGB', (64, 64), color=(73, 109, 137))
            d = ImageDraw.Draw(image)
            d.text((15, 25), "TyPy", fill=(255, 255, 0))
        return image

    def hide_window_thread(self):
        # Sets up the Pystray icon and menu. This has to run in its own thread!
        image = self.create_image()
        menu = pystray.Menu(
            pystray.MenuItem("Restore", self.show_window),
            pystray.MenuItem("Quit", self.quit_app)
        )
        self.icon = pystray.Icon("TyPy", image, "TyPy", menu)
        self.icon.run()

    def hide_window(self):
        # Hide the main Tkinter window from the taskbar and start the tray icon
        self.root.withdraw()
        threading.Thread(target=self.hide_window_thread, daemon=True).start()

    def show_window(self, icon, item):
        # Stop the tray icon and pop the main window back up!
        icon.stop()
        self.root.after(0, self.root.deiconify)

    def quit_app(self, icon, item):
        icon.stop()
        self.root.after(0, self.on_close_force)

    def on_close(self):
        # When the user hits the 'X' button, do we minimize or actually close?
        if hasattr(self, 'minimize_on_close_var') and self.minimize_on_close_var.get():
            self.hide_window()
            return
        self.on_close_force()

    def on_close_force(self):
        # Shut everything down properly
        self.stop_typing()
        if self.listener is not None:
            try:
                self.listener.stop()
            except Exception:
                pass
        self.root.destroy()


def format_code(text):
    # We used to do fancy auto-indentation here, but now we just pass the text back as-is 
    # to perfectly respect the user's exact spacing! We just make sure there's a newline at the end.
    return text.rstrip() + "\n"


def main():
    # The absolute entry point of the app! Let's get things rolling.
    root = tk.Tk()
    app = TypyApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
