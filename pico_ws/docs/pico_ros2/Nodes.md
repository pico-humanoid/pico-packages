# 节点构成

## IMU 节点

### 启动 IMU 驱动

```bash
ros2 run pico_ros2 imu_driver
```
也可以附带相应参数：
```bash
ros2 run pico_ros2 imu_driver --ros-args \
--params-file "$(ros2 pkg prefix --share pico_ros2)/config/imu.yaml"
```
其中 `$(ros2 pkg prefix --share pico_ros2)/config/imu.yaml` 可根据需要进行编辑调整。

### 查看 Topic

```bash
ros2 topic list
```
能看到的话题及其数据如下：

| 话题 | 消息类型 | 数据内容 | 启用条件 |
| --- | --- | --- | --- |
| `/imu/data_raw` | `sensor_msgs/msg/Imu` | 三轴加速度（m/s²）、角速度（rad/s），姿态字段标记为不可用 | 默认发布 |
| `/imu/data` | `sensor_msgs/msg/Imu` | 三轴加速度、角速度、姿态四元数 | 默认发布 |
| `/imu/mag` | `sensor_msgs/msg/MagneticField` | 三轴磁场（T） | `publish_mag: true`（默认） |
| `/imu/temperature` | `sensor_msgs/msg/Temperature` | IMU 温度（°C） | `publish_temperature: true`（默认） |

上述话题均可在其他程序中被订阅。

### 查看并使用 Service

```bash
ros2 service list -t
```
可用的服务有 `/imu/calibrate_accel` （类型为 `std_srvs/srv/Trigger`），作用是**执行自动校准**，可用如下命令调用：
```bash
ros2 service call /imu/calibrate_accel std_srvs/srv/Trigger "{}"
```

## Motor 节点