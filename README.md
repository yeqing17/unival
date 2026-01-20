# UniVal

**Universal Validator** - 一款轻量级的结构化配置文件校验工具

---

## ✨ 功能特性

- **智能注释识别**：自动忽略 `//` 和 `/* */` 注释（JSON5）
- **深度结构分析**：追踪 `{}`、`[]`、`""` 层级，识别不匹配括号
- **缺失逗号检测**：发现遗漏逗号的行
- **YAML 缩进检测**：检测空格/Tab 混用、缩进层级异常
- **重复键检测**：发现同层级重复定义的键名（YAML）
- **命令行 & GUI 双模式**：支持 Linux 服务器和 Windows 桌面使用

---

## 📦 支持格式

| 格式 | 状态 |
|------|------|
| JSON / JSON5 | ✅ 已支持 |
| YAML / YML | ✅ 已支持 |
| XML | 📋 待定 |

---

## 🚀 使用方法

### GUI 模式
```bash
python unival.py
# 或双击 UniVal.exe
```

### 命令行模式
```bash
python unival.py config.json
python unival.py config.yaml
python unival.py file1.json file2.yaml  # 批量校验
```

### 安装依赖
```bash
pip install json5 pyyaml tkinterdnd2
```

---

## 🔍 YAML 检测能力

- **缩进一致性**：检测空格与Tab混用问题
- **缩进层级**：识别不符合缩进规则的行
- **重复键检测**：发现同一层级重复定义的键
- **语法解析**：使用 PyYAML 进行最终语法校验，精确定位错误行号

---


## 📁 项目结构

```
unival/
├── unival.py      # 主程序
├── README.md      # 说明文档
├── CHANGELOG.md   # 版本更新记录
└── icon/          # 图标资源
    ├── icon.ico   # 应用图标
    └── ICON_PROMPTS.md  # 图标设计提示词
```

---

## 🔨 编译 EXE

### 本地编译
```bash
# PNG 转 ICO（需安装 Pillow）
python -c "from PIL import Image; img = Image.open('icon/icon.png'); img.save('icon/icon.ico', format='ICO', sizes=[(256,256),(48,48),(32,32),(16,16)])"

# 编译为单文件 EXE
pyinstaller --onefile --windowed --icon=icon/icon.ico --name=UniVal unival.py
```

### GitHub Actions 自动编译
推送 `v*` 格式的 tag 会自动触发编译并发布 Release：
```bash
git tag v2.0.0
git push origin v2.0.0
```

---

## 📄 License

MIT License

## 👤 Author

yeqing
