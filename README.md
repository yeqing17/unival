# <img src="icon/icon.png" width="32" height="32" align="center" /> UniVal (Universal Validator)

**一款现代化、轻量级的配置文件校验与实用工具箱**。

旨在解决开发过程中常见的配置文件格式错误，支持 JSONC (JSON with Comments) / YAML 深度语法检测，并集成文件哈希计算功能。

---

## ✨ 核心特性

### 🔍 深度语法校验
- **JSON / JSONC**（按 JSONC 规范严格校验）
  - **智能注释识别**：自动忽略 `//` 和 `/* */` 注释
  - **严格语法校验**：正确拒绝单引号字符串、未加引号的键、十六进制数字等 JSON5 私有语法
  - **精准错误定位**：解析失败时附带精确的「行:列」位置并翻译为中文，同时给出括号平衡等参考分析
  - **结构平衡分析**：追踪 `{}`、`[]`、`""` 层级，精确定位括号不匹配
  - **逗号检测**：智能识别缺失逗号和异常尾随逗号
  - **不可见字符检测**：发现隐藏的 NO-BREAK SPACE、ZERO WIDTH SPACE、BOM 等 15 种不可见字符
- **YAML** (基于专业工具 [yamllint](https://github.com/adrienverge/yamllint))
  - **语法错误**：检测层级未闭合、格式混乱等致命问题
  - **重复键**：发现同一层级下的重复键（会导致数据丢失）
  - **缩进规范**：检测缩进不一致、空格数量错误等问题
  - **格式规范**：冒号空格、大括号空格、行尾空格、空白行过多
  - **布尔值歧义**：检测 `on/off/yes/no` 等易误解析的值

### 📋 YAML 检测规则（基于 yamllint）

| 类型 | 规则 | 级别 | 说明 |
|------|------|------|------|
| **语法** | `syntax` | error | 语法错误，必须修复 |
| **重复键** | `key-duplicates` | error | 同层级键名重复，会导致数据丢失 |
| **缩进** | `indentation` | warning | 缩进不一致（推荐 2 空格） |
| **冒号** | `colons` | warning | 冒号前后空格不规范 |
| **大括号** | `braces` | warning | 大括号内空格过多 |
| **行尾空格** | `trailing-spaces` | warning | 行尾存在多余空格 |
| **空白行** | `empty-lines` | warning | 连续空白行超过 2 行 |
| **布尔值** | `truthy` | warning | 布尔值歧义（建议用引号包裹） |
| **行长度** | `line-length` | warning | 单行超过 160 字符 |


### 🛠️ 实用工具箱
- **MD5 计算器**：拖拽任意格式文件，即刻显示并复制 MD5 值
- **GUI / CLI 双模式**：
  - **GUI 模式**：现代化深色主题界面，支持拖拽操作，Windows 完美体验
  - **CLI 模式**：支持 CI/CD 管道集成，Linux 服务器批量校验

---

## 📦 支持格式一览

| 格式 | 扩展名 | 检测能力 |
| :--- | :--- | :--- |
| **JSON / JSONC** | `.json` | 语法结构、括号匹配、逗号检查、不可见字符、注释忽略 |
| **YAML** | `.yaml`, `.yml` | 缩进规范、重复键、保留字符、语法解析 |
| **其他文件** | `*.*` | MD5 哈希计算 |


---

## 🚀 快速开始

### 方式一：直接运行 (GUI)
双击 `UniVal.exe` 或运行脚本启动图形界面：
```bash
python unival.py
```
> **操作提示**：将文件或文件夹拖入窗口即可，程序会自动识别文件类型并输出结果。

### 方式二：命令行工具 (CLI)
适合脚本调用或批量处理：
```bash
# 校验单个文件
python unival.py config.json

# 校验整个文件夹（递归扫描）
python unival.py ./configs/

# 批量校验多个文件
python unival.py config.yaml data.json

# 获取任意文件 MD5
python unival.py setup.exe
```

---

## 🔧 安装依赖

确保已安装 Python 3.6+，然后安装核心依赖库：

```bash
pip install pyyaml yamllint tkinterdnd2 pillow
```

---

## 📦 开发指南

### ⚙️ 源码编译 (Build EXE)
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
├── icon/               # 图标资源目录
│   ├── icon.png/icon_transparent.png        # 原图/透明图
│   └── icon.ico        # 编译用图标
├── .github/workflows/  # GitHub Actions 自动构建配置
├── CHANGELOG.md        # 版本更新记录
└── README.md           # 项目文档
```

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 授权开源。

## 🙏 鸣谢

- [yamllint](https://github.com/adrienverge/yamllint) - 本项目 YAML 检测功能完全基于 yamllint 实现，感谢 Adrien Vergé 及所有贡献者

## 👤 作者

**yeqing**
