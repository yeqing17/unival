# UniVal

**Universal Validator** - 一款轻量级的结构化配置文件校验工具

---

## ✨ 功能特性

- **智能注释识别**：自动忽略 `//` 和 `/* */` 注释
- **深度结构分析**：追踪 `{}`、`[]`、`""` 层级，识别不匹配括号
- **缺失逗号检测**：发现遗漏逗号的行
- **命令行 & GUI 双模式**：支持 Linux 服务器和 Windows 桌面使用

---

## 📦 支持格式

| 格式 | 状态 |
|------|------|
| JSON / JSON5 | ✅ 已支持 |
| YAML | 🚧 计划中 |
| XML | 📋 待定 |

---

## � 使用方法

### GUI 模式
```bash
python unival.py
# 或双击 UniVal.exe
```

### 命令行模式
```bash
python unival.py config.json
python unival.py file1.json file2.json  # 批量校验
```

### 安装依赖
```bash
pip install json5 tkinterdnd2
```

---

## 🗺️ 开发计划：YAML 支持

- **v7.0** - 基础解析与行号定位
- **v7.1** - 缩进检测（空格/Tab 混用）
- **v7.2** - 结构平衡（列表/字典嵌套）
- **v8.0** - 统一多格式界面 & 批量校验

---

## 📁 项目结构

```
unival/
├── unival.py      # 主程序
├── README.md      # 说明文档
└── theme.json     # 示例文件
```

---

## 📄 License

MIT License

## 👤 Author

yeqing
