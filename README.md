# anjian20251212

一个基于 Python/Tkinter 的桌面自动化工具，用于管理脚本、按键操作、坐标选择、截图识别等本地自动化流程。

## 功能概览

- 图形化主控台
- 脚本文件管理与编辑
- 鼠标、键盘操作录制与执行
- 坐标拾取与屏幕截图辅助
- 可拖拽导入文件，未安装 `tkinterdnd2` 时会自动降级
- 本地配置自动生成，不需要提交到仓库

## 运行环境

- Windows
- Python 3.10 或更高版本

## 安装依赖

```powershell
pip install -r requirements.txt
```

## 启动方式

```powershell
python anjian20251212.py
```

也可以在 Windows 下运行：

```powershell
.\anjian26.bat
```

## 配置说明

程序运行时可能会在本地生成 `config.json`、`*.ini`、`*.log` 等配置或日志文件。这些文件通常包含本机路径、窗口布局、运行状态或个人配置，已经通过 `.gitignore` 排除，不建议上传到 GitHub。

## 开源前检查

提交前建议确认：

- 没有上传本地配置、日志或个人路径
- 没有上传打包生成的 `.exe`
- 没有上传临时备份目录，例如 `bak/`、`nouse/`

## License

本项目使用 MIT License，详见 [LICENSE](LICENSE)。
