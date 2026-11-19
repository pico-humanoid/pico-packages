# PICO-Humanoid - Python SDK

## 概述

- `pico_py` 是 PICO-Humanoid 的 Python 软件开发工具包 (Software Development Kit, SDK)，可用于调用 PICO-Humanoid 的各项基本功能，涵盖传感器数据读取、电机指令收发等。

## 快速开始

### 1 安装SDK

- 先获取 PICO-Humanoid 完整软件包：
    ```bash
    git clone https://github.com/pico-humanoid/pico-packages
    ```
- 其中 `pipo_py` 即为 Python SDK：
    ```bash
    cd pico-packages/pipo_py
    ```

在 `pyproject.toml` 所在目录运行 `python -m pip install .`。要生成可复制到 Jetson 的 wheel，运行：

```bash
python -m pip wheel --no-deps --wheel-dir dist .
```

将 wheel 复制到 Jetson，再运行 `python3 -m pip install ./pico_py-0.1.0-py3-none-any.whl`。pip 会处理 `pyserial` 依赖。

## 在线读取

```python
from pico_py.imu import Imu

with Imu(port="/dev/ttyUSB0", baudrate=9600) as imu:
    print(imu.read_data(timeout=1.0))
```

示例程序：`python examples/read_imu.py /dev/ttyUSB0`，按 Ctrl+C 退出。Linux 也可指定 `/dev/serial/by-id/` 下的设备路径，Windows 可用 `COM3` 这样的端口名。

- `connect()` 打开串口，收到通过校验的 CMP10A 帧后返回 `True`，并保留首帧。串口打开失败时抛出 `serial.SerialException`。一秒内没有有效帧则抛出 `TimeoutError` 并释放串口。
- `read_frame(timeout=1.0)` 返回下一帧完整的 11 字节 `bytes`。跳过坏帧，保留尚未收齐的字节，超时抛出 `TimeoutError`。
- `read_data(timeout=1.0)` 读取并解码一帧。加速度用 `g`，角速度用 `°/s`，欧拉角用 `°`，磁场用原始计数 `LSB`，温度用 `°C`。有效但还没有专用解码的帧返回 `UndecodedFrame`，包含类型和原始负载。
- `close()` 可重复调用，`with` 退出时会自动关闭。一个串口应只由一个读者读取。

## 离线解码

```python
from pico_py.imu import cmp10a

frame = bytes.fromhex("55 51 F9 FF 07 00 FE 07 09 0A BD")
print(cmp10a.decode_frame(frame).z_g)  # 0.9990234375
```

`decode_frame()` 对长度、帧头、类型或校验不正确的帧抛出 `ValueError`。安装后可用 `python -m unittest discover -s tests -v` 执行测试。
