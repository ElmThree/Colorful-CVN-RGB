# Colorful CVN Motherboard RGB Light Engine

> 七彩虹 CVN 系列主板 Linux RGB 灯光控制引擎

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-green.svg)]()
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-yellow.svg)]()

---

## 背景

七彩虹没有提供 Linux 驱动，OpenRGB 也不支持该系列主板。本项目通过在 Windows 下抓取官方软件的 USB HID 通信数据包，逆向分析出底层控制协议，在 Linux 下直接写入 `/dev/hidraw` 设备节点实现完整的灯光控制。

---

## 功能

- `solid`   — 单色静态常亮
- `off`     — 关闭灯光
- `rainbow` — 幻彩彩虹滚动
- `flow`    — 单色水波纹流光
- CS2 GSI 联动（见 cs2 分支）

---

## 硬件协议逆向记录

### 工具

- Windows：[Device Monitoring Studio](https://www.hhdsoftware.com/device-monitoring-studio)（抓取 USB HID 原始数据包）
- Linux：`hidapi`、`udevadm`、`/dev/hidraw*`

### 设备信息

| 字段 | 值 |
|---|---|
| VID | `0x2F4C` |
| PID | `0x1000` |
| 设备名 | `COLORFUL` |
| 控制接口 | Interface 2（`ID_USB_INTERFACE_NUM=02`） |
| hidraw 节点 | `/dev/hidraw*`（编号不固定，见下方 udev 配置） |

### HID 数据帧格式

设置颜色需连续发送 **11 个 64 字节数据包**：

**RGB 数据帧（共 10 帧，seq = 0x00 ~ 0x09）：**

```
字节偏移  内容
───────────────────────────────
00        0x01（固定）
01        0x00（固定）
02        0x88（固定，静态颜色命令字）
03        0x00~0x09（分包序号）
04~63     RGB 数据，每 3 字节一颗 LED，共 20 颗
```

**同步帧（第 11 帧，触发固件刷新并永久保存）：**

```
字节偏移  内容
───────────────────────────────
00        0x01
01        0x00
02        0x88
03        0xFF（同步标志）
04~63     全 0x00
```

### LED 地址空间

```
每帧 payload = 64 - 4（头部）= 60 字节
60 ÷ 3（RGB）= 每帧 20 颗 LED
10 帧 × 20 = 共 200 个 LED 地址
```

实际灯珠数量取决于主板型号，多余地址发送后固件忽略。

### 关键结论

- 官方软件**没有特殊的夺权/模式切换命令**，流水彩虹效果由软件持续发包实现
- 发送同步帧后颜色**永久保存**在固件，断开连接后保持不变，无需持续发包
- Linux 下需直接操作 `/dev/hidraw` 节点，`hidapi` 的路径解析在部分发行版下有兼容问题

---

## 环境要求

- Linux（测试环境：Manjaro）
- Python 3.10+
- 无需额外依赖（标准库即可）

---

## 安装与配置

### 1. 克隆项目

```bash
git clone https://github.com/YOUR_USERNAME/colorful-rgb-engine.git
cd colorful-rgb-engine
```

### 2. 找到正确的 hidraw 节点

```bash
# 找到对应 VID/PID 的 hidraw 设备
grep -rl "2F4C" /sys/class/hidraw/*/device/uevent

# 确认接口号
udevadm info /dev/hidrawX | grep -i interface
# 找到 ID_USB_INTERFACE_NUM=02 对应的节点即为控制接口
```

### 3. 配置 udev 规则（永久固定设备路径，无需 sudo）

```bash
sudo tee /etc/udev/rules.d/99-colorful-rgb.rules << 'RULE'
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="2f4c", ATTRS{idProduct}=="1000", ENV{ID_USB_INTERFACE_NUM}=="02", SYMLINK+="colorful-rgb", MODE="0666"
RULE

sudo udevadm control --reload-rules && sudo udevadm trigger

# 验证符号链接是否创建成功
ls -la /dev/colorful-rgb
# 预期输出：lrwxrwxrwx ... /dev/colorful-rgb -> hidrawX
```

配置完成后即可无需 `sudo` 直接运行脚本。

---

## 使用方法

```bash
# 单色常亮（全红）
python colorful_rgb.py solid 255 0 0

# 幻彩彩虹流光
python colorful_rgb.py rainbow

# 单色水波纹（蓝色）
python colorful_rgb.py flow 0 100 255

# 关闭灯光
python colorful_rgb.py off

# 指定设备节点（udev 未配置时使用）
python colorful_rgb.py --device /dev/hidraw10 solid 255 0 0

# 不加参数默认启动彩虹流光
python colorful_rgb.py
```

### 开机自动设置颜色（systemd）

```ini
# /etc/systemd/system/colorful-rgb.service
[Unit]
Description=七彩虹主板 RGB 初始化
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python /path/to/colorful_rgb.py solid 0 100 255
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now colorful-rgb
```

---

## 免责声明

- 本项目通过逆向工程分析 USB HID 通信协议实现，**与七彩虹官方无任何关联**。
- 本项目**仅供学习和个人使用**，不得用于任何商业目的。
- 直接写入硬件设备存在一定风险，**使用本项目造成的任何硬件损坏、数据丢失或其他问题，作者不承担任何责任**，请自行评估风险后使用。
- 本项目的核心代码由 **AI（Claude，Anthropic）辅助生成**，协议逆向分析、测试验证及项目整合由作者 ElmThree (Charlie) 完成。

---

## 许可证

本项目基于 [GNU General Public License v3.0](LICENSE) 开源。

你可以自由使用、修改和分发本项目，但修改后的版本必须同样以 GPL-3.0 协议开源。

---

## 致谢

- 协议逆向参考：[OpenRGB](https://gitlab.com/CalcProgrammer1/OpenRGB) 社区的逆向工程方法论
- AI 辅助：[Claude](https://claude.ai)（Anthropic）
