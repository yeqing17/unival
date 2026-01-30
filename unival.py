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

# ==================== YAML 检测函数 (基于 yamllint) ====================

# yamllint 内嵌配置（与项目根目录 .yamllint 保持一致）
YAMLLINT_CONFIG = """
extends: default
rules:
  # 核心校验规则（warning级别）
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
    max-spaces-inside: 1  # 允许1个空格，适应 { key: value } 风格
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
  # 关闭纯美观类校验
  new-lines: disable
  new-line-at-end-of-file: disable
  comments-indentation: disable
  document-start: disable
  comments: disable
"""

def parse_yaml_with_yamllint(file_path):
    """使用 yamllint 检测 YAML 文件，返回格式化的错误列表"""
    try:
        from yamllint import linter
        from yamllint.config import YamlLintConfig
    except ImportError:
        return None, "yamllint 未安装，请执行: pip install yamllint"
    
    try:
        # 使用内嵌配置
        config = YamlLintConfig(YAMLLINT_CONFIG)
        
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
        return f"{result}\n{md5_line}"
    
    # JSON/JSON5 文件处理
    success, msg, context = check_structural_balance(content)
    if not success:
        return f"{header}\n❌ {msg}\n{context}\n{md5_line}"
    try:
        json5.loads(content)
        if re.search(r',\s*[}\]]', get_clean_content(content)):
            return f"{header}\n❌ 语法错误：检测到异常尾随逗号\n{md5_line}"
        return f"{header}\n✅ 解析正常\n{md5_line}"
    except Exception as e:
        return f"{header}\n❌ 解析错误: {e}\n{md5_line}"

# 全局变量保存当前文件的MD5值
current_md5 = ""
gui_state = {'save_log': None}  # GUI 状态容器

def get_files_from_path(path):
    """获取路径下的所有支持文件（支持文件和文件夹）"""
    supported_extensions = ('.json', '.json5', '.yaml', '.yml')
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
        result_text.insert(tk.END, "未找到支持的文件 (.json, .json5, .yaml, .yml)")
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

def get_files_to_check(path):
    """获取需要检测的文件列表，支持文件和文件夹"""
    supported_extensions = ('.json', '.json5', '.yaml', '.yml')
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
    drop_area = tk.Label(root, text="📁 拖拽文件或文件夹至此处\n支持 JSON / YAML 校验 + MD5 计算", 
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
    
    version_label = tk.Label(footer, text="⚡ v4.0.0", font=("Consolas", 9), bg=COLORS['bg'], 
                             fg=COLORS['accent'], cursor="hand2")
    version_label.pack(side=tk.LEFT)
    version_label.bind("<Button-1>", open_github)
    
    # 保存日志复选框
    gui_state['save_log'] = tk.BooleanVar(value=False)
    log_checkbox = tk.Checkbutton(footer, text="保存日志", variable=gui_state['save_log'],
                                   bg=COLORS['bg'], fg=COLORS['text_dim'], 
                                   selectcolor=COLORS['surface'], activebackground=COLORS['bg'],
                                   activeforeground=COLORS['text'], font=("微软雅黑", 9))
    log_checkbox.pack(side=tk.LEFT, padx=(15, 0))
    
    tk.Button(footer, text="退出", command=root.destroy, bg=COLORS['btn_danger'], fg='#1e1e2e', 
              relief="flat", font=("微软雅黑", 9, "bold"), padx=12, pady=2, cursor="hand2").pack(side=tk.RIGHT)
    
    copy_btn = tk.Button(footer, text="复制MD5", command=copy_md5, bg=COLORS['btn_primary'], fg='#1e1e2e', 
                         relief="flat", font=("微软雅黑", 9, "bold"), padx=12, pady=2, cursor="hand2")
    copy_btn.pack(side=tk.RIGHT, padx=(0, 10))

    root.mainloop()

