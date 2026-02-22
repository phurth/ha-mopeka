"""Mopeka advertisement parser."""

from __future__ import annotations

from .const import (
    MANUFACTURER_ID,
    MediumType,
    SYNC_BYTE_TO_MODEL,
    apply_temperature_compensation,
    calculate_tank_percentage,
)
from .model import MopekaSensorData

MIN_MANUFACTURER_PAYLOAD = 10


def parse_mopeka_data(
    address: str,
    manufacturer_data: bytes,
    medium_type: MediumType,
    tank_type: str,
) -> MopekaSensorData | None:
    """Parse Mopeka manufacturer payload into structured data."""
    if len(manufacturer_data) < MIN_MANUFACTURER_PAYLOAD:
        return None

    sync_byte = manufacturer_data[0]
    if sync_byte not in SYNC_BYTE_TO_MODEL:
        return None

    battery_raw = manufacturer_data[1]
    temp_raw = manufacturer_data[2] & 0x7F
    temp_c = temp_raw - 40

    low = manufacturer_data[3]
    high = manufacturer_data[4]
    distance_raw_mm = ((high << 8) | low) & 0x3FFF
    quality_raw = (high >> 6) & 0x03
    quality_percent = round((quality_raw / 3.0) * 100.0)

    accel_x = manufacturer_data[8]
    accel_y = manufacturer_data[9]

    battery_voltage = battery_raw / 32.0
    battery_percent = round(((battery_voltage - 2.2) / 0.65) * 100.0)
    battery_percent = max(0, min(100, battery_percent))

    compensated_mm = apply_temperature_compensation(distance_raw_mm, temp_raw, medium_type)
    tank_percent = calculate_tank_percentage(tank_type, float(compensated_mm))

    return MopekaSensorData(
        mac_address=address,
        model_id=sync_byte,
        model_name=SYNC_BYTE_TO_MODEL[sync_byte],
        battery_percent=battery_percent,
        distance_raw_mm=distance_raw_mm,
        compensated_distance_mm=compensated_mm,
        temperature_c=temp_c,
        quality_percent=quality_percent,
        quality_raw=quality_raw,
        accelerometer_x=accel_x,
        accelerometer_y=accel_y,
        tank_level_percent=tank_percent,
        medium_type=medium_type,
        tank_type=tank_type,
    )


def extract_mopeka_manufacturer_payload(manufacturer_data_map: dict[int, bytes]) -> bytes | None:
    """Extract Mopeka payload from HA bluetooth manufacturer_data map."""
    return manufacturer_data_map.get(MANUFACTURER_ID)
