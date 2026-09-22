"""
HORIZON Hardware-in-the-Loop (HIL) Binary Telemetry Protocol Adapter
=====================================================================
Encodes rate commands into binary UDP telemetry packets and decodes incoming gimbal
encoder feedback with CRC32 checksum verification.

Packet Binary Structure (22 Bytes):
  Header (1B): 0xAA
  MsgID  (1B): 0x01 (Command) / 0x02 (Telemetry Feedback)
  Pan    (4B float32): Pan rate [deg/s] / angle [deg]
  Tilt   (4B float32): Tilt rate [deg/s] / angle [deg]
  PanRate(4B float32): Pan rate feedback [deg/s]
  TiltRate(4B float32): Tilt rate feedback [deg/s]
  CRC32  (4B uint32): Checksum
"""

from __future__ import annotations

import struct
from typing import Optional, Tuple
import zlib


HEADER_BYTE = 0xAA
MSG_ID_CMD = 0x01
MSG_ID_TELEMETRY = 0x02


class UDPTelemetryAdapter:
    """Binary UDP / Serial telemetry protocol encoder and decoder for HIL testing."""

    @staticmethod
    def pack_rate_command(pan_rate_deg_s: float, tilt_rate_deg_s: float, seq: int = 0) -> bytes:
        """Pack pan/tilt rate commands into a 24-byte binary telemetry packet with CRC32.

        Returns:
            24-byte binary bytes object.
        """
        payload = struct.pack("!BBffff", HEADER_BYTE, MSG_ID_CMD, float(pan_rate_deg_s), float(tilt_rate_deg_s), 0.0, 0.0)
        crc = zlib.crc32(payload) & 0xFFFFFFFF
        return payload + struct.pack("!I", crc)

    @staticmethod
    def unpack_telemetry_feedback(packet: bytes) -> Optional[Tuple[float, float, float, float]]:
        """Unpack 22-byte telemetry feedback packet and verify CRC32.

        Returns:
            Tuple[pan_deg, tilt_deg, pan_rate_deg_s, tilt_rate_deg_s] or None if corrupted.
        """
        if len(packet) != 22:
            return None

        payload = packet[:18]
        expected_crc = struct.unpack("!I", packet[18:22])[0]
        actual_crc = zlib.crc32(payload) & 0xFFFFFFFF

        if actual_crc != expected_crc:
            return None  # Checksum mismatch / corrupted packet

        hdr, msg_id, pan, tilt, pan_rate, tilt_rate = struct.unpack("!BBffff", payload)
        if hdr != HEADER_BYTE:
            return None

        return (float(pan), float(tilt), float(pan_rate), float(tilt_rate))
