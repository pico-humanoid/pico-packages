# 快速开始

## SDK 安装

1. 获取 PICO-Humanoid 完整软件包：
    ```bash
    git clone https://github.com/pico-humanoid/pico-packages.git
    ```

2. 其中 `pipo_py` 即为 Python SDK：
    ```bash
    cd pico-packages/pico_py
    ```

3. 执行安装：
    ```bash
    python -m pip install --user -v .
    ```

4. 安装完成后测试：
    ```bash
    python3 -c "import pico_py, serial; print('OK')"
    ```
    输出 `OK` 即说明 `pico_py` 库已完成安装。

## API 导航

|包|主要功能|API 参考|
|:---:|:---:|:---:|
|`imu`|惯导传感器的连接、读取与指令发送|[imu-APIs](./APIs/imu-api.md#imu-模块)|
|`motor`|关节电机的通讯与控制|[motor-APIs](./APIs/imu-api.md#motor-包)|

## 示例程序

`examples/` 下提供了示例程序，供用户快速预览效果。

- 读取 IMU ：
    - 确保硬件设备已正确连接
    - 在 `pico-packages/pico_py` 目录下运行示例程序：
      ```bash
      python3 examples/read_imu.py /dev/ttyUSB0 --baudrate 9600 --print-hz 5
      ```

- 设置 IMU ：
    - 确保硬件设备已正确连接
    - 在 `pico-packages/pico_py` 目录下运行示例程序：
      ```bash
      python3 examples/write_imu_baudrate.py /dev/ttyUSB0 --baudrate 115200
      ```
