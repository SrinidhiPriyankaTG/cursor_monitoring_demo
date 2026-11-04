"""Live metrics for this host only. Samples stay in memory."""

import subprocess
import threading
import time
from pathlib import Path

PROC_STAT = "/proc/stat"
PROC_MEMINFO = "/proc/meminfo"
PROC_NET_DEV = "/proc/net/dev"
SS_ARGV = ["ss", "-H", "-l", "-n", "-t", "-u", "-p"]
COLLECTING = "Collecting…"
LISTEN_STATES = {"LISTEN", "UNCONN"}

_lock = threading.Lock()
_state = {"cpu": None, "net": None, "net_at": None}


def parse_cpu_times(stat_text):
    for line in stat_text.splitlines():
        if line.startswith("cpu "):
            numbers = [int(part) for part in line.split()[1:]]
            if len(numbers) < 4:
                break
            idle = numbers[3]
            if len(numbers) > 4:
                idle += numbers[4]
            total = sum(numbers)
            return total - idle, total
    raise OSError("cpu line missing")


def cpu_percent(previous, current):
    prev_busy, prev_total = previous
    busy, total = current
    delta_total = total - prev_total
    if delta_total <= 0:
        return 0.0
    delta_busy = busy - prev_busy
    return round(100.0 * delta_busy / delta_total, 1)


def cpu_from_stat(stat_text, previous):
    current = parse_cpu_times(stat_text)
    if previous is None:
        return COLLECTING, current
    return cpu_percent(previous, current), current


def parse_meminfo(meminfo_text):
    values = {}
    for line in meminfo_text.splitlines():
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        parts = rest.split()
        if not parts:
            continue
        values[key] = int(parts[0])
    if "MemTotal" not in values or "MemAvailable" not in values:
        raise OSError("meminfo missing fields")
    total = values["MemTotal"]
    available = values["MemAvailable"]
    used = total - available
    used_percent = 0.0 if total <= 0 else round(100.0 * used / total, 1)
    return {
        "total_kb": total,
        "available_kb": available,
        "used_kb": used,
        "used_percent": used_percent,
    }


def parse_netdev(dev_text):
    interfaces = {}
    for line in dev_text.splitlines():
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        name = name.strip()
        if not name or name == "lo":
            continue
        columns = rest.split()
        if len(columns) < 9:
            continue
        interfaces[name] = (int(columns[0]), int(columns[8]))
    return interfaces


def network_from_dev(dev_text, previous, elapsed):
    current = parse_netdev(dev_text)
    rows = []
    for name in sorted(current):
        received, transmitted = current[name]
        rx_per_sec = None
        tx_per_sec = None
        if previous and name in previous and elapsed and elapsed > 0:
            old_received, old_transmitted = previous[name]
            rx_per_sec = round((received - old_received) / elapsed, 1)
            tx_per_sec = round((transmitted - old_transmitted) / elapsed, 1)
        rows.append(
            {
                "name": name,
                "received_bytes": received,
                "transmitted_bytes": transmitted,
                "rx_per_sec": rx_per_sec,
                "tx_per_sec": tx_per_sec,
            }
        )
    return rows, current


def parse_ss(ss_text):
    rows = []
    for line in ss_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("netid"):
            continue
        parts = stripped.split()
        if len(parts) < 5:
            continue
        state = parts[1].upper()
        if state not in LISTEN_STATES:
            continue
        port = parts[4].rsplit(":", 1)[-1]
        process = ""
        marker = '(("'
        start = stripped.find(marker)
        if start != -1:
            start += len(marker)
            end = stripped.find('"', start)
            if end != -1:
                process = stripped[start:end]
        rows.append(
            {"protocol": parts[0], "port": port, "process": process}
        )
    return rows


def sample_cpu():
    stat_text = Path(PROC_STAT).read_text()
    with _lock:
        value, _state["cpu"] = cpu_from_stat(stat_text, _state["cpu"])
    if value == COLLECTING:
        return {"text": COLLECTING}
    return {"percent": value}


def sample_memory():
    return parse_meminfo(Path(PROC_MEMINFO).read_text())


def sample_network():
    dev_text = Path(PROC_NET_DEV).read_text()
    now = time.monotonic()
    with _lock:
        previous = _state["net"]
        elapsed = 0 if _state["net_at"] is None else now - _state["net_at"]
        rows, current = network_from_dev(dev_text, previous, elapsed)
        _state["net"] = current
        _state["net_at"] = now
    return rows


def sample_ports():
    completed = subprocess.run(
        SS_ARGV,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or "").strip() or "ss failed"
        raise OSError(detail)
    return parse_ss(completed.stdout)


def collect_all():
    payload = {}
    for key, reader in (
        ("cpu", sample_cpu),
        ("memory", sample_memory),
        ("network", sample_network),
        ("ports", sample_ports),
    ):
        try:
            payload[key] = reader()
        except Exception:
            payload[key] = {"error": "Unavailable"}
    return payload
