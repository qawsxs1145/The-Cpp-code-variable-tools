# The-Cpp-code-variable-tools
# C++ 变量名混淆工具 — 配置说明与使用指南

## 一、简介

本工具用于对 C++ 源代码中的变量名、函数名等标识符进行批量混淆替换。

主要功能：

- **保护 `#include` 行**，不会误替换 `stdio.h`、`iostream` 等头文件名。
- **保护字符串字面量和注释**，只替换代码中的标识符。
- 支持多种**混淆命名模式**：随机、编号、前缀随机、词库、哈希。
- 支持**批量处理文件夹**，自动扫描所有 `.cpp` 文件并输出到指定子文件夹。
- 支持**拖拽运行**：把文件或文件夹拖到 exe 图标上即可自动处理。
- 输出目录、文件命名、文件夹命名均可通过配置文件自定义。

---

## 二、配置文件位置

程序首次运行时，会在 **exe 所在目录** 自动生成 `config.json`。

修改配置后，在 GUI 中点击 **“重新加载配置”** 即可生效，无需重启程序。

---

## 三、配置文件完整示例

```json
{
    "output_dir": "./output",
    "filename_rule": "{name}_obf{ext}",
    "folder_name_rule": "batch_{date}_{time}_{rand}",
    "source_extensions": [".cpp", ".cc", ".cxx"],
    "recursive": true,

    "naming_rule": {
        "mode": "random",
        "prefix": "",
        "length": 8,
        "charset": "lowercase",
        "start_index": 1,
        "word_pool": [
            "alpha", "beta", "gamma", "delta", "epsilon",
            "zeta", "eta", "theta", "iota", "kappa"
        ],
        "word_pool_suffix": true
    },

    "keep_uppercase_macros": true,
    "protect_includes": true,
    "exclude": [],
    "include_only": []
}
```

---

## 四、配置项详解

### 1. `output_dir` — 输出根目录

新文件保存到哪个目录。

| 写法 | 含义 |
|------|------|
| `"./output"` | 程序所在目录下的 `output` 文件夹 |
| `"D:/my_project/out"` | 绝对路径 |
| `"../backup"` | 上一级目录的 `backup` 文件夹 |

- 目录不存在时程序会**自动创建**。
- Windows 路径用 `/` 或 `\\`，例如 `"D:\\code\\out"`。
- 相对路径是相对于**程序运行的位置**。

---

### 2. `filename_rule` — 单个文件的输出命名规则

控制输出文件的文件名。

**可用占位符：**

| 占位符 | 含义 | 示例 |
|--------|------|------|
| `{name}` | 原文件名（不含后缀） | `main.cpp` → `main` |
| `{ext}` | 原后缀（含点） | `.cpp` |
| `{date}` | 当前日期 | `20261008` |
| `{time}` | 当前时间 | `143025` |
| `{rand}` | 6 位随机串 | `a7k2m9` |

**常见模板：**

| 模板 | 输出示例 |
|------|---------|
| `"{name}_obf{ext}"` | `main_obf.cpp` |
| `"{name}_new{ext}"` | `main_new.cpp` |
| `"{name}_{date}{ext}"` | `main_20261008.cpp` |
| `"{name}_{date}_{time}{ext}"` | `main_20261008_143025.cpp` |
| `"{name}_{rand}{ext}"` | `main_a7k2m9.cpp` |

> 注意：`{ext}` 已经包含点号，不用再加 `.`。

---

### 3. `folder_name_rule` — 批量输出子文件夹命名规则

批量处理文件夹时，会在 `output_dir` 下新建一个子文件夹，所有结果输出到里面。此配置控制该子文件夹的名字。

**可用占位符：**

| 占位符 | 含义 | 示例 |
|--------|------|------|
| `{src}` | 源文件夹名 | `mycode` |
| `{date}` | 当前日期 | `20261008` |
| `{time}` | 当前时间 | `143025` |
| `{rand}` | 6 位随机串 | `a7k2m9` |

**常见模板：**

| 模板 | 输出示例 |
|------|---------|
| `"batch_{date}_{time}_{rand}"` | `batch_20261008_143025_a7k2m9` |
| `"obf_{src}"` | `obf_mycode` |
| `"{src}_{date}"` | `mycode_20261008` |

---

### 4. `source_extensions` — 源文件后缀

被视为需要处理的源文件后缀列表。默认包含 `.cpp`、`.cc`、`.cxx`。

```json
"source_extensions": [".cpp", ".cc", ".cxx"]
```

---

### 5. `recursive` — 是否递归扫描

- `true`：递归扫描子文件夹中的源文件。
- `false`：只扫描当前文件夹。

---

### 6. `naming_rule` — 变量混淆命名规则

这是核心配置，决定新变量名长什么样。

#### 6.1 `mode` — 命名模式

| 值 | 含义 | 结果示例 |
|----|------|---------|
| `"random"` | 纯随机字符串 | `xkdhqpwl` |
| `"indexed"` | 前缀 + 递增编号 | `v1`、`v2`、`v3` |
| `"prefix_random"` | 前缀 + 随机字符串 | `v_xkdhqp` |
| `"pool"` | 从自定义词库中取词 | `alpha`、`beta` |
| `"hash"` | 基于原名字的哈希（同名同结果） | `a3f9c2e1` |

#### 6.2 `prefix` — 新名字前缀

加在每个新名字前面的固定字符串。

| 值 | 效果 |
|----|------|
| `""` | 无前缀 |
| `"v_"` | `v_xxxxxxxx` |
| `"var_"` | `var_xxxxxxxx` |

#### 6.3 `length` — 随机部分长度

只在 `random`、`prefix_random`、`hash` 模式下生效。

| 值 | 结果示例 |
|----|---------|
| `4` | `xkdh` |
| `8` | `xkdhqpwl` |
| `12` | `xkdhqpwlmznt` |

#### 6.4 `charset` — 随机字符集

只在 `random`、`prefix_random`、`hash` 模式下生效。

| 值 | 字符范围 | 示例 |
|----|---------|------|
| `"lowercase"` | `a-z` | `xkdhqpwl` |
| `"uppercase"` | `A-Z` | `XKDHQPWL` |
| `"letters"` | `a-z` + `A-Z` | `XkDhQpWl` |
| `"alnum"` | `a-z` + `A-Z` + `0-9` | `x7Kd2pW9` |

> 建议使用 `lowercase`，避免与全大写宏冲突。

#### 6.5 `start_index` — 起始编号

只在 `indexed` 模式下生效。

| 值 | 结果 |
|----|------|
| `1` | `v1`、`v2`、`v3` |
| `0` | `v0`、`v1`、`v2` |
| `100` | `v100`、`v101` |

#### 6.6 `word_pool` — 自定义词库

只在 `pool` 模式下生效。程序会从该列表中随机选取单词作为变量名。

```json
"word_pool": ["alpha", "beta", "gamma", "delta", "epsilon"]
```

#### 6.7 `word_pool_suffix` — 词库用完后是否加数字后缀

- `true`：词库用完后，生成类似 `alpha1`、`beta2` 的名字。
- `false`：循环使用词库，并附加随机后缀避免冲突。

---

### 7. `keep_uppercase_macros` — 保留全大写宏

- `true`：全大写标识符（如 `MAX_SIZE`、`PI`）**不替换**。
- `false`：全大写标识符也一起替换。

> 建议设为 `true`，避免破坏 `#define` 逻辑。

---

### 8. `protect_includes` — 保护 `#include` 行

- `true`：`#include` 行整体受保护，头文件名不会被替换。
- `false`：不保护（**不推荐**，可能导致 `stdio.h` 被误改）。

> 强烈建议保持 `true`。

---

### 9. `exclude` — 手动排除名单

一个字符串数组，里面的标识符**永远不替换**。

```json
"exclude": ["myImportantFunc", "globalConfig", "main"]
```

用途：保留关键函数名、外部库对接符号等。

---

### 10. `include_only` — 只替换名单

一个字符串数组。**不为空时**，只替换列表内的标识符，其他一律不动。

```json
"include_only": ["count", "sum", "temp"]
```

> `include_only` 为空 `[]` 时，走默认逻辑（替换所有非关键字标识符）。

---

## 五、使用方法

### 1. 双击运行（GUI 模式）

- 直接双击 `CppVarRandomizer.exe`，打开图形界面。
- 点击 **“浏览…”** 选择单个 `.cpp` 文件。
- 点击 **“开始处理”**，日志区会显示处理过程，输出文件路径会显示在按钮旁。
- 点击 **“打开输出目录”** 可快速定位输出文件夹。

### 2. 拖拽运行（批量模式）

- 把一个或多个 `.cpp` 文件拖到 `CppVarRandomizer.exe` 图标上。
- 或把一个**文件夹**拖到 exe 图标上，程序会扫描文件夹内所有源文件。
- 处理完成后弹窗提示成功/失败数量及输出目录。
- 所有结果输出到 `output_dir` 下按 `folder_name_rule` 生成的子文件夹中。

### 3. 命令行调用

```bat
CppVarRandomizer.exe D:\mycode
CppVarRandomizer.exe a.cpp b.cpp
CppVarRandomizer.exe D:\project1 D:\project2
```

---

## 六、配置组合示例

### 示例 1：最保守，只改指定的三个变量

```json
{
    "include_only": ["count", "sum", "temp"],
    "naming_rule": { "mode": "indexed", "prefix": "v", "start_index": 1 }
}
```
结果：`count` → `v1`，`sum` → `v2`，`temp` → `v3`，其他不动。

### 示例 2：全部替换，随机长名字

```json
{
    "include_only": [],
    "naming_rule": { "mode": "random", "prefix": "", "length": 12, "charset": "letters" }
}
```
结果：`int a = 1;` → `int XkDhQpWlMzNt = 1;`

### 示例 3：使用词库，输出带时间戳

```json
{
    "output_dir": "D:/projects/backup",
    "filename_rule": "{name}_{date}_{time}{ext}",
    "naming_rule": { "mode": "pool", "prefix": "x_", "word_pool": ["alpha", "beta", "gamma"] }
}
```
输出：`D:/projects/backup/main_20261008_143025.cpp`  
变量名：`x_alpha`、`x_beta`、`x_gamma` …

### 示例 4：确定性混淆（同名同结果）

```json
{
    "naming_rule": { "mode": "hash", "length": 10, "charset": "lowercase" }
}
```
同一变量名每次运行都会得到相同的混淆名，适合需要稳定输出的场景。

---

## 七、快速对照表

| 配置项 | 作用 | 影响范围 |
|--------|------|---------|
| `output_dir` | 输出根目录 | 文件位置 |
| `filename_rule` | 单文件输出命名 | 文件名 |
| `folder_name_rule` | 批量输出子文件夹命名 | 文件夹名 |
| `source_extensions` | 识别的源文件后缀 | 扫描范围 |
| `recursive` | 是否递归扫描 | 扫描范围 |
| `naming_rule.mode` | 混淆命名模式 | 变量名格式 |
| `naming_rule.prefix` | 新名字前缀 | 变量名格式 |
| `naming_rule.length` | 随机部分长度 | 变量名长度 |
| `naming_rule.charset` | 随机字符集 | 变量名字符 |
| `naming_rule.start_index` | indexed 模式起始编号 | 变量名编号 |
| `naming_rule.word_pool` | pool 模式词库 | 变量名内容 |
| `naming_rule.word_pool_suffix` | 词库用完后策略 | 变量名内容 |
| `keep_uppercase_macros` | 是否保留全大写宏 | 替换范围 |
| `protect_includes` | 是否保护 `#include` | 替换范围 |
| `exclude` | 永不替换的名单 | 替换范围 |
| `include_only` | 只替换的名单 | 替换范围 |

---

## 八、注意事项

1. **字符串和注释不会被替换**，只替换代码中的标识符。
2. **关键字、标准库名、宏名**默认保留，可在配置中调整。
3. 本工具基于词法分析，**无法做到 100% 语义准确**。复杂代码（模板、宏）可能误伤，建议先用副本测试。
4. 若发现某个标识符不应被替换，将其加入 `exclude` 列表。
5. **强烈建议保持 `protect_includes` 为 `true`**，否则头文件名可能被破坏。
6. 批量处理同名文件时，可在 `filename_rule` 中加入 `{rand}` 避免覆盖，例如：
   ```json
   "filename_rule": "{name}_obf_{rand}{ext}"
   ```
