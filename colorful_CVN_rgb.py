#!/usr/bin/env python3
"""
项目名称: Colorful CVN Motherboard RGB Light Engine
项目作者: ElmThree (Charlie)
许可证: GNU General Public License v3.0 (GPL-3.0)

底层协议说明: 本脚本通过原生 HID 报告数据包，直写七彩虹主板底层 LED 控制芯片。
主要功能:
- build_packets: 核心协议层，组装满足七彩虹主板固件握手要求的 HID 字节报告。
- generate_monochromatic_flow: 高反差单色水波纹动画算法。
- generate_rainbow_flow: 高饱和度 HSV 幻彩彩虹滚动算法。
"""

import argparse
import sys
import time
#import json
import math
import colorsys
#import threading

# ── 1. 基础硬件参数配置 ─────────────────────────────────────
DEVICE         = "/dev/colorful-rgb"  # 底层 HID 硬件挂载设备路径

# ── 2. 底层 HID 数据包组装与协议封装 ──────────────────────────
FRAMES         = 10                   # 总控制帧数（分包发送）
LEDS_PER_FRAME = 20                   # 每一帧包涵的灯珠数
TOTAL_LEDS     = FRAMES * LEDS_PER_FRAME  # 全车总灯珠数 (200颗)

def build_packets(leds: list[tuple[int, int, int]]) -> list[bytes]:
    """
    将 200 颗灯珠的 RGB 颜色列表打碎并封装成七彩虹主板专属的 HID 报告格式包
    报告格式：[0x01, 0x00, 0x88, 序列号(0-9/FF), 60字节RGB数据]
    """
    # 填充或裁剪列表，确保数据长度严格等于 TOTAL_LEDS
    padded = (leds + [(0, 0, 0)] * TOTAL_LEDS)[:TOTAL_LEDS]
    # 展平 RGB 元组为标准字节流
    flat = bytes([ch for r, g, b in padded for ch in (r, g, b)])
    
    packets = []
    # 拆分成 10 个数据子包，每个包装载 20 颗灯珠(60字节)
    for seq in range(FRAMES):
        packets.append(bytes([0x01, 0x00, 0x88, seq]) + flat[seq * 60:(seq + 1) * 60])
    # 附加第 11 个结束尾包，通知芯片刷新硬件显示
    packets.append(bytes([0x01, 0x00, 0x88, 0xFF]) + bytes(60))
    return packets


def send_colors(leds: list[tuple[int, int, int]], device: str = DEVICE):
    """
    【静态一次性写入函数】适合常亮(solid)或灭灯(off)等静态指令
    """
    packets = build_packets(leds)
    try:
        with open(device, "wb") as f:
            for p in packets:
                f.write(p)
    except IOError as e:
        print(f"❌ 硬件设备写入失败 ({device}): {e}", file=sys.stderr)


# ── 3. 核心动态数学灯效发生器 ─────────────────────────────────

def generate_monochromatic_flow(time_tick: float, color: tuple[int, int, int], total_leds: int = 200, wave_length: int = 8, speed: float = 10.0, reverse: bool = False) -> list[tuple[int, int, int]]:
    """
    波纹流光发生器（基于正弦波与幂次衰减）
    """
    frame = []
    offset = -time_tick * speed if reverse else time_tick * speed

    for i in range(total_leds):
        # 空间相位 + 时间偏移 组合形成滚动波形
        angle = (i / wave_length) * 2.0 * math.pi - offset
        # 将正弦区间 [-1, 1] 归一化映射至亮度区间 [0, 1]
        base_brightness = (math.sin(angle) + 1.0) / 2.0
        # 2次幂运算扩充黑场，大幅强化流光的明暗反差质感
        brightness = math.pow(base_brightness, 2)
        
        r = max(0, min(255, int(color[0] * brightness)))
        g = max(0, min(255, int(color[1] * brightness)))
        b = max(0, min(255, int(color[2] * brightness)))
        frame.append((r, g, b))
        
    return frame

def generate_rainbow_flow(time_tick: float, total_leds: int = 200, wave_length: int = 40, speed: float = 2.0, reverse: bool = False) -> list[tuple[int, int, int]]:
    """
    彩虹桥滚动发生器（基于 HSV 色彩空间变换）
    """
    frame = []
    time_offset = -time_tick * speed if reverse else time_tick * speed
        
    for i in range(total_leds):
        # 计算当前灯珠在色相环(Hue Circle)上的 0.0 ~ 1.0 切片位置
        hue = ((i / wave_length) - time_offset) % 1.0
        # 饱满度(S)与亮度(V)拉满，转换出超高饱和度 RGB 字节
        r_f, g_f, b_f = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        
        frame.append((int(r_f * 255), int(g_f * 255), int(b_f * 255)))
        
    return frame

def cmd_rainbow(args):
    """【彩虹动态命令】"""
    print("🌈 启动幻彩彩虹滚动模式 (按 Ctrl+C 退出)...")
    last_frame = None
    try:
        with open(args.device, "wb") as f:
            while True:
                current_time = time.perf_counter()
                frame = generate_rainbow_flow(
                    time_tick=current_time,
                    total_leds=TOTAL_LEDS,
                    wave_length=50,
                    speed=0.5,
                    reverse=True
                )
                if frame != last_frame:
                    for pkt in build_packets(frame): f.write(pkt)
                    f.flush()
                    last_frame = frame
                time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n[+] 已安全退出彩虹灯效模式。")

def cmd_flow(args):
    """【流光动态命令】"""
    print(f"🌊 启动单色流光效果，颜色: ({args.r}, {args.g}, {args.b}) (按 Ctrl+C 退出)...")
    last_frame = None
    try:
        with open(args.device, "wb") as f:
            while True:
                current_time = time.perf_counter()
                frame = generate_monochromatic_flow(
                    total_leds=TOTAL_LEDS,
                    time_tick=current_time,
                    color=(args.r, args.g, args.b),
                    wave_length=10,
                    speed=5.0,
                    reverse=True
                )
                if frame != last_frame:
                    for pkt in build_packets(frame): f.write(pkt)
                    f.flush()
                    last_frame = frame
                time.sleep(0.03)
    except KeyboardInterrupt:
        print("\n[+] 已安全退出流光灯效模式。")

def cmd_solid(args): send_colors([(args.r, args.g, args.b)] * TOTAL_LEDS, args.device),print("[+] 静态灯光启动")
def cmd_off(args): send_colors([(0, 0, 0)] * TOTAL_LEDS, args.device),print("[+] 灯光关闭")
# ── 4. 脚本主入口与自动化默认分发 ──────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="七彩虹CVN主板灯光控制")
    parser.add_argument("--device", default=DEVICE, help="指定主板 RGB 控制设备节点路径")
    sub = parser.add_subparsers(dest="cmd")
    
    # 注册 solid 静态常亮命令
    p = sub.add_parser("solid", help="灯光纯色常亮")
    p.add_argument("r", type=int); p.add_argument("g", type=int); p.add_argument("b", type=int)
    
    # 注册 rainbow 动态彩虹流光命令
    p = sub.add_parser("rainbow", help="彩虹流光")
    
    # 注册 flow 单色水波流光命令
    p = sub.add_parser("flow", help="单色水波纹")
    p.add_argument("r", type=int); p.add_argument("g", type=int); p.add_argument("b", type=int)
    
    # 注册 off 灯光熄灭命令
    sub.add_parser("off", help="熄灭灯光")
    
    args = parser.parse_args()
    
    # 映射路由字典
    dispatch = {
        "solid": cmd_solid, 
        "off": cmd_off,
        "rainbow": cmd_rainbow,
        "flow": cmd_flow
    }
    
    # 默认彩虹流光
    if args.cmd is None:
        print("[*] 未检测到显式指令，默认自动启动幻彩彩虹流光模式...")
        args.cmd = "rainbow"
        
    # 执行业务分发
    if args.cmd in dispatch: 
        dispatch[args.cmd](args)