# Tuya ROS2 老化脚本

独立于 `scripts/aging` 的 ROS2 老化工具，运行于机器人本机（Humble + `tuyarobot_msgs`）。

## 特点

- 上半身 / 头部 / 底盘子系统并行老化
- 底盘内部串行：轮运动 → LED → 升降（避免抢串口）
- 运动下发优先使用 Service；默认刷新模式 `1`
- **不含 Jog / 增量阶段**
- 回零失败只写报告并继续，不计入连续失败阈值
- Excel + 日志报告（默认 `tuya_ros2_aging/reports/<run_id>/`）

## 依赖

```bash
source /opt/ros/humble/setup.bash
source <workspace>/install/setup.bash
pip install -r requirements.txt   # openpyxl
```

启动整机节点后再运行本脚本。

## 示例

```bash
cd tuya_ros2_aging
python3 run_aging.py --validate-config
python3 run_aging.py --run-upper-motion --cycle-limit 1
python3 run_aging.py --run-upper-motion --run-head-motion --run-chassis-motion --cycle-limit 1
python3 run_aging.py --monitor-only --duration-hours 0.1
```

软件限位与底盘运动必须现场人工监护。
