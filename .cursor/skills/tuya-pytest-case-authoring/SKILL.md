---
name: tuya-pytest-case-authoring
description: >-
  Author and refactor Excel-driven TuyaRobot pytest cases in testcases/robot,
  testcases/upper_body, and testcases/chassis. Use for test skeletons, Excel
  sheets, parametrization, Allure steps and attachments, API parameter logs,
  normal/exception cases, state restoration, hardware markers, or fixture
  selection in this repository.
---

# TuyaRobot pytest 用例编写

## 先确认上下文

| 目录 | 数据文件 | 主 fixture | 可选 fixture |
|---|---|---|---|
| `testcases/robot` | `TuyaRobotBase.ROBOT_TEST_DATA_FILE` | `robot` | - |
| `testcases/upper_body` | `TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE` | `upper_body` | `left_arm`、`right_arm`、`head` |
| `testcases/chassis` | `TuyaRobotBase.CHASSIS_TEST_DATA_FILE` | `chassis` | - |

根 `conftest.py` 创建 session 级 `TuyaRobotBase`，各 fixture 只返回其子系统。复用现有 fixture，不在测试文件中自行连接或关闭设备。

## 读取 Excel

- 用 `get_test_data_from_excel(file, sheet_name)`；sheet 名与被测接口主题一致。
- Excel 首行是字段名，空行会跳过；需要防止表结构漂移时传 `required_columns`。
- 用例 `ID` 使用从 1 开始的连续纯数字，不添加 `SUA`、`UJA` 等接口缩写前缀。
- `title` 直接写实际验证功能和关键参数，不复述 ID 或 API 名；例如“设置J1运动到10度”“设置J1运动到-151度，验证角度超限”“设置左右臂J1依次运动到软件下限-150度”。软件限位不得称为机械硬限位。
- 参数化装饰器保持单行，固定写成 `@pytest.mark.parametrize("case", ..., ids=lambda c: c["title"])`。
- 仅在现有数据包含 `test_type` 时拆分 normal/exception；不要擅自改变收集范围。
- normal、exception、manual 等分类只读取 Excel 的 `test_type`；不要在测试代码中根据角度、限位或其他参数增加识别函数、兜底分类或覆盖分类。

```python
cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "get_upper_main_version",
)

normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]
```

## 使用统一骨架

以 `testcases/upper_body/test_get_upper_main_version.py` 为结构参考：

```python
# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, "sheet_name")


@allure.feature("UpperBody")
@allure.story("api_name")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_api_name(upper_body, case):
    title = case["title"]
    expected = case["expect_data"]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'axis:{case["axis"]}')

    with allure.step(f'调用 {case["api"]} 接口'):
        actual = upper_body.api_name(case["axis"])
        logger.debug(f"接口返回：{actual}")

    with allure.step("断言接口返回结果"):
        allure.attach(str(expected), name="期望值", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(actual), name="实际值", attachment_type=allure.attachment_type.TEXT)
        assert actual == expected

    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
```

执行时遵守：

- 将接口调用、等待、断言和恢复流程直接写在对应测试函数内，不创建 `_run_*`、Executor、Adapter 等主流程封装。
- 只有接口存在需要多次复用的独特测试动作（例如固定执行 1°、0.1° 的小步运动）时才考虑公共方法；提取任何测试公共方法前先取得用户明确确认。
- 保留现有函数名、fixture、接口调用顺序、marker 和断言语义。
- 开始日志后记录 `case["api"]`，并用逐项 f-string 记录所有真实传入 API 的 case 字段；不记录 `title`、`expect_data`、`test_type`。
- 把前置检查、每次 API 调用、断言及恢复动作放入含义明确的 `allure.step`。
- `allure.feature`、`allure.story`、`allure.step` 和附件名称使用简体中文描述实际验证功能。API 名可以作为中文句子的一部分保留，但不要直接使用 `UpperBody`、SDK 函数名等英文标识作为 Allure 展示标题。
- 仅当用例读取 `expect_data` 且有可比较的实际值时定义 `expected`，并在最终值断言步骤附加期望值与实际值；纯结构/类型检查不伪造附件。
- `expect_data` 始终表示接口业务数据。左臂、右臂和整臂接口都通过 `device.result_data(result)` 统一提取业务数据：`CommandResult` 失败由该方法报错，成功返回 `.data`，直接返回模式原样返回。测试文件不要重复编写 `CommandResult` 分支，也不要为不同 `plain_return` 模式重复创建期望列；只有专门测试失败状态契约时，才增加 `status_code`、`message`、`blocked_by` 等期望字段。
- 普通设置接口成功时 `expect_data` 使用 `1`；模式前置 setter 的业务返回值同样断言为 `1`。运动发送接口的 `expect_data` 跟随模式：插补模式 `0` 使用 `0`，刷新模式 `1` 使用 `1`。查询接口继续断言其真实查询数据。
- 返回值先检查类型和结构，再检查业务值。浮点边界使用 `pytest.approx`；保留已有复杂结构断言。
- 最后保留“测试通过”和“测试完成”日志。

## 状态修改与运动用例

涉及关节、坐标、Jog、增量、软限位或双臂避碰时，还必须完整读取并遵守
`.cursor/skills/tuya-motion-test-authoring/SKILL.md`；运动方案未经用户明确确认不得落代码或 Excel。

- setter 先读取原值，在 `try` 中修改、回读并断言，在 `finally` 中恢复原值。
- 双臂聚合状态需分别通过 `left_arm`、`right_arm` 恢复时，保留两个 fixture 和左右臂各自原值。
- 上半身测试的上电检查与按需上电统一由 `testcases/upper_body/conftest.py` 的 function 级自动 fixture 完成；测试文件不得重复调用 `is_upper_powered_on()` 检查前置上电状态。
- 底盘操作沿用对应上电状态检查，不统一套用上半身规则。
- 等待上半身停止使用 `device.wait_upper(timeout=...)`；禁止无超时忙等。
- 已确认的零位角度、关节/坐标软件限位等跨用例常量定义为 `TuyaRobotBase` 类属性，测试文件通过该类复用；公共恢复/回零速度引用 `TuyaRobotBase.speed`，当前值为 `20`。
- 保留语义 marker：`smoke`、`motion`、`manual`、`danger`、`firmware`、`reset`。根 `conftest.py` 会自动为 `testcases/` 添加 `hardware`。

## 异常用例

使用当前 SDK 的具体异常类型：底盘为 `TuyaRobotChassisDataException`，双臂为 `TuyaRobotDualArmDataException`。捕获后记录 `exc.value`：

```python
with pytest.raises(TuyaRobotDualArmDataException) as exc:
    with allure.step(f'调用 {case["api"]} 接口'):
        upper_body.some_api(case["state"])
logger.info("✅ 异常断言通过,异常信息：%s", exc.value)
```

不要用宽泛 `Exception` 代替 SDK 异常，也不要在 `raises` 块内部读取 `exc.value`。

## 验证

1. 运行 `python -m compileall -q testcases`。
2. 运行 `pytest testcases --collect-only -q`，确认无连接硬件即可收集。
3. 当前数据基线为 120 个测试文件、157 个测试函数、1019 条参数化测试；有意修改 Excel 后同步更新基线。
4. 真机执行必须显式启用根 `conftest.py` 定义的安全开关；不要在普通验证中运行硬件用例。
