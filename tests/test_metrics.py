import metrics
from metrics import (
    COLLECTING,
    SS_ARGV,
    cpu_from_stat,
    network_from_dev,
    parse_meminfo,
    parse_ss,
)
from tests.helpers import login

CPU_FIRST = "cpu  0 0 0 100 0 0 0 0\n"
CPU_SECOND = "cpu  50 0 50 100 0 0 0 0\n"
MEMINFO = "MemTotal:        1000 kB\nMemFree:          100 kB\nMemAvailable:     250 kB\n"
DEV_FIRST = """
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo: 5000 1 0 0 0 0 0 0 5000 1 0 0 0 0 0 0
  eth0: 1000 1 0 0 0 0 0 0 4000 1 0 0 0 0 0 0
"""
DEV_SECOND = """
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo: 9000 1 0 0 0 0 0 0 9000 1 0 0 0 0 0 0
  eth0: 5000 1 0 0 0 0 0 0 8000 1 0 0 0 0 0 0
"""
SS_FIXTURE = """
tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:* users:(("sshd",pid=100,fd=3))
tcp ESTAB 0 0 10.0.0.1:50000 10.0.0.2:443 users:(("curl",pid=9,fd=3))
udp UNCONN 0 0 0.0.0.0:68 0.0.0.0:* users:(("dhclient",pid=4,fd=5))
"""


def test_cpu_percent_needs_two_samples():
    first, state = cpu_from_stat(CPU_FIRST, None)
    assert first == COLLECTING
    second, _state = cpu_from_stat(CPU_SECOND, state)
    assert second == 100.0


def test_memory_used_is_total_minus_available():
    parsed = parse_meminfo(MEMINFO)
    assert parsed["used_kb"] == parsed["total_kb"] - parsed["available_kb"]
    assert parsed["total_kb"] == 1000
    assert parsed["available_kb"] == 250
    assert parsed["used_percent"] == 75.0


def test_network_rate_skips_loopback():
    _rows, previous = network_from_dev(DEV_FIRST, None, 0)
    rows, _current = network_from_dev(DEV_SECOND, previous, 4)
    assert [row["name"] for row in rows] == ["eth0"]
    assert rows[0]["received_bytes"] == 5000
    assert rows[0]["transmitted_bytes"] == 8000
    assert rows[0]["rx_per_sec"] == 1000.0
    assert rows[0]["tx_per_sec"] == 1000.0


def test_ss_parser_drops_established_sockets():
    rows = parse_ss(SS_FIXTURE)
    assert rows == [
        {"protocol": "tcp", "port": "22", "process": "sshd"},
        {"protocol": "udp", "port": "68", "process": "dhclient"},
    ]
    assert SS_ARGV == ["ss", "-H", "-l", "-n", "-t", "-u", "-p"]


def test_metrics_requires_sign_in_and_keeps_keys_when_one_reader_fails(client, monkeypatch):
    anonymous = client.get("/metrics")
    assert anonymous.status_code == 302
    assert anonymous.headers["Location"].endswith("/login")

    def fail_cpu():
        raise OSError("cpu failed")

    monkeypatch.setattr(metrics, "sample_cpu", fail_cpu)
    login(client)
    response = client.get("/metrics?path=/tmp/ignored")
    assert response.status_code == 200
    payload = response.get_json()
    assert set(payload) == {"cpu", "memory", "network", "ports"}
    assert payload["cpu"] == {"error": "Unavailable"}
    assert "error" not in payload["memory"]
    assert isinstance(payload["network"], list)
    assert isinstance(payload["ports"], list)


def test_metric_samples_are_not_stored(client, app):
    login(client)
    assert client.get("/metrics").status_code == 200
    import sqlite3

    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        names = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        ]
    finally:
        conn.close()
    assert set(names) == {"users", "servers"}
