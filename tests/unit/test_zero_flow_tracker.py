"""Unit tests for zero-flow tracking and continuous leak detection subsystem."""

from datetime import datetime, timedelta, timezone

from configuration import ZeroFlowMonitor
from leak.models import LeakState
from leak.tracker import ZeroFlowTracker


def test_tracker_initial_state():
    config = ZeroFlowMonitor(
        enabled=True,
        continuous_flow_hours=2.0,
        min_leak_volume=0.010,
        resolve_debounce_count=2,
    )
    tracker = ZeroFlowTracker(config)
    status = tracker.get_status()
    assert status.state == LeakState.OK
    assert status.current_flow_duration_seconds == 0.0
    assert status.current_flow_volume == 0.0
    assert len(status.recent_events) == 0


def test_tracker_disabled():
    config = ZeroFlowMonitor(enabled=False)
    tracker = ZeroFlowTracker(config)
    now = datetime(2026, 9, 7, 10, 0, 0, tzinfo=timezone.utc)
    status = tracker.evaluate_reading(now, 100.0)
    assert status.state == LeakState.OK
    status2 = tracker.evaluate_reading(now + timedelta(hours=3), 105.0)
    assert status2.state == LeakState.OK


def test_tracker_normal_intermittent_usage():
    config = ZeroFlowMonitor(
        enabled=True,
        continuous_flow_hours=2.0,
        min_leak_volume=0.010,
        resolve_debounce_count=2,
    )
    tracker = ZeroFlowTracker(config)
    t0 = datetime(2026, 9, 7, 10, 0, 0, tzinfo=timezone.utc)

    # Initial baseline reading
    s0 = tracker.evaluate_reading(t0, 100.000)
    assert s0.state == LeakState.OK

    # Flow for 30 minutes
    t1 = t0 + timedelta(minutes=30)
    s1 = tracker.evaluate_reading(t1, 100.050)
    assert s1.state == LeakState.FLOW_ACTIVE
    assert s1.current_flow_duration_seconds == 1800.0
    assert round(s1.current_flow_volume, 3) == 0.050

    # Flow stops (reading unchanged)
    t2 = t1 + timedelta(minutes=15)
    s2 = tracker.evaluate_reading(t2, 100.050)
    assert s2.consecutive_zero_readings == 1

    t3 = t2 + timedelta(minutes=15)
    s3 = tracker.evaluate_reading(t3, 100.050)
    assert s3.state == LeakState.OK
    assert s3.current_flow_volume == 0.0
    assert s3.last_zero_flow_time == t3


def test_tracker_leak_detection_and_debounced_resolution():
    config = ZeroFlowMonitor(
        enabled=True,
        continuous_flow_hours=2.0,
        min_leak_volume=0.010,
        resolve_debounce_count=2,
        max_history_events=5,
    )
    tracker = ZeroFlowTracker(config)
    start_time = datetime(2026, 9, 7, 0, 0, 0, tzinfo=timezone.utc)

    # Establish baseline
    tracker.evaluate_reading(start_time, 100.000)

    # Continuous small flow every 30 minutes for 2.5 hours (total +0.025 m3)
    current_time = start_time
    current_val = 100.000
    for i in range(1, 5):
        current_time += timedelta(minutes=30)
        current_val += 0.005
        status = tracker.evaluate_reading(current_time, current_val)
        # Until 2.0 hours reached, state is FLOW_ACTIVE
        if i < 4:
            assert status.state == LeakState.FLOW_ACTIVE
            assert status.active_event is None
        else:
            # At 2.0 hours and 0.020 m3, alert is triggered
            assert status.state == LeakState.LEAK_DETECTED
            assert status.active_event is not None
            assert status.current_flow_duration_seconds == 7200.0
            assert round(status.current_flow_volume, 3) == 0.020

    # Flow continues another 30 mins
    current_time += timedelta(minutes=30)
    current_val += 0.005
    status = tracker.evaluate_reading(current_time, current_val)
    assert status.state == LeakState.LEAK_DETECTED
    assert status.current_flow_duration_seconds == 9000.0
    assert round(status.current_flow_volume, 3) == 0.025

    # First zero-flow poll: Debounce not met yet (resolve_debounce_count = 2)
    current_time += timedelta(minutes=10)
    status_zero1 = tracker.evaluate_reading(current_time, current_val)
    assert status_zero1.state == LeakState.LEAK_DETECTED
    assert status_zero1.consecutive_zero_readings == 1
    assert len(status_zero1.recent_events) == 0

    # Second zero-flow poll: Resolves leak alert, archives event
    current_time += timedelta(minutes=10)
    status_zero2 = tracker.evaluate_reading(current_time, current_val)
    assert status_zero2.state == LeakState.OK
    assert status_zero2.active_event is None

    history = tracker.get_status().recent_events
    assert len(history) == 1
    event = history[0]
    assert event.start_time == start_time
    assert round(event.leaked_volume, 3) == 0.025
    assert event.duration_seconds >= 9000.0
    assert event.resolved is True


def test_tracker_jitter_filtering():
    """Optical needle / drum jitter below min_leak_volume should not trigger alert."""
    config = ZeroFlowMonitor(
        enabled=True,
        continuous_flow_hours=2.0,
        min_leak_volume=0.010,
        flow_threshold=0.00001,
        resolve_debounce_count=2,
    )
    tracker = ZeroFlowTracker(config)
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=timezone.utc)
    tracker.evaluate_reading(t0, 100.0000)

    # Jitter of 0.0001 every 30 mins for 3 hours (total 0.0006 < 0.010)
    cur_t = t0
    cur_v = 100.0000
    for _ in range(6):
        cur_t += timedelta(minutes=30)
        cur_v += 0.0001
        status = tracker.evaluate_reading(cur_t, cur_v)
        # Even after 3 hours, no leak alert because volume is below 0.010 m3
        assert status.state == LeakState.FLOW_ACTIVE
        assert status.active_event is None


def test_tracker_outage_gap_reset():
    """Long gap (>2h) between readings should reset continuous timer."""
    config = ZeroFlowMonitor(
        enabled=True,
        continuous_flow_hours=2.0,
        min_leak_volume=0.010,
    )
    tracker = ZeroFlowTracker(config)
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=timezone.utc)
    tracker.evaluate_reading(t0, 100.000)

    # 1 hour of flow
    t1 = t0 + timedelta(hours=1)
    tracker.evaluate_reading(t1, 100.050)

    # Camera/network outage for 3 hours (gap > 7200s)
    t2 = t1 + timedelta(hours=3)
    status = tracker.evaluate_reading(t2, 100.100)
    # Continuous flow timer reset
    assert status.state == LeakState.FLOW_ACTIVE
    assert status.current_flow_duration_seconds == 0.0


def test_tracker_manual_reset():
    config = ZeroFlowMonitor(
        enabled=True,
        continuous_flow_hours=1.0,
        min_leak_volume=0.005,
    )
    tracker = ZeroFlowTracker(config)
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=timezone.utc)
    tracker.evaluate_reading(t0, 100.000)

    t1 = t0 + timedelta(hours=1, minutes=30)
    tracker.evaluate_reading(t1, 100.020)
    assert tracker.get_status().state == LeakState.LEAK_DETECTED

    tracker.reset()
    assert tracker.get_status().state == LeakState.OK
    assert len(tracker.get_status().recent_events) == 1


def test_tracker_invalid_and_negative_readings():
    config = ZeroFlowMonitor(enabled=True)
    tracker = ZeroFlowTracker(config)
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=timezone.utc)
    tracker.evaluate_reading(t0, 100.0)

    # Negative delta
    status_neg = tracker.evaluate_reading(t0 + timedelta(minutes=10), 99.0)
    assert status_neg.state == LeakState.OK

    # Low confidence read ignored
    status_low_conf = tracker.evaluate_reading(
        t0 + timedelta(minutes=20), 101.0, confidence=20.0
    )
    assert status_low_conf.state == LeakState.OK

    # Uncertain quality read ignored
    status_bad_qual = tracker.evaluate_reading(
        t0 + timedelta(minutes=30), 102.0, quality="uncertain"
    )
    assert status_bad_qual.state == LeakState.OK

    # None reading ignored
    status_none = tracker.evaluate_reading(t0 + timedelta(minutes=40), None)
    assert status_none.state == LeakState.OK


def test_zero_flow_status_dict():
    config = ZeroFlowMonitor(enabled=True)
    tracker = ZeroFlowTracker(config)
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=timezone.utc)
    status = tracker.evaluate_reading(t0, 100.0)
    d = status.to_dict()
    assert d["enabled"] is True
    assert d["meter_name"] == "total"
    assert d["state"] == "OK"
    assert "last_zero_flow_time" in d
    assert "current_flow_duration_minutes" in d
