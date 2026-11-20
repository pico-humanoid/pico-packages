# `imu` 包

## API 说明

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

#### `Imu.write(data)`

- 作用：向已连接的串口写入原始字节。指令内容由对应型号的协议决定。
- 参数：`data` 为待发送的数据（`bytes`）；传入其他类型抛出 `TypeError`。
- 返回：`None`。未连接抛出 `RuntimeError`；写入失败或不完整抛出 `serial.SerialException`，写入超时（默认 1 秒）抛出 `serial.SerialTimeoutException`。
- 示例：`imu.write(cmp10a.encode_unlock())`。写入成功只表示主机提交了完整数据；是否执行需通过设备返回或实际行为确认。

#### `Imu.close()`

- 关闭串口并清空缓冲区
- 参数：无
- 返回： `None`。

### `cmp10a` 模块

- 该模块提供适配 [CMP10A 十轴传感器](https://www.yahboom.com/study/IMU) 通讯协议的接口工具
- 导入方式：
  ```python
  from pico_py.imu import cmp10a
  ```

#### `cmp10a.encode_unlock()`

- 作用：生成解锁设备配置寄存器的指令。修改设置之前先发送此指令。
- 参数：无。
- 返回：解锁指令（`bytes`）。

#### `cmp10a.encode_set_baudrate(baudrate)`

- 作用：生成修改 CMP10A 自身串口波特率的指令。
- 参数：`baudrate` 为目标波特率（`int`）：`4800`、`9600`、`19200`、`38400`、`57600`、`115200`、`230400`。
- 返回：设置指令（`bytes`）；不支持的值抛出 `ValueError`。
- 示例：`cmp10a.encode_set_baudrate(115200).hex(" ")` 得到 `ff aa 04 06 00`。

#### `cmp10a.encode_save()`

- 作用：生成保存设备当前配置的指令。
- 参数：无。
- 返回：保存指令（`bytes`）。
- 示例：将 CMP10A 从 `9600` 改为 `115200` 并保存。
  ```python
  from pico_py.imu import Imu, cmp10a

  port = "/dev/ttyUSB0"
  with Imu(port, 9600, protocol=cmp10a) as imu:
      imu.write(cmp10a.encode_unlock())
      imu.write(cmp10a.encode_set_baudrate(115200))

  with Imu(port, 115200, protocol=cmp10a) as imu:
      imu.write(cmp10a.encode_save())
  ```
  如果设备仍在 `9600`，保存时也用 `9600`。解锁后需在 10 秒内完成；详见[通讯协议：写入](#写入)。

> 以上函数只生成符合 CMP10A 的指令码，数据发送需由 `Imu.write()` 完成。

#### `cmp10a.extract_frame(buffer)` *

- 作用：从串口缓冲区中提取一帧有效数据，原地移除已消费的字节，保留半帧和后续数据。
- 参数：`buffer` 为待处理的字节缓冲区（`bytearray`）。
- 返回：一帧原始数据（`bytes`）；没有完整有效帧时返回 `None`。

#### `cmp10a.decode_frame(frame)` *

- 作用：校验并解码一帧 CMP10A 数据，无需连接串口。
- 参数：`frame` 为一帧完整的原始数据（`bytes`，11 字节）。
- 返回：加速度、角速度、欧拉角或磁场数据；有效但未实现解码的帧返回 `UndecodedFrame`，无效帧抛出 `ValueError`。
- 示例：
  ```python
  from pico_py.imu import cmp10a

  frame = bytes.fromhex("55 51 F9 FF 07 00 FE 07 09 0A BD")
  print(cmp10a.decode_frame(frame))
  ```

> 以上2个函数实现的是获取 IMU 数据的底层功能，用户一般不需使用，仅供开发者参考。

### 更多 IMU 型号开发中……


## 数据格式

### CMP10A IMU 数据结构定义

- 使用 `protocol=cmp10a` 时，`imu.read_data()` 每次返回**一帧**解码后的对象。
- 可用 `isinstance()` 判断类型，再访问对应字段，例如
  ```python
  data = imu.read_data()
  if isinstance(data, cmp10a.Acceleration):
    print(data.z_g)  # Z 轴加速度，单位是 g
  ```

| 返回类型 | 字段 | 含义和单位 |
| :--- | :--- | :--- |
| `cmp10a.Acceleration` | `x_g`、`y_g`、`z_g`（`float`） | X、Y、Z 轴加速度，单位 `g`；`1 g ≈ 9.81 m/s²` |
| `cmp10a.Acceleration` | `temperature_c`（`float`） | 温度，单位 `°C` |
| `cmp10a.AngularVelocity` | `x_dps`、`y_dps`、`z_dps`（`float`） | 绕 X、Y、Z 轴的角速度，单位 `°/s` |
| `cmp10a.EulerAngles` | `roll_deg`、`pitch_deg`、`yaw_deg`（`float`） | 滚转、俯仰、偏航角，单位 `°` |
| `cmp10a.MagneticField` | `x_lsb`、`y_lsb`、`z_lsb`（`int`） | X、Y、Z 轴磁场的原始计数，换算关系大致为 `6.67e-3 µT/LSB` |
| `cmp10a.MagneticField` | `temperature_c`（`float`） | 温度，单位 `°C` |

