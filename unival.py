import json5
import yaml
import re
import os
import hashlib
import tkinter as tk
from tkinter import scrolledtext
from tkinterdnd2 import DND_FILES, TkinterDnD

def calculate_md5(file_path):
    """计算文件的MD5值"""
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_indent(line):
    return len(line) - len(line.lstrip())

# ==================== YAML 检测函数 ====================

def check_yaml_indent_consistency(content):
    """检测YAML缩进一致性：空格/Tab混用问题"""
    lines = content.split('\n')
    has_tabs = False
    has_spaces = False
    mixed_lines = []
    
    for idx, line in enumerate(lines, 1):
        if not line.strip() or line.strip().startswith('#'):
            continue
        leading = line[:len(line) - len(line.lstrip())]
        if '\t' in leading:
            has_tabs = True
            if ' ' in leading:
                mixed_lines.append(idx)
        elif ' ' in leading:
            has_spaces = True
    
    if mixed_lines:
        return False, f"缩进错误：第 {mixed_lines[0]} 行存在空格与Tab混用", \
               f"参考分析：该行的缩进同时包含空格和Tab字符，YAML规范建议只使用空格。\n涉及行号：{mixed_lines[:5]}{'...' if len(mixed_lines) > 5 else ''}"
    
    if has_tabs and has_spaces:
        return False, "缩进警告：文件中同时存在Tab和空格缩进", \
               "参考分析：建议统一使用空格进行缩进（推荐2或4个空格）"
    
    return True, "", ""

def check_yaml_indent_levels(content):
    """检测YAML缩进层级问题"""
    lines = content.split('\n')
    indent_stack = [0]
    
    for idx, line in enumerate(lines, 1):
        if not line.strip() or line.strip().startswith('#'):
            continue
        
        current_indent = get_indent(line)
        prev_indent = indent_stack[-1]
        
        # 检查缩进是否合理
        if current_indent > prev_indent:
            # 缩进增加，记录新层级
            indent_stack.append(current_indent)
        elif current_indent < prev_indent:
            # 缩进减少，回退到之前的层级
            while indent_stack and indent_stack[-1] > current_indent:
                indent_stack.pop()
            if not indent_stack or indent_stack[-1] != current_indent:
                # 缩进不匹配任何已知层级
                return False, f"缩进错误：第 {idx} 行缩进异常", \
                       f"参考分析：当前缩进 {current_indent} 个空格，但无法对应到任何上级层级。\n期望的缩进层级为：{indent_stack}"
    
    return True, "", ""

def check_yaml_colon_space(content):
    """检测YAML冒号后是否有空格"""
    lines = content.split('\n')
    
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        
        # 检查键值对格式 key:value (冒号后无空格)
        # 但要排除 URL 中的冒号（如 http://）
        if ':' in stripped and not stripped.endswith(':'):
            # 查找所有冒号位置
            for i, char in enumerate(stripped):
                if char == ':':
                    # 跳过URL中的冒号
                    if i > 0 and stripped[i-1:i+2] in ['://']:
                        continue
                    # 检查冒号是否在字符串内（简单判断）
                    if i + 1 < len(stripped) and stripped[i+1] not in [' ', '\t', '\n', '/', '\\']:
                        # 可能是没有空格的键值对
                        if '"' not in stripped[:i] and "'" not in stripped[:i]:
                            # 排除端口号等纯数字情况
                            rest = stripped[i+1:].strip()
                            if rest and not rest[0].isdigit():
                                return False, f"格式警告：第 {idx} 行冒号后可能缺少空格", \
                                       f"参考分析：'{stripped[:30]}...' 中的冒号后建议添加空格"
    
    return True, "", ""

def check_yaml_duplicate_keys(content):
    """检测YAML重复键（同一层级）"""
    lines = content.split('\n')
    indent_keys = {}  # {缩进级别: {键名: 行号}}
    current_indent = 0
    in_list_context = {}  # 记录每个缩进层级是否在列表上下文中
    
    for idx, line in enumerate(lines, 1):
        if not line.strip() or line.strip().startswith('#'):
            continue
        
        indent = get_indent(line)
        stripped = line.strip()
        
        # 缩进变化时重置对应层级的键记录
        if indent < current_indent:
            # 清除所有更深层级的记录
            indent_keys = {k: v for k, v in indent_keys.items() if k <= indent}
            in_list_context = {k: v for k, v in in_list_context.items() if k < indent}
        
        # 检测列表项（- 开头），列表项内的同名键不算重复
        if stripped.startswith('-'):
            # 这是一个列表项，清除当前及更深层级的键记录
            keys_to_clear = [k for k in indent_keys if k >= indent]
            for k in keys_to_clear:
                indent_keys[k] = {}
            in_list_context[indent] = True
            
            # 列表项可能包含内联键值对，如 "- name: value"
            if ':' in stripped:
                # 提取列表项后的键
                after_dash = stripped[1:].strip()
                if ':' in after_dash:
                    key = after_dash.split(':')[0].strip().strip('"').strip("'")
                    # 列表项的键在父列表上下文中不检查重复
        elif ':' in stripped:
            # 普通键值对
            key = stripped.split(':')[0].strip().strip('"').strip("'")
            
            if indent not in indent_keys:
                indent_keys[indent] = {}
            
            # 只有在非列表上下文中才检查重复键
            if key in indent_keys[indent]:
                # 检查是否在列表上下文中
                parent_indent = max([i for i in in_list_context if i < indent], default=-1)
                if parent_indent < 0 or not in_list_context.get(parent_indent, False):
                    prev_line = indent_keys[indent][key]
                    return False, f"重复键错误：第 {idx} 行的键 '{key}' 重复", \
                           f"参考分析：该键在第 {prev_line} 行已定义，重复定义会覆盖之前的值"
            
            indent_keys[indent][key] = idx
        
        current_indent = indent
    
    return True, "", ""


def parse_yaml_content(content, file_path):
    """解析YAML内容并返回校验结果"""
    filename = os.path.basename(file_path)
    
    # 1. 检测缩进一致性（空格/Tab混用）
    success, msg, context = check_yaml_indent_consistency(content)
    if not success:
        return f"【文件】: {filename}\n------------------\n{msg}\n{context}"
    
    # 2. 检测缩进层级
    success, msg, context = check_yaml_indent_levels(content)
    if not success:
        return f"【文件】: {filename}\n------------------\n{msg}\n{context}"
    
    # 3. 检测重复键
    success, msg, context = check_yaml_duplicate_keys(content)
    if not success:
        return f"【文件】: {filename}\n------------------\n{msg}\n{context}"
    
    # 4. 使用PyYAML进行最终解析
    try:
        yaml.safe_load(content)
        return f"【文件】: {filename}\n------------------\n解析正常"
    except yaml.YAMLError as e:
        error_msg = str(e)
        # 提取行号信息
        line_info = ""
        if hasattr(e, 'problem_mark') and e.problem_mark:
            mark = e.problem_mark
            line_info = f"\n定位：第 {mark.line + 1} 行，第 {mark.column + 1} 列"
        return f"【文件】: {filename}\n------------------\n解析错误: {error_msg}{line_info}"

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
        thief_info = ""
        residue = stack[-1] 
        for o_row, o_indent, c_row, c_indent in reversed(matches):
            if o_row > residue['row'] and c_indent == residue['indent']:
                target_char = lines[o_row-1].strip()[0]
                thief_info = f" ，嫌疑位置：第 {o_row} 行 可能多写了左括号{target_char}"
                break
        item = stack[-1]
        analysis = f"参考分析：第 {item['row']} 行, 第 {item['col']} 列的左括号'{item['char']}'未闭合"
        return False, f"结构错误：{len(stack)} 个未闭合", f"{analysis}{thief_info}"
    return True, "", ""

def get_file_type(file_path):
    """根据文件扩展名判断文件类型"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.yaml', '.yml']:
        return 'yaml'
    elif ext in ['.json', '.json5']:
        return 'json'
    else:
        return 'unknown'

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
    if file_type == 'unknown':
        return f"【文件】: {filename}\n------------------\n{md5_line}\n（不支持的文件格式，仅显示MD5）"
    
    # 读取文件内容
    content = None
    for enc in ['utf-8', 'gbk', 'utf-16']:
        try:
            with open(file_path, 'r', encoding=enc) as f: content = f.read()
            break
        except UnicodeDecodeError: continue
    if not content: return f"【文件】: {filename}\n------------------\n{md5_line}\n解析失败：无法读取文件内容。"
    
    # YAML 文件处理
    if file_type == 'yaml':
        result = parse_yaml_content(content, file_path)
        return f"{result}\n{md5_line}"
    
    # JSON/JSON5 文件处理
    success, msg, context = check_structural_balance(content)
    if not success:
        return f"【文件】: {filename}\n------------------\n{msg}\n{context}\n{md5_line}"
    try:
        json5.loads(content)
        if re.search(r',\s*[}\]]', get_clean_content(content)):
            return f"【文件】: {filename}\n------------------\n语法错误：检测到异常尾随逗号\n{md5_line}"
        return f"【文件】: {filename}\n------------------\n解析正常\n{md5_line}"
    except Exception as e:
        return f"【文件】: {filename}\n------------------\n解析错误: {e}\n{md5_line}"

# 全局变量保存当前文件的MD5值
current_md5 = ""

def on_drop(event):
    global current_md5
    files = root.tk.splitlist(event.data)
    if not files: return
    file_path = files[0].strip('{}')
    
    # 计算并保存MD5
    try:
        current_md5 = calculate_md5(file_path)
    except:
        current_md5 = ""
    
    result = parse_content_by_file(file_path)
    result_text.config(state=tk.NORMAL)
    result_text.delete('1.0', tk.END)
    result_text.insert(tk.END, result)
    result_text.tag_config("c", foreground="#a6e3a1" if "解析正常" in result else "#f38ba8")
    result_text.tag_add("c", "1.0", tk.END)
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

if len(sys.argv) > 1:
    # 命令行模式：直接校验传入的文件
    for file_path in sys.argv[1:]:
        if os.path.isfile(file_path):
            print(parse_content_by_file(file_path))
            print()
        else:
            print(f"文件不存在: {file_path}")
else:
    # GUI 模式 - 深色主题
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
    root.geometry("520x360")
    root.configure(bg=COLORS['bg'])
    root.resizable(False, False)

    # 拖拽区域
    drop_area = tk.Label(root, text="📁 拖拽任意文件至此处\n支持 JSON / YAML 校验 + MD5 计算", 
                         font=("微软雅黑", 11), bg=COLORS['surface'], fg=COLORS['text_dim'], 
                         height=4, highlightthickness=2, highlightbackground=COLORS['border'])
    drop_area.pack(fill=tk.X, padx=16, pady=(16, 8))
    drop_area.drop_target_register(DND_FILES)
    drop_area.dnd_bind('<<Drop>>', on_drop)

    # 结果显示区
    result_text = scrolledtext.ScrolledText(root, height=10, font=("Consolas", 11), state=tk.DISABLED, 
                                            bg=COLORS['surface'], fg=COLORS['text'],
                                            relief="flat", highlightthickness=2, highlightbackground=COLORS['border'],
                                            insertbackground=COLORS['text'])
    result_text.pack(fill=tk.BOTH, padx=16, expand=True)

    # 底部栏
    footer = tk.Frame(root, bg=COLORS['bg'])
    footer.pack(fill=tk.X, padx=16, pady=12)
    
    # GitHub 链接版本号
    def open_github(event=None):
        import webbrowser
        webbrowser.open("https://github.com/yeqing17/unival")
    
    version_label = tk.Label(footer, text="⚡ v3.0.3", font=("Consolas", 9), bg=COLORS['bg'], 
                             fg=COLORS['accent'], cursor="hand2")
    version_label.pack(side=tk.LEFT)
    version_label.bind("<Button-1>", open_github)
    
    tk.Button(footer, text="退出", command=root.destroy, bg=COLORS['btn_danger'], fg='#1e1e2e', 
              relief="flat", font=("微软雅黑", 9, "bold"), padx=12, pady=2, cursor="hand2").pack(side=tk.RIGHT)
    
    copy_btn = tk.Button(footer, text="复制MD5", command=copy_md5, bg=COLORS['btn_primary'], fg='#1e1e2e', 
                         relief="flat", font=("微软雅黑", 9, "bold"), padx=12, pady=2, cursor="hand2")
    copy_btn.pack(side=tk.RIGHT, padx=(0, 10))

    root.mainloop()

