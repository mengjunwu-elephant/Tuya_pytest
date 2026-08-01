# TuyaRobot 上半身运动测试交接

交接更新日期：2026-07-21

## 当前成果

本次会话完成了上半身运动接口测试规则、公共恢复能力和首批 Excel 驱动用例的整理。目前基线为：

- 119 个测试文件。
- 142 个测试函数。
- 824 条参数化测试。
- 运动接口共 10 个测试文件、10 个同名 Excel Sheet、534 条参数化数据。
- `python -m compileall -q testcases settings.py` 通过。
- `pytest testcases --collect-only -q` 通过，收集 824 条。
- 未运行真机测试。

## 已确认的测试编写规则

### Excel 和用例结构

- 用例 ID 使用从 1 开始的连续纯数字，不加接口缩写前缀。
- `title` 描述实际验证功能和关键参数，例如“设置J1运动到10度”“设置J1运动到-167度，验证角度超限”。
- normal、exception、manual 等分类只读取 Excel 的 `test_type`，测试代码不得根据参数再次推断分类。
- 测试主流程直接写在测试函数中，不使用 `_run_motion_case`、Executor、Adapter 等过度封装。
- 只有接口特有且会重复使用的动作才考虑提取公共方法；新增测试公共方法前必须先得到用户确认。
- Allure 的 feature、story、step、附件名称以及日志统一使用中文。
- 每条用例记录开始、通过、完成日志；开始日志后记录真实 API 和真实入参。

### 返回值和回读断言

- Excel 的 `expect_data` 只表示被测接口的业务返回数据。
- 普通设置接口成功业务返回值为 `1`；运动发送接口按模式返回，插补模式 `0` 返回 `0`，刷新模式 `1` 返回 `1`；查询接口按实际查询数据断言。
- `plain_return=True` 时直接比较接口返回值与 `expect_data`。
- `plain_return=False` 时先确认 `CommandResult.ok`，再取 `CommandResult.data` 与同一列 `expect_data` 比较；不为两种返回模式重复增加期望列。
- `TuyaRobotBase.result_data(result)` 已统一处理直接返回值和 `CommandResult` 解包；失败的 `CommandResult` 会抛出错误。
- 先断言返回类型和结构，再断言业务值。
- 角度和坐标回读统一使用 `assert_almost_equal`，同时保留 Allure 期望值、实际值附件。
- `TuyaRobotBase.angle_tolerance = 0.1`，`TuyaRobotBase.coord_tolerance = 0.1`。
- 不使用 `_is_soft_limit_case` 等基于参数再次识别用例类型的辅助函数，以后也不要添加。

### fixture、连接和恢复

- 根 `conftest.py` 创建唯一的 session 级 `TuyaRobotBase`，测试文件只使用 fixture，不自行连接或关闭设备。
- `testcases/upper_body/conftest.py` 在每条上半身测试前检查双臂上电状态；未全部上电时执行上电并在 30 秒内确认。测试函数中不再重复检查上电状态。
- VS Code pytest 参数已加入 `-s`，终端可显示测试日志。
- 等待运动完成必须有超时；常规运动当前使用 30 秒，关节 Jog 到软件限位使用 300 秒。
- 参数 setter 先读取原值，并在 `try/finally` 中恢复；公共默认恢复动作放入 `TuyaRobotBase`。
- `TuyaRobotBase.speed = 20`，整臂回零和公共恢复动作使用该速度。
- `TuyaRobotBase.go_zero()` 负责双臂整臂回零；`go_arm_zero()` 保留为可复用的单臂回零能力。
- 普通接口默认在全部参数用例执行完成后统一恢复；`send_upper_angle` 和 `send_upper_coord` 为避免目标累积成未经确认的组合姿态，明确作为安全例外，每条运动用例结束后回零。

## `send_upper_angle` 当前设计

- 刷新模式为 `1`，插补模式为 `0`；每条用例先设置并回读验证目标模式。
- 左右臂分别通过单臂对象覆盖两种模式下 J1～J7 的普通目标和软件限位目标。
- 双臂通过 `robot.send_upper_angle` 覆盖两种模式下 J1～J7 正负 10°，不执行双臂软件限位。
- 每条关节用例在 `finally` 中调用 `device.go_zero()`；模块结束固定恢复双臂插补模式 `0`。
- 设置模式成功时业务返回值为 `1`；发送角度在插补模式下业务返回值为 `0`，刷新模式下为 `1`。
- Excel 成功用例共 112 条：刷新模式 56 条的 `expect_data=1`，插补模式 56 条的 `expect_data=0`。
- 角度回读使用 `assert_almost_equal(..., tol=TuyaRobotBase.angle_tolerance)`。
- 测试函数参数只保留实际需要的 fixture；能由 `upper_body` 完成的调用不额外传入 `device`。
- 不在测试函数中手写 `CommandResult` 分支，统一调用 `TuyaRobotBase.result_data()`。

## `send_upper_coord` 当前设计

- 只保留单臂测试，不保留双臂同时坐标运动用例。
- 左臂使用 `robot.left_arm.send_upper_coord`，右臂使用 `robot.right_arm.send_upper_coord`。
- 正常用例共 48 条：左右臂分别覆盖刷新模式 `1`、插补模式 `0` 下 X/Y/Z 正负 10 mm，以及 RX/RY/RZ 正负 10°。
- 异常用例覆盖速度 0、101，坐标轴 ID 0、7，以及六个坐标轴上下限外 1。
- 当前 SDK 单臂坐标校验范围与仓库实机范围不完全一致；异常数据按 SDK 范围生成：X/Y `±801`、Z `-801/651`、RX/RY/RZ `±181`，确保不会误下发真机。
- 每条用例先调用 `device.move_to_coord_initial_pose()`，进入并校验已确认的坐标初始姿态，再设置并回读目标手臂模式。
- 每条正常用例在 `finally` 中调用 `device.go_zero()`；模块结束固定恢复双臂插补模式 `0`。
- 设置模式成功时业务返回值为 `1`；发送坐标在插补模式下业务返回值为 `0`，刷新模式下为 `1`。
- Excel 正常用例共 48 条：刷新模式 24 条的 `expect_data=1`，插补模式 24 条的 `expect_data=0`；32 条异常参数已全部通过 SDK 本地静态校验。

## `send_upper_angles` 与 `send_upper_coords` 已确认目标

- 两个接口均使用 3 组已由用户和开发确认的左右臂目标，分别按低速 `10`、中速 `50`、高速 `100` 执行。
- 每组目标覆盖左臂、右臂和双臂同时运动，并分别覆盖插补模式 `0` 与刷新模式 `1`；每个接口均为 18 条正常用例。
- `send_upper_angles` 的夹爪速度固定为 `0`，对应用户提供调用中省略夹爪速度时的 SDK 默认值。
- 已确认坐标包含左臂 `Z=-464.0` 和右臂 `Z=-511.5`；当前 SDK 坐标范围为 X `[-650, 650]`、Y `[-841, 841]`、Z `[-636, 665]`、RX/RY/RZ `[-180, 180]`。
- `send_upper_coords` 的 Z 轴下限异常值已由过时的 `-351` 修正为 SDK 范围外 1 的 `-801`。
- `send_upper_coords` 每条正常用例结束后均在 `finally` 中调用 `device.go_zero()`，不再恢复到运动前坐标，确保成功或失败时最终回到双臂零位。

## `upper_jog_angle` 当前设计

- 正常运动共 42 条：左臂、右臂和双臂分别覆盖 J1～J7 的正向、负向 Jog，到对应软件限位后回读角度。
- 每条运动用例先设置双臂插补模式 `0` 并调用 `device.go_zero()`；Jog 以 `_async=True` 下发，随后用带超时的状态查询等待停止。
- Jog 到软件限位后自行停止；完成角度回读后，每条用例的 `finally` 直接调用 `device.go_zero()`，不额外调用 `upper_stop()`，避免停止状态帧干扰后续回零闭环。
- 软件限位运动统一使用低速 `10`，并保留 `motion + manual + danger` 门控。
- 刷新模式 `1` 不支持连续 Jog 与步进 Jog；四个 Jog 接口各保留 1 条左臂调用验证：返回失败 `CommandResult`（提示切换插补模式）；结束后恢复插补模式并回零。
- 非法参数共 15 条：速度 `0、101`、关节 ID `0`、方向 `-1、2` 分别覆盖左臂、右臂和双臂，已通过 SDK validation 静态验证。
- 当前 SDK 对 Jog / 关节步进的 `joint_id=0`：单臂抛出 `TuyaRobotSingleArmDataException`，双臂抛出 `TuyaRobotDualArmDataException`，测试按入口分别断言。

## `upper_jog_angle_increment` 当前设计

- 正常运动共 21 条：左臂、右臂和双臂分别覆盖 J1～J7，每条从零位执行单关节 30° 步进；J4 使用安全的 `-30°`，其他关节使用 `30°`。
- 正常步进使用 `_async=False` 同步闭环，接口业务返回值按插补模式断言为 `0`；完成后回读目标关节角度，并在 `finally` 中调用 `device.go_zero()`。
- 增量超限共 42 条：各关节完整行程按 `|负限位| + |正限位|` 计算，再使用正负 `完整行程+1°`，分别覆盖左臂、右臂和双臂。
- 超限数据通过公开接口正常调用，不在用例内增加 SDK 预校验、跳过或协议编码规避，并启用 `motion + manual + danger`；无论调用结果如何，`finally` 均执行双臂回零。
- 当前 SDK 不校验增量幅度；J1/J3/J5 的 `±333°` 超出协议 `int16 × 0.01°` 的 `±327.67°` 编码范围，该问题由用户另行提交 SDK Bug。
- 速度 `0、101` 和关节 ID `0` 共 9 条，分别覆盖左臂、右臂和双臂，已通过 SDK validation 静态验证。
- 另保留 1 条左臂刷新模式步进验证：返回失败 `CommandResult`（提示切换插补模式），结束后恢复插补并回零。

## `upper_jog_coord` 与 `upper_jog_coord_increment` 当前设计

- `TuyaRobotBase.move_to_coord_initial_pose()` 现支持可选 `arm_side`：无参时移动并校验双臂，传入 `left` 或 `right` 时只移动并校验目标单臂。
- `upper_jog_coord` 正常运动共 26 条：左右单臂分别覆盖六轴正负向，双臂只覆盖 Z 轴正负向。
- 坐标 Jog 不断言软件限位；使用 `_async=False` 持续运动。结束态以 Excel 与实机为准：业务返回 `0` 的用例只断言返回值；失败 `CommandResult` 分别断言 `status_code=32`（“坐标无解”）或 `33`（“直线运动无相邻解”），后者随后读取停止坐标并回零。
- `upper_jog_coord` 另保留 1 条刷新模式失败 `CommandResult` 验证，以及 18 条左右单臂/双臂速度、坐标轴 ID、方向非法参数。
- `upper_jog_coord_increment` 正常运动共 13 条：左右单臂分别覆盖六轴步进 30 mm/30°，双臂只覆盖 Z 轴步进 30 mm；使用同步闭环、回读增量结果，并在 `finally` 中回零。
- `upper_jog_coord_increment` 另保留 1 条左臂刷新模式步进验证：返回失败 `CommandResult`（提示切换插补模式）。
- 坐标步进超限共 36 条，按 `|负限位| + |正限位| + 1` 生成正负值并通过公开接口正常调用；另有 12 条速度和坐标轴 ID 基础异常。
- 当前 SDK 不校验坐标增量幅度，RX/RY/RZ 的 `±361°` 还超过协议编码范围；该问题由用户另行提交 SDK Bug，用例不增加跳过或预拦截。

## `TuyaRobotBase` 中的运动常量和方法

以下跨用例数据和动作统一放在 `settings.py` 的 `TuyaRobotBase` 中，测试文件不得重复硬编码：

- `speed = 20`
- `angle_tolerance = 0.1`
- `coord_tolerance = 0.1`
- 上半身零位角度和关节软件限位。
- 坐标软件限位 `UPPER_BODY_COORD_SOFT_LIMITS`。
- 坐标运动初始角度：
  - 左臂：`[-89.99, 39.99, 0.0, -100.0, 0.0, 0.0, 0.02, 0.0]`
  - 右臂：`[90.0, 39.99, 0.0, -100.0, 0.03, 0.0, 0.0, 0.0]`
- 对应的坐标初始姿态：
  - 左臂：`[519.5, 93.5, -6.5, 97.77, 9.13, -49.37]`
  - 右臂：`[519.5, -93.5, -6.5, -97.74, 9.16, 49.37]`
- `result_data()`：统一取得接口业务数据。
- `wait_upper()`：有超时的上半身运动等待。
- `go_zero()`：双臂整臂回零。
- `go_arm_zero()`：指定单臂整臂回零。
- `move_to_coord_initial_pose(arm_side=None)`：无参时双臂进入坐标初始角度；传入 `left` 或 `right` 时只移动目标臂，并按坐标容差回读验证。

## 主要文件

- `AGENTS.md`
- `.cursorrules`
- `.cursor/skills/tuya-pytest-case-authoring/SKILL.md`
- `.cursor/skills/tuya-pytest-registry-session/SKILL.md`
- `.cursor/skills/tuya-motion-test-authoring/SKILL.md`
- `README.md`
- `settings.py`
- `testcases/upper_body/conftest.py`
- `test_data/upper_body.xlsx`
- `testcases/upper_body/test_send_upper_angle.py`
- `testcases/upper_body/test_send_upper_coord.py`
- 其余 8 个上半身运动接口测试文件。
- `docs/MOTION_TEST_PLAN.md`

## 下一会话建议

1. 以已经整理完成的 `send_upper_angle` 和 `send_upper_coord` 为模板，逐个修改其余运动接口，禁止批量套用未经核对的恢复逻辑。
2. 每修改一个接口，同时核对测试文件、Excel Sheet、异常类型、Allure 中文描述和恢复时机。
3. 普通接口按接口结束统一恢复；`send_upper_angle` 和 `send_upper_coord` 按已确认的安全例外在每条运动用例后回零。
4. 坐标运动仍必须在每次运动前进入已确认的坐标初始姿态；这属于前置动作，不等同于结束回零。
5. 未确认的绝对目标、避碰姿态或大范围组合运动不得猜值；保留空值并显式跳过。
6. 修改后只运行编译和收集验证；真机执行必须再次取得用户明确授权。

## 真机安全门控

- 普通真机测试需要显式启用 `--run-hardware`。
- 运动测试还需要 `--run-motion`。
- manual、danger、firmware marker 存在时必须分别启用相应参数。
- 首次实机运动应单条、低速、有人监护并可随时急停。
- 禁止无超时等待、并发连接同一设备或吞掉清理异常。

## 工作区状态

工作区当前存在大量未提交修改和新增文件，部分修改早于本次运动接口工作。后续处理时：

- 不使用 `git reset --hard`、`git checkout --` 或批量覆盖。
- 不删除或回退无法确认归属的用户修改。
- 提交前按文件逐项审查，只纳入明确属于目标范围的变更。
