# TuyaRobot 第一批运动接口自动化说明

更新日期：2026-07-17

## 已建立的接口资产

以下接口均已建立同名 Python 测试文件和 Excel Sheet：

- `send_upper_angle`
- `send_upper_angles`
- `upper_jog_angle`
- `upper_jog_angle_increment`
- `send_upper_coord`
- `send_upper_coords`
- `write_upper_coord`
- `write_upper_coords`
- `upper_jog_coord`
- `upper_jog_coord_increment`
- `upper_go_zero`

本批共建立 10 个测试文件、28 个测试函数和 534 条参数化用例。

## 已确认并写入的数据

- `send_upper_angle` 同时验证刷新模式 `1` 和插补模式 `0`。左右单臂分别覆盖 J1～J7 普通角度及软件限位；双臂覆盖 J1～J7 正负 10°，不执行双臂软件限位。
- 所有刷新模式运动（`send_upper_angle`、`send_upper_angles`、`send_upper_coord`、`send_upper_coords` 及刷新模式 Jog 不支持验证）均在模式回读后显式启用 `set_upper_motion_async(True)`；插补模式显式设置为 `False`。发送用例在清理时恢复原默认异步状态，Jog 不支持验证恢复模块约定的插补同步状态。
- 公共回零统一经 `TuyaRobotBase.go_zero()` 或 `go_arm_zero()` 下发已确认的 `[0, 0, 0, 0, 0, 0, 0, 0]` 零位关节角度，调用 SDK `send_upper_angles`，不使用 SDK `upper_go_zero()`；发送后仍以 `wait_upper(timeout=...)` 确认停止。
- 为防止关节目标叠加成未经确认的组合姿态，每条 `send_upper_angle` 关节用例结束后回到 `[0, 0, 0, 0, 0, 0, 0, 0]`，模块结束固定恢复双臂插补模式 `0`。回零速度统一使用 `TuyaRobotBase.speed`。
- 关节速度合法值：`1、10、20、100`。
- 关节速度非法值：`0、101`。
- J1～J7 软件限位：
  - 最小值：`[-150, -72, -163, -149, -179, -87, -80]`
  - 最大值：`[176, 125, 167, 1, 148, 42, 92]`
- 各关节下限减 1°、上限加 1°的非法参数。
- 坐标范围：
  - 最小值：`[-650, -841, -636, -180, -180, -180]`
  - 最大值：`[650, 841, 665, 180, 180, 180]`
- 各坐标轴下限减 1、上限加 1 的非法参数。
- Jog 方向：`0` 为反向（负向），`1` 为正向。
- `send_upper_coord` 左右单臂分别覆盖刷新模式 `1` 和插补模式 `0` 下六个坐标轴的正负 10 mm/10° 运动，不创建双臂坐标用例。每条用例先进入已确认坐标初始姿态，结束后回零，模块结束恢复插补模式。
- `send_upper_angles` 使用 3 组已确认的左右臂完整姿态，分别按低速 `10`、中速 `50`、高速 `100` 覆盖左臂、右臂和双臂同时运动，并覆盖刷新模式 `1` 和插补模式 `0`。
- `send_upper_coords` 使用 3 组已确认的左右臂绝对目标，分别按低速 `10`、中速 `50`、高速 `100` 覆盖左臂、右臂和双臂同时运动，并覆盖刷新模式 `1` 和插补模式 `0`；`expect_data` 随模式分别为 `1` 和 `0`。每条正常用例均在 `finally` 中调用 `device.go_zero()`，确保最终回到双臂零位。

## Jog 测试方式

- `upper_jog_angle` 分别调用左臂、右臂和双臂正式接口，覆盖 J1～J7 的正向和负向运动，并以对应软件限位为期望值。
- 每条关节 Jog 运动用例先设置双臂插补模式 `0` 并调用 `device.go_zero()`；异步下发 Jog 后等待其在软件限位自行停止并回读角度，在 `finally` 中直接回零，不额外调用 `upper_stop()`。
- 刷新模式 `1` 不支持连续 Jog 与步进 Jog；`upper_jog_angle`、`upper_jog_coord`、`upper_jog_angle_increment`、`upper_jog_coord_increment` 各保留一条左臂调用验证：返回失败 `CommandResult`（提示切换插补模式），结束后恢复双臂插补模式并回零。
- `upper_jog_angle_increment` 正常用例共 21 条：左臂、右臂和双臂分别覆盖 J1～J7，每条从零位执行单关节 30° 步进，J4 因正向软件限位仅为 `1°`而使用 `-30°`；同步等待到位、回读角度，并在 `finally` 中回零。
- 关节步进超限共 42 条：按各关节 `|负限位| + |正限位|` 得到完整行程，再分别使用 `-(完整行程+1°)` 和 `完整行程+1°`，覆盖左臂、右臂和双臂。用例不增加 SDK 预校验或跳过逻辑，按公开接口正常调用，并启用 `motion + manual + danger`。
- `upper_jog_coord` 单臂正常用例共 24 条，左右臂分别覆盖六个坐标轴正负向；双臂正常用例只覆盖 Z 轴正负向 2 条。单臂仅移动目标臂到坐标初始点位，双臂移动双臂。结束态以 Excel 与实机为准：业务返回 `0` 的用例只断言返回值；失败 `CommandResult` 分别断言 `32`“坐标无解”或 `33`“直线运动无相邻解”，后者读取停止坐标后回零；不按坐标软件限位断言。
- `upper_jog_coord_increment` 正常用例共 13 条：左右单臂分别覆盖六轴步进 30 mm/30°，双臂只覆盖 Z 轴步进 30 mm；单臂仅移动目标臂到坐标初始点位，完成回读后回零。
- `get_upper_is_in_position` 共 24 条：模块级一次将双臂运动到坐标初始点位；`normal` 12 条验证 J1/X/RX 边界（期望到位 `1`），`exception` 12 条验证超限（期望未到位 `0`），分两个测试函数；标记 `motion + manual + danger`。
- 坐标步进超限共 36 条：各轴按 `|负限位| + |正限位|` 得到完整行程，再使用正负 `完整行程+1`，覆盖左臂、右臂和双臂。用例按公开接口正常下发并启用 `motion + manual + danger`，不增加 SDK 幅度校验规避逻辑。
- 关节 Jog 到软件限位统一使用低速 `10`；非法速度 `0、101` 分别覆盖左臂、右臂和双臂。
- Jog 到软限位属于真实大范围运动，统一标记 `motion + manual + danger`。

## 当前安全留空项

现有 URDF、DH 和软件限位只能确认运动学范围，不能证明某组完整双臂姿态在实机附件、线缆和装配条件下绝对不会自碰。因此以下字段保留为空：

- 尚未按零位方案重新确认的其他 Jog 和增量接口避让预备角度。

相关旧用例检测到这些字段为空时会明确调用 `pytest.skip`，不会下发运动。`upper_jog_angle` 已由用户确认改为每条用例从零位开始并在结束后回零，不再依赖 Excel 预备姿态字段。

## SDK 契约差异

- 文档说明单臂关节 Jog 不包含夹爪，但当前 SDK 允许 `joint_id=8` 通过本地校验。为避免误下发夹爪 Jog，未把 J8 作为自动异常用例执行。
- 当前 SDK 对 Jog / 关节步进的 `joint_id=0`：单臂抛出 `TuyaRobotSingleArmDataException`，双臂抛出 `TuyaRobotDualArmDataException`，测试按入口分别断言。
- 当前 SDK 的 `validate_upper_jog_increment_joint()` 不校验增量幅度；J1/J3/J5 的 `±333°` 还超过协议 `int16 × 0.01°` 的 `±327.67°` 编码范围。超限数据仍按用户确认写入 Excel 并由公开接口正常调用，该 SDK 风险不在用例中规避。
- 当前 SDK 的 `validate_upper_jog_increment_coord()` 同样不校验增量幅度；RX/RY/RZ 的 `±361°` 超过协议 `int16 × 0.01°` 的编码范围。超限数据仍按用户确认通过公开接口正常调用，不在用例中规避。
- 当前双臂单坐标校验函数对非法参数抛出 `TuyaRobotSingleArmDataException`，测试按当前 SDK 实际异常类型断言。
- 当前已确认 SDK 的坐标本地校验范围为 X `[-650, 650]`、Y `[-841, 841]`、Z `[-636, 665]`、RX/RY/RZ `[-180, 180]`。`send_upper_coords` 的 Z 轴下限异常值使用 `-637`，确保在本地校验阶段拦截。

## 执行安全门控

- 所有真机测试需要 `--run-hardware`。
- 普通运动还需要 `--run-motion`。
- Jog 到软限位还需要 `--run-manual --run-danger`。
- `upper_jog_angle` 已确认从零位开始；坐标 Jog/步进统一使用 `TuyaRobotBase.COORD_MOTION_INITIAL_ANGLES` 中已确认的初始关节姿态，单臂用例只移动目标臂，双臂用例移动双臂。其他尚未确认的运动接口仍会安全跳过。
