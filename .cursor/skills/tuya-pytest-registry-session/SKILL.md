---
name: tuya-pytest-registry-session
description: >-
  Maintain the TuyaRobot pytest session, connection configuration, subsystem
  fixtures, collection markers, and hardware safety gates in conftest.py,
  settings.py, and pytest.ini. Use when changing TuyaRobot IP or serial options,
  environment variables, device lifecycle, robot/upper_body/arm/head/chassis
  fixtures, hardware selection, or --run-* execution controls.
---

# TuyaRobot pytest 会话与连接

## 按职责定位修改

- `settings.py`：定义 `TuyaConnectionConfig`、环境变量解析、三个 Excel 路径和 `TuyaRobotBase` 设备封装。
- 根 `conftest.py`：定义 pytest CLI、合并 CLI/环境配置、创建 session 设备、暴露子系统 fixture、执行安全门控。
- `pytest.ini`：定义测试根目录、导入模式和 marker 注册。
- 测试文件：只消费 fixture，不创建 `TuyaRobot`、不关闭共享连接。

仓库没有 `arms.json`、`arm_registry.py` 或按 arm id 选臂的流程；不要引入旧仓库的 registry 模式。

## 连接配置优先级

`_connection_config()` 先读取 `TuyaConnectionConfig.from_env()`，再用显式 CLI 覆盖对应字段：

| 子系统 | CLI | 环境变量 | 默认值 |
|---|---|---|---|
| 上半身 | `--tuya-ip` / `--tuya-port` | `TUYA_ROBOT_IP` / `TUYA_ROBOT_PORT` | `192.168.0.232:6500` |
| 头部 | `--head-ip` / `--head-port` / `--connect-head` | `TUYA_HEAD_IP` / `TUYA_HEAD_PORT` / `TUYA_HEAD_AUTO_CONNECT` | `192.168.0.231 / 6501 / false` |
| 底盘 | `--chassis-port` / `--chassis-baud` / `--no-connect-chassis` | `TUYA_CHASSIS_PORT` / `TUYA_CHASSIS_BAUD` / `TUYA_CHASSIS_AUTO_CONNECT` | `COM16 / 2000000 / true` |

其余环境变量为 `TUYA_APPLY_LIMITS_ON_INIT`、`TUYA_DEBUG`、`TUYA_PLAIN_RETURN`。布尔值接受 `1/true/yes/on`；非法整数回退默认值。

保持当前覆盖语义：CLI 只覆盖明确提供的值；`--connect-head` 可启用头部，`--no-connect-chassis` 可强制禁用底盘。

## 设备生命周期与 fixture

- `device` 为 session scope，只构造一次 `TuyaRobotBase`，会话结束调用一次 `dev.close()`。
- `robot`、`upper_body`、`left_arm`、`right_arm` 直接返回 `device` 上的对应对象。
- `head` 在 `device.head.enabled` 为假时跳过；`testcases/head/conftest.py` 会覆盖它，以 `Head` 建立不依赖整机的独立 TCP 连接。
- `chassis` 在 `device.chassis.enabled` 为假时跳过。
- `testcases/upper_body/conftest.py` 定义 function 级自动 fixture：每条上半身测试前读取双臂上电状态，仅在状态不是 `[1, 1]` 时调用 `upper_power_on()`，并在 30 秒内轮询确认；复用根 `device`，不得新建或关闭连接。上半身测试文件不得重复检查上电状态。
- 除上述上半身公共前置上电外，不把接口专属校准、参数初始化或恢复时机加入 session fixture；可复用的整臂回零和设置参数后的默认恢复动作封装为 `TuyaRobotBase` 方法，由对应测试文件或 function 级 fixture 调用。

`TuyaRobotBase` 必须继续集中暴露 `robot`、`upper_body`、`left_arm`、`right_arm`、`head`、`chassis`。左臂、右臂和整臂接口通过公共 `result_data()` 统一兼容 `CommandResult` 与 plain return；上半身运动等待使用有超时的 `wait_upper()`。

## 收集与安全门控

collection 阶段自动给 `testcases/` 下项目添加 `hardware`。以下 marker 默认跳过，必须由 CLI 或环境变量显式启用：

| marker | CLI | 环境变量 |
|---|---|---|
| `hardware` | `--run-hardware` | `RUN_TUYA_HARDWARE` |
| `motion` | `--run-motion` | `RUN_TUYA_MOTION` |
| `manual` | `--run-manual` | `RUN_TUYA_MANUAL` |
| `danger` | `--run-danger` | `RUN_TUYA_DANGER` |
| `firmware` | `--run-firmware` | `RUN_TUYA_FIRMWARE` |

多个 marker 同时存在时必须分别启用。例如 `hardware + motion + danger` 需要三个门控都开启。`reset` 仅描述用例会恢复状态，不是执行门控。

## 修改规则

- 新增连接字段时同步更新 dataclass 默认值、`from_env()`、pytest CLI 和 `_connection_config()` 合并逻辑。
- 新增 fixture 时从 session `device` 派生；需要可选连接的子系统先检查 `enabled` 并给出明确 skip 原因。
- 新增安全 marker 时同步更新 `pytest.ini`、CLI、环境变量判断和 collection gate。
- 不在配置中打印凭据或敏感连接数据；本仓库当前只有局域网 IP 和串口参数。

## 验证

1. `pytest --help`：确认全部 TuyaRobot CLI 仍可见。
2. `pytest testcases --collect-only -q`：确认无需连接硬件即可收集，当前基线为 824 条。
3. 修改配置解析时，为 CLI 覆盖、环境变量回退和布尔/整数解析补充或运行针对性测试。
4. 不在普通验证中传 `--run-hardware`；只有用户明确要求真机执行时才开启对应门控。
