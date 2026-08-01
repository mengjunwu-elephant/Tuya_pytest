---
name: tuya-motion-test-authoring
description: >-
  Design, author, or review TuyaRobot upper-body motion pytest cases and Excel
  sheets involving joint/Cartesian moves, Jog, increments, software limits,
  speed boundaries, dual-arm avoidance poses, motion safety gates, or SDK and
  protocol discrepancies. Use for files under testcases/upper_body and motion
  sheets in test_data/upper_body.xlsx.
---

# TuyaRobot 运动用例编写

## 开始前

1. 完整读取仓库根目录 `AGENTS.md`、`.cursorrules` 和
   `.cursor/skills/tuya-pytest-case-authoring/SKILL.md`。
2. 读取 `docs/MOTION_TEST_PLAN.md`，核对当前限位、留空字段和已知 SDK 差异。
3. 先提交测试方案；用户未明确确认前，不创建测试文件、不修改 Excel。
4. 从本地已安装的 `pytuyarobot` 核对真实签名、验证函数和具体异常类型。

## 数据可信度

- URDF、DH 和单轴软限位不能单独证明双臂实机姿态无自碰。
- 只有资料明确或经过实机确认的数据才写入目标角度/坐标。
- 无法确认的完整姿态、避让姿态或绝对坐标保持空白；测试检测空值后必须
  `pytest.skip`，禁止猜值、补零或自动生成大范围目标。
- 软限位数值可以写入 Excel；若到达限位所需的完整姿态未确认，仍不得下发运动。
- 文档期望与 SDK 实际行为不一致时分别记录，按当前 SDK 的具体异常类型断言。

## Jog 与增量规则

- `direction=0` 表示反向/负向，`direction=1` 表示正向。
- 单臂分别使用 `left_arm`、`right_arm` fixture，双臂使用 `upper_body` fixture。
- 关节 Jog 覆盖 J1～J7；文档明确不含夹爪时，不向 J8 下发 Jog。
- `upper_jog_angle` 每条运动用例先设置双臂插补模式 `0` 并调用 `device.go_zero()`；Jog 自行运动到软件限位并停止，回读确认限位后在 `finally` 中直接回零，不额外调用 `upper_stop()`；同时覆盖左臂、右臂和双臂。坐标 Jog 使用统一的已确认坐标运动初始关节姿态，不从 Excel 读取预备角度。
- 刷新模式 `1` 不支持 Jog；`upper_jog_angle`、`upper_jog_coord`、`upper_jog_angle_increment`、`upper_jog_coord_increment` 各保留一条验证：返回失败 `CommandResult`（`ok=False`，消息含“刷新模式无法使用JOG运动”），结束后恢复双臂插补模式并回零。
- Jog 到软限位使用 `motion + manual + danger`，逐关节/坐标轴执行。
- `upper_jog_angle_increment` 分别覆盖左臂、右臂和双臂 J1～J7；每条正常用例从零位执行单关节 30° 步进，J4 使用 `-30°`，回读后在 `finally` 中回零。
- 关节增量超限值按 `|负限位| + |正限位| + 1°` 生成正负值，保留 `motion + manual + danger` 并通过公开接口正常下发；当前 SDK 缺少增量幅度校验，不在测试中增加跳过、预校验或其他规避逻辑。
- `upper_jog_coord` 单臂正常用例覆盖六轴正负向，双臂正常用例只覆盖 Z 轴正负向；单臂通过 `device.move_to_coord_initial_pose(arm_side)` 只移动目标臂，双臂通过无参调用移动双臂。结束态以 Excel 为准：业务返回 `0` 的用例只断言返回值；失败 `CommandResult` 按实机分别断言 `32`“坐标无解”或 `33`“直线运动无相邻解”，后者读取停止坐标后在 `finally` 中回零；不按坐标软件限位断言。
- `upper_jog_coord_increment` 单臂正常用例覆盖六轴步进 30 mm/30°，双臂正常用例只覆盖 Z 轴步进 30 mm；回读增量结果后在 `finally` 中回零。超限值按 `|负限位| + |正限位| + 1` 生成正负值，使用 `motion + manual + danger` 并通过公开接口正常下发，不增加 SDK 幅度校验规避逻辑。
- 其他增量接口验证正负增量及反馈，并在 `finally` 中恢复双臂原始状态。

## 速度和限位

- 已确认的零位角度、J1～J7 软件限位和坐标软件限位统一定义为 `TuyaRobotBase` 类属性；测试文件只引用，不重复维护数值。
- 已确认的坐标运动初始关节姿态定义为 `TuyaRobotBase.COORD_MOTION_INITIAL_ANGLES`。双臂坐标运动调用 `device.move_to_coord_initial_pose()`，单臂坐标 Jog/步进调用 `device.move_to_coord_initial_pose(arm_side)`，只移动目标臂；姿态发送、返回处理和等待逻辑只在该方法中维护。
- 初始姿态对应的左右臂 6 轴坐标定义为 `TuyaRobotBase.COORD_MOTION_INITIAL_COORDS`，初始姿态方法必须按 `coord_tolerance` 回读校验。`send_upper_coord` 不创建双臂同时运动用例：使用 `robot.left_arm`、`robot.right_arm` 分别覆盖刷新模式 `1`、插补模式 `0` 下 X/Y/Z `±10 mm`、RX/RY/RZ `±10°`。每条正常用例先调用 `device.move_to_coord_initial_pose()`，再设置并回读指定手臂模式，最后发送坐标；在 `finally` 中调用 `device.go_zero()`，模块 teardown 固定恢复双臂插补模式 `0`。
- 公共恢复/回零动作使用 `TuyaRobotBase.speed`；不得在测试文件中重复硬编码恢复速度。
- 双臂整臂回零统一调用 `TuyaRobotBase.go_zero()`；`go_zero()` 与 `go_arm_zero()` 使用已确认的零位关节角度通过 `send_upper_angles` 下发，并保留有超时的 `wait_upper()`；不得调用 SDK `upper_go_zero()`。设置参数后的公共默认恢复动作统一封装到 `TuyaRobotBase`，测试函数或 teardown fixture 只负责决定恢复时机。
- 角度、坐标回读分别使用 `TuyaRobotBase.angle_tolerance`、`TuyaRobotBase.coord_tolerance`，当前均为 `0.1`，并通过 `assert_almost_equal` 比较；Excel 的 `expect_data` 仅断言被测接口返回值，不作为位置容差。
- 合法速度至少覆盖 `1、10、20、100`，非法速度覆盖 `0、101`。
- 高速 `100` 只用于确认过的短距离，不用于未确认的大范围边界运动。
- 关节超限使用下限减 1°和上限加 1°；坐标超限使用下限减 1和上限加 1。
- 非法参数应在 SDK 本地校验阶段抛异常；静态调用 validation 函数确认不会发送。
- 精确软限位运动必须低速、逐轴、人工监护，并验证不越界、能停止和反向脱离。

## 测试文件要求

- 保持一接口一文件、一接口一 Sheet，名称与 SDK API/Allure Story 一致。
- 将运动调用、等待、断言和恢复顺序直接写入对应测试函数，禁止用 `_run_motion_case` 等辅助函数隐藏主测试流程。
- 只有接口特有且需多次复用的动作（例如固定执行 1°、0.1° 的小步运动）才可考虑封装；新增任何运动测试公共方法前必须先取得用户明确确认。
- 运动用例的 normal、exception、manual 分类只读取 Excel 的 `test_type`；禁止根据目标角度是否命中限位在代码中二次判断或重分类。
- 所有切换到刷新模式 `1` 后再下发运动的用例，必须在模式回读后显式调用并断言 `set_upper_motion_async(True)`；插补模式 `0` 显式设为 `False`，并在清理中恢复原默认异步状态或模块约定的插补同步状态。`send_upper_angle` 的 Excel 行使用 `arm_side`、`fresh_mode` 和 `motion_mode` 明确手臂、刷新/插补模式及单/双臂场景。模式 setter 只作为前置条件，`expect_data` 仍只断言角度发送接口的业务数据。
- 左右单臂分别覆盖两种模式的 J1～J7 普通目标和软件限位目标；双臂通过 `robot.send_upper_angle` 覆盖两种模式下 J1～J7 的正负 10°，不得创建双臂软件限位用例。为防止目标角度累积成未经确认的组合姿态，每条关节用例在 `finally` 中调用 `device.go_zero()`；模块 teardown 固定将双臂恢复为插补模式 `0`。
- 接口协议和业务断言直接写在测试文件内；不新增 Executor、Adapter、
  ResultHandler 或接口专属断言管理器。
- 使用 `device.wait_upper(timeout=...)`，禁止无超时等待。
- 运动前读取原始状态，在 `try/finally` 中停止并恢复；不吞掉恢复异常。
- 兼容 `plain_return=True` 下的 `CommandResult` 失败返回。
- 异常用例使用 SDK 当前具体异常类，并在 `pytest.raises` 后记录 `exc.value`。

## 验证

1. 静态遍历 Excel 异常行，调用 SDK validation 函数验证具体参数异常。
2. 运行 `python -m compileall -q testcases`。
3. 运行 `pytest testcases --collect-only -q`，不得开启真机门控。
4. 更新规则和技能中的收集基线；当前基线为 120 个测试文件、157 个测试函数、1020 条参数化测试。
5. 只有用户明确授权后，才逐条开启真机及运动门控。
