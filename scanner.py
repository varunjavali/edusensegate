import subprocess
import re
import socket

SUBNET = "192.168.0."  # 🔴 CHANGE THIS TO YOUR WIFI SUBNET

def get_subnet():
    """Auto-detect subnet from local IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        parts = ip.split(".")
        return f"{parts[0]}.{parts[1]}.{parts[2]}."
    except:
        return SUBNET

def ping_sweep():
    """Forces ARP cache refresh by pinging entire subnet."""
    subnet = get_subnet()
    for i in range(2, 255):
        ip = subnet + str(i)
        subprocess.Popen(
            ["ping", "-n", "1", "-w", "100", ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

def is_alive(ip):
    """Check if a specific IP is reachable."""
    r = subprocess.run(
        ["ping", "-n", "2", "-w", "500", ip],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return r.returncode == 0

def get_arp_table():
    """Return dict of {mac: ip} from ARP table."""
    devices = {}
    try:
        out = subprocess.check_output("arp -a", shell=True).decode()
        pairs = re.findall(
            r"(\d+\.\d+\.\d+\.\d+)\s+([a-f0-9\-]{17})",
            out, re.I
        )
        for ip, mac in pairs:
            devices[mac.lower().replace("-", ":")] = ip
    except Exception as e:
        print(f"ARP error: {e}")
    return devices

def get_live_macs():
    """
    Returns set of MAC addresses currently alive on the network.
    Uses ping + ARP — this is the correct way to detect connected devices.
    """
    ping_sweep()
    arp = get_arp_table()

    live_macs = set()
    for mac, ip in arp.items():
        if is_alive(ip):
            live_macs.add(mac)

    return live_macs

# Alias so old code calling get_connected_ips() won't crash
def get_connected_ips():
    """Legacy alias — returns list of IPs (for backward compat)."""
    ping_sweep()
    arp = get_arp_table()
    return [ip for mac, ip in arp.items() if is_alive(ip)]