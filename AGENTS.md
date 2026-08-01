# TuyaRobot pytest 仓库规则

## 项目边界

- 本仓库使用 `pytest`、`allure-pytest` 和 `openpyxl` 对 TuyaRobot 真机接口进行 Excel 驱动测试。
- 测试范围为 `testcases/robot`、`testcases/upper_body`、`testcases/chassis`。
- 不引入其他仓库的 `arms.json`、`arm_registry.py` 或按 arm id 选臂流程。
- 对用户说明、测试日志、注释和仓库文档优先使用简体中文。

## 目录职责

- `testcases/`：单 API 或单一紧密场景的测试；只使用 pytest fixture，不自行创建或关闭设备连接。
- `test_data/`：三类测试 Excel；sheet 名与接口主题一致，首行为字段名。
- `common1/`：日志、Excel 读取等通用能力。
- `settings.py`：连接配置、环境变量、Excel 路径、运动零位/软件限位常量、`TuyaRobotBase`、公共回零/默认恢复动作和有超时的等待逻辑。
- 根 `conftest.py`：pytest CLI、配置合并、session 设备、子系统 fixture、marker 和安全门控。
- `pytest.ini`：测试根目录、导入模式和 marker 注册。

## 测试骨架

- 使用 `get_test_data_from_excel` 和 Excel 参数化。
- 测试接口的调用、等待、断言和恢复流程直接写在对应测试函数内，不使用 `_run_*`、Executor、Adapter 等方式封装主流程。
- 只有接口存在需要多次复用的独特测试动作（例如固定执行 1°、0.1° 的小步运动）时才考虑提取公共方法；创建任何测试公共方法前必须先得到用户明确确认。
- Excel 用例 `ID` 使用从 1 开始的连续纯数字，不添加接口缩写前缀。
- `title` 直接描述实际验证功能和关键参数，例如“设置J1运动到10度”“设置J1运动到-167度，验证角度超限”“设置左右臂J1依次运动到软件下限-166度”；软件限位不得写成机械硬限位。
- normal、exception、manual 等用例分类完全以 Excel 的 `test_type` 为准；禁止在测试代码中根据角度、限位或其他参数再次推断、覆盖或兜底重分类。
- `@pytest.mark.parametrize` 保持单行，ids 使用 `lambda c: c["title"]`。
- 保留已有函数名、fixture、marker、调用顺序、断言语义、skip 条件和恢复逻辑。
- 每条用例包含开始、通过、完成日志；开始日志后记录 `test_api` 和真实 API 入参。
- API 调用、前置检查、断言和恢复动作使用语义明确的 `allure.step`。
- Allure 的 `feature`、`story`、`step` 和附件名称使用简体中文描述实际功能；API 标识符可作为中文描述的一部分保留，不得直接使用 `UpperBody`、函数名等英文标识充当展示标题。
- 仅在读取 `expect_data` 且有可比较实际值时定义 `expected`，并在最终值断言步骤附加期望值和实际值。
- `expect_data` 始终表示接口业务数据；左臂、右臂和整臂接口统一通过 `device.result_data(result)` 兼容直接返回与 `CommandResult`，再与期望值比较。不得在测试文件重复编写 `isinstance(result, CommandResult)` 分支，也不得为不同 `plain_return` 模式重复创建期望列；只有专门验证失败状态契约时才增加 `status_code`、`message` 或 `blocked_by` 等期望字段。
- 普通设置接口执行成功时业务返回值按 `1` 断言；运动发送接口按运动模式断言，插补模式 `0` 返回 `0`，刷新模式 `1` 返回 `1`。查询接口按实际查询数据断言。
- 先断言类型和结构，再断言业务值；运动角度和坐标回读统一使用 `assert_almost_equal`。
- setter 先读取原值，并用 `try/finally` 恢复；双臂状态按左右臂原值分别恢复。
- 异常用例使用 SDK 具体异常，通过 `pytest.raises(...) as exc` 捕获，并在块结束后记录 `exc.value`。

## 连接与 fixture

- 根 `conftest.py` 创建唯一的 session 级 `TuyaRobotBase`，会话结束统一关闭。
- 按需使用 `robot`、`upper_body`、`left_arm`、`right_arm`、`head`、`chassis` fixture。
- `head` 或 `chassis` 未启用时由 fixture 跳过；测试不得绕过检查自行连接。
- CLI 显式值覆盖环境变量，环境变量覆盖 `TuyaConnectionConfig` 默认值。
- 新增连接字段时同步更新 dataclass、`from_env()`、pytest CLI 和 `_connection_config()`。
- `testcases/upper_body/conftest.py` 使用 function 级自动 fixture，每条上半身测试执行前检查双臂状态，未全部上电时执行上电并在 30 秒内确认；不得新建设备连接。测试文件不得重复编写上电状态检查。
- 除上述上半身公共前置上电外，接口专属校准、初始化和恢复逻辑留在对应测试文件，不加入 session fixture。

## 实机安全

- `testcases/` 用例由 collection 自动标记为 `hardware`；常规验证不得主动开启真机门控。
- 真机执行必须得到用户明确授权，并显式启用所需的 `--run-hardware`、`--run-motion`、`--run-manual`、`--run-danger`、`--run-firmware`。
- 多个安全 marker 同时存在时分别启用；`reset` 不是执行门控。
- 禁止无超时等待、盲目并发连接同一设备、伪造硬件能力或吞掉清理异常。
- 运动方案未得到用户明确确认前，不得创建测试文件或修改 Excel。
- URDF、DH 和单轴软限位不能单独证明双臂姿态无自碰；未确认的避让姿态、完整角度和绝对坐标必须留空并显式 `pytest.skip`，禁止猜值或补零。
- Jog 方向固定为 `0` 负向、`1` 正向；关节 Jog 只覆盖文档支持的 J1～J7，并分别测试左臂、右臂和双臂。
- `upper_jog_angle` 每条运动用例先设置双臂插补模式 `0` 并调用 `device.go_zero()`；Jog 自行运动到软件限位并停止，回读确认限位后在 `finally` 中直接回零，不额外调用 `upper_stop()`。到软件限位的用例同时标记 `motion`、`manual`、`danger`。刷新模式 `1` 不支持 Jog；`upper_jog_angle`、`upper_jog_coord`、`upper_jog_angle_increment`、`upper_jog_coord_increment` 各保留一条返回失败 `CommandResult`（提示切换插补模式）的验证，并在结束后恢复插补模式后回零。
- `upper_jog_angle_increment` 分别覆盖左臂、右臂和双臂 J1～J7；每条正常用例从零位执行单关节 30° 步进，J4 使用安全的 `-30°`，回读后在 `finally` 中回零。增量超限值按 `|负限位| + |正限位| + 1°` 生成正负值，按公开接口正常下发，并同时标记 `motion`、`manual`、`danger`；不得在用例中为当前 SDK 缺少幅度校验增加跳过或预拦截。
- `upper_jog_coord` 的单臂正常用例分别覆盖六个坐标轴正负向，双臂正常用例只覆盖 Z 轴正负向；单臂仅将目标臂移动到坐标初始点位，双臂移动双臂。结束态以 Excel 为准：业务返回 `0` 的用例只断言返回值；失败 `CommandResult` 按实机分别断言 `32`“坐标无解”或 `33`“直线运动无相邻解”，后者读取停止位置后在 `finally` 中回零；不按坐标软件限位断言。
- `upper_jog_coord_increment` 的单臂正常用例分别覆盖六个坐标轴步进 30 mm/30°，双臂正常用例只覆盖 Z 轴步进 30 mm；单臂仅移动目标臂到坐标初始点位，双臂移动双臂，回读后在 `finally` 中回零。超限值按各坐标轴 `|负限位| + |正限位| + 1` 生成正负值，按公开接口正常下发并启用 `motion`、`manual`、`danger`，不增加 SDK 幅度校验规避逻辑。
- 已确认的零位角度、关节/坐标软件限位等跨用例运动常量统一定义为 `TuyaRobotBase` 类属性，测试文件只引用，不重复硬编码。
- 坐标运动初始关节姿态统一定义为 `TuyaRobotBase.COORD_MOTION_INITIAL_ANGLES`；双臂坐标运动调用 `device.move_to_coord_initial_pose()`，单臂坐标 Jog/步进调用 `device.move_to_coord_initial_pose(arm_side)` 只移动目标臂，并等待到位；不得在 Excel 或测试文件重复维护该姿态。
- 坐标运动初始坐标统一定义为 `TuyaRobotBase.COORD_MOTION_INITIAL_COORDS`，`move_to_coord_initial_pose()` 必须回读并校验左右臂 6 轴坐标。`send_upper_coord` 只测试单臂：左右臂分别覆盖刷新模式 `1`、插补模式 `0` 下 X/Y/Z `±10 mm` 和 RX/RY/RZ `±10°`；每条用例先进入坐标初始姿态，再设置并回读模式，最后发送坐标，并在 `finally` 中调用 `device.go_zero()`。模块结束固定恢复双臂插补模式 `0`，不保留双臂同时运动用例。
- `TuyaRobotBase.speed` 为公共恢复/回零速度；整臂回零等公共恢复动作统一引用该类属性，测试文件不得硬编码速度值。
- 双臂整臂回零统一调用 `TuyaRobotBase.go_zero()`；该封装使用已确认的零位关节角度和 `send_upper_angles` 下发，不调用 SDK `upper_go_zero()`。设置参数后的公共默认恢复动作也封装为 `TuyaRobotBase` 方法，测试文件只保留调用时机和 `try/finally` 或 fixture 流程，不重复实现恢复细节。
- `TuyaRobotBase.angle_tolerance` 和 `TuyaRobotBase.coord_tolerance` 分别为角度、坐标回读容差，当前均为 `0.1`；Excel 的 `expect_data` 只用于断言被测接口返回值。
- 所有切换到刷新模式 `1` 后再下发运动的用例，必须在模式回读后显式调用并断言 `set_upper_motion_async(True)`；插补模式 `0` 显式设为 `False`，清理时恢复原默认异步状态或模块约定的插补同步状态。`send_upper_angle` 左右单臂分别覆盖 J1～J7，双臂使用 `robot.send_upper_angle` 覆盖 J1～J7 正负 10°，单臂软件限位覆盖两种模式但双臂不执行软件限位。每条关节用例在 `finally` 中调用 `device.go_zero()`，模块结束固定恢复双臂插补模式 `0`。
- 运动速度合法值至少覆盖 1、10、20、100，非法值覆盖 0、101；高速不得用于未确认的大范围边界运动。
- 文档契约与 SDK 实际异常不一致时分别记录，按 SDK 当前具体异常断言，不得用宽泛 `Exception` 掩盖差异。

## 验证

- 修改测试后运行 `python -m compileall -q testcases`。
- 修改测试、Excel、fixture 或连接配置后运行 `pytest testcases --collect-only -q`。
- 当前基线为 120 个测试文件、157 个测试函数、1020 条参数化测试；有意改变收集范围时同步更新规则和技能。
- 修改连接或会话参数后运行 `pytest --help`。
- 不在常规验证中运行真实硬件测试。

## 仓库技能

- 编写或重构 Excel 用例时，完整读取并遵守 `.cursor/skills/tuya-pytest-case-authoring/SKILL.md`。
- 修改连接配置、pytest 会话、fixture 或安全门控时，完整读取并遵守 `.cursor/skills/tuya-pytest-registry-session/SKILL.md`。
- 编写关节、坐标、Jog、增量、软限位或避碰用例时，完整读取并遵守 `.cursor/skills/tuya-motion-test-authoring/SKILL.md`。
- `AGENTS.md` 和 `.cursorrules` 定义全仓库强制约束；具体步骤以对应技能为准。
