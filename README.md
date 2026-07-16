# TuyaRobot Pytest

基于 `pytuyarobot` 的整机自动化测试框架。测试资产按整机、上半身和底盘三个业务域组织，并沿用 450 框架的 Excel 参数化方式。

## 目录

- `testcases/robot`：整机接口测试。
- `testcases/upper_body`：上半身、左右臂和头部测试。
- `testcases/chassis`：底盘和升降机构测试。
- `test_data/*.xlsx`：与接口测试文件一一对应的 Excel Sheet。
- `conftest.py`：只管理整机连接和各子设备 Fixture。
- 每个测试文件显式维护接口前置条件、断言和 `finally` 恢复逻辑。
- `qt_platform`：TuyaRobot 图形化测试启动器。
- `docs/PENDING_CONFIRMATION.md`：高风险或协议不明确接口的待确认事项。

## 配置

连接参数可通过 pytest 参数或环境变量覆盖，环境变量示例见 `.env.example`。

```powershell
pytest --collect-only
pytest --run-hardware --tuya-ip 192.168.1.232
pytest testcases/chassis --run-hardware
pytest testcases/upper_body --run-hardware --connect-head
```

未传入 `--run-hardware` 时，所有真机测试都会跳过。运动、人工确认、高风险和固件测试还需要分别增加对应开关，例如：

```powershell
pytest testcases/upper_body --run-hardware --run-danger
pytest testcases/chassis --run-hardware --run-motion
```

## 启动方式

```powershell
python main.py --module robot --allure --run-hardware
python -m qt_platform
```

成功执行测试后，可按需使用 Allure CLI 生成报告：

```powershell
allure generate allure-results -o allure-report --clean
```
