# MURAMASA-Extractor

用于浏览和解包《装甲恶鬼村正》相关 NPA 存档的桌面工具。程序不附带游戏存档或提取出的游戏资源；请自行选择本机上的 `.npa` 文件。

## 功能

- 浏览 NPA 存档目录、查看条目和文件大小。
- 预览常见图片格式，并解包全部文件或选中的条目。
- 自动识别或手动选择本篇、邪念编、赎罪篇的数据配置。
- 自动选择或手动指定文件路径编码（CP932、GBK、UTF-8）。
- 显示解包进度，支持取消任务，并可在完成后打开输出文件夹。
- 记住上次使用的存档、输出目录和界面选项。

当前图形界面以浏览和解包为主。底层 Python 模块还包含 `pack()` API，但 GUI 不提供打包入口；生成的 NPA 能否被游戏识别没有保证。

## 使用

### Windows 可执行文件

从仓库的 `dist/MURAMASA-Extractor.exe` 下载并运行，再选择 NPA 存档和输出目录开始解包。默认输出目录会根据存档名称生成；非空目录可能覆盖同名文件，程序会在开始前提示。

首次启动时，如果没有保存过存档路径，程序会尝试从程序目录下的 `npa` 文件夹选择一个 `.npa` 文件，并优先选择 `cg.npa`。也可以随时通过浏览按钮手动选择。

设置保存在 Windows 的 `%APPDATA%\MURAMASA-Extractor\settings.json`。设置文件只记录路径和界面选项，不包含存档内容。

### 从源码运行

需要 Python 3.10 或更高版本。以下命令在项目根目录的 PowerShell 中运行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-build.txt
python src\MURAMASA_GUI.py
```

### 构建 Windows exe

```powershell
python -m pip install -r requirements-build.txt
.\build\build_exe.ps1
```

构建完成后，可执行文件位于 `dist/MURAMASA-Extractor.exe`。发布 exe 时请同时提供仓库中的 `THIRD_PARTY_NOTICES.md`，并核对实际构建依赖所要求的许可文件。构建会沿用 `assets/images/` 中的界面图片，并从 `icon_portrait.png` 生成程序图标。

## 项目文件

```text
src/                    图形界面与 NPA 处理模块
assets/images/          程序界面使用的图片素材
assets/icons/           Windows 程序图标
build/                  PyInstaller 配置和 Windows 构建脚本
requirements-build.txt  构建及运行所需的 Python 依赖
```

## 来源与第三方许可

`src/MURAMASA.py` 的部分 NPA 处理实现改编自 [oldprincess/GalgameCracker](https://github.com/oldprincess/GalgameCracker/tree/main/MURAMASA)。上游项目采用 MIT License；版权声明和许可全文见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。上游 README 也记录了其实现参考 Asmodean 的 `exnpa`。此处用于说明代码来源，不代表本项目与上游作者或游戏发行商有关联。

本项目自己的代码目前没有另行指定许可证。若没有单独的 `LICENSE`，公开仓库并不会自动授予他人复制、修改或再发布本项目原创部分的权限。

## 游戏内容与版权

本项目是独立工具，与 Nitroplus 或《装甲恶鬼村正》的发行方无关联。游戏名称及相关游戏内容的权利归各自权利人所有。仓库不分发 NPA 存档或从存档提取的数据；`assets/images/` 中的界面图片按项目现有版本保留并随程序构建。公开发布前，请确认有权再分发这些图片及其打包后的 exe。请只处理自己有权使用的 NPA 文件。
