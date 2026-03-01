"""
Smoke tests for the bundled sensowash library (lib/).

Imports lib/ directly (bypassing custom_components/__init__.py)
so no homeassistant install is needed.
"""
import sys
import os

# Insert lib/ directly so we can import it without triggering HA's __init__
LIB = os.path.join(os.path.dirname(__file__), "..", "custom_components", "sensowash", "lib")
sys.path.insert(0, os.path.abspath(LIB))


def test_all_model_imports():
    """Every model/enum used by the integration must be importable from lib."""
    from models import (
        OnOff,
        WaterFlow,
        WaterTemperature,
        NozzlePosition,
        SeatTemperature,
        DryerTemperature,
        DryerSpeed,
        LidState,
        WaterHardness,
        ProximityState,
        LightState,
        DeodorizationDelay,
        TankDrainage,
        DescalingStatus,
        DescalingState,
        DeviceInfo,
        DeviceCapabilities,
        ErrorCode,
    )


def test_descaling_state_parse():
    """DescalingState.from_bytes must correctly decode the 5-byte wire format."""
    from models import DescalingState, DescalingStatus

    ds = DescalingState.from_bytes(bytes([1, 0, 30, 0, 90]))
    assert ds is not None
    assert ds.status == DescalingStatus.IN_PROGRESS
    assert ds.counter_a == 30
    assert ds.counter_b == 90

    idle = DescalingState.from_bytes(bytes([0, 0, 0, 0, 0]))
    assert idle.status == DescalingStatus.IDLE

    assert DescalingState.from_bytes(b"") is None
    assert DescalingState.from_bytes(bytes([99])) is None  # unknown status


def test_proximity_state_values():
    from models import ProximityState
    assert ProximityState.NEAR.value == 0
    assert ProximityState.MEDIUM.value == 1
    assert ProximityState.FAR.value == 2


def test_light_state_values():
    from models import LightState
    assert LightState.OFF.value == 0
    assert LightState.ON.value == 1
    assert LightState.AUTO.value == 2


def test_deodorization_delay_values():
    from models import DeodorizationDelay
    assert DeodorizationDelay.OFF.value == 0
    assert DeodorizationDelay.DELAY_1.value == 1
    assert DeodorizationDelay.DELAY_2.value == 2


def test_tank_drainage_defaults_en1717():
    from models import TankDrainage
    assert TankDrainage.EN_1717.value == 0


def test_device_capabilities_defaults():
    from models import DeviceCapabilities
    caps = DeviceCapabilities()
    assert caps.rear_wash is False
    assert caps.descaling is False
    assert caps.proximity_detection is False
    assert caps.ambient_light is False
