# API 参考

## `imu` 包

### `Imu` 模块

- 该模块提供了 IMU 设备的通用接口，不依赖具体的 IMU 设备型号
- 导入方式：
  ```python
  from pico_py.imu import Imu
  ```

#### `Imu(port, baudrate, protocol=...)`

- `port`：串口设备名，例如 `/dev/ttyUSB0`。
- `baudrate`：设备的串口波特率，例如 `9600`。
- `protocol`：与设备型号对应的协议，须用关键字传入，例如 `protocol=cmp10a`。

#### `Imu.connect()`

- 作用：打开串口并启动连接
- 参数：无
- 返回：串口打开后返回 `True`；打开失败时抛出异常。
- 示例：
  ```python
  from pico_py.imu import Imu, cmp10a

  imu = Imu("/dev/ttyUSB0", baudrate=9600, protocol=cmp10a)
  imu.connect()
  try:
      print(imu.read_data())
  finally:
      imu.close()
  ```

#### `Imu.read_frame(timeout=1.0)`

- 作用：读取一帧原始数据（十六进制）
- 参数：`timeout` ：等待有效帧的超时秒数，默认 `1.0`。
- 返回：一帧通过协议校验的原始数据（`bytes`）；超时抛出 `TimeoutError`。

#### `Imu.read_data(timeout=1.0)`

- 作用：读取一帧传感器数据
- 参数：`timeout` 同 `read_frame()`。
- 返回：一帧解码后的数据，类型由协议决定；超时抛出 `TimeoutError`。

#### `Imu.close()`

- 关闭串口并清空缓冲区
- 参数：无
- 返回： `None`。

### * `cmp10a` 模块

> 该部分 API 供协议开发者参考，仅使用 IMU 的用户可以略过

- 该模块提供适配 [CMP10A 十轴传感器](https://www.yahboom.com/study/IMU) 通讯协议的接口工具
- 导入方式：
  ```python
  from pico_py.imu import cmp10a
  ```

#### `cmp10a.extract_frame(buffer)`

- 作用：从串口缓冲区中提取一帧有效数据，原地移除已消费的字节，保留半帧和后续数据。
- 参数：`buffer` 为待处理的字节缓冲区（`bytearray`）。
- 返回：一帧原始数据（`bytes`）；没有完整有效帧时返回 `None`。

#### `cmp10a.decode_frame(frame)`

- 作用：校验并解码一帧 CMP10A 数据，无需连接串口。
- 参数：`frame` 为一帧完整的原始数据（`bytes`，11 字节）。
- 返回：加速度、角速度、欧拉角或磁场数据；有效但未实现解码的帧返回 `UndecodedFrame`，无效帧抛出 `ValueError`。
- 示例：
  ```python
  from pico_py.imu import cmp10a

  frame = bytes.fromhex("55 51 F9 FF 07 00 FE 07 09 0A BD")
  print(cmp10a.decode_frame(frame))
  ```

### 更多 IMU 型号开发中……

## `motor` 包

*Coming Soon...*