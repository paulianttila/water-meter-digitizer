"""Unit tests for zero-flow tracking and continuous leak detection subsystem."""

from datetime import datetime, timedelta

from configuration import ZeroFlowMonitor
from services.leak.models import LeakState, ValueType
from services.leak.tracker import ZeroFlowTracker


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
    local_tz = datetime.now().astimezone().tzinfo
    now = datetime(2026, 9, 7, 10, 0, 0, tzinfo=local_tz)
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
    local_tz = datetime.now().astimezone().tzinfo
    t0 = datetime(2026, 9, 7, 10, 0, 0, tzinfo=local_tz)

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
    local_tz = datetime.now().astimezone().tzinfo
    start_time = datetime(2026, 9, 7, 0, 0, 0, tzinfo=local_tz)

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
    local_tz = datetime.now().astimezone().tzinfo
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=local_tz)
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
    """Long gap (>2h) between readings should reset continuous timer and re-establish baseline."""
    config = ZeroFlowMonitor(
        enabled=True,
        continuous_flow_hours=2.0,
        min_leak_volume=0.010,
    )
    tracker = ZeroFlowTracker(config)
    local_tz = datetime.now().astimezone().tzinfo
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=local_tz)
    tracker.evaluate_reading(t0, 100.000)

    # 1 hour of flow
    t1 = t0 + timedelta(hours=1)
    tracker.evaluate_reading(t1, 100.050)

    # Camera/network outage for 3 hours (gap > 7200s)
    t2 = t1 + timedelta(hours=3)
    status = tracker.evaluate_reading(t2, 100.100)
    # Continuous flow timer reset and baseline re-established
    assert status.state == LeakState.OK
    assert status.current_flow_duration_seconds == 0.0
    assert status.current_flow_volume == 0.0


def test_tracker_manual_reset():
    config = ZeroFlowMonitor(
        enabled=True,
        continuous_flow_hours=1.0,
        min_leak_volume=0.005,
    )
    tracker = ZeroFlowTracker(config)
    local_tz = datetime.now().astimezone().tzinfo
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=local_tz)
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
    local_tz = datetime.now().astimezone().tzinfo
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=local_tz)
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
    local_tz = datetime.now().astimezone().tzinfo
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=local_tz)
    status = tracker.evaluate_reading(t0, 100.0)
    d = status.to_dict()
    assert d["enabled"] is True
    assert d["meter_name"] == "total"
    assert d["value_type"] == "cumulative"
    assert d["state"] == "OK"
    assert "last_zero_flow_time" in d
    assert "current_flow_duration_minutes" in d


def test_tracker_flow_rate_mode_normal_and_leak():
    """Test flow rate mode (direct m3/h readings) for continuous leak detection and resolution."""
    config = ZeroFlowMonitor(
        enabled=True,
        value_type=ValueType.FLOW_RATE,
        continuous_flow_hours=2.0,
        min_leak_volume=0.010,
        flow_threshold=0.001,
        resolve_debounce_count=2,
        max_history_events=5,
    )
    tracker = ZeroFlowTracker(config)
    local_tz = datetime.now().astimezone().tzinfo
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=local_tz)

    # Initial reading: Zero flow (0.0 m3/h)
    s0 = tracker.evaluate_reading(t0, 0.0)
    assert s0.state == LeakState.OK
    assert s0.value_type == ValueType.FLOW_RATE
    assert s0.current_flow_rate == 0.0

    # Flow starts at 0.010 m3/h
    # After 30 mins (0.5h): volume = ((0 + 0.010)/2) * 0.5 = 0.0025 m3
    t1 = t0 + timedelta(minutes=30)
    s1 = tracker.evaluate_reading(t1, 0.010)
    assert s1.state == LeakState.FLOW_ACTIVE
    assert s1.current_flow_rate == 0.010
    assert s1.current_flow_duration_seconds == 1800.0
    assert round(s1.current_flow_volume, 4) == 0.0025

    # Flow continues at 0.010 m3/h for next 1.5 hours (total 2 hours)
    # t2: 1h -> delta_v = 0.010 * 0.5 = 0.005 -> total = 0.0075 m3
    t2 = t1 + timedelta(minutes=30)
    tracker.evaluate_reading(t2, 0.010)

    # t3: 1.5h -> delta_v = 0.005 -> total = 0.0125 m3
    t3 = t2 + timedelta(minutes=30)
    tracker.evaluate_reading(t3, 0.010)

    # t4: 2.0h -> delta_v = 0.005 -> total = 0.0175 m3 >= min_leak_volume (0.010)
    t4 = t3 + timedelta(minutes=30)
    s4 = tracker.evaluate_reading(t4, 0.010)
    assert s4.state == LeakState.LEAK_DETECTED
    assert s4.active_event is not None
    assert s4.current_flow_duration_seconds == 7200.0
    assert round(s4.current_flow_volume, 4) == 0.0175

    # Debounced resolution:
    # 1st zero-flow reading (flow rate = 0.0 <= flow_threshold)
    t5 = t4 + timedelta(minutes=10)
    s5 = tracker.evaluate_reading(t5, 0.000)
    assert s5.state == LeakState.LEAK_DETECTED
    assert s5.consecutive_zero_readings == 1

    # 2nd zero-flow reading -> resolves leak
    t6 = t5 + timedelta(minutes=10)
    s6 = tracker.evaluate_reading(t6, 0.000)
    assert s6.state == LeakState.OK
    assert s6.active_event is None

    events = tracker.get_status().recent_events
    assert len(events) == 1
    assert events[0].resolved is True
    assert events[0].start_time == t0


def test_tracker_flow_rate_threshold_and_jitter():
    """Test flow rate jitter below flow_threshold is treated as zero flow."""
    config = ZeroFlowMonitor(
        enabled=True,
        value_type=ValueType.FLOW_RATE,
        continuous_flow_hours=1.0,
        min_leak_volume=0.005,
        flow_threshold=0.002,  # flow <= 0.002 is considered zero
        resolve_debounce_count=2,
    )
    tracker = ZeroFlowTracker(config)
    local_tz = datetime.now().astimezone().tzinfo
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=local_tz)

    # Establish baseline
    tracker.evaluate_reading(t0, 0.001)  # below threshold -> zero flow

    # Small jitter below threshold for 2 hours
    cur_t = t0
    for i in range(4):
        cur_t += timedelta(minutes=30)
        st = tracker.evaluate_reading(cur_t, 0.0015)
        assert st.state == LeakState.OK
        if i >= 1:  # after debounce count is satisfied
            assert st.current_flow_duration_seconds == 0.0


def test_tracker_flow_rate_volume_integration():
    """Verify trapezoidal integration accuracy with varying flow rates."""
    config = ZeroFlowMonitor(
        enabled=True,
        value_type=ValueType.FLOW_RATE,
        continuous_flow_hours=5.0,
        min_leak_volume=1.0,
        flow_threshold=0.0001,
    )
    tracker = ZeroFlowTracker(config)
    local_tz = datetime.now().astimezone().tzinfo
    t0 = datetime(2026, 9, 7, 12, 0, 0, tzinfo=local_tz)

    # t0: flow is 0.100 m3/h
    tracker.evaluate_reading(t0, 0.100)

    # t1 (1 hour later): flow increases linearly to 0.300 m3/h
    # Area = (0.100 + 0.300) / 2 * 1.0 = 0.200 m3
    t1 = t0 + timedelta(hours=1)
    s1 = tracker.evaluate_reading(t1, 0.300)
    assert round(s1.current_flow_volume, 4) == 0.2000

    # t2 (0.5 hour later): flow is 0.300 m3/h
    # Area = (0.300 + 0.300) / 2 * 0.5 = 0.150 m3 -> total = 0.350 m3
    t2 = t1 + timedelta(minutes=30)
    s2 = tracker.evaluate_reading(t2, 0.300)
    assert round(s2.current_flow_volume, 4) == 0.3500


def test_tracker_flow_rate_invalid_and_negative():
    """Negative flow rates and invalid quality readings should be handled safely."""
    config = ZeroFlowMonitor(
        enabled=True,
        value_type=ValueType.FLOW_RATE,
    )
    tracker = ZeroFlowTracker(config)
    local_tz = datetime.now().astimezone().tzinfo
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=local_tz)

    tracker.evaluate_reading(t0, 0.050)
    t1 = t0 + timedelta(minutes=5)
    st_act = tracker.evaluate_reading(t1, 0.050)
    assert st_act.state == LeakState.FLOW_ACTIVE

    # Negative flow rate ignored / treated as non-event
    st_neg = tracker.evaluate_reading(t1 + timedelta(minutes=5), -0.010)
    assert st_neg.state == LeakState.FLOW_ACTIVE

    # Bad quality reading
    st_qual = tracker.evaluate_reading(
        t1 + timedelta(minutes=10), 0.080, quality="uncertain"
    )
    assert st_qual.state == LeakState.FLOW_ACTIVE
    assert st_qual.current_flow_rate == 0.050  # preserved previous valid flow rate


def test_tracker_gap_reset_no_stale_delta():
    """Verify post-gap readings compute delta from post-gap baseline, not stale pre-gap value."""
    config = ZeroFlowMonitor(
        enabled=True,
        continuous_flow_hours=2.0,
        min_leak_volume=0.010,
    )
    tracker = ZeroFlowTracker(config)
    local_tz = datetime.now().astimezone().tzinfo
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=local_tz)
    tracker.evaluate_reading(t0, 100.000)

    # Small flow before outage
    t1 = t0 + timedelta(minutes=30)
    tracker.evaluate_reading(t1, 100.010)

    # Outage for 4 hours; during outage 10 m3 consumed
    t2 = t1 + timedelta(hours=4)
    s2 = tracker.evaluate_reading(t2, 110.000)
    assert s2.state == LeakState.OK
    assert s2.current_flow_volume == 0.0

    # Next reading 15 minutes later: small usage of 0.005 m3
    t3 = t2 + timedelta(minutes=15)
    s3 = tracker.evaluate_reading(t3, 110.005)
    assert s3.state == LeakState.FLOW_ACTIVE
    # Delta must be 0.005, NOT 10.005!
    assert round(s3.current_flow_volume, 3) == 0.005


def test_tracker_snapshot_immutability():
    """Verify ZeroFlowStatus snapshots are independent copies not mutated by tracker state."""
    config = ZeroFlowMonitor(
        enabled=True,
        continuous_flow_hours=1.0,
        min_leak_volume=0.005,
    )
    tracker = ZeroFlowTracker(config)
    local_tz = datetime.now().astimezone().tzinfo
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=local_tz)
    tracker.evaluate_reading(t0, 100.000)

    # Trigger leak alert
    t1 = t0 + timedelta(hours=1, minutes=30)
    tracker.evaluate_reading(t1, 100.020)

    snap1 = tracker.get_status()
    assert snap1.active_event is not None
    orig_duration = snap1.active_event.duration_seconds
    orig_volume = snap1.active_event.leaked_volume

    # Advance flow further
    t2 = t1 + timedelta(minutes=30)
    tracker.evaluate_reading(t2, 100.030)

    # Snapshot 1 should remain unaffected
    assert snap1.active_event.duration_seconds == orig_duration
    assert snap1.active_event.leaked_volume == orig_volume

    # Fresh snapshot reflects updated values
    snap2 = tracker.get_status()
    assert snap2.active_event is not None
    assert snap2.active_event.duration_seconds > orig_duration
    assert snap2.active_event.leaked_volume > orig_volume


def test_tracker_invalid_reading_watchdog():
    """Verify gap watchdog resets continuous sequence even when invalid readings arrive after long gap."""
    config = ZeroFlowMonitor(
        enabled=True,
        continuous_flow_hours=2.0,
        min_leak_volume=0.010,
    )
    tracker = ZeroFlowTracker(config)
    local_tz = datetime.now().astimezone().tzinfo
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=local_tz)
    tracker.evaluate_reading(t0, 100.000)

    # Flow for 1 hour
    t1 = t0 + timedelta(hours=1)
    s1 = tracker.evaluate_reading(t1, 100.050)
    assert s1.state == LeakState.FLOW_ACTIVE

    # Gap of 3 hours, then invalid reading (meter_value=None)
    t2 = t1 + timedelta(hours=3)
    s2 = tracker.evaluate_reading(t2, None)
    assert s2.state == LeakState.OK
    assert s2.current_flow_volume == 0.0


def test_tracker_update_config():
    """Verify dynamic config update without losing tracking state."""
    cfg1 = ZeroFlowMonitor(
        enabled=True,
        continuous_flow_hours=2.0,
        min_leak_volume=0.010,
    )
    tracker = ZeroFlowTracker(cfg1)
    local_tz = datetime.now().astimezone().tzinfo
    t0 = datetime(2026, 9, 7, 0, 0, 0, tzinfo=local_tz)
    tracker.evaluate_reading(t0, 100.000)

    t1 = t0 + timedelta(minutes=30)
    s1 = tracker.evaluate_reading(t1, 100.020)
    assert s1.state == LeakState.FLOW_ACTIVE

    cfg2 = ZeroFlowMonitor(
        enabled=True,
        continuous_flow_hours=0.5,
        min_leak_volume=0.010,
    )
    tracker.update_config(cfg2)
    assert tracker.config.continuous_flow_hours == 0.5
