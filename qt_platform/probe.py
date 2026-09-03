# -*- coding: utf-8 -*-
"""在独立进程中探测 TuyaRobot 连接。"""
from __future__ import annotations

import argparse

from settings import TuyaConnectionConfig, TuyaRobotBase


def main() -> None:
    defaults = TuyaConnectionConfig.from_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default=defaults.upper_ip)
    parser.add_argument("--port", type=int, default=defaults.upper_port)
    parser.add_argument("--head-ip", default=defaults.head_ip)
    parser.add_argument("--head-port", type=int, default=defaults.head_port)
    parser.add_argument("--chassis-port", default=defaults.chassis_port)
    parser.add_argument("--chassis-baud", type=int, default=defaults.chassis_baud)
    parser.add_argument("--connect-head", action="store_true")
    parser.add_argument(
        "--no-connect-chassis",
        action="store_true",
        help="不连接底盘串口",
    )
    args = parser.parse_args()

    config = TuyaConnectionConfig(
        upper_ip=args.ip,
        upper_port=args.port,
        head_ip=args.head_ip,
        head_port=args.head_port,
        chassis_port=args.chassis_port,
        chassis_baud=args.chassis_baud,
        head_auto_connect=args.connect_head,
        chassis_auto_connect=not args.no_connect_chassis,
        apply_limits_on_init=False,
        debug=True,
        plain_return=True,
    )
    device = TuyaRobotBase(config)
    try:
        robot_type = device.robot.get_robot_type()
        version = device.robot.get_system_version()
        print(f"上半身: robot_type={robot_type!r} version={version!r}")

        head_ok = bool(getattr(device.head, "enabled", False))
        print(
            f"头部 TCP: enabled={head_ok} "
            f"ip={args.head_ip!r} port={args.head_port}"
        )

        chassis_ok = bool(getattr(device.chassis, "enabled", False))
        print(
            f"底盘串口: enabled={chassis_ok} port={args.chassis_port!r} "
            f"baud={args.chassis_baud}"
        )
        if not chassis_ok:
            print("底盘未连接：请检查串口号，并确认未传 --no-connect-chassis。")
        else:
            try:
                chassis_ver = device.chassis.get_agv_main_version()
                print(f"底盘主版本: {chassis_ver!r}")
            except Exception as exc:  # noqa: BLE001 — 探测仅打印，不掩盖主流程
                print(f"底盘主版本读取失败: {exc!r}")

        if head_ok or chassis_ok or robot_type is not None:
            print("OK")
        else:
            print("FAIL: 未能确认任何子系统连接")
    finally:
        device.close()


if __name__ == "__main__":
    main()
