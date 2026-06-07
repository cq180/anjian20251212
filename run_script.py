#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
脚本执行器 - 参考 anjian20251212.py 实现
支持所有按键精灵格式的脚本指令

用法: python run_script.py <脚本路径> [循环次数]
示例: python run_script.py "D:\\game\\按键精灵2014\\screen\\cmd\\tuiyiceng" 3
"""

import pyautogui
import time
import sys
import os
import re
import ctypes
import subprocess

# --- 高分屏适配 (关键!) ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

# --- 安全设置 ---
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

# --- DirectInput/SendInput 结构定义 ---
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class INPUT_I(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("ii", INPUT_I)
    ]

# 常量
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_ABSOLUTE = 0x8000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_EXTENDEDKEY = 0x0001

# DirectInput ScanCodes
SC_MAP = {
    'escape': 0x01, '1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05, '5': 0x06,
    '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A, '0': 0x0B,
    'a': 0x1E, 'b': 0x30, 'c': 0x2E, 'd': 0x20, 'e': 0x12, 'f': 0x21,
    'g': 0x22, 'h': 0x23, 'i': 0x17, 'j': 0x24, 'k': 0x25, 'l': 0x26,
    'm': 0x32, 'n': 0x31, 'o': 0x18, 'p': 0x19, 'q': 0x10, 'r': 0x13,
    's': 0x1F, 't': 0x14, 'u': 0x16, 'v': 0x2F, 'w': 0x11, 'x': 0x2D,
    'y': 0x15, 'z': 0x2C,
    'f1': 0x3B, 'f2': 0x3C, 'f3': 0x3D, 'f4': 0x3E, 'f5': 0x3F,
    'f6': 0x40, 'f7': 0x41, 'f8': 0x42, 'f9': 0x43, 'f10': 0x44,
    'f11': 0x57, 'f12': 0x58,
    'enter': 0x1C, 'space': 0x39, 'tab': 0x0F, 'backspace': 0x0E,
    'ctrl': 0x1D, 'ctrlleft': 0x1D, 'ctrlright': 0x1D,
    'shift': 0x2A, 'shiftleft': 0x2A, 'shiftright': 0x36,
    'alt': 0x38, 'altleft': 0x38, 'altright': 0x38,
    'up': 0xC8, 'down': 0xD0, 'left': 0xCB, 'right': 0xCD,
}

def get_screen_size():
    """获取屏幕尺寸"""
    SM_CXSCREEN = 0
    SM_CYSCREEN = 1
    w = ctypes.windll.user32.GetSystemMetrics(SM_CXSCREEN)
    h = ctypes.windll.user32.GetSystemMetrics(SM_CYSCREEN)
    return w, h

def send_mouse_event(flags, x=None, y=None):
    """使用 SendInput 发送鼠标事件"""
    extra = ctypes.pointer(ctypes.c_ulong(0))
    
    if x is not None and y is not None:
        flags |= MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
        screen_w, screen_h = get_screen_size()
        dx = int(x * 65535 / screen_w)
        dy = int(y * 65535 / screen_h)
    else:
        dx = 0
        dy = 0
    
    mi = MOUSEINPUT(dx, dy, 0, flags, 0, extra)
    ii = INPUT_I()
    ii.mi = mi
    inp = INPUT(ctypes.c_ulong(INPUT_MOUSE), ii)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))

def mouse_move(x, y):
    """移动鼠标到绝对坐标"""
    send_mouse_event(0, x, y)
    smart_sleep(0.02)

def mouse_click(button='left', count=1):
    """鼠标点击"""
    for _ in range(count):
        if button == 'left':
            send_mouse_event(MOUSEEVENTF_LEFTDOWN)
            smart_sleep(0.05)
            send_mouse_event(MOUSEEVENTF_LEFTUP)
        elif button == 'right':
            send_mouse_event(MOUSEEVENTF_RIGHTDOWN)
            smart_sleep(0.05)
            send_mouse_event(MOUSEEVENTF_RIGHTUP)
        elif button == 'middle':
            send_mouse_event(MOUSEEVENTF_MIDDLEDOWN)
            smart_sleep(0.05)
            send_mouse_event(MOUSEEVENTF_MIDDLEUP)
        smart_sleep(0.05)

def mouse_down(button='left'):
    if button == 'left':
        send_mouse_event(MOUSEEVENTF_LEFTDOWN)
    elif button == 'right':
        send_mouse_event(MOUSEEVENTF_RIGHTDOWN)

def mouse_up(button='left'):
    if button == 'left':
        send_mouse_event(MOUSEEVENTF_LEFTUP)
    elif button == 'right':
        send_mouse_event(MOUSEEVENTF_RIGHTUP)

def send_key(scancode, press=True):
    """使用扫描码发送按键"""
    extra = ctypes.pointer(ctypes.c_ulong(0))
    flags = KEYEVENTF_SCANCODE
    if not press:
        flags |= KEYEVENTF_KEYUP
    if scancode > 0x7F:
        flags |= KEYEVENTF_EXTENDEDKEY
    
    ki = KEYBDINPUT(0, scancode, flags, 0, extra)
    ii = INPUT_I()
    ii.ki = ki
    inp = INPUT(ctypes.c_ulong(INPUT_KEYBOARD), ii)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))

def key_press(key_name):
    key = key_name.lower()
    sc = SC_MAP.get(key)
    if sc:
        send_key(sc, True)
    else:
        pyautogui.keyDown(key)

def key_release(key_name):
    key = key_name.lower()
    sc = SC_MAP.get(key)
    if sc:
        send_key(sc, False)
    else:
        pyautogui.keyUp(key)

def key_click(key_name):
    key_press(key_name)
    smart_sleep(0.05)
    key_release(key_name)

# --- 脚本解析 ---

def parse_line(line):
    if "'" in line:
        line = line.split("'", 1)[0]
    if "//" in line:
        line = line.split("//", 1)[0]
    line = line.strip()
    if not line:
        return None, None
    if line.lower().startswith("end if"):
        return "endif", ""
    
    # 支持 Func(args) 格式 (无空格)
    if "(" in line and " " not in line.split("(", 1)[0]:
        idx = line.find("(")
        cmd = line[:idx].strip().lower()
        args = line[idx:].strip()
        return cmd, args

    parts = line.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    return cmd, args

def evaluate_expr(expr, variables):
    expr = re.sub(r'\bAnd\b', 'and', expr, flags=re.IGNORECASE)
    expr = re.sub(r'\bOr\b', 'or', expr, flags=re.IGNORECASE)
    try:
        return eval(expr, {"__builtins__": None}, variables)
    except:
        return 0

def smart_read_file(filepath):
    for enc in ['utf-8', 'gbk', 'gb18030']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read()
        except:
            continue
    return None

def check_stop():
    """检查是否触发了停止方案 (F12 或 鼠标移动到左上角)"""
    # 1. 检查 F12 键
    if ctypes.windll.user32.GetAsyncKeyState(0x7B) & 0x8000:
        return True
    # 2. 检查 FailSafe (鼠标到屏幕左上角)
    try:
        x, y = pyautogui.position()
        if x == 0 and y == 0:
            return True
    except:
        pass
    return False

def smart_sleep(seconds):
    """智能延时：支持在延时期间响应停止信号"""
    end_time = time.time() + seconds
    while time.time() < end_time:
        if check_stop():
            raise KeyboardInterrupt("用户终止")
        # 即使是极短的延时也要稍微休眠一下防止 CPU 占用过高
        remaining = end_time - time.time()
        if remaining > 0:
            time.sleep(min(0.01, remaining))

# --- 主执行函数 ---

def parse_findpic_args(args, variables):
    path = ""
    region = None
    conf = 0.9
    var_x = "intX"
    var_y = "intY"

    path_match = re.search(r'["\']([^"\']+)["\']', args)
    if path_match:
        path = path_match.group(1)
        left_args = args[:path_match.start()]
        right_args = args[path_match.end():]

        l_parts = [x.strip() for x in left_args.split(',') if x.strip()]
        if len(l_parts) >= 4:
            try:
                x1 = int(evaluate_expr(l_parts[0], variables))
                y1 = int(evaluate_expr(l_parts[1], variables))
                x2 = int(evaluate_expr(l_parts[2], variables))
                y2 = int(evaluate_expr(l_parts[3], variables))
                region = (x1, y1, max(1, x2 - x1), max(1, y2 - y1))
            except Exception:
                region = None

        r_parts = [x.strip() for x in right_args.split(',') if x.strip()]
        if len(r_parts) >= 1:
            try:
                conf = float(r_parts[0])
            except Exception:
                conf = 0.9
        if len(r_parts) >= 2:
            var_x = r_parts[1]
        if len(r_parts) >= 3:
            var_y = r_parts[2]
    else:
        parts = [x.strip() for x in args.split(',')]
        if len(parts) >= 8:
            try:
                x1 = int(evaluate_expr(parts[0], variables))
                y1 = int(evaluate_expr(parts[1], variables))
                x2 = int(evaluate_expr(parts[2], variables))
                y2 = int(evaluate_expr(parts[3], variables))
                region = (x1, y1, max(1, x2 - x1), max(1, y2 - y1))
            except Exception:
                region = None
            path = parts[4].strip('"').strip("'")
            try:
                conf = float(parts[5])
            except Exception:
                conf = 0.9
            var_x = parts[6]
            var_y = parts[7]

    return path, region, conf, var_x, var_y

def find_pic(args, variables):
    path, region, conf, var_x, var_y = parse_findpic_args(args, variables)
    found_x, found_y = -1, -1

    if not path or not os.path.exists(path):
        print(f"  FindPic missing image: {path}")
        variables[var_x] = found_x
        variables[var_y] = found_y
        return found_x, found_y

    print(f"  FindPic search: {path} region={region} confidence={conf}")
    box = None
    try:
        box = pyautogui.locateOnScreen(path, confidence=conf, region=region, grayscale=True)
    except Exception as e:
        print(f"  FindPic confidence search failed: {e}")
        try:
            box = pyautogui.locateOnScreen(path, region=region, grayscale=True)
        except Exception as e2:
            print(f"  FindPic exact search failed: {e2}")

    if box:
        point = pyautogui.center(box)
        found_x, found_y = int(point.x), int(point.y)

    variables[var_x] = found_x
    variables[var_y] = found_y
    print(f"  FindPic result: {found_x}, {found_y}")
    return found_x, found_y

def execute_script(script_path, loop_count=1):
    if not os.path.exists(script_path):
        for ext in ['.txt', '.ks']:
            if os.path.exists(script_path + ext):
                script_path = script_path + ext
                break
    
    if not os.path.exists(script_path):
        print(f"[ERROR] Script not found: {script_path}")
        return False
    
    content = smart_read_file(script_path)
    if content is None:
        print(f"[ERROR] Cannot read file: {script_path}")
        return False
    
    lines = content.splitlines()
    print(f"[OK] Loaded: {os.path.basename(script_path)} ({len(lines)} lines)")
    print(f"[OK] Loops: {loop_count}")
    print(f"[OK] Starting in 3 seconds... (F12 or mouse to top-left to stop)")
    smart_sleep(3)
    
    variables = {}
    
    try:
        for loop in range(loop_count):
            if loop_count > 1:
                print(f"\n--- Loop {loop + 1}/{loop_count} ---")
            
            pc = 0
            while pc < len(lines):
                if check_stop():
                    print("\n[STOP] User requested stop")
                    return False
                
                cmd, args = parse_line(lines[pc])
                if not cmd:
                    pc += 1
                    continue
                
                # 处理带括号的参数，如 Func(args) 格式
                args = args.strip()
                if args.startswith('(') and args.endswith(')'):
                    args = args[1:-1].strip()
                
                if cmd == 'if':
                    condition = args
                    if condition.lower().endswith('then'):
                        condition = condition[:-4].strip()
                    if not evaluate_expr(condition, variables):
                        stack_depth = 0
                        for scan_i in range(pc + 1, len(lines)):
                            sc_cmd, _ = parse_line(lines[scan_i])
                            if not sc_cmd:
                                continue
                            if sc_cmd == 'if':
                                stack_depth += 1
                            elif sc_cmd == 'endif':
                                if stack_depth == 0:
                                    pc = scan_i
                                    break
                                stack_depth -= 1

                elif cmd == 'endif':
                    pass

                elif cmd == 'findpic':
                    find_pic(args, variables)

                elif cmd == 'moveto':
                    parts = args.replace(' ', '').split(',')
                    if len(parts) >= 2:
                        x = int(evaluate_expr(parts[0], variables))
                        y = int(evaluate_expr(parts[1], variables))
                        mouse_move(x, y)
                        print(f"  MoveTo {x}, {y}")
                
                elif cmd == 'leftclick':
                    count = int(args) if args.strip().isdigit() else 1
                    mouse_click('left', count)
                    print(f"  LeftClick {count}")
                
                elif cmd == 'rightclick':
                    count = int(args) if args.strip().isdigit() else 1
                    mouse_click('right', count)
                    print(f"  RightClick {count}")
                
                elif cmd == 'middleclick':
                    count = int(args) if args.strip().isdigit() else 1
                    mouse_click('middle', count)
                    print(f"  MiddleClick {count}")
                
                elif cmd == 'leftdown':
                    mouse_down('left')
                    print(f"  LeftDown")
                
                elif cmd == 'leftup':
                    mouse_up('left')
                    print(f"  LeftUp")
                
                elif cmd == 'rightdown':
                    mouse_down('right')
                    print(f"  RightDown")
                
                elif cmd == 'rightup':
                    mouse_up('right')
                    print(f"  RightUp")
                
                elif cmd == 'delay':
                    ms = int(args) if args.strip().isdigit() else 100
                    smart_sleep(ms / 1000.0)
                    print(f"  Delay {ms}ms")
                
                elif cmd == 'keypress':
                    key = args.strip()
                    key_click(key)
                    print(f"  KeyPress {key}")
                
                elif cmd == 'keydown':
                    key = args.strip()
                    key_press(key)
                    print(f"  KeyDown {key}")
                
                elif cmd == 'keyup':
                    key = args.strip()
                    key_release(key)
                    print(f"  KeyUp {key}")
                
                elif cmd == 'mousewheel':
                    val = int(args) if args.strip().lstrip('-').isdigit() else 0
                    if -10 < val < 10:
                        val *= 120
                    pyautogui.scroll(val)
                    print(f"  MouseWheel {val}")
                
                elif cmd == 'msgbox':
                    print(f"  MsgBox: {args}")
                
                elif cmd == 'call':
                    raw_args = args.strip()
                    if raw_args.startswith('(') and raw_args.endswith(')'):
                        raw_args = raw_args[1:-1].strip()
                    sub_path = raw_args.strip('"').strip("'")
                    print(f"  Call: {sub_path}")
                    execute_script(sub_path, 1)
                
                elif cmd == 'stop':
                    target = args.strip()
                    subprocess.run(f'taskkill /F /IM "*{target}*" /FI "WINDOWTITLE eq *{target}*"', 
                                   shell=True, capture_output=True)
                    print(f"  Stop: {target}")
                
                elif cmd == 'runapp':
                    # 处理带括号的情况，如 RunApp ("path")
                    raw_args = args.strip()
                    if raw_args.startswith('(') and raw_args.endswith(')'):
                        raw_args = raw_args[1:-1].strip()
                    
                    app_path = raw_args.strip('"').strip("'")
                    if not app_path:
                        pc += 1
                        continue

                    if os.path.exists(app_path):
                        try:
                            # 尝试使用 os.startfile (关联程序启动)
                            os.startfile(app_path)
                            print(f"  RunApp: {app_path}")
                        except Exception as e:
                            # 降级到 subprocess
                            subprocess.Popen(app_path, shell=True)
                            print(f"  RunApp (fallback): {app_path}")
                    else:
                        # 处理带参数的情况或命令行程序
                        try:
                            subprocess.Popen(app_path, shell=True)
                            print(f"  RunApp (shell): {app_path}")
                        except Exception as e:
                            print(f"  RunApp Failed: {app_path} -> {e}")
                
                elif cmd == 'copypaste':
                    key_press('ctrl')
                    smart_sleep(0.05)
                    key_click('v')
                    smart_sleep(0.05)
                    key_release('ctrl')
                    print(f"  CopyPaste")
                
                pc += 1
        
        print(f"\n[DONE] Script completed!")
        return True
    
    except pyautogui.FailSafeException:
        print("\n[STOP] FailSafe triggered")
        return False
    except KeyboardInterrupt:
        print("\n[STOP] User interrupted")
        return False
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_script.py <script_path> [loop_count] [speed]")
        print("Example: python run_script.py \"D:\\game\\script.txt\" 5 1.5")
        sys.exit(1)
    
    script_path = sys.argv[1]
    loop_count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    speed = 1.0  # 已废弃，不再支持速度参数
    
    execute_script(script_path, loop_count)
