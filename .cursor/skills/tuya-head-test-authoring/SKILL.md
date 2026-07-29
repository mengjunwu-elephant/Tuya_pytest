---
name: tuya-head-test-authoring
description: >-
  Author TCP-based Tuya PI4 head v1.0 pytest cases, Excel parameters, safety
  gates, four-joint contract checks, restoration paths, and operator prompts.
---

# Tuya 头部 PI4 v1.0 用例编写

## 连接与数据

- 头部测试位于 `testcases/head/`，数据位于 `test_data/head.xlsx`；使用该目录的独立 `head` fixture，不依赖整机或串口。
- TCP 参数为 `--head-ip`、`--head-port`，环境变量为 `TUYA_HEAD_IP`、`TUYA_HEAD_PORT`，默认 `192.168.0.231:6501`；必须显式启用 `--connect-head`。
- 每个接口使用同名 sheet 和同名 `test_<api>.py` 测试文件；急停等跨接口安全场景使用单独专项文件，不得将多个接口聚合到通用分发测试中。首行至少包含 `ID`、`title`、`api`、`test_type`、输入参数、`expect_data`、`expect_kind`、恢复参数、`timeout`、`tolerance`。

## 优先级与方法

- P1：上/下电、使能、校准、角度、单/四关节运动、状态、错误、清错、碰撞阈值、急停。
- P2：运行速度、电流、温度、LED、屏幕动画。P3：版本、Debug、固件升级非法参数。
- 使用等价类、边界、场景、状态迁移、错误推断和接口一致性；不实现通信中断、100 次稳定性或真实固件升级。
- 四关节返回、J3/J4 运动和错误状态必须断言 4 项；旧 SDK 仅支持 2 关节时使用明确 `xfail`，不得报成设备故障。

## 安全与恢复

- 所有实机用例受 `hardware` 门控；运动为 `motion + manual`，校准、急停、使能、上/下电、碰撞阈值为 `danger`，固件参数校验为 `firmware`。
- 动作前后用 `prompt_continue` 弹窗确认。急停由人工按下/松开，不自动操作。
- 能读原值的 setter 必须 `try/finally` 读回恢复；使能与 LED 无读取接口时，Excel 必须提供恢复参数，否则跳过。校准不自动恢复，只能人工授权。
- 运动只能使用已现场确认的安全姿态和低速；等待运动停止必须有超时，结束后恢复初始角度。
