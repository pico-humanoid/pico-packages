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


## 通讯协议

以下字节格式适用于 CMP10A。正常读取连续上报的测量值无需发送指令；只有查询指定寄存器或修改设备配置时，才需要向串口写入数据。完整定义见《CMP10A 通讯协议》的“读格式”“写格式”。

### 读取

设备上报帧共 11 字节：`55 TYPE D0 D1 D2 D3 D4 D5 D6 D7 SUM`。`TYPE` 是帧类型，`SUM` 是前 10 个字节之和的低 8 位。下表的 `L/H` 分别表示低字节和高字节。

| 场景 | 主机发送 | 设备返回（帧头和字段） | SDK 处理 |
| :--- | :--- | :--- | :--- |
| 读取三轴加速度和温度 | 无 | `55 51 AxL AxH AyL AyH AzL AzH TL TH SUM` | `read_data()` 返回 `Acceleration`（`g`、`°C`） |
| 读取三轴角速度 | 无 | `55 52 WxL WxH WyL WyH WzL WzH VolL VolH SUM` | `read_data()` 返回 `AngularVelocity`（`°/s`）；SDK 不返回电压字段 |
| 读取滚转、俯仰、偏航 | 无 | `55 53 RollL RollH PitchL PitchH YawL YawH VL VH SUM` | `read_data()` 返回 `EulerAngles`（`°`）；SDK 不返回版本号字段 |
| 读取三轴磁场和温度 | 无 | `55 54 HxL HxH HyL HyH HzL HzH TL TH SUM` | `read_data()` 返回 `MagneticField`（原始计数、`°C`） |
| 主动查询寄存器，例如从 `AX`（`0x34`）开始读取 | 解锁后发送 `FF AA 27 34 00` | `55 5F AXL AXH AYL AYH AZL AZH GXL GXH SUM`；从指定地址起连续返回 4 个寄存器 | 用 `read_frame()` 检查帧类型并读取原始字节；`read_data()` 对 `0x5F` 返回 `UndecodedFrame` |

`read_data()` 每次只返回一帧，返回类型取决于下一帧是什么。主动查询时，连续上报帧可能先到；应跳过它们，等到 `0x5F` 应答。

### 写入

主机指令共 5 字节：`FF AA ADDR DATA_L DATA_H`。`ADDR` 为寄存器地址，设置值按低字节在前发送。表中的十六进制必须转换成原始 `bytes`，例如 `imu.write(bytes.fromhex("FF AA 03 07 00"))`；有对应 `encode_*()` 的指令可直接用其返回值。

| 场景 | 寄存器 | 发送字节（十六进制） | SDK 用法或说明 |
| :--- | :--- | :--- | :--- |
| 开始配置或查询前解锁 | `KEY`（`0x69`） | `FF AA 69 88 B5` | `imu.write(cmp10a.encode_unlock())` |
| 将设备串口改为 `115200` | `BAUD`（`0x04`） | `FF AA 04 06 00` | `imu.write(cmp10a.encode_set_baudrate(115200))`；要改回 `9600`，发送 `FF AA 04 02 00` |
| 将设备上报频率改为 `20 Hz` | `RRATE`（`0x03`） | `FF AA 03 07 00` | 用 `bytes.fromhex()`；`5 Hz`、`10 Hz` 分别把 `07` 换成 `05`、`06`。这与示例的 `--print-hz` 不同 |
| 只上报加速度、角速度、欧拉角 | `RSW`（`0x02`） | `FF AA 02 0E 00` | 用 `bytes.fromhex()`；`0E` 打开第 1、2、3 位。还要磁场则换成 `1E`（再打开第 4 位） |
| 保存配置，让断电后仍生效 | `SAVE`（`0x00`） | `FF AA 00 00 00` | `imu.write(cmp10a.encode_save())` |

改配置按 **解锁 → 写设置 → 保存** 操作，解锁后 10 秒内完成。改 `BAUD` 时，先用设备原来的波特率发送设置；发送保存指令时，主机必须使用设备当时实际生效的波特率。写入成功只代表主机提交了字节，应通过收帧验证设备是否已经应用设置。
