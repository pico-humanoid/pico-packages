# PICO-Humanoid - ROS2

`pico_ros2` 是 PICO-Humanoid 的 ROS2 包。

## 获取与构建

- 可通过 GitHub 获取 PICO-Humanoid 完整软件包：
    ```bash
    git clone https://github.com/pico-humanoid/pico-packages.git
    ```
  其中的 `pico_ros2/` 目录即为 ROS2 程序包。

- 以 ROS2 工作空间 `pico_ws` 为例，将 `pico_ros2` 置于 `pico_ws/src/` 下，并使用 `colcon` 构建（在工作空间目录下，且 ROS2 环境 `setup.bash` 已通过 `source` 命令配置）：
  ```bash
  colcon build --packages-select pico_ros2
  ```

## 启动与使用

- **启动节点前，应注意：**
    - 确保 ROS2 环境已正确配置，例如：
      ```bash
      source /opt/ros/humble/setup.bash
      ```
      该操作可能在安装 ROS2 时就已写入 `~/.bashrc`，如不确定可使用以下命令检查：
      ```bash
      echo $ROS_DISTRO
      ```
      环境正常则应显示当前 ROS2 版本名称，如 `humble`。
      如果是其他版本的 ROS2，则路径应作相应更改，例如 `/opt/ros/jazzy/setup.bash`
    - 确保工作空间已启用，例如：
      ```bash
      source ~/pico_ws/install/local_setup.bash
      ```
      也可选择将上述指令写入 `.bashrc`。