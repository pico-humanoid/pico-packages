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
|`imu`|惯导传感器的连接与读取|[imu-APIs](./api.md#imu-模块)|
|`motor`|关节电机的通讯与控制|[motor-APIs](./api.md#motor-包)|
