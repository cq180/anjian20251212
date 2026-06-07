import tkinter as tk
from tkinter import ttk
import configparser
import os
import sys
import subprocess
import ctypes
import re

# 获取当前脚本或exe所在目录
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(application_path, "xs_config.ini")
ICON_FILE = os.path.join(application_path, "pic", "1765879656.png")
CONFIG_TXT_FILE = os.path.join(application_path, "xuanshang.txt")

def load_rules_from_config():
    """从txt配置文件加载规则"""
    rules = {}
    if not os.path.exists(CONFIG_TXT_FILE):
        return rules
    
    try:
        with open(CONFIG_TXT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                key, values = line.split("=", 1)
                key = key.strip()
                # 使用中文逗号、英文逗号或斜杠分隔
                # 先把 / 替换成 , 再把 ， 替换成 ,
                normalized_values = values.replace("/", ",").replace("，", ",")
                keywords = [k.strip() for k in normalized_values.split(",") if k.strip()]
                
                # 如果key已存在，则追加rules，否则新建
                if key in rules:
                    rules[key].extend(keywords)
                else:
                    rules[key] = keywords
    except Exception as e:
        print(f"读取规则文件失败: {e}")
    return rules

# ================= 1. 核心规则字典 =================
# 动态加载规则
RULES = load_rules_from_config()

class ExtractionPanel(ttk.Frame):
    """
    封装了“输入”和“提取结果”的功能模块
    布局：Title+Button 一行 / 文本框 / 结果框
    """
    def __init__(self, parent, title_prefix="", btn_text="一键粘贴"):
        super().__init__(parent)
        self.title_prefix = title_prefix
        self.btn_text = btn_text
        self.setup_ui()

    def setup_ui(self):
        # === 1. 头部行：标注 + 粘贴按钮 ===
        header_frame = tk.Frame(self, bg="#2b2b2b")
        header_frame.pack(fill="x", pady=(0, 5))

        # 标注文字
        lbl_title = tk.Label(header_frame, text=self.title_prefix, 
                             font=("微软雅黑", 11, "bold"), fg="#ffffff", bg="#2b2b2b")
        lbl_title.pack(side="left", padx=(0, 10))

        # 粘贴按钮
        self.btn_paste = tk.Button(header_frame, text=self.btn_text, bg="#6c5ce7", fg="white",
                                   font=("微软雅黑", 10), command=self.paste_from_clipboard,
                                   relief="flat", cursor="hand2")
        self.btn_paste.pack(side="left")

        # === 2. 输入框 (直接下方) ===
        self.input_text = tk.Text(self, height=4, bg="#1e1e1e", fg="#cccccc", 
                                  font=("微软雅黑", 12), insertbackground="white", 
                                  relief="flat", wrap=tk.WORD)
        self.input_text.pack(fill="both", expand=True, pady=(0, 5))

        # === 3. 提取结果 (5个横向文本框) ===
        # 原 LabelFrame(text="提取结果") 改为 Frame，去除标题行
        self.output_frame = ttk.Frame(self)
        self.output_frame.pack(fill="x", pady=(0, 5))
        
        self.entries = []
        self.grid_container = ttk.Frame(self.output_frame)
        self.grid_container.pack(fill="x", expand=True)
        
        # 创建5个文本框和对应的复制按钮
        for i in range(5):
            # 列权重，保证均匀分布
            self.grid_container.columnconfigure(i, weight=1)
            
            # 文本框 (使用 Entry，居中显示)
            entry = tk.Entry(self.grid_container, font=("微软雅黑", 14, "bold"), 
                             bg="#333333", fg="#00ffcc", justify="center", relief="flat")
            entry.grid(row=0, column=i, padx=5, pady=(5, 5), sticky="ew")
            self.entries.append(entry)
            
            # 复制按钮
            btn = tk.Button(self.grid_container, text="复制", bg="#00b894", fg="white",
                            font=("微软雅黑", 9), relief="flat", cursor="hand2",
                            command=lambda idx=i: self.copy_entry(idx))
            btn.grid(row=1, column=i, padx=5, pady=(0, 5), sticky="ew")

    def paste_from_clipboard(self):
        """一键粘贴剪贴板内容"""
        try:
            text = self.winfo_toplevel().clipboard_get()
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", text)
            # 自动提取
            self.extract_and_display()
        except Exception as e:
            print(f"粘贴失败: {e}")

    def extract_monsters_list(self, raw_text):
        """核心处理逻辑：返回提取到的式神列表"""
        if not raw_text: return []
        
        candidates = []
        # 1. 查找所有 "击败...个" 的模式
        matches = list(re.finditer(r'击败\s*(\d+)\s*个', raw_text))
        
        # 如果找到了“击败...个”，则以数量为核心寻找最近的关键词
        if matches:
            for i, m in enumerate(matches):
                try:
                    count = int(m.group(1))
                    
                    # 确定搜索范围：当前匹配的前后区域
                    # 前向范围：上一个匹配的结束 ~ 当前匹配的开始
                    prev_end = matches[i-1].end() if i > 0 else 0
                    current_start = m.start()
                    pre_segment = raw_text[prev_end:current_start]
                    
                    # 后向范围：当前匹配的结束 ~ 下一个匹配的开始
                    current_end = m.end()
                    next_start = matches[i+1].start() if i < len(matches) - 1 else len(raw_text)
                    post_segment = raw_text[current_end:next_start]
                    
                    best_name = None
                    min_dist = float('inf')
                    
                    # 检查 RULES 中的关键词
                    for name, keywords in RULES.items():
                        for kw in keywords:
                            # 1. 在前面找 (取最后一个匹配，距离因为是倒序搜索)
                            # distance = current_start - (idx + len(kw))
                            # rfind找最后一个以确保离match最近
                            p_idx = pre_segment.rfind(kw)
                            if p_idx != -1:
                                dist = len(pre_segment) - (p_idx + len(kw)) # 距离 match start
                                if dist < min_dist:
                                    min_dist = dist
                                    best_name = name

                            # 2. 在后面找
                            # distance = idx
                            s_idx = post_segment.find(kw)
                            if s_idx != -1:
                                dist = s_idx # 距离 match end
                                if dist < min_dist:
                                    min_dist = dist
                                    best_name = name
                    
                    if best_name:
                        candidates.append({'name': best_name, 'count': count})
                except Exception:
                    pass
        # 2. 全文关键词匹配（作为补充）
        # 无论先前是否找到“击败...个”，都再次扫描全文
        # 这样确保 "自己击败鲤鱼精" 这种没有数量的也能被提出来
        found_items = []
        for name, keywords in RULES.items():
            for kw in keywords:
                idx = raw_text.find(kw)
                if idx != -1:
                    # 记录首次出现位置，用于大致排序
                    found_items.append({'name': name, 'idx': idx})
        
        # 按出现位置排序
        found_items.sort(key=lambda x: x['idx'])
        for item in found_items:
            candidates.append({'name': item['name'], 'count': 0}) # 默认数量0

        # 3. 去重
        unique_candidates = []
        seen = set()
        for item in candidates:
            if item['name'] not in seen:
                unique_candidates.append(item)
                seen.add(item['name'])
        
        # 4. 排序：按 N 的数值 “从小到大”
        # 如果是 fallback 模式 count 都是 0，则保持原有顺序 (按出现位置)
        unique_candidates.sort(key=lambda x: x['count'])
        
        return [x['name'] for x in unique_candidates]

    def extract_and_display(self):
        """提取文字并填充到5个文本框"""
        raw = self.input_text.get("1.0", tk.END)
        results = self.extract_monsters_list(raw)
        
        final_list = []
        
        # 逻辑：大于等于5个就按照5个填写
        if len(results) >= 5:
            final_list = results[:5]
        # 不到5个就按照最后一个补全
        elif len(results) > 0:
            final_list = results[:]
            while len(final_list) < 5:
                final_list.append(final_list[-1]) # 补全最后一个
        else:
            final_list = [""] * 5 # 没有结果
            
        # 填充到UI
        for i, entry in enumerate(self.entries):
            entry.delete(0, tk.END)
            # 确保不越界 (防御性编程)
            if i < len(final_list):
                 entry.insert(0, final_list[i])

    def copy_entry(self, idx):
        """复制指定索引的文本框内容"""
        text = self.entries[idx].get()
        if text:
            self.copy_to_clipboard(text)
            print(f"Copied: {text}")

    def copy_to_clipboard(self, text):
        """复制文字到剪贴板"""
        self.winfo_toplevel().clipboard_clear()
        self.winfo_toplevel().clipboard_append(text)
        self.winfo_toplevel().update() # 保持剪贴板内容


class DualTextApp:
    def __init__(self, root):
        self.root = root
        self.root.title("阴阳师文本提取助手")
        if os.path.exists(ICON_FILE):
            try:
                icon = tk.PhotoImage(file=ICON_FILE)
                self.root.iconphoto(False, icon)
            except Exception as e:
                print(f"图标加载失败: {e}")
        self.load_config()
        self.root.configure(bg="#2b2b2b")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 启动外部 OCR 程序
        self.launch_ocr()

    def launch_ocr(self):
        """
        通过 explorer.exe 启动外部程序，切断环境继承。
        """
        exe_path = r"D:\game\UmiOCR\Umi-OCR.exe"
        if os.path.exists(exe_path):
            try:
                # 使用 explorer.exe 启动，确保完全隔离环境
                subprocess.Popen(["explorer.exe", exe_path])
                print(f"已请求系统启动: {exe_path}")
            except Exception as e:
                print(f"启动 OCR 失败: {e}")
        else:
            print(f"未找到 OCR 程序: {exe_path}")

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", background="#2b2b2b", foreground="#ffffff", font=("微软雅黑", 10))
        style.configure("TButton", font=("微软雅黑", 11, "bold"))
        style.configure("TFrame", background="#2b2b2b")
        # style.configure("TLabelframe", ...) # Removed as LabelFrame is no longer used for results
        
        # === 主布局 ===
        self.main_pane = ttk.Frame(root)
        self.main_pane.pack(fill="both", expand=True, padx=10, pady=10)
        
        # === 模块一：情况一 ===
        self.panel1 = ExtractionPanel(self.main_pane, title_prefix="情况一", btn_text="粘贴1")
        self.panel1.pack(fill="both", expand=True, pady=(0, 10))
        
        # === 模块二：情况二 ===
        self.panel2 = ExtractionPanel(self.main_pane, title_prefix="情况二", btn_text="粘贴2")
        self.panel2.pack(fill="both", expand=True)

    def load_config(self):
        """加载配置文件，设置窗口大小和位置"""
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            try:
                config.read(CONFIG_FILE)
                if "Window" in config and "geometry" in config["Window"]:
                    geometry = config["Window"]["geometry"]
                    self.root.geometry(geometry)
                    return
            except Exception as e:
                print(f"配置文件读取失败: {e}")
        
        # 默认值
        self.root.geometry("720x750")

    def save_config(self):
        """保存当前窗口大小和位置到配置文件"""
        config = configparser.ConfigParser()
        config["Window"] = {
            "geometry": self.root.geometry()
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                config.write(f)
        except Exception as e:
            print(f"配置文件保存失败: {e}")

    def on_close(self):
        """窗口关闭时触发"""
        self.save_config()
        self.root.destroy()


if __name__ == "__main__":
    # 互斥锁逻辑
    mutex_name = "Global\\Xuanshang_App_Instance_Mutex_2025"
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    # ERROR_ALREADY_EXISTS = 183
    if kernel32.GetLastError() == 183:
        # 已经有一个实例在运行，直接退出，不提示
        sys.exit(0)

    root = tk.Tk()
    app = DualTextApp(root)
    root.mainloop()