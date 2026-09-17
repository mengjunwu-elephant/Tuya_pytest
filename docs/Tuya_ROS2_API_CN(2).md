# Tuya ROS2 API 中文使用说明

## 目录

- [文档说明](#overview)
  - [接口阅读约定](#reading)
  - [Service 通用返回字段](#service-return)
- [必要启动步骤](#startup)
  - [每个终端加载环境](#startup-environment)
  - [启动整机运动与系统节点](#startup-robot)
  - [按需启动感知节点](#startup-sensors)
  - [检查接口是否已注册](#startup-check)
- [日志管理](#logs)
  - [日志根目录](#log-root)
  - [日志路径](#log-paths)
  - [常用查看命令](#log-commands)
  - [容量与清理](#log-cleanup)
- [头部接口说明](#head)
  - [使用约定](#head-conventions)
  - [常用观测命令](#head-observe)
  - [接口列表](#api-head)
- [底盘接口说明](#chassis)
  - [使用约定](#chassis-conventions)
  - [常用观测命令](#chassis-observe)
  - [接口列表](#api-chassis)
- [上半身接口说明](#upper)
  - [使用约定](#upper-conventions)
  - [常用观测命令](#upper-observe)
  - [接口列表](#api-upper)
- [感知接口说明](#sensors)
  - [使用约定](#sensors-conventions)
  - [接口列表](#api-sensors)
- [系统接口说明](#system)
  - [使用约定](#system-conventions)
  - [接口列表](#api-system)
- [日志轮转限制说明](#log-retention-limit)
- [常见问题与故障排查](#troubleshooting)
  - [连接异常](#troubleshooting-connection)
  - [底盘无法使能轮毂](#troubleshooting-wheel)
- [更新日志](#changelog)

<a id="overview"></a>
## 文档说明

本文档汇总 Tuya Robot 的 ROS2 头部、底盘、上半身、感知和系统接口，用于真机联调、测试和 ROS2 接口调用。内容包括接口类型、ROS 名称、消息/服务类型、参数说明和 Real 示例。

- 运动接口首次验证请使用低速、小幅度目标，并确保急停、限位及工作空间安全。
- 本文 Real 示例默认已完成 ROS2 工作空间构建并安装匹配版本的 `pytuyarobot` Python 包。
- `robot.launch.py`的感知模块默认关闭，可通过对应`enable_*`参数启用；也可另开终端独立启动。
- D435/D435I 三机接口采用 `agv`、`abdomen`、`head` 三个固定角色命名。

<a id="reading"></a>
### 接口阅读约定

- **作用域**：由 ROS 名首段确定；`/left_arm`、`/right_arm`、`/upper` 分别表示左臂、右臂和双臂，`/head`、`/chassis`、`/system` 对应各子系统。
- **QoS**：状态 Topic 使用 BEST_EFFORT，控制 Topic 使用 RELIABLE，Service 使用 ROS 2 默认 Reliable；个别接口差异会单独说明。
- **Mock/Real**：示例均按 Real 编写。`mock.launch.py` 只启动头部、底盘和上半身组合运动节点，不启动 `system_manager` 与感知节点。
- **安全**：运动、上电、抱闸、校准、固件和动画接口执行前必须确认工作空间安全；只读接口不再逐条重复安全声明。
- **参数范围**：每个有请求参数的接口均在接口条目内列明取值范围。Topic 发布频率不等于底层采样频率。

<a id="service-return"></a>
### Service 通用返回字段

| 字段 | 说明 |
|---|---|
| `success` | `true` 表示调用成功，`false` 表示参数、连接、设备状态或执行过程异常。 |
| `message` | 成功时通常为空；失败时返回可读错误信息。 |
| `response_time_ms` | 单次调用耗时，单位毫秒；`0.0` 表示未计量。绝大多数 Service 的 Response 以 `success`、`message` 开头，并以本字段结尾。 |

各 Service 的“返回/观测”按对应 `.srv` Response 字段顺序列出。 `diagnostics` 已从绝大多数 Service 删除；仅 `GetBootSoundInfo`、`RestoreBootSound`、`SendUpperAngle` 仍保留该字段。

<a id="startup"></a>
## 必要启动步骤

<a id="startup-environment"></a>
### 1. 每个终端加载环境

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
```

<a id="startup-robot"></a>
### 2. 启动整机运动与系统节点

```bash
# Before：启动之前确认上半身和头部TCP是否正常，底盘是否正常通信
nc -zvw 3 192.168.0.232 6500  # 上半身
nc -zvw 3 192.168.0.231 6501  # 头部
fuser -v /dev/tuya_chassis    # 底盘 无输出即可

# Real：默认启动上半身、底盘、头部和 system_manager
ros2 launch tuyarobot_bringup robot.launch.py

# Mock：启动组合运动节点；不含 system_manager 和感知
ros2 launch tuyarobot_bringup mock.launch.py
```

#### `robot.launch.py` 启动参数选择

这里列出子系统启停、启动上电、头部自动连接和底层调试日志相关参数：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `enable_upper` | `true` | 是否启动 `upper_controllers_node`。设为 `false` 时不启动上半身控制节点，也不会注册该节点提供的上半身 Topic 和 Service。 |
| `enable_chassis` | `true` | 是否启动 `base_controller_node`。设为 `false` 时不启动底盘控制节点，也不会注册该节点提供的底盘 Topic 和 Service。 |
| `enable_head` | `true` | 是否启动 `head_controller_node`。该参数只控制头部 ROS 节点是否启动，不等同于连接头部硬件。 |
| `enable_camera_2d` | `false` | 是否由`system_manager_node`启动并管理三路2D相机。 |
| `enable_camera_3d` | `false` | 是否由`system_manager_node`启动并管理三路3D相机。 |
| `enable_lslidar` | `false` | 是否由`system_manager_node`启动并管理雷达。 |
| `enable_vtn_wakeup` | `false` | 是否由`system_manager_node`启动并管理语音唤醒。 |
| `startup_auto_power_on` | `true` | 启动后依次查询底盘、上半身、头部上电状态；仅对确认未上电的已启用模块调用一次上电 Service，成功上电后间隔2秒再处理下一模块。查询失败、状态异常、超时或上电失败时停止后续上电。设为 `false` 时跳过上电流程，但仍在已启用节点就绪后执行版本检查。 |
| `upper_publish_hz` | `100.0` | 上半身 HAL 自动上报缓存采样与对外 Topic 发布频率，`1.0~100.0Hz`。`:=50` 与 `:=50.0` 均可。不改变 `_safety_snapshot`（固定 20Hz）和 `/diagnostics`。 |
| `head_publish_hz` | `100.0` | 头部 HAL 自动上报缓存采样与状态 Topic 发布频率，`1.0~100.0Hz`。`:=50` 与 `:=50.0` 均可。不改变 `_safety_snapshot`（固定 20Hz）。 |
| `chassis_publish_hz` | `100.0` | 底盘 HAL 缓存采样与状态 Topic 发布频率，`1.0~100.0Hz`；`:=50` 与 `:=50.0` 均可。底盘 20Hz 报告与 `_safety_snapshot` 保持 20Hz。 |
| `upper_auto_report_enabled` | `true` | 上半身自动上报目标态。`true`：启动 `set_upper_auto_report(1)` 并在缓存断流后恢复；`false`：启动 `set(0)`，外部 SDK 再开则压回 0。仅 launch 生效。 |
| `chassis_auto_report_enabled` | `true` | 底盘自动上报目标态。`true`：启动 `set_agv_auto_report(1)` 并守护；`false`：启动 `set(0)`，新帧或状态变 1 则压回 0。仅 launch 生效。 |
| `head_auto_report_enabled` | `true` | 头部自动上报目标态。`true`：SDK `auto_recover` 维持上报；`false`：启动 `set_head_auto_report(0)` 并压回。仅 launch 生效。 |
| `enable_head_auto_report_recording` | `true` | Real模式是否记录头部最近约60秒自动上报缓存；Mock模式不写盘。 |
| `enable_incident_capture` | `true` | 是否在底盘、上半身或头部故障上升沿后继续捕获自动上报；捕获时长由`incident_capture_window_s`控制，默认20秒。 |
| `sdk_debug` | `false` | 是否开启底层协议跟踪。设为 `true` 后输出详细通信信息，日志位于 `/home/tuya/tuya/logs/pytuyarobot/python_debug_YYYYMMDD.log`；排障结束后建议恢复为 `false`，避免持续产生大量日志。 |

参数在启动命令末尾使用 `参数名:=值` 传入。例如，下列配置启用上半身和头部节点、关闭底盘节点，并让头部自动连接，同时开启底层协议日志：

```bash
ros2 launch tuyarobot_bringup robot.launch.py \
  enable_upper:=true \
  enable_chassis:=false \
  enable_head:=true \
  sdk_debug:=true
```

<a id="startup-sensors"></a>
### 3. 按需启动感知节点

可在`robot.launch.py`中显式设置对应`enable_*:=true`，也可继续使用以下独立Launch：

```bash
# 雷达
ros2 launch tuyarobot_sensors lidar.launch.py

# 三路 2D 相机
ros2 launch tuyarobot_sensors rgb_cameras.launch.py

# 三路 D435/D435I；无参数读取 perception_config.yaml（空 SN 会失败）
rs-enumerate-devices -s  # 查看 D435 序列号
source /etc/profile.d/tuya-realsense-rsusb.sh
ros2 launch tuyarobot_sensors d435_cameras.launch.py

```

<a id="startup-check"></a>
### 4. 检查接口是否已注册

```bash
ros2 node list
ros2 topic list
ros2 service list
```

<a id="logs"></a>
## 日志管理

<a id="log-root"></a>
### 日志根目录

业务日志统一位于 `/home/tuya/tuya/logs`，ROS 2启动与节点日志位于 `/home/tuya/.ros/log`。

<a id="log-paths"></a>
### 日志路径

| 日志类型 | 默认路径 | 说明 |
|---|---|---|
| 整机事件总日志 | `/home/tuya/tuya/logs/system/Tuya_ROS2_ALL.log` | 汇总所有节点的`INFO`、`WARN`、`ERROR`和`FATAL`事件 |
| 整机INFO事件 | `/home/tuya/tuya/logs/system/Tuya_ROS2_INFO.log` | 仅记录`INFO`事件 |
| 整机WARN事件 | `/home/tuya/tuya/logs/system/Tuya_ROS2_WARN.log` | 仅记录`WARN`事件 |
| 整机ERROR事件 | `/home/tuya/tuya/logs/system/Tuya_ROS2_ERROR.log` | 记录`ERROR`和`FATAL`事件 |
| ROS操作审计 | `/home/tuya/tuya/logs/ros2/operation_YYYYMMDD.log` | 记录Topic和Service调用 |
| 开机音频日志 | `/home/tuya/tuya/logs/boot/boot_YYYYMMDD.log` | 记录开机音频查询、设置、播放和恢复 |
| 开机音频失败日志 | `/home/tuya/tuya/logs/boot/boot_fail_YYYYMMDD.log` | 仅记录失败或未播放事件 |
| 底层协议日志 | `/home/tuya/tuya/logs/pytuyarobot/python_debug_YYYYMMDD.log` | 开启底层调试后记录协议通信 |
| 底盘滚动上报 | `/home/tuya/tuya/logs/agv/report/agv_report_YYYYMMDD_N.jsonl` | Real模式记录最近约60秒底盘上报 |
| 上半身滚动上报 | `/home/tuya/tuya/logs/upper/report/upper_auto_report_YYYYMMDD_N.jsonl` | Real模式记录最近约60秒自动上报 |
| 头部滚动上报 | `/home/tuya/tuya/logs/head/report/head_auto_report_YYYYMMDD_N.jsonl` | Real模式记录最近约60秒头部自动上报 |
| 底盘事故捕获 | `/home/tuya/tuya/logs/agv/post_report/agv_incident_YYYYMMDD_HHMMSS_<原因>.jsonl` | 故障触发后记录约20秒底盘数据 |
| 上半身事故捕获 | `/home/tuya/tuya/logs/upper/post_report/upper_incident_YYYYMMDD_HHMMSS_<原因>.jsonl` | 故障触发后记录约20秒上半身数据 |
| 头部事故捕获 | `/home/tuya/tuya/logs/head/post_report/head_incident_YYYYMMDD_HHMMSS_<原因>.jsonl` | `soft_error`或J1～J4 `motor_errors`故障上升沿触发，记录约20秒头部数据 |
| 2D相机日志 | `/home/tuya/tuya/logs/sensor/2d_camera/2d_camera_YYYYMMDD.log` | 记录2D相机启动和运行异常 |
| 雷达日志 | `/home/tuya/tuya/logs/sensor/lslidar/lslidar_YYYYMMDD.log` | 记录雷达启动和运行异常 |
| 日志保留事件 | `/home/tuya/tuya/logs/log_retention/log_retention_YYYYMMDD.log` | 按级别记录目录超限、删除文件、删除失败和清理结果 |
| 3D相机日志 | `/home/tuya/tuya/logs/sensor/3d_camera/3d_camera_YYYYMMDD.log` | 记录D435/D435I启动、就绪、告警、故障和关闭事件；同时写入整机分级日志 |
| ROS节点与Launch日志 | `/home/tuya/.ros/log` | 记录节点输出和启动异常 |
| 语音调试音频 | `/tmp/tuyarobot_vtn_wakeup/` | 仅在启用语音音频保存时生成，不属于常规运行日志 |

<a id="log-commands"></a>
### 常用查看命令

```bash
TUYA_LOG_ROOT="/home/tuya/tuya/logs"
ROS_LOG_ROOT="/home/tuya/.ros/log"

# 通过ROS查询全部已知日志路径
ros2 service call /system/get_log_path tuyarobot_msgs/srv/GetLogPath \
  '{module: "ALL", category: "ALL"}'

# 查看业务日志文件
find "$TUYA_LOG_ROOT" -type f -printf '%TY-%Tm-%Td %TH:%TM %10s %p\n' | sort

# 查看日志目录占用
du -sh "$TUYA_LOG_ROOT" "$ROS_LOG_ROOT" 2>/dev/null

# 查看当天ROS操作审计
tail -n 200 "$TUYA_LOG_ROOT/ros2/operation_$(date +%Y%m%d).log"

# 实时查看底层协议日志
tail -f "$TUYA_LOG_ROOT/pytuyarobot/python_debug_$(date +%Y%m%d).log"

# 查找业务日志中的异常信息
grep -RniE 'ERROR|FATAL|WARN|success=False|played=False' "$TUYA_LOG_ROOT"

# 查看最近生成的ROS 2日志目录
ls -td "$ROS_LOG_ROOT"/*/ 2>/dev/null | head
```

滚动上报和事故捕获文件采用JSON Lines格式，首行为元数据，其余行为采样记录：

```bash
# 查看底盘滚动上报元数据
jq -c 'select(.type == "metadata")' \
  "$TUYA_LOG_ROOT"/agv/report/agv_report_*.jsonl

# 查看上半身滚动上报的前十条采样记录
jq -c 'select(.type != "metadata")' \
  "$TUYA_LOG_ROOT"/upper/report/upper_auto_report_*.jsonl | head
```

<a id="log-cleanup"></a>
### 容量与清理

- 工程内部日志仍保留单文件限容；目录总量通过 `bash scripts/install_log_retention.sh` 安装统一保留服务。
- 文档列出的各日志分组独立限制为100 MiB；超过上限后每30秒按修改时间清理最旧日志至90 MiB。
- ROS 2运行日志按完整启动目录清理；底盘与上半身的滚动上报目录和事故日志分别计量，避免嵌套目录重复统计。
- 最新日志、正在写入的日志及最近120秒内更新的日志不会被删除，因此高写入期间目录可能暂时超过100 MiB。
- 每次真实清理均将目录超限、删除尝试、删除成功或失败以及清理汇总同时写入systemd journal和日志保留事件文件；成功操作为`INFO`、超限为`WARN`、清理失败为`ERROR`；预演不会写入该文件。
- 日志保留事件目录同样独立限制为100 MiB，超过上限后清理旧事件日志至90 MiB，当前正在写入的事件日志不会被删除。
- 可使用 `journalctl -u tuyarobot-log-retention.service` 查看清理记录，使用 `bash scripts/install_log_retention.sh --uninstall` 取消配置；取消配置不会删除已有日志。
- 日志可能包含控制参数和原始状态，外发前应进行脱敏。

<a id="head"></a>
## 一、头部接口说明

<a id="head-conventions"></a>
### 使用约定

- **Namespace**：`/head/{python_name}`（与底层方法名对齐）。状态读接口可通过 Topic 观测，支持点查的接口同时提供 `/head/service/<method_name>` Service。
- **发布频率**：状态流 Topic 按 `head_publish_hz` 定频发布最新有效缓存，默认100Hz，可配置为1～100Hz；该参数同时约束 HAL 自动上报缓存采样。`_safety_snapshot` 固定 20Hz。仅在源 `seq` 更新时重新转换消息。判断硬件是否产生新数据，应观察 `seq`、时间戳或内容变化。
- **关节**：头部包含 4 个关节，通过 `head_ip:head_port` 连接。
- **状态 Topic QoS**：BEST_EFFORT + VOLATILE + KEEP_LAST；状态 Topic 默认 depth=10。
- **状态读 Service**：Service按需读取；Topic发布最新有效缓存。当前设备不支持某项数据时，对应Topic保持静默。
- **自动上报日志**：Real默认按新`seq`记录最近约60秒缓存到`/home/tuya/tuya/logs/head/report/head_auto_report_YYYYMMDD_N.jsonl`。`soft_error`或J1～J4 `motor_errors`从0变为非0时，事故窗口写入`/home/tuya/tuya/logs/head/post_report/head_incident_YYYYMMDD_HHMMSS_<原因>.jsonl`；持续故障不重复触发，恢复后再次出现可重新触发。
- **动画类**：确认动画资源与播放模式后再调用；运动空间内禁止站人。
- 本文示例仅写 Real。通过 `mock.launch.py` 启动时，头部同名 Topic/Service 可用，但无真实硬件反馈。

<a id="head-observe"></a>
### 常用观测命令

启动并 source 工作空间后，用下列命令核对**类型**与**发布频率**（Hz 含义见上方「发布频率」）。各接口明细只给 echo/call，不重复本节。

```bash
# Topic：类型、发布端、字段定义
ros2 topic type /head/get_head_angles
ros2 topic info /head/get_head_angles -v
ros2 interface show tuyarobot_msgs/msg/JointDegreeState

# Topic：发布频率（由 head_publish_hz 控制，默认100Hz）
timeout 10s ros2 topic hz /head/get_head_angles
timeout 10s ros2 topic hz /head/head_auto_report

# Service：类型与字段定义
ros2 service type /head/service/get_head_angles
ros2 interface show tuyarobot_msgs/srv/GetScopedFloatValues
```

<a id="api-head"></a>
### `get_head_main_version`

- **功能说明**: 查询头部固件主版本
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetFloat`（CLI: `tuyarobot_msgs/srv/GetFloat`）
- **ROS 名**:
  - `/head/get_head_main_version`
- **请求字段**: 无。
- **返回语义**: `data` 为头部固件主版本号。
- **返回/观测**: `success` → `message` → `data`（浮点版本号等） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/get_head_main_version tuyarobot_msgs/srv/GetFloat '{}'
```

### `get_head_modify_version`

- **功能说明**: 查询头部固件修订版本
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/head/get_head_modify_version`
- **请求字段**: 无。
- **返回语义**: `data` 为头部固件修订版本整数。
- **返回/观测**: `success` → `message` → `data`（固件修订版本整数） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/get_head_modify_version tuyarobot_msgs/srv/GetInt '{}'
```

### `set_head_debug_state`

- **功能说明**: 设置头部固件调试状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetInt`（CLI: `tuyarobot_msgs/srv/SetInt`）
- **ROS 名**:
  - `/head/set_head_debug_state`
- **请求字段**: `data`（`int32`）。
- **参数范围**: `data` 为 `0~255` 的固件调试状态值；当前接口未定义各数值的日志类别名称，设置前应先读取并保留原值。
- **返回/观测**: `success` → `message` → `response_time_ms`；请求字段 `data`。
- **调用示例**:

```bash
ros2 service call /head/set_head_debug_state tuyarobot_msgs/srv/SetInt "{data: 1}"
```

### `get_head_debug_state`

- **功能说明**: 查询头部固件调试状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/head/get_head_debug_state`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `data`（固件调试状态原始值，`0~255`，无公开枚举名称） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/get_head_debug_state tuyarobot_msgs/srv/GetInt '{}'
```

### `head_power_on`

- **功能说明**: 为头部控制器和关节上电
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/head/head_power_on`
- **请求字段**: 无。
- **返回语义**: `success=true` 表示头部上电命令执行成功。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/head_power_on tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `head_power_off`

- **功能说明**: 关闭头部控制器和关节电源
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/head/head_power_off`
- **请求字段**: 无。
- **返回语义**: `success=true` 表示头部下电命令执行成功。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/head_power_off tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `is_head_powered_on`

- **功能说明**: 查询头部控制器上电状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/head/is_head_powered_on`
- **请求字段**: 无。
- **返回语义**: `data=0` 表示未上电；非零值表示已上电，`data` 保留设备返回的原始状态值。
- **返回/观测**: `success` → `message` → `data` → `response_time_ms`；`data=0` 时 `success=false`，非零时 `success=true`，`message` 对齐底层返回。
- **调用示例**:

```bash
ros2 service call /head/is_head_powered_on tuyarobot_msgs/srv/GetInt '{}'
```

### `set_head_joint_enable`

- **功能说明**: 使能或失能指定头部关节
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetHeadJointEnable`（CLI: `tuyarobot_msgs/srv/SetHeadJointEnable`）
- **ROS 名**:
  - `/head/set_head_joint_enable`
- **请求字段**: `joint_id`（`int32`）、`state`（`int32`）。
- **参数范围**: `joint_id` 为 `1~4` 或 `254`，`254` 表示全部关节；`state` 仅支持 `0` 或 `1`，`1=使能`，`0=失能`。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/set_head_joint_enable tuyarobot_msgs/srv/SetHeadJointEnable "{joint_id: 254, state: 1}"
```

### `set_head_calibrate`

- **功能说明**: 校准指定或全部头部关节
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/HeadJointCommand`（CLI: `tuyarobot_msgs/srv/HeadJointCommand`）
- **ROS 名**:
  - `/head/set_head_calibrate`
- **请求字段**: `joint_id`（`int32`）。
- **参数范围**: `joint_id` 为 `1~4` 或 `254`，`254` 表示全部头部关节。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/set_head_calibrate tuyarobot_msgs/srv/HeadJointCommand "{joint_id: 254}"
```

### `send_head_angles`

- **功能说明**: 控制头部四关节到目标角度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SendHeadAngles`（CLI: `tuyarobot_msgs/srv/SendHeadAngles`）
- **ROS 名**:
  - `/head/send_head_angles`
- **请求字段**: `angles`（`float64[]`）、`speed`（`int32`）。
- **参数范围**:

| 字段 | 范围 | 说明 |
|---|---|---|
| `angles` | 长度4；J1 `-120~120`，J2 `-21~21`，J3/J4 `-45~45` | 按J1～J4排列，单位为度。 |
| `speed` | `1~100` | 四关节运动速度。 |

- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/send_head_angles tuyarobot_msgs/srv/SendHeadAngles "{angles: [0.0, 0.0, 0.0, 0.0], speed: 20}"
```

### `get_head_angles`

#### Topic（发布/状态）

- **功能说明**: 发布头部四关节角度
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `tuyarobot_msgs/JointDegreeState`（CLI: `tuyarobot_msgs/msg/JointDegreeState`）
- **ROS 名**:
  - `/head/get_head_angles`
- **返回语义**: `name[]` 和 `position_deg[]` 均为4项，按J1～J4排列；`position_deg[]` 单位为度。
- **返回/观测**: 按 `head_publish_hz` 发布最新有效缓存；仅在源 `seq` 更新时重新转换消息。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /head/get_head_angles --once
```

#### Service

- **功能说明**: 查询头部四关节角度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/head/service/get_head_angles`
- **请求字段**: 无。
- **返回语义**: `values[]` 固定4项，按J1～J4排列，单位为度。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/service/get_head_angles tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `send_head_angle`

- **功能说明**: 控制指定头部关节到目标角度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SendHeadAngle`（CLI: `tuyarobot_msgs/srv/SendHeadAngle`）
- **ROS 名**:
  - `/head/send_head_angle`
- **请求字段**: `joint_id`（`int32`）、`angle`（`float64`）、`speed`（`int32`）。
- **参数范围**:

| 字段 | 范围 | 说明 |
|---|---|---|
| `joint_id` | `1~4` | 头部关节号。 |
| `angle` | J1 `-120~120`，J2 `-21~21`，J3/J4 `-45~45` | 目标角度，单位为度。 |
| `speed` | `1~100` | 运动速度。 |

- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/send_head_angle tuyarobot_msgs/srv/SendHeadAngle "{joint_id: 1, angle: 10.0, speed: 20}"
```

### `clear_head_error`

- **功能说明**: 清除指定或全部头部关节故障
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/HeadJointCommand`（CLI: `tuyarobot_msgs/srv/HeadJointCommand`）
- **ROS 名**:
  - `/head/clear_head_error`
- **请求字段**: `joint_id`（`int32`）。
- **参数范围**: `joint_id` 为 `1~4` 或 `254`，`254` 表示清除全部头部关节错误。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/clear_head_error tuyarobot_msgs/srv/HeadJointCommand "{joint_id: 254}"
```

### `is_head_in_position`

- **功能说明**: 判断指定头部关节是否到位
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetHeadInPosition`（CLI: `tuyarobot_msgs/srv/GetHeadInPosition`）
- **ROS 名**:
  - `/head/is_head_in_position`
- **请求字段**: `joint_id`（`int32`）、`angle`（`float64`）。
- **参数范围**: `joint_id` 为 `1~4`；`angle` 范围为J1 `-120~120`、J2 `-21~21`、J3/J4 `-45~45`，单位为度。
- **返回/观测**: `success` → `message` → `in_position` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/is_head_in_position tuyarobot_msgs/srv/GetHeadInPosition "{joint_id: 1, angle: 0.0}"
```

### `is_head_moving`

- **功能说明**: 判断头部是否正在运动
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/head/is_head_moving`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `data`（`0` 静止，`1` 运动中） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/is_head_moving tuyarobot_msgs/srv/GetInt '{}'
```

### `head_stop`

- **功能说明**: 立即停止头部关节运动
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/head/head_stop`
- **请求字段**: 无。
- **返回语义**: 无请求参数。立即停止头部关节运动；不是动画停止——停动画请用 `/head/stop_head_animation`。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/head_stop tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `get_head_robot_status`

#### Topic（发布/状态）

- **功能说明**: 发布头部软件及四关节错误
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `tuyarobot_msgs/HeadRobotStatus`（CLI: `tuyarobot_msgs/msg/HeadRobotStatus`）
- **ROS 名**:
  - `/head/get_head_robot_status`
- **返回/观测**: `soft_error` → `soft_error_message` → `motor_errors[4]` → `motor_error_messages[4]`；按 `head_publish_hz` 发布最新有效缓存。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /head/get_head_robot_status --once
```

#### Service

- **功能说明**: 查询头部软件及四关节错误
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetHeadRobotStatus`（CLI: `tuyarobot_msgs/srv/GetHeadRobotStatus`）
- **ROS 名**:
  - `/head/service/get_head_robot_status`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `soft_error` → `soft_error_message` → `motor_errors[4]` → `motor_error_messages[4]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/service/get_head_robot_status tuyarobot_msgs/srv/GetHeadRobotStatus '{}'
```

### `get_head_joints_run_sp`

#### Topic（发布/状态）

- **功能说明**: 发布头部四关节运行速度
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `std_msgs/Float64MultiArray`（CLI: `std_msgs/msg/Float64MultiArray`）
- **ROS 名**:
  - `/head/get_head_joints_run_sp`
- **返回语义**: `data[]` 固定4项，按J1～J4排列；各项为关节运行速度浮点值，消息未提供物理单位。
- **返回/观测**: 按 `head_publish_hz` 发布最新有效缓存；`--once` 取当前最新一帧。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /head/get_head_joints_run_sp --once
```

#### Service

- **功能说明**: 查询头部四关节运行速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/head/service/get_head_joints_run_sp`
- **请求字段**: 无。
- **返回语义**: `values[]` 固定4项，按J1～J4排列；各项为关节运行速度浮点值，消息未提供物理单位。
- **返回/观测**: `success` → `message` → `values[]`（按头部四关节顺序排列） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/service/get_head_joints_run_sp tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `get_head_joints_current`

- **功能说明**: 查询头部四关节电流。Topic publisher 为空入口、不发消息。
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/head/service/get_head_joints_current`
- **请求字段**: 无。
- **返回语义**: `values[]` 固定4项，按J1～J4排列；各项为关节电流浮点值，单位 A；当前电机不支持时返回原始失败信息。
- **返回/观测**: `success` → `message` → `values[]`（按头部四关节顺序排列） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/service/get_head_joints_current tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `get_head_joints_temp`

- **功能说明**: 查询头部四关节温度。Topic publisher 为空入口、不发消息。
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/head/service/get_head_joints_temp`
- **请求字段**: 无。
- **返回语义**: `data[]` 固定4项，按J1～J4排列，单位 `°C`。
- **返回/观测**: `success` → `message` → `data[]`（按头部四关节顺序排列） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/service/get_head_joints_temp tuyarobot_msgs/srv/GetInts '{}'
```

### `get_head_joints_torque`

- **功能说明**: 查询头部四关节力矩
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/head/get_head_joints_torque`
- **请求字段**: 无。
- **返回语义**: `values[]` 固定4项，按J1～J4排列，单位 `N`。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/get_head_joints_torque tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `get_head_auto_report`

- **功能说明**: 查询头部自动上报状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/head/get_head_auto_report`
- **请求字段**: 无。
- **返回语义**: `data=0` 表示关闭，`data=1` 表示开启。
- **返回/观测**: `success` → `message` → `data` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/get_head_auto_report tuyarobot_msgs/srv/GetInt '{}'
```

### `get_latest_head_auto_report`

#### Topic（发布/状态）

- **功能说明**: 发布头部最新自动上报缓存。
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `tuyarobot_msgs/HeadAutoReport`（CLI: `tuyarobot_msgs/msg/HeadAutoReport`）
- **ROS 名**:
  - `/head/head_auto_report`
- **返回语义**: `json` 为自动上报正文直出；`age` 单位为秒，`timestamp` 为源缓存时间戳，`seq` 为源缓存序号。
- **返回/观测**: 仅在源 `seq` 更新时转换，按 `head_publish_hz` 重发最新有效缓存；重复帧保留源 `seq` 和 `timestamp`。
- **调用示例**:

```bash
timeout 10s ros2 topic hz /head/head_auto_report
timeout 5s ros2 topic echo /head/head_auto_report --once --full-length
```

#### Service

- **功能说明**: 读取最新头部自动上报缓存
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetLatestHeadAutoReport`（CLI: `tuyarobot_msgs/srv/GetLatestHeadAutoReport`）
- **ROS 名**:
  - `/head/get_latest_head_auto_report`
- **请求字段**: 无。
- **返回语义**: `json` 为自动上报正文直出；`age` 单位为秒，`timestamp` 为时间戳，`seq` 为缓存序号。
- **返回/观测**: `success` → `message` → `json` → `age` → `timestamp` → `seq` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/get_latest_head_auto_report tuyarobot_msgs/srv/GetLatestHeadAutoReport '{}'
```

### `get_head_angles_auto_report`

#### Topic（发布/状态）

- **功能说明**: 发布头部自动上报中的四关节角度。
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `tuyarobot_msgs/JointDegreeState`（CLI: `tuyarobot_msgs/msg/JointDegreeState`）
- **ROS 名**:
  - `/head/get_head_angles_auto_report`
- **返回语义**: `name[]`、`position_deg[]` 固定4项，按J1～J4排列，单位为度。
- **返回/观测**: 按 `head_publish_hz`发布最新有效角度缓存；源数据未更新时保留原采样时间。
- **调用示例**:

```bash
timeout 10s ros2 topic hz /head/get_head_angles_auto_report
timeout 5s ros2 topic echo /head/get_head_angles_auto_report --once
```

#### Service

- **功能说明**: 读取头部自动上报中的四关节角度。
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/head/service/get_head_angles_auto_report`
- **请求字段**: 无。
- **返回语义**: `values[]` 固定4项，按J1～J4排列，单位为度。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`；缓存不可用时自动请求恢复后读取。
- **调用示例**:

```bash
ros2 service call /head/service/get_head_angles_auto_report tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `set_head_led_control`

- **功能说明**: 立即控制头部灯效
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetHeadLedControl`（CLI: `tuyarobot_msgs/srv/SetHeadLedControl`）
- **ROS 名**:
  - `/head/set_head_led_control`
- **请求字段**: `mode`（`int32`）、`r`（`int32`）、`g`（`int32`）、`b`（`int32`）、`brightness`（`int32`）、`side`（`int32`）、`frequency_ms`（`int64`）。
- **参数范围**: `mode`：`1=常亮`、`2=闪烁`、`3=呼吸`；`r/g/b`：`0~255`；`brightness`：`0~100`；`side`：`0=全关`、`1=左耳`、`2=右耳`、`3=左右全开`；`frequency_ms`：`10~10000 ms`。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/set_head_led_control tuyarobot_msgs/srv/SetHeadLedControl "{mode: 1, r: 0, g: 0, b: 255, brightness: 100, side: 3, frequency_ms: 10}"
```

### `set_head_default_led_config`

- **功能说明**: 保存默认灯效。不立即切换
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetHeadLedControl`（CLI: `tuyarobot_msgs/srv/SetHeadLedControl`）
- **ROS 名**:
  - `/head/set_head_default_led_config`
- **请求字段**: `mode`（`int32`）、`r`（`int32`）、`g`（`int32`）、`b`（`int32`）、`brightness`（`int32`）、`side`（`int32`）、`frequency_ms`（`int64`）。
- **参数范围**: `mode`：`1=常亮`、`2=闪烁`、`3=呼吸`；`r/g/b`：`0~255`；`brightness`：`0~100`；`side`：`0=全关`、`1=左耳`、`2=右耳`、`3=左右全开`；`frequency_ms`：`10~10000 ms`。该接口只保存配置，不立即播放灯效。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/set_head_default_led_config tuyarobot_msgs/srv/SetHeadLedControl "{mode: 3, r: 0, g: 250, b: 0, brightness: 50, side: 3, frequency_ms: 2000}"
```

### `head_firmware_flash`

- **功能说明**: 升级头部主控固件
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/HeadFirmwareFlash`（CLI: `tuyarobot_msgs/srv/HeadFirmwareFlash`）
- **ROS 名**:
  - `/head/head_firmware_flash`
- **请求字段**: `firmware_path`（`string`）、`skip_md5_check`（`bool`）。
- **参数范围**: `firmware_path` 为 Orin 本地路径；头部固件文件名必须是 `TuyaHead` 或以 `TuyaHead_V` 开头。`skip_md5_check` 取 `true/false`，分别表示跳过或启用 MD5 白名单校验。
- **返回/观测**: `success` → `message` → `version` → `response_time_ms`；`skip_md5_check` 需由调用方显式传入；耗时长，勿在运动中调用。
- **调用示例**:

```bash
ros2 service call /head/head_firmware_flash tuyarobot_msgs/srv/HeadFirmwareFlash "{firmware_path: '/path/to/TuyaHead', skip_md5_check: true}"
```

### `get_head_collision_threshold`

- **功能说明**: 查询指定关节碰撞阈值
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetHeadCollisionThreshold`（CLI: `tuyarobot_msgs/srv/GetHeadCollisionThreshold`）
- **ROS 名**:
  - `/head/get_head_collision_threshold`
- **请求字段**: `joint_id`（`int32`）。
- **参数范围**: `joint_id` 为 `1~4`，不支持 `254`。
- **返回/观测**: `success` → `message` → `threshold` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/get_head_collision_threshold tuyarobot_msgs/srv/GetHeadCollisionThreshold "{joint_id: 1}"
```

### `set_head_collision_threshold`

- **功能说明**: 设置指定关节碰撞阈值
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetHeadCollisionThreshold`（CLI: `tuyarobot_msgs/srv/SetHeadCollisionThreshold`）
- **ROS 名**:
  - `/head/set_head_collision_threshold`
- **请求字段**: `joint_id`（`int32`）、`threshold`（`int32`）。
- **参数范围**: `joint_id` 为 `1~4`，不支持 `254`；`threshold` 为 `1~100`，数值越小越容易触发碰撞。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/set_head_collision_threshold tuyarobot_msgs/srv/SetHeadCollisionThreshold "{joint_id: 1, threshold: 100}"
```

### `get_head_motion_mode`

- **功能说明**: 查询头部位置或速度模式
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/head/get_head_motion_mode`
- **请求字段**: 无。
- **返回语义**: `data=0` 为位置模式，`data=1` 为速度模式。
- **返回/观测**: `success` → `message` → `data` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/get_head_motion_mode tuyarobot_msgs/srv/GetInt '{}'
```

### `set_head_motion_mode`

- **功能说明**: 切换头部位置或速度模式
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetInt`（CLI: `tuyarobot_msgs/srv/SetInt`）
- **ROS 名**:
  - `/head/set_head_motion_mode`
- **请求字段**: `data`（`int32`）。
- **参数范围**: `data=0` 切换位置模式，`data=1` 切换速度模式。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/set_head_motion_mode tuyarobot_msgs/srv/SetInt "{data: 1}"
```

### `set_head_default_animation`

- **功能说明**: 保存默认动画。不立即播放
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetHeadDefaultAnimation`（CLI: `tuyarobot_msgs/srv/SetHeadDefaultAnimation`）
- **ROS 名**:
  - `/head/set_head_default_animation`
- **请求字段**: `name`（`string`）。
- **参数范围**: `name` 为一个已存在的远程动画名，不带时间列表；该接口只设置默认动画，不立即播放。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/set_head_default_animation tuyarobot_msgs/srv/SetHeadDefaultAnimation "{name: 'blink'}"
```

### `send_head_animation`

- **功能说明**: 上传PAG动画。不立即播放
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SendHeadAnimation`（CLI: `tuyarobot_msgs/srv/SendHeadAnimation`）
- **ROS 名**:
  - `/head/send_head_animation`
- **请求字段**: `animation_path`（`string`）。
- **参数范围**: `animation_path`：Orin 本地 `.pag` 绝对路径（对齐 Python `animation_path`）；远程文件名用 basename。播放前确认头部已上电且空间安全。
- **返回/观测**: `success` → `message` → `name` → `remote_path` → `bytes` → `seconds` → `milliseconds` → `kb_per_sec` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/send_head_animation tuyarobot_msgs/srv/SendHeadAnimation "{animation_path: '/path/to/blink.pag'}"
```

### `set_head_animation_play_mode`

- **功能说明**: 设置动画排队或刷新播放
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetHeadAnimationPlayMode`（CLI: `tuyarobot_msgs/srv/SetHeadAnimationPlayMode`）
- **ROS 名**:
  - `/head/set_head_animation_play_mode`
- **请求字段**: `mode`（`int32`）。
- **参数范围**: `mode`：`1` 队列模式，`2` 刷新模式（打断当前动画）。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/set_head_animation_play_mode tuyarobot_msgs/srv/SetHeadAnimationPlayMode "{mode: 1}"
```

### `play_exist_head_animation`

- **功能说明**: 播放头部已上传动画
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/PlayHeadAnimation`（CLI: `tuyarobot_msgs/srv/PlayHeadAnimation`）
- **ROS 名**:
  - `/head/play_exist_head_animation`
- **请求字段**: `names`（`string[]`）、`intervals_ms`（`int64[]`）、`play_times_ms`（`int64[]`）。
- **参数范围**: `names[]`：远程动画名（不带 `.pag`，1~10 个）；`intervals_ms`/`play_times_ms` 可空（单动画默认一直播放）；多动画三列表等长。单位 ms，`0` 表示一直播放。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/play_exist_head_animation tuyarobot_msgs/srv/PlayHeadAnimation "{names: ['blink'], intervals_ms: [], play_times_ms: []}"
```

### `set_head_jog_motion`

- **功能说明**: 按速度持续点动头部关节
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetHeadJogMotion`（CLI: `tuyarobot_msgs/srv/SetHeadJogMotion`）
- **ROS 名**:
  - `/head/set_head_jog_motion`
- **请求字段**: `joint_id`（`int32`）、`direction`（`int32`）、`speed`（`int32`）。
- **参数范围**: `joint_id`：`1~4`；`direction`：`0/1`；`speed`：`1~100`。调用前须切换到速度模式。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/set_head_jog_motion tuyarobot_msgs/srv/SetHeadJogMotion "{joint_id: 2, direction: 0, speed: 20}"
```

### `stop_head_animation`

- **功能说明**: 停止正在播放的头部动画
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/StopHeadAnimation`（CLI: `tuyarobot_msgs/srv/StopHeadAnimation`）
- **ROS 名**:
  - `/head/stop_head_animation`
- **请求字段**: 无。
- **返回语义**: 无请求参数；`success=true` 表示当前动画已停止，`result_value` 为执行结果值。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/stop_head_animation tuyarobot_msgs/srv/StopHeadAnimation '{}'
```

### `get_head_playing_animations`

- **功能说明**: 查询当前正在播放的头部动画
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetHeadAnimations`（CLI: `tuyarobot_msgs/srv/GetHeadAnimations`）
- **ROS 名**:
  - `/head/get_head_playing_animations`
- **请求字段**: 无。
- **返回语义**: `names[]` 为当前播放的动画名称，不带 `.pag`；无动画播放时返回空数组，头部未上电时也可查询。
- **返回/观测**: `success` → `message` → `names` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/get_head_playing_animations tuyarobot_msgs/srv/GetHeadAnimations '{}'
```

### `get_head_animations`

- **功能说明**: 查询头部已上传动画列表
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetHeadAnimations`（CLI: `tuyarobot_msgs/srv/GetHeadAnimations`）
- **ROS 名**:
  - `/head/get_head_animations`
- **请求字段**: 无。
- **返回语义**: `names[]` 为头部已保存动画的文件名列表，名称可直接用于 `play_exist_head_animation`。
- **返回/观测**: `success` → `message` → `names` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/get_head_animations tuyarobot_msgs/srv/GetHeadAnimations '{}'
```

### `delete_head_animation`

- **功能说明**: 删除头部已上传动画
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/DeleteHeadAnimation`（CLI: `tuyarobot_msgs/srv/DeleteHeadAnimation`）
- **ROS 名**:
  - `/head/delete_head_animation`
- **请求字段**: `name`（`string`）。
- **参数范围**: `name` 必须以 `.pag` 结尾；主文件名长度 `1~10`，仅允许英文字母、数字、`_` 和 `-`。
- **返回/观测**: `success` → `message` → `name` → `remote_path` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/delete_head_animation tuyarobot_msgs/srv/DeleteHeadAnimation "{name: 'blink.pag'}"
```

### `warmup_head_animation`

- **功能说明**: 预热头部动画资源
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/head/warmup_head_animation`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/warmup_head_animation tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `play_screen_animation`

- **功能说明**: 分块发送并播放屏幕动画
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/PlayScreenAnimation`（CLI: `tuyarobot_msgs/srv/PlayScreenAnimation`）
- **ROS 名**:
  - `/head/play_screen_animation`
- **请求字段**: `image_path`（`string`）。
- **参数范围**: `image_path`：本地帧目录/资源路径；HAL 读文件后按 254B 分包下发。
- **返回/观测**: `success` → `message` → `chunk_count`（实际下发分包数）→ `bytes`（下发字节数）→ `response_time_ms`；HAL 读取本地路径并按 254B 分包，超过 256 包时直接失败。
- **调用示例**:

```bash
ros2 service call /head/play_screen_animation tuyarobot_msgs/srv/PlayScreenAnimation "{image_path: '/path/to/screen_frames'}"
```

### `play_head_animation`

- **功能说明**: 上传并播放PAG动画
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/PlayHeadAnimationUpload`（CLI: `tuyarobot_msgs/srv/PlayHeadAnimationUpload`）
- **ROS 名**:
  - `/head/play_head_animation`
- **请求字段**: `animation_paths`（`string[]`）、`intervals_ms`（`int64[]`）、`play_times_ms`（`int64[]`）。
- **参数范围**: `animation_paths[]`：本地 `.pag` 路径列表（对齐 Python `animation_path`）；`intervals_ms`/`play_times_ms` 可空，单文件默认一直播放（`[0]/[0]`）；多文件必须等长且非空。单位 ms，`play_times_ms=0` 表示一直播放。
- **返回/观测**: `success` → `message` → `names` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/play_head_animation tuyarobot_msgs/srv/PlayHeadAnimationUpload "{animation_paths: ['/path/to/blink.pag'], intervals_ms: [], play_times_ms: []}"
```

### `get_head_joints_min_angle`

- **功能说明**: 查询头部四关节最小限位
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetHeadJointLimits`（CLI: `tuyarobot_msgs/srv/GetHeadJointLimits`）
- **ROS 名**:
  - `/head/get_head_joints_min_angle`
- **请求字段**: 无。
- **返回语义**: `values[]` 固定4项，按J1～J4排列，表示当前保存的最小角度限制，单位为度。
- **返回/观测**: `success` → `message` → `values` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/get_head_joints_min_angle tuyarobot_msgs/srv/GetHeadJointLimits '{}'
```

### `get_head_joints_max_angle`

- **功能说明**: 查询头部四关节最大限位
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetHeadJointLimits`（CLI: `tuyarobot_msgs/srv/GetHeadJointLimits`）
- **ROS 名**:
  - `/head/get_head_joints_max_angle`
- **请求字段**: 无。
- **返回语义**: `values[]` 固定4项，按J1～J4排列，表示当前保存的最大角度限制，单位为度。
- **返回/观测**: `success` → `message` → `values` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/get_head_joints_max_angle tuyarobot_msgs/srv/GetHeadJointLimits '{}'
```

### `get_head_joint_acc`

- **功能说明**: 读取头部四个关节的加速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetHeadJointAcc`（CLI: `tuyarobot_msgs/srv/GetHeadJointAcc`）
- **ROS 名**:
  - `/head/get_head_joint_acc`
- **请求字段**: 无。
- **返回语义**: `accelerations[]` 固定4项，按J1～J4排列，单位为 `°/s²`。
- **返回/观测**: `success` → `message` → `accelerations` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/get_head_joint_acc tuyarobot_msgs/srv/GetHeadJointAcc '{}'
```

### `set_head_joint_min_angle`

- **功能说明**: 设置指定头部关节最小限位
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetHeadJointLimit`（CLI: `tuyarobot_msgs/srv/SetHeadJointLimit`）
- **ROS 名**:
  - `/head/set_head_joint_min_angle`
- **请求字段**: `joint_id`（`int32`）、`angle`（`float64`）。
- **参数范围**:

| 字段 | 范围 | 说明 |
|---|---|---|
| `joint_id` | `1~4` | 不支持 `254`。 |
| `angle` | J1 `-120~120`，J2 `-21~21`，J3/J4 `-45~45` | 最小角度限制，单位为度。 |

- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/set_head_joint_min_angle tuyarobot_msgs/srv/SetHeadJointLimit "{joint_id: 1, angle: -30.0}"
```

### `set_head_joint_max_angle`

- **功能说明**: 设置指定头部关节最大限位
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetHeadJointLimit`（CLI: `tuyarobot_msgs/srv/SetHeadJointLimit`）
- **ROS 名**:
  - `/head/set_head_joint_max_angle`
- **请求字段**: `joint_id`（`int32`）、`angle`（`float64`）。
- **参数范围**:

| 字段 | 范围 | 说明 |
|---|---|---|
| `joint_id` | `1~4` | 不支持 `254`。 |
| `angle` | J1 `-120~120`，J2 `-21~21`，J3/J4 `-45~45` | 最大角度限制，单位为度。 |

- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /head/set_head_joint_max_angle tuyarobot_msgs/srv/SetHeadJointLimit "{joint_id: 1, angle: 30.0}"
```

### `set_head_joint_acc`

- **功能说明**: 设置指定头部关节的加速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetHeadJointAcc`（CLI: `tuyarobot_msgs/srv/SetHeadJointAcc`）
- **ROS 名**:
  - `/head/set_head_joint_acc`
- **请求字段**: `joint_id`（`int32`）、`acceleration`（`float64`）。
- **参数范围**: `joint_id=1~4`；`acceleration=1~100 °/s²`。ROS直接透传，由设备接口判定参数是否合法。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`；成功时 `result_value` 通常为 `1`。
- **调用示例**:

```bash
ros2 service call /head/set_head_joint_acc tuyarobot_msgs/srv/SetHeadJointAcc "{joint_id: 1, acceleration: 100.0}"
```

<a id="chassis"></a>
## 二、底盘接口说明

<a id="chassis-conventions"></a>
### 使用约定

- **Namespace**：`/chassis/*`；Nav2 兼容面使用根命名空间 `/cmd_vel`、`/odom`。
- **发布频率**：底盘状态 Topic 按 `chassis_publish_hz` 定频发布最新有效缓存，默认100Hz，可配置为1～100Hz；该参数同时约束 HAL 缓存采样。20Hz报告与 `_safety_snapshot` 固定20Hz。重复发布保留源 `seq` 和时间戳。
- **控制 QoS**：`/cmd_vel` 使用 `control_qos(depth=cmd_vel_qos_depth)`，默认 depth=1，只保留最新指令
- **`/cmd_vel` 语义**：非零速度持续运动，仅零速 Twist 或 `/chassis/agv_wheel_stop` 停止；无 ROS 超时自动停，执行结果和耗时写入审计日志。
- **轮毂控制 Service**：`/chassis/agv_wheel_control` 与 `/cmd_vel` 调用同一 HAL；用于需要同步读取执行结果和错误信息的场景，Nav2 继续使用 `/cmd_vel`。
- **状态读 Service**：`/chassis/service/<method_name>` 与同名状态 Topic 并存（Service 名不变）；不含 `/odom`。
- **状态 QoS**：BEST_EFFORT + VOLATILE + KEEP_LAST；状态 Topic 默认 depth=10
- **自动上报**：`chassis_auto_report_enabled=true`（默认）时 launch 启动后 `set_agv_auto_report(1)`，缓存断流或被关则恢复 1。设为 `false` 时首启 `set(0)`，新帧或状态变 1 时压回 0。目标态仅 launch 生效；无 ROS `set_agv_auto_report` Service。
- **TOF 防跌落**：`get/set_agv_tof_drop_threshold`（cm，`0`=关）、`get_agv_tof_refs`、`set_agv_tof_restore_drop`、`set_agv_tof_factory_calibrate`；改阈值、恢复或标定会影响保护，请在合适地面和姿态下操作。
- 本文示例仅写 Real。通过 `mock.launch.py` 启动时，底盘同名 Topic/Service 可用，但无真实硬件反馈。

<a id="chassis-observe"></a>
### 常用观测命令

启动并 source 工作空间后，用下列命令核对**类型**与**发布频率**（Hz 含义见上方「发布频率」）。各接口明细只给 echo/call，不重复本节。

```bash
# Topic：类型、发布端、字段定义
ros2 topic type /odom
ros2 topic info /odom -v
ros2 interface show nav_msgs/msg/Odometry

# Topic：发布频率（底盘状态由 chassis_publish_hz 控制，20Hz报告固定）
timeout 10s ros2 topic hz /chassis/get_latest_agv_report_msg
timeout 10s ros2 topic hz /chassis/get_latest_agv_report_msg_20hz

# Service：类型与字段定义
ros2 service type /chassis/service/get_agv_robot_status
ros2 interface show tuyarobot_msgs/srv/GetAgvRobotStatus
```

<a id="api-chassis"></a>
### `agv_wheel_control`

#### Topic（订阅/控制）

- **功能说明**: 接收底盘线速度和角速度
- **类型**: Topic（订阅/控制）
- **消息/服务类型**: `geometry_msgs/Twist`（CLI: `geometry_msgs/msg/Twist`）
- **ROS 名**:
  - `/cmd_vel`
- **消息字段**: `linear`（`geometry_msgs/Vector3`）、`angular`（`geometry_msgs/Vector3`）。
- **参数范围**: `linear.x` 前进速度：`0` 或 `-0.5~-0.02 m/s`、`0.02~0.5 m/s`；`angular.z` 旋转速度：`0` 或 `-1.82~-0.01 rad/s`、`0.01~1.82 rad/s`。非零指令持续运动，仅零速 Twist 或 `/chassis/agv_wheel_stop` 才会停；Topic 无同步回包，超限信息查看节点日志或审计日志。
- **返回/观测**: 无同步回包；第一层 ACK 耗时写入 operation 审计日志的 `response_time_ms`（ms）。成功与否看审计/节点日志；持续运动直到零速 Twist 或 `agv_wheel_stop`。
- **调用示例**:

```bash
ros2 topic pub -w 1 --keep-alive 2 --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}, angular: {z: 0.0}}"
# 停止：零速 Twist，或 ros2 service call /chassis/agv_wheel_stop tuyarobot_msgs/srv/TuyarobotTrigger '{}'
ros2 topic pub -w 1 --keep-alive 2 --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

#### Service

- **功能说明**: 控制底盘线速度和角速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/AgvWheelControl`（CLI: `tuyarobot_msgs/srv/AgvWheelControl`）
- **ROS 名**:
  - `/chassis/agv_wheel_control`
- **请求字段**: `forward_mps`（`float64`）、`rotate_rads`（`float64`）。
- **参数范围**: `forward_mps`：`0` 或 `-0.5~-0.02 m/s`、`0.02~0.5 m/s`；`rotate_rads`：`0` 或 `-1.82~-0.01 rad/s`、`0.01~1.82 rad/s`。非零指令持续运动，仅零速控制或 `/chassis/agv_wheel_stop` 才会停。
- **返回/观测**: `success` → `message` → `response_time_ms`；超出范围时 `success=false`，`message` 返回参数错误原因。
- **调用示例**:

```bash
ros2 service call /chassis/agv_wheel_control tuyarobot_msgs/srv/AgvWheelControl "{forward_mps: 0.1, rotate_rads: 0.0}"
```

### `agv_wheel_stop`

- **功能说明**: 立即停止底盘轮毂运动
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/chassis/agv_wheel_stop`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/agv_wheel_stop tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `agv_power_on`

- **功能说明**: 为底盘轮毂和升降机构上电
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/chassis/agv_power_on`
- **请求字段**: 无。
- **返回语义**: `success=true` 表示底盘上电命令执行成功。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/agv_power_on tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `clear_agv_error`

- **功能说明**: 清除指定设备或全部底盘故障
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/ClearAgvError`（CLI: `tuyarobot_msgs/srv/ClearAgvError`）
- **ROS 名**:
  - `/chassis/clear_agv_error`
- **请求字段**: `device_id`（`int32`）。
- **参数范围**: `device_id` 仅支持 `1`、`2`、`3` 或 `254`；`254` 表示清除全部底盘设备错误。
- **返回/观测**: `success` → `message` → `response_time_ms`；需显式传入 254 才清除全部关节/设备；ROS 不再代填。
- **调用示例**:

```bash
ros2 service call /chassis/clear_agv_error tuyarobot_msgs/srv/ClearAgvError "{device_id: 254}"
```

### `get_latest_agv_report_msg`

#### Topic（发布/状态）

- **功能说明**: 发布底盘最新报告
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `tuyarobot_msgs/AgvLatestReport`（CLI: `tuyarobot_msgs/msg/AgvLatestReport`）
- **ROS 名**:
  - `/chassis/get_latest_agv_report_msg`
- **返回语义**: `json` 为 Python SDK 自动上报正文直出；`age`、`timestamp`、`seq` 为 ROS 元数据，`message` 对齐 Python 返回信息。
- **返回/观测**: Real 读取内存中的最新报告；按 `chassis_publish_hz` 定频发布最新有效缓存。重复帧保留源 `seq` 和时间戳；缓存过期后停发。维护、上电和连接恢复期间暂停采样。
- **调用示例**:

```bash
timeout 10s ros2 topic hz /chassis/get_latest_agv_report_msg
timeout 5s ros2 topic echo /chassis/get_latest_agv_report_msg --once
```

#### Service

- **功能说明**: 读取底盘最新报告
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetLatestAgvReport`（CLI: `tuyarobot_msgs/srv/GetLatestAgvReport`）
- **ROS 名**:
  - `/chassis/service/get_latest_agv_report_msg`
- **请求字段**: 无。
- **返回语义**: `json` 为 Python SDK 自动上报正文直出；`age`、`timestamp`、`seq` 为 ROS 元数据，`message` 对齐 Python 返回信息。
- **返回/观测**: `success` → `message` → `json` → `age` → `timestamp` → `seq` → `response_time_ms`；读取现有缓存，不触发串口或新的 SDK 查询。
- **调用示例**:

```bash
ros2 service call /chassis/service/get_latest_agv_report_msg tuyarobot_msgs/srv/GetLatestAgvReport '{}'
```

### `get_latest_agv_report_msg_20hz`

#### Topic（发布/状态）

- **功能说明**: 发布20Hz底盘最新缓存
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `tuyarobot_msgs/AgvLatestReport20Hz`（CLI: `tuyarobot_msgs/msg/AgvLatestReport20Hz`）
- **ROS 名**:
  - `/chassis/get_latest_agv_report_msg_20hz`
- **返回语义**: `json` 为 Python SDK 20Hz 自动上报正文直出；`age`、`timestamp`、`seq` 为 ROS 缓存元数据，`message` 对齐 Python 返回信息。
- **返回/观测**: 独立20Hz节拍发布最新有效缓存；重复帧保留源 `seq` 和时间戳，缓存过期后停发，不受 `chassis_publish_hz` 影响。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /chassis/get_latest_agv_report_msg_20hz --once
```

#### Service

- **功能说明**: 读取20Hz底盘最新缓存
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetLatestAgvReport20Hz`（CLI: `tuyarobot_msgs/srv/GetLatestAgvReport20Hz`）
- **ROS 名**:
  - `/chassis/service/get_latest_agv_report_msg_20hz`
- **请求字段**: 无。
- **返回语义**: `json` 为 Python SDK 20Hz 自动上报正文直出；`age`、`timestamp`、`seq` 为 ROS 缓存元数据，`message` 对齐 Python 返回信息。
- **返回/观测**: `success` → `message` → `json` → `age` → `timestamp` → `seq` → `response_time_ms`；读取现有缓存，不触发串口或新的 SDK 查询。
- **调用示例**:

```bash
ros2 service call /chassis/service/get_latest_agv_report_msg_20hz tuyarobot_msgs/srv/GetLatestAgvReport20Hz '{}'
```

### `get_agv_main_version`

- **功能说明**: 查询底盘固件主版本
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetFloat`（CLI: `tuyarobot_msgs/srv/GetFloat`）
- **ROS 名**:
  - `/chassis/get_agv_main_version`
- **请求字段**: 无。
- **返回语义**: `data` 为底盘固件主版本号。
- **返回/观测**: `success` → `message` → `data`（浮点版本号等） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_main_version tuyarobot_msgs/srv/GetFloat '{}'
```

### `get_agv_modify_version`

- **功能说明**: 查询底盘固件修订版本
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/chassis/get_agv_modify_version`
- **请求字段**: 无。
- **返回语义**: `data` 为底盘固件修订版本整数。
- **返回/观测**: `success` → `message` → `data`（固件修订版本整数） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_modify_version tuyarobot_msgs/srv/GetInt '{}'
```

### `set_agv_debug_state`

- **功能说明**: 设置底盘固件调试状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetInt`（CLI: `tuyarobot_msgs/srv/SetInt`）
- **ROS 名**:
  - `/chassis/set_agv_debug_state`
- **请求字段**: `data`（`int32`）。
- **参数范围**: `data` 为 `0~255` 的固件调试状态值；当前接口未定义各数值的日志类别名称，设置前应先读取并保留原值。
- **返回/观测**: `success` → `message` → `response_time_ms`；请求字段 `data`。
- **调用示例**:

```bash
ros2 service call /chassis/set_agv_debug_state tuyarobot_msgs/srv/SetInt "{data: 1}"
```

### `get_agv_debug_state`

- **功能说明**: 查询底盘固件调试状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/chassis/get_agv_debug_state`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `data`（固件调试状态原始值，`0~255`，无公开枚举名称） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_debug_state tuyarobot_msgs/srv/GetInt '{}'
```

### `get_agv_auto_report`

- **功能说明**: 查询底盘自动上报开关
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/chassis/get_agv_auto_report`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `data`（`0` 关闭，`1` 开启） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_auto_report tuyarobot_msgs/srv/GetInt '{}'
```

### `set_agv_led_color`

- **功能说明**: 设置底盘指示灯颜色
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetAgvLedColor`（CLI: `tuyarobot_msgs/srv/SetAgvLedColor`）
- **ROS 名**:
  - `/chassis/set_agv_led_color`
- **请求字段**: `red`（`int32`）、`green`（`int32`）、`blue`（`int32`）、`brightness`（`int32`）。
- **参数范围**: `red/green/blue/brightness` 均为整数，范围 `0~255`。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/set_agv_led_color tuyarobot_msgs/srv/SetAgvLedColor "{red: 0, green: 0, blue: 255, brightness: 255}"
```

### `agv_power_off`

- **功能说明**: 关闭底盘轮毂和升降机构电源
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/chassis/agv_power_off`
- **请求字段**: 无。
- **返回语义**: `success=true` 表示底盘下电命令执行成功。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/agv_power_off tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `is_agv_powered_on`

- **功能说明**: 查询底盘设备上电状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/chassis/is_agv_powered_on`
- **请求字段**: 无。
- **返回语义**: `data=1` 表示已上电，`data=0` 表示未上电或状态异常。
- **返回/观测**: `success` → `message`（异常原因）→ `data`（1=已上电，0=未上电或状态异常） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/is_agv_powered_on tuyarobot_msgs/srv/GetInt '{}'
```

### `set_agv_wheel_enabled`

- **功能说明**: 使能或失能底盘轮毂
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetAgvWheelEnabled`（CLI: `tuyarobot_msgs/srv/SetAgvWheelEnabled`）
- **ROS 名**:
  - `/chassis/set_agv_wheel_enabled`
- **请求字段**: `state`（`int32`）。
- **参数范围**: `state`：`0` 失能，`1` 使能。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/set_agv_wheel_enabled tuyarobot_msgs/srv/SetAgvWheelEnabled "{state: 1}"
```

### `get_agv_wheel_brake`

- **功能说明**: 查询底盘轮毂刹车状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/chassis/get_agv_wheel_brake`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `data`（`0` 关闭抱闸，`1` 打开抱闸） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_wheel_brake tuyarobot_msgs/srv/GetInt '{}'
```

### `set_agv_wheel_brake`

- **功能说明**: 打开或关闭底盘轮毂刹车
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetInt`（CLI: `tuyarobot_msgs/srv/SetInt`）
- **ROS 名**:
  - `/chassis/set_agv_wheel_brake`
- **请求字段**: `data`（`int32`）。
- **参数范围**: `data` 仅支持 `0` 或 `1`，`1=打开抱闸`，`0=释放抱闸`。
- **返回/观测**: `success` → `message` → `response_time_ms`；请求字段 `data`。
- **调用示例**:

```bash
ros2 service call /chassis/set_agv_wheel_brake tuyarobot_msgs/srv/SetInt "{data: 1}"
```

### `get_agv_move_state`

- **功能说明**: 查询轮毂与升降运动状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetAgvMoveState`（CLI: `tuyarobot_msgs/srv/GetAgvMoveState`）
- **ROS 名**:
  - `/chassis/get_agv_move_state`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `wheel_state` → `lift_state` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_move_state tuyarobot_msgs/srv/GetAgvMoveState '{}'
```

### `get_agv_robot_status`

#### Topic（发布/状态）

- **功能说明**: 发布底盘电量、TOF及电机错误
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `tuyarobot_msgs/AgvRobotStatus`（CLI: `tuyarobot_msgs/msg/AgvRobotStatus`）
- **ROS 名**:
  - `/chassis/get_agv_robot_status`
- **返回/观测**: 状态码与可读 message；仅在源 `seq` 更新时发布，hz 跟随自动上报源频。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /chassis/get_agv_robot_status --once
```

#### Service

- **功能说明**: 查询底盘电量、TOF及电机错误
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetAgvRobotStatus`（CLI: `tuyarobot_msgs/srv/GetAgvRobotStatus`）
- **ROS 名**:
  - `/chassis/service/get_agv_robot_status`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `status` → `battery_voltage` → `battery_level` → `battery_percent` → `left_motor_error` → `right_motor_error` → `lift_motor_error` → `tof_drop_uncalibrated` → `tof_drop_triggered` → `wheel_acc_mismatch` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/service/get_agv_robot_status tuyarobot_msgs/srv/GetAgvRobotStatus '{}'
```

### `get_agv_motors_run_sp`

- **功能说明**: 查询轮毂和升降电机速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/chassis/get_agv_motors_run_sp`
- **请求字段**: 无。
- **返回语义**: `data=[left_wheel, right_wheel, lift]`，依次为左轮、右轮和升降电机转速原始值。
- **返回/观测**: `success` → `message` → `data[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_motors_run_sp tuyarobot_msgs/srv/GetInts '{}'
```

### `get_agv_motors_current`

#### Topic（发布/状态）

- **功能说明**: 发布底盘三电机电流
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `std_msgs/Float32MultiArray`（CLI: `std_msgs/msg/Float32MultiArray`）
- **ROS 名**:
  - `/chassis/get_agv_motors_current`
- **返回语义**: `data=[left_wheel, right_wheel, lift]`，依次为左轮、右轮和升降电机电流，单位为 `A`。
- **返回/观测**: 电流随报告源 `seq` 更新发布一帧；缓存过期或上报未提供电流时停发，不重复发布旧缓存。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /chassis/get_agv_motors_current --once
```

#### Service

- **功能说明**: 查询底盘三电机电流
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/chassis/service/get_agv_motors_current`
- **请求字段**: 无。
- **返回语义**: `data=[left_wheel, right_wheel, lift]`，依次为左轮、右轮和升降电机原始整数计数，物理电流为 `data × 0.1 A`。
- **返回/观测**: 唯一按需真实电流读取入口；`success` → `message` → `data[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/service/get_agv_motors_current tuyarobot_msgs/srv/GetInts '{}'
```

### `get_agv_joints_status`

#### Topic（发布/状态）

- **功能说明**: 发布底盘综合状态兼容数据
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `tuyarobot_msgs/AgvRobotStatus`（CLI: `tuyarobot_msgs/msg/AgvRobotStatus`）
- **ROS 名**:
  - `/chassis/get_agv_joints_status`
- **返回/观测**: 状态码与可读 message；仅在源 `seq` 更新时发布，hz 跟随自动上报源频。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /chassis/get_agv_joints_status --once
```

#### Service

- **功能说明**: 兼容查询。等同底盘综合状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetAgvRobotStatus`（CLI: `tuyarobot_msgs/srv/GetAgvRobotStatus`）
- **ROS 名**:
  - `/chassis/service/get_agv_joints_status`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `status` → `battery_voltage` → `battery_level` → `battery_percent` → `left_motor_error` → `right_motor_error` → `lift_motor_error` → `tof_drop_uncalibrated` → `tof_drop_triggered` → `wheel_acc_mismatch` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/service/get_agv_joints_status tuyarobot_msgs/srv/GetAgvRobotStatus '{}'
```

### `get_agv_motors_temp`

- **功能说明**: 查询左右轮毂电机温度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/chassis/get_agv_motors_temp`
- **请求字段**: 无。
- **返回语义**: `data=[left_wheel, right_wheel]`，依次为左右轮毂电机温度，单位 `°C`。
- **返回/观测**: `success` → `message` → `data[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_motors_temp tuyarobot_msgs/srv/GetInts '{}'
```

### `get_agv_motor_drivers_temp`

- **功能说明**: 查询轮毂与升降驱动板温度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/chassis/get_agv_motor_drivers_temp`
- **请求字段**: 无。
- **返回语义**: `data=[hub_driver, lift_driver]`，依次为轮毂驱动板和升降驱动板温度，单位 `°C`。
- **返回/观测**: `success` → `message` → `data[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_motor_drivers_temp tuyarobot_msgs/srv/GetInts '{}'
```

### `get_agv_motors_loss_count`

- **功能说明**: 查询底盘电机通信丢包次数
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/chassis/get_agv_motors_loss_count`
- **请求字段**: 无。
- **返回语义**: `data[]` 为各设备通信丢帧计数，按设备协议槽位顺序排列。
- **返回/观测**: `success` → `message` → `data[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_motors_loss_count tuyarobot_msgs/srv/GetInts '{}'
```

### `set_agv_handle_state`

- **功能说明**: 设置底盘手柄状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetInt`（CLI: `tuyarobot_msgs/srv/SetInt`）
- **ROS 名**:
  - `/chassis/set_agv_handle_state`
- **请求字段**: `data`（`int32`）。
- **参数范围**: `data` 仅支持 `0` 或 `1`；`0` 关闭手柄控制，`1` 开启手柄控制。
- **返回/观测**: `success` → `message` → `response_time_ms`；请求字段 `data`。
- **调用示例**:

```bash
ros2 service call /chassis/set_agv_handle_state tuyarobot_msgs/srv/SetInt "{data: 1}"
```

### `get_agv_handle_state`

- **功能说明**: 查询底盘手柄状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/chassis/get_agv_handle_state`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `data`（`0` 关闭手柄控制，`1` 开启手柄控制） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_handle_state tuyarobot_msgs/srv/GetInt '{}'
```

### `get_agv_handle_data`

- **功能说明**: 查询手柄摇杆和按键数据
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetAgvHandleData`（CLI: `tuyarobot_msgs/srv/GetAgvHandleData`）
- **ROS 名**:
  - `/chassis/get_agv_handle_data`
- **请求字段**: 无。
- **返回语义**: `mode` 为手柄模式原始值，`115` 表示控制底盘模式；`right_ry` 为右摇杆RY原始值，居中约为 `127`，上推减小、下推增大；`select`、`l1`、`r1`、`l2`、`r2` 表示对应按键是否按下。
- **返回/观测**: `success` → `message` → `mode` → `right_ry` → `select` → `l1` → `r1` → `l2` → `r2` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_handle_data tuyarobot_msgs/srv/GetAgvHandleData '{}'
```

### `get_agv_tof_drop_threshold`

- **功能说明**: 查询五路TOF防跌落阈值
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/chassis/get_agv_tof_drop_threshold`
- **请求字段**: 无。
- **返回语义**: TOF 防跌落阈值，单位 cm，范围 `0~255`；`0` 关闭防跌落。设置后掉电不丢失；关闭后再开启需重新上电才会自动触发基准校准。真机验收优先先读当前值、原值写回。
- **返回/观测**: `success` → `message` → `data`（防跌落阈值，`0~255 cm`；`0` 表示关闭） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_tof_drop_threshold tuyarobot_msgs/srv/GetInt '{}'
```

### `set_agv_tof_drop_threshold`

- **功能说明**: 设置五路TOF防跌落阈值
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetInt`（CLI: `tuyarobot_msgs/srv/SetInt`）
- **ROS 名**:
  - `/chassis/set_agv_tof_drop_threshold`
- **请求字段**: `data`（`int32`）。
- **参数范围**: `data` 为 TOF 防跌落阈值，范围 `0~255 cm`；`0` 表示关闭。设置后掉电不丢失；关闭后再开启需重新上电才会自动触发基准校准。
- **返回/观测**: `success` → `message` → `response_time_ms`；请求字段 `data`。
- **调用示例**:

```bash
ros2 service call /chassis/set_agv_tof_drop_threshold tuyarobot_msgs/srv/SetInt "{data: 5}"
```

### `get_agv_tof_refs`

- **功能说明**: 查询五路TOF校准基准值
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetAgvTofRefs`（CLI: `tuyarobot_msgs/srv/GetAgvTofRefs`）
- **ROS 名**:
  - `/chassis/get_agv_tof_refs`
- **请求字段**: 无。
- **返回语义**: 5 路 TOF 基准，单位 cm；`calibrated=false` 时 `refs_cm` 为空（未上电/未校准）。
- **返回/观测**: `success` → `message` → `calibrated` → `refs_cm[]`（已校准时为 5 路 cm，未校准时为空）→ `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_tof_refs tuyarobot_msgs/srv/GetAgvTofRefs '{}'
```

### `set_agv_tof_restore_drop`

- **功能说明**: 恢复触发前TOF防跌落配置
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/chassis/set_agv_tof_restore_drop`
- **请求字段**: 无。
- **返回语义**: 恢复 TOF 防跌落功能；用于触发防跌落后回到平地，清除触发前 RAM 阈值。固件 ACK 可能约 2s，Worker 超时约 4s。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/set_agv_tof_restore_drop tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `set_agv_tof_factory_calibrate`

- **功能说明**: 标定五路TOF出厂基准值
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetAgvTofFactoryCalibrate`（CLI: `tuyarobot_msgs/srv/SetAgvTofFactoryCalibrate`）
- **ROS 名**:
  - `/chassis/set_agv_tof_factory_calibrate`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `data` → `response_time_ms`；标定约需 1 秒，请在合适地面和姿态下调用。
- **调用示例**:

```bash
ros2 service call /chassis/set_agv_tof_factory_calibrate tuyarobot_msgs/srv/SetAgvTofFactoryCalibrate '{}'
```

### `agv_firmware_flash`

- **功能说明**: 升级底盘主控固件
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/AgvFirmwareFlash`（CLI: `tuyarobot_msgs/srv/AgvFirmwareFlash`）
- **ROS 名**:
  - `/chassis/agv_firmware_flash`
- **请求字段**: `firmware_path`（`string`）、`skip_md5_check`（`bool`）。
- **参数范围**: `firmware_path` 为 Orin 本地已存在、非空的 `.bin` 文件，最大 496KiB；`skip_md5_check` 必须显式传入，`true` 跳过 MD5 白名单校验，`false` 启用校验。
- **返回/观测**: `success` → `message` → `version` → `response_time_ms`；耗时较长，升级期间禁止运动和断电。
- **调用示例**:

```bash
ros2 service call /chassis/agv_firmware_flash tuyarobot_msgs/srv/AgvFirmwareFlash "{firmware_path: '/path/to/agv.bin', skip_md5_check: true}"
```

### `get_agv_wheel_motor_acc`

- **功能说明**: 查询左右轮毂电机加速时间
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetAgvWheelMotorAcc`（CLI: `tuyarobot_msgs/srv/GetAgvWheelMotorAcc`）
- **ROS 名**:
  - `/chassis/get_agv_wheel_motor_acc`
- **请求字段**: 无。
- **返回语义**: `data` 为左右轮毂共用的加速时间，范围 `0~5000`，单位为毫秒。
- **返回/观测**: `success` → `message` → `data` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_wheel_motor_acc tuyarobot_msgs/srv/GetAgvWheelMotorAcc '{}'
```

### `set_agv_wheel_motor_acc`

- **功能说明**: 设置左右轮毂电机加速时间
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetAgvWheelMotorAcc`（CLI: `tuyarobot_msgs/srv/SetAgvWheelMotorAcc`）
- **ROS 名**:
  - `/chassis/set_agv_wheel_motor_acc`
- **请求字段**: `acceleration`（`int32`）。
- **参数范围**:

| 字段 | 范围 | 说明 |
|---|---|---|
| `acceleration` | `0~5000` | 左右轮毂共用的加速时间，单位为毫秒。 |

- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/set_agv_wheel_motor_acc tuyarobot_msgs/srv/SetAgvWheelMotorAcc "{acceleration: 300}"
```

### `get_agv_lift_motor_acc`

- **功能说明**: 查询升降柱电机加速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetAgvLiftMotorAcc`（CLI: `tuyarobot_msgs/srv/GetAgvLiftMotorAcc`）
- **ROS 名**:
  - `/chassis/get_agv_lift_motor_acc`
- **请求字段**: 无。
- **返回语义**: `data` 为升降电机加速度，单位为指令单位/s²，范围 0～65535。
- **返回/观测**: `success` → `message` → `data`（加速度，指令单位/s²） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_lift_motor_acc tuyarobot_msgs/srv/GetAgvLiftMotorAcc '{}'
```

### `set_agv_lift_motor_acc`

- **功能说明**: 设置升降柱电机加速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetAgvLiftMotorAcc`（CLI: `tuyarobot_msgs/srv/SetAgvLiftMotorAcc`）
- **ROS 名**:
  - `/chassis/set_agv_lift_motor_acc`
- **请求字段**: `acceleration`（`int32`）。
- **参数范围**: `acceleration` 为升降电机加速度，单位为指令单位/s²，范围 0～65535。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/set_agv_lift_motor_acc tuyarobot_msgs/srv/SetAgvLiftMotorAcc "{acceleration: 1000}"
```

### `set_agv_lift_calibrate`

- **功能说明**: 校准底盘升降机构
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/chassis/set_agv_lift_calibrate`
- **请求字段**: 无。
- **返回语义**: 成功表示校准命令已被设备接受；校准结果用 `is_agv_lift_init_calibrate` 查询。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/set_agv_lift_calibrate tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `is_agv_lift_init_calibrate`

- **功能说明**: 查询升降校准状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetAgvLiftInitCalibrate`（CLI: `tuyarobot_msgs/srv/GetAgvLiftInitCalibrate`）
- **ROS 名**:
  - `/chassis/is_agv_lift_init_calibrate`
- **请求字段**: 无。
- **返回语义**: `state=1` 表示已完成初始校准，`state=0` 表示未完成。
- **返回/观测**: `success` → `message` → `state` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/is_agv_lift_init_calibrate tuyarobot_msgs/srv/GetAgvLiftInitCalibrate '{}'
```

### `get_agv_lift_mileage`

- **功能说明**: 查询底盘升降行程
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetAgvLiftMileage`（CLI: `tuyarobot_msgs/srv/GetAgvLiftMileage`）
- **ROS 名**:
  - `/chassis/get_agv_lift_mileage`
- **请求字段**: 无。
- **返回语义**: `mileage_mm` 为升降柱绝对行程，单位 `mm`，正常范围 `0~560`。
- **返回/观测**: `success` → `message` → `mileage_mm` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_lift_mileage tuyarobot_msgs/srv/GetAgvLiftMileage '{}'
```

### `set_agv_lift_control`

- **功能说明**: 控制底盘升降位置
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetAgvLiftControl`（CLI: `tuyarobot_msgs/srv/SetAgvLiftControl`）
- **ROS 名**:
  - `/chassis/set_agv_lift_control`
- **请求字段**: `lift_mm`（`float64`）、`speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**: `lift_mm`：`0~560 mm`；`speed`：整数 `0~100`；`async_mode=true` 接收设备确认后返回，`false` 等待升降运动完成。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/set_agv_lift_control tuyarobot_msgs/srv/SetAgvLiftControl "{lift_mm: 50.0, speed: 20, async_mode: false}"
```

### `get_agv_lift_encoder`

- **功能说明**: 查询底盘升降编码器
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetAgvLiftEncoder`（CLI: `tuyarobot_msgs/srv/GetAgvLiftEncoder`）
- **ROS 名**:
  - `/chassis/get_agv_lift_encoder`
- **请求字段**: 无。
- **返回语义**: `encoder` 为升降电机编码器原始计数值，不是毫米行程。
- **返回/观测**: `success` → `message` → `encoder` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_lift_encoder tuyarobot_msgs/srv/GetAgvLiftEncoder '{}'
```

### `get_agv_zero_status`

- **功能说明**: 兼容查询。等同升降校准状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/chassis/get_agv_zero_status`
- **请求字段**: 无。
- **返回语义**: `data=1` 表示升降已完成初始校准，`data=0` 表示未完成。
- **返回/观测**: `success` → `message` → `data` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /chassis/get_agv_zero_status tuyarobot_msgs/srv/GetInt '{}'
```

<a id="upper"></a>
## 三、上半身接口说明

<a id="upper-conventions"></a>
### 使用约定

- **Namespace**：`/left_arm`、`/right_arm`、`/upper`（双臂聚合）。
- **发布频率**：上半身自动上报主 Topic 与三作用域字段 Topic 按 `upper_publish_hz` 定频发布最新有效缓存，默认100Hz，可配置为1～100Hz；该参数同时约束 HAL 自动上报缓存采样。`_safety_snapshot` 固定 20Hz。重复帧保留源 `seq` 和时间戳。点查接口为对应 Service。
- **关节**：单臂 8 值（J1–J7 角度 + J8 夹爪）；`/upper/send_upper_angles` 为 16 值（左 8 + 右 8）。J1～J7 单位为度，J8 开合量单位为 mm。
- **关节运动范围**：J1 `-160~160`、J2 `-65~110`、J3 `-160~160`、J4 `-164~-10`、J5 `-160~160`、J6 `-40~85`、J7 `-75~75` 单位为度；J8 `0~125` 单位为 mm。
- **发角 Topic `speeds`**：单臂 `[arm_speed, gripper_speed]`，双臂 `[left_arm, left_gripper, right_arm, right_gripper]`。各速度均为整数 `0~100`，其中 `0` 表示对应夹爪不运动。
- **双臂运动 Service**：角度用 `MoveDualUpperAngles`（`left_angles`/`right_angles`）；坐标用 `SendDualUpperCoords`（`left_pose`/`right_pose`）。Topic 仍可用拼接数组（`angles[16]` / `poses[2]`）。
- **双臂同目标 Service**：`/upper` 下仅含一个 `joint_id` 或 `coord_id`、一个目标值的 Service，会把同一关节或坐标指令同时作用于左右臂；左右目标不同时应使用带 `left_*`、`right_*` 字段的双臂 Service。
- **控制 Topic QoS**：RELIABLE + VOLATILE + KEEP_LAST；控制 Topic 默认 depth=10
- **状态 Topic QoS**：BEST_EFFORT + VOLATILE + KEEP_LAST；状态 Topic 默认 depth=10
- **Topic 无同步返回值**；需要回执用 `/<scope>/service/<name>` 运动 Service，或 `/<scope>/<name>` 查询 Service。
- **双形态运动接口**：`upper_jog_angle`、`upper_jog_coord`的Topic和Service固定向SDK传`_async=True`，其Service不包含`async_mode`字段；其余6类运动Topic不向SDK传`_async`并使用SDK默认配置，同名Service的`async_mode`映射到SDK `_async`。JOG在刷新模式由SDK拒绝下发。
- **点查 Service**：`/<scope>/get_upper_angles`（`GetScopedFloatValues`）、`/<scope>/get_upper_joints_current`（`GetScopedFloatValues`）、`/<scope>/get_upper_robot_status`（`GetUpperRobotStatus`）始终注册，调用时直调 SDK，路径不含 `/service/`。编码器仍为 `/<scope>/get_upper_encoders`。
- **自动上报 Topic**：`upper_auto_report_enabled=true`（默认）时 worker 维持 `set_upper_auto_report(1)`，缓存停止或过期后恢复 1；`false` 时首启 `set(0)`，新 `seq` 则压回 0。Real HAL 持续接纳源缓存；ROS 仅在源 `seq` 更新时转换并发布。`/upper/upper_auto_report` 与 `/left_arm|right_arm|upper/get_*_auto_report` 同源同频。点查用 `/<scope>/service/get_*_auto_report`。`power_protection_state` 从 0 变为 1 时会执行 `upper_stop`，并异步调用 `/chassis/agv_power_off`。Real 默认将最近 60s 缓存滚落到 `/home/tuya/tuya/logs/upper/report/upper_auto_report_YYYYMMDD_N.jsonl`。
- **审计日志**：`/home/tuya/tuya/logs/ros2/operation_YYYYMMDD.log`
- 本文示例仅写 Real。通过 `mock.launch.py` 启动时，上半身同名 Topic/Service 可用，但无真实硬件反馈。

<a id="upper-observe"></a>
### 常用观测命令

启动并 source 工作空间后，用下列命令核对**类型**与**发布频率**（Hz 含义见上方「发布频率」）。各接口明细只给 echo/call，不重复本节。

```bash
# Topic：类型、发布端、字段定义（流式为 *_auto_report）
ros2 topic type /left_arm/get_upper_angles_auto_report
ros2 topic info /left_arm/get_upper_angles_auto_report -v
ros2 interface show tuyarobot_msgs/msg/JointDegreeState

# Topic：发布频率（由 upper_publish_hz 控制，默认100Hz）
timeout 10 ros2 topic hz /left_arm/get_upper_angles_auto_report
timeout 10 ros2 topic hz /right_arm/get_upper_angles_auto_report
timeout 10 ros2 topic hz /upper/get_upper_angles_auto_report
timeout 10 ros2 topic hz /upper/upper_auto_report

# 内容更新：seq 是否随源采样变化
timeout 5s ros2 topic echo /upper/upper_auto_report --once --full-length

# Service：类型与字段定义（点查直调 SDK）
ros2 service type /left_arm/get_upper_angles
ros2 interface show tuyarobot_msgs/srv/GetScopedFloatValues
```

<a id="api-upper"></a>
### `clear_upper_error`

- **功能说明**: 清除指定关节或全部故障
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/ClearUpperError`（CLI: `tuyarobot_msgs/srv/ClearUpperError`）
- **ROS 名**:
  - `/left_arm/clear_upper_error`
  - `/right_arm/clear_upper_error`
  - `/upper/clear_upper_error`
- **请求字段**: `joint_id`（`int32`）。
- **参数范围**: `joint_id` 为 `1~8` 或 `254`；`254` 表示清除全部上半身关节和设备错误。
- **返回/观测**: `success` → `message` → `response_time_ms`；需显式传入 254 才清除全部关节/设备；ROS 不再代填。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/clear_upper_error tuyarobot_msgs/srv/ClearUpperError "{joint_id: 254}"

# 右臂 /right_arm
ros2 service call /right_arm/clear_upper_error tuyarobot_msgs/srv/ClearUpperError "{joint_id: 254}"

# 双臂 /upper
ros2 service call /upper/clear_upper_error tuyarobot_msgs/srv/ClearUpperError "{joint_id: 254}"
```

### `drag_teach_multi_record`

- **功能说明**: 将当前轨迹加入多段记录
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/left_arm/drag_teach_multi_record`
  - `/right_arm/drag_teach_multi_record`
  - `/upper/drag_teach_multi_record`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/drag_teach_multi_record tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 右臂 /right_arm
ros2 service call /right_arm/drag_teach_multi_record tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 双臂 /upper
ros2 service call /upper/drag_teach_multi_record tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `get_latest_upper_auto_report`

- **功能说明**: 读取双臂最新自动上报缓存
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetLatestUpperAutoReport`（CLI: `tuyarobot_msgs/srv/GetLatestUpperAutoReport`）
- **ROS 名**:
  - `/upper/get_latest_upper_auto_report`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `json`（Python SDK 自动上报正文直出）→ `age` → `timestamp` → `seq` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/get_latest_upper_auto_report tuyarobot_msgs/srv/GetLatestUpperAutoReport '{}'
```

### `get_upper_angles`

- **功能说明**: 查询上半身关节角度。直调 SDK；流式请订阅 `get_upper_angles_auto_report`。
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/left_arm/get_upper_angles`
  - `/right_arm/get_upper_angles`
  - `/upper/get_upper_angles`
- **请求字段**: 无。
- **返回语义**: 单臂 `values[]` 固定8项，按当前手臂J1～J8排列；`/upper` 固定16项，先左臂J1～J8，再右臂J1～J8；J1～J7 单位为度，J8 夹爪单位为 mm。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_angles tuyarobot_msgs/srv/GetScopedFloatValues '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_angles tuyarobot_msgs/srv/GetScopedFloatValues '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_angles tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `get_upper_angles_auto_report`

#### Topic（发布/状态）

- **功能说明**: 发布自动上报关节角度
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `tuyarobot_msgs/JointDegreeState`（CLI: `tuyarobot_msgs/msg/JointDegreeState`）
- **ROS 名**:
  - `/left_arm/get_upper_angles_auto_report`
- **返回语义**: `name[]/position_deg[]` 固定8项，按当前手臂J1～J8排列；J1～J7 单位为度，J8 夹爪单位为 mm（字段名仍为 `position_deg[]`）。
- **返回/观测**: `name[]` + `position_deg[]`（J1～J7 为度，J8 为 mm）；按 `upper_publish_hz` 发布最新有效缓存，缓存过期后停发。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /left_arm/get_upper_angles_auto_report --once
```

#### Service

- **功能说明**: 查询自动上报关节角度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/left_arm/service/get_upper_angles_auto_report`
- **请求字段**: 无。
- **返回语义**: `values[]` 固定8项，按当前手臂J1～J8排列；J1～J7 单位为度，J8 夹爪单位为 mm。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /left_arm/service/get_upper_angles_auto_report tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

#### Topic（发布/状态）

- **功能说明**: 发布自动上报关节角度
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `tuyarobot_msgs/JointDegreeState`（CLI: `tuyarobot_msgs/msg/JointDegreeState`）
- **ROS 名**:
  - `/right_arm/get_upper_angles_auto_report`
- **返回语义**: `name[]/position_deg[]` 固定8项，按当前手臂J1～J8排列；J1～J7 单位为度，J8 夹爪单位为 mm（字段名仍为 `position_deg[]`）。
- **返回/观测**: `name[]` + `position_deg[]`（J1～J7 为度，J8 为 mm）；按 `upper_publish_hz` 发布最新有效缓存，缓存过期后停发。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /right_arm/get_upper_angles_auto_report --once
```

#### Service

- **功能说明**: 查询自动上报关节角度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/right_arm/service/get_upper_angles_auto_report`
- **请求字段**: 无。
- **返回语义**: `values[]` 固定8项，按当前手臂J1～J8排列；J1～J7 单位为度，J8 夹爪单位为 mm。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /right_arm/service/get_upper_angles_auto_report tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

#### Topic（发布/状态）

- **功能说明**: 发布自动上报关节角度
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `tuyarobot_msgs/JointDegreeState`（CLI: `tuyarobot_msgs/msg/JointDegreeState`）
- **ROS 名**:
  - `/upper/get_upper_angles_auto_report`
- **返回语义**: `name[]/position_deg[]` 固定16项，先左臂J1～J8，再右臂J1～J8；J1～J7 单位为度，J8 夹爪单位为 mm（字段名仍为 `position_deg[]`）。
- **返回/观测**: `name[]` + `position_deg[]`（J1～J7 为度，J8 为 mm）；按 `upper_publish_hz` 发布最新有效缓存，缓存过期后停发。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /upper/get_upper_angles_auto_report --once
```

#### Service

- **功能说明**: 查询自动上报关节角度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/upper/service/get_upper_angles_auto_report`
- **请求字段**: 无。
- **返回语义**: `values[]` 固定16项，先左臂J1～J8，再右臂J1～J8；J1～J7 单位为度，J8 夹爪单位为 mm。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/service/get_upper_angles_auto_report tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `get_upper_auto_report`

- **功能说明**: 查询整机自动上报开关。不分左右臂
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/upper/get_upper_auto_report`
- **请求字段**: 无。
- **返回语义**: `data=0` 表示自动上报关闭，`data=1` 表示开启。
- **返回/观测**: `success` → `message` → `data`（`0` 关闭，`1` 开启） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/get_upper_auto_report tuyarobot_msgs/srv/GetInt '{}'
```

### `get_upper_collision_mode`

- **功能说明**: 查询关节碰撞检测开关
- **类型**: Service
- **消息/服务类型**: 单臂 `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）；双臂 `/upper` `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/left_arm/get_upper_collision_mode`
  - `/right_arm/get_upper_collision_mode`
  - `/upper/get_upper_collision_mode`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → 单臂 `data`，双臂 `data[]=[left,right]`（每项 `0` 关闭、`1` 开启） → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_collision_mode tuyarobot_msgs/srv/GetInt '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_collision_mode tuyarobot_msgs/srv/GetInt '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_collision_mode tuyarobot_msgs/srv/GetInts '{}'
```

### `get_upper_collision_threshold`

- **功能说明**: 查询关节碰撞阈值
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetUpperCollisionThresholds`（CLI: `tuyarobot_msgs/srv/GetUpperCollisionThresholds`）
- **ROS 名**:
  - `/left_arm/get_upper_collision_threshold`
  - `/right_arm/get_upper_collision_threshold`
  - `/upper/get_upper_collision_threshold`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `values` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_collision_threshold tuyarobot_msgs/srv/GetUpperCollisionThresholds '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_collision_threshold tuyarobot_msgs/srv/GetUpperCollisionThresholds '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_collision_threshold tuyarobot_msgs/srv/GetUpperCollisionThresholds '{}'
```

### `get_upper_control_mode`

- **功能说明**: 查询位置或力矩控制模式
- **类型**: Service
- **消息/服务类型**: 单臂 `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）；双臂 `/upper` `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/left_arm/get_upper_control_mode`
  - `/right_arm/get_upper_control_mode`
  - `/upper/get_upper_control_mode`
- **请求字段**: 无。
- **返回语义**: 控制模式：`0=位置`，`1=力矩`。单臂标量，`/upper` 为 `[left, right]`。
- **返回/观测**: `success` → `message` → 单臂 `data`，双臂 `data[]=[left,right]`（每项 `0` 位置控制、`1` 力矩控制） → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_control_mode tuyarobot_msgs/srv/GetInt '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_control_mode tuyarobot_msgs/srv/GetInt '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_control_mode tuyarobot_msgs/srv/GetInts '{}'
```

### `get_upper_coords`

- **功能说明**: 查询末端笛卡尔坐标
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetCartesianPoses`（CLI: `tuyarobot_msgs/srv/GetCartesianPoses`）
- **ROS 名**:
  - `/left_arm/get_upper_coords`
  - `/right_arm/get_upper_coords`
  - `/upper/get_upper_coords`
- **请求字段**: 无。
- **返回语义**: 单臂作用域返回6项 `[x,y,z,rx,ry,rz]`；`/upper` 返回12项，先左臂后右臂。`x/y/z` 单位为毫米，`rx/ry/rz` 单位为度。
- **返回/观测**: `success` → `message` → `poses` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_coords tuyarobot_msgs/srv/GetCartesianPoses '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_coords tuyarobot_msgs/srv/GetCartesianPoses '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_coords tuyarobot_msgs/srv/GetCartesianPoses '{}'
```

### `get_upper_coords_auto_report`

#### Topic（发布/状态）

- **功能说明**: 发布自动上报末端坐标
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `std_msgs/Float64MultiArray`（CLI: `std_msgs/msg/Float64MultiArray`）
- **ROS 名**:
  - `/left_arm/get_upper_coords_auto_report`
- **返回语义**: 返回当前手臂6项 `[x,y,z,rx,ry,rz]`；位置单位毫米，姿态单位度。
- **返回/观测**: 仅在源 `seq` 更新时发布一帧，hz 跟随自动上报源频；`--once` 取当前最新一帧。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /left_arm/get_upper_coords_auto_report --once
```

#### Service

- **功能说明**: 查询自动上报末端坐标
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetCartesianPoses`（CLI: `tuyarobot_msgs/srv/GetCartesianPoses`）
- **ROS 名**:
  - `/left_arm/service/get_upper_coords_auto_report`
- **请求字段**: 无。
- **返回语义**: 返回当前手臂6项 `[x,y,z,rx,ry,rz]`；位置单位毫米，姿态单位度。
- **返回/观测**: `success` → `message` → `poses` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /left_arm/service/get_upper_coords_auto_report tuyarobot_msgs/srv/GetCartesianPoses '{}'
```

#### Topic（发布/状态）

- **功能说明**: 发布自动上报末端坐标
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `std_msgs/Float64MultiArray`（CLI: `std_msgs/msg/Float64MultiArray`）
- **ROS 名**:
  - `/right_arm/get_upper_coords_auto_report`
- **返回语义**: 返回当前手臂6项 `[x,y,z,rx,ry,rz]`；位置单位毫米，姿态单位度。
- **返回/观测**: 仅在源 `seq` 更新时发布一帧，hz 跟随自动上报源频；`--once` 取当前最新一帧。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /right_arm/get_upper_coords_auto_report --once
```

#### Service

- **功能说明**: 查询自动上报末端坐标
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetCartesianPoses`（CLI: `tuyarobot_msgs/srv/GetCartesianPoses`）
- **ROS 名**:
  - `/right_arm/service/get_upper_coords_auto_report`
- **请求字段**: 无。
- **返回语义**: 返回当前手臂6项 `[x,y,z,rx,ry,rz]`；位置单位毫米，姿态单位度。
- **返回/观测**: `success` → `message` → `poses` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /right_arm/service/get_upper_coords_auto_report tuyarobot_msgs/srv/GetCartesianPoses '{}'
```

#### Topic（发布/状态）

- **功能说明**: 发布自动上报末端坐标
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `std_msgs/Float64MultiArray`（CLI: `std_msgs/msg/Float64MultiArray`）
- **ROS 名**:
  - `/upper/get_upper_coords_auto_report`
- **返回语义**: 返回12项，先左臂 `[x,y,z,rx,ry,rz]`，再右臂 `[x,y,z,rx,ry,rz]`；位置单位毫米，姿态单位度。
- **返回/观测**: 仅在源 `seq` 更新时发布一帧，hz 跟随自动上报源频；`--once` 取当前最新一帧。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /upper/get_upper_coords_auto_report --once
```

#### Service

- **功能说明**: 查询自动上报末端坐标
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetCartesianPoses`（CLI: `tuyarobot_msgs/srv/GetCartesianPoses`）
- **ROS 名**:
  - `/upper/service/get_upper_coords_auto_report`
- **请求字段**: 无。
- **返回语义**: 返回12项，先左臂 `[x,y,z,rx,ry,rz]`，再右臂 `[x,y,z,rx,ry,rz]`；位置单位毫米，姿态单位度。
- **返回/观测**: `success` → `message` → `poses` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/service/get_upper_coords_auto_report tuyarobot_msgs/srv/GetCartesianPoses '{}'
```

### `get_upper_debug_state`

- **功能说明**: 查询全局调试状态。不分左右臂
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/upper/get_debug_state`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `data`（全局调试状态原始值，`0~255`，无公开枚举名称） → `response_time_ms`。
- **调用示例**:

```bash
# 双臂 /upper
ros2 service call /upper/get_debug_state tuyarobot_msgs/srv/GetInt '{}'
```

### `get_upper_encoders`

- **功能说明**: 查询上半身编码器
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetUpperEncoders`（CLI: `tuyarobot_msgs/srv/GetUpperEncoders`）
- **ROS 名**:
  - `/left_arm/get_upper_encoders`
  - `/right_arm/get_upper_encoders`
  - `/upper/get_upper_encoders`
- **请求字段**: 无。
- **返回语义**: `/upper` 的 `left[]`、`right[]` 各 7 个整数（J1～J7）；`/left_arm` 仅填 `left[]`，`right[]` 为空；`/right_arm` 仅填 `right[]`，`left[]` 为空。
- **返回/观测**: `success` → `message` → `left[]` → `right[]` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_encoders tuyarobot_msgs/srv/GetUpperEncoders '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_encoders tuyarobot_msgs/srv/GetUpperEncoders '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_encoders tuyarobot_msgs/srv/GetUpperEncoders '{}'
```

### `get_upper_end_type`

- **功能说明**: 查询末端为法兰或工具
- **类型**: Service
- **消息/服务类型**: 单臂 `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）；双臂 `/upper` `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/left_arm/get_upper_end_type`
  - `/right_arm/get_upper_end_type`
  - `/upper/get_upper_end_type`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → 单臂 `data`，双臂 `data[]=[left,right]`（每项 `0` 法兰、`1` 工具） → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_end_type tuyarobot_msgs/srv/GetInt '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_end_type tuyarobot_msgs/srv/GetInt '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_end_type tuyarobot_msgs/srv/GetInts '{}'
```

### `get_upper_filter_len`

- **功能说明**: 查询关节滤波长度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetUpperFilterLen`（CLI: `tuyarobot_msgs/srv/GetUpperFilterLen`）
- **ROS 名**:
  - `/left_arm/get_upper_filter_len`
  - `/right_arm/get_upper_filter_len`
  - `/upper/get_upper_filter_len`
- **请求字段**: `rank`（`int32`）。
- **参数范围**: `rank` 为 `1~5` 的滤波参数编号；当前接口未定义各编号名称，查询时返回该编号对应的滤波长度。
- **返回/观测**: `success` → `message` → `values` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_filter_len tuyarobot_msgs/srv/GetUpperFilterLen "{rank: 1}"

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_filter_len tuyarobot_msgs/srv/GetUpperFilterLen "{rank: 1}"

# 双臂 /upper
ros2 service call /upper/get_upper_filter_len tuyarobot_msgs/srv/GetUpperFilterLen "{rank: 1}"
```

### `get_upper_fresh_mode`

- **功能说明**: 查询插补或刷新运动模式
- **类型**: Service
- **消息/服务类型**: 单臂 `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）；双臂 `/upper` `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/left_arm/get_upper_fresh_mode`
  - `/right_arm/get_upper_fresh_mode`
  - `/upper/get_upper_fresh_mode`
- **请求字段**: 无。
- **返回语义**: 0=插补，1=刷新。
- **返回/观测**: `success` → `message` → 单臂 `data`，双臂 `data[]=[left,right]`（每项 `0` 插补、`1` 刷新） → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_fresh_mode tuyarobot_msgs/srv/GetInt '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_fresh_mode tuyarobot_msgs/srv/GetInt '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_fresh_mode tuyarobot_msgs/srv/GetInts '{}'
```

### `get_upper_gripper_collision_threshold`

- **功能说明**: 查询夹爪碰撞阈值
- **类型**: Service
- **消息/服务类型**: 单臂 `tuyarobot_msgs/GetFloat`（CLI: `tuyarobot_msgs/srv/GetFloat`）；双臂 `/upper` `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/left_arm/get_upper_gripper_collision_threshold`
  - `/right_arm/get_upper_gripper_collision_threshold`
  - `/upper/get_upper_gripper_collision_threshold`
- **请求字段**: 无。
- **返回语义**: 单臂返回当前夹爪阈值，双臂按 `[left,right]` 返回；单位 `Nm`，范围 `0~1`，`0` 表示关闭碰撞检测。
- **返回/观测**: `success` → `message` → 单臂 `data`，双臂 `values[]=[left,right]` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_gripper_collision_threshold tuyarobot_msgs/srv/GetFloat '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_gripper_collision_threshold tuyarobot_msgs/srv/GetFloat '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_gripper_collision_threshold tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `get_upper_gripper_force`

- **功能说明**: 查询夹爪设定夹持力
- **类型**: Service
- **消息/服务类型**: 单臂 `tuyarobot_msgs/GetFloat`（CLI: `tuyarobot_msgs/srv/GetFloat`）；双臂 `/upper` `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/left_arm/get_upper_gripper_force`
  - `/right_arm/get_upper_gripper_force`
  - `/upper/get_upper_gripper_force`
- **请求字段**: 无。
- **返回语义**: 夹持力，单位 N，范围 `0.5~15.0`。
- **返回/观测**: `success` → `message` → 单臂 `data`，双臂 `values[]=[left,right]` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_gripper_force tuyarobot_msgs/srv/GetFloat '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_gripper_force tuyarobot_msgs/srv/GetFloat '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_gripper_force tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `get_upper_gripper_param`

- **功能说明**: 按地址查询夹爪参数
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetUpperParameter`（CLI: `tuyarobot_msgs/srv/GetUpperParameter`）
- **ROS 名**:
  - `/left_arm/get_upper_gripper_param`
  - `/right_arm/get_upper_gripper_param`
  - `/upper/get_upper_gripper_param`
- **请求字段**: `parameter_id`（`int32`）。
- **参数范围**: `parameter_id` 为 `1~254`；`1` 表示夹持力。
- **返回/观测**: `success` → `message` → `values` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_gripper_param tuyarobot_msgs/srv/GetUpperParameter "{parameter_id: 1}"

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_gripper_param tuyarobot_msgs/srv/GetUpperParameter "{parameter_id: 1}"

# 双臂 /upper
ros2 service call /upper/get_upper_gripper_param tuyarobot_msgs/srv/GetUpperParameter "{parameter_id: 1}"
```

### `get_upper_gripper_status`

- **功能说明**: 查询夹爪夹持或故障状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetUpperGripperStatus`（CLI: `tuyarobot_msgs/srv/GetUpperGripperStatus`）
- **ROS 名**:
  - `/left_arm/get_upper_gripper_status`
  - `/right_arm/get_upper_gripper_status`
  - `/upper/get_upper_gripper_status`
- **请求字段**: 无。
- **返回语义**: `left/right.status`：`0=空闲`、`1=张开中`、`2=闭合中`、`3=建力中`、`4=力保持`、`5=物体丢失`、`6=松开中`、`7=点动中`、`8=故障`；`state_message` 为对应状态文本。
- **返回/观测**: `success` → `message` → `left` → `right` → `response_time_ms`。单臂只填充对应侧（左臂仅 `left`，右臂仅 `right`），对侧保持默认空值；`/upper` 两侧都填。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_gripper_status tuyarobot_msgs/srv/GetUpperGripperStatus '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_gripper_status tuyarobot_msgs/srv/GetUpperGripperStatus '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_gripper_status tuyarobot_msgs/srv/GetUpperGripperStatus '{}'
```

### `get_upper_gripper_temp`

- **功能说明**: 查询夹爪MOS及驱动板温度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedIntValues`（CLI: `tuyarobot_msgs/srv/GetScopedIntValues`）
- **ROS 名**:
  - `/left_arm/get_upper_gripper_temp`
  - `/right_arm/get_upper_gripper_temp`
  - `/upper/get_upper_gripper_temp`
- **请求字段**: 无。
- **返回语义**: 温度数组，单位 ℃；单臂 `values=[mos,driver]`，双臂按 `[left_mos,left_driver,right_mos,right_driver]` 返回。
- **返回/观测**: `success` → `message` → `values` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_gripper_temp tuyarobot_msgs/srv/GetScopedIntValues '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_gripper_temp tuyarobot_msgs/srv/GetScopedIntValues '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_gripper_temp tuyarobot_msgs/srv/GetScopedIntValues '{}'
```

### `get_upper_is_in_position`

- **功能说明**: 判断关节或末端是否到位
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetUpperInPosition`（CLI: `tuyarobot_msgs/srv/GetUpperInPosition`）
- **ROS 名**:
  - `/left_arm/get_upper_is_in_position`
  - `/right_arm/get_upper_is_in_position`
  - `/upper/get_upper_is_in_position`
- **请求字段**: `mode`（`int32`）、`targets`（`float64[]`）。
- **参数范围**: `mode=0` 时，单臂 `targets` 固定8项、`/upper` 固定16项并先左后右；各关节范围为 J1 `-160~160°`、J2 `-65~110°`、J3 `-160~160°`、J4 `-164~-10°`、J5 `-160~160°`、J6 `-40~85°`、J7 `-75~75°`、J8 `0~125 mm`。`mode=1` 时，单臂固定6项 `[x,y,z,rx,ry,rz]`、`/upper` 固定12项并先左后右；X `-695~695 mm`，左臂 Y `-305~850 mm`，右臂 Y `-850~305 mm`，Z `-671~680 mm`，RX/RY/RZ `-180~180°`。
- **返回/观测**: `success` → `message` → `in_position` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_is_in_position tuyarobot_msgs/srv/GetUpperInPosition "{mode: 0, targets: [0,0,0,-90,0,0,0,0]}"

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_is_in_position tuyarobot_msgs/srv/GetUpperInPosition "{mode: 0, targets: [0,0,0,-90,0,0,0,0]}"

# 双臂 /upper
ros2 service call /upper/get_upper_is_in_position tuyarobot_msgs/srv/GetUpperInPosition "{mode: 0, targets: [0,0,0,-90,0,0,0,0, 0,0,0,-90,0,0,0,0]}"
```

### `get_upper_is_init_calibrate`

- **功能说明**: 查询各关节零位校准状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetUpperInitCalibrate`（CLI: `tuyarobot_msgs/srv/GetUpperInitCalibrate`）
- **ROS 名**:
  - `/left_arm/get_upper_is_init_calibrate`
  - `/right_arm/get_upper_is_init_calibrate`
  - `/upper/get_upper_is_init_calibrate`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `left_states` → `right_states` → `left_status` → `left_uncalibrated_joints` → `right_status` → `right_uncalibrated_joints` → `response_time_ms`。单臂只填充对应侧，对侧数组为空、status 为 0。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_is_init_calibrate tuyarobot_msgs/srv/GetUpperInitCalibrate '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_is_init_calibrate tuyarobot_msgs/srv/GetUpperInitCalibrate '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_is_init_calibrate tuyarobot_msgs/srv/GetUpperInitCalibrate '{}'
```

### `get_upper_is_moving`

- **功能说明**: 查询上半身运动状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/left_arm/get_upper_is_moving`
  - `/right_arm/get_upper_is_moving`
  - `/upper/get_upper_is_moving`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `data`（单臂 `0` 静止、`1` 运动中；`/upper` 仅在左右臂均运动时返回 `1`，否则返回 `0`） → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_is_moving tuyarobot_msgs/srv/GetInt '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_is_moving tuyarobot_msgs/srv/GetInt '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_is_moving tuyarobot_msgs/srv/GetInt '{}'
```

### `get_upper_is_paused`

- **功能说明**: 查询上半身暂停状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/left_arm/get_upper_is_paused`
  - `/right_arm/get_upper_is_paused`
  - `/upper/get_upper_is_paused`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `data`（单臂 `0` 未暂停、`1` 已暂停；`/upper` 仅在左右臂均暂停时返回 `1`，否则返回 `0`） → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_is_paused tuyarobot_msgs/srv/GetInt '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_is_paused tuyarobot_msgs/srv/GetInt '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_is_paused tuyarobot_msgs/srv/GetInt '{}'
```

### `get_upper_joint_acc`

- **功能说明**: 查询关节加速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/left_arm/get_upper_joint_acc`
  - `/right_arm/get_upper_joint_acc`
  - `/upper/get_upper_joint_acc`
- **请求字段**: 无。
- **返回语义**: 单臂作用域返回J1～J7的7个加速度值；`/upper` 依次返回左臂J1～J7、右臂J1～J7；每项范围 `0.001~0.1`。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_joint_acc tuyarobot_msgs/srv/GetScopedFloatValues '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_joint_acc tuyarobot_msgs/srv/GetScopedFloatValues '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_joint_acc tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `get_upper_joint_loss_count`

- **功能说明**: 查询关节通信丢包次数
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetUpperJointLossCount`（CLI: `tuyarobot_msgs/srv/GetUpperJointLossCount`）
- **ROS 名**:
  - `/left_arm/get_upper_joint_loss_count`
  - `/right_arm/get_upper_joint_loss_count`
  - `/upper/get_upper_joint_loss_count`
- **请求字段**: `joint_id`（`int32`）。
- **参数范围**: `joint_id` 为 `1~8`，表示需要查询的关节号。
- **返回语义**: 单臂 `data=[send_abnormal, read_abnormal]`；`/upper` 为 `[left_send, left_read, right_send, right_read]`，分别表示指定关节的发送异常和读取异常计数。
- **返回/观测**: `success` → `message` → `data[]` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_joint_loss_count tuyarobot_msgs/srv/GetUpperJointLossCount "{joint_id: 1}"

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_joint_loss_count tuyarobot_msgs/srv/GetUpperJointLossCount "{joint_id: 1}"

# 双臂 /upper
ros2 service call /upper/get_upper_joint_loss_count tuyarobot_msgs/srv/GetUpperJointLossCount "{joint_id: 1}"
```

### `get_upper_joints_current`

- **功能说明**: 查询上半身关节电流。直调 SDK；流式请订阅 `get_upper_joints_current_auto_report`。
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/left_arm/get_upper_joints_current`
  - `/right_arm/get_upper_joints_current`
  - `/upper/get_upper_joints_current`
- **请求字段**: 无。
- **返回语义**: 单臂 `values[]` 固定8项、双臂16项，均按J1～J8排列；双臂先左后右，单位为安培（`A`）。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_joints_current tuyarobot_msgs/srv/GetScopedFloatValues '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_joints_current tuyarobot_msgs/srv/GetScopedFloatValues '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_joints_current tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `get_upper_joints_current_auto_report`

#### Topic（发布/状态）

- **功能说明**: 发布自动上报关节电流
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `std_msgs/Float64MultiArray`（CLI: `std_msgs/msg/Float64MultiArray`）
- **ROS 名**:
  - `/left_arm/get_upper_joints_current_auto_report`
- **返回语义**: 固定8项，按当前手臂J1～J8排列，单位为安培（`A`），保留小数精度。
- **返回/观测**: `data[]`（`float64[]`）固定8项；仅在源 `seq` 更新时发布，hz 跟随自动上报源频。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /left_arm/get_upper_joints_current_auto_report --once
```

#### Service

- **功能说明**: 查询自动上报关节电流
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/left_arm/service/get_upper_joints_current_auto_report`
- **请求字段**: 无。
- **返回语义**: `values[]` 固定8项，按当前手臂J1～J8排列，单位为安培（`A`），保留小数精度。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /left_arm/service/get_upper_joints_current_auto_report tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

#### Topic（发布/状态）

- **功能说明**: 发布自动上报关节电流
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `std_msgs/Float64MultiArray`（CLI: `std_msgs/msg/Float64MultiArray`）
- **ROS 名**:
  - `/right_arm/get_upper_joints_current_auto_report`
- **返回语义**: 固定8项，按当前手臂J1～J8排列，单位为安培（`A`），保留小数精度。
- **返回/观测**: `data[]`（`float64[]`）固定8项；仅在源 `seq` 更新时发布，hz 跟随自动上报源频。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /right_arm/get_upper_joints_current_auto_report --once
```

#### Service

- **功能说明**: 查询自动上报关节电流
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/right_arm/service/get_upper_joints_current_auto_report`
- **请求字段**: 无。
- **返回语义**: `values[]` 固定8项，按当前手臂J1～J8排列，单位为安培（`A`），保留小数精度。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /right_arm/service/get_upper_joints_current_auto_report tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

#### Topic（发布/状态）

- **功能说明**: 发布自动上报关节电流
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `std_msgs/Float64MultiArray`（CLI: `std_msgs/msg/Float64MultiArray`）
- **ROS 名**:
  - `/upper/get_upper_joints_current_auto_report`
- **返回语义**: 固定16项，先左臂J1～J8，再右臂J1～J8，单位为安培（`A`），保留小数精度。
- **返回/观测**: `data[]`（`float64[]`）固定16项；仅在源 `seq` 更新时发布，hz 跟随自动上报源频。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /upper/get_upper_joints_current_auto_report --once
```

#### Service

- **功能说明**: 查询自动上报关节电流
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/upper/service/get_upper_joints_current_auto_report`
- **请求字段**: 无。
- **返回语义**: `values[]` 固定16项，先左臂J1～J8，再右臂J1～J8，单位为安培（`A`），保留小数精度。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/service/get_upper_joints_current_auto_report tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `get_upper_joints_max_angle`

- **功能说明**: 查询全局最大限位。不分左右臂
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/upper/get_upper_joints_max_angle`
- **请求字段**: 无。
- **返回语义**: `values[]` 固定8项，按J1～J8排列，表示当前保存的最大限位；J1～J7 单位为度，J8 夹爪单位为 mm。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/get_upper_joints_max_angle tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `get_upper_joints_min_angle`

- **功能说明**: 查询全局最小限位。不分左右臂
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/upper/get_upper_joints_min_angle`
- **请求字段**: 无。
- **返回语义**: `values[]` 固定8项，按J1～J8排列，表示当前保存的最小限位；J1～J7 单位为度，J8 夹爪单位为 mm。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/get_upper_joints_min_angle tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `get_upper_joints_run_sp`

- **功能说明**: 查询上半身关节速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/left_arm/get_upper_joints_run_sp`
  - `/right_arm/get_upper_joints_run_sp`
  - `/upper/get_upper_joints_run_sp`
- **请求字段**: 无。
- **返回语义**: 单臂 `values[]` 固定8项，按J1～J8排列；`/upper` 固定16项，先左臂后右臂；单位 `rpm`，保留小数精度。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_joints_run_sp tuyarobot_msgs/srv/GetScopedFloatValues '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_joints_run_sp tuyarobot_msgs/srv/GetScopedFloatValues '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_joints_run_sp tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `get_upper_joints_run_sp_auto_report`

#### Topic（发布/状态）

- **功能说明**: 发布自动上报关节速度
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `std_msgs/Float64MultiArray`（CLI: `std_msgs/msg/Float64MultiArray`）
- **ROS 名**:
  - `/left_arm/get_upper_joints_run_sp_auto_report`
- **返回语义**: 数组固定8项，按当前手臂J1～J8排列，单位 `rpm`。
- **返回/观测**: 仅在源 `seq` 更新时发布一帧，hz 跟随自动上报源频；`--once` 取当前最新一帧。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /left_arm/get_upper_joints_run_sp_auto_report --once
```

#### Service

- **功能说明**: 查询自动上报关节速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/left_arm/service/get_upper_joints_run_sp_auto_report`
- **请求字段**: 无。
- **返回语义**: 数组固定8项，按当前手臂J1～J8排列，单位 `rpm`。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /left_arm/service/get_upper_joints_run_sp_auto_report tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

#### Topic（发布/状态）

- **功能说明**: 发布自动上报关节速度
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `std_msgs/Float64MultiArray`（CLI: `std_msgs/msg/Float64MultiArray`）
- **ROS 名**:
  - `/right_arm/get_upper_joints_run_sp_auto_report`
- **返回语义**: 数组固定8项，按当前手臂J1～J8排列，单位 `rpm`。
- **返回/观测**: 仅在源 `seq` 更新时发布一帧，hz 跟随自动上报源频；`--once` 取当前最新一帧。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /right_arm/get_upper_joints_run_sp_auto_report --once
```

#### Service

- **功能说明**: 查询自动上报关节速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/right_arm/service/get_upper_joints_run_sp_auto_report`
- **请求字段**: 无。
- **返回语义**: 数组固定8项，按当前手臂J1～J8排列，单位 `rpm`。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /right_arm/service/get_upper_joints_run_sp_auto_report tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

#### Topic（发布/状态）

- **功能说明**: 发布自动上报关节速度
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `std_msgs/Float64MultiArray`（CLI: `std_msgs/msg/Float64MultiArray`）
- **ROS 名**:
  - `/upper/get_upper_joints_run_sp_auto_report`
- **返回语义**: 数组固定16项，先左臂J1～J8，再右臂J1～J8，单位 `rpm`。
- **返回/观测**: 仅在源 `seq` 更新时发布一帧，hz 跟随自动上报源频；`--once` 取当前最新一帧。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /upper/get_upper_joints_run_sp_auto_report --once
```

#### Service

- **功能说明**: 查询自动上报关节速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/upper/service/get_upper_joints_run_sp_auto_report`
- **请求字段**: 无。
- **返回语义**: 数组固定16项，先左臂J1～J8，再右臂J1～J8，单位 `rpm`。
- **返回/观测**: `success` → `message` → `values[]` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/service/get_upper_joints_run_sp_auto_report tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `get_upper_joints_temp`

- **功能说明**: 查询上半身关节温度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/left_arm/get_upper_joints_temp`
  - `/right_arm/get_upper_joints_temp`
  - `/upper/get_upper_joints_temp`
- **请求字段**: 无。
- **返回语义**: 单臂 `data[]` 固定14项：前7项为J1～J7 MOS温度，后7项为J1～J7驱动板温度；`/upper` 固定28项，先左臂14项后右臂14项；单位 `°C`。
- **返回/观测**: `success` → `message` → `data[]` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_joints_temp tuyarobot_msgs/srv/GetInts '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_joints_temp tuyarobot_msgs/srv/GetInts '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_joints_temp tuyarobot_msgs/srv/GetInts '{}'
```

### `get_upper_main_version`

- **功能说明**: 查询上半身主控版本。不分左右臂
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetFloat`（CLI: `tuyarobot_msgs/srv/GetFloat`）
- **ROS 名**:
  - `/upper/get_upper_main_version`
- **请求字段**: 无。
- **返回语义**: `data` 为上半身主控固件主版本号。
- **返回/观测**: `success` → `message` → `data` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/get_upper_main_version tuyarobot_msgs/srv/GetFloat '{}'
```

### `get_upper_modify_version`

- **功能说明**: 查询上半身修订版本。不分左右臂
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/upper/get_upper_modify_version`
- **请求字段**: 无。
- **返回语义**: `data` 为上半身主控固件修订版本整数。
- **返回/观测**: `success` → `message` → `data`（固件修订版本整数） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/get_upper_modify_version tuyarobot_msgs/srv/GetInt '{}'
```

### `get_upper_model_direction`

- **功能说明**: 查询关节模型方向配置
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/left_arm/get_upper_model_direction`
  - `/right_arm/get_upper_model_direction`
  - `/upper/get_upper_model_direction`
- **请求字段**: 无。
- **返回语义**: 单臂 `data[]` 固定7项，按J1～J7排列；`/upper` 固定14项，先左臂后右臂；每项为方向值 `0/1`。
- **返回/观测**: `success` → `message` → `data[]` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_model_direction tuyarobot_msgs/srv/GetInts '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_model_direction tuyarobot_msgs/srv/GetInts '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_model_direction tuyarobot_msgs/srv/GetInts '{}'
```

### `get_upper_movement_type`

- **功能说明**: 查询上半身运动类型
- **类型**: Service
- **消息/服务类型**: 单臂 `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）；双臂 `/upper` `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/left_arm/get_upper_movement_type`
  - `/right_arm/get_upper_movement_type`
  - `/upper/get_upper_movement_type`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → 单臂 `data`，双臂 `data[]=[left,right]`（每项为 `0~4` 的运动类型编号，当前接口未定义编号名称） → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_movement_type tuyarobot_msgs/srv/GetInt '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_movement_type tuyarobot_msgs/srv/GetInt '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_movement_type tuyarobot_msgs/srv/GetInts '{}'
```

### `get_upper_plan_acc`

- **功能说明**: 查询角度或坐标规划加速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetUpperPlanValues`（CLI: `tuyarobot_msgs/srv/GetUpperPlanValues`）
- **ROS 名**:
  - `/left_arm/get_upper_plan_acc`
  - `/right_arm/get_upper_plan_acc`
  - `/upper/get_upper_plan_acc`
- **请求字段**: `mode`（`int32`）。
- **参数范围**: `mode` 仅支持 `0` 或 `1`；`0=角度规划`，`1=坐标规划`。
- **返回语义**: 单臂作用域返回当前臂的规划加速度；`/upper` 按 `[left, right]` 返回。角度规划范围 `1~200`，坐标规划范围 `1~400`。
- **返回/观测**: `success` → `message` → `values` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_plan_acc tuyarobot_msgs/srv/GetUpperPlanValues "{mode: 0}"

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_plan_acc tuyarobot_msgs/srv/GetUpperPlanValues "{mode: 0}"

# 双臂 /upper
ros2 service call /upper/get_upper_plan_acc tuyarobot_msgs/srv/GetUpperPlanValues "{mode: 0}"
```

### `get_upper_plan_sp`

- **功能说明**: 查询角度或坐标规划速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetUpperPlanValues`（CLI: `tuyarobot_msgs/srv/GetUpperPlanValues`）
- **ROS 名**:
  - `/left_arm/get_upper_plan_sp`
  - `/right_arm/get_upper_plan_sp`
  - `/upper/get_upper_plan_sp`
- **请求字段**: `mode`（`int32`）。
- **参数范围**: `mode` 仅支持 `0` 或 `1`，`0=角度规划`，`1=坐标规划`。
- **返回/观测**: `success` → `message` → `values` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_plan_sp tuyarobot_msgs/srv/GetUpperPlanValues "{mode: 0}"

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_plan_sp tuyarobot_msgs/srv/GetUpperPlanValues "{mode: 0}"

# 双臂 /upper
ros2 service call /upper/get_upper_plan_sp tuyarobot_msgs/srv/GetUpperPlanValues "{mode: 0}"
```

### `get_upper_reference_frame`

- **功能说明**: 查询全局参考系。不分左右臂
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）
- **ROS 名**:
  - `/upper/get_upper_reference_frame`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `data`（`0` 基座坐标系，`1` 世界坐标系） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/get_upper_reference_frame tuyarobot_msgs/srv/GetInt '{}'
```

### `get_upper_robot_status`

- **功能说明**: 查询上半身综合状态。直调 SDK；流式请订阅 `get_upper_robot_status_auto_report`。
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetUpperRobotStatus`（CLI: `tuyarobot_msgs/srv/GetUpperRobotStatus`）
- **ROS 名**:
  - `/left_arm/get_upper_robot_status`
  - `/right_arm/get_upper_robot_status`
  - `/upper/get_upper_robot_status`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `status` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_robot_status tuyarobot_msgs/srv/GetUpperRobotStatus '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_robot_status tuyarobot_msgs/srv/GetUpperRobotStatus '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_robot_status tuyarobot_msgs/srv/GetUpperRobotStatus '{}'
```

### `get_upper_robot_status_auto_report`

#### Topic（发布/状态）

- **功能说明**: 发布自动上报综合状态
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `tuyarobot_msgs/RobotStatus`（CLI: `tuyarobot_msgs/msg/RobotStatus`）
- **ROS 名**:
  - `/left_arm/get_upper_robot_status_auto_report`
- **返回/观测**: 状态码与可读 message；仅在源 `seq` 更新时发布，hz 跟随自动上报源频。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /left_arm/get_upper_robot_status_auto_report --once
```

#### Service

- **功能说明**: 查询自动上报综合状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetUpperRobotStatus`（CLI: `tuyarobot_msgs/srv/GetUpperRobotStatus`）
- **ROS 名**:
  - `/left_arm/service/get_upper_robot_status_auto_report`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `status` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /left_arm/service/get_upper_robot_status_auto_report tuyarobot_msgs/srv/GetUpperRobotStatus '{}'
```

#### Topic（发布/状态）

- **功能说明**: 发布自动上报综合状态
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `tuyarobot_msgs/RobotStatus`（CLI: `tuyarobot_msgs/msg/RobotStatus`）
- **ROS 名**:
  - `/right_arm/get_upper_robot_status_auto_report`
- **返回/观测**: 状态码与可读 message；仅在源 `seq` 更新时发布，hz 跟随自动上报源频。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /right_arm/get_upper_robot_status_auto_report --once
```

#### Service

- **功能说明**: 查询自动上报综合状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetUpperRobotStatus`（CLI: `tuyarobot_msgs/srv/GetUpperRobotStatus`）
- **ROS 名**:
  - `/right_arm/service/get_upper_robot_status_auto_report`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `status` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /right_arm/service/get_upper_robot_status_auto_report tuyarobot_msgs/srv/GetUpperRobotStatus '{}'
```

#### Topic（发布/状态）

- **功能说明**: 发布自动上报综合状态
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `tuyarobot_msgs/RobotStatus`（CLI: `tuyarobot_msgs/msg/RobotStatus`）
- **ROS 名**:
  - `/upper/get_upper_robot_status_auto_report`
- **返回/观测**: 状态码与可读 message；仅在源 `seq` 更新时发布，hz 跟随自动上报源频。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /upper/get_upper_robot_status_auto_report --once
```

#### Service

- **功能说明**: 查询自动上报综合状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetUpperRobotStatus`（CLI: `tuyarobot_msgs/srv/GetUpperRobotStatus`）
- **ROS 名**:
  - `/upper/service/get_upper_robot_status_auto_report`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `status` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/service/get_upper_robot_status_auto_report tuyarobot_msgs/srv/GetUpperRobotStatus '{}'
```

### `get_upper_tool_modify_version`

- **功能说明**: 查询末端工具固件修订版本
- **类型**: Service
- **消息/服务类型**: 单臂 `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）；双臂 `/upper` `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/left_arm/get_upper_tool_modify_version`
  - `/right_arm/get_upper_tool_modify_version`
  - `/upper/get_upper_tool_modify_version`
- **请求字段**: 无。
- **返回语义**: 单臂 `data`、双臂 `data[]=[left,right]`，均为末端工具固件修订版本整数。
- **返回/观测**: `success` → `message` → 单臂 `data`，双臂 `data[]=[left,right]`（每项为工具固件修订版本整数） → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_tool_modify_version tuyarobot_msgs/srv/GetInt '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_tool_modify_version tuyarobot_msgs/srv/GetInt '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_tool_modify_version tuyarobot_msgs/srv/GetInts '{}'
```

### `get_upper_tool_reference`

- **功能说明**: 查询工具参考坐标
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetCartesianPoses`（CLI: `tuyarobot_msgs/srv/GetCartesianPoses`）
- **ROS 名**:
  - `/left_arm/get_upper_tool_reference`
  - `/right_arm/get_upper_tool_reference`
  - `/upper/get_upper_tool_reference`
- **请求字段**: 无。
- **返回语义**: 单臂作用域返回6项 `[x,y,z,rx,ry,rz]`；`/upper` 先返回左臂6项，再返回右臂6项。位置单位毫米，姿态单位度。
- **返回/观测**: `success` → `message` → `poses` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_tool_reference tuyarobot_msgs/srv/GetCartesianPoses '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_tool_reference tuyarobot_msgs/srv/GetCartesianPoses '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_tool_reference tuyarobot_msgs/srv/GetCartesianPoses '{}'
```

### `get_upper_tool_version`

- **功能说明**: 查询末端工具固件主版本
- **类型**: Service
- **消息/服务类型**: 单臂 `tuyarobot_msgs/GetFloat`（CLI: `tuyarobot_msgs/srv/GetFloat`）；双臂 `/upper` `tuyarobot_msgs/GetScopedFloatValues`（CLI: `tuyarobot_msgs/srv/GetScopedFloatValues`）
- **ROS 名**:
  - `/left_arm/get_upper_tool_version`
  - `/right_arm/get_upper_tool_version`
  - `/upper/get_upper_tool_version`
- **请求字段**: 无。
- **返回语义**: 单臂 `data`、双臂 `values[]=[left,right]`，均为末端工具固件主版本号。
- **返回/观测**: `success` → `message` → 单臂 `data`，双臂 `values[]` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_tool_version tuyarobot_msgs/srv/GetFloat '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_tool_version tuyarobot_msgs/srv/GetFloat '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_tool_version tuyarobot_msgs/srv/GetScopedFloatValues '{}'
```

### `get_upper_vr_mode`

- **功能说明**: 查询VR控制开关
- **类型**: Service
- **消息/服务类型**: 单臂 `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）；双臂 `/upper` `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/left_arm/get_upper_vr_mode`
  - `/right_arm/get_upper_vr_mode`
  - `/upper/get_upper_vr_mode`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → 单臂 `data`，双臂 `data[]=[left,right]`（每项 `0` 关闭、`1` 开启） → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_vr_mode tuyarobot_msgs/srv/GetInt '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_vr_mode tuyarobot_msgs/srv/GetInt '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_vr_mode tuyarobot_msgs/srv/GetInts '{}'
```

### `get_upper_world_reference`

- **功能说明**: 查询世界参考坐标。不分左右臂
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetCartesianPoses`（CLI: `tuyarobot_msgs/srv/GetCartesianPoses`）
- **ROS 名**:
  - `/upper/get_upper_world_reference`
- **请求字段**: 无。
- **返回语义**: 返回6项 `[x,y,z,rx,ry,rz]`；位置单位毫米，姿态单位度。
- **返回/观测**: `success` → `message` → `poses` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/get_upper_world_reference tuyarobot_msgs/srv/GetCartesianPoses '{}'
```

### `get_upper_zero_encoder`

- **功能说明**: 查询关节零位原始编码器
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/left_arm/get_upper_zero_encoder`
  - `/right_arm/get_upper_zero_encoder`
  - `/upper/get_upper_zero_encoder`
- **请求字段**: 无。
- **返回语义**: 单臂 `data[]` 固定7项，按J1～J7排列；`/upper` 固定14项，先左臂后右臂；各项为零位编码器原始计数。
- **返回/观测**: `success` → `message` → `data[]` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/get_upper_zero_encoder tuyarobot_msgs/srv/GetInts '{}'

# 右臂 /right_arm
ros2 service call /right_arm/get_upper_zero_encoder tuyarobot_msgs/srv/GetInts '{}'

# 双臂 /upper
ros2 service call /upper/get_upper_zero_encoder tuyarobot_msgs/srv/GetInts '{}'
```

### `is_upper_powered_on`

- **功能说明**: 查询上半身上电状态
- **类型**: Service
- **消息/服务类型**: 单臂 `tuyarobot_msgs/GetInt`（CLI: `tuyarobot_msgs/srv/GetInt`）；双臂 `/upper` `tuyarobot_msgs/GetInts`（CLI: `tuyarobot_msgs/srv/GetInts`）
- **ROS 名**:
  - `/left_arm/is_upper_powered_on`
  - `/right_arm/is_upper_powered_on`
  - `/upper/is_upper_powered_on`
- **请求字段**: 无。
- **返回语义**: 单臂返回 `data`，双臂返回 `data[]=[left,right]`；每项可能为 `0/1/2`，仅 `1` 表示已上电，`0` 表示未上电，`2` 表示设备返回的其他状态。
- **返回/观测**: `success` → `message` → 单臂 `data`，双臂 `data[]=[left,right]`（每项保留原始 `0/1/2` 状态值） → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/is_upper_powered_on tuyarobot_msgs/srv/GetInt '{}'

# 右臂 /right_arm
ros2 service call /right_arm/is_upper_powered_on tuyarobot_msgs/srv/GetInt '{}'

# 双臂 /upper
ros2 service call /upper/is_upper_powered_on tuyarobot_msgs/srv/GetInts '{}'
```

### `get_upper_lift_coords`

- **功能说明**: 读取末端坐标并补偿升降柱高度
- **类型**: Service
- **消息/服务类型**: 单臂 `tuyarobot_msgs/GetUpperLiftCoords`（CLI: `tuyarobot_msgs/srv/GetUpperLiftCoords`）；双臂 `tuyarobot_msgs/GetDualUpperLiftCoords`（CLI: `tuyarobot_msgs/srv/GetDualUpperLiftCoords`）
- **ROS 名**:
  - `/left_arm/get_upper_lift_coords`
  - `/right_arm/get_upper_lift_coords`
  - `/upper/get_upper_lift_coords`
- **请求字段**: 无。
- **升降里程来源**: `get_*` / `preview_*` 在未显式提供 `height` 时，以及全部 `send_*` 升降补偿接口，均由上半身节点通过 `/chassis/get_agv_lift_mileage` 获取当前里程并传给 Python SDK，不会重复打开底盘串口；底盘服务不可用、超时或读取失败时，`success=false`，`message` 保留对应失败原因。
- **返回/观测**: `success` → `message`。成功时 `message` 为 Python SDK `data` 的 `repr`（`raw_*` 与补偿坐标相同时省略）；失败时 `message` 为 Python SDK/桥接错误原文。
- **调用示例**:

```bash
# 左臂
ros2 service call /left_arm/get_upper_lift_coords tuyarobot_msgs/srv/GetUpperLiftCoords '{}'

# 右臂
ros2 service call /right_arm/get_upper_lift_coords tuyarobot_msgs/srv/GetUpperLiftCoords '{}'

# 双臂
ros2 service call /upper/get_upper_lift_coords tuyarobot_msgs/srv/GetDualUpperLiftCoords '{}'
```

### `send_upper_angle`

#### Topic（订阅/控制）

- **功能说明**: 控制单个关节角度
- **类型**: Topic（订阅/控制）
- **消息/服务类型**: `tuyarobot_msgs/UpperAngleCommand`（CLI: `tuyarobot_msgs/msg/UpperAngleCommand`）
- **ROS 名**:
  - `/left_arm/send_upper_angle`
  - `/right_arm/send_upper_angle`
  - `/upper/send_upper_angle`
- **消息字段**: `joint_id`（`int32`）、`angle`（`float64`）、`speed`（`int32`）。
- **参数范围**:

| 字段 | 范围 | 说明 |
|---|---|---|
| `joint_id` | `1~8` | J8为夹爪。 |
| `angle` | J1 `-160~160`，J2 `-65~110`，J3 `-160~160`，J4 `-164~-10`，J5 `-160~160`，J6 `-40~85`，J7 `-75~75`，J8 `0~125` | J1～J7 为目标角度（度），J8 为夹爪开合量（mm）。 |
| `speed` | `1~100` | 整数运动速度。 |

- **返回/观测**: 无同步回包；成功与否看 operation 审计日志；状态用对应 get_* Topic/Service 观测。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 topic pub -w 1 --keep-alive 2 --once /left_arm/send_upper_angle tuyarobot_msgs/msg/UpperAngleCommand "{joint_id: 2, angle: 10.0, speed: 20}"

# 右臂 /right_arm
ros2 topic pub -w 1 --keep-alive 2 --once /right_arm/send_upper_angle tuyarobot_msgs/msg/UpperAngleCommand "{joint_id: 2, angle: 10.0, speed: 20}"

# 双臂 /upper
ros2 topic pub -w 1 --keep-alive 2 --once /upper/send_upper_angle tuyarobot_msgs/msg/UpperAngleCommand "{joint_id: 2, angle: 10.0, speed: 20}"
```

#### Service

- **功能说明**: 控制单个关节角度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SendUpperAngle`（CLI: `tuyarobot_msgs/srv/SendUpperAngle`）
- **ROS 名**:
  - `/left_arm/service/send_upper_angle`
- **请求字段**: `joint_id`（`int32`）、`angle`（`float64`）、`speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**:

| 字段 | 范围 | 说明 |
|---|---|---|
| `joint_id` | `1~8` | J8为夹爪。 |
| `angle` | J1 `-160~160`，J2 `-65~110`，J3 `-160~160`，J4 `-164~-10`，J5 `-160~160`，J6 `-40~85`，J7 `-75~75`，J8 `0~125` | J1～J7 为目标角度（度），J8 为夹爪开合量（mm）。 |
| `speed` | `1~100` 的整数 | 运动速度。 |

- **返回/观测**: `success` → `message` → `result_value` → `has_left_gripper_feedback` → `left_gripper_status_code` → `left_gripper_message` → `has_right_gripper_feedback` → `right_gripper_status_code` → `right_gripper_message` → `diagnostics` → `response_time_ms`。`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。
- **调用示例**:

```bash
ros2 service call /left_arm/service/send_upper_angle tuyarobot_msgs/srv/SendUpperAngle "{joint_id: 1, angle: 10.0, speed: 20, async_mode: false}"
```

#### Service

- **功能说明**: 控制单个关节角度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SendUpperAngle`（CLI: `tuyarobot_msgs/srv/SendUpperAngle`）
- **ROS 名**:
  - `/right_arm/service/send_upper_angle`
- **请求字段**: `joint_id`（`int32`）、`angle`（`float64`）、`speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**:

| 字段 | 范围 | 说明 |
|---|---|---|
| `joint_id` | `1~8` | J8为夹爪。 |
| `angle` | J1 `-160~160`，J2 `-65~110`，J3 `-160~160`，J4 `-164~-10`，J5 `-160~160`，J6 `-40~85`，J7 `-75~75`，J8 `0~125` | J1～J7 为目标角度（度），J8 为夹爪开合量（mm）。 |
| `speed` | `1~100` 的整数 | 运动速度。 |

- **返回/观测**: `success` → `message` → `result_value` → `has_left_gripper_feedback` → `left_gripper_status_code` → `left_gripper_message` → `has_right_gripper_feedback` → `right_gripper_status_code` → `right_gripper_message` → `diagnostics` → `response_time_ms`。`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。
- **调用示例**:

```bash
ros2 service call /right_arm/service/send_upper_angle tuyarobot_msgs/srv/SendUpperAngle "{joint_id: 1, angle: 10.0, speed: 20, async_mode: false}"
```

#### Service

- **功能说明**: 同时控制双臂的同一关节角度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SendUpperAngle`（CLI: `tuyarobot_msgs/srv/SendUpperAngle`）
- **ROS 名**:
  - `/upper/service/send_upper_angle`
- **请求字段**: `joint_id`（`int32`）、`angle`（`float64`）、`speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**:

| 字段 | 范围 | 说明 |
|---|---|---|
| `joint_id` | `1~8` | 同一编号同时作用于左右臂；J8为夹爪。 |
| `angle` | J1 `-160~160`，J2 `-65~110`，J3 `-160~160`，J4 `-164~-10`，J5 `-160~160`，J6 `-40~85`，J7 `-75~75`，J8 `0~125` | J1～J7 为目标角度（度），J8 为夹爪开合量（mm）。 |
| `speed` | `1~100` 的整数 | 运动速度。 |

- **返回/观测**: `success` → `message` → `result_value` → `has_left_gripper_feedback` → `left_gripper_status_code` → `left_gripper_message` → `has_right_gripper_feedback` → `right_gripper_status_code` → `right_gripper_message` → `diagnostics` → `response_time_ms`。`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。
- **调用示例**:

```bash
ros2 service call /upper/service/send_upper_angle tuyarobot_msgs/srv/SendUpperAngle "{joint_id: 1, angle: 10.0, speed: 20, async_mode: false}"
```

### `send_upper_angles`

#### Topic（订阅/控制）

- **功能说明**: 控制多关节角度
- **类型**: Topic（订阅/控制）
- **消息/服务类型**: `tuyarobot_msgs/UpperAnglesCommand`（CLI: `tuyarobot_msgs/msg/UpperAnglesCommand`）
- **ROS 名**:
  - `/left_arm/send_upper_angles`
  - `/right_arm/send_upper_angles`
  - `/upper/send_upper_angles`
- **消息字段**: `angles`（`float64[]`）、`speeds`（`int32[]`）。
- **参数范围**:

| 字段 | 范围 | 说明 |
|---|---|---|
| `angles[]` | 单臂8项；`/upper` 16项 | 单臂按J1～J8；双臂先左后右。J1 `-160~160`，J2 `-65~110`，J3 `-160~160`，J4 `-164~-10`，J5 `-160~160`，J6 `-40~85`，J7 `-75~75` 单位为度；J8 `0~125` 单位为 mm。 |
| `speeds[]` | 单臂2项；`/upper` 4项 | 单臂 `[arm_speed, gripper_speed]`；双臂 `[left_arm_speed, left_gripper_speed, right_arm_speed, right_gripper_speed]`。手臂速度 `1~100`，夹爪速度为 `0` 或 `1~100`。 |

- **返回/观测**: 无同步回包；成功与否看 operation 审计日志；状态用对应 get_* Topic/Service 观测。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 topic pub -w 1 --keep-alive 2 --once /left_arm/send_upper_angles tuyarobot_msgs/msg/UpperAnglesCommand "{angles: [0,0,0,-90,0,0,0,0], speeds: [20, 0]}"

# 右臂 /right_arm
ros2 topic pub -w 1 --keep-alive 2 --once /right_arm/send_upper_angles tuyarobot_msgs/msg/UpperAnglesCommand "{angles: [0,0,0,-90,0,0,0,0], speeds: [20, 0]}"

# 双臂 /upper
ros2 topic pub -w 1 --keep-alive 2 --once /upper/send_upper_angles tuyarobot_msgs/msg/UpperAnglesCommand "{angles: [0,0,0,-90,0,0,0,0, 0,0,0,-90,0,0,0,0], speeds: [20, 0, 20, 0]}"
```

#### Service

- **功能说明**: 控制多关节角度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/MoveUpperAngles`（CLI: `tuyarobot_msgs/srv/MoveUpperAngles`）
- **ROS 名**:
  - `/left_arm/service/send_upper_angles`
- **请求字段**: `angles`（`float64[]`）、`arm_speed`（`int32`）、`gripper_speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**:

| 字段 | 范围 | 说明 |
|---|---|---|
| `angles` | 8项 | 按J1～J8排列。J1 `-160~160`，J2 `-65~110`，J3 `-160~160`，J4 `-164~-10`，J5 `-160~160`，J6 `-40~85`，J7 `-75~75` 单位为度；J8 `0~125` 单位为 mm。 |
| `arm_speed` | `1~100` 的整数 | J1～J7运动速度。 |
| `gripper_speed` | `0` 或 `1~100` 的整数 | J8速度；`0` 表示夹爪不动作。 |

- **返回/观测**: `success` → `message` → `response_time_ms`。`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。夹爪速度 `0` 表示不运动，`1~100` 驱动 `angles[7]` 对应的夹爪开口。
- **调用示例**:

```bash
ros2 service call /left_arm/service/send_upper_angles tuyarobot_msgs/srv/MoveUpperAngles "{angles: [0,0,0,-90,0,0,0,0], arm_speed: 20, gripper_speed: 0, async_mode: false}"
```

#### Service

- **功能说明**: 控制多关节角度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/MoveUpperAngles`（CLI: `tuyarobot_msgs/srv/MoveUpperAngles`）
- **ROS 名**:
  - `/right_arm/service/send_upper_angles`
- **请求字段**: `angles`（`float64[]`）、`arm_speed`（`int32`）、`gripper_speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**:

| 字段 | 范围 | 说明 |
|---|---|---|
| `angles` | 8项 | 按J1～J8排列。J1 `-160~160`，J2 `-65~110`，J3 `-160~160`，J4 `-164~-10`，J5 `-160~160`，J6 `-40~85`，J7 `-75~75` 单位为度；J8 `0~125` 单位为 mm。 |
| `arm_speed` | `1~100` 的整数 | J1～J7运动速度。 |
| `gripper_speed` | `0` 或 `1~100` 的整数 | J8速度；`0` 表示夹爪不动作。 |

- **返回/观测**: `success` → `message` → `response_time_ms`。`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。夹爪速度 `0` 表示不运动，`1~100` 驱动 `angles[7]` 对应的夹爪开口。
- **调用示例**:

```bash
ros2 service call /right_arm/service/send_upper_angles tuyarobot_msgs/srv/MoveUpperAngles "{angles: [0,0,0,-90,0,0,0,0], arm_speed: 20, gripper_speed: 0, async_mode: false}"
```

#### Service

- **功能说明**: 控制多关节角度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/MoveDualUpperAngles`（CLI: `tuyarobot_msgs/srv/MoveDualUpperAngles`）
- **ROS 名**:
  - `/upper/service/send_upper_angles`
- **请求字段**: `left_angles`（`float64[]`）、`left_arm_speed`（`int32`）、`left_gripper_speed`（`int32`）、`right_angles`（`float64[]`）、`right_arm_speed`（`int32`）、`right_gripper_speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**:

| 字段 | 范围 | 说明 |
|---|---|---|
| `left_angles` / `right_angles` | 各8项 | 按J1～J8排列。J1 `-160~160`，J2 `-65~110`，J3 `-160~160`，J4 `-164~-10`，J5 `-160~160`，J6 `-40~85`，J7 `-75~75` 单位为度；J8 `0~125` 单位为 mm。 |
| `left_arm_speed` / `right_arm_speed` | `1~100` 的整数 | J1～J7运动速度。 |
| `left_gripper_speed` / `right_gripper_speed` | `0` 或 `1~100` 的整数 | J8速度；`0` 表示夹爪不动作。 |

- **返回/观测**: `success` → `message` → `response_time_ms`。`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。双臂字段为 `left_angles/right_angles`；夹爪速度 `0` 表示不运动，`1~100` 驱动对应的夹爪开口。
- **调用示例**:

```bash
ros2 service call /upper/service/send_upper_angles tuyarobot_msgs/srv/MoveDualUpperAngles "{left_angles: [0,0,0,-90,0,0,0,0], left_arm_speed: 20, left_gripper_speed: 0, right_angles: [0,0,0,-90,0,0,0,0], right_arm_speed: 20, right_gripper_speed: 0, async_mode: false}"
```

### `send_upper_coord`

#### Topic（订阅/控制）

- **功能说明**: 控制单轴末端坐标
- **类型**: Topic（订阅/控制）
- **消息/服务类型**: `tuyarobot_msgs/UpperCartesianAxisTarget`（CLI: `tuyarobot_msgs/msg/UpperCartesianAxisTarget`）
- **ROS 名**:
  - `/left_arm/send_upper_coord`
  - `/right_arm/send_upper_coord`
  - `/upper/send_upper_coord`
- **消息字段**: `coord_id`（`int32`）、`value`（`float64`）、`speed`（`int32`）、`async_mode`（`int32`）。
- **参数范围**: `coord_id` 为 `1~6`，依次对应 `x/y/z/rx/ry/rz`；`value` 范围为 X `-695~695 mm`，左臂 Y `-305~850 mm`，右臂 Y `-850~305 mm`，Z `-671~680 mm`，RX/RY/RZ `-180~180` 度；`speed` 为 `1~100`。`/upper` 同一 `value` 同时作用于左右臂，`coord_id=2`（Y）时须同时落在两侧范围内。
- **返回/观测**: 无同步回包；成功与否看 operation 审计日志；状态用对应 get_* Topic/Service 观测。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 topic pub -w 1 --keep-alive 2 --once /left_arm/send_upper_coord tuyarobot_msgs/msg/UpperCartesianAxisTarget "{coord_id: 1, value: 10.0, speed: 20}"

# 右臂 /right_arm
ros2 topic pub -w 1 --keep-alive 2 --once /right_arm/send_upper_coord tuyarobot_msgs/msg/UpperCartesianAxisTarget "{coord_id: 1, value: 10.0, speed: 20}"

# 双臂 /upper
ros2 topic pub -w 1 --keep-alive 2 --once /upper/send_upper_coord tuyarobot_msgs/msg/UpperCartesianAxisTarget "{coord_id: 1, value: 10.0, speed: 20}"
```

#### Service

- **功能说明**: 控制单轴末端坐标
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SendUpperCoord`（CLI: `tuyarobot_msgs/srv/SendUpperCoord`）
- **ROS 名**:
  - `/left_arm/service/send_upper_coord`
- **请求字段**: `coord_id`（`int32`）、`value`（`float64`）、`speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**: `coord_id` 为 `1~6`，依次对应 `x/y/z/rx/ry/rz`；`value` 范围为 X `-695~695 mm`，Y `-305~850 mm`，Z `-671~680 mm`，RX/RY/RZ `-180~180` 度；`speed` 为 `1~100`。
- **返回/观测**: `success` → `message` → `response_time_ms`。`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。
- **调用示例**:

```bash
ros2 service call /left_arm/service/send_upper_coord tuyarobot_msgs/srv/SendUpperCoord "{coord_id: 1, value: 10.0, speed: 20, async_mode: false}"
```

#### Service

- **功能说明**: 控制单轴末端坐标
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SendUpperCoord`（CLI: `tuyarobot_msgs/srv/SendUpperCoord`）
- **ROS 名**:
  - `/right_arm/service/send_upper_coord`
- **请求字段**: `coord_id`（`int32`）、`value`（`float64`）、`speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**: `coord_id` 为 `1~6`，依次对应 `x/y/z/rx/ry/rz`；`value` 范围为 X `-695~695 mm`，Y `-850~305 mm`，Z `-671~680 mm`，RX/RY/RZ `-180~180` 度；`speed` 为 `1~100`。
- **返回/观测**: `success` → `message` → `response_time_ms`。`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。
- **调用示例**:

```bash
ros2 service call /right_arm/service/send_upper_coord tuyarobot_msgs/srv/SendUpperCoord "{coord_id: 1, value: 10.0, speed: 20, async_mode: false}"
```

#### Service

- **功能说明**: 同时控制双臂的同一末端坐标轴
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SendUpperCoord`（CLI: `tuyarobot_msgs/srv/SendUpperCoord`）
- **ROS 名**:
  - `/upper/service/send_upper_coord`
- **请求字段**: `coord_id`（`int32`）、`value`（`float64`）、`speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**: `coord_id` 为 `1~6`，依次对应 `x/y/z/rx/ry/rz`，同一 `coord_id/value/speed` 同时作用于左右臂；`value` 范围为 X `-695~695 mm`，左臂 Y `-305~850 mm`，右臂 Y `-850~305 mm`，Z `-671~680 mm`，RX/RY/RZ `-180~180` 度；`speed` 为 `1~100`。`coord_id=2`（Y）时须同时落在两侧范围内。
- **返回/观测**: `success` → `message` → `response_time_ms`。`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。
- **调用示例**:

```bash
ros2 service call /upper/service/send_upper_coord tuyarobot_msgs/srv/SendUpperCoord "{coord_id: 1, value: 10.0, speed: 20, async_mode: false}"
```

### `send_upper_coords`

#### Topic（订阅/控制）

- **功能说明**: 控制末端笛卡尔坐标
- **类型**: Topic（订阅/控制）
- **消息/服务类型**: `tuyarobot_msgs/UpperCartesianTargets`（CLI: `tuyarobot_msgs/msg/UpperCartesianTargets`）
- **ROS 名**:
  - `/left_arm/send_upper_coords`
  - `/right_arm/send_upper_coords`
  - `/upper/send_upper_coords`
- **消息字段**: `poses`（`CartesianPose[]`）、`speeds`（`int32[]`）、`async_mode`（`int32`）。
- **参数范围**: `poses[]` 每项含 `[x,y,z,rx,ry,rz]`；X `-695~695 mm`，左臂 Y `-305~850 mm`，右臂 Y `-850~305 mm`，Z `-671~680 mm`，RX/RY/RZ `-180~180°`；`speeds[]` 与 `poses[]` 等长，每项 `1~100`。双臂 Topic 的 `poses[0]` 为左、`poses[1]` 为右。
- **返回/观测**: 无同步回包；成功与否看 operation 审计日志；状态用对应 get_* Topic/Service 观测。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 topic pub -w 1 --keep-alive 2 --once /left_arm/send_upper_coords tuyarobot_msgs/msg/UpperCartesianTargets "{poses: [{x: 200.0, y: 0.0, z: 300.0, rx: 0.0, ry: 0.0, rz: 0.0}], speeds: [20]}"

# 右臂 /right_arm
ros2 topic pub -w 1 --keep-alive 2 --once /right_arm/send_upper_coords tuyarobot_msgs/msg/UpperCartesianTargets "{poses: [{x: 200.0, y: 0.0, z: 300.0, rx: 0.0, ry: 0.0, rz: 0.0}], speeds: [20]}"

# 双臂 /upper
ros2 topic pub -w 1 --keep-alive 2 --once /upper/send_upper_coords tuyarobot_msgs/msg/UpperCartesianTargets "{poses: [{x: 200.0, y: 0.0, z: 300.0, rx: 0.0, ry: 0.0, rz: 0.0}, {x: 200.0, y: 0.0, z: 300.0, rx: 0.0, ry: 0.0, rz: 0.0}], speeds: [20, 20]}"
```

#### Service

- **功能说明**: 控制末端笛卡尔坐标
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SendUpperCoords`（CLI: `tuyarobot_msgs/srv/SendUpperCoords`）
- **ROS 名**:
  - `/left_arm/service/send_upper_coords`
- **请求字段**: `poses`（`CartesianPose[]`）、`speeds`（`int32[]`）、`async_mode`（`bool`）。
- **参数范围**: `poses[]` 每项含 `[x,y,z,rx,ry,rz]`；X `-695~695 mm`，Y `-305~850 mm`，Z `-671~680 mm`，RX/RY/RZ `-180~180°`；`speeds[]` 与 `poses[]` 等长，每项 `1~100`。
- **返回/观测**: `success` → `message` → `response_time_ms`。`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。
- **调用示例**:

```bash
ros2 service call /left_arm/service/send_upper_coords tuyarobot_msgs/srv/SendUpperCoords "{poses: [{x: 200.0, y: 0.0, z: 300.0, rx: 0.0, ry: 0.0, rz: 0.0}], speeds: [20], async_mode: false}"
```

#### Service

- **功能说明**: 控制末端笛卡尔坐标
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SendUpperCoords`（CLI: `tuyarobot_msgs/srv/SendUpperCoords`）
- **ROS 名**:
  - `/right_arm/service/send_upper_coords`
- **请求字段**: `poses`（`CartesianPose[]`）、`speeds`（`int32[]`）、`async_mode`（`bool`）。
- **参数范围**: `poses[]` 每项含 `[x,y,z,rx,ry,rz]`；X `-695~695 mm`，Y `-850~305 mm`，Z `-671~680 mm`，RX/RY/RZ `-180~180°`；`speeds[]` 与 `poses[]` 等长，每项 `1~100`。
- **返回/观测**: `success` → `message` → `response_time_ms`。`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。
- **调用示例**:

```bash
ros2 service call /right_arm/service/send_upper_coords tuyarobot_msgs/srv/SendUpperCoords "{poses: [{x: 200.0, y: 0.0, z: 300.0, rx: 0.0, ry: 0.0, rz: 0.0}], speeds: [20], async_mode: false}"
```

#### Service

- **功能说明**: 控制末端笛卡尔坐标
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SendDualUpperCoords`（CLI: `tuyarobot_msgs/srv/SendDualUpperCoords`）
- **ROS 名**:
  - `/upper/service/send_upper_coords`
- **请求字段**: `left_pose`（`CartesianPose`）、`left_speed`（`int32`）、`right_pose`（`CartesianPose`）、`right_speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**: `left_pose/right_pose` 均含 `[x,y,z,rx,ry,rz]`；X `-695~695 mm`，左臂 Y `-305~850 mm`，右臂 Y `-850~305 mm`，Z `-671~680 mm`，RX/RY/RZ `-180~180°`；`left_speed/right_speed` 均为 `1~100`。
- **返回/观测**: `success` → `message` → `response_time_ms`。`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。双臂字段为 `left_pose/left_speed/right_pose/right_speed`，范围见本接口参数表。
- **调用示例**:

```bash
ros2 service call /upper/service/send_upper_coords tuyarobot_msgs/srv/SendDualUpperCoords "{left_pose: {x: 200.0, y: 0.0, z: 300.0, rx: 0.0, ry: 0.0, rz: 0.0}, left_speed: 20, right_pose: {x: 200.0, y: 0.0, z: 300.0, rx: 0.0, ry: 0.0, rz: 0.0}, right_speed: 20, async_mode: false}"
```

### `send_upper_lift_coords`

- **功能说明**: 按升降系目标运动：SDK 用当前升降里程对 Z 做 Z − mileage 后再下发坐标运动。
- **类型**: Service
- **消息/服务类型**: 单臂 `tuyarobot_msgs/SendUpperLiftCoords`（CLI: `tuyarobot_msgs/srv/SendUpperLiftCoords`）；双臂 `tuyarobot_msgs/SendDualUpperLiftCoords`（CLI: `tuyarobot_msgs/srv/SendDualUpperLiftCoords`）
- **ROS 名**:
  - `/left_arm/send_upper_lift_coords`
  - `/right_arm/send_upper_lift_coords`
  - `/upper/send_upper_lift_coords`
- **请求字段**: 单臂：`pose`、`speed`、`async_mode`；双臂：`left_pose`、`left_speed`、`right_pose`、`right_speed`、`async_mode`。请求不带 `height`。
- **参数范围**: 各坐标均为 `[x,y,z,rx,ry,rz]`；X `-695~695 mm`，左臂 Y `-305~850 mm`，右臂 Y `-850~305 mm`，Z `-671~680 mm`，RX/RY/RZ `-180~180°`；速度为整数 `1~100`；升降里程由 `/chassis/get_agv_lift_mileage` 读取后作为 SDK `height` 注入；`async_mode` 原样传给 SDK `_async`。
- **返回/观测**: `success` → `message` → `response_time_ms`（对齐 `send_upper_coords`）。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/send_upper_lift_coords tuyarobot_msgs/srv/SendUpperLiftCoords "{pose: {x: 100.0, y: 0.0, z: 300.0, rx: 0.0, ry: 0.0, rz: 0.0}, speed: 20, async_mode: true}"

# 右臂 /right_arm
ros2 service call /right_arm/send_upper_lift_coords tuyarobot_msgs/srv/SendUpperLiftCoords "{pose: {x: 100.0, y: 0.0, z: 320.0, rx: 0.0, ry: 0.0, rz: 0.0}, speed: 20, async_mode: true}"

# 双臂 /upper
ros2 service call /upper/send_upper_lift_coords tuyarobot_msgs/srv/SendDualUpperLiftCoords "{left_pose: {x: 100.0, y: 0.0, z: 300.0, rx: 0.0, ry: 0.0, rz: 0.0}, left_speed: 20, right_pose: {x: 100.0, y: 0.0, z: 320.0, rx: 0.0, ry: 0.0, rz: 0.0}, right_speed: 20, async_mode: true}"
```

### `send_upper_torques`

- **功能说明**: 发送J1至J7力矩电流
- **类型**: Service
- **消息/服务类型**: 单臂 `tuyarobot_msgs/SendUpperTorques`（CLI: `tuyarobot_msgs/srv/SendUpperTorques`）；双臂 `/upper` `tuyarobot_msgs/SendDualUpperTorques`（CLI: `tuyarobot_msgs/srv/SendDualUpperTorques`）
- **ROS 名**:
  - `/left_arm/send_upper_torques`
  - `/right_arm/send_upper_torques`
  - `/upper/send_upper_torques`
- **请求字段**: `SendUpperTorques`：`torques`（`float64[]`）；`SendDualUpperTorques`：`left_torques`（`float64[]`）、`right_torques`（`float64[]`）。
- **参数范围**: 单臂 `torques[]` 固定7项；双臂 `left_torques[]/right_torques[]` 各7项；均按J1～J7排列，单位 `A`，每项 `-20~20`。调用前须切换力矩模式。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/send_upper_torques tuyarobot_msgs/srv/SendUpperTorques "{torques: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}"

# 右臂 /right_arm
ros2 service call /right_arm/send_upper_torques tuyarobot_msgs/srv/SendUpperTorques "{torques: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}"

# 双臂 /upper
ros2 service call /upper/send_upper_torques tuyarobot_msgs/srv/SendDualUpperTorques "{left_torques: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], right_torques: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}"
```

### `set_joint_max_angle`

- **功能说明**: 设置全局最大限位。不分左右臂
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetArmScope`（CLI: `tuyarobot_msgs/srv/SetArmScope`）
- **ROS 名**:
  - `/upper/set_joint_max_angle`
- **请求字段**: `arm_type`（`int32`）、`param_id`（`int32`）、`param_value`（`int32`）。
- **参数范围**: `param_id`：`1~8`；`param_value` 对 J1～J7 单位为度、对 J8 单位为 mm，各关节范围为 J1 `-160~160`、J2 `-65~110`、J3 `-160~160`、J4 `-164~-10`、J5 `-160~160`、J6 `-40~85`、J7 `-75~75`、J8 `0~125`。该限位为整机全局配置，仅支持 `/upper` 作用域。 `arm_type` 为兼容字段，取 `1/2/3`，实际作用域由 ROS 路径决定。
- **返回/观测**: `success` → `message` → `result_value`（成功通常为 1） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/set_joint_max_angle tuyarobot_msgs/srv/SetArmScope "{arm_type: 3, param_id: 1, param_value: 90}"
```

### `set_joint_min_angle`

- **功能说明**: 设置全局最小限位。不分左右臂
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetArmScope`（CLI: `tuyarobot_msgs/srv/SetArmScope`）
- **ROS 名**:
  - `/upper/set_joint_min_angle`
- **请求字段**: `arm_type`（`int32`）、`param_id`（`int32`）、`param_value`（`int32`）。
- **参数范围**: `param_id`：`1~8`；`param_value` 对 J1～J7 单位为度、对 J8 单位为 mm，各关节范围为 J1 `-160~160`、J2 `-65~110`、J3 `-160~160`、J4 `-164~-10`、J5 `-160~160`、J6 `-40~85`、J7 `-75~75`、J8 `0~125`。该限位为整机全局配置，仅支持 `/upper` 作用域。 `arm_type` 为兼容字段，取 `1/2/3`，实际作用域由 ROS 路径决定。
- **返回/观测**: `success` → `message` → `result_value`（成功通常为 1） → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/set_joint_min_angle tuyarobot_msgs/srv/SetArmScope "{arm_type: 3, param_id: 1, param_value: -90}"
```

### `set_upper_collision_mode`

- **功能说明**: 开启或关闭关节碰撞检测
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetUpperCollisionMode`（CLI: `tuyarobot_msgs/srv/SetUpperCollisionMode`）
- **ROS 名**:
  - `/left_arm/set_upper_collision_mode`
  - `/right_arm/set_upper_collision_mode`
  - `/upper/set_upper_collision_mode`
- **请求字段**: `mode`（`int32`）。
- **参数范围**: `mode` 仅支持 `0` 或 `1`，`0=关闭碰撞检测`，`1=开启碰撞检测`。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_collision_mode tuyarobot_msgs/srv/SetUpperCollisionMode "{mode: 0}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_collision_mode tuyarobot_msgs/srv/SetUpperCollisionMode "{mode: 0}"

# 双臂 /upper
ros2 service call /upper/set_upper_collision_mode tuyarobot_msgs/srv/SetUpperCollisionMode "{mode: 0}"
```

### `set_upper_collision_threshold`

- **功能说明**: 设置关节碰撞阈值
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetUpperCollisionThreshold`（CLI: `tuyarobot_msgs/srv/SetUpperCollisionThreshold`）
- **ROS 名**:
  - `/left_arm/set_upper_collision_threshold`
  - `/right_arm/set_upper_collision_threshold`
  - `/upper/set_upper_collision_threshold`
- **请求字段**: `joint_id`（`int32`）、`threshold`（`int32`）。
- **参数范围**: `joint_id` 为 `1~7`；`threshold` 为 `50~250`。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_collision_threshold tuyarobot_msgs/srv/SetUpperCollisionThreshold "{joint_id: 1, threshold: 100}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_collision_threshold tuyarobot_msgs/srv/SetUpperCollisionThreshold "{joint_id: 1, threshold: 100}"

# 双臂 /upper
ros2 service call /upper/set_upper_collision_threshold tuyarobot_msgs/srv/SetUpperCollisionThreshold "{joint_id: 1, threshold: 100}"
```

### `set_upper_control_mode`

- **功能说明**: 切换位置或力矩控制模式
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetScopedIntValues`（CLI: `tuyarobot_msgs/srv/SetScopedIntValues`）
- **ROS 名**:
  - `/left_arm/set_upper_control_mode`
  - `/right_arm/set_upper_control_mode`
  - `/upper/set_upper_control_mode`
- **请求字段**: `values`（`int32[]`）。
- **参数范围**: `values`：单臂 `[mode]`；双臂 `[mode, mode]`（两侧必须相同，SDK 一次设两臂）；`0=位置`，`1=力矩`。受上电保护；不会自动发力矩。左右要不同请走单臂 Service。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_control_mode tuyarobot_msgs/srv/SetScopedIntValues "{values: [0]}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_control_mode tuyarobot_msgs/srv/SetScopedIntValues "{values: [0]}"

# 双臂 /upper
ros2 service call /upper/set_upper_control_mode tuyarobot_msgs/srv/SetScopedIntValues "{values: [0, 0]}"
```

### `set_upper_debug_state`

- **功能说明**: 设置全局调试状态。不分左右臂
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetInt`（CLI: `tuyarobot_msgs/srv/SetInt`）
- **ROS 名**:
  - `/upper/set_upper_debug_state`
- **请求字段**: `data`（`int32`）。
- **参数范围**: `data` 为 `0~255` 的固件调试状态值；当前接口未定义各数值的日志类别名称，设置前应先读取并保留原值。
- **返回/观测**: `success` → `message` → `response_time_ms`；请求字段 `data`。
- **调用示例**:

```bash
# 双臂 /upper
ros2 service call /upper/set_upper_debug_state tuyarobot_msgs/srv/SetInt "{data: 1}"
```

### `set_upper_end_type`

- **功能说明**: 设置末端为法兰或工具
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetScopedIntValues`（CLI: `tuyarobot_msgs/srv/SetScopedIntValues`）
- **ROS 名**:
  - `/left_arm/set_upper_end_type`
  - `/right_arm/set_upper_end_type`
  - `/upper/set_upper_end_type`
- **请求字段**: `values`（`int32[]`）。
- **参数范围**: 单臂作用域的 `values[]` 固定1项，`/upper` 固定2项 `[left,right]`；每项仅支持 `0` 或 `1`，`0=法兰`，`1=工具`。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_end_type tuyarobot_msgs/srv/SetScopedIntValues "{values: [0]}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_end_type tuyarobot_msgs/srv/SetScopedIntValues "{values: [0]}"

# 双臂 /upper
ros2 service call /upper/set_upper_end_type tuyarobot_msgs/srv/SetScopedIntValues "{values: [0, 1]}"
```

### `set_upper_filter_len`

- **功能说明**: 设置关节滤波长度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetUpperFilterLen`（CLI: `tuyarobot_msgs/srv/SetUpperFilterLen`）
- **ROS 名**:
  - `/left_arm/set_upper_filter_len`
  - `/right_arm/set_upper_filter_len`
  - `/upper/set_upper_filter_len`
- **请求字段**: `rank`（`int32`）、`value`（`int32`）。
- **参数范围**: `rank` 为 `1~5` 的滤波参数编号，当前接口未定义各编号名称；`value` 为 `1~255` 的滤波长度。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_filter_len tuyarobot_msgs/srv/SetUpperFilterLen "{rank: 1, value: 5}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_filter_len tuyarobot_msgs/srv/SetUpperFilterLen "{rank: 1, value: 5}"

# 双臂 /upper
ros2 service call /upper/set_upper_filter_len tuyarobot_msgs/srv/SetUpperFilterLen "{rank: 1, value: 5}"
```

### `set_upper_fresh_mode`

- **功能说明**: 切换插补或刷新运动模式
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetInt`（CLI: `tuyarobot_msgs/srv/SetInt`）
- **ROS 名**:
  - `/left_arm/set_upper_fresh_mode`
  - `/right_arm/set_upper_fresh_mode`
  - `/upper/set_upper_fresh_mode`
- **请求字段**: `data`（`int32`）。
- **参数范围**: `data=0` 为插补模式，`data=1` 为刷新模式。
- **返回/观测**: `success` → `message` → `response_time_ms`；请求字段 `data`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_fresh_mode tuyarobot_msgs/srv/SetInt "{data: 1}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_fresh_mode tuyarobot_msgs/srv/SetInt "{data: 1}"

# 双臂 /upper
ros2 service call /upper/set_upper_fresh_mode tuyarobot_msgs/srv/SetInt "{data: 1}"
```

### `set_upper_gripper_calibrate_mode`

- **功能说明**: 设置夹爪校准模式
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetUpperGripperCalibrateMode`（CLI: `tuyarobot_msgs/srv/SetUpperGripperCalibrateMode`）
- **ROS 名**:
  - `/left_arm/set_upper_gripper_calibrate_mode`
  - `/right_arm/set_upper_gripper_calibrate_mode`
  - `/upper/set_upper_gripper_calibrate_mode`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `status_values` → `response_time_ms`；`message` 直接保留 Python SDK 文案，状态含 `255` 时可附加 `(status=255)`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_gripper_calibrate_mode tuyarobot_msgs/srv/SetUpperGripperCalibrateMode '{}'

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_gripper_calibrate_mode tuyarobot_msgs/srv/SetUpperGripperCalibrateMode '{}'

# 双臂 /upper
ros2 service call /upper/set_upper_gripper_calibrate_mode tuyarobot_msgs/srv/SetUpperGripperCalibrateMode '{}'
```

### `set_upper_gripper_calibrate`

- **功能说明**: 按人工流程执行夹爪整定阶段
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetUpperGripperCalibrate`（CLI: `tuyarobot_msgs/srv/SetUpperGripperCalibrate`）
- **ROS 名**:
  - `/left_arm/set_upper_gripper_calibrate`
  - `/right_arm/set_upper_gripper_calibrate`
  - `/upper/set_upper_gripper_calibrate`
- **请求字段**: `mode`（`int32`）。
- **参数范围**: `mode` 为 `0~2`；`0=张开`，`1=闭合`，`2=保存`，应按顺序调用。
- **返回/观测**: `success` → `message` → `data` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂
ros2 service call /left_arm/set_upper_gripper_calibrate tuyarobot_msgs/srv/SetUpperGripperCalibrate "{mode: 0}"
ros2 service call /left_arm/set_upper_gripper_calibrate tuyarobot_msgs/srv/SetUpperGripperCalibrate "{mode: 1}"
ros2 service call /left_arm/set_upper_gripper_calibrate tuyarobot_msgs/srv/SetUpperGripperCalibrate "{mode: 2}"

# 右臂
ros2 service call /right_arm/set_upper_gripper_calibrate tuyarobot_msgs/srv/SetUpperGripperCalibrate "{mode: 0}"
ros2 service call /right_arm/set_upper_gripper_calibrate tuyarobot_msgs/srv/SetUpperGripperCalibrate "{mode: 1}"
ros2 service call /right_arm/set_upper_gripper_calibrate tuyarobot_msgs/srv/SetUpperGripperCalibrate "{mode: 2}"

# 双臂
ros2 service call /upper/set_upper_gripper_calibrate tuyarobot_msgs/srv/SetUpperGripperCalibrate "{mode: 0}"
ros2 service call /upper/set_upper_gripper_calibrate tuyarobot_msgs/srv/SetUpperGripperCalibrate "{mode: 1}"
ros2 service call /upper/set_upper_gripper_calibrate tuyarobot_msgs/srv/SetUpperGripperCalibrate "{mode: 2}"
```

### `set_upper_gripper_collision_threshold`

- **功能说明**: 设置夹爪碰撞阈值
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetFloat`（CLI: `tuyarobot_msgs/srv/SetFloat`）
- **ROS 名**:
  - `/left_arm/set_upper_gripper_collision_threshold`
  - `/right_arm/set_upper_gripper_collision_threshold`
  - `/upper/set_upper_gripper_collision_threshold`
- **请求字段**: `data`（`float64`）。
- **参数范围**: `data` 为 `0.0~1.0` Nm；`0` 表示关闭夹爪碰撞检测。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_gripper_collision_threshold tuyarobot_msgs/srv/SetFloat "{data: 0.5}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_gripper_collision_threshold tuyarobot_msgs/srv/SetFloat "{data: 0.5}"

# 双臂 /upper
ros2 service call /upper/set_upper_gripper_collision_threshold tuyarobot_msgs/srv/SetFloat "{data: 0.5}"
```

### `set_upper_gripper_force`

- **功能说明**: 设置夹爪目标夹持力
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetUpperGripperForce`（CLI: `tuyarobot_msgs/srv/SetUpperGripperForce`）
- **ROS 名**:
  - `/left_arm/set_upper_gripper_force`
  - `/right_arm/set_upper_gripper_force`
  - `/upper/set_upper_gripper_force`
- **请求字段**: `value`（`float64`）。
- **参数范围**: `value` 为夹持力，单位 N，范围 `0.5~15.0`。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_gripper_force tuyarobot_msgs/srv/SetUpperGripperForce "{value: 10.0}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_gripper_force tuyarobot_msgs/srv/SetUpperGripperForce "{value: 10.0}"

# 双臂 /upper
ros2 service call /upper/set_upper_gripper_force tuyarobot_msgs/srv/SetUpperGripperForce "{value: 10.0}"
```

### `set_upper_gripper_param`

- **功能说明**: 按地址设置夹爪参数
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetUpperParameter`（CLI: `tuyarobot_msgs/srv/SetUpperParameter`）
- **ROS 名**:
  - `/left_arm/set_upper_gripper_param`
  - `/right_arm/set_upper_gripper_param`
  - `/upper/set_upper_gripper_param`
- **请求字段**: `parameter_id`（`int32`）、`value`（`int32`）。
- **参数范围**: `parameter_id` 为 `1~254`；当 `parameter_id=1` 时 `value` 为 `0~15` N。其他地址的 `value` 受当前 `int32` 字段限制，为 `0~2147483647`，具体含义按设备参数定义。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_gripper_param tuyarobot_msgs/srv/SetUpperParameter "{parameter_id: 1, value: 2}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_gripper_param tuyarobot_msgs/srv/SetUpperParameter "{parameter_id: 1, value: 2}"

# 双臂 /upper
ros2 service call /upper/set_upper_gripper_param tuyarobot_msgs/srv/SetUpperParameter "{parameter_id: 1, value: 2}"
```

### `set_upper_joint_acc`

- **功能说明**: 设置关节加速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetUpperJointAcc`（CLI: `tuyarobot_msgs/srv/SetUpperJointAcc`）
- **ROS 名**:
  - `/left_arm/set_joint_acc`
  - `/right_arm/set_joint_acc`
  - `/upper/set_joint_acc`
- **请求字段**: `joint_id`（`int32`）、`acceleration`（`float64`）。
- **参数范围**: `joint_id` 范围 `1~7`；`acceleration` 范围 `0.001~0.1`。
- **返回/观测**: `success` → `message` → `result_value` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_joint_acc tuyarobot_msgs/srv/SetUpperJointAcc "{joint_id: 1, acceleration: 0.05}"

# 右臂 /right_arm
ros2 service call /right_arm/set_joint_acc tuyarobot_msgs/srv/SetUpperJointAcc "{joint_id: 1, acceleration: 0.05}"

# 双臂 /upper
ros2 service call /upper/set_joint_acc tuyarobot_msgs/srv/SetUpperJointAcc "{joint_id: 1, acceleration: 0.05}"
```

### `set_upper_joint_calibrate`

- **功能说明**: 校准指定或全部上半身关节
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetArmScope`（CLI: `tuyarobot_msgs/srv/SetArmScope`）
- **ROS 名**:
  - `/left_arm/set_upper_joint_calibrate`
  - `/right_arm/set_upper_joint_calibrate`
  - `/upper/set_upper_joint_calibrate`
- **请求字段**: `arm_type`（`int32`）、`param_id`（`int32`）、`param_value`（`int32`）。
- **参数范围**: `param_id`=关节号 `1~8` 或 `254`（全部）；`param_value` 可填 0（未使用）。 `arm_type` 为兼容字段，取 `1/2/3`，实际作用域由 ROS 路径决定。
- **返回/观测**: `success` → `message` → `result_value`（成功通常为 1） → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_joint_calibrate tuyarobot_msgs/srv/SetArmScope "{arm_type: 1, param_id: 254, param_value: 0}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_joint_calibrate tuyarobot_msgs/srv/SetArmScope "{arm_type: 1, param_id: 254, param_value: 0}"

# 双臂 /upper
ros2 service call /upper/set_upper_joint_calibrate tuyarobot_msgs/srv/SetArmScope "{arm_type: 1, param_id: 254, param_value: 0}"
```

### `set_upper_joint_enable`

- **功能说明**: 使能或失能指定上半身关节
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetArmScope`（CLI: `tuyarobot_msgs/srv/SetArmScope`）
- **ROS 名**:
  - `/left_arm/set_upper_joint_enable`
  - `/right_arm/set_upper_joint_enable`
  - `/upper/set_upper_joint_enable`
- **请求字段**: `arm_type`（`int32`）、`param_id`（`int32`）、`param_value`（`int32`）。
- **参数范围**: `param_id`=关节号 `1~8` 或 `254`（全部）；`param_value`：`1` 使能，`0` 失能。 `arm_type` 为兼容字段，取 `1/2/3`，实际作用域由 ROS 路径决定。
- **返回/观测**: `success` → `message` → `result_value`（成功通常为 1） → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_joint_enable tuyarobot_msgs/srv/SetArmScope "{arm_type: 1, param_id: 254, param_value: 1}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_joint_enable tuyarobot_msgs/srv/SetArmScope "{arm_type: 1, param_id: 254, param_value: 1}"

# 双臂 /upper
ros2 service call /upper/set_upper_joint_enable tuyarobot_msgs/srv/SetArmScope "{arm_type: 1, param_id: 254, param_value: 1}"
```

### `set_upper_light_brightness`

- **功能说明**: 设置上半身灯光亮度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetInt`（CLI: `tuyarobot_msgs/srv/SetInt`）
- **ROS 名**:
  - `/left_arm/set_upper_light_brightness`
  - `/right_arm/set_upper_light_brightness`
  - `/upper/set_upper_light_brightness`
- **请求字段**: `data`（`int32`）。
- **参数范围**: `data` 为 `0~100`；`0=关闭`，`100=最亮`。
- **返回/观测**: `success` → `message` → `response_time_ms`；请求字段 `data`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_light_brightness tuyarobot_msgs/srv/SetInt "{data: 1}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_light_brightness tuyarobot_msgs/srv/SetInt "{data: 1}"

# 双臂 /upper
ros2 service call /upper/set_upper_light_brightness tuyarobot_msgs/srv/SetInt "{data: 1}"
```

### `set_upper_model_direction`

- **功能说明**: 设置关节模型方向配置
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetJointValue`（CLI: `tuyarobot_msgs/srv/SetJointValue`）
- **ROS 名**:
  - `/left_arm/set_upper_model_direction`
  - `/right_arm/set_upper_model_direction`
  - `/upper/set_upper_model_direction`
- **请求字段**: `joint_id`（`int32`）、`direction`（`int32`）。
- **参数范围**: `joint_id` 为 `1~7`；`direction` 仅支持 `0` 或 `1`。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_model_direction tuyarobot_msgs/srv/SetJointValue "{joint_id: 1, direction: 1}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_model_direction tuyarobot_msgs/srv/SetJointValue "{joint_id: 1, direction: 1}"

# 双臂 /upper
ros2 service call /upper/set_upper_model_direction tuyarobot_msgs/srv/SetJointValue "{joint_id: 1, direction: 1}"
```

### `set_upper_movement_type`

- **功能说明**: 设置上半身运动类型
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetScopedIntValues`（CLI: `tuyarobot_msgs/srv/SetScopedIntValues`）
- **ROS 名**:
  - `/left_arm/set_upper_movement_type`
  - `/right_arm/set_upper_movement_type`
  - `/upper/set_upper_movement_type`
- **请求字段**: `values`（`int32[]`）。
- **参数范围**: 单臂作用域的 `values[]` 固定1项，`/upper` 固定2项 `[left,right]`；每项为 `0~4` 的运动类型编号，当前接口未定义编号名称。修改前应读取并保留原值。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_movement_type tuyarobot_msgs/srv/SetScopedIntValues "{values: [0]}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_movement_type tuyarobot_msgs/srv/SetScopedIntValues "{values: [0]}"

# 双臂 /upper
ros2 service call /upper/set_upper_movement_type tuyarobot_msgs/srv/SetScopedIntValues "{values: [0, 1]}"
```

### `set_upper_plan_acc`

- **功能说明**: 设置角度或坐标规划加速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetPlanAcc`（CLI: `tuyarobot_msgs/srv/SetPlanAcc`）
- **ROS 名**:
  - `/left_arm/set_upper_plan_acc`
  - `/right_arm/set_upper_plan_acc`
  - `/upper/set_upper_plan_acc`
- **请求字段**: `mode`（`int32`）、`acceleration`（`int32`）。
- **参数范围**:

| 字段 | 范围 | 说明 |
|---|---|---|
| `mode` | `0` 或 `1` | `0=角度规划`，`1=坐标规划`。 |
| `acceleration` | `mode=0` 时 `1~200`；`mode=1` 时 `1~400` | 规划加速度。 |

- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_plan_acc tuyarobot_msgs/srv/SetPlanAcc "{mode: 0, acceleration: 100}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_plan_acc tuyarobot_msgs/srv/SetPlanAcc "{mode: 0, acceleration: 100}"

# 双臂 /upper
ros2 service call /upper/set_upper_plan_acc tuyarobot_msgs/srv/SetPlanAcc "{mode: 0, acceleration: 100}"
```

### `set_upper_plan_sp`

- **功能说明**: 设置角度或坐标规划速度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetPlanSpeed`（CLI: `tuyarobot_msgs/srv/SetPlanSpeed`）
- **ROS 名**:
  - `/left_arm/set_upper_plan_sp`
  - `/right_arm/set_upper_plan_sp`
  - `/upper/set_upper_plan_sp`
- **请求字段**: `mode`（`int32`）、`speed`（`int32`）。
- **参数范围**: `mode` 仅支持 `0` 或 `1`，`0=角度规划`，`1=坐标规划`；`speed` 在 `mode=0` 时为 `1~150`，在 `mode=1` 时为 `1~200`。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_plan_sp tuyarobot_msgs/srv/SetPlanSpeed "{mode: 0, speed: 50}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_plan_sp tuyarobot_msgs/srv/SetPlanSpeed "{mode: 0, speed: 50}"

# 双臂 /upper
ros2 service call /upper/set_upper_plan_sp tuyarobot_msgs/srv/SetPlanSpeed "{mode: 0, speed: 50}"
```

### `set_upper_reference_frame`

- **功能说明**: 设置全局参考系。不分左右臂
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetInt`（CLI: `tuyarobot_msgs/srv/SetInt`）
- **ROS 名**:
  - `/upper/set_upper_reference_frame`
- **请求字段**: `data`（`int32`）。
- **参数范围**: `data` 仅支持 `0` 或 `1`，`0=base`，`1=world`。
- **返回/观测**: `success` → `message` → `response_time_ms`；请求字段 `data`。
- **调用示例**:

```bash
ros2 service call /upper/set_upper_reference_frame tuyarobot_msgs/srv/SetInt "{data: 1}"
```

### `set_upper_tool_reference`

- **功能说明**: 设置工具参考坐标
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetCartesianPoses`（CLI: `tuyarobot_msgs/srv/SetCartesianPoses`）
- **ROS 名**:
  - `/left_arm/set_upper_tool_reference`
  - `/right_arm/set_upper_tool_reference`
  - `/upper/set_upper_tool_reference`
- **请求字段**: `poses`（`CartesianPose[]`）。
- **参数范围**: 单臂 `pose` 为6项，`/upper` 的 `poses[]` 为左右臂各6项；顺序均为 `[x,y,z,rx,ry,rz]`。`x/y/z` 范围 `-1000~1000` mm，`rx/ry/rz` 范围 `-180~180` 度。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_tool_reference tuyarobot_msgs/srv/SetCartesianPoses "{poses: [{x: 0.0, y: 0.0, z: 0.0, rx: 0.0, ry: 0.0, rz: 0.0}]}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_tool_reference tuyarobot_msgs/srv/SetCartesianPoses "{poses: [{x: 0.0, y: 0.0, z: 0.0, rx: 0.0, ry: 0.0, rz: 0.0}]}"

# 双臂 /upper
ros2 service call /upper/set_upper_tool_reference tuyarobot_msgs/srv/SetCartesianPoses "{poses: [{x: 0.0, y: 0.0, z: 0.0, rx: 0.0, ry: 0.0, rz: 0.0}, {x: 0.0, y: 0.0, z: 0.0, rx: 0.0, ry: 0.0, rz: 0.0}]}"
```

### `set_upper_vr_mode`

- **功能说明**: 开启或关闭VR控制
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetScopedIntValues`（CLI: `tuyarobot_msgs/srv/SetScopedIntValues`）
- **ROS 名**:
  - `/left_arm/set_upper_vr_mode`
  - `/right_arm/set_upper_vr_mode`
  - `/upper/set_upper_vr_mode`
- **请求字段**: `values`（`int32[]`）。
- **参数范围**: 单臂作用域的 `values[]` 固定1项，`/upper` 固定2项 `[left,right]`；每项仅支持 `0` 或 `1`，`0=关闭`，`1=开启`。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/set_upper_vr_mode tuyarobot_msgs/srv/SetScopedIntValues "{values: [0]}"

# 右臂 /right_arm
ros2 service call /right_arm/set_upper_vr_mode tuyarobot_msgs/srv/SetScopedIntValues "{values: [0]}"

# 双臂 /upper
ros2 service call /upper/set_upper_vr_mode tuyarobot_msgs/srv/SetScopedIntValues "{values: [0, 1]}"
```

### `set_upper_world_reference`

- **功能说明**: 设置世界参考坐标。不分左右臂
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetCartesianPose`（CLI: `tuyarobot_msgs/srv/SetCartesianPose`）
- **ROS 名**:
  - `/upper/set_upper_world_reference`
- **请求字段**: `pose`（`CartesianPose`）。
- **参数范围**: `pose` 为6项 `[x,y,z,rx,ry,rz]`；`x/y/z` 范围 `-1000~1000` mm，`rx/ry/rz` 范围 `-180~180` 度。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /upper/set_upper_world_reference tuyarobot_msgs/srv/SetCartesianPose "{pose: {x: 0.0, y: 0.0, z: 0.0, rx: 0.0, ry: 0.0, rz: 0.0}}"
```

### `upper_auto_report_stream`

- **功能说明**: 发布双臂自动上报聚合数据
- **类型**: Topic（发布/状态）
- **消息/服务类型**: `tuyarobot_msgs/UpperAutoReport`（CLI: `tuyarobot_msgs/msg/UpperAutoReport`）
- **ROS 名**:
  - `/upper/upper_auto_report`
- **返回语义**: `left/right_angles[8]` 中 J1～J7 单位为度、J8 夹爪单位为 mm；`left/right_coords[6]` 依次为毫米位置和角度姿态；`left/right_joints_run_sp[8]` 单位 `rpm`；`left/right_joints_current[8]` 单位安培；`power_protection_state=1` 表示触发电源保护。
- **返回/观测**: 按 `upper_publish_hz` 发布最新有效缓存；含 status/message 与传感器字段，重复帧保留源 `seq` 和时间戳。
- **调用示例**:

```bash
timeout 5s ros2 topic echo /upper/upper_auto_report --once
```

### `upper_drag_teach_multi_play`

- **功能说明**: 依次播放多段拖动示教轨迹
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/PlayUpperMultiDragTeach`（CLI: `tuyarobot_msgs/srv/PlayUpperMultiDragTeach`）
- **ROS 名**:
  - `/left_arm/upper_drag_teach_multi_play`
  - `/right_arm/upper_drag_teach_multi_play`
  - `/upper/upper_drag_teach_multi_play`
- **请求字段**: `count`（`int32`）、`async_mode`（`bool`）。
- **参数范围**: `count` 为 `1~100`，表示依次播放的轨迹条数。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/upper_drag_teach_multi_play tuyarobot_msgs/srv/PlayUpperMultiDragTeach "{count: 1, async_mode: true}"

# 右臂 /right_arm
ros2 service call /right_arm/upper_drag_teach_multi_play tuyarobot_msgs/srv/PlayUpperMultiDragTeach "{count: 1, async_mode: true}"

# 双臂 /upper
ros2 service call /upper/upper_drag_teach_multi_play tuyarobot_msgs/srv/PlayUpperMultiDragTeach "{count: 1, async_mode: true}"
```

### `upper_drag_teach_play`

- **功能说明**: 播放拖动示教轨迹
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperAsyncTrigger`（CLI: `tuyarobot_msgs/srv/UpperAsyncTrigger`）
- **ROS 名**:
  - `/left_arm/upper_drag_teach_play`
  - `/right_arm/upper_drag_teach_play`
  - `/upper/upper_drag_teach_play`
- **请求字段**: `async_mode`。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/upper_drag_teach_play tuyarobot_msgs/srv/UpperAsyncTrigger "{async_mode: true}"

# 右臂 /right_arm
ros2 service call /right_arm/upper_drag_teach_play tuyarobot_msgs/srv/UpperAsyncTrigger "{async_mode: true}"

# 双臂 /upper
ros2 service call /upper/upper_drag_teach_play tuyarobot_msgs/srv/UpperAsyncTrigger "{async_mode: true}"
```

### `upper_drag_teach_record`

- **功能说明**: 开始录制拖动示教轨迹
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/left_arm/upper_drag_teach_record`
  - `/right_arm/upper_drag_teach_record`
  - `/upper/upper_drag_teach_record`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/upper_drag_teach_record tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 右臂 /right_arm
ros2 service call /right_arm/upper_drag_teach_record tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 双臂 /upper
ros2 service call /upper/upper_drag_teach_record tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `upper_drag_teach_record_clear`

- **功能说明**: 清除拖动示教轨迹
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/left_arm/upper_drag_teach_record_clear`
  - `/right_arm/upper_drag_teach_record_clear`
  - `/upper/upper_drag_teach_record_clear`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/upper_drag_teach_record_clear tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 右臂 /right_arm
ros2 service call /right_arm/upper_drag_teach_record_clear tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 双臂 /upper
ros2 service call /upper/upper_drag_teach_record_clear tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `upper_drag_teach_record_pause`

- **功能说明**: 暂停录制拖动示教轨迹
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/left_arm/upper_drag_teach_record_pause`
  - `/right_arm/upper_drag_teach_record_pause`
  - `/upper/upper_drag_teach_record_pause`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/upper_drag_teach_record_pause tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 右臂 /right_arm
ros2 service call /right_arm/upper_drag_teach_record_pause tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 双臂 /upper
ros2 service call /upper/upper_drag_teach_record_pause tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `upper_export_dynamic_identify_traj`

- **功能说明**: 导出动力学辨识轨迹文件
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/ExportDynamicIdentifyTrajectory`（CLI: `tuyarobot_msgs/srv/ExportDynamicIdentifyTrajectory`）
- **ROS 名**:
  - `/left_arm/upper_export_dynamic_identify_traj`
  - `/right_arm/upper_export_dynamic_identify_traj`
  - `/upper/upper_export_dynamic_identify_traj`
- **请求字段**: `output_dir`（`string`）。
- **参数范围**: `output_dir` 为可选的 Orin 本地保存目录；省略或传空字符串时使用 `/home/tuya/tuya/dynamic`，Windows 环境使用当前工作目录下的 `dynamic`。
- **返回/观测**: `success` → `message` → `output_path` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/upper_export_dynamic_identify_traj tuyarobot_msgs/srv/ExportDynamicIdentifyTrajectory "{output_dir: ''}"

# 右臂 /right_arm
ros2 service call /right_arm/upper_export_dynamic_identify_traj tuyarobot_msgs/srv/ExportDynamicIdentifyTrajectory "{output_dir: ''}"

# 双臂 /upper
ros2 service call /upper/upper_export_dynamic_identify_traj tuyarobot_msgs/srv/ExportDynamicIdentifyTrajectory "{output_dir: ''}"
```

### `upper_firmware_flash`

- **功能说明**: 升级上半身主控。不分左右臂
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperFirmwareFlash`（CLI: `tuyarobot_msgs/srv/UpperFirmwareFlash`）
- **ROS 名**:
  - `/upper/upper_firmware_flash`
- **请求字段**: `firmware_path`（`string`）、`restart_mode`（`string`）、`skip_md5_check`（`bool`）。
- **参数范围**: `firmware_path` 为 Orin 本地绝对路径，目标文件最终落为 RK `/root/Tuya/bin/TuyaBody`。`restart_mode`：远程 RK 已部署 `tuya_body_watchdog.sh` 时应显式传入 `watchdog`；未部署看门狗时用 `direct` 直接启动 `TuyaBody`。`skip_md5_check` 需显式传入；true 跳过 MD5 白名单校验，false 启用该校验。
- **返回/观测**: `success` → `message` → `version` → `response_time_ms`；`skip_md5_check` 需由调用方显式传入；耗时长，勿在运动中调用。
- **调用示例**:

```bash
ros2 service call /upper/upper_firmware_flash tuyarobot_msgs/srv/UpperFirmwareFlash "{firmware_path: '/path/to/upper.bin', restart_mode: 'watchdog', skip_md5_check: true}"
```

### `upper_fourier_trajectories`

- **功能说明**: 执行动力学辨识运动轨迹
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/RunUpperFourierTrajectory`（CLI: `tuyarobot_msgs/srv/RunUpperFourierTrajectory`）
- **ROS 名**:
  - `/left_arm/upper_fourier_trajectories`
  - `/right_arm/upper_fourier_trajectories`
  - `/upper/upper_fourier_trajectories`
- **请求字段**: `rank`（`int32`）、`async_mode`（`bool`）。
- **参数范围**: `rank` 仅支持 `0` 或 `1`，`0=正常轨迹`，`1=低速确认轨迹`。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/upper_fourier_trajectories tuyarobot_msgs/srv/RunUpperFourierTrajectory "{rank: 1, async_mode: true}"

# 右臂 /right_arm
ros2 service call /right_arm/upper_fourier_trajectories tuyarobot_msgs/srv/RunUpperFourierTrajectory "{rank: 1, async_mode: true}"

# 双臂 /upper
ros2 service call /upper/upper_fourier_trajectories tuyarobot_msgs/srv/RunUpperFourierTrajectory "{rank: 1, async_mode: true}"
```

### `upper_go_zero`

- **功能说明**: 控制上半身回零
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperAsyncTrigger`（CLI: `tuyarobot_msgs/srv/UpperAsyncTrigger`）
- **ROS 名**:
  - `/left_arm/upper_go_zero`
  - `/right_arm/upper_go_zero`
  - `/upper/upper_go_zero`
- **请求字段**: `async_mode`。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/upper_go_zero tuyarobot_msgs/srv/UpperAsyncTrigger "{async_mode: true}"

# 右臂 /right_arm
ros2 service call /right_arm/upper_go_zero tuyarobot_msgs/srv/UpperAsyncTrigger "{async_mode: true}"

# 双臂 /upper
ros2 service call /upper/upper_go_zero tuyarobot_msgs/srv/UpperAsyncTrigger "{async_mode: true}"
```

### `upper_jog_angle`

#### Topic（订阅/控制）

- **功能说明**: 按方向持续点动指定关节
- **类型**: Topic（订阅/控制）
- **消息/服务类型**: `tuyarobot_msgs/UpperJogAngleCommand`（CLI: `tuyarobot_msgs/msg/UpperJogAngleCommand`）
- **ROS 名**:
  - `/left_arm/upper_jog_angle`
  - `/right_arm/upper_jog_angle`
  - `/upper/upper_jog_angle`
- **消息字段**: `joint_id`（`int32`）、`direction`（`int32`）、`speed`（`int32`）。
- **参数范围**: `joint_id` 为 `1~7`；`direction` 仅支持 `0` 或 `1`；`speed` 为 `1~100`。Topic固定向SDK传`_async=True`。
- **返回/观测**: 无同步回包；成功与否看 operation 审计日志；状态用对应 get_* Topic/Service 观测。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 topic pub -w 1 --keep-alive 2 --once /left_arm/upper_jog_angle tuyarobot_msgs/msg/UpperJogAngleCommand "{joint_id: 1, direction: 1, speed: 20}"

# 右臂 /right_arm
ros2 topic pub -w 1 --keep-alive 2 --once /right_arm/upper_jog_angle tuyarobot_msgs/msg/UpperJogAngleCommand "{joint_id: 1, direction: 1, speed: 20}"

# 双臂 /upper
ros2 topic pub -w 1 --keep-alive 2 --once /upper/upper_jog_angle tuyarobot_msgs/msg/UpperJogAngleCommand "{joint_id: 1, direction: 1, speed: 20}"
```

#### Service

- **功能说明**: 按方向持续点动指定关节
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperJogAngle`（CLI: `tuyarobot_msgs/srv/UpperJogAngle`）
- **ROS 名**:
  - `/left_arm/service/upper_jog_angle`
- **请求字段**: `joint_id`（`int32`）、`direction`（`int32`）、`speed`（`int32`）。
- **参数范围**: 参数范围由SDK校验，ROS不增加业务参数校验；固定异步调用。
- **返回/观测**: `success` → `message` → `response_time_ms`。`message`对齐SDK返回；固定向SDK传`_async=True`。
- **调用示例**:

```bash
ros2 service call /left_arm/service/upper_jog_angle tuyarobot_msgs/srv/UpperJogAngle "{joint_id: 1, direction: 1, speed: 20}"
```

#### Service

- **功能说明**: 按方向持续点动指定关节
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperJogAngle`（CLI: `tuyarobot_msgs/srv/UpperJogAngle`）
- **ROS 名**:
  - `/right_arm/service/upper_jog_angle`
- **请求字段**: `joint_id`（`int32`）、`direction`（`int32`）、`speed`（`int32`）。
- **参数范围**: 参数范围由SDK校验，ROS不增加业务参数校验；固定异步调用。
- **返回/观测**: `success` → `message` → `response_time_ms`。`message`对齐SDK返回；固定向SDK传`_async=True`。
- **调用示例**:

```bash
ros2 service call /right_arm/service/upper_jog_angle tuyarobot_msgs/srv/UpperJogAngle "{joint_id: 1, direction: 1, speed: 20}"
```

#### Service

- **功能说明**: 同时持续点动双臂的同一关节
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperJogAngle`（CLI: `tuyarobot_msgs/srv/UpperJogAngle`）
- **ROS 名**:
  - `/upper/service/upper_jog_angle`
- **请求字段**: `joint_id`（`int32`）、`direction`（`int32`）、`speed`（`int32`）。
- **参数范围**: 参数范围由SDK校验，ROS不增加业务参数校验；同一组参数作用于左右臂，固定异步调用。
- **返回/观测**: `success` → `message` → `response_time_ms`。`message`对齐SDK返回；固定向SDK传`_async=True`。
- **调用示例**:

```bash
ros2 service call /upper/service/upper_jog_angle tuyarobot_msgs/srv/UpperJogAngle "{joint_id: 1, direction: 1, speed: 20}"
```

### `upper_jog_angle_increment`

#### Topic（订阅/控制）

- **功能说明**: 增量点动关节角度
- **类型**: Topic（订阅/控制）
- **消息/服务类型**: `tuyarobot_msgs/UpperJogAngleIncrementCommand`（CLI: `tuyarobot_msgs/msg/UpperJogAngleIncrementCommand`）
- **ROS 名**:
  - `/left_arm/upper_jog_angle_increment`
  - `/right_arm/upper_jog_angle_increment`
  - `/upper/upper_jog_angle_increment`
- **消息字段**: `joint_id`（`int32`）、`increment`（`float64`）、`speed`（`int32`）。
- **参数范围**: `joint_id` 为 `1~7`，J8不支持；`increment` 为增量角度，J1 `-320~320`、J2 `-175~175`、J3 `-320~320`、J4 `-154~154`、J5 `-320~320`、J6 `-125~125`、J7 `-150~150`；`speed` 为 `1~100`。
- **返回/观测**: 无同步回包；成功与否看 operation 审计日志；状态用对应 get_* Topic/Service 观测。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 topic pub -w 1 --keep-alive 2 --once /left_arm/upper_jog_angle_increment tuyarobot_msgs/msg/UpperJogAngleIncrementCommand "{joint_id: 1, increment: 1.0, speed: 20}"

# 右臂 /right_arm
ros2 topic pub -w 1 --keep-alive 2 --once /right_arm/upper_jog_angle_increment tuyarobot_msgs/msg/UpperJogAngleIncrementCommand "{joint_id: 1, increment: 1.0, speed: 20}"

# 双臂 /upper
ros2 topic pub -w 1 --keep-alive 2 --once /upper/upper_jog_angle_increment tuyarobot_msgs/msg/UpperJogAngleIncrementCommand "{joint_id: 1, increment: 1.0, speed: 20}"
```

#### Service

- **功能说明**: 增量点动关节角度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperJogAngleIncrement`（CLI: `tuyarobot_msgs/srv/UpperJogAngleIncrement`）
- **ROS 名**:
  - `/left_arm/service/upper_jog_angle_increment`
- **请求字段**: `joint_id`（`int32`）、`increment`（`float64`）、`speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**: `joint_id` 为 `1~7`，J8不支持；`increment` 范围为J1 `-320~320`、J2 `-175~175`、J3 `-320~320`、J4 `-154~154`、J5 `-320~320`、J6 `-125~125`、J7 `-150~150`，单位为度；`speed` 为 `1~100`。
- **返回/观测**: `success` → `message` → `response_time_ms`。刷新模式（fresh_mode=1）直接失败且不下发；插补模式下，`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。
- **调用示例**:

```bash
ros2 service call /left_arm/service/upper_jog_angle_increment tuyarobot_msgs/srv/UpperJogAngleIncrement "{joint_id: 1, increment: 1.0, speed: 20, async_mode: false}"
```

#### Service

- **功能说明**: 增量点动关节角度
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperJogAngleIncrement`（CLI: `tuyarobot_msgs/srv/UpperJogAngleIncrement`）
- **ROS 名**:
  - `/right_arm/service/upper_jog_angle_increment`
- **请求字段**: `joint_id`（`int32`）、`increment`（`float64`）、`speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**: `joint_id` 为 `1~7`，J8不支持；`increment` 范围为J1 `-320~320`、J2 `-175~175`、J3 `-320~320`、J4 `-154~154`、J5 `-320~320`、J6 `-125~125`、J7 `-150~150`，单位为度；`speed` 为 `1~100`。
- **返回/观测**: `success` → `message` → `response_time_ms`。刷新模式（fresh_mode=1）直接失败且不下发；插补模式下，`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。
- **调用示例**:

```bash
ros2 service call /right_arm/service/upper_jog_angle_increment tuyarobot_msgs/srv/UpperJogAngleIncrement "{joint_id: 1, increment: 1.0, speed: 20, async_mode: false}"
```

#### Service

- **功能说明**: 同时增量点动双臂的同一关节
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperJogAngleIncrement`（CLI: `tuyarobot_msgs/srv/UpperJogAngleIncrement`）
- **ROS 名**:
  - `/upper/service/upper_jog_angle_increment`
- **请求字段**: `joint_id`（`int32`）、`increment`（`float64`）、`speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**: `joint_id` 为 `1~7`，J8不支持；`increment` 范围为J1 `-320~320`、J2 `-175~175`、J3 `-320~320`、J4 `-154~154`、J5 `-320~320`、J6 `-125~125`、J7 `-150~150`，单位为度；`speed` 为 `1~100`。同一组参数同时作用于左右臂。
- **返回/观测**: `success` → `message` → `response_time_ms`。刷新模式（fresh_mode=1）直接失败且不下发；插补模式下，`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。
- **调用示例**:

```bash
ros2 service call /upper/service/upper_jog_angle_increment tuyarobot_msgs/srv/UpperJogAngleIncrement "{joint_id: 1, increment: 1.0, speed: 20, async_mode: false}"
```

### `upper_jog_coord`

#### Topic（订阅/控制）

- **功能说明**: 沿指定末端坐标轴持续点动
- **类型**: Topic（订阅/控制）
- **消息/服务类型**: `tuyarobot_msgs/UpperCartesianJog`（CLI: `tuyarobot_msgs/msg/UpperCartesianJog`）
- **ROS 名**:
  - `/left_arm/upper_jog_coord`
  - `/right_arm/upper_jog_coord`
  - `/upper/upper_jog_coord`
- **消息字段**: `coord_id`（`int32`）、`direction`（`int32`）、`speed`（`int32`）。
- **参数范围**: `coord_id` 为 `1~6`，依次对应 `x/y/z/rx/ry/rz`；方向仅支持 `0` 或 `1`；`speed` 为 `1~100`。Topic固定向SDK传`_async=True`，连续点动不会产生到位结果。
- **返回/观测**: 无同步回包；成功与否看 operation 审计日志；状态用对应 get_* Topic/Service 观测。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 topic pub -w 1 --keep-alive 2 --once /left_arm/upper_jog_coord tuyarobot_msgs/msg/UpperCartesianJog "{coord_id: 1, direction: 1, speed: 20}"

# 右臂 /right_arm
ros2 topic pub -w 1 --keep-alive 2 --once /right_arm/upper_jog_coord tuyarobot_msgs/msg/UpperCartesianJog "{coord_id: 1, direction: 1, speed: 20}"

# 双臂 /upper
ros2 topic pub -w 1 --keep-alive 2 --once /upper/upper_jog_coord tuyarobot_msgs/msg/UpperCartesianJog "{coord_id: 1, direction: 1, speed: 20}"
```

#### Service

- **功能说明**: 沿指定末端坐标轴持续点动
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperJogCoord`（CLI: `tuyarobot_msgs/srv/UpperJogCoord`）
- **ROS 名**:
  - `/left_arm/service/upper_jog_coord`
- **请求字段**: `coord_id`（`int32`）、`direction`（`int32`）、`speed`（`int32`）。
- **参数范围**: 参数范围由SDK校验，ROS不增加业务参数校验；固定异步调用。
- **返回/观测**: `success` → `message` → `response_time_ms`。`message`对齐SDK返回；固定向SDK传`_async=True`。
- **调用示例**:

```bash
ros2 service call /left_arm/service/upper_jog_coord tuyarobot_msgs/srv/UpperJogCoord "{coord_id: 1, direction: 1, speed: 20}"
```

#### Service

- **功能说明**: 沿指定末端坐标轴持续点动
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperJogCoord`（CLI: `tuyarobot_msgs/srv/UpperJogCoord`）
- **ROS 名**:
  - `/right_arm/service/upper_jog_coord`
- **请求字段**: `coord_id`（`int32`）、`direction`（`int32`）、`speed`（`int32`）。
- **参数范围**: 参数范围由SDK校验，ROS不增加业务参数校验；固定异步调用。
- **返回/观测**: `success` → `message` → `response_time_ms`。`message`对齐SDK返回；固定向SDK传`_async=True`。
- **调用示例**:

```bash
ros2 service call /right_arm/service/upper_jog_coord tuyarobot_msgs/srv/UpperJogCoord "{coord_id: 1, direction: 1, speed: 20}"
```

#### Service

- **功能说明**: 同时沿双臂的同一末端坐标轴持续点动
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperJogCoord`（CLI: `tuyarobot_msgs/srv/UpperJogCoord`）
- **ROS 名**:
  - `/upper/service/upper_jog_coord`
- **请求字段**: `coord_id`（`int32`）、`direction`（`int32`）、`speed`（`int32`）。
- **参数范围**: 参数范围由SDK校验，ROS不增加业务参数校验；同一组参数作用于左右臂，固定异步调用。
- **返回/观测**: `success` → `message` → `response_time_ms`。`message`对齐SDK返回；固定向SDK传`_async=True`。
- **调用示例**:

```bash
ros2 service call /upper/service/upper_jog_coord tuyarobot_msgs/srv/UpperJogCoord "{coord_id: 1, direction: 1, speed: 20}"
```

### `upper_jog_coord_increment`

#### Topic（订阅/控制）

- **功能说明**: 增量点动末端坐标
- **类型**: Topic（订阅/控制）
- **消息/服务类型**: `tuyarobot_msgs/UpperCartesianIncrement`（CLI: `tuyarobot_msgs/msg/UpperCartesianIncrement`）
- **ROS 名**:
  - `/left_arm/upper_jog_coord_increment`
  - `/right_arm/upper_jog_coord_increment`
  - `/upper/upper_jog_coord_increment`
- **消息字段**: `coord_id`（`int32`）、`increment`（`float64`）、`speed`（`int32`）、`async_mode`（`int32`）。
- **参数范围**: `coord_id` 为 `1~6`，依次对应 `x/y/z/rx/ry/rz`；`increment` 范围为X `-1390~1390`、Y `-1155~1155`、Z `-1351~1351` mm，RX/RY/RZ `-360~360` 度；`speed` 为 `1~100`。
- **返回/观测**: 无同步回包；成功与否看 operation 审计日志；状态用对应 get_* Topic/Service 观测。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 topic pub -w 1 --keep-alive 2 --once /left_arm/upper_jog_coord_increment tuyarobot_msgs/msg/UpperCartesianIncrement "{coord_id: 1, increment: 1.0, speed: 20}"

# 右臂 /right_arm
ros2 topic pub -w 1 --keep-alive 2 --once /right_arm/upper_jog_coord_increment tuyarobot_msgs/msg/UpperCartesianIncrement "{coord_id: 1, increment: 1.0, speed: 20}"

# 双臂 /upper
ros2 topic pub -w 1 --keep-alive 2 --once /upper/upper_jog_coord_increment tuyarobot_msgs/msg/UpperCartesianIncrement "{coord_id: 1, increment: 1.0, speed: 20}"
```

#### Service

- **功能说明**: 增量点动末端坐标
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperJogCoordIncrement`（CLI: `tuyarobot_msgs/srv/UpperJogCoordIncrement`）
- **ROS 名**:
  - `/left_arm/service/upper_jog_coord_increment`
- **请求字段**: `coord_id`（`int32`）、`increment`（`float64`）、`speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**: `coord_id` 为 `1~6`，依次对应 `x/y/z/rx/ry/rz`；`increment` 范围为X `-1390~1390`、Y `-1155~1155`、Z `-1351~1351` mm，RX/RY/RZ `-360~360` 度；`speed` 为 `1~100`。
- **返回/观测**: `success` → `message` → `response_time_ms`。刷新模式（fresh_mode=1）直接失败且不下发；插补模式下，`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。
- **调用示例**:

```bash
ros2 service call /left_arm/service/upper_jog_coord_increment tuyarobot_msgs/srv/UpperJogCoordIncrement "{coord_id: 1, increment: 1.0, speed: 20, async_mode: false}"
```

#### Service

- **功能说明**: 增量点动末端坐标
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperJogCoordIncrement`（CLI: `tuyarobot_msgs/srv/UpperJogCoordIncrement`）
- **ROS 名**:
  - `/right_arm/service/upper_jog_coord_increment`
- **请求字段**: `coord_id`（`int32`）、`increment`（`float64`）、`speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**: `coord_id` 为 `1~6`，依次对应 `x/y/z/rx/ry/rz`；`increment` 范围为X `-1390~1390`、Y `-1155~1155`、Z `-1351~1351` mm，RX/RY/RZ `-360~360` 度；`speed` 为 `1~100`。
- **返回/观测**: `success` → `message` → `response_time_ms`。刷新模式（fresh_mode=1）直接失败且不下发；插补模式下，`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。
- **调用示例**:

```bash
ros2 service call /right_arm/service/upper_jog_coord_increment tuyarobot_msgs/srv/UpperJogCoordIncrement "{coord_id: 1, increment: 1.0, speed: 20, async_mode: false}"
```

#### Service

- **功能说明**: 同时增量点动双臂的同一末端坐标轴
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperJogCoordIncrement`（CLI: `tuyarobot_msgs/srv/UpperJogCoordIncrement`）
- **ROS 名**:
  - `/upper/service/upper_jog_coord_increment`
- **请求字段**: `coord_id`（`int32`）、`increment`（`float64`）、`speed`（`int32`）、`async_mode`（`bool`）。
- **参数范围**: `coord_id` 为 `1~6`，依次对应 `x/y/z/rx/ry/rz`；`increment` 范围为X `-1390~1390`、Y `-1155~1155`、Z `-1351~1351` mm，RX/RY/RZ `-360~360` 度；`speed` 为 `1~100`。同一组参数同时作用于左右臂。
- **返回/观测**: `success` → `message` → `response_time_ms`。刷新模式（fresh_mode=1）直接失败且不下发；插补模式下，`async_mode=false`时同步等待SDK完成，`async_mode=true`时异步等待SDK受理。
- **调用示例**:

```bash
ros2 service call /upper/service/upper_jog_coord_increment tuyarobot_msgs/srv/UpperJogCoordIncrement "{coord_id: 1, increment: 1.0, speed: 20, async_mode: false}"
```

### `upper_parameter_identify`

- **功能说明**: 执行上半身动力学参数辨识
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperAsyncTrigger`（CLI: `tuyarobot_msgs/srv/UpperAsyncTrigger`）
- **ROS 名**:
  - `/left_arm/upper_parameter_identify`
  - `/right_arm/upper_parameter_identify`
  - `/upper/upper_parameter_identify`
- **请求字段**: `async_mode`。
- **使用条件**: 仅插补模式可用。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/upper_parameter_identify tuyarobot_msgs/srv/UpperAsyncTrigger "{async_mode: true}"

# 右臂 /right_arm
ros2 service call /right_arm/upper_parameter_identify tuyarobot_msgs/srv/UpperAsyncTrigger "{async_mode: true}"

# 双臂 /upper
ros2 service call /upper/upper_parameter_identify tuyarobot_msgs/srv/UpperAsyncTrigger "{async_mode: true}"
```

### `upper_pause`

- **功能说明**: 暂停上半身运动
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperAsyncTrigger`（CLI: `tuyarobot_msgs/srv/UpperAsyncTrigger`）
- **ROS 名**:
  - `/left_arm/upper_pause`
  - `/right_arm/upper_pause`
  - `/upper/upper_pause`
- **请求字段**: `async_mode`。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/upper_pause tuyarobot_msgs/srv/UpperAsyncTrigger "{async_mode: true}"

# 右臂 /right_arm
ros2 service call /right_arm/upper_pause tuyarobot_msgs/srv/UpperAsyncTrigger "{async_mode: true}"

# 双臂 /upper
ros2 service call /upper/upper_pause tuyarobot_msgs/srv/UpperAsyncTrigger "{async_mode: true}"
```

### `upper_power_off`

- **功能说明**: 对指定作用域执行下电；单臂作用域只关闭对应手臂，`/upper` 关闭双臂。
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/left_arm/upper_power_off`
  - `/right_arm/upper_power_off`
  - `/upper/upper_power_off`
- **请求字段**: 无。
- **返回语义**: `success=true` 表示对应作用域下电命令执行成功。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂
ros2 service call /left_arm/upper_power_off tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 右臂
ros2 service call /right_arm/upper_power_off tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 双臂
ros2 service call /upper/upper_power_off tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `upper_power_on`

- **功能说明**: 上半身设备上电
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/left_arm/upper_power_on`
  - `/right_arm/upper_power_on`
  - `/upper/upper_power_on`
- **请求字段**: 无。
- **返回语义**: `success=true` 表示对应作用域上电命令执行成功。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/upper_power_on tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 右臂 /right_arm
ros2 service call /right_arm/upper_power_on tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 双臂 /upper
ros2 service call /upper/upper_power_on tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `upper_resume`

- **功能说明**: 恢复上半身运动
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/left_arm/upper_resume`
  - `/right_arm/upper_resume`
  - `/upper/upper_resume`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/upper_resume tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 右臂 /right_arm
ros2 service call /right_arm/upper_resume tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 双臂 /upper
ros2 service call /upper/upper_resume tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `upper_set_break`

- **功能说明**: 设置上半身关节抱闸
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetArmScope`（CLI: `tuyarobot_msgs/srv/SetArmScope`）
- **ROS 名**:
  - `/left_arm/upper_set_break`
  - `/right_arm/upper_set_break`
  - `/upper/upper_set_break`
- **请求字段**: `arm_type`（`int32`）、`param_id`（`int32`）、`param_value`（`int32`）。
- **参数范围**: `param_id`：关节号 `1~7`；`param_value`：`0` 释放抱闸，`1` 打开抱闸。 `arm_type` 为兼容字段，取 `1/2/3`，实际作用域由 ROS 路径决定。
- **返回/观测**: `success` → `message` → `result_value`（成功通常为 1） → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/upper_set_break tuyarobot_msgs/srv/SetArmScope "{arm_type: 1, param_id: 1, param_value: 1}"

# 右臂 /right_arm
ros2 service call /right_arm/upper_set_break tuyarobot_msgs/srv/SetArmScope "{arm_type: 1, param_id: 1, param_value: 1}"

# 双臂 /upper
ros2 service call /upper/upper_set_break tuyarobot_msgs/srv/SetArmScope "{arm_type: 1, param_id: 1, param_value: 1}"
```

### `upper_stop`

- **功能说明**: 停止上半身运动
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/TuyarobotTrigger`（CLI: `tuyarobot_msgs/srv/TuyarobotTrigger`）
- **ROS 名**:
  - `/left_arm/upper_stop`
  - `/right_arm/upper_stop`
  - `/upper/upper_stop`
- **请求字段**: 无。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/upper_stop tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 右臂 /right_arm
ros2 service call /right_arm/upper_stop tuyarobot_msgs/srv/TuyarobotTrigger '{}'

# 双臂 /upper
ros2 service call /upper/upper_stop tuyarobot_msgs/srv/TuyarobotTrigger '{}'
```

### `upper_tool_firmware_flash`

- **功能说明**: 触发末端板使用已有固件升级
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/UpperToolFirmwareFlash`（CLI: `tuyarobot_msgs/srv/UpperToolFirmwareFlash`）
- **ROS 名**:
  - `/left_arm/upper_tool_firmware_flash`
  - `/right_arm/upper_tool_firmware_flash`
  - `/upper/upper_tool_firmware_flash`
- **请求字段**: `main_version`（`string`）。
- **参数范围**: `main_version` 为数值版本字符串，乘以 `10` 并取整后的结果须为 `0~255`；不接收固件路径或 MD5 参数。
- **返回语义**: 单臂 `versions[]` 为1项，`/upper` 为2项 `[left,right]`，表示升级后的末端工具版本号。
- **返回/观测**: `success` → `message` → `versions[]` → `response_time_ms`；使用设备已有固件升级，耗时较长，禁止在运动中调用。
- **调用示例**:

```bash
# 左臂 /left_arm
ros2 service call /left_arm/upper_tool_firmware_flash tuyarobot_msgs/srv/UpperToolFirmwareFlash "{main_version: '1.0'}"

# 右臂 /right_arm
ros2 service call /right_arm/upper_tool_firmware_flash tuyarobot_msgs/srv/UpperToolFirmwareFlash "{main_version: '1.0'}"

# 双臂 /upper
ros2 service call /upper/upper_tool_firmware_flash tuyarobot_msgs/srv/UpperToolFirmwareFlash "{main_version: '1.0'}"
```

<a id="sensors"></a>
## 四、感知接口说明

<a id="sensors-conventions"></a>
### 使用约定

- 2D：读取运行时 `perception_config.yaml` 的 V4L2 路径并校验字符设备与三路唯一；3D：读取其中的 RealSense `serial_no`；雷达：读取 `perception.lidar.lslidar`；VTN：读取 `perception.vtn_wakeup.sn`。各模块仅补齐和校验自己的配置字段。
- D435 Topic 表中的 `<role>` 取值为 `agv`、`abdomen`、`head`，同一路径中的两个 `<role>` 必须取相同值。
- 感知日志：2D相机写入 `/home/tuya/tuya/logs/sensor/2d_camera`，3D相机写入 `/home/tuya/tuya/logs/sensor/3d_camera/3d_camera_YYYYMMDD.log`，雷达写入 `/home/tuya/tuya/logs/sensor/lslidar`。3D相机关键事件同时写入 `Tuya_ROS2_ALL.log` 及对应的INFO、WARN或ERROR分级日志。
- 感知配置唯一运行时文件为 `/home/tuya/tuya/config/perception_config.yaml`；创建、补缺、覆盖和失败事件写入 `Tuya_ROS2_ALL.log` 及对应分级日志，3D 复用专用日志链路且不重复整机事件。
- `robot.launch.py`的四个感知开关默认均为`false`；`mock.launch.py`不启动感知节点。感知Topic仅在对应模块启动后可用。

运行时设备映射（唯一文件）为 `${TUYA_HOME:-$HOME/tuya}/config/perception_config.yaml`：
`perception.camera_2d.{right_2d_camera,left_2d_camera,agv_2d_camera}`、
`perception.camera_3d.{agv_3d_camera,abdomen_3d_camera,head_3d_camera}`、
`perception.lidar.lslidar` 和 `perception.vtn_wakeup.sn`。初始化脚本与 Launch 共用原子写入、Linux 进程锁和只补缺字段实现。

<a id="api-sensors"></a>
### `lidar`

- **功能说明**: 发布二维扫描和三维点云
- **类型**: Topic（发布）
- **消息类型**: `sensor_msgs/LaserScan + PointCloud2`
- **ROS 名**:
  - `/lidar/scan`
  - `/lidar/points`
- **返回语义**: `LaserScan.ranges[]` 与 `PointCloud2` 的XYZ坐标单位为米；`LaserScan` 角度字段单位为弧度。有效距离 `0.2~200 m`（`config/lidar.yaml`）。串口使用 `perception.lidar.lslidar` 映射。
- **返回/观测**: LaserScan ranges[] 非空；PointCloud2 有点数据。
- **启动**: `ros2 launch tuyarobot_sensors lidar.launch.py`
- **调用示例**:

```bash
timeout 5s ros2 topic echo /lidar/scan --once
```

### `2d_cameras`

- **功能说明**: 发布三路二维图像及相机内参
- **类型**: Topic（发布）
- **消息类型**: `sensor_msgs/Image + sensor_msgs/CameraInfo`
- **ROS 名**:
  - `/left_2d_camera/image_raw`
  - `/left_2d_camera/camera_info`
  - `/right_2d_camera/image_raw`
  - `/right_2d_camera/camera_info`
  - `/agv_2d_camera/image_raw`
  - `/agv_2d_camera/camera_info`
- **返回语义**: 图像宽高单位为像素，固定640x480 @ 30fps；`CameraInfo.k/p`中的焦距与主点使用像素坐标。设备路径来自 `perception.camera_2d.*`（`config/rgb_cam.yaml` 仅保留图像参数）。
- **返回/观测**: Image 宽高与 encoding 正常；日志位于 `/home/tuya/tuya/logs/sensor/2d_camera/`。
- **启动**: `ros2 launch tuyarobot_sensors rgb_cameras.launch.py`
- **调用示例**:

```bash
timeout 5s ros2 topic echo /left_2d_camera/image_raw --once
timeout 5s ros2 topic echo /left_2d_camera/camera_info --once
```

### `d435_cameras`

- **功能说明**: 发布三路彩色、深度及IMU数据
- **类型**: Topic（发布）
- **消息类型**: `sensor_msgs/Image + sensor_msgs/CameraInfo`；D435I 启用 IMU 时另有 `sensor_msgs/Imu`
- **ROS 根命名空间/节点名**:
  - `/agv_3d_camera/agv_3d_camera_node`
  - `/abdomen_3d_camera/abdomen_3d_camera_node`
  - `/head_3d_camera/head_3d_camera_node`
- **Topic 后缀**: `/color/image_raw`、`/color/camera_info`、`/depth/image_rect_raw`、`/depth/camera_info`；D435I 启用 IMU 时另有 `/gyro/sample`、`/accel/sample`、`/imu`。
- **配置**: Color/Depth 固定 640x480@30；Infra、PointCloud、Depth alignment 和同步关闭。
- **返回语义**: 图像宽高单位为像素；`CameraInfo.k/p`中的焦距与主点使用像素坐标；`Z16/16UC1` 深度值乘相机 `depth_scale` 后换算为米；IMU线加速度单位为 `m/s²`，角速度单位为 `rad/s`。
- **多机规则**: 无参数时读取 `perception.camera_3d.*` 的三个唯一序列号；显式传入对应 `*_device` 仅覆盖本次启动且不回写。最终 SN 为空记录 `ERROR` 并停止 Launch，不使用历史默认值。命名空间和节点名固定，三个驱动使用独立进程；型号为 `auto` 时按实际设备决定 IMU。
- **启动参数**:

| 参数 | 默认值 | 说明 |
|---|---|---|
| `agv_3d_camera_device` | 空（读取 `perception.camera_3d.agv_3d_camera`） | AGV 相机序列号 |
| `abdomen_3d_camera_device` | 空（读取 `perception.camera_3d.abdomen_3d_camera`） | abdomen 相机序列号 |
| `head_3d_camera_device` | 空（读取 `perception.camera_3d.head_3d_camera`） | head 相机序列号 |
| `agv_3d_camera_model` | `auto` | `auto`、`d435` 或 `d435i` |
| `abdomen_3d_camera_model` | `auto` | `auto`、`d435` 或 `d435i` |
| `head_3d_camera_model` | `auto` | `auto`、`d435` 或 `d435i` |
| `config_file` | 包内 `config/d435.yaml` | 三路共用的 RealSense 参数文件 |

- **IMU**: Accel 默认 100 Hz、Gyro 默认 200 Hz，`unite_imu_method=2` 生成融合 `imu` Topic。
- **单机启动**:
  `ros2 launch tuyarobot_sensors d435.launch.py serial_no:=261722072906 camera_model:=d435i camera_namespace:=agv_3d_camera camera_name:=agv_3d_camera_node`
- **三机启动**:
  `ros2 launch tuyarobot_sensors d435_cameras.launch.py agv_3d_camera_device:=<SN1> abdomen_3d_camera_device:=<SN2> head_3d_camera_device:=<SN3>`
- **调用示例**:

```bash
timeout 5s ros2 topic echo /agv_3d_camera/agv_3d_camera_node/color/image_raw --qos-profile sensor_data --once
timeout 5s ros2 topic echo /agv_3d_camera/agv_3d_camera_node/color/camera_info --qos-profile sensor_data --once
timeout 5s ros2 topic echo /agv_3d_camera/agv_3d_camera_node/depth/image_rect_raw --qos-profile sensor_data --once
timeout 5s ros2 topic echo /agv_3d_camera/agv_3d_camera_node/depth/camera_info --qos-profile sensor_data --once
timeout 5s ros2 topic echo /agv_3d_camera/agv_3d_camera_node/gyro/sample --qos-profile sensor_data --once
timeout 5s ros2 topic echo /agv_3d_camera/agv_3d_camera_node/accel/sample --qos-profile sensor_data --once
timeout 5s ros2 topic echo /agv_3d_camera/agv_3d_camera_node/imu --qos-profile sensor_data --once
```

### `voice_wakeup`

- **功能说明**: 检测唤醒词并发布声源方向
- **类型**: Topic（发布）
- **消息类型**: `tuyarobot_msgs/VoiceWakeup`
- **ROS 名**:
  - `/voice/wakeup`
- **返回语义**: `raw_angle_deg` 为 VTN 原始角；`angle_deg` 含 offset/invert。唤醒词默认「嘿，涂鸦」。回声消除达标判据：本机喇叭播报唤醒词不产生唤醒、近场人声与外部声源正常唤醒；`rolling_record_channel: 0` 的滚动录音录到喇叭声属正常，不代表 AEC 失败。
- **返回/观测**: 唤醒成功发布一帧，含角度字段。
- **启动**: `ros2 launch tuyarobot_sensors vtn_wakeup.launch.py`（无参读取运行时配置，显式`sn`仅覆盖本次启动）
- **启动参数**:

| 参数 | 默认值 | 说明 |
|---|---|---|
| `appid` | `9faae788` | 授权应用 ID |
| `sn` | 空（读取 `perception.vtn_wakeup.sn`） | 麦阵序列号；显式值仅本次覆盖；长度 ≤32；仅 ASCII 字母数字及 `-` `:` `_` |
| `angle_offset_deg` | `0` | 唤醒角度偏置（度），用于正前方零位校准 |
| `save_rec` | `false` | 保存降噪后识别音频，存至 `/tmp/tuyarobot_vtn_wakeup/`；仅诊断用，开关不影响唤醒行为 |
| `save_aec` | `false` | 保存回声消除后音频，存至 `/tmp/tuyarobot_vtn_wakeup/`；仅诊断用，开关不影响唤醒行为 |
| `rolling_record_channel` | `0` | 滚动录音通道：0~5 为麦克风通道，6/7 为本机播报回采参考（仅用于验证回采接线，日常保持 0）；通道越界时自动禁用滚动录音，不影响唤醒 |

- **调用示例**:

```bash
timeout 30s ros2 topic echo /voice/wakeup --once
```

<a id="system"></a>
## 五、系统接口说明

<a id="system-conventions"></a>
### 使用约定

- `mock.launch.py` 不启动 `system_manager_node`；如需验证系统 Mock 接口，须单独启动系统管理节点并设置 `use_mock:=true`。
- 型号默认 `Tuya`（ROS 参数 `model`，可被 launch 覆盖）。
- 系统镜像版本默认读取 `/etc/version` 首行；文件缺失/为空/不可读时回退 `V1.0.0`。ROS软件栈版本由安装在`tuyarobot_bringup` Share目录中的`VERSION`提供。
- 整机实际版本记录在`${TUYA_HOME:-$HOME/tuya}/config/robot_version.yaml`；最低版本要求由用户填写在同目录的`robot_version_check.yaml`。校验项为`''`时跳过并记录日志，低于要求时记录`status=false`但不阻止启动。
- 与上半身固件版本无关（固件请用 `get_upper_main_version` / `get_head_main_version`）。
- 开机提示音：PCM WAV / 48 kHz / 16-bit / Mono；目标文件 `/home/tuya/tuya/config/boot/boot_prompt.wav`。
- `play_boot_sound` 的 `wav_path` 为空时播放已安装开机音，不报缺参错误。
- `set`/`play` 可能阻塞数秒（USB busy 重试）；与查询 Service 分属不同 callback group。
- **开机音日志**（不改 Python 库）：每次 Service 写入 `/home/tuya/tuya/logs/boot/boot_YYYYMMDD.log`；`success=False` 或 `played=False` 另抄一份到 `/home/tuya/tuya/logs/boot/boot_fail_YYYYMMDD.log`。整机操作总账位于 `/home/tuya/tuya/logs/ros2/operation_YYYYMMDD.log`。
- `/diagnostics` 由已启动的上半身、底盘、头部节点各自发布本模块链路状态；`diagnostics_publish_hz` 默认 `20Hz`，与 `*_publish_hz` 无关。
- 安全报警订阅内部固定约 20Hz 的 `_safety_snapshot` 与 `/diagnostics`，不订阅对外状态 Topic，也不执行停机、弹窗、声音或硬件查询。

### 整机版本配置

`system_manager_node`启动时创建并补齐以下文件：

```yaml
# ${TUYA_HOME:-$HOME/tuya}/config/robot_version.yaml
version:
  ros2: ''
  head: ''
  upper: ''
  chassis: ''
  hardware: ''

# ${TUYA_HOME:-$HOME/tuya}/config/robot_version_check.yaml
version:
  ros2: ''
  head: ''
  upper: ''
  chassis: ''
  python: ''
```

实际版本文件中的`hardware`及最低版本文件中的全部值由用户维护。最低版本字段严格为`''`时跳过对应校验并记录`status=skipped`；非空值低于要求时记录`status=false`，不阻止整机启动。

<a id="api-system"></a>
### `get_robot_type`

- **功能说明**: 读取ROS配置的整机型号
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetString`（CLI: `tuyarobot_msgs/srv/GetString`）
- **ROS 名**: `/system/get_robot_type`
- **返回语义**: 空请求；型号由参数 `model` 配置，默认 `Tuya`。
- **返回/观测**: `success` → `message` → `data` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /system/get_robot_type tuyarobot_msgs/srv/GetString '{}'
```

### `get_system_version`

- **功能说明**: 读取Orin系统镜像版本
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetString`（CLI: `tuyarobot_msgs/srv/GetString`）
- **ROS 名**: `/system/get_system_version`
- **返回语义**: 空请求；Real 读取版本文件首行，缺失或为空时回退 `V1.0.0`。
- **返回/观测**: `success` → `message` → `data` → `response_time_ms`。
- **参数**:

| 参数 | 默认 | 说明 |
|---|---|---|
| `model` | `Tuya` | 整机型号 |
| `version_file_path` | `/etc/version` | 版本文件路径（launch 参数名 `system_version_file`） |
| `use_mock` | launch 决定 | 单独启动系统管理节点且设为 `true` 时，固定返回 `Tuya` / `V1.0.0`；`mock.launch.py` 不启动该节点 |

- **调用示例**:

```bash
ros2 service call /system/get_system_version tuyarobot_msgs/srv/GetString '{}'
```

### `get_ros_version`

- **功能说明**: 读取Tuya ROS 2软件栈版本
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetString`（CLI: `tuyarobot_msgs/srv/GetString`）
- **ROS 名**: `/system/get_ros_version`
- **返回语义**: 空请求；读取`tuyarobot_bringup`安装Share目录中`VERSION`文件的首行，不调用机器人SDK，也不使用`system_version_file`参数。
- **返回/观测**: `success` → `message` → `data` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /system/get_ros_version tuyarobot_msgs/srv/GetString '{}'
```

### `get_robot_version`

- **功能说明**: 采集整机实际版本并更新运行时版本文件
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetRobotVersion`（CLI: `tuyarobot_msgs/srv/GetRobotVersion`）
- **ROS 名**: `/system/get_robot_version`
- **返回语义**: 空请求；读取ROS2版本及已启用头部、上半身、底盘的实际版本并写入`robot_version.yaml`，同时读取用户维护的`hardware`字段。该Service不执行最低版本校验，也不返回Python版本。
- **返回/观测**: `success` → `message` → `ros2_available` → `ros2_version` → `head_available` → `head_version` → `upper_available` → `upper_version` → `chassis_available` → `chassis_version` → `hardware_available` → `hardware_version` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /system/get_robot_version tuyarobot_msgs/srv/GetRobotVersion '{}'
```

### `is_robot_moving`

- **功能说明**: 汇总头部、双臂和底盘运动状态
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetRobotMoving`（CLI: `tuyarobot_msgs/srv/GetRobotMoving`）
- **ROS 名**:
  - `/system/is_robot_moving`
- **返回语义**: 空请求；Real 通过现有 ROS Service 汇总各运动节点状态。
- **返回/观测**: `success` → `message` → `upper_available` → `left_arm_moving` → `right_arm_moving` → `chassis_available` → `wheel_moving` → `lift_moving` → `head_available` → `head_moving` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /system/is_robot_moving tuyarobot_msgs/srv/GetRobotMoving '{}'
```

### `get_boot_sound_info`

- **功能说明**: 检查开机音文件、格式及播放设备
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetBootSoundInfo`（CLI: `tuyarobot_msgs/srv/GetBootSoundInfo`）
- **ROS 名**: `/system/get_boot_sound_info`
- **返回语义**: 空请求；目标格式为 PCM WAV、48kHz、16-bit、Mono。
- **返回/观测**: `success` → `message` → `path` → `factory_path` → `factory_exists` → `alsa_device` → `exists` → `format_ok` → `channels` → `sampwidth`（字节/采样点）→ `framerate`（Hz）→ `comptype` → `nframes`（采样帧数）→ `duration_s`（秒）→ `size_bytes`（字节）→ `diagnostics` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /system/get_boot_sound_info tuyarobot_msgs/srv/GetBootSoundInfo '{}'
```

### `set_boot_sound`

- **功能说明**: 复制开机音并尝试试听
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetBootSound`（CLI: `tuyarobot_msgs/srv/SetBootSound`）
- **ROS 名**: `/system/set_boot_sound`
- **参数范围**: `wav_path` 为节点所在主机的 PCM WAV、48kHz、16-bit、Mono 文件。
- **返回/观测**: `success` → `message` → `played` → `path` → `response_time_ms`。覆盖成功但试听失败时 `success=true`、`played=false`。
- **调用示例**:

```bash
ros2 service call /system/set_boot_sound tuyarobot_msgs/srv/SetBootSound "{wav_path: '/home/tuya/new_boot_prompt.wav'}"
```

### `play_boot_sound`

- **功能说明**: 播放指定或已安装开机音
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/PlayBootSound`（CLI: `tuyarobot_msgs/srv/PlayBootSound`）
- **ROS 名**: `/system/play_boot_sound`
- **参数范围**: `wav_path` 为空时播放已安装开机音；非空时播放指定本地 WAV。
- **返回/观测**: `success` → `message` → `played` → `path` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /system/play_boot_sound tuyarobot_msgs/srv/PlayBootSound "{wav_path: ''}"
```

### `restore_boot_sound`

- **功能说明**: 从出厂备份恢复开机音
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/RestoreBootSound`（CLI: `tuyarobot_msgs/srv/RestoreBootSound`）
- **ROS 名**: `/system/restore_boot_sound`
- **返回语义**: 空请求；从出厂备份覆盖当前开机音。
- **返回/观测**: `success` → `message` → `path` → `diagnostics` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /system/restore_boot_sound tuyarobot_msgs/srv/RestoreBootSound '{}'
```

### `get_robot_safety_alarm`

- **功能说明**: 读取整机安全报警分级
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetRobotSafetyAlarm`（CLI: `tuyarobot_msgs/srv/GetRobotSafetyAlarm`）
- **ROS 名**: `/robot/get_robot_safety_alarm`
- **请求字段**: `language`（`string`）。
- **参数范围**: 空值、`zh_CN` 或 `en_US`；空值使用安全配置语言。
- **返回/观测**: `success` → `message`（仅接口或配置失败原因）→ `overall_level`（`0` 正常、`1` 低、`2` 中、`3` 高）→ `messages[]`（本地化报警）→ `attitude_threshold_deg`（度）→ `response_time_ms`。无异常时中文返回 `["正常"]`，英文返回 `["OK"]`。
- **调用示例**:

```bash
ros2 service call /robot/get_robot_safety_alarm \
  tuyarobot_msgs/srv/GetRobotSafetyAlarm "{language: 'zh_CN'}"
```

### `set_attitude_threshold`

- **功能说明**: 设置翻滚与俯仰报警阈值
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetAttitudeThreshold`（CLI: `tuyarobot_msgs/srv/SetAttitudeThreshold`）
- **ROS 名**: `/robot/set_attitude_threshold`
- **请求字段**: `threshold_deg`（`float32`）。
- **参数范围**: 有限数值，`5.0~45.0` 度。
- **返回/观测**: `success` → `message` → `attitude_threshold_deg`（当前生效值，度）→ `response_time_ms`。成功后原子写入 `/home/tuya/tuya/config/safety_alarm.yaml`；配置目录不存在时失败且不创建父目录。
- **调用示例**:

```bash
ros2 service call /robot/set_attitude_threshold \
  tuyarobot_msgs/srv/SetAttitudeThreshold "{threshold_deg: 20.0}"
```

### 安全报警配置

`robot.launch.py` 支持 `safety_alarm_config_path`、`safety_alarm_default_language` 和 `safety_alarm_perception_enabled`（`config` / `true` / `false`）。默认配置路径为 `/home/tuya/tuya/config/safety_alarm.yaml`。感知监控仅在 `perception.enabled: true` 时启用；仅配置实际启动的路。

```yaml
safety_alarm:
  attitude_threshold_deg: 15.0
  language: zh_CN
  perception:
    enabled: true
    stale_timeout_s: 3.0
    startup_grace_s: 10.0
    monitors:
      - name: lidar
        type: laser_scan
        topic: /lidar/scan
      - name: microphone
        type: node
        node: /vtn_wakeup_node
```

支持 `image`、`laser_scan`、`point_cloud2` 和 `node`。传感器监控需先启动对应相机或雷达 launch；麦克风使用 `vtn_wakeup.launch.py` 后监控 `/vtn_wakeup_node`，不以触发型 `/voice/wakeup` 判断健康状态。

### `get_log_path`

- **功能说明**: 查询各模块现有日志路径
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetLogPath`（CLI: `tuyarobot_msgs/srv/GetLogPath`）
- **ROS 名**: `/system/get_log_path`
- **参数范围**: 空值按 `ALL` 处理，英文字段不区分大小写。

| 请求字段 | 可选值 | 说明 |
|---|---|---|
| `module` | `SYSTEM` / `HEAD` / `UPPER` / `CHASSIS` / `LIDAR` / `CAMERA_2D` / `CAMERA_3D` / `VOICE` / `ALL` | 按模块筛选日志族 |
| `category` | `INFO` / `HEX` / `WARN` / `ERROR` / `ALL` | 匹配日志族的 `categories`，不读取或过滤文件内容 |

- **查询语义**: `path` 返回当前或最近文件；没有匹配文件时 `exists=false`、`path` 为空、时间和大小为 `0`，但仍返回绝对路径 `pattern`。共享的底层协议日志和 ROS 运行日志会按相关模块分别返回相同实际路径。
- **失败语义**: 模块或类别非法时返回 `success=false`、空 `entries` 和英文允许值列表。
- **返回/观测**: `success` → `message` → `entries[]` → `response_time_ms`。

| 字段 | 说明 |
|---|---|
| `entries[].module` / `name` | 日志所属模块和英文日志族名称 |
| `entries[].categories` | 日志族包含的类别；类别筛选按该数组匹配 |
| `entries[].path` / `pattern` | 最近实际文件和日志族绝对路径模式 |
| `entries[].format` | `text` 或 `jsonl` |
| `entries[].exists` | 是否找到实际文件 |
| `entries[].updated_unix_ms` | 文件修改时间，Unix毫秒 |
| `entries[].size_bytes` | 文件大小，单位字节 |
- **调用示例**:

```bash
ros2 service call /system/get_log_path tuyarobot_msgs/srv/GetLogPath \
  '{module: "ALL", category: "ALL"}'

# 查询头部底层协议日志
ros2 service call /system/get_log_path tuyarobot_msgs/srv/GetLogPath \
  '{module: "HEAD", category: "HEX"}'
```

### `get_camera_2d_device`

- **功能说明**: 读取三路2D相机设备映射
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetCamera2DDevice`（CLI: `tuyarobot_msgs/srv/GetCamera2DDevice`）
- **ROS 名**: `/system/get_camera_2d_device`
- **返回语义**: 空请求；读取`perception_config.yaml`，不调用机器人SDK。
- **返回/观测**: `success` → `message` → `left_device` → `right_device` → `agv_device` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /system/get_camera_2d_device tuyarobot_msgs/srv/GetCamera2DDevice '{}'
```

### `set_camera_2d_device`

- **功能说明**: 设置单路或全部2D相机设备映射
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetCamera2DDevice`（CLI: `tuyarobot_msgs/srv/SetCamera2DDevice`）
- **ROS 名**: `/system/set_camera_2d_device`
- **请求字段**: `camera_role`、`device`、`left_device`、`right_device`、`agv_device`。
- **参数范围**: `camera_role`接受小写`left/right/agv/all`；空值按`all`处理。单路使用`device`，全量模式填写三路字段且路径不得重复。
- **返回语义**: 原子写入配置；重新开启2D相机模块后生效。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /system/set_camera_2d_device tuyarobot_msgs/srv/SetCamera2DDevice "{camera_role: left, device: '/dev/video2'}"

ros2 service call /system/set_camera_2d_device tuyarobot_msgs/srv/SetCamera2DDevice "{camera_role: all, left_device: '/dev/video2', right_device: '/dev/video0', agv_device: '/dev/video4'}"
```

### `get_camera_3d_serial`

- **功能说明**: 读取三路3D相机SN映射
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetCamera3DSerial`（CLI: `tuyarobot_msgs/srv/GetCamera3DSerial`）
- **ROS 名**: `/system/get_camera_3d_serial`
- **返回语义**: 空请求；读取`perception_config.yaml`，不调用机器人SDK。
- **返回/观测**: `success` → `message` → `agv_serial` → `abdomen_serial` → `head_serial` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /system/get_camera_3d_serial tuyarobot_msgs/srv/GetCamera3DSerial '{}'
```

### `set_camera_3d_serial`

- **功能说明**: 设置单路或全部3D相机SN映射
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetCamera3DSerial`（CLI: `tuyarobot_msgs/srv/SetCamera3DSerial`）
- **ROS 名**: `/system/set_camera_3d_serial`
- **请求字段**: `camera_role`、`serial`、`agv_serial`、`abdomen_serial`、`head_serial`。
- **参数范围**: `camera_role`接受小写`agv/abdomen/head/all`；空值按`all`处理。单路使用`serial`，全量模式填写三路字段且SN不得重复。
- **返回语义**: 原子写入配置；重新开启3D相机模块后生效。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /system/set_camera_3d_serial tuyarobot_msgs/srv/SetCamera3DSerial "{camera_role: head, serial: '<HEAD_SN>'}"

ros2 service call /system/set_camera_3d_serial tuyarobot_msgs/srv/SetCamera3DSerial "{camera_role: all, agv_serial: '<AGV_SN>', abdomen_serial: '<ABDOMEN_SN>', head_serial: '<HEAD_SN>'}"
```

### `get_vtn_wakeup_sn`

- **功能说明**: 读取语音唤醒授权SN
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/GetVtnWakeupSn`（CLI: `tuyarobot_msgs/srv/GetVtnWakeupSn`）
- **ROS 名**: `/system/get_vtn_wakeup_sn`
- **返回语义**: 空请求；读取`perception_config.yaml`，不调用机器人SDK。
- **返回/观测**: `success` → `message` → `sn` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /system/get_vtn_wakeup_sn tuyarobot_msgs/srv/GetVtnWakeupSn '{}'
```

### `set_vtn_wakeup_sn`

- **功能说明**: 设置或清除语音唤醒授权SN
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetVtnWakeupSn`（CLI: `tuyarobot_msgs/srv/SetVtnWakeupSn`）
- **ROS 名**: `/system/set_vtn_wakeup_sn`
- **请求字段**: `sn`。
- **参数范围**: 非空值长度不超过32，仅允许ASCII字母、数字及`-`、`:`、`_`；空字符串用于清除配置。
- **返回语义**: 原子写入配置；不热更新已运行节点，重新开启VTN模块后生效。SN为空时VTN启动失败。
- **返回/观测**: `success` → `message` → `response_time_ms`。
- **调用示例**:

```bash
ros2 service call /system/set_vtn_wakeup_sn tuyarobot_msgs/srv/SetVtnWakeupSn "{sn: '<授权SN>'}"
```


### `camera_2d_enable`

- **功能说明**: 启动或关闭三路2D相机模块
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetPerceptionModuleEnable`（CLI: `tuyarobot_msgs/srv/SetPerceptionModuleEnable`）
- **ROS 名**: `/system/camera_2d_enable`
- **请求字段**: `enable`（`true`启动，`false`关闭）。
- **返回语义**: 启动使用最新配置并等待三路节点及图像Topic就绪；只关闭本节点启动的进程。外部Launch返回`success=false, state=EXTERNAL`，`enabled`按完整就绪状态填写。
- **返回/观测**: `success` → `message` → `enabled` → `state` → `response_time_ms`；`enabled=true`仅表示全部预期节点和Publisher已就绪；`state`为`STOPPED/STARTING/RUNNING/STOPPING/FAILED/EXTERNAL`之一。
- **调用示例**:

```bash
ros2 service call /system/camera_2d_enable tuyarobot_msgs/srv/SetPerceptionModuleEnable '{enable: true}'
```

### `camera_3d_enable`

- **功能说明**: 启动或关闭三路3D相机模块
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetPerceptionModuleEnable`（CLI: `tuyarobot_msgs/srv/SetPerceptionModuleEnable`）
- **ROS 名**: `/system/camera_3d_enable`
- **请求字段**: `enable`（`true`启动，`false`关闭）。
- **返回语义**: 启动使用最新SN配置并等待三路彩色、深度Topic就绪；只关闭本节点启动的进程。外部Launch返回`success=false, state=EXTERNAL`，`enabled`按完整就绪状态填写。
- **返回/观测**: `success` → `message` → `enabled` → `state` → `response_time_ms`；`enabled=true`仅表示全部预期节点和Publisher已就绪；状态枚举同上。
- **调用示例**:

```bash
ros2 service call /system/camera_3d_enable tuyarobot_msgs/srv/SetPerceptionModuleEnable '{enable: true}'
```

### `lslidar_enable`

- **功能说明**: 启动或关闭雷达模块
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetPerceptionModuleEnable`（CLI: `tuyarobot_msgs/srv/SetPerceptionModuleEnable`）
- **ROS 名**: `/system/lslidar_enable`
- **请求字段**: `enable`（`true`启动，`false`关闭）。
- **返回语义**: 启动使用最新配置并等待节点及`/lidar/scan`发布者就绪；只关闭本节点启动的进程。外部Launch返回`success=false, state=EXTERNAL`，`enabled`按完整就绪状态填写。
- **返回/观测**: `success` → `message` → `enabled` → `state` → `response_time_ms`；`enabled=true`仅表示全部预期节点和Publisher已就绪；状态枚举同上。
- **调用示例**:

```bash
ros2 service call /system/lslidar_enable tuyarobot_msgs/srv/SetPerceptionModuleEnable '{enable: true}'
```

### `vtn_wakeup_enable`

- **功能说明**: 启动或关闭语音唤醒模块
- **类型**: Service
- **消息/服务类型**: `tuyarobot_msgs/SetPerceptionModuleEnable`（CLI: `tuyarobot_msgs/srv/SetPerceptionModuleEnable`）
- **ROS 名**: `/system/vtn_wakeup_enable`
- **请求字段**: `enable`（`true`启动，`false`关闭）。
- **返回语义**: 启动后等待节点及`/voice/wakeup`发布者就绪，不等待实际唤醒消息；只关闭本节点启动的进程。外部Launch返回`success=false, state=EXTERNAL`，`enabled`按完整就绪状态填写。
- **返回/观测**: `success` → `message` → `enabled` → `state` → `response_time_ms`；`enabled=true`仅表示全部预期节点和Publisher已就绪；状态枚举同上。
- **调用示例**:

```bash
ros2 service call /system/vtn_wakeup_enable tuyarobot_msgs/srv/SetPerceptionModuleEnable '{enable: true}'
```

<a id="log-retention-limit"></a>
## 六、日志轮转限制说明

文档列出的各日志分组独立限制为100 MiB，超过上限后清理最旧日志至90 MiB。最新日志、正在写入的日志和最近120秒内更新的日志受到保护。日志保留服务每30秒检查一次，真实清理记录同时写入systemd journal和以下分级事件日志：

```text
/home/tuya/tuya/logs/log_retention/log_retention_YYYYMMDD.log
```

整机关键状态边沿同时写入`/home/tuya/tuya/logs/system/Tuya_ROS2_ALL.log`和对应等级日志。`INFO`写入`Tuya_ROS2_INFO.log`，`WARN`写入`Tuya_ROS2_WARN.log`，`ERROR`与`FATAL`写入`Tuya_ROS2_ERROR.log`。每行保留`node`来源。`INFO`表示正常启动、成功操作或故障恢复；`WARN`表示业务拒绝、设备不支持、短时超时或版本低于要求；`ERROR`表示通信断联、安全故障、存储故障或内部异常；`FATAL`仅表示进程无法安全继续。持续相同的安全故障最多每30秒汇总一次，恢复时立即记录`INFO`。自动上报和事故JSONL仍保存原始数据，不逐帧写入分级事件日志。

### 部署指令

已安装旧版本时无需先卸载，重复执行安装脚本会原位更新清理程序、配置和systemd单元：

```bash
cd /home/tuya/tuya_robot_ros2
bash scripts/install_log_retention.sh
```

### 验收指令

```bash
systemctl is-enabled tuyarobot-log-retention.timer
systemctl is-active tuyarobot-log-retention.timer
sudo systemctl status tuyarobot-log-retention.timer --no-pager
systemctl list-timers --all | grep tuyarobot-log-retention

sudo python3 /usr/local/libexec/tuyarobot-log-retention \
  --config /etc/tuyarobot/log-retention.json \
  --check-config

sudo systemctl start tuyarobot-log-retention.service
sudo systemctl status tuyarobot-log-retention.service --no-pager

sudo ls -lh /home/tuya/tuya/logs/log_retention
```

正常情况下timer应为`enabled`和`active`，配置校验应显示`groups=12`，oneshot service执行后显示`status=0/SUCCESS`且回到`inactive (dead)`。没有目录超限时，当天事件日志可以为空。

### 警告查看指令

```bash
# 查看systemd journal中的最近清理记录
sudo journalctl -u tuyarobot-log-retention.service -n 100 --no-pager

# 持续查看systemd journal
sudo journalctl -fu tuyarobot-log-retention.service

# 查看当天日志轮转事件
sudo tail -n 100 \
  /home/tuya/tuya/logs/log_retention/log_retention_$(date +%Y%m%d).log

# 查看目录超限、删除及清理汇总记录
sudo grep -E 'event=(directory_over_limit|delete_attempt|delete_success|delete_failed|cleanup_summary|remains_over_limit)' \
  /home/tuya/tuya/logs/log_retention/log_retention_*.log
```

`--dry-run`仅在终端显示预计删除内容，不写入事件日志；历史版本已经完成的删除不会补写到新事件日志中。整机关键事件可在`/home/tuya/tuya/logs/system/Tuya_ROS2_ALL.log`中检索，也可直接查看对应等级日志。

<a id="troubleshooting"></a>
## 常见问题与故障排查

<a id="troubleshooting-connection"></a>
### 1. 头部、上半身或底盘连接异常

关闭 launch 后检查 TCP 端口和底盘串口占用：

```bash
nc -zvw 3 192.168.0.232 6500  # 上半身
nc -zvw 3 192.168.0.231 6501  # 头部
fuser -v /dev/tuya_chassis    # 底盘；无输出表示未被占用
```

启动后可查看连接诊断。上半身、底盘、头部由各自控制节点独立发布；在采样窗口内应分别看到 `tuya/upper_link`、`tuya/chassis_link`、`tuya/head_link`。未启动的模块不会发布占位错误状态：

```bash
timeout 5s ros2 topic echo /diagnostics
```

TCP 失败时检查供电、网段和控制程序；串口有输出时先关闭占用进程。

<a id="troubleshooting-vtn-authorization"></a>
### 2. 声源定位节点鉴权失败

声源定位节点无法启动，并输出以下错误时：

```text
no authorization, so feed audio failed! auth.result=3
```

该错误表示声源定位模块鉴权失败。启动时应传入正确的设备序列号，例如：

```bash
ros2 launch tuyarobot_sensors vtn_wakeup.launch.py sn:=mk_test
```

如需持久生效，使用`/system/set_vtn_wakeup_sn`写入运行时`perception_config.yaml`。Launch命令显式传入的`sn`只覆盖本次启动，不回写配置。

<a id="troubleshooting-wheel"></a>
### 3. 底盘无法使能轮毂

先设置抱闸，再使能轮毂：

```bash
ros2 service call /chassis/set_agv_wheel_brake tuyarobot_msgs/srv/SetInt "{data: 1}"
ros2 service call /chassis/set_agv_wheel_enabled tuyarobot_msgs/srv/SetAgvWheelEnabled "{state: 1}"
```

<a id="changelog"></a>
## 更新日志

| 版本号 | 更新时间 | 执行人 | 更新内容概述 |
|---|---|---|---|
| `V1.0.0` | 2026/8/24 | 徐子豪 | 总接口说明文档初版 |
| `V1.0.1` | 2026/8/25 | 徐子豪 | 关节角度规范、示例越界修复、接口类型修改等 |
| `V1.0.2` | 2026/8/25 | 徐子豪 | 新增一些接口修改 |
| `V1.0.3` | 2026/8/26 | 徐子豪 | 头部功能性接口添加，底盘上报新增内容 |
| `V1.0.4` | 2026/9/4 | 徐子豪 | 一批接口修改、日志轮转、上电维护等 |
| `V1.0.5` | 2026/9/11 | 徐子豪 | 新增感知部分继承配置/启停管理接口 |
