# -*- coding: utf-8 -*-
"""
C++ 变量名混淆工具
功能：
  1. GUI 模式：双击 exe，选择单个 .cpp 文件处理
  2. 拖拽模式：把文件/文件夹拖到 exe 图标上，批量处理
  3. 文件夹模式：扫描文件夹内所有源文件，输出到 output 下按规则命名的子文件夹

关键修复：
  - 保护 #include 行，避免 stdio.h 等头文件名被误替换
  - 保护字符串字面量和注释
  - 支持自定义混淆模式（random / indexed / prefix_random / pool / hash）
  - 支持自定义输出文件夹命名规则

配置：config.json（首次运行自动生成）
"""

import os
import re
import json
import random
import string
import sys
import hashlib
from datetime import datetime

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ============================================================
# 一、默认配置
# ============================================================
DEFAULT_CONFIG = {
    # 输出根目录（相对或绝对路径均可）
    "output_dir": "./output",

    # 单个文件的输出命名规则
    # 占位符：{name} 原名  {ext} 后缀  {date} 日期  {time} 时间  {rand} 随机串
    "filename_rule": "{name}_obf{ext}",

    # 批量模式下子文件夹命名规则
    # 占位符：{src} 源文件夹名  {date}  {time}  {rand}
    "folder_name_rule": "batch_{date}_{time}_{rand}",

    # 视为源文件的后缀
    "source_extensions": [".cpp", ".cc", ".cxx"],

    # 是否递归扫描子文件夹
    "recursive": True,

    # 变量命名规则
    "naming_rule": {
        # 命名模式：
        #   random         纯随机字符串
        #   indexed        前缀 + 递增编号（v1, v2, v3 ...）
        #   prefix_random  前缀 + 随机字符串
        #   pool           从自定义词库中随机选词
        #   hash           基于原名字的哈希（同名同结果）
        "mode": "random",

        # 新名字前缀（所有模式通用）
        "prefix": "",

        # 随机部分的长度（random / prefix_random / hash 模式有效）
        "length": 8,

        # 随机字符集（random / prefix_random / hash 模式有效）
        #   lowercase  a-z
        #   uppercase  A-Z
        #   letters    a-z + A-Z
        #   alnum      a-z + A-Z + 0-9
        "charset": "lowercase",

        # indexed 模式起始编号
        "start_index": 1,

        # pool 模式使用的自定义词库
        "word_pool": [
            "alpha", "beta", "gamma", "delta", "epsilon",
            "zeta", "eta", "theta", "iota", "kappa",
            "lambda", "mu", "nu", "xi", "omicron",
            "pi", "rho", "sigma", "tau", "upsilon"
        ],

        # pool 模式：词库用完后是否加数字后缀
        "word_pool_suffix": True
    },

    # 是否保留全大写宏名（如 MAX_SIZE）
    "keep_uppercase_macros": True,

    # 是否保护 #include 行（强烈建议 true）
    "protect_includes": True,

    # 额外排除的标识符（永不替换）
    "exclude": [],

    # 若不为空，则只替换列表内的标识符
    "include_only": []
}


CONFIG_FILE = "config.json"


# ============================================================
# 二、C++ 关键字表
#    这些标识符永不替换
# ============================================================
CPP_KEYWORDS = {
    # 关键字
    "alignas","alignof","and","and_eq","asm","auto","bitand","bitor","bool",
    "break","case","catch","char","char16_t","char32_t","class","compl",
    "const","constexpr","const_cast","continue","decltype","default","delete",
    "do","double","dynamic_cast","else","enum","explicit","export","extern",
    "false","float","for","friend","goto","if","inline","int","long","mutable",
    "namespace","new","noexcept","not","not_eq","nullptr","operator","or",
    "or_eq","private","protected","public","register","reinterpret_cast",
    "return","short","signed","sizeof","static","static_assert","static_cast",
    "struct","switch","template","this","thread_local","throw","true","try",
    "typedef","typeid","typename","union","unsigned","using","virtual","void",
    "volatile","wchar_t","while","xor","xor_eq",
    # 预处理指令
    "include","define","ifdef","ifndef","endif","pragma","undef",
    "elif","line","error","warning",
    # 标准库常见名字
    "std","cout","cin","cerr","clog","endl","flush",
    "string","vector","map","set","pair","list","queue","stack","deque",
    "array","tuple","optional","variant","function","unique_ptr","shared_ptr",
    "printf","scanf","puts","gets","main","size_t","ssize_t",
    "int8_t","int16_t","int32_t","int64_t",
    "uint8_t","uint16_t","uint32_t","uint64_t",
    "NULL","EOF","ostream","istream","iostream",
    "algorithm","utility","fstream","sstream","iomanip","cstring","cmath",
    "cstdio","cstdlib",
}


# ============================================================
# 三、代码保护模块
#    替换前保护：#include 行、字符串字面量、注释
# ============================================================

# 匹配 #include 行：行首空白 + # + include + <文件> 或 "文件"
INCLUDE_PATTERN = re.compile(
    r'^[ \t]*#[ \t]*include[ \t]*[<"][^>"]*[>"]',
    re.MULTILINE
)

# 匹配字符串、字符、注释
STR_PATTERN = re.compile(
    r'R"\(.*?\)"'                    # C++ 原始字符串
    r'|"(?:\\.|[^"\\])*"'            # 普通字符串
    r"|'(?:\\.|[^'\\])*'"            # 字符字面量
    r'|//[^\n]*'                     # 行注释
    r'|/\*.*?\*/',                   # 块注释
    re.DOTALL
)


def protect_includes(code):
    """
    保护 #include 行，替换为占位符。
    占位符格式：\x01 + 数字 + \x01
    因为首字符不是字母/下划线，不会被 IDENT_RE 匹配到。
    """
    placeholders = []

    def repl(m):
        placeholders.append(m.group(0))
        return f"\x01{len(placeholders) - 1}\x01"

    return INCLUDE_PATTERN.sub(repl, code), placeholders


def protect_strings_and_comments(code):
    """保护字符串字面量和注释，替换为占位符（\x00 + 数字 + \x00）"""
    placeholders = []

    def repl(m):
        placeholders.append(m.group(0))
        return f"\x00{len(placeholders) - 1}\x00"

    return STR_PATTERN.sub(repl, code), placeholders


def restore_placeholders(code, include_ph, string_ph):
    """把占位符还原为原始内容"""
    # 先还原字符串/注释（\x00 标记）
    for i, ph in enumerate(string_ph):
        code = code.replace(f"\x00{i}\x00", ph)
    # 再还原 include（\x01 标记）
    for i, ph in enumerate(include_ph):
        code = code.replace(f"\x01{i}\x01", ph)
    return code


# ============================================================
# 四、标识符提取与过滤
# ============================================================

IDENT_RE = re.compile(r'\b[A-Za-z_]\w*\b')


def is_macro_like(name):
    """判断是否为全大写宏名（如 MAX_SIZE）"""
    return len(name) >= 2 and re.fullmatch(r'[A-Z_][A-Z0-9_]*', name) is not None


def filter_candidates(idents, config):
    """
    根据配置过滤标识符，返回需要替换的集合。
    过滤规则：
      - 排除 C++ 关键字和标准库名
      - 排除配置中 exclude 列表里的名字
      - keep_uppercase_macros=true 时，排除全大写宏名
      - 排除双下划线开头的名字（保留给编译器/库）
      - include_only 非空时，只保留其中的名字
    """
    if config.get("include_only"):
        return set(config["include_only"]) & idents

    exclude = set(CPP_KEYWORDS) | set(config.get("exclude", []))
    keep_macro = config.get("keep_uppercase_macros", True)

    result = set()
    for name in idents:
        if name in exclude:
            continue
        if name.startswith("__"):
            continue
        if keep_macro and is_macro_like(name):
            continue
        result.add(name)
    return result


def collect_candidates(code, config):
    """从代码中提取所有可替换的标识符"""
    idents = set(IDENT_RE.findall(code))
    return filter_candidates(idents, config)


# ============================================================
# 五、混淆名生成模块
#    支持多种模式，可扩展
# ============================================================

def _charset(name):
    """根据名称返回对应的字符集"""
    return {
        "lowercase": string.ascii_lowercase,
        "uppercase": string.ascii_uppercase,
        "letters":   string.ascii_letters,
        "alnum":     string.ascii_letters + string.digits,
    }.get(name, string.ascii_lowercase)


def _gen_random(rule, used):
    """纯随机字符串模式"""
    length = max(1, int(rule.get("length", 8)))
    cs = _charset(rule.get("charset", "lowercase"))
    while True:
        name = "".join(random.choices(cs, k=length))
        if not name[0].isdigit() and name not in used:
            return name


def _gen_prefix_random(rule, used):
    """前缀 + 随机字符串模式"""
    prefix = rule.get("prefix", "")
    length = max(1, int(rule.get("length", 8)))
    cs = _charset(rule.get("charset", "lowercase"))
    while True:
        name = prefix + "".join(random.choices(cs, k=length))
        if not name[0].isdigit() and name not in used:
            return name


def _gen_pool(rule, used):
    """从自定义词库中取词（词库用完后按 word_pool_suffix 决定策略）"""
    pool = rule.get("word_pool", [])
    prefix = rule.get("prefix", "")

    # 词库为空时退化为随机模式
    if not pool:
        return _gen_prefix_random(rule, used)

    suffix = rule.get("word_pool_suffix", True)

    # 先尝试从词库里找一个未使用的词
    for word in pool:
        candidate = prefix + word
        if candidate not in used:
            return candidate

    # 词库用完了
    if suffix:
        # 加数字后缀，从 1 开始递增
        i = 1
        while True:
            candidate = f"{prefix}{random.choice(pool)}{i}"
            if candidate not in used:
                return candidate
            i += 1
    else:
        # 循环使用词库，加随机后缀避免冲突
        while True:
            candidate = prefix + random.choice(pool)
            candidate += "".join(random.choices(string.ascii_lowercase, k=4))
            if candidate not in used:
                return candidate


def _gen_hash(name, rule):
    """
    基于原名字的哈希生成（确定性：同名同结果）。
    用哈希值的十六进制字符映射到字符集。
    """
    prefix = rule.get("prefix", "")
    length = max(1, int(rule.get("length", 8)))
    cs = _charset(rule.get("charset", "lowercase"))
    h = hashlib.md5(name.encode("utf-8")).hexdigest()

    result = []
    for i in range(length):
        idx = int(h[i % 32], 16) % len(cs)
        result.append(cs[idx])
    return prefix + "".join(result)


def generate_mapping(idents, rule):
    """
    生成 原名字 -> 混淆名 的映射。
    根据 rule["mode"] 选择不同策略。
    """
    mode = rule.get("mode", "random")
    prefix = rule.get("prefix", "")
    idx = int(rule.get("start_index", 1))

    mapping = {}
    used = set()

    for name in sorted(idents):
        if mode == "indexed":
            new_name = f"{prefix}{idx}"
            idx += 1
        elif mode == "pool":
            new_name = _gen_pool(rule, used)
        elif mode == "prefix_random":
            new_name = _gen_prefix_random(rule, used)
        elif mode == "hash":
            new_name = _gen_hash(name, rule)
        else:  # random
            new_name = _gen_random(rule, used)

        used.add(new_name)
        mapping[name] = new_name

    return mapping


# ============================================================
# 六、替换模块
# ============================================================

def apply_mapping(code, mapping):
    """把代码中所有匹配的标识符替换为映射中的名字"""
    def repl(m):
        w = m.group(0)
        return mapping.get(w, w)
    return IDENT_RE.sub(repl, code)


# ============================================================
# 七、文件名/文件夹名生成
# ============================================================

def _rand_str(n=6):
    """生成 n 位随机小写字母+数字串"""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def make_output_filename(input_path, config):
    """根据 filename_rule 生成输出文件名"""
    base = os.path.basename(input_path)
    name, ext = os.path.splitext(base)
    now = datetime.now()

    return config.get("filename_rule", "{name}_obf{ext}").format(
        name=name,
        ext=ext,
        date=now.strftime("%Y%m%d"),
        time=now.strftime("%H%M%S"),
        rand=_rand_str(6),
    )


def make_batch_folder(config, source_root):
    """根据 folder_name_rule 生成批量输出的子文件夹"""
    base_dir = config.get("output_dir", "./output")
    now = datetime.now()
    src_name = os.path.basename(os.path.abspath(source_root)) or "src"

    folder_name = config.get("folder_name_rule", "batch_{date}_{time}_{rand}").format(
        src=src_name,
        date=now.strftime("%Y%m%d"),
        time=now.strftime("%H%M%S"),
        rand=_rand_str(6),
    )

    out_dir = os.path.join(base_dir, folder_name)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


# ============================================================
# 八、单文件处理
# ============================================================

def process_file(input_path, config, out_dir_override=None, log=print):
    """
    处理单个 C++ 源文件。
    流程：
      1. 读取源文件
      2. 保护 #include 行
      3. 保护字符串和注释
      4. 提取并过滤标识符
      5. 生成混淆映射
      6. 应用映射
      7. 还原保护内容
      8. 输出到目标目录
    """
    with open(input_path, "r", encoding="utf-8") as f:
        original = f.read()

    log(f"[1/6] 读取文件：{input_path}")

    # ---- 2. 保护 #include 行 ----
    if config.get("protect_includes", True):
        code, include_ph = protect_includes(original)
        log(f"[2/6] 保护了 {len(include_ph)} 个 #include 行")
    else:
        code, include_ph = original, []
        log(f"[2/6] 未保护 #include（配置关闭）")

    # ---- 3. 保护字符串和注释 ----
    code, string_ph = protect_strings_and_comments(code)
    log(f"[3/6] 保护了 {len(string_ph)} 处字符串/注释")

    # ---- 4. 提取并过滤标识符 ----
    candidates = collect_candidates(code, config)
    log(f"[4/6] 识别到 {len(candidates)} 个待替换标识符")

    # ---- 5. 生成映射 ----
    if candidates:
        mapping = generate_mapping(candidates, config["naming_rule"])
        log(f"[5/6] 已生成混淆映射（示例前 5 个）：")
        for i, (k, v) in enumerate(sorted(mapping.items())):
            if i >= 5:
                break
            log(f"      {k}  ->  {v}")
    else:
        mapping = {}
        log(f"[5/6] 无待替换标识符")

    # ---- 6. 应用映射并还原 ----
    new_code = apply_mapping(code, mapping)
    new_code = restore_placeholders(new_code, include_ph, string_ph)
    log(f"[6/6] 已还原保护内容并生成新代码")

    # ---- 输出 ----
    out_dir = out_dir_override or config.get("output_dir", "./output")
    os.makedirs(out_dir, exist_ok=True)

    out_name = make_output_filename(input_path, config)
    out_path = os.path.join(out_dir, out_name)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(new_code)

    log(f"      输出文件：{out_path}")
    return out_path, mapping


# ============================================================
# 九、批量处理
# ============================================================

def find_source_files(folder, config):
    """在文件夹内查找所有源文件"""
    exts = tuple(e.lower() for e in config.get("source_extensions", [".cpp"]))
    recursive = config.get("recursive", True)
    result = []

    if recursive:
        for root, _, files in os.walk(folder):
            for fn in files:
                if fn.lower().endswith(exts):
                    result.append(os.path.join(root, fn))
    else:
        for fn in os.listdir(folder):
            p = os.path.join(folder, fn)
            if os.path.isfile(p) and fn.lower().endswith(exts):
                result.append(p)

    return sorted(result)


def _resolve_source_root(paths):
    """从路径列表中确定批量输出文件夹的命名来源"""
    for p in paths:
        if os.path.isdir(p):
            return p
        elif os.path.isfile(p):
            return os.path.dirname(p)
    return "."


def batch_process(paths, config, log=print):
    """
    批量处理一组路径（文件或文件夹）。
    返回：(输出目录, 成功数, 失败数)
    """
    files = []
    exts = tuple(e.lower() for e in config.get("source_extensions", [".cpp"]))

    # ---- 收集所有源文件 ----
    for p in paths:
        p = os.path.abspath(p)
        if os.path.isfile(p):
            if p.lower().endswith(exts):
                files.append(p)
            else:
                log(f"跳过（后缀不匹配）：{p}")
        elif os.path.isdir(p):
            found = find_source_files(p, config)
            log(f"扫描文件夹 {p} → 发现 {len(found)} 个源文件")
            files.extend(found)
        else:
            log(f"路径无效：{p}")

    if not files:
        log("没有找到可处理的源文件")
        return None, 0, 0

    # ---- 生成批量输出目录 ----
    src_root = _resolve_source_root(paths)
    out_dir = make_batch_folder(config, src_root)

    log(f"批量输出目录：{out_dir}")
    log("=" * 60)

    # ---- 逐个处理 ----
    ok, fail = 0, 0
    for i, f in enumerate(files, 1):
        log(f"[{i}/{len(files)}] 处理 {os.path.basename(f)}")
        try:
            process_file(f, config, out_dir_override=out_dir, log=log)
            ok += 1
        except Exception as e:
            log(f"      [失败] {e}")
            fail += 1
        log("-" * 60)

    return out_dir, ok, fail


# ============================================================
# 十、配置读写
# ============================================================

def load_config():
    """加载配置文件，不存在时创建默认配置"""
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        return json.loads(json.dumps(DEFAULT_CONFIG))

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # 与默认配置合并（保证新增字段有默认值）
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)

    # naming_rule 也需要合并
    nr = dict(DEFAULT_CONFIG["naming_rule"])
    nr.update(cfg.get("naming_rule", {}))
    merged["naming_rule"] = nr

    return merged


# ============================================================
# 十一、图形界面
# ============================================================

class App:
    """主窗口应用"""

    def __init__(self, root):
        self.root = root
        root.title("C++ 变量名混淆工具")
        root.geometry("760x560")
        root.minsize(700, 520)

        try:
            ttk.Style().theme_use("vista")
        except Exception:
            pass

        self.config = load_config()
        self._build_ui()
        self._log_welcome()

    # ---------------- UI 构建 ----------------
    def _build_ui(self):
        """构建界面布局"""
        # 顶部：文件选择
        top = ttk.LabelFrame(self.root, text=" 输入 .cpp 文件 ")
        top.pack(fill="x", padx=12, pady=(12, 6))

        self.path_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.path_var).pack(
            side="left", fill="x", expand=True, padx=(8, 6), pady=8
        )
        ttk.Button(top, text="浏览…", command=self.browse).pack(
            side="left", padx=(0, 8), pady=8
        )

        # 中部：操作按钮
        mid = ttk.Frame(self.root)
        mid.pack(fill="x", padx=12, pady=6)

        ttk.Button(mid, text="开始处理", command=self.run).pack(side="left")
        ttk.Button(mid, text="打开输出目录", command=self.open_out).pack(side="left", padx=6)
        ttk.Button(mid, text="重新加载配置", command=self.reload_cfg).pack(side="left", padx=6)

        self.out_label = ttk.Label(mid, text="", foreground="#1a7f37")
        self.out_label.pack(side="left", padx=12)

        # 底部：日志
        log_frame = ttk.LabelFrame(self.root, text=" 日志 ")
        log_frame.pack(fill="both", expand=True, padx=12, pady=(6, 12))

        self.log_text = tk.Text(log_frame, wrap="word", height=18)
        self.log_text.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)

        sb = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        sb.pack(side="right", fill="y", pady=8)
        self.log_text.config(yscrollcommand=sb.set)

    def _log_welcome(self):
        """显示欢迎信息"""
        self.log("C++ 变量名混淆工具已启动")
        self.log(f"配置文件：{os.path.abspath(CONFIG_FILE)}")
        self.log(f"输出目录：{os.path.abspath(self.config.get('output_dir', './output'))}")
        self.log(f"命名模式：{self.config['naming_rule'].get('mode')}")
        self.log("-" * 60)

    # ---------------- 事件处理 ----------------
    def log(self, msg):
        """向日志区域追加一行"""
        self.log_text.insert("end", str(msg) + "\n")
        self.log_text.see("end")
        self.root.update_idletasks()

    def browse(self):
        """选择源文件"""
        p = filedialog.askopenfilename(
            title="选择一个 C++ 源文件",
            filetypes=[("C++ 源文件", "*.cpp *.cc *.cxx"), ("所有文件", "*.*")]
        )
        if p:
            self.path_var.set(p)

    def reload_cfg(self):
        """重新加载配置"""
        self.config = load_config()
        self.log("已重新加载 config.json")

    def open_out(self):
        """在文件管理器中打开输出目录"""
        d = os.path.abspath(self.config.get("output_dir", "./output"))
        os.makedirs(d, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(d)
            elif sys.platform == "darwin":
                os.system(f'open "{d}"')
            else:
                os.system(f'xdg-open "{d}"')
        except Exception as e:
            self.log(f"打开目录失败：{e}")

    def run(self):
        """处理当前选中的文件"""
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("提示", "请先选择 .cpp 文件")
            return
        if not os.path.isfile(path):
            messagebox.showerror("错误", "文件不存在")
            return
        if not path.lower().endswith((".cpp", ".cc", ".cxx")):
            if not messagebox.askyesno("确认", "文件后缀不是 .cpp，是否继续？"):
                return

        try:
            out_path, _ = process_file(path, self.config, log=self.log)
            self.out_label.config(text=f"完成 → {out_path}")
            messagebox.showinfo("完成", f"已输出：\n{out_path}")
        except Exception as e:
            self.log(f"[错误] {e}")
            messagebox.showerror("错误", str(e))


# ============================================================
# 十二、程序入口
# ============================================================

def run_cli_mode(paths, config):
    """命令行/拖拽模式：批量处理并弹窗提示"""
    def collect(msg):
        print(msg)

    try:
        out_dir, ok, fail = batch_process(paths, config, log=collect)
    except Exception as e:
        print(f"[错误] {e}")
        input("按回车退出…")
        return

    try:
        root = tk.Tk()
        root.withdraw()
        if out_dir:
            messagebox.showinfo(
                "处理完成",
                f"成功 {ok} 个，失败 {fail} 个\n\n输出目录：\n{out_dir}"
            )
        else:
            messagebox.showwarning("提示", "没有找到可处理的源文件")
        root.destroy()
    except Exception:
        pass


def run_gui_mode():
    """GUI 模式"""
    root = tk.Tk()
    App(root)
    root.mainloop()


def main():
    """程序入口"""
    config = load_config()

    # 有命令行参数（拖拽或命令行调用）→ 批处理模式
    if len(sys.argv) > 1:
        paths = [p for p in sys.argv[1:] if os.path.exists(p)]
        if not paths:
            print("没有有效的文件或文件夹路径")
            input("按回车退出…")
            return
        run_cli_mode(paths, config)
        return

    # 无参数 → 启动 GUI
    run_gui_mode()


if __name__ == "__main__":
    main()