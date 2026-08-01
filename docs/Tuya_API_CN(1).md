# Tuya Robot 上半身双臂 Python API 中文说明

[toc]

## 使用前提

在使用上半身双臂 API 之前，请先确认以下条件：

- 机器人上半身控制器已正确上电，并且处于可通信状态。
- PC 与机器人上半身控制器处于同一网段。
- 默认上半身 TCP 端口为 `6500`。如果设备端配置不同，请以实际端口为准。
- 已安装 Python 3.9 或更高版本。
- 调试真机运动接口前，请确认急停、限位、工作空间和周围环境安全。
- 运动类接口可能会立即驱动双臂动作。首次验证建议使用低速、小幅度目标；未传 `_async` 时使用全局到位反馈默认策略。

常用网络检查：

```bash
ping 192.168.0.232
```

## 安装库

正式交付时通常提供 `.whl` 安装包，直接使用 `pip install` 安装即可：

```bash
python -m pip install pytuyarobot-版本号-py3-none-any.whl
```

如果需要覆盖安装已有版本，可以使用：

```bash
python -m pip install --force-reinstall pytuyarobot-版本号-py3-none-any.whl
```

如果安装包在当前目录，也可以写成：

```bash
python -m pip install .\pytuyarobot-版本号-py3-none-any.whl
```

仅在开发源码时才需要使用源码目录安装或开发模式安装：

```bash
cd D:\Tuya定制项目\pytuyarobot
python -m pip install -e .
```

安装后验证导入：

```python
from pytuyarobot import TuyaRobot

print(TuyaRobot)
```

## 导入与实例化

最常用的入口类是 `TuyaRobot`。上半身双臂接口直接通过 `robot` 调用；单臂接口可通过 `robot.left_arm` 和 `robot.right_arm` 调用。

```python
from pytuyarobot import TuyaRobot

robot = TuyaRobot(
    "192.168.1.232",
    6500,
    head_auto_connect=False,
    chassis_auto_connect=False,
    apply_limits_on_init=False,
)

# 上电
print(robot.upper_power_on())

print(robot.get_upper_angles())

robot.close()
```

### 构造参数

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `upper_ip` | `str` | 上半身控制器 IP。 |
| `upper_port` | `int` | 上半身 TCP 端口，默认 `6500`。 |
| `head_ip` / `head_port` | `str` / `int` | 头部 TCP socket 配置，默认 `192.168.0.231:6501`。只调上半身时可通过 `head_auto_connect=False` 跳过。 |
| `chassis_port` / `chassis_baud` | `str` / `int` | 底盘串口配置。只调上半身时可通过 `chassis_auto_connect=False` 跳过。 |
| `head_auto_connect` | `bool` | 是否初始化时自动连接头部 TCP socket。 |
| `chassis_auto_connect` | `bool` | 是否初始化时自动连接底盘串口。 |
| `apply_limits_on_init` | `bool` | 初始化时是否下发本地保存的软件限位。调试时可设为 `False`。 |
| `debug` | `bool` | 是否输出详细通信日志，包括 `_write` / `_read` 十六进制帧。 |
| `plain_return` | `bool` | `False` 时返回 `CommandResult`；`True` 时成功直接返回解析后的 `data`。 |

## 返回值约定

默认 `plain_return=False`，接口返回 `CommandResult`：

| 字段 | 说明 |
| --- | --- |
| `ok` | `True` 表示通信和协议处理成功；`False` 表示失败。 |
| `data` | 协议 payload 解析后的业务值，如 `int`、`list`、`dict`。 |
| `status_code` | 失败时的状态码或错误码。 |
| `message` | 可读错误信息。 |
| `raw` | 当前公开 `CommandResult` 不固定暴露该字段；需要原始帧时请使用 `debug=True` 查看 `_write` / `_read` 日志。 |
| `blocked_by` | SDK 安全策略阻断来源；触发组合保护时为实际故障模块的 `ModuleId`。 |

示例：

```python
result = robot.get_upper_angles()
if result.ok:
    print(result.data)
else:
    print(result.status_code, result.message)
```

如果实例化时设置 `plain_return=True`，成功时直接返回解析值，失败时仍返回 `CommandResult`：

```python
robot = TuyaRobot(
    "192.168.1.232",
    6500,
    head_auto_connect=False,
    chassis_auto_connect=False,
    plain_return=True,
)

angles = robot.get_upper_angles()
print(angles)
```

## 双臂与单臂调用约定

双臂总接口通常返回：

- `[left, right]`：左右臂各一个标量状态。
- `{"left": ..., "right": ...}`：左右臂各一组结构化数据。
- 运动类接口成功时常见返回 `0` 或 ACK 字节，具体以 `data` 为准。

单臂接口：

```python
robot.left_arm.get_upper_angles()
robot.right_arm.get_upper_angles()
robot.left_arm.send_upper_angles([0, 0, 0, 0, 0, 0, 0, 0], 20, 0)
```

单臂接口会把双臂结果筛选为当前手臂的数据。例如双臂 `is_upper_powered_on()` 返回 `[1, 1]`，单臂 `robot.left_arm.is_upper_powered_on()` 返回 `1`。
读取类接口请求帧通常不带 `arm_type`；单臂对象只是 SDK 侧从固件返回的左右数据中筛选当前手臂。

## 上电状态门禁

`TuyaRobot` / `UpperBody` 初始化后会尝试读取一次 `is_upper_powered_on()` 并缓存左右臂上电状态。电机相关读取、配置和运动接口会先检查缓存，避免未上电时继续下发指令并等待超时。

- 总接口（例如 `robot.get_upper_angles()`、`robot.send_upper_angles(...)`）要求左右臂都为上电状态；任一侧未上电都会直接返回 `CommandResult(ok=False, message=...)`。
- 单臂接口（例如 `robot.left_arm.get_upper_angles()`）只检查当前手臂状态。
- 未上电时仍允许读版本、上电、下电、读取 `robot_status`、读取 `is_upper_powered_on()`、主控固件升级和调试状态等与电机无关的接口。
- `is_upper_powered_on()`、`upper_power_on()`、`upper_power_off()` 成功后会更新缓存。

```python
power = robot.is_upper_powered_on()
if power.ok and power.data != [1, 1]:
    robot.upper_power_on()
```

## 参数范围速查

SDK 会在发送指令前做参数校验，常用范围如下：

| 参数 | 范围 | 说明 |
| --- | --- | --- |
| `angles` | 长度 8 | J1~J7 为关节角，J8 通常为夹爪开合量。 |
| J1~J7 角度 | J1 `-166.0 ~ 166.0`，J2 `-80.0 ~ 105.0`，J3 `-166.0 ~ 166.0`，J4 `-170.0 ~ 10.0`，J5 `-166.0 ~ 166.0`，J6 `-100.0 ~ 100.0`，J7 `-100.0 ~ 100.0` | 单位为度。 |
| J8 夹爪 | `0.0 ~ 125.0` | 夹爪开合量，按协议定义解释。 |
| `coords` | 长度 6 | `[x, y, z, rx, ry, rz]`。 |
| `x/y/z` | X `-650.0 ~ 650.0`，Y `-841.0 ~ 841.0`，Z `-636.0 ~ 665.0` | 位置坐标，单位按协议/固件定义，通常为 mm。 |
| `rx/ry/rz` | `-180.0 ~ 180.0` | 姿态角，单位按协议/固件定义，通常为度。 |
| `speed` / `arm_speed` | `1 ~ 100` | 运动速度。 |
| `gripper_speed` | `0` 或 `1 ~ 100` | `0` 表示夹爪不动作。 |
| `plan speed` | 角度模式 `1 ~ 150`，坐标模式 `1 ~ 200` | `set_upper_plan_sp(mode, speed)` 使用，`mode=0` 为角度规划，`mode=1` 为坐标规划。 |
| `plan acc` | 角度模式 `1 ~ 200`，坐标模式 `1 ~ 400` | `set_upper_plan_acc(mode, acc)` 使用。 |
| `joint acc` | `0.001 ~ 0.1` | `set_upper_joint_acc(joint_id, acc)` 使用，`joint_id` 为 `1 ~ 7`，协议下发值为 `acc * 1000`。 |
| `joint_id` | `1 ~ 8` | J8 通常对应夹爪；部分配置接口支持 `254` 表示全部关节。 |
| `coord_id` | `1 ~ 6` | 依次对应 `x, y, z, rx, ry, rz`。 |
| `direction` | `0` 或 `1` | 点动方向。 |
| `mode` | 按接口定义 | `fresh_mode` 为 `0/1`；`get_upper_is_in_position` 为 `0` 角度、`1` 坐标。 |
| `debug state` | `0 ~ 4` | 上半身调试状态。 |
| `robot safety level` | `0`、`1 ~ 6` 或组合列表 | SDK 整机安全模式；`0` 为默认独立模式，列表用于组合保护。 |
| `base_type` | `0` 或 `1` | `0` base，`1` world。 |
| `movement_type` | `0 ~ 4` | 运动类型。 |
| `end_type` | `0` 或 `1` | `0` tool，`1` world。 |
| 碰撞 `param_type` | `1` 或 `2` | `1` 为模式，`2` 为阈值。 |
| 碰撞 `data` / `threshold` | `0 ~ 255` | 单字节参数。 |
| `increment` | `int` 或 `float` | 增量值按对应关节或坐标轴完整跨度校验，不允许 `bool`。 |

## 版本、调试与模式

### `get_upper_main_version()`

- **功能**：读取上半身主版本号。
- **参数**：无。
- **返回值**：`float`，例如 `1.0`。

```python
print(robot.get_upper_main_version())
```

### `get_upper_modify_version()`

- **功能**：读取上半身修正版本号。
- **参数**：无。
- **返回值**：`float`。

```python
print(robot.get_upper_modify_version())
```

### `get_system_version()`

- **功能**：兼容接口，等价于读取上半身主版本号。
- **参数**：无。
- **返回值**：`float`。

```python
print(robot.get_system_version())
```

### `upper_firmware_flash(firmware_path, *, restart_mode="watchdog")`

- **功能**：升级 RK3562 上的上半身主控程序 `TuyaBody`。
- **参数**：
  - `firmware_path`：本地待升级固件文件路径，例如 `./TuyaBody` 或 `./TuyaBody_V2.0.1`；本地文件名可带版本号。
  - `restart_mode`：升级后启动方式，默认 `"watchdog"`；调试阶段可传 `"direct"` 直接启动 `TuyaBody`。
- **固定连接信息**：
  - RK 地址：`192.168.0.232`
  - SSH 用户名/密码：`root` / `root`
  - 远端固件路径：`/root/Tuya/bin/TuyaBody`
  - 远端看门狗脚本：`/root/Tuya/bin/tuya_body_watchdog.sh`
- **执行流程**：
  1. SSH 登录 RK3562。
  2. 停止看门狗脚本，避免旧程序被立即拉起。
  3. 停止当前 `TuyaBody` 进程。
  4. 上传固件到 `/root/Tuya/bin/TuyaBody.new`。
  5. 备份旧固件为 `/root/Tuya/bin/TuyaBody.bak`。
  6. 替换 `/root/Tuya/bin/TuyaBody` 并执行 `chmod +x`。
  7. 按 `restart_mode` 重启：`"watchdog"` 启动看门狗脚本，`"direct"` 直接启动 `TuyaBody`。
  8. 尝试读取主版本号。
- **协议说明**：升级流程不再发送 `0x20` 准备指令，避免旧主控固件不回复 ACK 时导致升级失败。
- **文件名说明**：上传时会使用本地文件内容，但 RK 端最终固定替换为 `/root/Tuya/bin/TuyaBody`，确保看门狗和直接启动模式都能找到主程序。
- **白名单说明**：本地文件名只允许 `TuyaBody` 或 `TuyaBody_V*`；文件 MD5 必须在 `pytuyarobot/config/upper_firmware_md5_allowlist.json` 中，避免误传未批准主控程序。
- **返回值**：成功时返回升级后从主控读到的主版本字符串；默认模式为 `CommandResult(ok=True, data="2.0")`，`plain_return=True` 时直接返回 `"2.0"`。
- **失败语义**：本地文件名非法、文件不存在、空文件、MD5 未批准、SSH/SFTP 失败、远端命令失败，或升级后无法读取版本，都会返回 `CommandResult(ok=False, message=...)`；替换失败且存在备份时会尝试恢复旧固件并重启看门狗。

```python
result = robot.upper_firmware_flash("./TuyaBody")
print(result)

# 调试阶段如需升级后直接启动 TuyaBody：
robot.upper_firmware_flash("./TuyaBody", restart_mode="direct")
```

### `get_upper_debug_state()`

- **功能**：读取上半身调试日志模式。
- **参数**：无。
- **返回值**：`int`。

```python
print(robot.get_upper_debug_state())
```

### `set_upper_debug_state(state)`

- **功能**：设置上半身调试日志模式。
- **参数**：
  - `state`：`int`，范围由 SDK 校验，当前为 `0 ~ 4`。
- **返回值**：ACK 解析值，成功通常为 `1`。

```python
robot.set_upper_debug_state(1)
```

### `get_upper_fresh_mode()`

- **功能**：读取左右臂运动刷新模式。
- **参数**：无。
- **返回值**：`[left_mode, right_mode]`。
  - `0`：插补模式。
  - `1`：刷新模式。

```python
print(robot.get_upper_fresh_mode())
```

### `set_upper_fresh_mode(mode)`

- **功能**：设置双臂运动刷新模式。
- **参数**：
  - `mode`：`0` 或 `1`。
- **返回值**：ACK 解析值。
- **联动行为**：双臂总入口设置成功后会自动同步 SDK 全局运动默认值：`mode=1` 时等价于 `set_upper_motion_async(True)`，`mode=0` 时等价于 `set_upper_motion_async(False)`。单臂对象设置刷新模式时不会修改全局默认值。

```python
robot.set_upper_fresh_mode(1)
```

### `set_upper_motion_async(enabled)` / `get_upper_motion_async()`

- **功能**：设置或读取 SDK 运动接口的全局开环默认值。该接口不下发固件指令，只影响未显式传 `_async` 的运动调用。
- **参数**：
  - `enabled`：支持 `True` / `False` / `1` / `0`。`True` 或 `1` 表示运动接口默认只等待第一层 ACK；`False` 或 `0` 表示默认继续等待 `0x5B/0x5C` 到位反馈。
- **返回值**：`bool`。
- **刷新模式说明**：`fresh_mode=1` 时固件没有 `0x5B/0x5C` 到位反馈。如果未开启全局开环，SDK 会在运动前读取 `get_upper_fresh_mode()`，发现刷新模式后直接返回提示，不下发运动指令，避免等待 300 秒；提示语言会按当前系统语言在中文/英文之间切换。
```python
robot.set_upper_motion_async(True)
print(robot.get_upper_motion_async())

# 也可以只对本次调用关闭到位反馈等待
robot.send_upper_angles(left, 20, 0, right, 20, 0, _async=True)
```

## 电源、启停与状态

### `upper_power_on()`

- **功能**：上半身双臂上电。
- **参数**：无。
- **返回值**：`[left, right]`。
  - `1`：上电。
  - `0`：未上电。
  - `2`：协议原始状态，SDK 不映射为急停异常。

```python
print(robot.upper_power_on())
```

单臂调用：

```python
print(robot.left_arm.upper_power_on())
```

### `upper_power_off()`

- **功能**：上半身下电。
- **参数**：无；整机入口默认左右臂一起下电。
- **返回值**：ACK 解析值，成功通常为 `1`。

```python
robot.upper_power_off()
robot.left_arm.upper_power_off()
robot.right_arm.upper_power_off()
```

### `is_upper_powered_on()`

- **功能**：查询双臂是否上电。
- **参数**：无。
- **返回值**：`[left, right]`，取值含义同 `upper_power_on()`。

```python
print(robot.is_upper_powered_on())
```

### `upper_pause()`

- **功能**：暂停上半身运动。
- **参数**：无。
- **返回值**：运动 ACK，成功通常表示指令已接收。

```python
robot.upper_pause()
```

### `upper_resume()`

- **功能**：恢复上半身运动。
- **参数**：无。
- **返回值**：运动 ACK。

```python
robot.upper_resume()
```

### `upper_stop()`

- **功能**：停止上半身运动。
- **参数**：无。
- **返回值**：运动 ACK。

```python
robot.upper_stop()
```

### `get_upper_is_moving()`

- **功能**：查询双臂是否正在运动。
- **参数**：无。
- **返回值**：`[left, right]`，每个值通常为 `0` 或 `1`。

```python
print(robot.get_upper_is_moving())
```

单臂调用返回当前臂的 `int`：

```python
print(robot.left_arm.get_upper_is_moving())
```

### `get_upper_is_paused()`

- **功能**：查询双臂是否处于暂停状态。
- **参数**：无。
- **返回值**：`[left, right]`，每个值通常为 `0` 或 `1`。

```python
print(robot.get_upper_is_paused())
```

### `get_upper_is_in_position(mode=0, left=None, right=None)`

- **功能**：查询目标是否到位。
- **参数**：
  - `mode`：`0` 表示按关节角目标查询；`1` 表示按坐标目标查询。
  - `left`：左臂目标。`mode=0` 时为 8 个关节角，J1 `-166.0 ~ 166.0`，J2 `-80.0 ~ 105.0`，J3 `-166.0 ~ 166.0`，J4 `-170.0 ~ 10.0`，J5 `-166.0 ~ 166.0`，J6 `-100.0 ~ 100.0`，J7 `-100.0 ~ 100.0`，J8 `0.0 ~ 125.0`；`mode=1` 时为 6 个坐标，X `-650.0 ~ 650.0`，Y `-841.0 ~ 841.0`，Z `-636.0 ~ 665.0`，`rx/ry/rz` 范围 `-180.0 ~ 180.0`。
  - `right`：右臂目标。格式和范围同 `left`。
- **返回值**：双臂到位状态。正常到位时通常为 `0`；异常时 `CommandResult.message` 会包含错误码说明。

```python
result = robot.get_upper_is_in_position(
    0,
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
)
print(result)
```

坐标模式：

```python
print(robot.get_upper_is_in_position(1, [0, 0, 300, 0, 0, 0], [0, 0, 300, 0, 0, 0]))
```

## 关节运动

### `get_upper_angles()`

- **功能**：读取左右臂当前关节角。
- **参数**：无。
- **返回值**：`{"left": [J1..J8], "right": [J1..J8]}`，单位为度。

```python
print(robot.get_upper_angles())
print(robot.left_arm.get_upper_angles())
```

### `send_upper_angles(left_angles, left_arm_speed, left_gripper_speed, right_angles, right_arm_speed, right_gripper_speed, _async=None)`

- **功能**：双臂关节角运动。
- **参数**：
  - `left_angles`：左臂 8 个关节角，J1 `-166.0 ~ 166.0`，J2 `-80.0 ~ 105.0`，J3 `-166.0 ~ 166.0`，J4 `-170.0 ~ 10.0`，J5 `-166.0 ~ 166.0`，J6 `-100.0 ~ 100.0`，J7 `-100.0 ~ 100.0`，J8 `0.0 ~ 125.0`。
  - `left_arm_speed`：左臂 J1~J7 运动速度，范围 `1 ~ 100`。
  - `left_gripper_speed`：左臂 J8 速度，`0` 表示夹爪不动作，非零范围 `1 ~ 100`。
  - `right_angles`：右臂 8 个关节角，范围同 `left_angles`。
  - `right_arm_speed`：右臂 J1~J7 运动速度，范围 `1 ~ 100`。
  - `right_gripper_speed`：右臂 J8 速度，`0` 表示夹爪不动作，非零范围 `1 ~ 100`。
  - `_async`：`False` 时等待到位反馈；`True` 时只等待指令 ACK。
- **返回值**：运动结果。同步模式到位成功时 `data` 通常为 `0`；失败时 `message` 包含错误说明。

```python
robot.send_upper_angles(
    [0, 0, 0, 0, 0, 0, 0, 0],
    20,
    0,
    [0, 0, 0, 0, 0, 0, 0, 0],
    20,
    0,
)
```

### `send_upper_angle(joint_id, angle, speed, _async=None)`

- **功能**：双臂同一关节运动到指定角度。
- **参数**：
  - `joint_id`：关节号 `1 ~ 8`。
  - `angle`：目标角度，按 `joint_id` 校验；J1 `-166.0 ~ 166.0`，J2 `-80.0 ~ 105.0`，J3 `-166.0 ~ 166.0`，J4 `-170.0 ~ 10.0`，J5 `-166.0 ~ 166.0`，J6 `-100.0 ~ 100.0`，J7 `-100.0 ~ 100.0`，J8 `0.0 ~ 125.0`。
  - `speed`：运动速度，范围 `1 ~ 100`。
  - `_async`：是否异步。
- **返回值**：运动结果。

```python
robot.send_upper_angle(1, 10.0, 20)
```

### `upper_jog_angle(joint_id, direction, speed, _async=None)`

- **功能**：双臂同一关节点动。
- **参数**：
  - `joint_id`：关节号 `1 ~ 8`。
  - `direction`：方向，`0` 或 `1`。
  - `speed`：点动速度，范围 `1 ~ 100`。
  - `_async`：是否异步；默认 `None` 时按开环处理，只等待指令反馈，不等待到位；显式传 `_async=False` 时才等待到位。JOG 在刷新模式下始终不可用。
- **返回值**：运动 ACK。
- **刷新模式限制**：`fresh_mode=1` 时会直接返回“刷新模式无法使用JOG运动，请切换插补模式使用。”，不会下发 JOG 指令。

```python
robot.upper_jog_angle(1, 1, 10)
```

### `upper_jog_angle_increment(joint_id, increment, speed, _async=None)`

- **功能**：双臂同一关节按角度增量步进。
- **参数**：
  - `joint_id`：关节号 `1 ~ 7`；J8 夹爪不支持该增量接口。
  - `increment`：增量角度，单位度，参数类型为 `int` 或 `float`，不允许 `bool`；范围按对应关节总跨度校验，即 `关节最大值 - 关节最小值` 的正负值。J1 `-332.0 ~ 332.0`，J2 `-185.0 ~ 185.0`，J3 `-332.0 ~ 332.0`，J4 `-180.0 ~ 180.0`，J5 `-332.0 ~ 332.0`，J6 `-200.0 ~ 200.0`，J7 `-200.0 ~ 200.0`。
  - `speed`：运动速度，范围 `1 ~ 100`。
  - `_async`：是否异步；JOG 增量在刷新模式下始终不可用。
- **返回值**：运动结果。
- **刷新模式限制**：`fresh_mode=1` 时不会下发 JOG 增量指令。
- **协议编码说明**：增量会按协议乘以 `100` 编码为 int16；如果物理范围内的增量换算后超过 `-32768 ~ 32767`，SDK 会按 Pro450 策略截断到 int16 边界后下发。

```python
robot.upper_jog_angle_increment(1, 5.0, 20)
```

## 坐标运动

坐标列表统一为 `[x, y, z, rx, ry, rz]`。X `-650.0 ~ 650.0`，Y `-841.0 ~ 841.0`，Z `-636.0 ~ 665.0`，`rx/ry/rz` 范围为 `-180.0 ~ 180.0`；位置单位和姿态单位以协议和固件定义为准。

### `get_upper_coords()` / `get_coords()`

- **功能**：读取左右臂当前末端坐标。
- **参数**：无。
- **返回值**：`{"left": [x, y, z, rx, ry, rz], "right": [x, y, z, rx, ry, rz]}`。

```python
print(robot.get_upper_coords())
print(robot.get_coords())
```

### `send_upper_coords(left_coords, left_speed, right_coords, right_speed, _async=None)`

- **功能**：双臂坐标运动。
- **参数**：
  - `left_coords`：左臂 6 个坐标，X `-650.0 ~ 650.0`，Y `-841.0 ~ 841.0`，Z `-636.0 ~ 665.0`，`rx/ry/rz` 范围 `-180.0 ~ 180.0`。
  - `left_speed`：左臂速度，范围 `1 ~ 100`。
  - `right_coords`：右臂 6 个坐标，范围同 `left_coords`。
  - `right_speed`：右臂速度，范围 `1 ~ 100`。
  - `_async`：是否异步。
- **返回值**：运动结果。

```python
robot.send_upper_coords(
    [0, 0, 300, 0, 0, 0],
    20,
    [0, 0, 300, 0, 0, 0],
    20,
)
```

### `write_upper_coords(...)`

- **功能**：`send_upper_coords(...)` 的同义接口。
- **参数**：同 `send_upper_coords(...)`。
- **返回值**：同 `send_upper_coords(...)`。

```python
robot.write_upper_coords([0, 0, 300, 0, 0, 0], 20, [0, 0, 300, 0, 0, 0], 20)
```

### `send_upper_coord(coord_id, value, speed, _async=None)`

- **功能**：双臂同一坐标轴运动到指定值。
- **参数**：
  - `coord_id`：坐标轴编号 `1 ~ 6`，对应 `x, y, z, rx, ry, rz`。
  - `value`：目标值；`coord_id=1` X 范围 `-650.0 ~ 650.0`，`coord_id=2` Y 范围 `-841.0 ~ 841.0`，`coord_id=3` Z 范围 `-636.0 ~ 665.0`，`coord_id=4~6` 时范围 `-180.0 ~ 180.0`。
  - `speed`：运动速度，范围 `1 ~ 100`。
  - `_async`：是否异步。
- **返回值**：运动结果。

```python
robot.send_upper_coord(3, 300, 20)
```

### `write_upper_coord(...)`

- **功能**：`send_upper_coord(...)` 的同义接口。
- **参数**：同 `send_upper_coord(...)`。
- **返回值**：同 `send_upper_coord(...)`。

```python
robot.write_upper_coord(3, 300, 20)
```

### `upper_jog_coord(coord_id, direction, speed, _async=None)`

- **功能**：双臂同一坐标轴点动。
- **参数**：
  - `coord_id`：坐标轴编号 `1 ~ 6`。
  - `direction`：方向，`0` 或 `1`。
  - `speed`：点动速度，范围 `1 ~ 100`。
  - `_async`：是否异步；默认 `None` 时按开环处理，只等待指令反馈，不等待到位；显式传 `_async=False` 时才等待到位。JOG 在刷新模式下始终不可用。
- **返回值**：运动 ACK。
- **刷新模式限制**：`fresh_mode=1` 时会直接返回“刷新模式无法使用JOG运动，请切换插补模式使用。”，不会下发 JOG 指令。

```python
robot.upper_jog_coord(3, 1, 10)
```

### `upper_jog_coord_increment(coord_id, increment, speed, _async=None)`

- **功能**：双臂同一坐标轴按增量步进。
- **参数**：
  - `coord_id`：坐标轴编号 `1 ~ 6`。
  - `increment`：坐标增量，参数类型为 `int` 或 `float`，不允许 `bool`；范围按对应坐标轴总跨度校验，即 `坐标最大值 - 坐标最小值` 的正负值。X `-1300.0 ~ 1300.0`，Y `-1682.0 ~ 1682.0`，Z `-1301.0 ~ 1301.0`，RX/RY/RZ `-360.0 ~ 360.0`。
  - `speed`：运动速度，范围 `1 ~ 100`。
  - `_async`：是否异步；JOG 增量在刷新模式下始终不可用。
- **返回值**：运动结果。
- **刷新模式限制**：`fresh_mode=1` 时不会下发 JOG 增量指令。
- **协议编码说明**：XYZ 增量会乘以 `10`，RX/RY/RZ 增量会乘以 `100` 后编码为 int16；如果物理范围内的增量换算后超过 `-32768 ~ 32767`，SDK 会按 Pro450 策略截断到 int16 边界后下发。

```python
robot.upper_jog_coord_increment(3, 10, 20)
```

### `upper_solve_inv_kinematics(left_coords, right_coords)`

- **功能**：根据左右臂目标坐标求逆解。
- **参数**：
  - `left_coords`：左臂 6 个坐标，X `-650.0 ~ 650.0`，Y `-841.0 ~ 841.0`，Z `-636.0 ~ 665.0`，`rx/ry/rz` 范围 `-180.0 ~ 180.0`。
  - `right_coords`：右臂 6 个坐标，范围同 `left_coords`。
  - 单臂对象调用时只传当前手臂的 `coords`。
- **返回值**：协议返回的逆解结果，具体结构以固件 payload 为准。

```python
print(robot.upper_solve_inv_kinematics([0, 0, 300, 0, 0, 0], [0, 0, 300, 0, 0, 0]))
print(robot.left_arm.upper_solve_inv_kinematics([0, 0, 300, 0, 0, 0]))
```

### `upper_write_mov_c(payload=b"", _async=None)`

- **功能**：发送 MovC 相关原始 payload。
- **参数**：
  - `payload`：`bytes`，由调用方按协议构造。
  - `_async`：是否异步。
- **返回值**：运动结果。

```python
robot.upper_write_mov_c(b"", _async=True)
robot.left_arm.upper_write_mov_c(b"", _async=True)
```

## 校准、使能、限位与参数

### `set_upper_joint_calibrate(joint_id=254)`

- **功能**：设置关节零位。
- **参数**：
  - `joint_id`：`1 ~ 8`；`254` 表示全部关节。
- **返回值**：ACK 解析值。

```python
robot.set_upper_joint_calibrate(254)
robot.left_arm.set_upper_joint_calibrate(1)
```

### `get_upper_is_init_calibrate()`

- **功能**：读取零位校准状态。
- **参数**：无。
- **返回值**：`{"left": {...}, "right": {...}}`。
  - `ok`：该臂是否全部校准。
  - `states`：每个关节的原始状态。
  - `uncalibrated_joints`：未校准关节号列表。

```python
print(robot.get_upper_is_init_calibrate())
```

### `get_upper_zero_encoder()`

- **功能**：读取零位编码器值。
- **参数**：无。
- **返回值**：`{"left": [7个int32], "right": [7个int32]}`。

```python
print(robot.get_upper_zero_encoder())
```

### `set_upper_joint_enable(joint_id, state)`

- **功能**：设置关节使能。
- **参数**：
  - `joint_id`：`1 ~ 8`；`254` 表示全部关节。
  - `state`：`1` 使能，`0` 失能。
- **返回值**：ACK 解析值。

```python
robot.set_upper_joint_enable(254, 1)
```

### `upper_set_break(joint_id, state)`

- **功能**：设置关节抱闸状态。
- **参数**：
  - `joint_id`：关节号 `1 ~ 8`。
  - `state`：协议定义的抱闸状态值，按单字节发送，常用 `0` / `1`。
- **返回值**：ACK 解析值。

```python
robot.upper_set_break(1, 1)
```

### `set_robot_safety_level(level)` / `get_robot_safety_level()`

- **功能**：设置或读取 SDK 侧整机安全模式，不下发上半身 `0x3A` 协议。
- **参数**：
  - `0`：默认独立模式，各模块故障只保护自身。
  - `1`：底盘双轮。
  - `2`：底盘升降。
  - `3`：左臂。
  - `4`：右臂。
  - `5`：夹爪。
  - `6`：头部。
  - `[1..6]` 组合列表：组合内任一模块出现 `CRITICAL` 故障时，组合内其它模块运动接口会被 SDK 拦截。
- **参数校验**：不允许空列表、单元素列表、重复值、`0` 出现在列表中或非整数类型。
- **返回值**：默认成功返回 `CommandResult(ok=True, data=level)`；`plain_return=True` 时直接返回 `level`。被拦截时返回 `CommandResult(ok=False, blocked_by=<故障模块>)`。
- **故障缓存来源**：
  - 真实链路实例化时会尝试读取一次 `get_upper_robot_status()`，成功后同步左右臂/夹爪故障缓存；失败不影响对象创建。
  - 每次 `get_upper_robot_status()` / 单臂状态读取成功后，都会更新对应模块故障缓存。
  - 运动闭环收到 `0x5B` / `0x5C` 非 0 错误反馈时，会把对应左臂/右臂登记为 `CRITICAL`；J8 单关节运动错误会额外登记夹爪故障。
  - 状态恢复正常后，状态查询会清除对应缓存。

```python
robot.set_robot_safety_level(0)        # 默认：模块独立
robot.set_robot_safety_level(3)        # 左臂单模块保护
robot.set_robot_safety_level([3, 4])   # 左臂/右臂组合保护
robot.get_robot_safety_level()
```

### `get_upper_joints_min_angle()` / `get_upper_joints_max_angle()`

- **功能**：读取上半身总的关节最小/最大限位；该组接口不区分左右臂。
- **参数**：无。
- **返回值**：`[J1..J8]`，8 个关节的角度限位列表；协议值按 `0.1°` 解析。

```python
print(robot.get_upper_joints_min_angle())
print(robot.get_upper_joints_max_angle())
```

### `set_joint_min_angle(joint_id, degree)` / `set_joint_max_angle(joint_id, degree)`

- **功能**：设置上半身总的关节软件最小/最大限位；该组接口不区分左右臂，只通过 `robot` 总入口调用。
- **参数**：
  - `joint_id`：关节号 `1 ~ 8`。
  - `degree`：角度，按 `joint_id` 校验；J1 `-166.0 ~ 166.0`，J2 `-80.0 ~ 105.0`，J3 `-166.0 ~ 166.0`，J4 `-170.0 ~ 10.0`，J5 `-166.0 ~ 166.0`，J6 `-100.0 ~ 100.0`，J7 `-100.0 ~ 100.0`，J8 `0.0 ~ 125.0`。
- **返回值**：ACK 解析值。
- **说明**：协议下发值按 `0.1°` 编码，例如 `90°` 下发为 `900`。

```python
robot.set_joint_min_angle(1, -90)
robot.set_joint_max_angle(1, 90)
```

### `get_upper_plan_sp(mode)` / `set_upper_plan_sp(mode, speed)`

- **功能**：读取/设置规划速度。
- **参数**：
  - `mode`：`0` 表示角度/关节规划速度；`1` 表示坐标规划速度。
  - `speed`：`mode=0` 时范围 `1 ~ 150`；`mode=1` 时范围 `1 ~ 200`。
- **返回值**：
  - 读取：`[left, right]`。
  - 设置：ACK 解析值。

```python
print(robot.get_upper_plan_sp(0))
robot.set_upper_plan_sp(0, 100)
```

### `get_upper_plan_acc(mode)` / `set_upper_plan_acc(mode, acc)`

- **功能**：读取/设置规划加速度。
- **参数**：
  - `mode`：`0` 表示角度/关节规划加速度；`1` 表示坐标规划加速度。
  - `acc`：`mode=0` 时范围 `1 ~ 200`；`mode=1` 时范围 `1 ~ 400`。
- **返回值**：
  - 读取：`[left, right]`。
  - 设置：ACK 解析值。

```python
print(robot.get_upper_plan_acc(1))
robot.set_upper_plan_acc(1, 100)
```

### `get_upper_joint_acc()` / `set_upper_joint_acc(joint_id, acc)`

- **功能**：读取左右臂 7 个关节加速度参数，或设置指定关节加速度参数。
- **参数**：
  - `get_upper_joint_acc()`：无参数。
  - `joint_id`：设置时的关节号 `1 ~ 7`。
  - `acc`：加速度参数，范围 `0.001 ~ 0.1`，协议下发值为 `acc * 1000`。
- **模式限制**：`set_upper_joint_acc()` 只能在刷新模式下使用。SDK 会在下发前读取 `get_upper_fresh_mode()`；目标手臂处于插补模式时直接返回提示，不下发 `0x8A`。
- **返回值**：
  - 读取：`{"left": [J1..J7], "right": [J1..J7]}`，每个值按协议 `uint16 / 1000` 解析。
  - 单臂读取：`[J1..J7]`。
  - 设置：ACK 解析值。

```python
print(robot.get_upper_joint_acc())
print(robot.left_arm.get_upper_joint_acc())
robot.set_upper_joint_acc(1, 0.02)
```

## 状态与诊断

### `get_upper_robot_status()`

- **功能**：读取上半身错误状态。
- **参数**：无。
- **返回值**：
  - 正常：`{"left": 0, "right": 0}`。
  - 单臂正常：`0`。
  - 有错误时，仅返回异常侧的有效信息。
  - `robot.get_upper_robot_status()` 是总接口，始终保留 `"left"` / `"right"` 外层结构。
  - `robot.left_arm.get_upper_robot_status()` / `robot.right_arm.get_upper_robot_status()` 是单臂接口，只返回当前臂内容，因此异常时不会再带 `"left"` 或 `"right"` 外层 key。

错误示例：

```python
{
    "left": 0,
    "right": {
        "soft_error": {
            "raw": 0x8088,
            "joint_mask": 0x80,
            "joint_ids": [8],
            "error_code": 0x88,
            "message": "..."
        },
        "motor_errors": [
            {"joint_id": 3, "bitmask": 256, "messages": ["..."]}
        ]
    }
}
```

调用示例：

```python
print(robot.get_upper_robot_status())
print(robot.left_arm.get_upper_robot_status())
print(robot.right_arm.get_upper_robot_status())
```

右臂软件错误示例：

```python
# 总接口返回，左臂正常、右臂异常
{
    "left": 0,
    "right": {
        "soft_error": {
            "raw": 481,
            "joint_mask": 1,
            "joint_ids": [1],
            "error_code": 225,
            "message": "..."
        }
    }
}

# robot.right_arm.get_upper_robot_status() 单臂返回，只保留右臂内容
{
    "soft_error": {
        "raw": 481,
        "joint_mask": 1,
        "joint_ids": [1],
        "error_code": 225,
        "message": "..."
    }
}
```

### `get_upper_joints_status()`

- **功能**：读取上半身关节/机器人状态。
- **参数**：无。
- **返回值**：同 `get_upper_robot_status()`。

```python
print(robot.get_upper_joints_status())
```

### `clear_upper_error(joint_id=254)`

- **功能**：清除上半身错误。
- **参数**：
  - `joint_id`：`1 ~ 8`；`254` 表示全部关节。
- **返回值**：ACK 解析值。

```python
robot.clear_upper_error()
```

### `get_upper_joints_current()`

- **功能**：读取左右臂关节电流。
- **参数**：无。
- **返回值**：`{"left": [J1..J8], "right": [J1..J8]}`。

```python
print(robot.get_upper_joints_current())
```

### `get_upper_joints_run_sp()`

- **功能**：读取左右臂关节运行速度。
- **参数**：无。
- **返回值**：`{"left": [J1..J8], "right": [J1..J8]}`。

```python
print(robot.get_upper_joints_run_sp())
```

### `get_upper_encoders()`

- **功能**：读取左右臂编码器值。
- **参数**：无。
- **返回值**：`{"left": [7个int32], "right": [7个int32]}`。

```python
print(robot.get_upper_encoders())
```

### `get_upper_joint_loss_count(joint_id)`

- **功能**：读取指定关节通信丢包/异常计数。
- **参数**：
  - `joint_id`：关节号 `1 ~ 8`。
- **返回值**：`{"left": {"send_abnormal": int, "read_abnormal": int}, "right": {...}}`。

```python
print(robot.get_upper_joint_loss_count(1))
print(robot.left_arm.get_upper_joint_loss_count(1))
```

### `get_upper_model_direction()` / `set_upper_model_direction(joint_id, direction)`

- **功能**：读取/设置模型方向参数。
- **参数**：
  - `joint_id`：设置时的关节号。
  - `direction`：方向值，按协议定义，按单字节发送。
- **返回值**：
  - 读取：`{"left": [...], "right": [...]}`。
  - 设置：ACK 解析值。

```python
print(robot.get_upper_model_direction())
robot.set_upper_model_direction(1, 0)
```

## 拖动示教与轨迹

### `upper_drag_teach_record()`

- **功能**：开始拖动示教录制。
- **参数**：无。
- **返回值**：ACK 解析值。

```python
robot.upper_drag_teach_record()
robot.left_arm.upper_drag_teach_record()
```

### `upper_drag_teach_record_pause()`

- **功能**：暂停拖动示教录制。
- **参数**：无。
- **返回值**：ACK 解析值。

```python
robot.upper_drag_teach_record_pause()
```

### `upper_drag_teach_record_clear()`

- **功能**：清除拖动示教录制数据。
- **参数**：无。
- **返回值**：ACK 解析值。

```python
robot.upper_drag_teach_record_clear()
```

### `upper_drag_teach_play()`

- **功能**：播放拖动示教轨迹。
- **参数**：无。
- **返回值**：运动结果。

```python
robot.upper_drag_teach_play()
```

### `drag_teach_multi_record(trajectory_id=0)`

- **功能**：按轨迹 ID 录制拖动示教。
- **参数**：
  - `trajectory_id`：轨迹编号，默认 `0`。
- **返回值**：ACK 解析值。

```python
robot.drag_teach_multi_record(0)
```

### `upper_drag_teach_multi_play(trajectory_id=0)`

- **功能**：按轨迹 ID 播放拖动示教。
- **参数**：
  - `trajectory_id`：轨迹编号，默认 `0`。
- **返回值**：运动结果。

```python
robot.upper_drag_teach_multi_play(0)
```

### `upper_fourier_trajectories(rank=0)`

- **功能**：执行参数辨识轨迹。建议先用 `rank=1` 低速轨迹确认运动范围安全，再用 `rank=0` 正常轨迹。
- **参数**：`rank` 为 `0` 或 `1`，`0=辨识轨迹`，`1=低速辨识轨迹`。
- **返回值**：ACK 解析值，成功通常为 `1`。单臂可用 `robot.left_arm.upper_fourier_trajectories(rank)` 或 `robot.right_arm.upper_fourier_trajectories(rank)`。

```python
robot.upper_fourier_trajectories(rank=1)
robot.upper_fourier_trajectories(rank=0)
```

### `upper_parameter_identify()`

- **功能**：执行参数辨识计算，协议说明耗时约 5 分钟。
- **参数**：无。
- **返回值**：ACK 解析值，成功通常为 `1`。

```python
robot.upper_parameter_identify()
```

## 高级配置

本节部分接口属于单臂对象能力，示例中会使用 `robot.left_arm` 或 `robot.right_arm` 调用。读取类请求帧不下发 `arm_type`；固件返回左右臂数据时，SDK 在单臂对象中筛选当前手臂的数据。

### `set_upper_tool_reference(left, right)` / `get_upper_tool_reference()`

- **功能**：设置/读取工具坐标系参考值。
- **参数**：
  - `left`：左臂 6 个工具坐标值 `[x, y, z, rx, ry, rz]`。
  - `right`：右臂 6 个工具坐标值 `[x, y, z, rx, ry, rz]`；总入口必须传左右两组参数。
  - 坐标范围：`x/y/z` 为 `-1000.0 ~ 1000.0 mm`，`rx/ry/rz` 为 `-180.0 ~ 180.0 deg`。
- **返回值**：
  - 总入口读取：`{"left": [x, y, z, rx, ry, rz], "right": [x, y, z, rx, ry, rz]}`。
  - 单臂入口读取：当前手臂 `[x, y, z, rx, ry, rz]`。
  - 设置：ACK 解析值，成功通常为 `1`。
- **说明**：单臂设置时，SDK 会按左右顺序补另一侧为 `0` 后下发。

```python
robot.set_upper_tool_reference([10, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0])
print(robot.get_upper_tool_reference())
print(robot.right_arm.get_upper_tool_reference())
robot.right_arm.set_upper_tool_reference([10, 0, 0, 0, 0, 0])
```

### `set_upper_world_reference(coords)` / `get_upper_world_reference()`

- **功能**：设置/读取世界坐标系参考值。
- **参数**：
  - `coords`：6 个坐标值，左右臂同时设置为同一份世界坐标系参考值，协议 payload 使用 `arm_type=0x03`。
  - 坐标范围：`x/y/z` 为 `-1000.0 ~ 1000.0 mm`，`rx/ry/rz` 为 `-180.0 ~ 180.0 deg`。
- **返回值**：
  - 读取：`{"left": [x, y, z, rx, ry, rz], "right": [x, y, z, rx, ry, rz]}`。
  - 设置：ACK 解析值，成功通常为 `1`。
- **说明**：该接口仅通过 `robot` 总入口调用，不再提供 `robot.left_arm` / `robot.right_arm` 同名入口。

```python
robot.set_upper_world_reference([0, 0, 0, 0, 0, 0])
print(robot.get_upper_world_reference())
```

### `set_upper_reference_frame(base_type)` / `get_upper_reference_frame()`

- **功能**：设置/读取参考坐标系。
- **参数**：
  - `base_type`：`0` 表示 base，`1` 表示 world。
- **返回值**：
  - 读取：`0` 或 `1`。
  - 设置：ACK 解析值。
- **说明**：该接口为上半身总参数，不区分左右臂；仅通过 `robot` 总入口调用。

```python
robot.set_upper_reference_frame(0)
print(robot.get_upper_reference_frame())
```

### `set_upper_movement_type(left, right)` / `get_upper_movement_type()`

- **功能**：设置/读取运动类型。
- **参数**：
  - `left`：左臂运动类型值，当前 SDK 校验范围为 `0 ~ 4`。
  - `right`：右臂运动类型值，当前 SDK 校验范围为 `0 ~ 4`；总入口必须同时传入左右两个值。
- **返回值**：
  - 总入口读取：`[left, right]`；双字节返回时分别表示左右臂，旧固件单字节返回时左右同值。
  - 单臂读取：`int`。
  - 设置：返回 ACK 解析值，成功通常为 `1`。
- **说明**：公开接口不需要传手臂类型；总入口由 SDK 内部按双臂下发，单臂入口会将另一侧补 `0`。

```python
robot.set_upper_movement_type(0, 1)
robot.right_arm.set_upper_movement_type(1)
print(robot.get_upper_movement_type())
```

### `set_upper_end_type(left, right)` / `get_upper_end_type()`

- **功能**：设置/读取末端类型。
- **参数**：
  - `left`：左臂末端类型，`0` 表示法兰，`1` 表示工具。
  - `right`：右臂末端类型，`0` 表示法兰，`1` 表示工具；总入口必须同时传入左右两个值。
- **返回值**：
  - 总入口读取：`[left, right]`；双字节返回时分别表示左右臂，旧固件单字节返回时左右同值。
  - 单臂读取：`0` 或 `1`。
  - 设置：返回 ACK 解析值，成功通常为 `1`。
- **说明**：公开接口不需要传手臂类型；总入口由 SDK 内部按双臂下发，单臂入口会将另一侧补 `0`。

```python
robot.set_upper_end_type(0, 1)
robot.right_arm.set_upper_end_type(1)
print(robot.get_upper_end_type())
```

### `get_upper_collision_mode()`

- **功能**：读取左右臂碰撞检测模式。
- **参数**：无。
- **返回值**：
  - `robot.get_upper_collision_mode()` 返回 `{"left": 0/1, "right": 0/1}`。
  - `robot.left_arm.get_upper_collision_mode()` / `robot.right_arm.get_upper_collision_mode()` 返回当前侧整数值。
- **说明**：`0=关闭`，`1=开启`。
- **数据顺序**：读取返回中不包含手臂类型，第 1 个值是左臂模式，第 9 个值是右臂模式。

```python
print(robot.get_upper_collision_mode())
print(robot.left_arm.get_upper_collision_mode())
```

### `set_upper_collision_mode(mode)`

- **功能**：设置碰撞检测模式。
- **参数**：
  - `mode`：`0` 或 `1`，`0=关闭`，`1=开启`。
- **返回值**：成功时通常返回 `1`。
- **说明**：整机入口会同时设置左右臂；单臂入口只设置当前侧。

```python
robot.set_upper_collision_mode(1)
robot.left_arm.set_upper_collision_mode(1)
```

### `get_upper_collision_threshold()`

- **功能**：读取碰撞阈值。
- **参数**：无。
- **返回值**：
  - `robot.get_upper_collision_threshold()` 返回 `{"left": [J1..J7], "right": [J1..J7]}`。
  - `robot.left_arm.get_upper_collision_threshold()` / `robot.right_arm.get_upper_collision_threshold()` 返回当前侧 7 个关节阈值列表。
- **说明**：列表顺序固定为 J1 到 J7。
- **数据顺序**：读取返回中不包含手臂类型，左臂阈值为第 2~8 个值，右臂阈值为第 10~16 个值。

```python
print(robot.get_upper_collision_threshold())
print(robot.left_arm.get_upper_collision_threshold())
```

### `set_upper_collision_threshold(joint_id, threshold)`

- **功能**：设置某个关节的碰撞阈值。
- **参数**：
  - `joint_id`：`1 ~ 7`。
  - `threshold`：`50 ~ 250`。
- **返回值**：成功时通常返回 `1`。
- **说明**：整机入口会同时设置左右臂指定关节；单臂入口只设置当前侧。

```python
robot.set_upper_collision_threshold(3, 100)
robot.left_arm.set_upper_collision_threshold(3, 100)
```

### `get_upper_vr_mode()` / `set_upper_vr_mode(left, right)`

- **功能**：读取/设置 VR 模式。
- **参数**：
  - `left`：左臂 VR 模式值，`0=关闭`，`1=开启`。
  - `right`：右臂 VR 模式值，`0=关闭`，`1=开启`；总入口必须同时传入左右两个值。
- **返回值**：
  - 读取：总入口返回 `[left, right]`，单臂入口返回对应手臂值。
  - 设置：ACK 解析值。
- **说明**：总入口下发 `arm_type=0x03 + left + right`；单臂入口只下发 `arm_type + mode`，不补另一侧 `0`。

```python
print(robot.get_upper_vr_mode())
robot.set_upper_vr_mode(0, 1)
robot.right_arm.set_upper_vr_mode(1)
```

### `get_upper_filter_len(rank)` / `set_upper_filter_len(rank, value)`

- **功能**：读取/设置滤波长度。
- **参数**：
  - `rank`：滤波参数类型，`1~5`。
  - `value`：滤波参数值，`1~255`，仅设置接口需要。
- **返回值**：
  - 读取：总入口返回 `[left, right]`，单臂入口返回对应手臂值。
  - 设置：ACK 解析值。

```python
print(robot.left_arm.get_upper_filter_len(1))
robot.left_arm.set_upper_filter_len(1, 10)
```

### `get_upper_gripper_force()`

- **功能**：读取地址 `1` 的夹爪夹持力参数。
- **参数**：无。
- **返回值**：
  - 总入口返回 `{"left": int, "right": int}`。
  - 单臂入口返回当前手臂夹爪夹持力 `int`。
- **说明**：该接口等价于读取 `get_upper_gripper_param(1)`，但更适合测试人员直接验证夹持力。

```python
print(robot.get_upper_gripper_force())
print(robot.left_arm.get_upper_gripper_force())
print(robot.right_arm.get_upper_gripper_force())
```

### `set_upper_gripper_force(value)`

- **功能**：设置地址 `1` 的夹爪夹持力参数。
- **参数**：
  - `value`：夹持力参数值，范围 `0 ~ 500`。
- **返回值**：成功通常返回 `1`。
- **说明**：该接口等价于设置 `set_upper_gripper_param(1, value)`，但更适合测试人员直接验证夹持力。

```python
print(robot.set_upper_gripper_force(200))
print(robot.left_arm.set_upper_gripper_force(200))
print(robot.right_arm.set_upper_gripper_force(200))
```

### `get_upper_gripper_param(addr)` / `set_upper_gripper_param(addr, value)`

- **功能**：读取/设置夹爪参数。
- **参数**：
  - `addr`：参数地址，暂定范围 `1 ~ 254`；当前已知地址 `1` 为夹持力参数。
  - `value`：参数值，仅设置接口需要；`addr=1` 时范围 `0 ~ 500`，其它地址暂按 `0 ~ 0xFFFFFFFF` 基础整型校验。
- **协议行为**：设置接口会下发 `arm_type + addr + left_value(4B) + right_value(4B)`；总入口左右同值，单臂入口另一侧补 `0`。读取接口只下发 `addr`，不带 `arm_type`。
- **返回值**：
  - 总入口读取返回 `{left: int, right: int}`。
  - 单臂读取返回对应手臂的 `int`。
  - 设置返回 ACK 解析值，成功通常为 `1`。

```python
print(robot.get_upper_gripper_param(1))
print(robot.left_arm.get_upper_gripper_param(1))
print(robot.right_arm.get_upper_gripper_param(1))

robot.set_upper_gripper_param(1, 200)
robot.left_arm.set_upper_gripper_param(1, 200)
robot.right_arm.set_upper_gripper_param(1, 200)
```

### `get_upper_gripper_status()`

- **功能**：读取夹爪夹持状态，对应 `0x56 GetGripper`。
- **参数**：无。
- **返回值**：总入口返回左右状态结构，单臂入口返回当前手臂状态；状态值含义为 `0=空闲`、`1=张开中`、`2=闭合中`、`3=建力中`、`4=力保持`、`5=物体丢失`、`6=松开中`、`7=点动中`、`8=故障`。

```python
print(robot.get_upper_gripper_status())
print(robot.left_arm.get_upper_gripper_status())
```

### `set_upper_gripper_calibrate_mode(calibrate_type)`

- **功能**：夹爪力/摩擦标定，对应 `0x57 ForceCalibrate`。
- **参数**：`calibrate_type` 取值 `1 ~ 2`，`1=力标定`，`2=摩擦标定`。
- **返回值**：ACK 解析值，成功通常为 `1`。

```python
robot.set_upper_gripper_calibrate_mode(1)
robot.left_arm.set_upper_gripper_calibrate_mode(2)
```

### `get_upper_joints_temp()`

- **功能**：读取上半身左右臂 8 个关节温度。
- **参数**：无。
- **返回值**：
  - 总入口：`{"left": [...8], "right": [...8]}`。
  - 单臂入口：对应手臂的 8 个温度值列表。

```python
print(robot.get_upper_joints_temp())
print(robot.left_arm.get_upper_joints_temp())
```

### `get_upper_gripper_temp()`

- **功能**：读取上半身夹爪温度；该接口复用 `GetJointsTemp(0xC2)` 返回内容，并取每侧 J8 温度。
- **参数**：无。
- **返回值**：
  - 总入口：`{"left": int, "right": int}`。
  - 单臂入口：对应手臂的夹爪温度 `int`。

```python
print(robot.get_upper_gripper_temp())
print(robot.left_arm.get_upper_gripper_temp())
print(robot.right_arm.get_upper_gripper_temp())
```

## 单臂常用接口补充

单臂对象由 `TuyaRobot` 自动创建：

```python
left = robot.left_arm
right = robot.right_arm
```

常用单臂接口和双臂接口同名或近似：

| 单臂接口 | 功能 | 返回值差异 |
| --- | --- | --- |
| `left.send_upper_angles(angles, arm_speed, gripper_speed)` | 左臂关节角运动 | 当前臂运动结果。 |
| `right.send_upper_angle(joint_id, angle, speed)` | 右臂单关节运动 | 当前臂运动结果。 |
| `left.get_upper_angles()` | 读取左臂角度 | `[J1..J8]`。 |
| `right.get_upper_coords()` | 读取右臂坐标 | `[x, y, z, rx, ry, rz]`。 |
| `left.upper_jog_angle(...)` | 左臂关节点动 | 当前臂 ACK。 |
| `right.upper_jog_coord(...)` | 右臂坐标点动 | 当前臂 ACK。 |
| `left.get_upper_robot_status()` | 左臂错误状态 | 正常为 `0`，异常为错误结构。 |
| `right.get_upper_is_init_calibrate()` | 右臂零位状态 | 当前臂 `{"ok": ..., "states": ..., "uncalibrated_joints": ...}`。 |

示例：

```python
robot.left_arm.send_upper_angles([0, 0, 0, 0, 0, 0, 0, 0], 20, 0)
print(robot.right_arm.get_upper_robot_status())
```

## 常用安全调试流程

建议真机首次验证按以下顺序：

```python
from pytuyarobot import TuyaRobot

robot = TuyaRobot(
    "192.168.1.232",
    6500,
    head_auto_connect=False,
    chassis_auto_connect=False,
    apply_limits_on_init=False,
    debug=True,
)

print("power:", robot.is_upper_powered_on())
print("status:", robot.get_upper_robot_status())
print("calibrate:", robot.get_upper_is_init_calibrate())
print("angles:", robot.get_upper_angles())

robot.upper_power_on()
robot.send_upper_angle(1, 0, 10, _async=False)
print("in position:", robot.get_upper_is_in_position(0, [0] * 8, [0] * 8))

robot.close()
```

## 注意事项

- 角度目标为 8 个关节，其中 J8 通常对应夹爪相关轴；编码器接口目前按协议返回 7 个关节编码器值。
- 坐标目标为 6 个值：`x, y, z, rx, ry, rz`。
- 所有运动速度、角度、坐标都会经过 SDK 参数校验；若参数越界，会抛出对应的数据异常。
- 使用 `debug=True` 可查看通信帧，便于和协议文档或真机日志对照。
- 运动接口 `_async=True` 只表示不等待到位反馈，不代表运动已经完成；未传 `_async` 时使用 `get_upper_motion_async()` 的全局默认值。
- 使用完毕建议调用 `robot.close()` 释放连接。
