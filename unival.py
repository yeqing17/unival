import json5
import re
import os
import tkinter as tk
from tkinter import scrolledtext
from tkinterdnd2 import DND_FILES, TkinterDnD

def get_indent(line):
    return len(line) - len(line.lstrip())

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

def parse_content_by_file(file_path):
    content = None
    for enc in ['utf-8', 'gbk', 'utf-16']:
        try:
            with open(file_path, 'r', encoding=enc) as f: content = f.read()
            break
        except UnicodeDecodeError: continue
    if not content: return "解析失败：无法读取文件内容。"
    
    success, msg, context = check_structural_balance(content)
    if not success:
        return f"【文件】: {os.path.basename(file_path)}\n------------------\n{msg}\n{context}"
    try:
        json5.loads(content)
        if re.search(r',\s*[}\]]', get_clean_content(content)):
            return f"【文件】: {os.path.basename(file_path)}\n------------------\n语法错误：检测到异常尾随逗号"
        return f"【文件】: {os.path.basename(file_path)}\n------------------\n解析正常"
    except Exception as e:
        return f"【文件】: {os.path.basename(file_path)}\n------------------\n解析错误: {e}"

def on_drop(event):
    files = root.tk.splitlist(event.data)
    if not files: return
    result = parse_content_by_file(files[0].strip('{}'))
    result_text.config(state=tk.NORMAL)
    result_text.delete('1.0', tk.END)
    result_text.insert(tk.END, result)
    result_text.tag_config("c", foreground="#00c853" if "解析正常" in result else "#ff1744")
    result_text.tag_add("c", "1.0", tk.END)
    result_text.config(state=tk.DISABLED)

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
    # GUI 模式
    root = TkinterDnD.Tk()
    root.title("UniVal")
    root.geometry("480x320")
    root.configure(bg="#fefefe")
    root.resizable(False, False)

    drop_area = tk.Label(root, text="拖拽文件至此处校验", font=("微软雅黑", 10), bg="#fafafa", fg="#9e9e9e", height=4,
                         highlightthickness=1, highlightbackground="#e0e0e0")
    drop_area.pack(fill=tk.X, padx=12, pady=(12, 6))
    drop_area.drop_target_register(DND_FILES)
    drop_area.dnd_bind('<<Drop>>', on_drop)

    result_text = scrolledtext.ScrolledText(root, height=9, font=("Consolas", 10), state=tk.DISABLED, bg="#fff", fg="#424242",
                                            relief="flat", highlightthickness=1, highlightbackground="#eee")
    result_text.pack(fill=tk.BOTH, padx=12, expand=True)

    footer = tk.Frame(root, bg="#fefefe")
    footer.pack(fill=tk.X, padx=12, pady=8)
    tk.Label(footer, text="v1.0.0", font=("Consolas", 8), bg="#fefefe", fg="#bdbdbd").pack(side=tk.LEFT)
    tk.Button(footer, text="退出", command=root.destroy, bg="#ff5252", fg="white", relief="flat", font=("微软雅黑", 9), padx=10).pack(side=tk.RIGHT)

    root.mainloop()

