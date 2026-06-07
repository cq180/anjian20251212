import tkinter as tk


from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser


import pyautogui


from pynput import keyboard, mouse


import time


import threading


import os


import ctypes


import json


import sys


import subprocess


import configparser


import re

import shutil

import argparse





# --- 尝试导入可选库 ---


try:


    from tkinterdnd2 import DND_FILES, TkinterDnD


    RootClass = TkinterDnD.Tk


    HAS_DND = True


except ImportError:


    RootClass = tk.Tk


    HAS_DND = False





try:


    from PIL import Image, ImageTk, ImageGrab


    HAS_PIL = True


except ImportError:


    HAS_PIL = False





# --- 高分屏适配 ---


try:


    ctypes.windll.shcore.SetProcessDpiAwareness(1)


except Exception:


    try:


        ctypes.windll.user32.SetProcessDPIAware()


    except:


        pass





# --- 全局配置 ---


BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0])) 


CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


GRID_INI_FILE = os.path.join(BASE_DIR, "grid_config.ini")


PIC_DIR = os.path.join(BASE_DIR, "pic")





if not os.path.exists(PIC_DIR):


    try: os.makedirs(PIC_DIR)


    except: pass





pyautogui.FAILSAFE = True 


pyautogui.PAUSE = 0 





# --- 虚拟键码定义 ---


VK_MAP = {


    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,


    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,


    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,


    'esc': 0x1B


}





# --- [辅助函数] ---


def smart_read_file(filepath):


    encodings = ['utf-8', 'gbk', 'gb18030', 'ansi']


    for enc in encodings:


        try:


            with open(filepath, 'r', encoding=enc) as f:


                content = f.read()


                lines = content.splitlines(keepends=True)


                return content, lines


        except UnicodeDecodeError: continue


        except Exception: break


    return None, None





def check_admin():


    try: return ctypes.windll.shell32.IsUserAnAdmin()


    except: return False





# --- 截图工具类 ---


class ScreenCapture(tk.Toplevel):


    def __init__(self, parent, callback):


        super().__init__(parent)


        self.callback = callback 


        self.attributes('-fullscreen', True) 


        self.attributes('-alpha', 0.4)       


        self.attributes('-topmost', True)    


        self.configure(bg="black", cursor="cross")


        sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()


        self.geometry(f"{sw}x{sh}+0+0")


        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)


        self.canvas.pack(fill=tk.BOTH, expand=True)


        self.start_x = None; self.start_y = None; self.rect_id = None


        self.canvas.bind('<Button-1>', self.on_press)


        self.canvas.bind('<B1-Motion>', self.on_drag)


        self.canvas.bind('<ButtonRelease-1>', self.on_release)


        self.bind('<Escape>', self.on_cancel) 


        self.after(100, self.force_focus)


    def force_focus(self): self.grab_set(); self.focus_set() 


    def on_press(self, event):


        self.start_x = event.x; self.start_y = event.y


        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=3)


    def on_drag(self, event):


        if self.rect_id: self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)


    def on_release(self, event):


        if not self.start_x: return


        x1, y1 = self.start_x, self.start_y; x2, y2 = event.x, event.y


        left = min(x1, x2); top = min(y1, y2); right = max(x1, x2); bottom = max(y1, y2)


        self.withdraw(); self.grab_release(); self.update_idletasks(); time.sleep(0.2) 


        captured_path = None


        if (right - left) > 5 and (bottom - top) > 5:


            try:


                img = ImageGrab.grab(bbox=(left, top, right, bottom))


                filename = f"img_{int(time.time())}.png" 


                filepath = os.path.join(PIC_DIR, filename)


                img.save(filepath)


                captured_path = filepath


            except Exception as e: messagebox.showerror("截图失败", str(e))


        if self.callback: self.callback(captured_path)


        self.destroy()


    def on_cancel(self, event):


        if self.callback: self.callback(None) 


        self.destroy()





# --- 坐标拾取器 ---


class CoordinatePicker(tk.Toplevel):


    def __init__(self, parent, callback):


        super().__init__(parent)


        self.callback = callback


        self.attributes('-fullscreen', True)


        self.attributes('-alpha', 0.1) # 只有一点点透明度，用于捕获点击


        self.attributes('-topmost', True)


        self.configure(bg="black", cursor="cross")


        


        # 绑定事件


        self.bind('<Button-1>', self.on_click)


        self.bind('<Escape>', self.on_cancel)


        


        self.after(100, self.force_focus)


        


    def force_focus(self): 


        self.grab_set()


        self.focus_set()





    def on_click(self, event):


        self.withdraw()


        self.grab_release()


        if self.callback:


            self.callback(event.x, event.y)


        self.destroy()





    def on_cancel(self, event):


        self.grab_release()


        self.destroy()





# --- DirectInput (ScanCode) Support for Games/Emulators ---


# Define ctypes structures globally to avoid scoping errors


PULKey = ctypes.POINTER(ctypes.c_ulong)





class KeyBdInput(ctypes.Structure):


    _fields_ = [("wVk", ctypes.c_ushort),


                ("wScan", ctypes.c_ushort),


                ("dwFlags", ctypes.c_ulong),


                ("time", ctypes.c_ulong),


                ("dwExtraInfo", ctypes.c_void_p)] # ULONG_PTR





class HardwareInput(ctypes.Structure):


    _fields_ = [("uMsg", ctypes.c_ulong),


                ("wParamL", ctypes.c_ushort),


                ("wParamH", ctypes.c_ushort)]





class MouseInput(ctypes.Structure):


    _fields_ = [("dx", ctypes.c_long),


                ("dy", ctypes.c_long),


                ("mouseData", ctypes.c_ulong),


                ("dwFlags", ctypes.c_ulong),


                ("time", ctypes.c_ulong),


                ("dwExtraInfo", ctypes.c_void_p)]





class Input_I(ctypes.Union):


    _fields_ = [("ki", KeyBdInput),


                ("mi", MouseInput),


                ("hi", HardwareInput)]





class Input(ctypes.Structure):


    _fields_ = [("type", ctypes.c_ulong),


                ("ii", Input_I)]





class DirectInput:


    # DirectInput ScanCodes


    SC = {


        'escape': 0x01, '1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05, '5': 0x06, '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A, '0': 0x0B, '-': 0x0C, '=': 0x0D, 'backspace': 0x0E,


        'tab': 0x0F, 'q': 0x10, 'w': 0x11, 'e': 0x12, 'r': 0x13, 't': 0x14, 'y': 0x15, 'u': 0x16, 'i': 0x17, 'o': 0x18, 'p': 0x19, '[': 0x1A, ']': 0x1B, 'enter': 0x1C,


        'ctrl': 0x1D, 'ctrlleft': 0x1D, 'ctrlright': 0x1D, 


        'a': 0x1E, 's': 0x1F, 'd': 0x20, 'f': 0x21, 'g': 0x22, 'h': 0x23, 'j': 0x24, 'k': 0x25, 'l': 0x26, ';': 0x27, "'": 0x28, '`': 0x29,


        'shift': 0x2A, 'shiftleft': 0x2A, '\\': 0x2B,


        'z': 0x2C, 'x': 0x2D, 'c': 0x2E, 'v': 0x2F, 'b': 0x30, 'n': 0x31, 'm': 0x32, ',': 0x33, '.': 0x34, '/': 0x35, 'shiftright': 0x36,


        'kpmult': 0x37, 'alt': 0x38, 'altleft': 0x38, 'space': 0x39, 'capslock': 0x3A,


        'f1': 0x3B, 'f2': 0x3C, 'f3': 0x3D, 'f4': 0x3E, 'f5': 0x3F, 'f6': 0x40, 'f7': 0x41, 'f8': 0x42, 'f9': 0x43, 'f10': 0x44,


        'numlock': 0x45, 'scrolllock': 0x46, 'kp7': 0x47, 'kp8': 0x48, 'kp9': 0x49, 'kpsub': 0x4A, 'kp4': 0x4B, 'kp5': 0x4C, 'kp6': 0x4D, 'kpplus': 0x4E, 'kp1': 0x4F, 'kp2': 0x50, 'kp3': 0x51, 'kp0': 0x52, 'kpdot': 0x53,


        'f11': 0x57, 'f12': 0x58,


        'up': 0xC8, 'left': 0xCB, 'right': 0xCD, 'down': 0xD0, 'delete': 0xD3, 'altright': 0xB8, 'win': 0xDB


    }





    @staticmethod


    def _send_key(scancode, press):


        extra = ctypes.c_void_p(0)


        ii_ = Input_I()


        flags = 0x0008 # KEYEVENTF_SCANCODE


        if not press: flags |= 0x0002 # KEYEVENTF_KEYUP


        if scancode > 0x7F: flags |= 0x0001 # KEYEVENTF_EXTENDEDKEY


        


        ii_.ki = KeyBdInput(0, scancode, flags, 0, extra)


        x = Input(ctypes.c_ulong(1), ii_)


        ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))





    @staticmethod


    def press(key_name):


        sc = DirectInput.SC.get(key_name.lower())


        if sc: DirectInput._send_key(sc, True)





    @staticmethod


    def release(key_name):


        sc = DirectInput.SC.get(key_name.lower())


        if sc: DirectInput._send_key(sc, False)


    


    @staticmethod


    def click_key(key_name):


        DirectInput.press(key_name)


        time.sleep(0.05)


        DirectInput.release(key_name)





# --- 按钮配置弹窗 ---


# --- 按钮配置弹窗 ---


class ButtonConfigWindow(tk.Toplevel):


    def __init__(self, parent, initial_data, geometry, on_save_callback, on_close_callback):


        super().__init__(parent)


        self.title("编辑按钮配置")


        try: self.geometry(geometry)


        except: self.geometry("500x400")


        


        # --- 子窗口也可以设置一下图标 (可选) ---


        try:


            icon_path = os.path.join(BASE_DIR, "anjian20251216.ico")


            if os.path.exists(icon_path):


                self.iconbitmap(icon_path)


        except: pass


        # ----------------------------------





        self.resizable(True, True)


        self.grab_set() 


        self.on_save = on_save_callback


        self.on_close_cb = on_close_callback


        self.protocol("WM_DELETE_WINDOW", self.on_close)


        


        self.name_var = tk.StringVar(value=initial_data.get('text', ''))


        self.script_var = tk.StringVar(value=initial_data.get('script', ''))


        self.image_var = tk.StringVar(value=initial_data.get('image', ''))


        self.bold_var = tk.BooleanVar(value=initial_data.get('bold', '1') == '1')


        self.text_color = initial_data.get('text_color', '#333333')





        main_frame = ttk.Frame(self, padding=20)


        main_frame.pack(fill=tk.BOTH, expand=True)





        ttk.Label(main_frame, text="显示名称:").grid(row=0, column=0, sticky="w", pady=5)


        ttk.Entry(main_frame, textvariable=self.name_var, width=40).grid(row=0, column=1, columnspan=2, sticky="ew")





        ttk.Label(main_frame, text="绑定脚本:").grid(row=1, column=0, sticky="w", pady=5)


        ttk.Entry(main_frame, textvariable=self.script_var, width=30).grid(row=1, column=1, sticky="ew")


        ttk.Button(main_frame, text="...", width=4, command=self.browse_script).grid(row=1, column=2, padx=5)





        ttk.Label(main_frame, text="背景图片:").grid(row=2, column=0, sticky="w", pady=5)


        img_frame = ttk.Frame(main_frame)


        img_frame.grid(row=2, column=1, columnspan=2, sticky="ew")


        ttk.Entry(img_frame, textvariable=self.image_var, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)


        ttk.Button(img_frame, text="📷", width=4, command=self.capture_image).pack(side=tk.LEFT, padx=2)


        ttk.Button(img_frame, text="...", width=4, command=self.browse_image).pack(side=tk.LEFT)





        ttk.Label(main_frame, text="字体样式:").grid(row=3, column=0, sticky="w", pady=15)


        style_frame = ttk.Frame(main_frame)


        style_frame.grid(row=3, column=1, columnspan=2, sticky="w")


        ttk.Checkbutton(style_frame, text="加粗 (Bold)", variable=self.bold_var).pack(side=tk.LEFT, padx=(0, 20))


        self.color_btn = tk.Button(style_frame, text="选择文字颜色", bg=self.text_color, fg="white" if self.is_dark(self.text_color) else "black", command=self.choose_color)


        self.color_btn.pack(side=tk.LEFT)





        btn_frame = ttk.Frame(self, padding=(0, 20, 0, 0))


        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)


        ttk.Button(btn_frame, text="取消", command=self.on_close).pack(side=tk.RIGHT, padx=10, pady=10)


        ttk.Button(btn_frame, text="✅ 保存配置", command=self.save_config).pack(side=tk.RIGHT, pady=10)


        main_frame.columnconfigure(1, weight=1)





    def on_close(self):


        if self.on_close_cb: self.on_close_cb(self.geometry())


        self.destroy()


    def is_dark(self, hex_color):


        if not hex_color: return False


        h = hex_color.lstrip('#')


        try:


            rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


            return (rgb[0]*0.299 + rgb[1]*0.587 + rgb[2]*0.114) < 186


        except: return False


    def browse_script(self):


        f = filedialog.askopenfilename()


        if f: self.script_var.set(f)


    def browse_image(self):


        f = filedialog.askopenfilename(filetypes=[("Image","*.png;*.jpg;*.gif;*.ico;*.bmp")])


        if f: self.image_var.set(f)


    def capture_image(self):


        self.withdraw(); self.master.withdraw(); time.sleep(0.2)


        def on_finish(path):


            if path: self.image_var.set(path)


            self.master.deiconify(); self.deiconify() 


        ScreenCapture(self.master, on_finish)


    def choose_color(self):


        c = colorchooser.askcolor(color=self.text_color, title="选择文字颜色")[1]


        if c: 


            self.text_color = c


            try:


                if self.color_btn.winfo_exists():


                    self.color_btn.config(bg=c, fg="white" if self.is_dark(c) else "black")


            except: pass


    def save_config(self):


        data = {'text': self.name_var.get(), 'script': self.script_var.get(), 'image': self.image_var.get(), 'bold': self.bold_var.get(), 'text_color': self.text_color}


        self.on_save(data); self.on_close()





class FloatingPanelWindow(tk.Toplevel):


    def __init__(self, app, page_index, drop_x=None, drop_y=None):


        super().__init__(app.root)


        self.app = app


        self.page_index = page_index


        self.title(app.grid_config.get_panel_name(page_index))


        


        win_w, win_h = 1100, 650


        if drop_x is not None and drop_y is not None:


            scr_w = app.root.winfo_screenwidth()


            scr_h = app.root.winfo_screenheight()


            pos_x = drop_x - (win_w // 2)


            pos_y = drop_y - 20


            pos_x = max(0, min(pos_x, scr_w - win_w))


            pos_y = max(0, min(pos_y, scr_h - win_h))


            self.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")


        else:


            self.geometry(f"{win_w}x{win_h}")


            


        self.configure(bg=app.BG)


        self.protocol("WM_DELETE_WINDOW", self.on_close)


        


        ## self.attributes('-topmost', False)


        


        self.grid_container = ttk.Frame(self, padding="5")


        self.grid_container.pack(fill=tk.BOTH, expand=True)


        


        for c in range(9): self.grid_container.columnconfigure(c, weight=1)


        


        self.local_buttons = {}


        BTN_SIZE = 116


        current_font = ('Microsoft YaHei UI', app.btn_font_size_var.get())


        


        for r in range(5):


            for c in range(9):


                btn = tk.Button(self.grid_container, text="", font=current_font, wraplength=100, bg="#F5F5F5", relief="raised", bd=1, image=app.pixel_ref, width=BTN_SIZE, height=BTN_SIZE, compound="center")


                btn.grid(row=r, column=c, padx=3, pady=3)


                btn.bind("<Button-1>", lambda e, r=r, c=c: app.on_grid_click_or_drag_start(e, r, c, self.page_index))


                btn.bind("<ButtonRelease-1>", lambda e, r=r, c=c: app.on_grid_release(e, r, c, self.page_index))


                btn.bind("<B1-Motion>", lambda e, r=r, c=c: app.on_grid_motion(e, r, c, self.page_index))
                btn.bind("<Button-3>", lambda e, r=r, c=c: app.on_grid_right_click(e, r, c, self.page_index))
                btn.bind("<Enter>", lambda e, r=r, c=c: app.on_btn_enter(e, r, c, self.page_index))
                btn.bind("<Leave>", lambda e, r=r, c=c: app.on_btn_leave(e, r, c, self.page_index))
                if HAS_DND:


                    try: btn.drop_target_register(DND_FILES); btn.dnd_bind('<<Drop>>', lambda e, r=r, c=c: app.on_grid_drop_external(e, r, c, self.page_index))


                    except: pass


                self.local_buttons[(r, c)] = btn


                self.update_btn_ui(r, c)


                


    def on_close(self):


        del self.app.floating_panels[self.page_index]


        self.app.refresh_panel_tabs()


        self.destroy()


        


    def update_btn_ui(self, r, c):


        data = self.app.grid_config.get_btn_data(r, c, page=self.page_index)


        btn = self.local_buttons[(r, c)]


        


        script_path = data.get('script', '')


        text = data.get('text', '')


        font_weight = 'bold' if data.get('bold', '1') == '1' else 'normal'


        text_color = data.get('text_color', '#333333')


        img_path = data.get('image', '')


        


        if text: display_name = text


        elif img_path and os.path.exists(img_path): display_name = "" 


        else: display_name = os.path.basename(script_path) if script_path else "" 


        


        if img_path and os.path.exists(img_path):


            try:


                if HAS_PIL:


                    img = Image.open(img_path)


                    img = img.resize((104, 104), Image.Resampling.LANCZOS)


                    tk_img = ImageTk.PhotoImage(img)


                    self.app.grid_images[f"float_{self.page_index}_{r}_{c}"] = tk_img


                    btn.config(image=tk_img, text=display_name, compound="center", bg="white")


                else: 


                     btn.config(text=f"[{os.path.basename(img_path)}]\n{display_name}")


            except: btn.config(image=self.app.pixel_ref, text=display_name)


        else:


            btn.config(image=self.app.pixel_ref, text=display_name, bg="#F5F5F5")


            


        current_font = ('Microsoft YaHei UI', self.app.btn_font_size_var.get(), font_weight)


        btn.config(font=current_font, fg=text_color)





# --- KS 引擎 (增加 Call 支持) ---


class KSEngine:


    def __init__(self, update_status_callback, error_callback, msgbox_callback):


        self.running = False; self.paused = False; self.stop_signal = False


        self.update_status = update_status_callback; self.error_callback = error_callback; self.msgbox_callback = msgbox_callback 


        self.vars = {}


        # [NEW] Step execution support


        self.step_mode = False


        self.step_event = threading.Event()


        self.step_callback = None # func(line_index) 


    def check_hardware_stop(self):


        if (ctypes.windll.user32.GetAsyncKeyState(0x7B) & 0x8000): self.stop_signal = True; return True


        return False


    def check_stop(self):


        if self.stop_signal: raise InterruptedError("FORCE_STOP_SIGNAL")


        if self.check_hardware_stop(): raise InterruptedError("HARDWARE_F12_DETECTED")


        try:


            x, y = pyautogui.position()


            if x == 0 and y == 0: self.stop_signal = True; raise pyautogui.FailSafeException("Manual FailSafe")


        except: pass


    def parse_line(self, line):


        if "'" in line: line = line.split("'", 1)[0]


        if "//" in line: line = line.split("//", 1)[0]


        line = line.strip()


        if not line: return None, None


        if line.lower().startswith("end if"): return "endif", ""


        parts = line.split(maxsplit=1); cmd = parts[0].lower(); args = parts[1] if len(parts) > 1 else ""


        return cmd, args


    def evaluate_expr(self, expr):


        expr = re.sub(r'\bAnd\b', 'and', expr, flags=re.IGNORECASE); expr = re.sub(r'\bOr\b', 'or', expr, flags=re.IGNORECASE)


        try: return eval(expr, {"__builtins__": None}, self.vars)


        except Exception: return 0 


    def smart_sleep(self, seconds):


        end_time = time.time() + seconds


        while time.time() < end_time: self.check_stop(); time.sleep(0.01) 


    def wait_until_time(self, target_text):


        target_text = target_text.strip().strip('"').strip("'")


        match = re.match(r'^(\d{1,2}):(\d{1,2})(?::(\d{1,2})(?:\.(\d{1,3}))?)?$', target_text)


        if not match:


            raise ValueError("WaitUntil 格式应为 HH:MM 或 HH:MM:SS 或 HH:MM:SS.mmm")


        hour = int(match.group(1))


        minute = int(match.group(2))


        second = int(match.group(3) or 0)


        millisecond = int((match.group(4) or "0").ljust(3, "0"))


        if not 0 <= hour <= 23: raise ValueError("WaitUntil 小时必须在 0-23 之间")


        if not 0 <= minute <= 59: raise ValueError("WaitUntil 分钟必须在 0-59 之间")


        if not 0 <= second <= 59: raise ValueError("WaitUntil 秒必须在 0-59 之间")


        now_ts = time.time()


        now = time.localtime(now_ts)


        target_tuple = (now.tm_year, now.tm_mon, now.tm_mday, hour, minute, second, now.tm_wday, now.tm_yday, now.tm_isdst)


        target_ts = time.mktime(target_tuple) + millisecond / 1000.0


        if target_ts <= now_ts:


            target_ts += 24 * 60 * 60


        target_label = time.strftime("%Y-%m-%d", time.localtime(target_ts)) + f" {hour:02d}:{minute:02d}:{second:02d}.{millisecond:03d}"


        self.update_status(f"⏰ 等待到 {target_label}", color="blue")


        while True:


            self.check_stop()


            remain = target_ts - time.time()


            if remain <= 0:


                break


            time.sleep(min(0.05, remain))



    def _map_key(self, k):


        # Map recorded keys (pynput) to pyautogui keys


        k = k.lower()


        # [Fix] Emulators (MuMu) often recognize generic 'ctrl' better than 'ctrlleft'


        if k in ['ctrlleft', 'ctrlright']: return 'ctrl'


        if k in ['shiftleft', 'shiftright']: return 'shift'


        if k in ['altleft', 'altright']: return 'alt'


        return k


    def execute_script(self, filepath, speed_factor=1.0):


        if self.stop_signal: return


        if not os.path.exists(filepath):


            if os.path.exists(filepath + ".txt"): filepath += ".txt"


            elif os.path.exists(filepath + ".ks"): filepath += ".ks"


            else: return 


        _, lines = smart_read_file(filepath)


        if lines is None: self.error_callback(0, "无法识别文件编码", "", os.path.basename(filepath)); return


        


    def execute_from_lines(self, lines, source_name="Script", speed_factor=1.0):


        # [Refactored] Core execution logic extracted from execute_script


        if self.stop_signal: return





        # Save parent scope


        parent_vars = self.vars


        self.vars = {}; loop_stack = []; for_stack = []; jump_map = {}   


        


        try:


            for i, line in enumerate(lines):


                cmd, _ = self.parse_line(line)


                if not cmd: continue


                if cmd == 'do': loop_stack.append(i)


                elif cmd == 'loop': 


                    if loop_stack: jump_map[i] = loop_stack.pop()


                elif cmd == 'for': for_stack.append(i)


                elif cmd == 'next':


                    if for_stack: jump_map[i] = for_stack.pop()


            pc = 0


            while pc < len(lines):


                self.check_stop()


                while self.paused: self.check_stop(); self.update_status("⏸ 暂停中 (按 F11 继续)", color="blue"); time.sleep(0.05)


                cmd, args = self.parse_line(lines[pc])


                cmd, args = self.parse_line(lines[pc])


                if not cmd: pc += 1; continue


                self.check_stop()





                # [NEW] Check Step Mode


                if self.step_mode:


                    if self.step_callback: 


                        # Run callback in main thread if possible, but here we are in thread. 


                        # The callback handles thread safety (e.g., using after or event).


                        self.step_callback(pc)


                    self.step_event.wait() # Wait for signal


                    self.step_event.clear() # Reset


                    self.check_stop() # Check again after wait


                


                if cmd == 'call':


                    sub_path = args.strip().replace('"', '')


                    if not os.path.exists(sub_path):


                        if os.path.exists(sub_path + ".txt"): sub_path += ".txt"


                        elif os.path.exists(sub_path + ".ks"): sub_path += ".ks"


                    if os.path.exists(sub_path):


                        self.execute_script(sub_path, speed_factor)


                    else:


                        print(f"Warning: Script not found: {sub_path}")


                elif cmd == 'msgbox':


                    content = args


                    try:


                        expr_for_eval = content.replace('&', '+')


                        try: res = eval(expr_for_eval, {"__builtins__": None}, self.vars); content = str(res)


                        except:


                            if (content.startswith('"') and content.endswith('"')) or (content.startswith("'") and content.endswith("'")): content = content[1:-1]


                    except Exception: pass


                    stop_event = threading.Event(); self.msgbox_callback(content, stop_event); stop_event.wait()


                elif cmd == 'moveto': 


                    parts = args.split(',')


                    if len(parts) >= 2: x = self.evaluate_expr(parts[0]); y = self.evaluate_expr(parts[1]); pyautogui.moveTo(int(x), int(y))


                elif cmd == 'leftclick': pyautogui.click(clicks=int(args) if args.isdigit() else 1, button='left')


                elif cmd == 'rightclick': pyautogui.click(clicks=int(args) if args.isdigit() else 1, button='right')


                elif cmd == 'leftdown': pyautogui.mouseDown(button='left')


                elif cmd == 'leftup': pyautogui.mouseUp(button='left')


                elif cmd == 'rightdown': pyautogui.mouseDown(button='right')


                elif cmd == 'rightup': pyautogui.mouseUp(button='right')


                elif cmd == 'delay': val = int(args) if args.isdigit() else 100; self.smart_sleep((val/1000.0)/speed_factor)


                elif cmd == 'waituntil': self.wait_until_time(args)


                elif cmd == 'mousewheel':


                    val = int(args)


                    if -10 < val < 10: val *= 120


                    pyautogui.scroll(val)


                elif cmd == 'keypress':


                    if args:


                        try: 


                            # [Fix] Use DirectInput for emulators


                            DirectInput.click_key(args.lower())


                        except: pass


                elif cmd == 'keydown':


                    if args:


                        try: 


                            DirectInput.press(args.lower())


                        except: pass


                elif cmd == 'keyup':


                    if args:


                        try: 


                            DirectInput.release(args.lower())


                        except: pass


                elif cmd == 'copypaste':


                    # [NEW] Paste from clipboard (supports Chinese)


                    try:


                        # Use DirectInput (ScanCode) for Ctrl+V


                        DirectInput.press('ctrl')


                        time.sleep(0.05)


                        DirectInput.click_key('v')


                        time.sleep(0.05)


                        DirectInput.release('ctrl')


                    except: pass


                elif cmd == 'findpic':


                    try:


                        # [Refactored] Robust parsing for FindPic 0,0,1745,2059,"path",0.9,intX,intY


                        path = ""; region = None


                        


                        # Extract path first (quoted)


                        path_match = re.search(r'["\']([^"\']+)["\']', args)


                        if path_match:


                            path = path_match.group(1)


                            left_args = args[:path_match.start()]


                            right_args = args[path_match.end():]


                            


                            # Parse Region (Left args): x1, y1, x2, y2


                            l_parts = [x.strip() for x in left_args.split(',') if x.strip()]


                            if len(l_parts) >= 4:


                                try:


                                    r_x1 = int(self.evaluate_expr(l_parts[0]))


                                    r_y1 = int(self.evaluate_expr(l_parts[1]))


                                    r_x2 = int(self.evaluate_expr(l_parts[2]))


                                    r_y2 = int(self.evaluate_expr(l_parts[3]))


                                    # PyAutoGUI region: (left, top, width, height)


                                    region = (r_x1, r_y1, r_x2 - r_x1, r_y2 - r_y1)


                                except: pass





                            # Parse Params (Right args): conf, var_x, var_y


                            r_parts = [x for x in right_args.split(',') if x.strip()]


                            conf = 0.9; var_x = "intX"; var_y = "intY"


                            if len(r_parts) >= 1: 


                                try: conf = float(r_parts[0])


                                except: pass


                            if len(r_parts) >= 2: var_x = r_parts[1].strip()


                            if len(r_parts) >= 3: var_y = r_parts[2].strip()


                        else:


                            # Fallback


                            parts = [x.strip() for x in args.split(',')]


                            if len(parts) >= 8:


                                try:


                                    r_x1 = int(self.evaluate_expr(parts[0]))


                                    r_y1 = int(self.evaluate_expr(parts[1]))


                                    r_x2 = int(self.evaluate_expr(parts[2]))


                                    r_y2 = int(self.evaluate_expr(parts[3]))


                                    region = (r_x1, r_y1, r_x2 - r_x1, r_y2 - r_y1)


                                except: pass


                                path = parts[4]


                                try: conf = float(parts[5])


                                except: conf = 0.9


                                var_x = parts[6]; var_y = parts[7]





                        found_x, found_y = -1, -1


                        if os.path.exists(path):


                            # Debug Info


                            print(f"[FindPic] Searching: {path} Region={region} Conf={conf}")


                            


                            try:


                                # Try locating with confidence + grayscale (more robust)


                                # NOTE: confidence requires opencv-python installed


                                box = pyautogui.locateOnScreen(path, confidence=conf, region=region, grayscale=True)


                                if box: 


                                    pt = pyautogui.center(box)


                                    found_x, found_y = int(pt.x), int(pt.y)


                            except Exception as e:


                                err_msg = str(e)


                                print(f"[FindPic] Confidence Search Error: {err_msg}")


                                # Alert user via UI if looks like missing OpenCV


                                if "opencv" in err_msg.lower() or "module" in err_msg.lower():


                                    self.update_status(f"⚠️ [找图失败] 缺少OpenCV组件，请pip install opencv-python", "red")


                                


                                try:


                                    # Fallback: Exact match (no confidence), grayscale


                                    print("[FindPic] Falling back to exact match...")


                                    box = pyautogui.locateOnScreen(path, region=region, grayscale=True)


                                    if box:


                                        pt = pyautogui.center(box)


                                        found_x, found_y = int(pt.x), int(pt.y)


                                except Exception as e2:


                                    print(f"[FindPic] Fallback Failed: {e2}")


                        else:


                            print(f"FindPic Image Not Found on Disk: {path}")


                            self.update_status(f"⚠️ 找不到图片文件: {os.path.basename(path)}", "red")





                        self.vars[var_x] = found_x


                        self.vars[var_y] = found_y


                        print(f"FindPic Result: {found_x}, {found_y}")


                        


                    except Exception as e: 


                        print(f"FindPic Parse Error: {e}")


                        self.update_status(f"⚠️ 找图指令解析错误: {e}", "red")


                elif cmd == 'if':


                    condition_str = args; 


                    if condition_str.lower().endswith('then'): condition_str = condition_str[:-4]


                    if not self.evaluate_expr(condition_str):


                        stack_depth = 0


                        for scan_i in range(pc + 1, len(lines)):


                            sc_cmd, _ = self.parse_line(lines[scan_i])


                            if not sc_cmd: continue


                            if sc_cmd == 'if': stack_depth += 1


                            elif sc_cmd == 'endif':


                                if stack_depth == 0: pc = scan_i; break


                                else: stack_depth -= 1


                elif cmd == 'endif': pass 


                elif cmd == 'do': pass


                elif cmd == 'loop':


                    if pc in jump_map: pc = jump_map[pc]; continue 


                elif cmd == 'exit':


                    if args.lower() == 'do':


                        stack_depth = 0


                        for scan_i in range(pc + 1, len(lines)):


                            sc_cmd, _ = self.parse_line(lines[scan_i])


                            if sc_cmd == 'do': stack_depth += 1


                            elif sc_cmd == 'loop':


                                if stack_depth == 0: pc = scan_i; break


                                else: stack_depth -= 1


                elif cmd == 'exitdoifkey':


                    key_val = args; triggered = False


                    if key_val.isdigit(): pass 


                    else:


                        vk = VK_MAP.get(key_val.lower())


                        if vk and (ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000): triggered = True


                    if triggered:


                        stack_depth = 0


                        for scan_i in range(pc + 1, len(lines)):


                            sc_cmd, _ = self.parse_line(lines[scan_i])


                            if sc_cmd == 'do': stack_depth += 1


                            elif sc_cmd == 'loop':


                                if stack_depth == 0: pc = scan_i; break


                                else: stack_depth -= 1


                elif cmd == 'stop':


                    target = args.strip()


                    if target:


                        self.update_status(f"正在停止进程: {target}...", "black")


                        cflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0


                        # 1. Try stopping by Image Name (using /IM which is more robust for names)


                        cmd_im = f'taskkill /F /IM "*{target}*"'


                        # 2. Try stopping by Window Title


                        cmd_title = f'taskkill /F /FI "WINDOWTITLE eq *{target}*"'


                        


                        executed_count = 0


                        for c in [cmd_im, cmd_title]:


                            try:


                                res = subprocess.run(c, capture_output=True, text=True, shell=True, creationflags=cflags)


                                if res.returncode == 0:


                                    print(f"[Stop] Success: {c}")


                                    executed_count += 1


                                else:


                                    # Ignore "not found" errors (exit code 128 usually), print others


                                    if "这是没有" not in res.stderr and "not found" not in res.stderr:


                                        print(f"[Stop] Failed: {c} -> {res.stderr}")


                            except Exception as e:


                                print(f"[Stop] Error executing {c}: {e}")


                                


                        if executed_count > 0:


                            self.update_status(f"已停止包含 '{target}' 的进程", "green")


                        else:


                            # If completely failed/not found, mostly harmless, but good to know in debug


                            pass


                elif cmd == 'runapp':


                    raw_cmd = args.strip()


                    if raw_cmd.startswith('(') and raw_cmd.endswith(')'):


                        raw_cmd = raw_cmd[1:-1].strip()


                    if (raw_cmd.startswith('"') and raw_cmd.endswith('"')) or (raw_cmd.startswith("'") and raw_cmd.endswith("'")):


                        raw_cmd = raw_cmd[1:-1].strip()


                    app_path = raw_cmd


                    if os.path.exists(app_path):


                        work_dir = os.path.dirname(app_path)


                        # [Refactored] Universal environment cleanup for ALL apps (EXE, BAT, CMD)


                        # This avoids PyInstaller environment leakage (PYTHONPATH, _MEIPASS) causing crashes in child apps


                        clean_env = os.environ.copy()


                        for k in ['PYTHONPATH', 'PYTHONHOME', 'TCL_LIBRARY', 'TK_LIBRARY', '_MEIPASS', '_MEIPASS2', 


                                  'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'LD_LIBRARY_PATH']: 


                            clean_env.pop(k, None)


                        


                        executed = False


                        


                        # Special handling for shortcuts (.lnk) - use os.startfile


                        if app_path.lower().endswith('.lnk'):


                            try:


                                try: os.startfile(app_path, cwd=work_dir); executed = True


                                except TypeError: pass 


                            except Exception as e:


                                print(f"RunApp startfile failed: {e}")


                        


                        # Universal Popen fallback for EXE, BAT, CMD, etc.


                        if not executed:


                            try:


                                # [Refactored] Run as Admin using PowerShell Start-Process -Verb RunAs


                                # We still use Popen to launch PowerShell so we can pass the 'clean_env'


                                # This ensures the child process runs as Admin AND has a clean environment.


                                ps_cmd = f"Start-Process -FilePath '{app_path}' -WorkingDirectory '{work_dir}' -Verb RunAs"


                                


                                subprocess.Popen(


                                    ["powershell", "-NoProfile", "-Command", ps_cmd],


                                    cwd=work_dir,


                                    env=clean_env,


                                    stdin=subprocess.DEVNULL,


                                    stdout=subprocess.DEVNULL,


                                    stderr=subprocess.DEVNULL,


                                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0


                                )


                            except Exception as e:


                                print(f"RunApp Admin Popen failed: {e}")


                    else:


                        try: subprocess.Popen(app_path, shell=True)


                        except Exception as e: print(f"RunApp Failed: {e}")


                elif cmd == 'for':


                    if 'to' in args.lower(): pass


                    else:


                        count = int(args)


                        if pc not in self.vars: self.vars[f"_loop_cnt_{pc}"] = 0


                        if self.vars[f"_loop_cnt_{pc}"] >= count:


                            del self.vars[f"_loop_cnt_{pc}"]; stack_depth = 0


                            for scan_i in range(pc + 1, len(lines)):


                                sc_cmd, _ = self.parse_line(lines[scan_i])


                                if sc_cmd == 'for': stack_depth += 1


                                elif sc_cmd == 'next':


                                    if stack_depth == 0: pc = scan_i; break


                                    else: stack_depth -= 1


                elif cmd == 'next':


                    if pc in jump_map:


                        start_line = jump_map[pc]; _, f_args = self.parse_line(lines[start_line]); total = int(f_args); key = f"_loop_cnt_{start_line}"; self.vars[key] = self.vars.get(key, 0) + 1


                        if self.vars[key] < total: pc = start_line


                        else: del self.vars[key]


                pc += 1


        except InterruptedError: return 


        except pyautogui.FailSafeException: self.stop_signal = True; raise InterruptedError("FailSafe Triggered")


        except Exception as e:


            if self.stop_signal: return 


            if self.error_callback(pc+1, str(e), lines[pc].strip(), source_name) == "stop": self.stop_signal = True; return


        finally:


            self.vars = parent_vars





    def execute_script(self, filepath, speed_factor=1.0):


        if self.stop_signal: return


        if not os.path.exists(filepath):


            if os.path.exists(filepath + ".txt"): filepath += ".txt"


            elif os.path.exists(filepath + ".ks"): filepath += ".ks"


            else: return 


        _, lines = smart_read_file(filepath)


        if lines is None: self.error_callback(0, "无法识别文件编码", "", os.path.basename(filepath)); return


        self.execute_from_lines(lines, source_name=os.path.basename(filepath), speed_factor=speed_factor)





class Recorder:


    def __init__(self):


        self.recording = False; self.events = []; self.last_action_time = 0 


        self.temp_press_start_time = 0; self.temp_press_pos = (0, 0); self.mouse_listener = None; self.keyboard_listener = None


        self.HOLD_THRESHOLD = 0.2


        self.last_recorded_pos = None # [NEW] 记录上一次记录的坐标，防止重复 MoveTo





        # --- 键值映射 ---


        self.special_keys = {


            keyboard.Key.space: 'space',


            keyboard.Key.enter: 'enter',


            keyboard.Key.tab: 'tab',


            keyboard.Key.esc: 'esc',


            keyboard.Key.backspace: 'backspace',


            keyboard.Key.delete: 'delete',


            keyboard.Key.up: 'up',


            keyboard.Key.down: 'down',


            keyboard.Key.left: 'left',


            keyboard.Key.right: 'right',


            keyboard.Key.shift: 'shift',


            keyboard.Key.shift_l: 'shiftleft',


            keyboard.Key.shift_r: 'shiftright',


            keyboard.Key.ctrl: 'ctrl',


            keyboard.Key.ctrl_l: 'ctrlleft',


            keyboard.Key.ctrl_r: 'ctrlright',


            keyboard.Key.alt: 'alt',


            keyboard.Key.alt_l: 'altleft',


            keyboard.Key.alt_r: 'altright',


            keyboard.Key.f1: 'f1', keyboard.Key.f2: 'f2', keyboard.Key.f3: 'f3', keyboard.Key.f4: 'f4',


            keyboard.Key.f5: 'f5', keyboard.Key.f6: 'f6', keyboard.Key.f7: 'f7', keyboard.Key.f8: 'f8',


            keyboard.Key.f9: 'f9', keyboard.Key.f10: 'f10', keyboard.Key.f11: 'f11', keyboard.Key.f12: 'f12'


        }





    def start(self):


        self.events = []; self.last_action_time = time.time(); self.recording = True


        self.last_recorded_pos = None # 重置坐标状态


        self.mouse_listener = mouse.Listener(on_click=self.on_click, on_scroll=self.on_scroll)


        self.mouse_listener.start()


        self.keyboard_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)


        self.keyboard_listener.start()





    def stop(self): 


        self.recording = False


        if self.mouse_listener: self.mouse_listener.stop()


        if self.keyboard_listener: self.keyboard_listener.stop()





    def trim_last_click(self):


        if not self.events: return


        try:


            # [Refactored] More robust trimming of the last action (clicking the Stop button)


            # Typically: MoveTo -> Delay -> LeftDown (or Click) -> ...


            # We want to remove the entire last sequence related to the stop button click.


            


            # 1. Remove trailing Delays (post-click delays)


            while self.events and self.events[-1].startswith("Delay"):


                self.events.pop()


                


            # 2. Remove Up/Click/Down action


            # If successfully merged to Click


            if self.events and "Click" in self.events[-1]:


                self.events.pop()


            # If split Down/Up


            elif self.events and "Up" in self.events[-1]:


                self.events.pop()


                while self.events and self.events[-1].startswith("Delay"): self.events.pop()


                if self.events and "Down" in self.events[-1]: self.events.pop()


            elif self.events and "Down" in self.events[-1]:


                self.events.pop()


                


            # 3. Remove Pre-Click Delay


            while self.events and self.events[-1].startswith("Delay"):


                self.events.pop()


                


            # 4. Remove the MoveTo that moved to the button


            if self.events and self.events[-1].startswith("MoveTo"):


                self.events.pop()


                


        except: pass





    def _record_delay(self):


        ct = time.time()


        delay = int((ct - self.last_action_time) * 1000)


        if delay > 10:


            self.events.append(f"Delay {delay}")


        self.last_action_time = ct





    # [NEW] 坐标去重辅助函数


    def _record_moveto_if_needed(self, x, y):


        if self.last_recorded_pos == (x, y):


            return


        self.events.append(f"MoveTo {x}, {y}")


        self.last_recorded_pos = (x, y)





    def on_click(self, x, y, button, pressed):


        if not self.recording: return


        


        # 记录当前动作前的延时


        self._record_delay()


        


        # 记录坐标 (按下和抬起都记录，确保拖拽正确)


        self._record_moveto_if_needed(x, y)


        


        btn_str = "Left" if button == mouse.Button.left else "Right"


        if pressed:


            self.events.append(f"{btn_str}Down 1")


        else:


            # [Fix] 尝试将 Down + Delay + Up 合并为 Click


            merged = False


            if self.events:


                last_idx = len(self.events) - 1


                last_event = self.events[last_idx]


                target_down = f"{btn_str}Down 1"


                


                # 情况1: Down -> Up (无延迟)


                if last_event == target_down:


                    self.events.pop()


                    self.events.append(f"{btn_str}Click 1")


                    merged = True


                


                # [Fix] 增强合并逻辑：允许中间夹杂 MoveTo (鼠标抖动)


                # 倒序检查最后几个事件: [Down] or [Down, Delay] or [Down, MoveTo] or [Down, Delay, MoveTo]


                merged = False


                


                # 获取待检查的事件列表 (最多回溯3个)


                last_evs = self.events[-3:] 


                pop_count = 0


                found_down = False


                delay_val = 0


                


                # 从后往前扫描


                for ev in reversed(last_evs):


                    pop_count += 1


                    if ev == target_down:


                        found_down = True


                        break


                    elif ev.startswith("Delay "):


                        try: delay_val += int(ev.split()[1])


                        except: pass


                    elif ev.startswith("MoveTo "):


                        pass # 忽略中间的移动 (认为是抖动)


                    else:


                        break # 遇到其他指令，停止匹配


                


                # 如果找到了Down，且总延时很短 (<= 500ms)，则合并为点击


                # 用户提到 100ms，这里设 500ms 比较稳，83ms 肯定包含在内


                if found_down and delay_val <= 500:


                    for _ in range(pop_count): self.events.pop()


                    self.events.append(f"{btn_str}Click 1")


                    merged = True


            


            if not merged:


                self.events.append(f"{btn_str}Up 1")


            


        self.last_action_time = time.time()





    def on_scroll(self, x, y, dx, dy):


        if not self.recording: return


        self._record_delay()


        self._record_moveto_if_needed(x, y)


        self.events.append(f"MouseWheel {int(dy)}")


        self.last_action_time = time.time()





    def get_key_name(self, key):


        if key in self.special_keys:


            return self.special_keys[key]


        if hasattr(key, 'char') and key.char:


            # [Fix] Handle control codes (1-26 for Ctrl+A to Ctrl+Z)


            if ord(key.char) < 32:


                # Map \x01 -> a, \x02 -> b, ..., \x16 -> v


                val = ord(key.char)


                if 1 <= val <= 26:


                    return chr(val + 96) # 97 is 'a'


            return key.char


        return str(key).replace('Key.', '')





    def on_press(self, key):


        if not self.recording: return


        if key == keyboard.Key.f12: return


        


        self._record_delay()


        


        try:


            x, y = pyautogui.position()


            self._record_moveto_if_needed(x, y)


        except: pass





        k_name = self.get_key_name(key)


        


        # [Fix] 如果按键是空的 (例如某些特殊键没处理好), 跳过以免脚本乱


        if not k_name or not k_name.strip(): return 





        self.events.append(f"KeyDown {k_name}")


        self.last_action_time = time.time()





    def on_release(self, key):


        if not self.recording: return


        if key == keyboard.Key.f12: return





        self._record_delay()


        


        try:


            x, y = pyautogui.position()


            self._record_moveto_if_needed(x, y)


        except: pass





        k_name = self.get_key_name(key)


        


        # [Fix]


        if not k_name or not k_name.strip(): return 





        self.events.append(f"KeyUp {k_name}")


        self.last_action_time = time.time()





    def save(self, p):


        with open(p, 'w', encoding='utf-8') as f: f.write("\n".join(self.events))





class ScriptEditor:


    def __init__(self, master, script_path, refresh_callback, geometry, save_geom_callback=None, app_instance=None):


        self.path = script_path; self.cb = refresh_callback; self.g_cb = save_geom_callback; self.mod = False; self.app = app_instance


        self.root = tk.Toplevel(master) # 这里的master其实是app.root


        self.root.title(f"编辑: {os.path.basename(script_path)}")


        try: self.root.geometry(geometry)


        except: self.root.geometry("800x600") 


        self.root.protocol("WM_DELETE_WINDOW", self.on_close)


        


        # --- 子窗口图标 ---


        try:


            icon_path = os.path.join(BASE_DIR, "anjian20251216.ico")


            if os.path.exists(icon_path):


                self.root.iconbitmap(icon_path)


        except: pass


        # ----------------


        


        # [修改] 第一排按钮改成两行


        toolbar = ttk.Frame(self.root, padding="5 5 5 0")


        toolbar.pack(fill=tk.X, side=tk.TOP)


        


        toolbar1 = ttk.Frame(toolbar); toolbar1.pack(fill=tk.X, side=tk.TOP)


        toolbar2 = ttk.Frame(toolbar); toolbar2.pack(fill=tk.X, side=tk.TOP, pady=(5,0))


        


        # 第一行: 文件和录制操作


        if self.app:


            ttk.Button(toolbar1, text="🔴 录制", command=self.record_script, width=8).pack(side=tk.LEFT, padx=2) 


            ttk.Button(toolbar1, text="▶ 播放", command=self.play_script, width=8).pack(side=tk.LEFT, padx=2)


            ttk.Button(toolbar1, text="⏭ 单步(F11)", command=self.step_execution, width=10).pack(side=tk.LEFT, padx=2)


            self.root.bind('<F11>', lambda e: self.step_execution())


            self.root.bind('<F12>', lambda e: self.stop_step_execution())





        # Continue __init__ logic


        ttk.Button(toolbar1, text="💾 另存为", command=self.save_as, width=8).pack(side=tk.LEFT, padx=2)


        ttk.Button(toolbar1, text="✅ 保存并退出", command=self.save_and_exit, width=12).pack(side=tk.LEFT, padx=2)


        


        self.st = tk.StringVar(value="已加载")


        ttk.Label(toolbar1, textvariable=self.st).pack(side=tk.RIGHT, padx=10)





        # 第二行: 编辑插入工具 (Style Tool.TButton implies colors, we set fg_color directly)


        ttk.Button(toolbar2, text="📷 找图", style='Tool.TButton', command=self.insert_image_search, width=8).pack(side=tk.LEFT, padx=2)


        ttk.Button(toolbar2, text="⏳ Delay", style='Tool.TButton', command=self.insert_delay, width=8).pack(side=tk.LEFT, padx=2)


        ttk.Button(toolbar2, text="💬 MsgBox", style='Tool.TButton', command=self.insert_msgbox, width=10).pack(side=tk.LEFT, padx=2)


        ttk.Button(toolbar2, text="⏰ 定时", style='Tool.TButton', command=self.insert_schedule_template, width=8).pack(side=tk.LEFT, padx=2)


        # [NEW] FOR Loop Button


        ttk.Button(toolbar2, text="🔁 FOR", style='Tool.TButton', command=self.insert_for_loop, width=8).pack(side=tk.LEFT, padx=2)


        ttk.Button(toolbar2, text="' 注释", style='Tool.TButton', command=self.comment_selection, width=8).pack(side=tk.LEFT, padx=2)


        ttk.Button(toolbar2, text="📑 缩进", style='Tool.TButton', command=self.auto_format, width=8).pack(side=tk.LEFT, padx=2)


        


        mf = ttk.Frame(self.root); mf.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)


        self.v_sb = ttk.Scrollbar(mf); self.v_sb.pack(side=tk.RIGHT, fill=tk.Y)


        self.h_sb = ttk.Scrollbar(mf, orient=tk.HORIZONTAL); self.h_sb.pack(side=tk.BOTTOM, fill=tk.X)


        self.txt = tk.Text(mf, wrap="none", font=('Consolas', 14), undo=True, yscrollcommand=self.v_sb.set, xscrollcommand=self.h_sb.set)


        self.txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)


        self.v_sb.config(command=self.txt.yview); self.h_sb.config(command=self.txt.xview)


        # For code editor, horizontal scroll IS critical.


        


        # Let's bind keys.


        self.txt.bind("<Control-s>", lambda e: self.save())


        self.txt.bind("<KeyRelease>", self.mark)


        


        self.load()





    def stop_step_execution(self):


        if self.app and self.app.is_executing:


             self.app.engine.stop_signal = True


             self.app.engine.step_event.set() # Unblock wait to allow check_stop to run





    def load(self):


        content, _ = smart_read_file(self.path)


        if content is not None: self.txt.insert(tk.END, content); self.txt.edit_modified(False); self.mod = False


        else: messagebox.showerror("Err", "无法识别文件编码"); self.root.destroy()


    def mark(self, e=None):


        if self.txt.edit_modified(): self.mod = True; self.root.title(f"*编辑: {os.path.basename(self.path)}"); self.st.set("未保存"); self.txt.edit_modified(False)


    def save(self, e=None):


        try:


            with open(self.path, 'w', encoding='utf-8') as f: f.write(self.txt.get('1.0', tk.END))


            self.mod = False; self.root.title(f"编辑: {os.path.basename(self.path)}"); self.st.set("已保存"); self.cb()


        except Exception as e: messagebox.showerror("Fail", str(e))


    def save_as(self):


        initial_dir = os.path.dirname(self.path); initial_file = os.path.basename(self.path)


        f = filedialog.asksaveasfilename(initialdir=initial_dir, initialfile=initial_file, title="另存为脚本", filetypes=[("所有文件", "*.*")])


        if f:


            try:


                with open(f, 'w', encoding='utf-8') as file: file.write(self.txt.get('1.0', tk.END))


                self.path = f; self.mod = False; self.root.title(f"编辑: {os.path.basename(self.path)}"); self.st.set("已另存"); self.cb()


            except Exception as e: messagebox.showerror("另存失败", str(e))


    def save_and_exit(self):


        self.save()


        if not self.mod: self.root.destroy()


    def record_script(self): # [NEW]


        if not self.app: return


        self.root.withdraw() # Hide editor


        


        def on_finish_record(content):


            self.root.deiconify() # Show editor


            if content:


                 # [Modified] Add separator comments


                 final_content = f"\n' ------录制-------\n{content}\n' ------录制-------\n"


                 self.txt.insert(tk.INSERT, final_content)


                 self.mark()


                 


        self.app.on_record_finish_callback = on_finish_record


        # Trigger global record start. 


        # Note: app.toggle_record checks if recording, if not starts.


        if self.app.recorder.recording:


             self.app.toggle_record() # Stop existing?


             


        self.app.toggle_record() # Start recording


        


    def play_script(self):


        self.save() 


        if not self.app: return


        


        if self.app.is_executing:


            messagebox.showinfo("提示", "当前有任务正在执行，请等待执行完毕")


            return


            


        self.app.is_executing = True


        self.app.engine.stop_signal = False


        


        # 隐藏当前窗口


        self.root.withdraw()


        


        def run_thread():


            if hasattr(self.app, 'update_status_bar'): self.app.update_status_bar(f"▶ 正在调试: {os.path.basename(self.path)}", "blue")


            if hasattr(self.app, 'update_run_status'): self.app.update_run_status("▶ 调试中", "blue")


            try:


                # Use engine, pass speed from app if available


                speed = 1.0


                if hasattr(self.app, 'speed_var'): speed = self.app.speed_var.get()


                self.app.engine.execute_script(self.path, speed)


            except Exception as e:


                print(f"Debug Error: {e}")


            


            self.app.is_executing = False


            if self.app.engine.stop_signal:


                if hasattr(self.app, 'update_status_bar'): self.app.update_status_bar("⛔ 调试已终止", "red")


                if hasattr(self.app, 'update_run_status'): self.app.update_run_status("⛔ 已停止", "red")


            else:


                if hasattr(self.app, 'update_status_bar'): self.app.update_status_bar("✅ 调试完成", "black")


                if hasattr(self.app, 'update_run_status'): self.app.update_run_status("✅ 完成", "black")


            


            # 恢复窗口显示


            self.root.after(0, self.root.deiconify)





        threading.Thread(target=run_thread, daemon=True).start()





    def step_execution(self):


        self.save()


        if not self.app: return


        


        # Highlight Callback


        def on_step(line_idx):


            # Highlight execution line


            def _ui():


                try:


                    self.txt.tag_remove("exec_highlight", "1.0", tk.END)


                    self.txt.tag_config("exec_highlight", background="#FFFF00") # Yellow background


                    self.txt.tag_add("exec_highlight", f"{line_idx+1}.0", f"{line_idx+1}.end")


                    self.txt.see(f"{line_idx+1}.0")


                except: pass


            self.root.after(0, _ui)





        # If already running (and paused in step mode), just advance


        if self.app.is_executing and self.app.engine.step_mode:


             self.app.engine.step_event.set()


             return





        if self.app.is_executing:


             messagebox.showinfo("提示", "当前有任务正在执行，无法切换到单步模式")


             return





        # Start new execution in Step Mode


        self.app.is_executing = True


        self.app.engine.stop_signal = False


        self.app.engine.step_mode = True


        self.app.engine.step_callback = on_step


        self.app.engine.step_event.clear() # Ensure wait


        


        self.app.engine.step_mode = True


        self.app.engine.step_callback = on_step


        self.app.engine.step_event.clear() # Ensure wait


        


        self.auto_step_running = False


        self.auto_step_thread = None





        def auto_step_worker():


            # Initial Delay 1s


            time.sleep(1)


            while self.auto_step_running and self.app.is_executing and not self.app.engine.stop_signal:


                if self.app.engine.step_mode:


                     self.root.after(0, lambda: self.app.engine.step_event.set())


                # Wait 1s between steps


                for _ in range(10): # Check every 0.1s to allow faster pause


                    if not self.auto_step_running or self.app.engine.stop_signal: break


                    time.sleep(0.1)





        def on_toggle_auto_step():


             self.auto_step_running = not self.auto_step_running


             self.step_win.update_btn_state(self.auto_step_running)


             


             if self.auto_step_running:


                 # Start thread


                 if self.auto_step_thread is None or not self.auto_step_thread.is_alive():


                     self.auto_step_thread = threading.Thread(target=auto_step_worker, daemon=True)


                     self.auto_step_thread.start()


        


        def on_stop_step():


             self.auto_step_running = False


             self.stop_step_execution()


        


        # Use saved position if available


        initial_pos = getattr(self.app, 'floating_step_pos', None)


        if not initial_pos: initial_pos = "+100+100"


             


        self.step_win = FloatingStepWindow(self.app, on_toggle_auto_step, on_stop_step, initial_pos=initial_pos)





        def run_thread():


            if hasattr(self.app, 'update_status_bar'): self.app.update_status_bar(f"⏭ 单步调试: {os.path.basename(self.path)}", "blue")


            if hasattr(self.app, 'update_run_status'): self.app.update_run_status("⏭ 单步中", "blue")


            self.root.after(0, lambda: self.txt.config(state='disabled')) # Disable editing while running


            


            try:


                self.app.engine.execute_script(self.path, self.app.speed_var.get())


            except Exception as e:


                print(f"Step Debug Error: {e}")


            


            self.app.is_executing = False


            self.app.engine.step_mode = False


            self.app.engine.step_callback = None


            self.auto_step_running = False


            


            # [NEW] Cleanup Step Window


            if hasattr(self, 'step_win') and self.step_win:


                 self.root.after(0, self.step_win.destroy)


            


            if self.app.engine.stop_signal:


                if hasattr(self.app, 'update_status_bar'): self.app.update_status_bar("⛔ 调试已终止", "red")


            else:


                if hasattr(self.app, 'update_status_bar'): self.app.update_status_bar("✅ 调试完成", "black")


            


            def restore_ui():


                self.txt.config(state='normal')


                self.txt.tag_remove("exec_highlight", "1.0", tk.END)


                


            self.root.after(0, restore_ui)





        threading.Thread(target=run_thread, daemon=True).start()





    def insert_image_search(self):


        self.root.withdraw(); time.sleep(0.2)


        def on_capture_finished(img_path):


            self.root.deiconify() 


            if img_path:


                img_name = os.path.basename(img_path); screen_w, screen_h = pyautogui.size(); code = f"\n' --- 找图: {img_name} ---\nFindPic 0,0,{screen_w},{screen_h},\"{img_path}\",0.9,intX,intY\nIf intX >= 0 And intY >= 0 Then\n    MoveTo intX, intY\n    LeftClick 1\n    Delay 500\nEnd If\n"


                self.txt.insert(tk.INSERT, code); self.mark()


        ScreenCapture(self.root, on_capture_finished)


    def insert_delay(self): self.txt.insert(tk.INSERT, '\nDelay 1000\n'); self.mark()


    def insert_msgbox(self): self.txt.insert(tk.INSERT, '\nMsgBox "提示内容"\n'); self.mark()


    def insert_schedule_template(self):


        template = (
            "\n' --- 定时执行模板 ---\n"
            "' WaitUntil 格式: 时:分:秒.毫秒，时间已过会等到明天\n"
            "WaitUntil 20:30:15.500\n"
            "Call \"E:\\\\ProjectAI\\\\anjian20251212\\\\scripts\\\\你的脚本.txt\"\n"
        )


        self.txt.insert(tk.INSERT, template); self.mark()


    def insert_for_loop(self): self.txt.insert(tk.INSERT, "\nFor 5\n    \nNext\n"); self.mark()


    def auto_format(self):


        content = self.txt.get("1.0", tk.END)


        lines = [line.strip() for line in content.splitlines()]


        formatted = []; indent = 0


        for line in lines:


            if not line: continue


            lower_line = line.lower()


            if lower_line.startswith(("end if", "endif", "next", "loop")): indent = max(0, indent - 1)


            elif lower_line.startswith(("else", "elseif")): indent = max(0, indent - 1)


            formatted.append("    " * indent + line)


            if lower_line.startswith("if ") and lower_line.endswith(" then"): indent += 1


            elif lower_line.startswith(("for ", "do")): indent += 1


            elif lower_line.startswith(("else", "elseif")): indent += 1


        self.txt.delete("1.0", tk.END); self.txt.insert("1.0", "\n".join(formatted)); self.mark()


    def comment_selection(self):


        try:


            # 尝试获取选区


            try:


                start_index = self.txt.index("sel.first")


                end_index = self.txt.index("sel.last")


            except tk.TclError:


                # 无选区，则默认当前行


                start_index = self.txt.index("insert linestart")


                end_index = self.txt.index("insert lineend")





            # expand to full lines


            start_line = int(start_index.split('.')[0])


            end_line = int(end_index.split('.')[0])


            


            # if sel.last is at column 0, it means it selected the newline of prev line


            if end_index.endswith('.0') and end_line > start_line:


                end_line -= 1





            lines = []


            all_commented = True


            for i in range(start_line, end_line + 1):


                line = self.txt.get(f"{i}.0", f"{i}.end")


                lines.append(line)


                # 检查是否已注释 (支持 #, //, ')


                stripped = line.strip()


                if stripped and not (stripped.startswith('#') or stripped.startswith('//') or stripped.startswith("'")):


                    all_commented = False


            


            new_lines = []


            if all_commented:


                # Uncomment


                for line in lines:


                    stripped = line.lstrip()


                    if stripped.startswith('# '): new_lines.append(line.replace('# ', '', 1))


                    elif stripped.startswith('#'): new_lines.append(line.replace('#', '', 1))


                    elif stripped.startswith("' "): new_lines.append(line.replace("' ", '', 1)) 


                    elif stripped.startswith("'"): new_lines.append(line.replace("'", '', 1))


                    elif stripped.startswith("//"): new_lines.append(line.replace("//", '', 1))


                    else: new_lines.append(line)


            else:


                # Comment


                for line in lines:


                    if line.strip() == "": new_lines.append(line)


                    else: new_lines.append("' " + line)


            


            # Replace


            self.txt.delete(f"{start_line}.0", f"{end_line}.end")


            self.txt.insert(f"{start_line}.0", "\n".join(new_lines))


            self.mark()


            


            # restore trigger slightly


            # self.txt.tag_add("sel", f"{start_line}.0", f"{end_line}.end")


        except Exception as e:


            print(f"Comment Err: {e}")


    def on_close(self):


        if self.mod and messagebox.askyesno("保存?", "内容已更改，是否保存？"): self.save()


        if self.g_cb: self.g_cb(self.root.geometry())


        self.root.destroy()





class DragManager:


    def __init__(self, app_instance):


        self.app = app_instance; self.root = app_instance.root; self.drag_start_x = 0; self.drag_start_y = 0


        self.drag_mode = None; self.drag_data = None; self.is_dragging = False; self.drag_window = None


    def on_start_drag(self, event, mode, data):


        self.drag_start_x = event.x_root; self.drag_start_y = event.y_root; self.drag_mode = mode; self.drag_data = data


        self.is_dragging = False; self.drag_window = None


    def on_drag_motion(self, event):


        if not self.drag_data: return False


        if not self.is_dragging:


            if abs(event.x_root - self.drag_start_x) > 15 or abs(event.y_root - self.drag_start_y) > 15:


                self.is_dragging = True; self.create_drag_window(event); return True


        else:


            if self.drag_window: self.drag_window.geometry(f"+{event.x_root+10}+{event.y_root+10}")


            return True


        return False


    def create_drag_window(self, event):


        # 拖拽时，如果是文件拖拽，可能跨窗口，最好以root为parent


        self.drag_window = tk.Toplevel(self.root); self.drag_window.overrideredirect(True)


        self.drag_window.attributes('-alpha', 0.6); self.drag_window.attributes('-topmost', True) 


        text = ""


        if self.drag_mode == 'file': text = os.path.basename(self.drag_data)


        elif self.drag_mode == 'button':


            r, c = self.drag_data


            btn_data = self.app.grid_config.get_btn_data(r, c, page=self.app.current_page_index if c < 10 else 0)


            display_text = btn_data.get('text')


            if not display_text and btn_data.get('script'): display_text = os.path.basename(btn_data['script'])


            text = display_text if display_text else f"按钮 [{r+1},{c+1}]"


        lbl = tk.Label(self.drag_window, text=text, bg="#007AFF", fg="white", font=("Segoe UI", 10)); lbl.pack(); self.drag_window.geometry(f"+{event.x_root+10}+{event.y_root+10}")


    def on_stop_drag(self, event):


        action_taken = 'none'


        if self.is_dragging:


            if self.drag_window: self.drag_window.destroy(); self.drag_window = None


            x, y = event.x_root, event.y_root


            try:


                # 0. Check modifiers


                is_ctrl = (event.state & 0x0004) or (ctypes.windll.user32.GetAsyncKeyState(0x11) & 0x8000)


                is_shift = (event.state & 0x0001) or (ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000)





                # 1. Check if dropped on Script Window Treeview (File Move/Copy)


                tree = getattr(self.app, 'dir_tree', None)


                tree_drop_handled = False


                


                if self.drag_mode == 'file' and tree and tree.winfo_exists() and tree.winfo_viewable():


                     tx, ty, tw, th = tree.winfo_rootx(), tree.winfo_rooty(), tree.winfo_width(), tree.winfo_height()


                     if tx <= x <= tx + tw and ty <= y <= ty + th:


                         try:


                             item_id = tree.identify_row(y - ty)


                             if item_id:


                                 target_dir = tree.item(item_id, 'values')[0]


                                 if os.path.isdir(target_dir):


                                     src_path = self.drag_data


                                     fname = os.path.basename(src_path); dest_path = os.path.join(target_dir, fname)


                                     


                                     if os.path.normpath(os.path.dirname(src_path)) == os.path.normpath(target_dir):


                                         pass # Same folder, ignore


                                     else:


                                         op_name = "复制" if is_ctrl else "移动"


                                         if os.path.exists(dest_path):


                                             if not messagebox.askyesno("覆盖确认", f"目标已存在: {fname}\n确认覆盖?"):


                                                 return 'cancelled'


                                         


                                         try:


                                             if is_ctrl: shutil.copy2(src_path, dest_path)


                                             else: shutil.move(src_path, dest_path)


                                             


                                             self.app.update_status_bar(f"✅ 已{op_name}: {fname}")


                                             self.app.refresh_file_list() # Refresh current view if moved away


                                             # Refresh drag source UI logic is handled by refresh_file_list


                                         except Exception as e:


                                             messagebox.showerror("操作失败", str(e))


                                     


                                     tree_drop_handled = True


                                     action_taken = 'file_op'


                         except Exception as e: print(f"Tree Drop Logic Error: {e}")





                if tree_drop_handled: 


                    self.is_dragging = False; self.drag_mode = None; self.drag_data = None


                    return action_taken





                if tree_drop_handled: 


                    self.is_dragging = False; self.drag_mode = None; self.drag_data = None


                    return action_taken





                # 1.5 Check if dropped on File Grid (Duplicate File)


                file_grid = getattr(self.app, 'grid_canvas', None)


                if self.drag_mode == 'file' and file_grid and file_grid.winfo_exists() and file_grid.winfo_viewable():


                     gx, gy, gw, gh = file_grid.winfo_rootx(), file_grid.winfo_rooty(), file_grid.winfo_width(), file_grid.winfo_height()


                     # If dropped anywhere inside the file grid area


                     if gx <= x <= gx + gw and gy <= y <= gy + gh:


                         # Only if Ctrl is held (Copy)


                         if is_ctrl:


                             src_path = self.drag_data


                             dirname = os.path.dirname(src_path)


                             


                             # Ensure source is in current dir (should be, but check)


                             current_view_dir = self.app.scripts_dir_var.get()


                             if os.path.normpath(dirname) == os.path.normpath(current_view_dir):


                                 fname = os.path.basename(src_path)


                                 base, ext = os.path.splitext(fname)


                                 


                                 # Generate new name: filename - 副本.txt, filename - 副本 (2).txt, etc.


                                 new_name = f"{base} - 副本{ext}"


                                 counter = 2


                                 while os.path.exists(os.path.join(dirname, new_name)):


                                     new_name = f"{base} - 副本 ({counter}){ext}"


                                     counter += 1


                                     


                                 dest_path = os.path.join(dirname, new_name)


                                 try:


                                     shutil.copy2(src_path, dest_path)


                                     self.app.update_status_bar(f"✅ 已创建副本: {new_name}")


                                     self.app.refresh_file_list()


                                     action_taken = 'copied'


                                 except Exception as e:


                                     messagebox.showerror("复制失败", str(e))





                # 1.8 Check if dropped on Script Editor (Insert Call)


                target_widget = self.root.winfo_containing(x, y)


                if target_widget and self.drag_mode == 'button':


                    for editor in self.app.open_editors.values():


                        if not editor.root.winfo_exists(): continue


                        # Check if dropped on the Text widget of an editor


                        if target_widget == editor.txt:


                            r, c = self.drag_data


                            page = self.app.current_page_index if c < 10 else 0


                            btn_data = self.app.grid_config.get_btn_data(r, c, page=page)


                            script_path = btn_data.get('script')


                            


                            if script_path:


                                try:


                                    # Convert screen coordinates to widget relative


                                    rel_x = x - editor.txt.winfo_rootx()


                                    rel_y = y - editor.txt.winfo_rooty()


                                    # Get index at position


                                    insert_index = editor.txt.index(f"@{rel_x},{rel_y}")


                                    


                                    # Insert Call statement


                                    # Add quotes if needed, though engine handles both


                                    code_line = f'Call "{script_path}"\n'


                                    editor.txt.insert(insert_index, code_line)


                                    editor.mark()


                                    self.app.update_status_bar(f"✅ 已插入调用: {os.path.basename(script_path)}")


                                    action_taken = 'inserted_call'


                                except Exception as e:


                                    print(f"Insert Call Error: {e}")


                            break


                            


                if action_taken == 'inserted_call':


                     self.is_dragging = False; self.drag_mode = None; self.drag_data = None


                     return action_taken





                # 2. Existing Button Drop Logic


                # 判断落在哪个窗口（主窗口还是脚本窗口）


                # 这里只处理落入主窗口的按钮区域


                target_widget = self.root.winfo_containing(x, y); target_rc = None


                if target_widget:


                    for (r, c), btn in self.app.grid_buttons.items():


                        if target_widget == btn: target_rc = (r, c); break


                if target_rc:


                    tr, tc = target_rc


                    if self.drag_mode == 'file': self.app.handle_internal_drop(tr, tc, self.drag_data); action_taken = 'assigned'


                    elif self.drag_mode == 'button':


                        sr, sc = self.drag_data


                        if (sr, sc) != (tr, tc):


                            if is_ctrl:


                                pass # Cancel Ctrl Drag


                            elif is_shift:


                                self.app.swap_grid_buttons(sr, sc, tr, tc)


                                action_taken = 'swapped'


                            else:


                                self.app.copy_grid_button(sr, sc, tr, tc)


                                action_taken = 'copied'


                else: 


                     # [NEW] Drop outside window -> Delete


                     if self.drag_mode == 'button':


                         # 防止手抖误操作：如果拖拽距离很短 (< 50px)，不认为是删除


                         dist = ((x - self.drag_start_x)**2 + (y - self.drag_start_y)**2)**0.5


                         if dist > 50:


                             sr, sc = self.drag_data


                             self.app.clear_btn_config(sr, sc)


                             action_taken = 'cleared'


            except Exception as e: print(f"Drop Err: {e}")


        self.is_dragging = False; self.drag_mode = None; self.drag_data = None


        return action_taken





# --- 网格配置管理器 (INI) ---


class GridConfig:


    def __init__(self):


        self.config = configparser.ConfigParser(); self.load()


    def load(self):


        if os.path.exists(GRID_INI_FILE): self.config.read(GRID_INI_FILE, encoding='utf-8')


    def save(self):


        with open(GRID_INI_FILE, 'w', encoding='utf-8') as f: self.config.write(f)


    def _get_section_name(self, row, col, page):


        if col >= 10: return f"Btn_{row}_{col}" 


        # [NEW] Column 8 (9th column) is global/independent of pages


        if col == 8: return f"Btn_{row}_{col}"


        if page == 0: return f"Btn_{row}_{col}"


        return f"P{page}_Btn_{row}_{col}"


    def get_btn_data(self, row, col, page=0):


        section = self._get_section_name(row, col, page)


        if self.config.has_section(section):


            return {


                'script': self.config.get(section, 'script', fallback=""),


                'image': self.config.get(section, 'image', fallback=""),


                'text': self.config.get(section, 'text', fallback=""),


                'bold': self.config.get(section, 'bold', fallback="1"), 


                'text_color': self.config.get(section, 'text_color', fallback="#333333") 


            }


        return {'script': "", 'image': "", 'text': "", 'bold': "1", 'text_color': "#333333"}


    def set_btn_data(self, row, col, page=0, script=None, image=None, text=None, bold=None, text_color=None):


        section = self._get_section_name(row, col, page)


        if not self.config.has_section(section): self.config.add_section(section)


        if script is not None: self.config.set(section, 'script', script)


        if image is not None: self.config.set(section, 'image', image)


        if text is not None: self.config.set(section, 'text', text)


        if bold is not None: self.config.set(section, 'bold', '1' if bold else '0') 


        if text_color is not None: self.config.set(section, 'text_color', text_color) 


        self.save()


    def swap_data(self, r1, c1, r2, c2, page=0):


        sec1 = self._get_section_name(r1, c1, page); sec2 = self._get_section_name(r2, c2, page)


        def get_all(sec):


            if not self.config.has_section(sec): return {}


            return dict(self.config.items(sec))


        data1 = get_all(sec1); data2 = get_all(sec2)


        self.config.remove_section(sec1); self.config.remove_section(sec2)


        self.config.add_section(sec1); 


        for k, v in data2.items(): self.config.set(sec1, k, v)


        self.config.add_section(sec2)


        for k, v in data1.items(): self.config.set(sec2, k, v)


        self.save()


    def get_panel_name(self, index):


        defaults = {0: "日常", 1: "备用", 2: "战斗", 3: "其他"}


        fallback = defaults.get(index, f"面板{index+1}")


        if not self.config.has_section("PanelNames"): return fallback


        return self.config.get("PanelNames", f"p{index}", fallback=fallback)


    def set_panel_name(self, index, name):


        if not self.config.has_section("PanelNames"): self.config.add_section("PanelNames")


        self.config.set("PanelNames", f"p{index}", name)


        self.save()


        


    def get_panel_count(self):


        return self.config.getint("PanelNames", "count", fallback=4) if self.config.has_section("PanelNames") else 4


        


    def set_panel_count(self, count):


        if not self.config.has_section("PanelNames"): self.config.add_section("PanelNames")


        self.config.set("PanelNames", "count", str(count))


        self.save()


        


    def add_panel(self):


        count = self.get_panel_count()


        self.set_panel_count(count + 1)


        self.set_panel_name(count, f"新面板{count+1}")


        return count


        


    def delete_panel(self, idx):


        count = self.get_panel_count()


        if count <= 1: return # Cannot delete the last one


        


        # Shift panel names


        for i in range(idx, count - 1):


            name = self.get_panel_name(i + 1)


            self.set_panel_name(i, name)


            


        if self.config.has_option("PanelNames", f"p{count-1}"):


            self.config.remove_option("PanelNames", f"p{count-1}")


            


        # Shift button data


        for i in range(idx, count - 1):


            for r in range(5):


                for c in range(9):


                    sec_to = self._get_section_name(r, c, i)


                    sec_from = self._get_section_name(r, c, i + 1)


                    


                    if self.config.has_section(sec_to): self.config.remove_section(sec_to)


                    if self.config.has_section(sec_from):


                        if not self.config.has_section(sec_to): self.config.add_section(sec_to)


                        for k, v in self.config.items(sec_from):


                            self.config.set(sec_to, k, v)


                            


        # Clear the last panel's data


        for r in range(5):


            for c in range(9):


                sec_last = self._get_section_name(r, c, count - 1)


                if self.config.has_section(sec_last):


                    self.config.remove_section(sec_last)


                    


        self.set_panel_count(count - 1)


        self.save()





# --- 独立的脚本管理窗口类 ---


# --- 独立的脚本管理窗口类 ---


class ScriptManagerWindow(tk.Toplevel):


    def __init__(self, app_instance):


        super().__init__(app_instance.root)


        self.app = app_instance


        self.title("脚本文件管理")


        


        # [修改] 使用配置中保存的 geometry，如果不存在则使用默认


        try:


            self.geometry(app_instance.script_manager_geometry)


        except:


            self.geometry("1000x800")


        


        # --- [新增] 设置窗口图标 ---


        try:


            icon_path = os.path.join(BASE_DIR, "anjian20251216.ico")


            if os.path.exists(icon_path):


                self.iconbitmap(icon_path)


        except Exception as e:


            print(f"脚本窗口图标加载失败: {e}")


        # ------------------------





        self.protocol("WM_DELETE_WINDOW", self.hide_window) # 关闭时只隐藏





        # 将原 setup_ui 的顶部部分逻辑移到这里


        top_bar = ttk.Frame(self, padding="10 10 10 0", style='Glass.TFrame'); top_bar.pack(fill=tk.X)


        self.app.btn_rec = ttk.Button(top_bar, text="🔴 录制 (F12)", command=self.app.toggle_record, style='Accent.TButton'); self.app.btn_rec.pack(side=tk.LEFT)


        


        ttk.Button(top_bar, text="🔄 刷新列表", command=self.app.refresh_file_list).pack(side=tk.LEFT, padx=10)


        ttk.Button(top_bar, text="📂 打开文件", command=self.app.open_external_file).pack(side=tk.LEFT, padx=2)





        # [移除] 窗口置顶已移至主界面


        # ttk.Checkbutton(top_bar, text="窗口置顶", variable=self.app.topmost_var).pack(side=tk.RIGHT)





        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)


        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)





        left_frame = ttk.Frame(paned, style='Glass.TFrame'); paned.add(left_frame, weight=1)


        ttk.Label(left_frame, text="目录结构", font=('Microsoft YaHei UI', 11, 'bold')).pack(anchor=tk.W)


        tree_scroll = ttk.Scrollbar(left_frame); tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)


        # 将创建的 tree 赋值给 app 实例，以便兼容原代码逻辑


        self.app.dir_tree = ttk.Treeview(left_frame, show='tree', yscrollcommand=tree_scroll.set)


        self.app.dir_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); tree_scroll.config(command=self.app.dir_tree.yview)


        self.app.dir_tree.bind('<<TreeviewOpen>>', self.app.on_tree_open); self.app.dir_tree.bind('<<TreeviewSelect>>', self.app.on_tree_select)





        right_frame = ttk.Frame(paned, style='Glass.TFrame'); paned.add(right_frame, weight=3)


        path_box = ttk.Frame(right_frame); path_box.pack(fill=tk.X, pady=(0,5))


        ttk.Label(path_box, text="当前路径:", font=('Microsoft YaHei UI', 11, 'bold')).pack(side=tk.LEFT)


        ttk.Entry(path_box, textvariable=self.app.scripts_dir_var, state='readonly').pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)


        


        grid_outer = tk.Frame(right_frame, bd=1, relief="flat", bg='#FFFFFF'); grid_outer.pack(fill=tk.BOTH, expand=True)


        self.app.grid_vsb = ttk.Scrollbar(grid_outer, orient="vertical"); self.app.grid_vsb.pack(side=tk.RIGHT, fill=tk.Y)


        # 将创建的 canvas 赋值给 app 实例


        self.app.grid_canvas = tk.Canvas(grid_outer, bg='#FFFFFF', highlightthickness=0, yscrollcommand=self.app.grid_vsb.set, takefocus=1)


        self.app.grid_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); self.app.grid_vsb.config(command=self.app.grid_canvas.yview)


        


        self.app.grid_frame = tk.Frame(self.app.grid_canvas, bg='#FFFFFF')


        self.app.grid_canvas_window = self.app.grid_canvas.create_window((0, 0), window=self.app.grid_frame, anchor="nw")


        


        self.app.grid_frame.bind("<Configure>", self.app.on_frame_configure); self.app.grid_canvas.bind("<Configure>", self.app.on_canvas_configure)


        self.app.grid_canvas.bind_all("<MouseWheel>", self.app.on_mousewheel)


        


        # 绑定事件支持搜索


        self.app.grid_canvas.bind("<Button-1>", lambda e: self.app.grid_canvas.focus_set())


        self.app.grid_canvas.bind("<Key>", self.app.handle_quick_search)


        self.bind("<Key>", self.app.handle_quick_search) # 给窗口也绑定





        btn_bar = ttk.Frame(right_frame, padding="0 5 0 0"); btn_bar.pack(fill=tk.X, side=tk.BOTTOM)


        for txt, cmd in [("▶ 回放", self.app.play_sel), ("✏ 编辑", self.app.edit_sel), ("📛 重命名", self.app.rename_sel), ("❌ 删除", self.app.del_sel), ("📁 新建文件夹", self.app.create_new_folder)]:


            ttk.Button(btn_bar, text=txt, command=cmd).pack(side=tk.LEFT, padx=5)





    def hide_window(self):


        self.withdraw()





# --- 悬浮停止按钮窗口 ---


class FloatingStopWindow(tk.Toplevel):


    def __init__(self, parent, on_stop_callback, initial_pos=None):


        super().__init__(parent.root)


        self.on_stop_callback = on_stop_callback


        self.overrideredirect(True)


        self.attributes('-topmost', True)


        self.attributes('-alpha', 0.8)


        


        # 默认位置 or 上次位置


        geo = initial_pos if initial_pos else "+100+50"


        try: self.geometry(geo)


        except: self.geometry("+100+50")





        self.configure(bg="#FF4444")


        


        # 拖拽相关


        self.offset_x = 0


        self.offset_y = 0





        # UI


        frame = tk.Frame(self, bg="#FF4444", bd=2, relief="raised")


        frame.pack(fill=tk.BOTH, expand=True)





        # [Modified] Increased font size and padding


        lbl = tk.Label(frame, text="⏹ 停止录制", font=('Microsoft YaHei UI', 20, 'bold'), bg="#FF4444", fg="white", cursor="hand2")


        lbl.pack(padx=20, pady=10)


        


        # 绑定事件


        lbl.bind("<Button-1>", self.on_click_stop)


        # 整个窗口和Label都支持拖拽


        self.bind("<Button-1>", self.on_start_drag)


        self.bind("<B1-Motion>", self.on_drag)


        self.bind("<ButtonRelease-1>", self.on_stop_drag)


        lbl.bind("<Button-1>", self.on_start_drag, add="+")


        lbl.bind("<B1-Motion>", self.on_drag, add="+")


        lbl.bind("<ButtonRelease-1>", self.on_stop_drag, add="+")


        


        # 单击停止优先于拖拽，区分一下：如果拖拽距离很小，则是点击


        self.drag_start_pos = (0, 0)


        self.is_dragging = False





    def on_click_stop(self, event):


        # 如果是拖拽结束的释放，不触发


        if not self.is_dragging: 


             self.on_stop_callback()





    def on_start_drag(self, event):


        self.offset_x = event.x


        self.offset_y = event.y


        self.drag_start_pos = (self.winfo_rootx(), self.winfo_rooty())


        self.is_dragging = False





    def on_drag(self, event):


        x = self.winfo_x() + event.x - self.offset_x


        y = self.winfo_y() + event.y - self.offset_y


        self.geometry(f"+{x}+{y}")


        # 如果移动距离超过一定阈值，视为拖拽


        if abs(self.winfo_rootx() - self.drag_start_pos[0]) > 5 or abs(self.winfo_rooty() - self.drag_start_pos[1]) > 5:


            self.is_dragging = True





    def on_stop_drag(self, event):


        # 如果没有发生明显拖拽，且点击的是Label（通过tag或判断），执行Stop


        # 这里简化：已经在 on_click_stop 处理了点击，这里只负责保存位置


        if self.is_dragging:


            # save position logic handled by App via polling or explicit save? 


            # Better let App know or App query this window.


            # actually we can just update parent's config directly if we want, or rely on App on_close/save


            pass


        elif event.widget.winfo_class() == 'Label': # 只有点击Label才触发停止，点击背景作为拖拽句柄


             self.on_stop_callback()


        self.is_dragging = False





    def on_stop_drag(self, event):


        # [NEW] Save position to App config whenever drag stops


        try:


             geo_parts = self.geometry().split('+')


             app = self.master.master if hasattr(self.master, 'master') else None # self.master is root, root.master is None usually. Wait, parent passed is App instance? No, parent passed is App.


             # Actually, creating FloatingStepWindow(self.app, ...)


             # So self.master is self.app.root (Tk instance)


             # We can't easily access App instance from here unless passed or found.


             # Let's rely on the callback or pass App instance.


             # Ah, in ScriptEditor we passed `self.app`.


             pass


        except: pass





class FloatingStepWindow(tk.Toplevel):


    def __init__(self, app_instance, on_next_callback, on_stop_callback, initial_pos=None):


        super().__init__(app_instance.root)


        self.app = app_instance # Store App reference


        self.on_next_callback = on_next_callback


        self.on_stop_callback = on_stop_callback


        self.overrideredirect(True)


        self.attributes('-topmost', True)


        self.attributes('-alpha', 0.9)


        


        # Default position


        geo = initial_pos if initial_pos else "+100+100"


        try: self.geometry(geo)


        except: self.geometry("+100+100")





        self.configure(bg="#333333")


        


        # Drag Logic


        self.offset_x = 0; self.offset_y = 0; self.is_dragging = False; self.drag_start_pos = (0,0)





        # UI


        frame = tk.Frame(self, bg="#333333", bd=2, relief="raised")


        frame.pack(fill=tk.BOTH, expand=True)





        # Start/Pause Button


        self.btn_next = tk.Label(frame, text="▶ 开始", font=('Microsoft YaHei UI', 16, 'bold'), bg="#4CAF50", fg="white", cursor="hand2", padx=15, pady=8)


        self.btn_next.pack(side=tk.LEFT, padx=5, pady=5)


        self.btn_next.bind("<Button-1>", self.on_click_next)


        


        # Stop Button


        btn_stop = tk.Label(frame, text="⏹ 终止", font=('Microsoft YaHei UI', 16, 'bold'), bg="#FF4444", fg="white", cursor="hand2", padx=15, pady=8)


        btn_stop.pack(side=tk.LEFT, padx=5, pady=5)


        btn_stop.bind("<Button-1>", self.on_click_stop)





        # Drag Hint


        tk.Label(frame, text="(右键拖动窗口)", font=('Microsoft YaHei UI', 8), bg="#333333", fg="#AAAAAA").pack(side=tk.BOTTOM, pady=2)





        # Bind drag events (Use Right Mouse Button to avoid conflict with script Left Clicks)


        for widget in [self, frame]:


            widget.bind("<Button-3>", self.on_start_drag)


            widget.bind("<B3-Motion>", self.on_drag)


            widget.bind("<ButtonRelease-3>", self.on_stop_drag)





    def update_btn_state(self, is_running):


        if is_running: self.btn_next.config(text="⏸ 暂停", bg="#FF9800")


        else: self.btn_next.config(text="▶ 开始", bg="#4CAF50")





    def on_click_next(self, event):


        self.on_next_callback()





    def on_click_stop(self, event):


        self.on_stop_callback()





    def on_start_drag(self, event):


        self.offset_x = event.x


        self.offset_y = event.y





    def on_drag(self, event):


        x = self.winfo_x() + event.x - self.offset_x


        y = self.winfo_y() + event.y - self.offset_y


        self.geometry(f"+{x}+{y}")


    


    def on_stop_drag(self, event):


        # [NEW] Check if just a click or real drag? 


        # Actually just save position


        try:


             geo_parts = self.geometry().split('+')


             self.app.floating_step_pos = f"+{geo_parts[1]}+{geo_parts[2]}"


        except: pass








# --- 主程序 ---


class App:


    def __init__(self, root):


        self.root = root


        style = ttk.Style(); style.theme_use('clam')


        self.BG = '#F0F3F7'; self.FG = '#333333'; self.ACCENT = '#007AFF'


        root.configure(bg=self.BG)


        self.pixel_ref = tk.PhotoImage(width=1, height=1)


        main_font = ('Microsoft YaHei UI', 11)


        style.configure('.', font=main_font, background=self.BG)


        style.configure('TLabel', background='#FFFFFF', foreground=self.FG)


        style.configure('Glass.TFrame', background='#FFFFFF', borderwidth=0)


        style.configure('Accent.TButton', background=self.ACCENT, foreground='white', font=('Microsoft YaHei UI', 11, 'bold'))


        style.map('Accent.TButton', background=[('active', '#55C2FF')])


        


        # [NEW] 工具栏第二排按钮样式 (Teal/Info)


        style.configure('Tool.TButton', background='#17A2B8', foreground='white', font=('Microsoft YaHei UI', 10))


        style.map('Tool.TButton', background=[('active', '#138496')])





        style.configure("Treeview", rowheight=50, font=main_font)


        


        self.root.title("anjian2025 - 主控台")


        # [修改] 调整默认主窗口大小，因为现在非常紧凑了


        self.root.geometry("1450x650") 








        # --- [新增] 设置主窗口图标 ---


        try:


            icon_path = os.path.join(BASE_DIR, "anjian20251216.ico")


            if os.path.exists(icon_path):


                self.root.iconbitmap(icon_path)


        except Exception as e:


            print(f"主窗口图标加载失败: {e}")


        # ---------------------------





        self.scripts_dir_var = tk.StringVar()


        self.loop_var = tk.IntVar(value=1); self.speed_var = tk.DoubleVar(value=1.0)


        #self.topmost_var = tk.BooleanVar(value=False); self.topmost_var.trace_add('write', self.toggle_topmost)


        self.hotkeys_enabled_var = tk.IntVar(value=1); self.btn_font_size_var = tk.IntVar(value=8)


        self.current_editing_btn = None 


        self.loop_key_buffer = ""; self.loop_key_time = 0





        self.editor_geometry = "1000x800"; self.hotkey_editor_geometry = "800x600"; self.grid_dialog_geometry = None


        self.btn_config_geometry = "500x400"


        self.script_manager_geometry = "1000x800" # [新增] 脚本管理窗口默认大小


        


        self.current_page_index = 0; self.panel_buttons = []; self.all_items_cache = [] 


        self.floating_panels = {} # {page_index: FloatingPanelWindow_instance}


        


        self.sched_h_var = tk.StringVar(value="00")


        self.sched_m_var = tk.StringVar(value="00")


        self.sched_s_var = tk.StringVar(value="00")


        self.sched_ms_var = tk.StringVar(value="000")


        self.sched_enabled_var = tk.BooleanVar(value=False)


        self.last_sched_trigger_time = None


        self.sched_after_id = None


        self.sched_target_text = None





        self.engine = KSEngine(self.update_status_bar, self.show_error_dialog, self.handle_msgbox_request) 


        self.recorder = Recorder(); self.grid_config = GridConfig(); self.drag_manager = DragManager(self)


        


        self.is_executing = False


        self.grid_buttons = {}; self.grid_images = {}; self.capture_window = None


        self.is_holding_btn = False; self.long_press_triggered = False; self.current_holding_btn = None


        self.open_editors = {}; self.search_buffer = ""; self.last_key_time = 0


        self.selected_label = None; self.selected_filename = None; self.file_widgets = {} 


        self.hotkey_data = []; self.custom_hotkey_listener = None; self.hotkey_win = None 


        self.recording_target = None # [NEW] target (r, c) for quick record 


        self.global_hotkey_listener = None; self.global_mouse_listener = None


        self.long_press_timer = None # [NEW] Timer for long press edit





        # [新增] 悬浮搜索框变量


        self.float_search_var = tk.StringVar()


        self.float_search_var.trace_add("write", self.on_search_update) 


        self.float_search_frame = None


        self.float_search_entry = None


        


        self.script_window = None # 脚本管理窗口实例





        # [NEW] 记录正在运行的脚本路径实现 Start/Stop Toggle


        self.current_executing_path = None


        


        # [NEW] 悬浮停止按钮位置


        self.floating_stop_pos = None


        self.floating_stop_win = None





        self.root.bind_all("<KeyPress-z>", self.on_z_keypress)
        self.root.bind_all("<KeyPress-Z>", self.on_z_keypress)

        self.load_config() 

        self.setup_hotkeys()


        self.setup_ui() 


        # setup_ui 内部会初始化 script_window，所以这里可以直接调用 setup_floating_search


        self.setup_floating_search() 


        self.update_hotkey_state() 


        self.refresh_file_list()


        self.load_drives_into_tree()


        self.root.after(100, lambda: self.sync_tree_to_path(self.scripts_dir_var.get()))


        self.root.after(1000, self.check_scheduled_task) 


        self.root.protocol("WM_DELETE_WINDOW", self.on_close)





        if not check_admin():


            self.root.after(1000, lambda: messagebox.showwarning("⚠️ 权限警告", "请务必以【管理员身份】运行此程序！\n否则游戏内 F12 无法检测。"))

    def on_btn_enter(self, event, r, c, page_index=None):
        page = page_index if page_index is not None else (self.current_page_index if c < 10 else 0)
        self.currently_hovered_btn = (r, c, page)

    def on_btn_leave(self, event, r, c, page_index=None):
        page = page_index if page_index is not None else (self.current_page_index if c < 10 else 0)
        if getattr(self, 'currently_hovered_btn', None) == (r, c, page):
            self.currently_hovered_btn = None

    def on_z_keypress(self, event):
        hovered = getattr(self, 'currently_hovered_btn', None)
        if hovered:
            r, c, page = hovered
            self.add_to_combined_execution(r, c, page)

    def add_to_combined_execution(self, src_r, src_c, src_page):
        src_data = self.grid_config.get_btn_data(src_r, src_c, page=src_page)
        if not src_data.get('script') and not src_data.get('text'):
            return

        target_r, target_c = None, None
        for r in range(4):
            for c in range(10, 12):
                data = self.grid_config.get_btn_data(r, c, page=0)
                if not data.get('script') and not data.get('text'):
                    target_r, target_c = r, c
                    break
            if target_r is not None:
                break
        
        if target_r is not None:
            self.grid_config.set_btn_data(target_r, target_c, page=0, **src_data)
            self.update_grid_button_ui(target_r, target_c, 0)
            self.update_status_bar(f"✅ 已加入组合执行区域: {src_data.get('text', '未命名')}", "green")
        else:
            self.update_status_bar("❌ 组合执行区域已满！", "red")

    def handle_msgbox_request(self, content, stop_event):


        def _show(): messagebox.showinfo("脚本消息", content); stop_event.set()


        self.root.after(0, _show)





    def update_status_bar(self, msg, color="black"):


        try: self.status_bar_label.config(text=msg, foreground=color)


        except: pass





    def update_run_status(self, msg, color="black"):


        pass





    def show_error_dialog(self, ln, msg, line, fn):


        res = [None]


        def popup(): res[0] = "stop" if messagebox.askyesno("Err", f"{fn} 行 {ln}\n{msg}\n停止?") else "skip"


        self.root.after(0, popup); 


        while res[0] is None: time.sleep(0.1)


        if self.engine.stop_signal: return "stop"


        return res[0]





    def toggle_record(self, event=None):


        if self.recorder.recording:


            self.recorder.stop()


            self.recorder.trim_last_click() # [NEW] Trim the stop button click


            self.update_status_bar("✅ 录制结束，脚本已保存", "black")


            self.update_run_status("✅ 录制完成", "black")


            


            # [NEW] 关闭悬浮停止窗口


            if self.floating_stop_win:


                try:


                    # Save position before destroying


                    geo_parts = self.floating_stop_win.geometry().split('+')


                    self.floating_stop_pos = f"+{geo_parts[1]}+{geo_parts[2]}"


                    self.floating_stop_win.destroy()


                except: pass


                self.floating_stop_win = None


            


            # [Fix] 如果有回调（比如来自编辑器），则直接将内容传回，不保存文件


            if getattr(self, 'on_record_finish_callback', None):


                 content = "\n".join(self.recorder.events)


                 self.on_record_finish_callback(content)


                 self.on_record_finish_callback = None


                 return





            if self.recording_target:


                r, c = self.recording_target


                t_str = str(int(time.time()))


                fname = f"Record_{r+1}_{c+1}_{t_str}.txt"


                d = self.scripts_dir_var.get()


                f = os.path.join(d, fname)


                try:


                    self.recorder.save(f)


                    self.refresh_file_list()


                    # auto bind


                    page = self.current_page_index if c < 10 else 0


                    self.grid_config.set_btn_data(r, c, page=page, script=f, text=fname)


                    self.update_grid_button_ui(r, c)


                    self.update_status_bar(f"已录制并绑定到 [{r+1},{c+1}]: {fname}")


                    if messagebox.askyesno("录制完成", f"录制已保存至 {fname} 并绑定。\n是否立刻编辑？"):


                         self.open_editor_window(f)


                except Exception as e:


                    messagebox.showerror("保存失败", str(e))


                self.recording_target = None


            else:


                # 弹窗询问保存路径


                initial_file = f"script_{int(time.time())}.txt"


                filepath = filedialog.asksaveasfilename(


                    initialdir=self.scripts_dir_var.get(),


                    initialfile=initial_file,


                    defaultextension=".txt",


                    filetypes=[("Text Files", "*.txt"), ("KS Scripts", "*.ks")]


                )


                if filepath:


                    self.recorder.save(filepath)


                    self.refresh_file_list()


                    messagebox.showinfo("成功", f"脚本已保存到:\n{filepath}")


        else:


            self.root.iconify() # 最小化主窗口


            self.recorder.start()


            self.update_status_bar("🔴 正在录制... (按F11暂停/F12停止)", "red")


            self.update_run_status("🔴 录制中", "red")


            


            # [NEW] 显示悬浮停止窗口


            if not self.floating_stop_win:


                self.floating_stop_win = FloatingStopWindow(self, self.toggle_record, self.floating_stop_pos)





    # [NEW] Quick record for button


    def start_record_for_btn(self, r, c):


        if self.recorder.recording:


             messagebox.showinfo("提示", "正在录制中，请先停止")


             return


        self.recording_target = (r, c)


        self.toggle_record()





    # --- [新增] 打开外部文件功能 ---


    def open_external_file(self):


        f = filedialog.askopenfilename(


            title="打开脚本文件",


            initialdir=self.scripts_dir_var.get(),


            filetypes=[("脚本文件", "*.txt;*.ks;*.py"), ("所有文件", "*.*")]


        )


        if f:


            self.open_editor_window(f)





    # --- [新增] 坐标拾取功能 ---


    def pick_coordinate(self):


        self.root.iconify() # 最小化主窗口，方便看后面的


        def on_picked(x, y):


            self.root.deiconify()


            self.coord_label.config(text=f"{x}, {y}")


            # print(f"Picked: {x}, {y}")


        


        CoordinatePicker(self.root, on_picked)





    def copy_coordinates(self, event):


        txt = self.coord_label.cget("text")


        if txt and "----" not in txt:


            self.root.clipboard_clear()


            self.root.clipboard_append(txt)


            self.update_status_bar(f"✅ 坐标 {txt} 已复制", "green")


    # ----------------------------





    def open_editor_window(self, filepath):


        if not os.path.exists(filepath): return


        if filepath in self.open_editors and self.open_editors[filepath].root.winfo_exists(): self.open_editors[filepath].root.lift(); return


        def update_geom_cb(geom): self.editor_geometry = geom; self.save_settings()


        self.open_editors[filepath] = ScriptEditor(self.root, filepath, self.refresh_file_list, self.editor_geometry, update_geom_cb, app_instance=self)


    


    def toggle_topmost(self, *args): 


        # [修改] 置顶现在同时控制主窗口和脚本管理窗口


        is_top = self.topmost_var.get()


        self.root.attributes('-topmost', is_top)


        if self.script_window:


            self.script_window.attributes('-topmost', is_top)





    def open_script_manager(self):


        if self.script_window:


            if self.script_window.state() == 'normal':


                self.script_window.withdraw()


            else:


                self.script_window.deiconify()


                self.script_window.lift()





    def on_loop_combo_keypress(self, event, combo):


        if not event.char or not event.char.isdigit():


            return


        now = time.time()


        if now - self.loop_key_time > 0.7:


            self.loop_key_buffer = ""


        self.loop_key_time = now


        candidate = self.loop_key_buffer + event.char


        if candidate.startswith("0"):


            candidate = event.char


        value = int(candidate)


        if 1 <= value <= 12:


            self.loop_key_buffer = candidate


            combo.set(str(value))


            self.loop_var.set(value)


            try: combo.current(value - 1)


            except Exception: pass


        else:


            self.loop_key_buffer = event.char


            value = int(event.char)


            if 1 <= value <= 9:


                combo.set(str(value))


                self.loop_var.set(value)


                try: combo.current(value - 1)


                except Exception: pass


        return "break"



    def create_script_window(self):


        # 即使一开始不显示，也要创建，因为 dir_tree 和 grid_canvas 是必须存在的


        self.script_window = ScriptManagerWindow(self)


        self.script_window.withdraw() # 初始隐藏





    # [修改] UI 设置，完全移除主窗口上半部分，只保留控制条和网格


    def setup_ui(self):


        # 1. 先创建隐藏的脚本窗口


        self.create_script_window()





        # 2. 顶部控制条 (直接放在主窗口顶部)


        ctrl_line_top = ttk.Frame(self.root, padding="10 10 10 5")


        ctrl_line_top.pack(side=tk.TOP, fill=tk.X)


        


        # [新增] 脚本管理按钮


        ttk.Button(ctrl_line_top, text="📂 脚本", command=self.open_script_manager).pack(side=tk.LEFT, padx=(0, 5))





        ttk.Button(ctrl_line_top, text="⌨️ 快捷键...", command=self.open_hotkey_editor).pack(side=tk.LEFT)


        tk.Button(ctrl_line_top, text="🛑 停止 (F12)", bg="#FF4444", fg="white", font=('Microsoft YaHei UI', 9, 'bold'), command=self.force_stop).pack(side=tk.LEFT, padx=5)


        ttk.Separator(ctrl_line_top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)


        # [修改] 移除倍率，循环改为下拉菜单 (1-12)，控件放大


        # [NEW] 设置下拉列表的字体大小 (全局生效)


        self.root.option_add('*TCombobox*Listbox.font', ('Microsoft YaHei UI', 14))


        


        ttk.Label(ctrl_line_top, text="循环:").pack(side=tk.LEFT, padx=(10, 2))


        loop_combo = ttk.Combobox(ctrl_line_top, textvariable=self.loop_var, values=[str(i) for i in range(1, 13)], width=5, font=('Microsoft YaHei UI', 14), state="readonly", height=20)


        loop_combo.pack(side=tk.LEFT, ipady=3) # ipady增加高度


        loop_combo.bind("<KeyPress>", lambda e, combo=loop_combo: self.on_loop_combo_keypress(e, combo))


        ttk.Label(ctrl_line_top, text="字号:").pack(side=tk.LEFT, padx=(10, 2))


        font_combo = ttk.Combobox(ctrl_line_top, textvariable=self.btn_font_size_var, values=[8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 36], width=3, state="readonly")


        font_combo.pack(side=tk.LEFT); font_combo.bind("<<ComboboxSelected>>", self.on_font_scale_change)





        # [新增] 窗口置顶 (移到主界面)


        #ttk.Checkbutton(ctrl_line_top, text="置顶", variable=self.topmost_var).pack(side=tk.LEFT, padx=(10, 0))





        # [新增] 坐标拾取


        ttk.Button(ctrl_line_top, text="坐标", command=self.pick_coordinate, width=6).pack(side=tk.LEFT, padx=(10, 2))


        self.coord_label = tk.Label(ctrl_line_top, text="----, ----", bg="white", fg="blue", cursor="hand2", font=('Consolas', 10), relief="sunken", padx=5)


        self.coord_label.pack(side=tk.LEFT, padx=2)


        self.coord_label.bind("<Button-1>", self.copy_coordinates)


        


        # [NEW] Top Status Indicator (Removed as requested)





        # 3. 状态栏 (放在最底部)


        status_frame = ttk.Frame(self.root, padding=3, relief=tk.SUNKEN)


        status_frame.pack(side=tk.BOTTOM, fill=tk.X)


        self.status_bar_label = ttk.Label(status_frame, text="✅ 系统就绪 (遇到卡死请把鼠标猛甩到左上角停止)", font=('Segoe UI', 10))


        self.status_bar_label.pack(side=tk.LEFT, padx=5)





        # 4. 任务网格 (填充剩余的所有空间)


        grid_container = ttk.Frame(self.root, padding="5 0 5 5")


        grid_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True) # 紧接顶部控制条，占满剩余空间





        left_area = ttk.LabelFrame(grid_container, text="单任务区域 (9x5) - 左键切换/右键编辑", padding=5)


        left_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))





        right_area = ttk.LabelFrame(grid_container, text="组合", padding=5)


        right_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)





        BTN_SIZE = 116 


        current_font = ('Microsoft YaHei UI', self.btn_font_size_var.get())





        self.panel_bar = tk.Frame(left_area, bg=self.BG)


        self.panel_bar.grid(row=0, column=0, columnspan=9, sticky="ew", pady=(0, 5))


        


        self.refresh_panel_tabs()








        for c in range(9): left_area.columnconfigure(c, weight=1)


        for r in range(5):


            for c in range(9):


                self.create_grid_button(left_area, r, c, BTN_SIZE, current_font, grid_row_offset=1)





        # [NEW] 定时模块移动到上方

        sched_frame = ttk.Frame(right_area)

        sched_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))

        

        ttk.Label(sched_frame, text="⏰").pack(side=tk.LEFT)

        cb_h = ttk.Combobox(sched_frame, textvariable=self.sched_h_var, values=[f"{i:02d}" for i in range(24)], width=3, state="readonly")

        cb_h.pack(side=tk.LEFT, padx=2)

        ttk.Label(sched_frame, text=":").pack(side=tk.LEFT)

        cb_m = ttk.Combobox(sched_frame, textvariable=self.sched_m_var, values=[f"{i:02d}" for i in range(60)], width=3, state="readonly")

        cb_m.pack(side=tk.LEFT, padx=2)

        ttk.Label(sched_frame, text=":").pack(side=tk.LEFT)

        cb_s = ttk.Combobox(sched_frame, textvariable=self.sched_s_var, values=[f"{i:02d}" for i in range(60)], width=3, state="readonly")

        cb_s.pack(side=tk.LEFT, padx=2)

        ttk.Label(sched_frame, text=".").pack(side=tk.LEFT)

        ttk.Entry(sched_frame, textvariable=self.sched_ms_var, width=4).pack(side=tk.LEFT, padx=2)

        ttk.Checkbutton(sched_frame, text="定时", variable=self.sched_enabled_var, command=self.toggle_scheduled_task).pack(side=tk.LEFT, padx=5)



        # 组合按钮下移
        btn_exec = tk.Button(right_area, text="▶ 组合执行", command=self.run_right_group_sequence, bg="#4CAF50", fg="white", borderwidth=1, height=3, font=('', 13, 'bold'))
        btn_exec.grid(row=1, column=0, sticky="ew", padx=(0, 2), pady=(5, 5))
        btn_exec.bind("<Configure>", lambda e: e.widget.config(wraplength=max(20, e.width - 8)))

        btn_clear = tk.Button(right_area, text="🗑️ 一键清空", command=self.clear_right_group, bg="#F44336", fg="white", borderwidth=1, height=3, font=('', 13, 'bold'))
        btn_clear.grid(row=1, column=1, sticky="ew", padx=(2, 0), pady=(5, 5))
        btn_clear.bind("<Configure>", lambda e: e.widget.config(wraplength=max(20, e.width - 8)))



        for c in range(2): right_area.columnconfigure(c, weight=1)

        for r in range(4): # Reduced to 2x4

            for c in range(10, 12):

                # Shift icons down by 3 rows

                self.create_grid_button(right_area, r, c, BTN_SIZE, current_font, grid_col_offset=-10, grid_row_offset=3)





    # [新增] 初始化悬浮搜索框，现在挂载在 script_window 上


    def setup_floating_search(self):


        if not self.script_window: return


        # 创建一个 Frame 容器，黄色边框醒目一点


        self.float_search_frame = tk.Frame(self.script_window, bg="#FFD700", padx=2, pady=2)


        # 内部放置 Entry


        self.float_search_entry = tk.Entry(self.float_search_frame, textvariable=self.float_search_var, width=20, font=('Segoe UI', 12))


        self.float_search_entry.pack()


        


        # 绑定 Esc 键关闭搜索框


        self.float_search_entry.bind("<Escape>", self.hide_floating_search)


        # 绑定回车键关闭（可选）


        self.float_search_entry.bind("<Return>", self.hide_floating_search)


        


        # 初始状态隐藏


        self.float_search_frame.place_forget()





    # [新增] 处理快速搜索按键


    def handle_quick_search(self, event):


        # 搜索是在脚本窗口进行的，所以判断脚本窗口的焦点


        if not self.script_window.winfo_ismapped(): return





        focus_w = self.script_window.focus_get()


        # 判定逻辑：如果 focus 是 grid_canvas 或者 某个文件Label


        is_grid_focus = (focus_w == self.grid_canvas)


        if not is_grid_focus and isinstance(focus_w, tk.Label):


            if focus_w.master == self.grid_frame:


                is_grid_focus = True


        


        if self.float_search_frame.winfo_ismapped():


            return 





        if not is_grid_focus:


            return





        # 忽略控制键


        if event.keysym in ['Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Shift_L', 'Shift_R', 'F1', 'F5', 'F12', 'Delete', 'BackSpace', 'Escape']:


            return





        # 确保是可打印字符


        if len(event.char) == 1 and event.char.isprintable():


            # 获取鼠标位置 (相对于脚本窗口)


            mx = self.script_window.winfo_pointerx() - self.script_window.winfo_rootx()


            my = self.script_window.winfo_pointery() - self.script_window.winfo_rooty()


            


            # 清空并设置搜索内容


            self.float_search_var.set("") 


            self.float_search_frame.place(x=mx + 10, y=my + 10)


            self.float_search_entry.focus_set()


            


            self.float_search_entry.insert(0, event.char)


            self.on_search_update()





    # [新增] 隐藏悬浮搜索框


    def hide_floating_search(self, event=None):


        self.float_search_frame.place_forget()


        self.float_search_var.set("") # 清空搜索内容，恢复列表


        self.grid_canvas.focus_set() # 焦点还给画布





    def clear_right_group(self):


        for r in range(4):


            for c in range(10, 12):


                self.grid_config.set_btn_data(r, c, page=0, script="", image="", text="", bold=True, text_color="#333333")


                if self.current_editing_btn == (r, c): self.current_editing_btn = None


                self.update_grid_button_ui(r, c)


        self.update_status_bar("✅ 组合任务区域已清空", "black")



    def _get_schedule_parts(self):


        try:


            hour = int(str(self.sched_h_var.get()).strip())


            minute = int(str(self.sched_m_var.get()).strip())


            second = int(str(self.sched_s_var.get()).strip())


            millisecond = int(str(self.sched_ms_var.get()).strip() or "0")


        except ValueError:


            raise ValueError("定时时间必须是数字")


        if not 0 <= hour <= 23: raise ValueError("小时必须在 0-23 之间")


        if not 0 <= minute <= 59: raise ValueError("分钟必须在 0-59 之间")


        if not 0 <= second <= 59: raise ValueError("秒必须在 0-59 之间")


        if not 0 <= millisecond <= 999: raise ValueError("毫秒必须在 0-999 之间")


        self.sched_h_var.set(f"{hour:02d}")


        self.sched_m_var.set(f"{minute:02d}")


        self.sched_s_var.set(f"{second:02d}")


        self.sched_ms_var.set(f"{millisecond:03d}")


        return hour, minute, second, millisecond



    def _format_schedule_time(self, hour=None, minute=None, second=None, millisecond=None):


        if hour is None:


            hour, minute, second, millisecond = self._get_schedule_parts()


        return f"{hour:02d}:{minute:02d}:{second:02d}.{millisecond:03d}"



    def cancel_scheduled_script(self):


        if self.sched_after_id is not None:


            try:


                self.root.after_cancel(self.sched_after_id)


            except Exception:


                pass


            self.sched_after_id = None


        self.sched_target_text = None



    def disable_scheduled_script(self):


        self.sched_enabled_var.set(False)


        self.cancel_scheduled_script()



    def schedule_script_at(self, hour, minute, second=0, millisecond=0, script_path=None, use_loop=True):


        """
        在指定的 时:分:秒.毫秒 执行脚本。script_path 为空时执行右侧组合任务；
        时间已经过了会自动排到明天。返回本次 Tk after 任务 id。
        示例: self.schedule_script_at(20, 30, 15, 500, r"E:\\test\\demo.txt")
        """


        hour = int(hour); minute = int(minute); second = int(second); millisecond = int(millisecond)


        if not 0 <= hour <= 23: raise ValueError("小时必须在 0-23 之间")


        if not 0 <= minute <= 59: raise ValueError("分钟必须在 0-59 之间")


        if not 0 <= second <= 59: raise ValueError("秒必须在 0-59 之间")


        if not 0 <= millisecond <= 999: raise ValueError("毫秒必须在 0-999 之间")


        if script_path:


            exists = os.path.exists(script_path) or os.path.exists(script_path + ".txt") or os.path.exists(script_path + ".ks")


            if not exists:


                raise FileNotFoundError(f"脚本不存在: {script_path}")


        self.cancel_scheduled_script()


        now_ts = time.time()


        now = time.localtime(now_ts)


        target_tuple = (now.tm_year, now.tm_mon, now.tm_mday, hour, minute, second, now.tm_wday, now.tm_yday, now.tm_isdst)


        target_ts = time.mktime(target_tuple) + millisecond / 1000.0


        if target_ts <= now_ts:


            target_ts += 24 * 60 * 60


        delay_ms = max(0, int(round((target_ts - now_ts) * 1000)))


        target_day = time.strftime("%Y-%m-%d", time.localtime(target_ts))


        self.sched_target_text = f"{target_day} {self._format_schedule_time(hour, minute, second, millisecond)}"


        def _fire():


            self.sched_after_id = None


            self.last_sched_trigger_time = self.sched_target_text


            self.sched_enabled_var.set(False)


            self.update_status_bar(f"⏰ 定时任务触发: {self.sched_target_text}", "blue")


            if script_path:


                if self.is_executing:


                    self.update_status_bar("⛔ 定时任务触发时已有任务正在执行", "red")


                    return


                self.execute_single_script(script_path, use_loop=use_loop)


            else:


                self.run_right_group_sequence(from_scheduler=True)


        self.sched_after_id = self.root.after(delay_ms, _fire)


        return self.sched_after_id



    def toggle_scheduled_task(self):


        if not self.sched_enabled_var.get():


            self.cancel_scheduled_script()


            self.update_status_bar("定时任务已取消", "black")


            return


        try:


            hour, minute, second, millisecond = self._get_schedule_parts()


            self.schedule_script_at(hour, minute, second, millisecond)


            self.update_status_bar(f"⏰ 已定时: {self.sched_target_text}", "blue")


        except Exception as e:


            self.sched_enabled_var.set(False)


            self.cancel_scheduled_script()


            messagebox.showerror("定时设置错误", str(e))





    def run_right_group_sequence(self, from_scheduler=False):


        if self.is_executing:


            messagebox.showinfo("提示", "当前有任务正在执行，请等待执行完毕")


            return





        # 如果是手动点击，且定时已开启，则提示等待


        if not from_scheduler and self.sched_enabled_var.get():


            try:


                target = self._format_schedule_time()


            except Exception:


                target = f"{self.sched_h_var.get()}:{self.sched_m_var.get()}"


            messagebox.showinfo("提示", f"已开启定时功能！\n任务将在 {target} 自动执行。\n\n(请勿关闭软件，保持挂机状态)")


            return





        tasks = []


        for r in range(4): 


            for c in range(10, 12): 


                data = self.grid_config.get_btn_data(r, c, page=0)


                script_path = data.get('script')


                if script_path and os.path.exists(script_path): tasks.append(script_path)


        


        if not tasks:


            if not from_scheduler: 


                messagebox.showinfo("提示", "右侧区域没有检测到有效的脚本")


            return





        self.is_executing = True


        self.engine.stop_signal = False


        


        def run_seq():


            self.update_status_bar(f"🚀 开始组合执行: 共 {len(tasks)} 个任务", "blue")


            self.update_run_status(f"🚀 组合任务运行中 ({len(tasks)}个)", "blue")


            try:


                for i, path in enumerate(tasks):


                    if self.engine.stop_signal: break


                    self.update_status_bar(f"▶ ({i+1}/{len(tasks)}) 正在组合执行: {os.path.basename(path)}", "green")


                    


                    # --- [新增] 检查 exe/bat ---


                    ext = os.path.splitext(path)[1].lower()


                    if ext in ['.exe', '.bat', '.cmd']:


                        try:


                            os.startfile(path)


                            # 给其一点启动时间，防止瞬时并发太快


                            time.sleep(1.0) 


                        except Exception as e:


                            print(f"Group Run Exe Error: {e}")


                    else:


                        # 普通脚本走引擎


                        self.engine.execute_script(path, self.speed_var.get())


                    


                    time.sleep(0.5)


            except Exception as e:


                print(f"Group Run Error: {e}")


            


            self.is_executing = False


            if self.engine.stop_signal:


                self.update_status_bar("⛔ 组合任务已终止", "red")


                self.update_run_status("⛔ 组合任务已停止", "red")


            else:


                self.update_status_bar("✅ 组合任务全部执行完毕", "black")


                self.update_run_status("✅ 组合任务完成", "black")





        threading.Thread(target=run_seq, daemon=True).start()





    def check_scheduled_task(self):


        try:


            if self.sched_enabled_var.get() and self.sched_after_id is None:


                hour, minute, second, millisecond = self._get_schedule_parts()


                self.schedule_script_at(hour, minute, second, millisecond)


        except:


            pass


        self.root.after(1000, self.check_scheduled_task) 





    def on_search_update(self, *args):


        # [修改] 使用 float_search_var


        term = self.float_search_var.get()


        self.render_file_grid(term)





    def clear_search(self):


        # [修改] 适配新逻辑


        self.float_search_var.set("")


        self.render_file_grid("")


        self.hide_floating_search()








    def refresh_panel_tabs(self):


        for widget in self.panel_bar.winfo_children():


            widget.destroy()


        self.panel_buttons.clear()


        


        count = self.grid_config.get_panel_count()


        


        if self.current_page_index >= count:


            self.current_page_index = max(0, count - 1)


            


        for i in range(count):


            if i in self.floating_panels:


                self.panel_buttons.append(None)


                continue


                


            p_name = self.grid_config.get_panel_name(i)


            bg_color = self.ACCENT if i == self.current_page_index else "#DDDDDD"


            fg_color = "white" if i == self.current_page_index else "#333333"


            


            p_btn = tk.Button(self.panel_bar, text=p_name, font=('Microsoft YaHei UI', 9), bg=bg_color, fg=fg_color, relief="flat", padx=10)


            p_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)


            p_btn.bind("<Button-1>", lambda e, idx=i: self.switch_panel(idx))


            p_btn.bind("<Button-3>", lambda e, idx=i: self.show_panel_context_menu(e, idx))


            p_btn.bind("<B1-Motion>", lambda e, idx=i, btn=p_btn: self.on_panel_drag(e, idx, btn))


            p_btn.bind("<ButtonRelease-1>", lambda e, idx=i, btn=p_btn: self.on_panel_drag_release(e, idx, btn))


            self.panel_buttons.append(p_btn)


            


        self.refresh_single_task_grid()





    def show_panel_context_menu(self, event, index):


        menu = tk.Menu(self.root, tearoff=0)


        menu.add_command(label="📝 重命名面板", command=lambda: self.rename_panel(index))


        menu.add_command(label="➕ 添加面板", command=self.add_panel)


        menu.add_separator()


        menu.add_command(label="🗑️ 删除面板", command=lambda: self.delete_panel(index))


        menu.add_separator()


        menu.add_command(label="ℹ️ 提示: 按住向下拖拽可分离面板", state="disabled")


        menu.post(event.x_root, event.y_root)





    def add_panel(self):


        new_idx = self.grid_config.add_panel()


        self.switch_panel(new_idx)


        self.refresh_panel_tabs()





    def delete_panel(self, idx):


        if self.grid_config.get_panel_count() <= 1:


            messagebox.showwarning("警告", "必须至少保留一个面板！")


            return


        if messagebox.askyesno("确认删除", f"确定要删除面板 '{self.grid_config.get_panel_name(idx)}' 及配置吗？"):


            self.grid_config.delete_panel(idx)


            if self.current_page_index >= self.grid_config.get_panel_count():


                self.current_page_index = max(0, self.grid_config.get_panel_count() - 1)


            self.refresh_panel_tabs()





    def on_panel_drag(self, event, index, btn):


        btn.config(cursor="fleur")


        if not hasattr(self, '_panel_drag_start_y'): self._panel_drag_start_y = event.y_root





    def on_panel_drag_release(self, event, index, btn):


        btn.config(cursor="")


        if not hasattr(self, '_panel_drag_start_y'): return


        y_diff = event.y_root - self._panel_drag_start_y


        del self._panel_drag_start_y


        


        if y_diff > 50:


            if index not in self.floating_panels:


                self.floating_panels[index] = FloatingPanelWindow(self, index, event.x_root, event.y_root)


                if self.current_page_index == index:


                    for non_float_i in range(self.grid_config.get_panel_count()):


                        if non_float_i not in self.floating_panels:


                            self.current_page_index = non_float_i


                            break


                self.refresh_panel_tabs()





    def switch_panel(self, index):


        if self.current_page_index == index: return


        self.current_page_index = index


        self.refresh_panel_tabs()





    def rename_panel(self, index):


        old_name = self.grid_config.get_panel_name(index)


        new_name = simpledialog.askstring("重命名面板", f"请输入面板的新名称:", initialvalue=old_name)


        if new_name:


            self.grid_config.set_panel_name(index, new_name)


            self.refresh_panel_tabs()


            if index in self.floating_panels:


                self.floating_panels[index].title(new_name)





    def refresh_single_task_grid(self):


        for r in range(5):


            for c in range(9):


                self.update_grid_button_ui(r, c)


                if self.current_editing_btn == (r, c):


                    self.grid_buttons[(r, c)].config(bg="#FFD1DC")





    def create_grid_button(self, parent, r, c, size, font, grid_col_offset=0, grid_row_offset=0):


        btn = tk.Button(parent, text="", font=font, wraplength=100, bg="#F5F5F5", relief="raised", bd=1, image=self.pixel_ref, width=size, height=size, compound="center") 


        btn.grid(row=r + grid_row_offset, column=c+grid_col_offset, padx=3, pady=3)


        btn.bind("<Button-1>", lambda e, r=r, c=c: self.on_grid_click_or_drag_start(e, r, c))


        btn.bind("<ButtonRelease-1>", lambda e, r=r, c=c: self.on_grid_release(e, r, c))


        btn.bind("<B1-Motion>", lambda e, r=r, c=c: self.on_grid_motion(e, r, c))
        btn.bind("<Button-3>", lambda e, r=r, c=c: self.on_grid_right_click(e, r, c))
        btn.bind("<Enter>", lambda e, r=r, c=c: self.on_btn_enter(e, r, c))
        btn.bind("<Leave>", lambda e, r=r, c=c: self.on_btn_leave(e, r, c))
        if HAS_DND:


            try: btn.drop_target_register(DND_FILES); btn.dnd_bind('<<Drop>>', lambda e, r=r, c=c: self.on_grid_drop_external(e, r, c))


            except: pass


        self.grid_buttons[(r, c)] = btn


        self.update_grid_button_ui(r, c)





    def open_btn_config_dialog(self, r, c, page_index=None):


        page = page_index if page_index is not None else (self.current_page_index if c < 10 else 0)


        if getattr(self, 'current_editing_btn', None):


            pr, pc = self.current_editing_btn


            self.update_grid_button_ui(pr, pc, getattr(self, 'current_editing_page', None)) 


        


        self.current_editing_btn = (r, c)


        self.current_editing_page = page


        


        if c >= 10 or page == self.current_page_index:


            self.grid_buttons[(r, c)].config(bg="#FFD1DC")





        data = self.grid_config.get_btn_data(r, c, page=page)





        def save_callback(new_data):


            self.grid_config.set_btn_data(r, c, page=page, **new_data)


            self.update_grid_button_ui(r, c, page)


            self.current_editing_btn = None 


            self.update_status_bar(f"按钮 [{r+1},{c+1}] 配置已保存")


            


        def on_close_callback(geom):


            self.btn_config_geometry = geom


            


        self.root.after(100, lambda: ButtonConfigWindow(self.root, data, self.btn_config_geometry, save_callback, on_close_callback))





    def on_grid_right_click(self, event, r, c, page_index=None):


        page = page_index if page_index is not None else (self.current_page_index if c < 10 else 0)


        data = self.grid_config.get_btn_data(r, c, page=page)


        menu = tk.Menu(self.root, tearoff=0)


        


        def add_item(label, cmd_func):


            py_idx_paren = label.find('(')


            if py_idx_paren == -1:


                menu.add_command(label=label, command=lambda: self.root.after(100, cmd_func))


                return


            py_idx_target = py_idx_paren + 1 


            prefix = label[:py_idx_target]


            offset = sum(1 for ch in prefix if ord(ch) > 0xFFFF)


            final_underline = py_idx_target + offset


            menu.add_command(label=label, command=lambda: self.root.after(100, cmd_func), underline=final_underline)





        if data.get('script') and os.path.exists(data['script']):


            add_item("📝 编辑脚本(E)", lambda: self.open_editor_window(data['script']))


            menu.add_separator()


        else:


            add_item("🔴 录制功能(R)", lambda: self.start_record_for_btn(r, c))


            menu.add_separator()

        if data.get('script') or data.get('text'):
            add_item("➡️ 移入组合执行区域(Z)", lambda: self.add_to_combined_execution(r, c, page))
            menu.add_separator()

        add_item("✏ 配置(S)", lambda: self.open_btn_config_dialog(r, c, page))


        add_item("🗑 清除(D)", lambda: self.clear_btn_config(r, c, page))


        menu.add_separator()


        menu.add_command(label="❌ 取消", command=None)


        menu.post(event.x_root, event.y_root)





    def clear_btn_config(self, r, c, page_index=None):


        if messagebox.askyesno("清除", f"清除按钮 [{r+1},{c+1}] 的所有配置？"):


            page = page_index if page_index is not None else (self.current_page_index if c < 10 else 0)


            self.grid_config.set_btn_data(r, c, page=page, script="", image="", text="", bold=True, text_color="#333333")


            if getattr(self, 'current_editing_btn', None) == (r, c) and getattr(self, 'current_editing_page', None) == page: 


                self.current_editing_btn = None


            self.update_grid_button_ui(r, c, page)





    def on_font_scale_change(self, event=None):


        for (r, c), btn in self.grid_buttons.items():


            self.update_grid_button_ui(r, c)


    def on_font_scale_change(self, event=None):


        for (r, c), btn in self.grid_buttons.items():


            self.update_grid_button_ui(r, c)


            if self.current_editing_btn == (r, c): btn.config(bg="#FFD1DC")





    def on_long_press_trigger(self, r, c, page_index=None):


        if self.is_holding_btn and self.current_holding_btn == (r, c) and not self.drag_manager.is_dragging:


            self.is_holding_btn = False 


            self.long_press_timer = None


            


            page = page_index if page_index is not None else (self.current_page_index if c < 10 else 0)


            data = self.grid_config.get_btn_data(r, c, page=page)


            script_path = data.get('script')


            


            if script_path and os.path.exists(script_path):


                self.update_status_bar(f"🔥 长按触发编辑: {os.path.basename(script_path)}")


                self.open_editor_window(script_path)


            else:


                self.update_status_bar("🔥 长按触发: 无脚本", "orange")





    def on_grid_click_or_drag_start(self, event, r, c, page_index=None):


        self.is_holding_btn = True; self.current_holding_btn = (r, c)


        


        if self.long_press_timer: self.root.after_cancel(self.long_press_timer)


        self.long_press_timer = self.root.after(2500, lambda: self.on_long_press_trigger(r, c, page_index))


        


        # Disable button dragging for floating panels for now, but allow click


        if page_index is None or page_index == self.current_page_index:


            self.drag_manager.on_start_drag(event, mode='button', data=(r, c))





    def on_grid_motion(self, event, r, c, page_index=None):


        if page_index is None or page_index == self.current_page_index:


            if self.drag_manager.on_drag_motion(event): 


                self.is_holding_btn = False


                if self.long_press_timer: self.root.after_cancel(self.long_press_timer); self.long_press_timer = None





    def on_grid_release(self, event, r, c, page_index=None):


        if self.long_press_timer: self.root.after_cancel(self.long_press_timer); self.long_press_timer = None


        


        if page_index is None or page_index == self.current_page_index:


            drag_action = self.drag_manager.on_stop_drag(event)


            if drag_action == 'swapped':


                pr = getattr(self, 'current_editing_btn', [None, None])[0]


                pc = getattr(self, 'current_editing_btn', [None, None])[1]


                if pr is not None: self.update_grid_button_ui(pr, pc, getattr(self, 'current_editing_page', None)) 


                self.is_holding_btn = False; return


                


        is_valid_click = (self.is_holding_btn and self.current_holding_btn == (r, c))


        self.is_holding_btn = False; self.current_holding_btn = None


        if is_valid_click:


            page = page_index if page_index is not None else (self.current_page_index if c < 10 else 0)


            data = self.grid_config.get_btn_data(r, c, page=page)


            is_shift = bool(getattr(event, 'state', 0) & 0x0001)
            try:
                is_shift = is_shift or bool(ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000)
            except Exception:
                pass


            if is_shift:


                if data.get('script') or data.get('text'):


                    self.add_to_combined_execution(r, c, page)


                return


            if data['script'] and os.path.exists(data['script']): 


                if self.is_executing and self.current_executing_path == data['script']:


                     self.engine.stop_signal = True


                     self.update_status_bar("⛔ 正在停止...", "orange")


                     return


                self.execute_single_script(data['script'], use_loop=True)





    def swap_grid_buttons(self, r1, c1, r2, c2):


        p1 = self.current_page_index if c1 < 10 else 0


        p2 = self.current_page_index if c2 < 10 else 0


        data1 = self.grid_config.get_btn_data(r1, c1, page=p1)


        data2 = self.grid_config.get_btn_data(r2, c2, page=p2)


        self.grid_config.set_btn_data(r1, c1, page=p1, **data2) 


        self.grid_config.set_btn_data(r2, c2, page=p2, **data1) 


        self.update_grid_button_ui(r1, c1); self.update_grid_button_ui(r2, c2)





    def copy_grid_button(self, r1, c1, r2, c2):


        p1 = self.current_page_index if c1 < 10 else 0


        p2 = self.current_page_index if c2 < 10 else 0


        data = self.grid_config.get_btn_data(r1, c1, page=p1)


        


        # Fix bold type (config returns str, set expects bool/condition)


        if 'bold' in data and isinstance(data['bold'], str):


             data['bold'] = (data['bold'] == '1')





        self.grid_config.set_btn_data(r2, c2, page=p2, **data)


        self.update_grid_button_ui(r2, c2)


        self.update_status_bar(f"已复制按钮 [{r1+1},{c1+1}] 到 [{r2+1},{c2+1}]")





    def handle_internal_drop(self, r, c, path, page_index=None):


        if path and os.path.exists(path):


            page = page_index if page_index is not None else (self.current_page_index if c < 10 else 0)


            self.grid_config.set_btn_data(r, c, page=page, script=path)


            self.update_grid_button_ui(r, c, page); self.update_status_bar(f"已绑定脚本到 [{r+1},{c+1}]")





    def on_grid_drop_external(self, event, r, c, page_index=None):


        path = event.data


        if path.startswith('{') and path.endswith('}'): path = path[1:-1]


        if os.path.isfile(path):


            page = page_index if page_index is not None else (self.current_page_index if c < 10 else 0)


            ext = os.path.splitext(path)[1].lower()


            if ext in ['.png', '.jpg', '.jpeg', '.gif', '.ico', '.bmp']: 


                self.grid_config.set_btn_data(r, c, page=page, image=path)


            else: 


                self.grid_config.set_btn_data(r, c, page=page, script=path)


            self.update_grid_button_ui(r, c, page)





    def update_grid_button_ui(self, r, c, page_index=None):


        page = page_index if page_index is not None else (self.current_page_index if c < 10 else 0)


        data = self.grid_config.get_btn_data(r, c, page=page)


        


        script_path = data['script']; img_path = data['image']; custom_text = data.get('text', '')


        base_size = int(self.btn_font_size_var.get()); is_bold = data.get('bold', '1') == '1'; text_color = data.get('text_color', '#333333')


        current_font = ('Microsoft YaHei UI', base_size, 'bold' if is_bold else 'normal')


        if custom_text: display_name = custom_text


        elif img_path and os.path.exists(img_path): display_name = "" 


        else: display_name = os.path.basename(script_path) if script_path else "" 


        


        if c < 10 and page in self.floating_panels:


            self.floating_panels[page].update_btn_ui(r, c)


            


        if c >= 10 or page == self.current_page_index:


            btn = self.grid_buttons.get((r, c))


            if not btn: return


            


            btn.config(text=display_name, fg=text_color, font=current_font, compound="center")





            if img_path and os.path.exists(img_path):


                try:


                    target_size = 104 


                    if HAS_PIL:


                        pil_img = Image.open(img_path)


                        pil_img = pil_img.resize((target_size, target_size), Image.Resampling.LANCZOS)


                        tk_img = ImageTk.PhotoImage(pil_img)


                        self.grid_images[(r, c)] = tk_img 


                        btn.config(image=tk_img, text=display_name, compound="center") 


                    else:


                        self.grid_images[(r, c)] = tk.PhotoImage(file=img_path)


                        btn.config(image=self.grid_images[(r, c)], text=display_name, compound="center")


                except Exception as e:


                    btn.config(image=self.pixel_ref, text=display_name)


            else:


                btn.config(image=self.pixel_ref)


                


            if getattr(self, 'current_editing_btn', None) != (r, c) or getattr(self, 'current_editing_page', None) != page:


                btn.config(bg="#F5F5F5") 





    # --- 原有功能 ---


    def create_new_folder(self):


        current_dir = self.scripts_dir_var.get()


        if not current_dir or not os.path.exists(current_dir): messagebox.showwarning("提示", "当前未选择有效目录"); return


        folder_name = simpledialog.askstring("新建文件夹", "请输入文件夹名称:")


        if folder_name and folder_name.strip():


            new_path = os.path.join(current_dir, folder_name.strip())


            try: 


                os.makedirs(new_path)


                self.update_status_bar(f"创建成功: {folder_name.strip()}")


                


                # [Fix] Refresh the current tree node so the new folder appears in the tree structure immediately.


                # If we don't do this, entering the folder later will fail because sync_tree_to_path 


                # won't find the new node, causing it to select the parent and revert the view.


                try:


                    selected = self.dir_tree.selection()


                    if selected:


                        node = selected[0]


                        # Verify path matches


                        node_path = self.dir_tree.item(node, 'values')[0]


                        if os.path.normpath(node_path) == os.path.normpath(current_dir):


                             # Clear children and re-expand to refresh


                             self.dir_tree.delete(*self.dir_tree.get_children(node))


                             # Insert dummy to satisfy _expand_node logic


                             self.dir_tree.insert(node, 'end', text='dummy') 


                             self.dir_tree.item(node, open=True) # Ensure it stays open


                             self._expand_node(node)


                except Exception as e:


                    print(f"Tree refresh error: {e}")





                self.refresh_file_list()


                self.sync_tree_to_path(current_dir)


            except Exception as e: messagebox.showerror("错误", f"创建失败: {e}")





    def rename_sel(self):


        if not self.selected_filename: messagebox.showinfo("提示", "请先选择一个文件或文件夹！"); return


        current_dir = self.scripts_dir_var.get(); old_path = os.path.join(current_dir, self.selected_filename)


        new_name = simpledialog.askstring("重命名", f"请输入新名称:\n(原名: {self.selected_filename})", initialvalue=self.selected_filename)


        if new_name and new_name.strip():


            new_name = new_name.strip()


            if new_name == self.selected_filename: return 


            new_path = os.path.join(current_dir, new_name)


            if os.path.exists(new_path): messagebox.showerror("错误", "该名称已存在！"); return


            try:


                os.rename(old_path, new_path); self.update_status_bar(f"重命名成功: {new_name}"); self.refresh_file_list() 


                if new_name in self.file_widgets: self.select_file_ui(new_name, self.file_widgets[new_name])


            except Exception as e: messagebox.showerror("错误", f"重命名失败: {e}")





    def load_drives_into_tree(self):


        drives = []


        if sys.platform == 'win32':


            import string


            drives = ['%s:\\' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]


        else: drives = ['/']


        for d in drives:


            node = self.dir_tree.insert('', 'end', text=d, values=[d], open=False); self.dir_tree.insert(node, 'end', text='dummy')





    def _expand_node(self, node):


        path = self.dir_tree.item(node, 'values')[0]


        children = self.dir_tree.get_children(node)


        if len(children) == 1 and self.dir_tree.item(children[0], 'text') == 'dummy':


            self.dir_tree.delete(children[0])


            try:


                for p in os.listdir(path):


                    full_p = os.path.join(path, p)


                    if os.path.isdir(full_p):


                        sub_node = self.dir_tree.insert(node, 'end', text=p, values=[full_p], open=False); self.dir_tree.insert(sub_node, 'end', text='dummy')


            except PermissionError: pass





    def on_tree_open(self, event):


        node = self.dir_tree.focus()


        if node: self._expand_node(node)





    def sync_tree_to_path(self, target_path):


        if not target_path or not os.path.exists(target_path): return


        target_path = os.path.abspath(target_path); drive, tail = os.path.splitdrive(target_path)


        current_node = None


        for child in self.dir_tree.get_children(''):


            node_path = self.dir_tree.item(child, 'values')[0]


            if node_path.upper().startswith(drive.upper()): current_node = child; break


        if not current_node: return


        parts = tail.strip(os.sep).split(os.sep)


        self.dir_tree.item(current_node, open=True); self._expand_node(current_node)


        for part in parts:


            if not part: continue


            found_child = None


            for child in self.dir_tree.get_children(current_node):


                text = self.dir_tree.item(child, 'text')


                if text.lower() == part.lower(): found_child = child; break


            if found_child:


                current_node = found_child; self.dir_tree.item(current_node, open=True); self._expand_node(current_node)


            else: break


        self.dir_tree.selection_set(current_node); self.dir_tree.see(current_node)





    def on_tree_select(self, event):


        node = self.dir_tree.selection()


        if not node: return


        path = self.dir_tree.item(node[0], 'values')[0]; self.scripts_dir_var.set(path); self.refresh_file_list(); self.save_settings()





    def on_frame_configure(self, event): self.grid_canvas.configure(scrollregion=self.grid_canvas.bbox("all"))


    def on_canvas_configure(self, event): self.grid_canvas.itemconfig(self.grid_canvas_window, width=event.width)


    def on_mousewheel(self, event): self.grid_canvas.yview_scroll(int(-1*(event.delta/120)), "units")





    def refresh_file_list(self):


        d = self.scripts_dir_var.get()


        if not os.path.exists(d): return


        self.all_items_cache = [] 


        try:


            items = os.listdir(d); items.sort()


            dirs = []; files = []


            for item in items:


                if item.startswith('.'): continue


                full_p = os.path.join(d, item)


                if os.path.isdir(full_p): dirs.append(item)


                elif os.path.isfile(full_p): files.append(item)


            for folder in dirs: self.all_items_cache.append((folder, True))


            for file in files: self.all_items_cache.append((file, False))


        except: pass


        # [修改] 使用新的变量


        term = self.float_search_var.get()


        self.render_file_grid(term)





    def render_file_grid(self, filter_text=""):


        for widget in self.grid_frame.winfo_children(): widget.destroy()


        self.file_widgets = {}; self.selected_label = None; self.selected_filename = None


        filter_text = filter_text.lower()


        self.grid_frame.columnconfigure(0, weight=1); self.grid_frame.columnconfigure(1, weight=1); self.grid_frame.columnconfigure(2, weight=1)


        row = 0; col = 0


        for name, is_dir in self.all_items_cache:


            if filter_text and filter_text not in name.lower(): continue


            display_name = f"📁 {name}" if is_dir else name


            text_color = '#0055AA' if is_dir else '#333333'


            lbl = tk.Label(self.grid_frame, text=display_name, bg='#FFFFFF', fg=text_color, font=('Microsoft YaHei UI', 12), anchor='w', padx=20, pady=20, relief='flat')


            


            # [修改] 给Label绑定点击，不仅选择，还要让Canvas获得焦点，以便继续支持键盘搜索


            lbl.bind("<Button-1>", lambda event, n=name, widget=lbl: (self.select_file_ui(n, widget, event), self.grid_canvas.focus_set()))


            


            if is_dir: lbl.bind("<Double-Button-1>", lambda event, n=name: self.enter_folder(n))


            if not is_dir:


                lbl.bind("<B1-Motion>", self.drag_manager.on_drag_motion)


                lbl.bind("<ButtonRelease-1>", self.drag_manager.on_stop_drag)


            lbl.bind("<Enter>", lambda event, widget=lbl: self.on_hover(widget, True))


            lbl.bind("<Leave>", lambda event, widget=lbl: self.on_hover(widget, False))


            lbl.grid(row=row, column=col, sticky='ew', padx=2, pady=2)


            self.file_widgets[name] = lbl


            col += 1


            if col > 2: col = 0; row += 1


        self.grid_frame.update_idletasks()


        self.grid_canvas.configure(scrollregion=self.grid_canvas.bbox("all"))


        self.grid_canvas.yview_moveto(0)





    def enter_folder(self, folder_name):


        current = self.scripts_dir_var.get(); new_path = os.path.join(current, folder_name)


        if os.path.exists(new_path): 


            # [修改] 进文件夹后清空搜索


            self.scripts_dir_var.set(new_path); self.float_search_var.set(""); self.refresh_file_list(); self.sync_tree_to_path(new_path); self.save_settings()





    def on_hover(self, widget, is_hovering):


        if widget == self.selected_label: return


        if is_hovering: widget.config(bg='#E1F5FE') 


        else: widget.config(bg='#FFFFFF')





    def select_file_ui(self, fname, widget, event=None):


        if self.selected_label and self.selected_label.winfo_exists():


            old_name = self.selected_filename


            try:


                is_dir = os.path.isdir(os.path.join(self.scripts_dir_var.get(), old_name))


                self.selected_label.config(bg='#FFFFFF', fg='#0055AA' if is_dir else '#333333')


            except: self.selected_label.config(bg='#FFFFFF', fg='#333333')


        widget.config(bg=self.ACCENT, fg='#FFFFFF'); self.selected_label = widget; self.selected_filename = fname; self.update_status_bar(f"选中: {fname}")


        self.ensure_visible(widget)


        if event and not os.path.isdir(os.path.join(self.scripts_dir_var.get(), fname)):


            self.drag_manager.on_start_drag(event, mode='file', data=os.path.join(self.scripts_dir_var.get(), fname))





    def ensure_visible(self, widget):


        try:


            wy = widget.winfo_y(); ch = self.grid_canvas.winfo_height()


            if wy > ch: self.grid_canvas.yview_moveto(wy / self.grid_frame.winfo_height())


        except: pass





    # [移除] 之前空的 on_keypress，现在逻辑在 handle_quick_search


    # def on_keypress(self, event):


    #     pass





    def edit_sel(self):


        if not self.selected_filename: return


        p = os.path.join(self.scripts_dir_var.get(), self.selected_filename)


        if os.path.isdir(p): return 


        self.open_editor_window(p)





    def play_sel(self):


        if not self.selected_filename: messagebox.showinfo("提示", "请先在列表中选中一个脚本文件！"); return


        p = os.path.join(self.scripts_dir_var.get(), self.selected_filename)


        if os.path.isdir(p): messagebox.showinfo("提示", "不能运行文件夹！"); return 


        if self.is_executing: return


        self.execute_single_script(p, True)





    def del_sel(self):


        if not self.selected_filename: return


        if messagebox.askyesno("Del", f"删除 {self.selected_filename}?"):


            try:


                p = os.path.join(self.scripts_dir_var.get(), self.selected_filename); 


                if os.path.isdir(p): os.rmdir(p) 


                else: os.remove(p)


                self.refresh_file_list()


            except Exception as e: messagebox.showerror("Err", str(e))


        


    def save_settings(self):


        if self.hotkey_win and self.hotkey_win.winfo_exists(): self.hotkey_editor_geometry = self.hotkey_win.geometry()


        


        # [修改] 尝试保存脚本窗口的位置


        try:


            if self.script_window:


                self.script_manager_geometry = self.script_window.geometry()


        except: pass





        # [NEW] Save floating stop window position


        if self.floating_stop_win:


            try:


                geo_parts = self.floating_stop_win.geometry().split('+')


                self.floating_stop_pos = f"+{geo_parts[1]}+{geo_parts[2]}"


            except:


                self.floating_stop_pos = None # Reset if error


        


        d = {'geometry': self.root.geometry(), 'hotkeys': self.hotkey_data, 'scripts_dir': self.scripts_dir_var.get(),


             'hotkey_editor_geometry': self.hotkey_editor_geometry, 'hotkeys_enabled': self.hotkeys_enabled_var.get(), 'grid_dialog_geometry': self.grid_dialog_geometry,


             'btn_font_size': self.btn_font_size_var.get(), 'editor_geometry': self.editor_geometry,


             'btn_config_geometry': self.btn_config_geometry,


             'script_manager_geometry': self.script_manager_geometry, # [新增] 保存脚本窗口位置


             'sched_h': self.sched_h_var.get(), 'sched_m': self.sched_m_var.get(), 'sched_s': self.sched_s_var.get(), 'sched_ms': self.sched_ms_var.get(), 'sched_enabled': self.sched_enabled_var.get(),


             'floating_stop_pos': self.floating_stop_pos,


             'floating_step_pos': getattr(self, 'floating_step_pos', None) # [NEW] Save floating step pos


             }     


        try:


            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(d, f, indent=4, ensure_ascii=False)


        except: pass


        


    def load_config(self):


        d = os.path.join(BASE_DIR, "scripts"); 


        if not os.path.exists(d): 


            try: os.makedirs(d) 


            except: pass


        fd = d


        if os.path.exists(CONFIG_FILE):


            try:


                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:


                    cfg = json.load(f)


                    self.root.geometry(cfg.get('geometry', "1700x1000"))


                    self.hotkey_data = cfg.get('hotkeys', []) 


                    #self.topmost_var.set(cfg.get('topmost', False))


                    self.hotkey_editor_geometry = cfg.get('hotkey_editor_geometry', "600x400") 


                    self.hotkeys_enabled_var.set(cfg.get('hotkeys_enabled', 1))


                    self.grid_dialog_geometry = cfg.get('grid_dialog_geometry', None)


                    self.btn_font_size_var.set(cfg.get('btn_font_size', 8))


                    self.editor_geometry = cfg.get('editor_geometry', "800x600")


                    self.btn_config_geometry = cfg.get('btn_config_geometry', "500x400")


                    self.script_manager_geometry = cfg.get('script_manager_geometry', "1000x800") # [新增] 读取脚本窗口位置


                    self.sched_h_var.set(cfg.get('sched_h', "00"))


                    self.sched_m_var.set(cfg.get('sched_m', "00"))


                    self.sched_s_var.set(cfg.get('sched_s', "00"))


                    self.sched_ms_var.set(cfg.get('sched_ms', "000"))


                    self.sched_enabled_var.set(cfg.get('sched_enabled', False))


                    self.floating_stop_pos = cfg.get('floating_stop_pos', None) # [NEW] Load floating stop window position


                    self.floating_step_pos = cfg.get('floating_step_pos', None) # [NEW] Load floating step pos


                    sd = cfg.get('scripts_dir')


                    if sd and os.path.exists(sd): fd = sd


            except: pass


        self.scripts_dir_var.set(fd)





    def open_hotkey_editor(self):


        editor = tk.Toplevel(self.root); self.hotkey_win = editor 


        editor.title("编辑全局快捷键")


        try: editor.geometry(self.hotkey_editor_geometry)


        except: editor.geometry("600x400")


        btn_frame = ttk.Frame(editor, padding=5); btn_frame.pack(side=tk.BOTTOM, fill=tk.X)


        txt_frame = ttk.Frame(editor, padding=5); txt_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)


        txt = tk.Text(txt_frame, font=('Consolas', 12), wrap=tk.NONE); txt.pack(fill=tk.BOTH, expand=True)


        current_text = "# 格式: ctrl+alt+a = D:\\scripts\\test.ks\n\n"


        for item in self.hotkey_data: current_text += f"{item['key']} = {item['path']}\n"


        txt.insert(tk.END, current_text)


        original_content = current_text.strip()


        def parse_and_save():


            content = txt.get("1.0", tk.END).strip(); new_data = []


            for line in content.splitlines():


                line = line.strip()


                if not line or line.startswith("#"): continue


                if "=" in line:


                    parts = line.split("=", 1); k = parts[0].strip(); p = parts[1].strip()


                    if k and p: new_data.append({'key': k, 'path': p})


            self.hotkey_data = new_data; self.save_settings(); self.update_hotkey_state()


            nonlocal original_content; original_content = content


        def save_and_close(): parse_and_save(); messagebox.showinfo("成功", "快捷键配置已更新", parent=editor); editor.destroy()


        def on_hk_close():


            current_content = txt.get("1.0", tk.END).strip()


            if current_content != original_content:


                resp = messagebox.askyesnocancel("保存更改", "全局快捷键配置已修改，是否保存？", parent=editor)


                if resp is None: return 


                if resp is True: parse_and_save()


            self.hotkey_editor_geometry = editor.geometry(); editor.destroy()


        editor.protocol("WM_DELETE_WINDOW", on_hk_close)


        ttk.Button(btn_frame, text="✅ 保存并生效", command=save_and_close).pack(side=tk.RIGHT, padx=10)





    def normalize_hotkey(self, key_str):


        # [Fix] pynput needs <shift>+F (upper) not <shift>+f (lower) to match correctly


        parts = key_str.split('+')


        norm_parts = []


        has_shift = False


        


        # First pass: check for shift and identify modifiers


        raw_parts = [p.strip() for p in parts]


        for p in raw_parts:


            if p.lower() == 'shift': has_shift = True


            


        for p in raw_parts:


            pl = p.lower()


            if pl in ['ctrl', 'alt', 'shift', 'cmd']:


                norm_parts.append(f"<{pl}>")


            else:


                # If shift is ON, and it's a single letter, make it UPPER


                # Otherwise, keep it lower (pynput usually prefers lower for keys like 'a', 'f1')


                if has_shift and len(p) == 1 and p.isalpha():


                    norm_parts.append(p.upper())


                else:


                    norm_parts.append(pl)


        


        return '+'.join(norm_parts)





    def update_hotkey_state(self):


        if self.global_hotkey_listener:


            try: self.global_hotkey_listener.stop()


            except: pass


            self.global_hotkey_listener = None


        if self.global_mouse_listener:


            try: self.global_mouse_listener.stop()


            except: pass


            self.global_mouse_listener = None


        if self.custom_hotkey_listener:


            try: self.custom_hotkey_listener.stop()


            except: pass


            self.custom_hotkey_listener = None





        if self.hotkeys_enabled_var.get() == 1:


            self.setup_hotkeys() # [FIX] Reactivate Global F11/F12


            self.setup_custom_scripts_hotkeys()


            self.update_status_bar("✅ 热键已启用: F11/F12(鼠标中键) + 自定义")


        else: self.update_status_bar("❌ 热键已禁用")





    def setup_custom_scripts_hotkeys(self):


        mapping = {}


        errors = []


        for item in self.hotkey_data:


            k = item.get('key', ''); p = item.get('path', '')


            if k and p and os.path.exists(p):


                try: 


                    norm_key = self.normalize_hotkey(k)


                    mapping[norm_key] = lambda p=p: self.run_hotkey_script(p)


                except Exception as e:


                    errors.append(f"{k}: {e}")





        if mapping:


            try: 


                self.custom_hotkey_listener = keyboard.GlobalHotKeys(mapping)


                self.custom_hotkey_listener.start()


            except Exception as e: 


                print(f"Custom Hotkeys Start Err: {e}")


                errors.append(str(e))


        


        if errors:


            print("Hotkey Errors:", errors)


            # Optional: messagebox.showwarning("热键注册警告", "\n".join(errors))





    def run_hotkey_script(self, path):


        if not self.is_executing: self.root.after(0, lambda: self.execute_single_script(path, use_loop=True))





    def execute_single_script(self, path, use_loop=False):


        self.is_executing = True; self.engine.stop_signal = False


        self.current_executing_path = path # [NEW] Set current script


        loop_cnt = self.loop_var.get() if use_loop else 1





        # [Refactored] Use RunApp wrapper for binary files to ensure consistent environment handling


        ext = os.path.splitext(path)[1].lower()


        if ext in ['.exe', '.bat', '.cmd', '.lnk']:


            # Create a wrapper script in memory


            safe_path = path.replace('"', '') # Simple sanitization


            wrapper_script = [f'RunApp "{safe_path}"']


            


            def run_binary_wrapper():


                self.update_status_bar(f"🚀 正在启动: {os.path.basename(path)} (共{loop_cnt}次)", "blue")


                self.update_run_status(f"▶ 启动中: {os.path.basename(path)}", "blue")


                try:


                    for i in range(loop_cnt):


                        if self.engine.stop_signal: break


                        if i > 0: time.sleep(0.5) 


                        


                        # Use execute_from_lines to run the RunApp command


                        self.engine.execute_from_lines(wrapper_script, source_name=f"Run:{os.path.basename(path)}", speed_factor=1.0)


                        


                        self.update_status_bar(f"✅ 已启动 ({i+1}/{loop_cnt}): {os.path.basename(path)}", "green")


                except Exception as e:


                    print(f"Wrapper Err: {e}")


                    self.update_status_bar(f"❌ 启动失败: {str(e)}", "red")


                


                self.is_executing = False
                self.current_executing_path = None # [NEW] Clear current script
                self.root.after(0, lambda: self.loop_var.set(1)) # [NEW] Reset loop to 1


                if self.engine.stop_signal:


                    self.update_run_status("⛔ 已停止", "red")


                else: 


                    self.update_run_status("✅ 启动结束", "#808080")





            threading.Thread(target=run_binary_wrapper, daemon=True).start()


            return





        def run():


            self.update_status_bar(f"⏳ 正在执行: {os.path.basename(path)}", "green")


            self.update_run_status(f"▶ 运行中: {os.path.basename(path)}", "blue")


            try:


                for _ in range(loop_cnt):


                    if self.engine.stop_signal: break


                    self.engine.execute_script(path, self.speed_var.get())


            except Exception as e: print(f"Exec Err: {e}")


            self.is_executing = False
            self.current_executing_path = None # [NEW] Clear current script
            self.root.after(0, lambda: self.loop_var.set(1)) # [NEW] Reset loop to 1


            if self.engine.stop_signal: 


                self.update_status_bar("⛔ 脚本已强制终止", "red")


                self.update_run_status("⛔ 已停止", "red")


            else: 


                self.update_status_bar("✅ 执行完毕", "black")


                self.update_run_status("✅ 运行结束", "black")


        threading.Thread(target=run, daemon=True).start()






    def force_stop(self):
        if hasattr(self, 'recorder') and self.recorder and getattr(self.recorder, 'recording', False):
            self.root.after(0, self.toggle_record)
        
        # [NEW] Always clear schedule and reset loop on stop signal
        self.root.after(0, self.disable_scheduled_script)
        self.root.after(0, lambda: self.loop_var.set(1))

        if hasattr(self, 'is_executing') and self.is_executing:
            if not getattr(self.engine, 'stop_signal', True):
                self.engine.stop_signal = True
                if getattr(self.engine, 'step_mode', False):
                    self.engine.step_event.set()
                print("STOP SIGNAL SENT (BUTTON)")
                self.root.after(0, lambda: self.update_status_bar("⛔ 正在强制停止...", "red"))

    def setup_hotkeys(self):


        def on_f11():


            # [Modified] F11: Simply Pause/Resume, NO Step Mode Logic here as moved to Floating Window


            if self.is_executing and not self.engine.step_mode:


                self.engine.paused = not self.engine.paused; state_text = "⏸ 已暂停" if self.engine.paused else "▶ 继续运行"


                self.root.after(0, lambda: self.update_status_bar(state_text, "blue"))





        def on_stop():
            if self.recorder.recording: self.root.after(0, self.toggle_record)
            
            # [NEW] Always clear schedule and reset loop on stop signal
            self.root.after(0, self.disable_scheduled_script)
            self.root.after(0, lambda: self.loop_var.set(1))

            if self.is_executing:
                if not self.engine.stop_signal:
                    self.engine.stop_signal = True; 
                    # [NEW] Unblock step wait if in step mode
                    if self.engine.step_mode: self.engine.step_event.set()
                    print("STOP SIGNAL SENT"); self.root.after(0, lambda: self.update_status_bar("⛔ 正在强制停止...", "red"))


        


        # [Modified] Removed F11 binding for Step Execution, now only Pause


        hotkey_map = { '<f11>': on_f11, '<f12>': on_stop, '<ctrl>+<f12>': on_stop }


        try: self.global_hotkey_listener = keyboard.GlobalHotKeys(hotkey_map); self.global_hotkey_listener.start()


        except Exception as e: print(f"Global Hotkey Init Err: {e}")


        def on_click(x, y, button, pressed):


            if pressed and button == mouse.Button.middle: on_stop()


        try: self.global_mouse_listener = mouse.Listener(on_click=on_click); self.global_mouse_listener.start()


        except: pass


        


    def on_close(self):


        self.save_settings()


        if self.script_window: self.script_window.destroy() # 确保关闭子窗口


        if self.global_hotkey_listener: self.global_hotkey_listener.stop()


        if self.custom_hotkey_listener: self.custom_hotkey_listener.stop()


        if self.global_mouse_listener: self.global_mouse_listener.stop()


        self.engine.stop_signal = True; self.root.destroy(); os._exit(0)





if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='AnJian2025 自动化工具')
    parser.add_argument('--run', type=str, help='执行指定脚本路径')
    parser.add_argument('--loop', type=int, default=1, help='循环次数 (默认 1)')
    args = parser.parse_args()

    if args.run:
        script_path = args.run.strip()
        
        if not os.path.exists(script_path):
            if os.path.exists(script_path + ".txt"): 
                script_path += ".txt"
            elif os.path.exists(script_path + ".ks"): 
                script_path += ".ks"
        
        if not os.path.exists(script_path):
            print(f"错误：找不到脚本文件 {args.run}")
            sys.exit(1)

        root = tk.Tk()
        root.withdraw()
        app = App(root)
        
        try:
            print(f"开始执行脚本: {script_path}")
            for i in range(args.loop):
                if i > 0:
                    time.sleep(0.5)
                app.engine.execute_script(script_path)
            print("脚本执行完成")
        except Exception as e:
            print(f"执行出错: {e}")
        
        root.destroy()
        sys.exit(0)

    try:
        mutex_name = "AnJian20251212_Unique_Instance_Mutex"
        # 创建互斥体，用于检测程序是否已在运行
        my_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        
        if ctypes.windll.kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
            # 如果程序已经在运行，尝试寻找并激活已有窗口
            def enum_handler(hwnd, _):
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                        title = buf.value
                        # 匹配主窗口标题或编辑窗口标题
                        if "anjian2025 - 主控台" in title or "编辑: " in title:
                            # 1. 恢复窗口（如果是最小化的）
                            if ctypes.windll.user32.IsIconic(hwnd):
                                ctypes.windll.user32.ShowWindow(hwnd, 9) # SW_RESTORE
                            else:
                                ctypes.windll.user32.ShowWindow(hwnd, 5) # SW_SHOW
                            # 2. 置于顶层并激活
                            ctypes.windll.user32.SetForegroundWindow(hwnd)
                            return False # 停止枚举
                return True
            
            # 使用 EnumWindows 遍历所有顶层窗口
            proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(enum_handler)
            ctypes.windll.user32.EnumWindows(proc, 0)
            sys.exit(0)
    except Exception as e:
        print(f"Single Instance Check Error: {e}")

    root = RootClass()
    try:
        root.deiconify()
        root.update()
        hwnd_main = ctypes.windll.user32.GetParent(root.winfo_id())
        ctypes.windll.user32.ShowWindow(hwnd_main, 5)
    except:
        pass

    app = App(root)
    root.mainloop()
