import json
import yaml
import re
import os
import hashlib
import tkinter as tk
from tkinter import scrolledtext
from tkinterdnd2 import DND_FILES, TkinterDnD

# 需要检测的不可见特殊字符（名称 => Unicode 码点）
INVISIBLE_CHARS = {
    '\u00a0': 'NO-BREAK SPACE (\\xa0)',
    '\u200b': 'ZERO WIDTH SPACE (\\u200b)',
    '\u200c': 'ZERO WIDTH NON-JOINER (\\u200c)',
    '\u200d': 'ZERO WIDTH JOINER (\\u200d)',
    '\u00ad': 'SOFT HYPHEN (\\u00ad)',
    '\u200e': 'LEFT-TO-RIGHT MARK (\\u200e)',
    '\u200f': 'RIGHT-TO-LEFT MARK (\\u200f)',
    '\u202a': 'LEFT-TO-RIGHT EMBEDDING (\\u202a)',
    '\u202b': 'RIGHT-TO-LEFT EMBEDDING (\\u202b)',
    '\u202c': 'POP DIRECTIONAL FORMATTING (\\u202c)',
    '\u202d': 'LEFT-TO-RIGHT OVERRIDE (\\u202d)',
    '\u202e': 'RIGHT-TO-LEFT OVERRIDE (\\u202e)',
    '\u2060': 'WORD JOINER (\\u2060)',
    '\ufeff': 'BYTE ORDER MARK (\\ufeff)',
    '\u3000': 'IDEOGRAPHIC SPACE (\\u3000)',
}

def check_invisible_chars(content):
    """检测文件中的不可见特殊字符，返回警告列表"""
    warnings = []
    lines = content.split('\n')
    for idx, line in enumerate(lines):
        for char, name in INVISIBLE_CHARS.items():
            if char in line:
                # 找出该字符在本行中的所有位置
                col = line.find(char)
                while col != -1:
                    pos = f"{idx + 1}行{col + 1}列"
                    # 取上下文：显示该字符前后的可见内容
                    ctx_start = max(0, col - 10)
                    ctx_end = min(len(line), col + 10)
                    context = line[ctx_start:col] + '◆' + line[col + 1:ctx_end]
                    warnings.append(f"[不可见字符] {pos} 发现 {name}，上下文: ...{context}...")
                    col = line.find(char, col + 1)
    return warnings

def calculate_md5(file_path):
    """计算文件的MD5值"""
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_indent(line):
    return len(line) - len(line.lstrip())

# ==================== YAML 检测函数 (基于 yamllint) ====================

# yamllint 内嵌配置（移除 extends: default，直接定义完整规则，解决 PyInstaller 打包问题）
YAMLLINT_CONFIG = """
yaml-files:
  - '*.yaml'
  - '*.yml'

rules:
  # 启用的规则
  anchors: enable
  brackets: enable
  commas: enable
  hyphens: enable
  key-duplicates: enable        # 重复键检测 (error)
  
  # 自定义级别的规则
  colons:
    max-spaces-after: 1
    max-spaces-before: 0
    level: warning
  indentation:
    spaces: 2
    indent-sequences: consistent
    check-multi-line-strings: false
    level: warning
  braces:
    max-spaces-inside: 1        # 允许1个空格，适应 { key: value } 风格
    level: warning
  trailing-spaces:
    level: warning
  truthy:
    level: warning
  empty-lines:
    max: 2
    max-start: 1
    max-end: 1
    level: warning
  line-length:
    max: 160
    level: warning
  
  # 禁用的规则
  new-lines: disable
  new-line-at-end-of-file: disable
  comments-indentation: disable
  document-start: disable
  document-end: disable
  comments: disable
  empty-values: disable
  float-values: disable
  key-ordering: disable
  octal-values: disable
  quoted-strings: disable
"""


def parse_yaml_with_yamllint(file_path):
    """使用 yamllint 检测 YAML 文件，返回格式化的错误列表"""
    try:
        from yamllint import linter
        from yamllint.config import YamlLintConfig
    except ImportError:
        return None, "yamllint 未安装，请执行: pip install yamllint"
    
    try:
        # 使用内嵌配置（通过 content= 参数避免 PyInstaller 打包后找不到默认配置的问题）
        config = YamlLintConfig(content=YAMLLINT_CONFIG)
        
        # 读取文件内容
        content = None
        for enc in ['utf-8', 'gbk', 'utf-16']:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            return None, "无法读取文件内容（编码问题）"
        
        # 执行 yamllint 检测
        problems = list(linter.run(content, config, file_path))
        
        if not problems:
            return ([], []), None
        
        # 分类收集问题
        errors = []
        warnings = []
        
        for problem in problems:
            # 格式化问题信息
            level = "error" if problem.level == "error" else "warning"
            rule = problem.rule if problem.rule else "syntax"
            msg = problem.message if problem.message else str(problem)
            
            # 生成中文友好的描述
            desc = format_yamllint_message(rule, msg, problem.line, problem.column)
            
            if level == "error":
                errors.append((problem.line, problem.column, rule, desc))
            else:
                warnings.append((problem.line, problem.column, rule, desc))
        
        return (errors, warnings), None
        
    except Exception as e:
        return None, f"yamllint 执行出错: {str(e)}"

def format_yamllint_message(rule, message, line, column):
    """将 yamllint 的英文消息转换为中文友好格式"""
    
    # 规则名称映射
    rule_names = {
        'syntax': '语法错误',
        'indentation': '缩进问题',
        'colons': '冒号格式',
        'braces': '大括号格式',
        'trailing-spaces': '行尾空格',
        'truthy': '布尔值歧义',
        'empty-lines': '空白行',
        'line-length': '行长度',
        'key-duplicates': '重复键',
        'new-lines': '换行符',
    }
    
    rule_name = rule_names.get(rule, rule)
    pos = f"{line}行{column}列"  # 位置信息：中文格式
    
    # 常见消息模式翻译
    if 'wrong indentation' in message:
        # 提取 expected X but found Y
        import re
        match = re.search(r'expected (\d+) but found (\d+)', message)
        if match:
            expected, found = match.groups()
            return f"[{rule_name}] {pos} 缩进应为 {expected} 个空格，实际为 {found} 个"
    
    if 'too many spaces' in message:
        if 'after colon' in message:
            return f"[{rule_name}] {pos} 冒号后空格过多"
        if 'inside braces' in message:
            return f"[{rule_name}] {pos} 大括号内空格过多"
        if 'before colon' in message:
            return f"[{rule_name}] {pos} 冒号前不应有空格"
    
    if 'trailing spaces' in message:
        return f"[{rule_name}] {pos} 行尾存在多余空格"
    
    if 'too many blank lines' in message:
        return f"[{rule_name}] {pos} 连续空白行过多"
    
    if 'duplication of key' in message:
        # 提取重复的键名
        import re
        match = re.search(r'duplication of key "([^"]+)"', message)
        if match:
            key = match.group(1)
            return f"[{rule_name}] {pos} 键 '{key}' 重复定义（会导致数据丢失）"
    
    if 'syntax error' in message or 'expected' in message:
        return f"[{rule_name}] {pos} {message}"
    
    # 默认格式
    return f"[{rule_name}] {pos} {message}"


def parse_yaml_content(content_unused, file_path):
    """解析YAML内容并返回校验结果（使用 yamllint）"""
    filename = os.path.basename(file_path)
    
    # 使用 yamllint 进行检测
    result, error = parse_yaml_with_yamllint(file_path)
    
    # 文件头部分隔线
    header = f"\n{'━' * 50}\n📄 {filename}\n{'━' * 50}"
    
    if error:
        # yamllint 执行失败，回退到基础检测
        return f"{header}\n{error}"
    
    errors, warnings = result
    
    # 无问题
    if not errors and not warnings:
        return f"{header}\n✅ 解析正常"
    
    # 格式化输出
    output = header
    
    # 先显示 errors（严重问题）
    if errors:
        output += f"\n\n❌ 错误 ({len(errors)} 个) - 必须修复:"
        for i, (line, col, rule, desc) in enumerate(errors, 1):
            output += f"\n  {i}. {desc}"
    
    # 再显示 warnings
    if warnings:
        output += f"\n\n⚠️ 警告 ({len(warnings)} 个) - 建议修复:"
        # 限制显示数量，避免输出过长
        display_warnings = warnings[:50]
        for i, (line, col, rule, desc) in enumerate(display_warnings, 1):
            output += f"\n  {i}. {desc}"
        if len(warnings) > 50:
            output += f"\n  ... 还有 {len(warnings) - 50} 个警告未显示"
    
    return output


# ==================== JSON 检测函数 ====================


def get_clean_content(content):
    out = []
    i = 0
    in_string = None
    in_comment = None
    while i < len(content):
        char = content[i]
        next_char = content[i+1] if i+1 < len(content) else ""
        if in_comment == '//':
            if char == '\n': in_comment = None; out.append('\n')
            else: out.append(' ')
        elif in_comment == '/*':
            if char == '*' and next_char == '/':
                in_comment = None; out.append('  '); i += 1
            elif char == '\n': out.append('\n')
            else: out.append(' ')
        elif in_string:
            if char == '\\': out.append(content[i:i+2]); i += 1
            elif char == in_string: in_string = None; out.append(char)
            else: out.append(char)
        else:
            if char == '/' and next_char == '/': in_comment = '//'; out.append('  '); i += 1
            elif char == '/' and next_char == '*': in_comment = '/*'; out.append('  '); i += 1
            elif char in ("'", '"'): in_string = char; out.append(char)
            else: out.append(char)
        i += 1
    return "".join(out)

def _indent_of(line, tab_width=4):
    """归一化缩进宽度：tab 按 tab_width 展开并对齐到 tab_width 的倍数（tab/空格混用健壮）"""
    w = 0
    for ch in line:
        if ch == '\t':
            w += tab_width - (w % tab_width)
        elif ch == ' ':
            w += 1
        else:
            break
    return w

def _tokenize_brackets(content):
    """可靠分词：只收集结构性括号 { } [ ]，正确跳过字符串和注释。返回 [(char, line)]，line 为 1-based"""
    toks = []
    i = 0
    n = len(content)
    line = 1
    in_str = None
    in_cmt = None
    while i < n:
        ch = content[i]
        nxt = content[i+1] if i+1 < n else ''
        if in_cmt == '//':
            if ch == '\n':
                in_cmt = None
                line += 1
        elif in_cmt == '/*':
            if ch == '\n':
                line += 1
            elif ch == '*' and nxt == '/':
                in_cmt = None
                i += 1
        elif in_str:
            if ch == '\\':
                i += 1
            elif ch == in_str:
                in_str = None
        else:
            if ch == '\n':
                line += 1
            elif ch == '/' and nxt == '/':
                in_cmt = '//'
                i += 1
            elif ch == '/' and nxt == '*':
                in_cmt = '/*'
                i += 1
            elif ch in "'\"":
                in_str = ch
            elif ch in '{}[]':
                toks.append((ch, line))
        i += 1
    return toks

def locate_unclosed_brace(content):
    """存在未闭合括号时，用"缩进不匹配 + 跨度最大的叶子"启发式定位最可能缺闭合的对象。
    返回要拼到"参考分析"末尾的中文提示串（含前导 " ，"）；无法定位时返回 None。
    原理：少一个 } 后，后续 } 会"借"给外层对象闭合，导致"闭括号缩进 < 开括号缩进"的错配；
    跨度最大且内部无其它错配的叶子，就是真正缺闭合的对象。"""
    lines = content.split('\n')
    total_lines = len(lines)
    toks = _tokenize_brackets(content)

    # 压缩/单行守卫：结构括号挤在过少的行里，缩进不承载结构信息，定位必然误报
    distinct_lines = {ln for _, ln in toks}
    if total_lines <= 1 or len(distinct_lines) < min(len(toks) * 0.3, 20):
        return None

    # 栈匹配，带括号类型校验
    pairs = []   # [{'char','open_line','close_line','open_indent','close_indent'}]
    stack = []   # [{'char','open_line','open_indent'}]
    for ch, ln in toks:
        if ch in '{[':
            stack.append({'char': ch, 'open_line': ln, 'open_indent': _indent_of(lines[ln-1])})
        else:  # } ]
            close_indent = _indent_of(lines[ln-1])
            if not stack:
                return None   # 多余右括号，由 check_structural_balance 主体兜底
            opener = stack[-1]
            if (ch == '}' and opener['char'] != '{') or (ch == ']' and opener['char'] != '['):
                return (f" ，括号类型不匹配：第 {ln} 行的 '{ch}' "
                        f"无法闭合第 {opener['open_line']} 行的 '{opener['char']}'")
            stack.pop()
            pairs.append({'char': opener['char'], 'open_line': opener['open_line'],
                          'close_line': ln, 'open_indent': opener['open_indent'],
                          'close_indent': close_indent})

    # 缩进不匹配配对：闭括号缩进 < 开括号缩进（闭括号是从外层"借"来的）
    mismatches = [p for p in pairs if p['close_indent'] < p['open_indent']]
    if not mismatches:
        # 无缩进不匹配但仍有未闭合 → 可能纯缺文件末尾的闭合括号
        if stack:
            outer = min(stack, key=lambda o: o['open_indent'])
            return (f" ，第 {outer['open_line']} 行的 {outer['char']} "
                    f"疑似缺少闭合（缩进未见异常，可能在文件末尾附近遗漏）")
        return None

    # 选择真凶：内部不含其它错配的"叶子"中，跨度最大的（吸收内容最多 = 最可能缺闭合）
    leaves = [p for p in mismatches
              if not any(q is not p and q['open_line'] > p['open_line']
                         and q['close_line'] < p['close_line'] for q in mismatches)]
    culprit = max((leaves or mismatches), key=lambda p: p['close_line'] - p['open_line'])

    # 从原始行提取对象名
    idx = culprit['open_line'] - 1
    target_line = lines[idx] if 0 <= idx < len(lines) else ''
    m = re.match(r'\s*"([^"]+)"\s*:', target_line)
    name = m.group(1) if m else target_line.strip()[:24]
    return (f" ，最可能缺少闭合的是第 {culprit['open_line']} 行 '{name}' "
            f"开启的 {culprit['char']}，其闭合括号被后续内容顶替")

def check_structural_balance(content):
    clean_content = get_clean_content(content)
    lines = clean_content.split('\n')
    
    for row_idx in range(len(lines) - 1):
        line1, line2 = lines[row_idx].strip(), lines[row_idx+1].strip()
        if not line1 or line1.endswith(',') or line1.endswith('{') or line1.endswith('['): continue
        if re.match(r'^"[^"]*"\s*:', line2) or re.match(r"^'[^']*'\s*:", line2):
            if re.search(r'[:\s]([0-9.-]+|true|false|null|"[^"]*"|\'[^\']*\'|\]|\})$', line1):
                return False, f"语法错误：第 {row_idx+1} 行疑似缺少逗号", \
                       f"可能原因：该行末尾缺少 ','\n参考分析：下一行 (第{row_idx+2}行) 开启了新字段，但当前行未闭合。"

    stack = []
    matches = []
    i, row, col = 0, 1, 1
    while i < len(clean_content):
        char = clean_content[i]
        if char == '\n': row += 1; col = 1
        else:
            if char in ('{', '['):
                stack.append({'char': char, 'row': row, 'col': col, 'indent': get_indent(lines[row-1])})
            elif char in ('}', ']'):
                closer_indent = get_indent(lines[row-1])
                if not stack:
                    return False, f"结构错误：第 {row} 行多写了 '{char}'", "可能原因：此处多了一个右括号"
                opener = stack.pop()
                if (char == '}' and opener['char'] != '{') or (char == ']' and opener['char'] != '['):
                    return False, f"结构错误：第 {row} 行的 '{char}'", \
                           f"可能原因：括号不匹配，无法闭合第 {opener['row']} 行的 '{opener['char']}'"
                matches.append((opener['row'], opener['indent'], row, closer_indent))
            col += 1
        i += 1
        
    if stack:
        item = stack[-1]
        analysis = f"参考分析：第 {item['row']} 行, 第 {item['col']} 列的左括号'{item['char']}'未闭合"
        thief_info = locate_unclosed_brace(content)
        return False, f"结构错误：{len(stack)} 个未闭合", f"{analysis}{thief_info or ''}"
    return True, "", ""

def get_file_type(file_path):
    """根据文件扩展名判断文件类型"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.yaml', '.yml']:
        return 'yaml'
    elif ext == '.json':
        return 'json'
    else:
        return 'unknown'

def explain_json_error(je, total_lines):
    """将 json.JSONDecodeError 翻译为友好的中文提示，并附上精确的行列位置"""
    m = je.msg
    line, col = je.lineno, je.colno
    if 'property name enclosed in double quotes' in m:
        hint = '键名缺少双引号（或上一行少写了逗号）'
    elif "Expecting ',' delimiter" in m:
        hint = '缺少逗号'
    elif "Expecting ':' delimiter" in m:
        hint = '缺少冒号'
    elif m.startswith('Expecting value'):
        hint = '此处不是合法的值（常见原因：单引号、未加引号、十六进制、前导/尾随小数点等 JSONC 不支持的写法）'
    elif 'Extra data' in m:
        hint = 'JSON 结束后仍有多余内容'
    elif 'Unterminated string' in m:
        hint = '字符串未闭合（缺少结束的双引号）'
    elif 'Invalid \\escape' in m:
        hint = '非法的转义字符'
    elif 'control character' in m:
        hint = '字符串中包含非法控制字符'
    else:
        hint = m
    # 多行文件中，错误出现在最后一行，通常是某个 } 或 ] 没有闭合
    # （单行文件不适用；缺括号的情况也会由"结构参考分析"补充说明）
    if total_lines > 1 and line >= total_lines and ('Expecting' in m or 'End of file' in m):
        hint += '（位于文件末尾，很可能是某个 } 或 ] 未闭合）'
    return f'{hint}（第 {line} 行 第 {col} 列）'

def parse_content_by_file(file_path):
    filename = os.path.basename(file_path)
    
    # 计算文件 MD5
    try:
        md5_value = calculate_md5(file_path)
    except Exception:
        md5_value = "无法计算"
    
    md5_line = f"MD5: {md5_value}"
    
    file_type = get_file_type(file_path)
    
    # 不支持的文件类型，只显示 MD5
    # 文件头部分隔线
    header = f"\n{'━' * 50}\n📄 {filename}\n{'━' * 50}"
    
    if file_type == 'unknown':
        return f"{header}\n{md5_line}\n（不支持的文件格式，仅显示MD5）"
    
    # 读取文件内容
    content = None
    for enc in ['utf-8', 'gbk', 'utf-16']:
        try:
            with open(file_path, 'r', encoding=enc) as f: content = f.read()
            break
        except UnicodeDecodeError: continue
    if not content: return f"{header}\n{md5_line}\n解析失败：无法读取文件内容。"
    
    # YAML 文件处理
    if file_type == 'yaml':
        result = parse_yaml_content(content, file_path)
        # YAML 也检测不可见特殊字符
        invisible_warnings = check_invisible_chars(content)
        if invisible_warnings:
            result += f"\n\n⚠️ 不可见字符警告（共{len(invisible_warnings)}处）："
            for w in invisible_warnings:
                result += f"\n  {w}"
        return f"{result}\n{md5_line}"
    
    # JSON/JSONC 文件处理（按 JSONC = JSON with Comments 规范严格校验）
    # 先检测不可见特殊字符
    invisible_warnings = check_invisible_chars(content)
    clean_content = get_clean_content(content)
    total_lines = content.count('\n') + 1

    # 尾随逗号检测：公司 JSONC 规范不允许尾随逗号。
    # 单独捕获以给出友好提示（json.loads 对尾随逗号的报错不够直观）
    if re.search(r',\s*[}\]]', clean_content):
        result = f"{header}\n❌ 语法错误：检测到异常尾随逗号"
        if invisible_warnings:
            result += f"\n⚠️ 不可见字符警告（共{len(invisible_warnings)}处）："
            for w in invisible_warnings:
                result += f"\n  {w}"
        return f"{result}\n{md5_line}"

    # 严格 JSONC 解析：标准 JSON + 注释（注释已在 get_clean_content 中剥离为空白）。
    # 以 json.loads 为权威校验：它能给出精确的首错位置（行:列），且能正确忽略字符串内部的括号，
    # 避免"结构预检"因字符串里出现的括号而误报；同时正确拒绝 JSON5 私有语法（单引号、裸键、十六进制等）。
    try:
        json.loads(clean_content)
        if invisible_warnings:
            result = f"{header}\n⚠️ 不可见字符警告（共{len(invisible_warnings)}处）："
            for w in invisible_warnings:
                result += f"\n  {w}"
            return f"{result}\n{md5_line}"
        return f"{header}\n✅ 解析正常\n{md5_line}"
    except json.JSONDecodeError as je:
        # 主错误：json 给出的精确首错（翻译为中文 + 行:列）
        result = f"{header}\n❌ {explain_json_error(je, total_lines)}"
        # 参考分析：结构预检（括号平衡/缺逗号猜测）。少一个括号的位置天生有歧义，仅作辅助参考。
        success, msg, context = check_structural_balance(content)
        if not success:
            result += f"\n💡 {msg}"
            if context:
                result += f"\n{context}"
        if invisible_warnings:
            result += f"\n⚠️ 不可见字符警告（共{len(invisible_warnings)}处）："
            for w in invisible_warnings:
                result += f"\n  {w}"
        return f"{result}\n{md5_line}"

# 全局变量保存当前文件的MD5值
current_md5 = ""
gui_state = {'save_log': None}  # GUI 状态容器

def get_files_from_path(path):
    """获取路径下的所有支持文件（支持文件和文件夹）"""
    supported_extensions = ('.json', '.yaml', '.yml')
    files = []
    
    if os.path.isfile(path):
        files.append(path)
    elif os.path.isdir(path):
        for root, dirs, filenames in os.walk(path):
            for filename in filenames:
                if filename.lower().endswith(supported_extensions):
                    files.append(os.path.join(root, filename))
        files.sort()
    
    return files

def on_drop(event):
    global current_md5
    dropped_items = root.tk.splitlist(event.data)
    if not dropped_items: return
    
    # 收集所有文件
    all_files = []
    for item in dropped_items:
        path = item.strip('{}')
        all_files.extend(get_files_from_path(path))
    
    if not all_files:
        result_text.config(state=tk.NORMAL)
        result_text.delete('1.0', tk.END)
        result_text.insert(tk.END, "未找到支持的文件 (.json, .yaml, .yml)")
        result_text.config(state=tk.DISABLED)
        return
    
    # 检测所有文件
    results = []
    # 分类统计
    ok_files = []       # 解析正常
    error_files = []    # 有错误
    warning_files = []  # 只有警告
    
    for file_path in all_files:
        result = parse_content_by_file(file_path)
        filename = os.path.basename(file_path)
        results.append((file_path, result))
        
        if "❌" in result or ("错误" in result and "解析正常" not in result):
            error_files.append(filename)
        elif "⚠️" in result or "警告" in result:
            warning_files.append(filename)
        else:
            ok_files.append(filename)
    
    # 合并结果
    full_result = "\n\n".join([r[1] for r in results])
    
    # 如果是单文件，保存 MD5 并启用复制按钮
    if len(all_files) == 1:
        try:
            current_md5 = calculate_md5(all_files[0])
        except:
            current_md5 = ""
        # 启用复制按钮
        copy_btn.config(state=tk.NORMAL, bg=COLORS['btn_primary'], fg='#1e1e2e')
    else:
        current_md5 = ""
        # 禁用复制按钮（多文件模式）- 浅灰背景 + 浅色文字
        copy_btn.config(state=tk.DISABLED, bg='#4a4a5c', fg='#b0b0c0')
        # 生成汇总信息
        summary = "╔══════════════════════════════════════════════════╗\n"
        summary += f"║  📊 检测汇总：共 {len(all_files)} 个文件\n"
        summary += "╠══════════════════════════════════════════════════╣\n"
        summary += f"║  ✅ 正常: {len(ok_files)} 个\n"
        summary += f"║  ⚠️ 警告: {len(warning_files)} 个\n"
        summary += f"║  ❌ 错误: {len(error_files)} 个\n"
        summary += "╚══════════════════════════════════════════════════╝\n"
        
        # 如果有错误文件，列出
        if error_files:
            summary += "\n🔴 有错误的文件:\n"
            for f in error_files:
                summary += f"   • {f}\n"
        
        # 如果有警告文件，列出
        if warning_files:
            summary += "\n🟡 有警告的文件:\n"
            for f in warning_files:
                summary += f"   • {f}\n"
        
        # 如果有正常文件，列出（可选，文件多时可以不显示）
        if ok_files and len(ok_files) <= 10:
            summary += "\n🟢 正常的文件:\n"
            for f in ok_files:
                summary += f"   • {f}\n"
        elif ok_files:
            summary += f"\n🟢 正常的文件: {len(ok_files)} 个 (略)\n"
        
        summary += "\n" + "─" * 50 + "\n详细信息:\n" + "─" * 50 + "\n"
        full_result = summary + full_result
    
    # 判断整体状态
    has_error = len(error_files) > 0
    has_warning = len(warning_files) > 0
    all_ok = not has_error and not has_warning
    
    # 显示结果
    result_text.config(state=tk.NORMAL)
    result_text.delete('1.0', tk.END)
    result_text.insert(tk.END, full_result)
    
    # 设置颜色
    if all_ok:
        color = "#a6e3a1"  # 绿色
    elif has_error:
        color = "#f38ba8"  # 红色
    else:
        color = "#fab387"  # 橙色
    
    result_text.tag_config("c", foreground=color)
    result_text.tag_add("c", "1.0", tk.END)
    result_text.config(state=tk.DISABLED)
    
    # 自动保存日志
    if gui_state['save_log'] and gui_state['save_log'].get():
        save_log(full_result, all_files)

def save_log(content, files):
    """保存检测日志到文件"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.dirname(files[0]) if files else "."
    log_file = os.path.join(log_dir, f"unival_log_{timestamp}.txt")
    
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"UniVal 检测日志\n")
            f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"文件数: {len(files)}\n")
            f.write("=" * 50 + "\n\n")
            f.write(content)
        # 在 GUI 结果区顶部插入保存通知
        result_text.config(state=tk.NORMAL)
        result_text.insert("1.0", f"📝 日志已保存: {log_file}\n\n")
        result_text.config(state=tk.DISABLED)
    except Exception as e:
        result_text.config(state=tk.NORMAL)
        result_text.insert("1.0", f"❗ 日志保存失败: {e}\n\n")
        result_text.config(state=tk.DISABLED)

def copy_md5():
    if current_md5:
        root.clipboard_clear()
        root.clipboard_append(current_md5)
        # 临时更改按钮文字提示已复制
        copy_btn.config(text="已复制!")
        root.after(1500, lambda: copy_btn.config(text="复制MD5"))

# --- 入口判断：命令行模式 or GUI 模式 ---
import sys
import glob


def enable_high_dpi():
    """Enable Windows per-monitor DPI awareness before creating the Tk window."""
    if sys.platform != "win32":
        return

    try:
        import ctypes
    except ImportError:
        return

    user32 = None
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        set_dpi_context = user32.SetProcessDpiAwarenessContext
        set_dpi_context.argtypes = [ctypes.c_void_p]
        set_dpi_context.restype = ctypes.c_bool
        if set_dpi_context(ctypes.c_void_p(-4)):
            return
        if ctypes.get_last_error() == 5:  # ERROR_ACCESS_DENIED: already configured
            return
    except (AttributeError, OSError, ctypes.ArgumentError):
        pass

    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        set_dpi_awareness = shcore.SetProcessDpiAwareness
        set_dpi_awareness.argtypes = [ctypes.c_int]
        set_dpi_awareness.restype = ctypes.c_long
        result = set_dpi_awareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        if result == 0 or result == 0x80070005:  # S_OK / E_ACCESSDENIED
            return
    except (AttributeError, OSError, ctypes.ArgumentError):
        pass

    try:
        set_dpi_aware = user32.SetProcessDPIAware
        set_dpi_aware.argtypes = []
        set_dpi_aware.restype = ctypes.c_bool
        set_dpi_aware()
    except (AttributeError, OSError, ctypes.ArgumentError):
        pass


def get_dpi_scale(root):
    """返回当前屏幕 DPI 相对 96 DPI(100% 系统缩放) 的比例。

    开启 Windows DPI 感知后，Tkinter 会按真实 DPI 渲染以"点"为单位的字体（更清晰），
    但窗口尺寸、内边距等以"像素"为单位的硬编码值不会随之放大，导致高 DPI 下
    窗口偏小、内容被裁切。用此比例把这些像素值等比放大即可保持布局一致。
    """
    try:
        dpi = float(root.winfo_fpixels('1i'))  # 每英寸像素数
        if dpi > 0:
            return dpi / 96.0
    except Exception:
        pass
    return 1.0


def get_files_to_check(path):
    """获取需要检测的文件列表，支持文件和文件夹"""
    supported_extensions = ('.json', '.yaml', '.yml')
    files = []
    
    if os.path.isfile(path):
        files.append(path)
    elif os.path.isdir(path):
        # 递归扫描文件夹
        for root, dirs, filenames in os.walk(path):
            for filename in filenames:
                if filename.lower().endswith(supported_extensions):
                    files.append(os.path.join(root, filename))
        files.sort()  # 按路径排序
    
    return files

if len(sys.argv) > 1:
    # 命令行模式：支持文件和文件夹
    all_files = []
    for path in sys.argv[1:]:
        files = get_files_to_check(path)
        if files:
            all_files.extend(files)
        else:
            print(f"路径不存在或无支持的文件: {path}")
    
    # 检测所有文件
    for file_path in all_files:
        print(parse_content_by_file(file_path))
        print()
else:
    # GUI 模式 - 深色主题
    enable_high_dpi()

    # 配色方案
    COLORS = {
        'bg': '#1e1e2e',           # 主背景 (深蓝灰)
        'surface': '#2a2a3c',      # 表面/卡片
        'border': '#3a3a4c',       # 边框
        'text': '#cdd6f4',         # 主文字
        'text_dim': '#6c7086',     # 次要文字
        'accent': '#89b4fa',       # 强调色 (蓝)
        'success': '#a6e3a1',      # 成功 (绿)
        'error': '#f38ba8',        # 错误 (粉红)
        'btn_primary': '#89b4fa',  # 主按钮
        'btn_danger': '#f38ba8',   # 危险按钮
    }
    
    root = TkinterDnD.Tk()
    root.title("UniVal")

    # 按当前 DPI 等比缩放以 96 DPI(100%) 为基准设计的像素尺寸，
    # 避免高 DPI 下窗口偏小、字体按 DPI 放大后被裁切。
    dpi_scale = get_dpi_scale(root)

    def px(v):
        return int(round(v * dpi_scale))

    root.geometry(f"{px(520)}x{px(360)}")
    root.configure(bg=COLORS['bg'])
    root.resizable(False, False)

    # 源码运行时显示自定义窗口图标；打包后 EXE 已内嵌图标，找不到文件时静默跳过
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon', 'icon.ico')
    try:
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass

    # 拖拽区域
    drop_area = tk.Label(root, text="📁 拖拽文件或文件夹至此处\n支持 JSON / YAML 校验 + MD5 计算", 
                         font=("微软雅黑", 11), bg=COLORS['surface'], fg=COLORS['text_dim'], 
                         height=4, highlightthickness=px(2), highlightbackground=COLORS['border'])
    drop_area.pack(fill=tk.X, padx=px(16), pady=(px(16), px(8)))
    drop_area.drop_target_register(DND_FILES)
    drop_area.dnd_bind('<<Drop>>', on_drop)

    # 结果显示区
    result_text = scrolledtext.ScrolledText(root, height=10, font=("Consolas", 11), state=tk.DISABLED, 
                                            bg=COLORS['surface'], fg=COLORS['text'],
                                            relief="flat", highlightthickness=px(2), highlightbackground=COLORS['border'],
                                            insertbackground=COLORS['text'])
    result_text.pack(fill=tk.BOTH, padx=px(16), expand=True)

    # 底部栏
    footer = tk.Frame(root, bg=COLORS['bg'])
    footer.pack(fill=tk.X, padx=px(16), pady=px(12))
    
    # GitHub 链接版本号
    def open_github(event=None):
        import webbrowser
        webbrowser.open("https://github.com/yeqing17/unival")
    
    version_label = tk.Label(footer, text="⚡ v5.2.0", font=("Consolas", 9), bg=COLORS['bg'],
                             fg=COLORS['accent'], cursor="hand2")
    version_label.pack(side=tk.LEFT)
    version_label.bind("<Button-1>", open_github)
    
    # 保存日志复选框
    gui_state['save_log'] = tk.BooleanVar(value=False)
    log_checkbox = tk.Checkbutton(footer, text="保存日志", variable=gui_state['save_log'],
                                   bg=COLORS['bg'], fg=COLORS['text_dim'], 
                                   selectcolor=COLORS['surface'], activebackground=COLORS['bg'],
                                   activeforeground=COLORS['text'], font=("微软雅黑", 9))
    log_checkbox.pack(side=tk.LEFT, padx=(px(15), 0))

    # 窗口置顶小按钮：置顶时 📌 高亮为强调色，窗口始终浮在其他程序上层，方便拖拽文件
    def toggle_on_top():
        topmost_var.set(not topmost_var.get())
        on = topmost_var.get()
        root.attributes('-topmost', on)
        topmost_btn.config(bg=COLORS['accent'] if on else COLORS['surface'],
                           fg='#1e1e2e' if on else COLORS['text_dim'],
                           activebackground=COLORS['accent'] if on else COLORS['surface'],
                           activeforeground='#1e1e2e' if on else COLORS['text_dim'])

    topmost_var = tk.BooleanVar(value=False)
    topmost_btn = tk.Button(footer, text="📌", command=toggle_on_top, bg=COLORS['surface'],
                            fg=COLORS['text_dim'], relief="flat", font=("微软雅黑", 10),
                            padx=px(8), pady=px(2), cursor="hand2")
    topmost_btn.pack(side=tk.LEFT, padx=(px(15), 0))

    tk.Button(footer, text="退出", command=root.destroy, bg=COLORS['btn_danger'], fg='#1e1e2e', 
              relief="flat", font=("微软雅黑", 9, "bold"), padx=px(12), pady=px(2), cursor="hand2").pack(side=tk.RIGHT)
    
    copy_btn = tk.Button(footer, text="复制MD5", command=copy_md5, bg=COLORS['btn_primary'], fg='#1e1e2e', 
                         relief="flat", font=("微软雅黑", 9, "bold"), padx=px(12), pady=px(2), cursor="hand2")
    copy_btn.pack(side=tk.RIGHT, padx=(0, px(10)))

    root.mainloop()

