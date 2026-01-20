# <img src="icon/icon.png" width="32" height="32" align="center" /> UniVal (Universal Validator)

**一款现代化、轻量级的配置文件校验与实用工具箱**。

旨在解决开发过程中常见的配置文件格式错误，支持 JSON/JSON5/YAML 深度语法检测，并集成文件哈希计算功能。

---

## ✨ 核心特性

### 🔍 深度语法校验
- **JSON/JSON5**
  - **智能注释识别**：自动忽略 `//` 和 `/* */` 注释
  - **结构平衡分析**：追踪 `{}`、`[]`、`""` 层级，精确定位括号不匹配
  - **逗号检测**：智能识别缺失逗号和异常尾随逗号
- **YAML**
  - **缩进一致性**：严查空格/Tab 混用，防止隐形缩进错误
  - **层级逻辑**：检测缩进层级异常
  - **键名冲突**：发现同一层级下的重复键（如重复定义的配置项）

### 🛠️ 实用工具箱
- **MD5 计算器**：拖拽任意格式文件，即刻显示并复制 MD5 值
- **GUI / CLI 双模式**：
  - **GUI 模式**：现代化深色主题界面，支持拖拽操作，Windows 完美体验
  - **CLI 模式**：支持 CI/CD 管道集成，Linux 服务器批量校验

---

## 📦 支持格式一览

| 格式 | 扩展名 | 检测能力 |
| :--- | :--- | :--- |
| **JSON / JSON5** | `.json`, `.json5` | 语法结构、括号匹配、逗号检查、注释忽略 |
| **YAML** | `.yaml`, `.yml` | 缩进规范、重复键、语法解析 |
| **其他文件** | `*.*` | MD5 哈希计算 |

---

## 🚀 快速开始

### 方式一：直接运行 (GUI)
双击 `UniVal.exe` 或运行脚本启动图形界面：
```bash
python unival.py
```
> **操作提示**：直接将文件拖入窗口即可，程序会自动识别文件类型并输出结果。

### 方式二：命令行工具 (CLI)
适合脚本调用或批量处理：
```bash
# 校验单个文件
python unival.py config.json

# 批量校验
python unival.py config.yaml data.json

# 获取任意文件 MD5
python unival.py setup.exe
```

---

## 🔧 安装依赖

确保已安装 Python 3.6+，然后安装核心依赖库：

```bash
pip install json5 pyyaml tkinterdnd2 pillow
```

---

## � 开发指南

### � 源码编译 (Build EXE)
如果你需要分发给没有 Python 环境的用户使用，可打包为单文件 EXE。

**1. 准备图标**
```bash
# 将 PNG 图标转换为 ICO 格式
python -c "from PIL import Image; img = Image.open('icon/icon.png'); img.save('icon/icon.ico', format='ICO', sizes=[(256,256),(48,48),(32,32),(16,16)])"
```

**2. 执行打包**
```bash
# 使用 PyInstaller 编译 (需安装: pip install pyinstaller)
pyinstaller --onefile --windowed --icon=icon/icon.ico --name=UniVal unival.py
```

### 📂 项目结构
```
unival/
├── unival.py           # 核心源码 (GUI + 逻辑)
├── theme-error.json    # 测试用例文件
├── icon/               # 图标资源目录
│   ├── icon.png        # 原图
│   └── icon.ico        # 编译用图标
├── .github/workflows/  # GitHub Actions 自动构建配置
├── CHANGELOG.md        # 版本更新记录
└── README.md           # 项目文档
```

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 授权开源。

## 👤 作者

**yeqing**
