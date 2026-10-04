# Track Separator

[English](README.md) | [简体中文](README-CN.md)

Track Separator 是一款在 Windows 本地运行的音轨分离工具，可将音频分离为六个声部：**人声、鼓、贝斯、吉他、钢琴和其他**。导入音频后，即可分离、试听各个声部，并打开保存完整质量 WAV 文件的文件夹。

无需账号或 API 密钥，音频分离在本机完成，不使用云端推理。应用专注于音轨分离，不包含和弦分析或 MIDI 导出。

## 安装与启动

从 [Releases](https://github.com/MDFX03-ctrl/TrackSeparator/releases) 下载 `TrackSeparator-Setup.exe`，安装后从开始菜单打开 **Track Separator**。

如使用便携版本，请保留整个 `dist/TrackSeparator` 文件夹，再双击其中的 `TrackSeparator.exe`。可执行文件依赖同目录下的 `_internal` 文件夹，请勿只复制 EXE。项目中的 `start-app.bat` 也可启动本地构建的程序。

安装包已包含运行环境和 FFmpeg，普通用户无需另行安装 Python、Node 或 FFmpeg。目前主要面向 Windows 11 x64。

## 使用方法

1. 展开 **Model setup**（模型设置），点击 **Download model**（下载模型），完成首次模型下载。模型约 52 MB，下载后会验证固定的完整 SHA-256 校验值。模型准备好后，可离线进行分离。
2. 选择或拖入一个时长不超过 15 分钟的音频文件。支持 WAV、MP3、M4A、AAC、OGG、FLAC、AIFF 和 WMA。当模型就绪且没有其他任务运行时，应用会自动开始分离；否则，可在音轨列表中点击 **Separate**（分离）。
3. 等待六个声部生成。CPU 处理耗时可能超过音频本身的时长。**Cancel**（取消）可停止任务；**Retry**（重试）会复用匹配的已完成结果，或重新进行分离。关闭浏览器页面不会停止后台处理。
4. 点击 **Open stems**（打开声部），在 **Listen to** 中选择声部，即可使用音频播放器试听。六个 WAV 文件已经保存在本地；点击 **Open stems folder**（打开声部文件夹）即可在文件资源管理器中查看，无需再次下载或复制。

**Library and settings**（音频库与设置）可选择其他音频库文件夹，但不会自动移动原有文件。**Remove**（移除）会将音轨放入可恢复的回收区；通过 **Show trash**（查看回收区）和 **Restore**（恢复）可找回音轨。**Quit app**（退出应用）会停止本地服务和处理任务。

## 数据保存位置

新安装默认使用 `%LOCALAPPDATA%/TrackSeparator` 保存应用数据。如果存在旧版 Music Digest Chords 的数据目录，且新数据目录尚不存在，应用会复用旧目录，以保留音频库、设置和本地模型。已分离的声部仍可使用，升级和卸载会保留音频库。

启动 Track Separator 时，应用会自动关闭占用共享音频库锁的空闲旧版进程。如果旧版仍有任务运行，需要先完成或取消该任务。

## 源码开发

Python 应用源码位于 `trackseparator/`，界面文件位于 `viewer/`。仓库包含源码和构建脚本，不包含安装包、运行环境包、模型权重或个人音频。发布构建方式见 [构建说明](build/README.md)。

开发需使用 Python 3.11 x64，并将 FFmpeg 加入 PATH。创建虚拟环境并安装固定版本的 CPU 依赖：

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install torch==2.5.1+cpu torchaudio==2.5.1+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r build/requirements-lock.txt
python -m trackseparator doctor
python -m trackseparator app
```

可使用环境变量 `TRACK_SEPARATOR_DATA_HOME`，或启动参数 `app --data-home FOLDER`，指定独立的数据目录。应用也兼容旧版环境变量 `MDCHORD_DATA_HOME`。

## 卸载

通过 Windows 的“已安装的应用”卸载，或运行安装目录中的 `unins000.exe`。

卸载程序会关闭安装目录对应的应用进程，删除程序文件和运行过程中生成的私有运行环境缓存，并移除空的安装文件夹。保存在安装目录之外的模型、设置、音频和声部会保留。

`unins000.exe` 属于其对应的安装记录，不作为独立文件分发，也不应在不同安装之间直接复制。

## 致谢与许可证

本项目提供本地 Windows 界面、音频库管理、分离任务、声部试听和安装流程。音轨分离引擎及 `htdemucs_6s` 模型来自 [Demucs](https://github.com/facebookresearch/demucs)。Demucs 使用本机 CPU 进行处理；模型仅在用户主动进行模型设置时下载。

Track Separator 由 Music Digest Chords 演变而来。应用源码采用 MIT 许可证，原有贡献者署名保留在 [LICENSE](LICENSE) 中。随安装包分发的依赖具有各自的许可证，详见 [THIRD-PARTY.md](THIRD-PARTY.md)。
