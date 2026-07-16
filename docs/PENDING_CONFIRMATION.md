# TuyaRobot 自动化接口进度与剩余确认项

更新时间：2026-07-15

## 当前进度

- 已建立 109 个接口测试文件：整机 2、上半身 69、底盘 38。
- 109 个 Python 文件与 109 个 Excel Sheet 一一对应。
- 当前共收集 149 条 pytest 用例。
- 未执行真机测试；本轮完成代码、Excel 数据、接口签名和 pytest 收集验证。

## 已按批注完成

- 上半身上下电、暂停、恢复、停止和无错误状态清除。
- 关节使能、抱闸和零位标定；标定前分两次弹窗确认放松关节和对准零位刻度线，结束后恢复抱闸和使能。
- 最大/最小角度、模型方向的设置测试；先保存现场值并在 `finally` 中恢复，限位设置使用 `persist=False`。
- 碰撞模式、VR 模式、滤波长度的设置—读取—原值恢复。
- 拖动示教录制、暂停、清空、播放、多轨迹录制/播放；录制时长为 5 秒，低于 2 分钟限制。
- 动力学辨识运行前弹窗提示确认安全区域。
- 吊装底盘的低速轮毂运动、停止、使能、刹车、升降、升降标定和 LED 设置。
- 底盘 LED 测试结束后恢复绿色。
- 上半身和底盘错误清除目前只验证无错误状态调用。
- 逆运动学使用运行时读取的当前双臂坐标，不产生运动。

## 仍暂缓的接口

### 1. 等待机械臂安全运动点

- `send_upper_angles`、`send_upper_angle`
- `upper_jog_angle`、`upper_jog_angle_increment`
- `send_upper_coords`、`write_upper_coords`
- `send_upper_coord`、`write_upper_coord`
- `upper_jog_coord`、`upper_jog_coord_increment`
- `upper_write_mov_c`

这些接口等左右臂安全测试点更新后再补；届时统一增加 `motion + danger`，执行后停止并回零。

### 2. 当前 SDK 无法可靠验证碰撞阈值

`Arm.get_upper_collision_threshold()` 在当前本地 `pytuyarobot 1.0.3` 中直接调用 `get_upper_collision_mode()`，因此无法证明读回的是阈值，也无法保证恢复正确的阈值。暂不生成 `set_upper_collision_threshold` 真机用例，建议先修正 SDK 查询实现或确认协议返回结构。

### 3. 夹爪参数协议不完整

`set_gripper_param(...)` 仍缺少每个字节的具体含义、长度和合法范围；SDK 会直接按单字节截断。按批注意见暂不填充。

### 4. 安全等级缺少可读取的原值

`set_upper_safety_level` 没有对应 Getter。文档示例中的 `0` 不能证明是现场默认值，而且安全 bit mask 设置错误可能关闭保护，因此未使用猜测值做恢复。需要明确默认安全等级后再补。

### 5. 固件升级

`agv_firmware_flash` 按批注意见暂不测试，不进入普通回归。

## 安全开关

- 所有真机接口都需要 `--run-hardware`。
- 真实运动还需要 `--run-motion`。
- 标定、抱闸、上下电和参数修改还需要 `--run-danger`。
- 弹窗确认测试还需要 `--run-manual`。

多个标记必须同时满足才会执行。例如动力学辨识需要：

```powershell
pytest testcases/upper_body/test_upper_run_dynamic_identify_traj.py `
  --run-hardware --run-motion --run-danger --run-manual
```
