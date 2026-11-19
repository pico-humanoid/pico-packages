from unittest import TestCase
from unittest.mock import patch

from pico_py.imu import Imu, cmp10a


ACC = bytes.fromhex("55 51 F9 FF 07 00 FE 07 09 0A BD")
GYRO = bytes.fromhex("55 52 00 00 00 00 00 00 01 00 A8")
ANGLES = bytes.fromhex("55 53 28 00 1E 00 66 1A 08 47 BD")
MAG = bytes.fromhex("55 54 EC 0F F3 12 72 EA 00 00 05")


class ProtocolTests(TestCase):
    def test_decode_captured_measurements(self):
        acc = cmp10a.decode_frame(ACC)
        self.assertIsInstance(acc, cmp10a.Acceleration)
        self.assertAlmostEqual(acc.x_g, -0.00341796875)
        self.assertAlmostEqual(acc.z_g, 0.9990234375)
        self.assertAlmostEqual(acc.temperature_c, 25.69)
        self.assertEqual(cmp10a.decode_frame(GYRO), cmp10a.AngularVelocity(0, 0, 0))
        angles = cmp10a.decode_frame(ANGLES)
        self.assertAlmostEqual(angles.yaw_deg, 37.122802734375)
        self.assertEqual(cmp10a.decode_frame(MAG), cmp10a.MagneticField(4076, 4851, -5518, 0))

    def test_invalid_and_unimplemented_frames(self):
        for invalid in (ACC[:-1], b"\x00" + ACC[1:], ACC[:-1] + b"\x00"):
            with self.subTest(frame=invalid), self.assertRaises(ValueError):
                cmp10a.decode_frame(invalid)
        data = b"\x55\x59" + bytes(8)
        self.assertEqual(
            cmp10a.decode_frame(data + bytes([sum(data) & 0xFF])),
            cmp10a.UndecodedFrame(0x59, bytes(8)),
        )


class Cmp10aSerialTests(TestCase):
    def test_reads_frames_after_noise_and_bad_checksum(self):
        wire = bytearray(b"\xAB\x55\x01" + ACC[:-1] + b"\x00" + ACC + GYRO)
        with patch("pico_py.imu.device.Serial") as create_serial:
            serial = create_serial.return_value
            serial.in_waiting = 0

            def read(size):
                chunk = bytes(wire[:size])
                del wire[:size]
                return chunk

            serial.read.side_effect = read
            imu = Imu("test-port", 9600, protocol=cmp10a)
            with imu:
                self.assertTrue(imu.connect())
                self.assertEqual(imu.read_frame(), ACC)
                self.assertEqual(imu.read_data(), cmp10a.AngularVelocity(0, 0, 0))
            imu.close()
            create_serial.assert_called_once()
            serial.close.assert_called_once()
            with self.assertRaisesRegex(RuntimeError, "connect"):
                imu.read_frame()
