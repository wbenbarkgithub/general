#!/usr/bin/env python3
"""
TC 07-04 (Distribution Side): Link Failure From Distribution Switch to L2 Border
Shutdown Te4/0/20 on L2-DIST-1 (distribution side), Te4/0/21 (L2H-1 to L2-DIST-2) provides redundancy.

This is the REVERSE of run_tc_07-04.py — same trunk, shutdown from the DIST switch end.

Topology:
  L2-DIST-1 --Te4/0/20 (L2 trunk)--> FS2_L2H-1 Te4/0/20  <-- DIST-1 SIDE SHUT
  L2-DIST-2 --Te1/0/20 (L2 trunk)--> FS2_L2H-1 Te4/0/21  <-- REDUNDANT (stays UP)

  VLANs on both trunks: 101 (BMS1, 10.5.28.0/22) + 1301 (EUT, 10.5.20.0/22)
  STP Root: FS2_L2H-1 for both VLANs

  Expected: STP reconverges traffic to Te4/0/21 via L2-DIST-2.
  Fabric side (Po40/Po41, OSPF, BFD, LISP to BCs) MUST remain operational.

Usage: python3 run_tc_07-04_dist_side.py [--iter 1|2|3]
"""

import os
import sys
import datetime
import time
import argparse
from netmiko import ConnectHandler

# =============================================================================
# CONFIGURATION
# =============================================================================

TC_DIR = os.path.dirname(os.path.abspath(__file__))

L2H1_TACACS = {
    'device_type': 'cisco_ios',
    'host': '172.31.0.194',
    'username': 'admin1',
    'password': 'CXlabs.123',
    'timeout': 30,
    'name': 'FS2_L2H-1',
}

L2H1_LOCAL = {
    'device_type': 'cisco_ios',
    'host': '172.31.0.194',
    'username': 'admin',
    'password': 'CXlabs.123',
    'secret': 'CXlabs.123',
    'timeout': 30,
    'name': 'FS2_L2H-1',
}

DIST1 = {
    'device_type': 'cisco_ios',
    'host': '172.31.0.193',
    'username': 'admin',
    'password': 'CXlabs.123',
    'timeout': 30,
    'name': 'L2-DIST-1',
}

DIST2 = {
    'device_type': 'cisco_ios',
    'host': '172.31.0.180',
    'username': 'admin',
    'password': 'CXlabs.123',
    'timeout': 30,
    'name': 'L2-DIST-2',
}

BC1 = {
    'device_type': 'cisco_ios',
    'host': '172.31.2.0',
    'username': 'admin1',
    'password': 'CXlabs.123',
    'timeout': 30,
    'name': 'FS2_BC1',
}

BC1_ALT = {
    'device_type': 'cisco_ios',
    'host': '172.31.2.0',
    'username': 'dnac_admin_tacacs',
    'password': 'CXlabs.123',
    'timeout': 30,
    'name': 'FS2_BC1',
}

L2_9300_1 = {
    'device_type': 'cisco_ios',
    'host': '172.31.0.179',
    'username': 'admin',
    'password': 'CXlabs.123',
    'timeout': 30,
    'name': 'FS2_L2_9300-1',
}

L2_9300_2 = {
    'device_type': 'cisco_ios',
    'host': '172.31.0.178',
    'username': 'admin',
    'password': 'CXlabs.123',
    'timeout': 30,
    'name': 'FS2_L2_9300-2',
}

# =============================================================================
# HELPERS
# =============================================================================

def ts():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')

def pause(msg):
    print(f"\n{'='*70}")
    print(f"  PAUSE: {msg}")
    print(f"{'='*70}")
    input("  >>> Press ENTER when ready to continue... ")
    print()

def banner(text, char='='):
    width = 70
    print(f"\n{char*width}")
    print(f"  {text}")
    print(f"{char*width}\n")

def sub_banner(text):
    print(f"\n--- {text} ---\n")

def safe_disconnect(conn):
    if conn is None:
        return
    try:
        conn.disconnect()
    except Exception:
        pass

def connect(device_info, try_alt=None):
    name = device_info['name']
    host = device_info['host']
    print(f"  Connecting to {name} ({host}) as {device_info['username']}...", end=' ', flush=True)
    dev = {k: v for k, v in device_info.items() if k != 'name'}
    try:
        conn = ConnectHandler(**dev)
        prompt = conn.find_prompt()
        print(f"OK [{prompt}]")
        return conn
    except Exception as e:
        print(f"FAILED ({type(e).__name__})")
        if try_alt:
            print(f"  Trying {try_alt['username']}...", end=' ', flush=True)
            dev_alt = {k: v for k, v in try_alt.items() if k != 'name'}
            try:
                conn = ConnectHandler(**dev_alt)
                prompt = conn.find_prompt()
                print(f"OK [{prompt}]")
                return conn
            except Exception as e2:
                print(f"FAILED ({type(e2).__name__})")
                raise
        else:
            raise


def connect_l2h1():
    """Connect to L2H-1 trying TACACS first, then local."""
    return connect(L2H1_TACACS, try_alt=L2H1_LOCAL)

def connect_dist1():
    """Connect to L2-DIST-1."""
    return connect(DIST1)

def run_cmd(conn, cmd, read_timeout=30):
    try:
        output = conn.send_command(cmd, read_timeout=read_timeout)
    except Exception as e:
        output = f"ERROR running command: {e}"
    print(output)
    return output

def collect_commands(device_info, commands, filename, try_alt=None):
    conn = connect(device_info, try_alt=try_alt)
    output_all = ""
    for cmd, label in commands:
        sub_banner(f"{label}: {cmd}")
        out = run_cmd(conn, cmd)
        output_all += f"\n--- {label}: {cmd} ---\n{out}\n"
    safe_disconnect(conn)
    save_output(filename, output_all)

def save_output(filename, content):
    with open(filename, 'w') as f:
        f.write(f"Collected: {ts()}\n{'='*60}\n\n")
        f.write(content)
    size = os.path.getsize(filename)
    print(f"  Saved: {os.path.basename(filename)} ({size:,} bytes)")


# =============================================================================
# COMMAND SETS
# =============================================================================

# L2H-1 full baseline (both distribution trunks + fabric side)
L2H1_FULL_CMDS = [
    ("show version | include uptime", "UPTIME"),
    # -- Distribution trunk side --
    ("show interfaces TenGigabitEthernet4/0/20", "Te4/0/20 (trunk to L2-DIST-1)"),
    ("show interfaces TenGigabitEthernet4/0/20 human-readable", "Te4/0/20 (human-readable)"),
    ("show interfaces TenGigabitEthernet4/0/21", "Te4/0/21 (trunk to L2-DIST-2)"),
    ("show interfaces TenGigabitEthernet4/0/21 human-readable", "Te4/0/21 (human-readable)"),
    ("show interfaces trunk", "ALL TRUNKS"),
    ("show spanning-tree vlan 101", "STP VLAN 101 (BMS1)"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301 (EUT)"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
    ("show interfaces vlan 101", "SVI VLAN 101 (BMS1)"),
    ("show interfaces vlan 1301", "SVI VLAN 1301 (EUT)"),
    # -- Fabric side (must remain UP) --
    ("show etherchannel summary", "ALL ETHERCHANNELS"),
    ("show interfaces Port-channel40 | include line protocol|BW|5 minute", "Po40 STATUS"),
    ("show interfaces Port-channel41 | include line protocol|BW|5 minute", "Po41 STATUS"),
    ("show ip ospf neighbor", "OSPF NEIGHBORS"),
    ("show bfd neighbors", "BFD SESSIONS"),
    ("show lisp session", "LISP SESSIONS"),
    ("show ip route summary", "ROUTE SUMMARY"),
    ("show cts role-based counters", "CTS COUNTERS"),
    # -- Multicast verification --
    ("show ip multicast", "MULTICAST GLOBAL STATUS"),
    ("show ip pim vrf BMS1 neighbor", "PIM NEIGHBORS (VRF BMS1)"),
    ("show ip pim vrf BMS1 rp mapping", "PIM RP MAPPING (VRF BMS1)"),
    ("show ip mroute vrf BMS1 225.1.1.1", "MROUTE 225.1.1.1 (VRF BMS1)"),
    ("show ip mroute vrf BMS1 summary", "MROUTE SUMMARY (VRF BMS1)"),
    ("show ip mfib vrf BMS1 225.1.1.1", "MFIB 225.1.1.1 HW COUNTERS (VRF BMS1)"),
    ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (BMS1)"),
    ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301 (EUT)"),
    ("show ip igmp snooping vlan 101", "IGMP SNOOPING CONFIG VLAN 101"),
]

# L2H-1 during failure — remote end (DIST-1) shut, L2H-1 sees Te4/0/20 go down
L2H1_DURING_CMDS = [
    # -- Distribution trunk side --
    ("show interfaces TenGigabitEthernet4/0/20 | include line protocol|BW", "Te4/0/20 STATUS (remote side shut)"),
    ("show interfaces TenGigabitEthernet4/0/20 human-readable", "Te4/0/20 (human-readable)"),
    ("show interfaces TenGigabitEthernet4/0/21 | include line protocol|BW", "Te4/0/21 STATUS (UP - redundant)"),
    ("show interfaces TenGigabitEthernet4/0/21 human-readable", "Te4/0/21 (human-readable, UP)"),
    ("show interfaces trunk", "TRUNKS (Te4/0/21 MUST be present)"),
    ("show spanning-tree vlan 101", "STP VLAN 101 (reconverged via Te4/0/21)"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301 (reconverged via Te4/0/21)"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
    ("show interfaces vlan 101", "SVI VLAN 101 (should stay UP)"),
    ("show interfaces vlan 1301", "SVI VLAN 1301 (should stay UP)"),
    # -- Fabric side (MUST remain UP) --
    ("show etherchannel summary", "ETHERCHANNELS (MUST be RU)"),
    ("show interfaces Port-channel40 | include line protocol|BW|5 minute", "Po40 (MUST be UP)"),
    ("show interfaces Port-channel41 | include line protocol|BW|5 minute", "Po41 (MUST be UP)"),
    ("show ip ospf neighbor", "OSPF (MUST be FULL to both BCs)"),
    ("show bfd neighbors", "BFD (MUST be UP to both BCs)"),
    ("show lisp session", "LISP (MUST be 2/2 established)"),
    ("show ip route summary", "ROUTE SUMMARY"),
    ("show cts role-based counters", "CTS COUNTERS"),
    # -- Multicast verification during failure --
    ("show ip mroute vrf BMS1 225.1.1.1", "MROUTE 225.1.1.1 (MUST still have entries)"),
    ("show ip mfib vrf BMS1 225.1.1.1", "MFIB 225.1.1.1 HW COUNTERS (check forwarding)"),
    ("show ip pim vrf BMS1 neighbor", "PIM NEIGHBORS (VRF BMS1, MUST be UP)"),
    ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (group 225.1.1.1)"),
    ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301"),
    ("show logging | include LINK|UPDOWN|LINEPROTO|STP", "SYSLOG (filtered)"),
]

# L2-DIST-1 commands — THIS IS THE DUT (shutdown happens here)
DIST1_BASELINE_CMDS = [
    ("show version | include uptime", "UPTIME"),
    ("show interfaces TenGigabitEthernet4/0/20", "Te4/0/20 (trunk to L2H-1) — WILL BE SHUT"),
    ("show interfaces TenGigabitEthernet4/0/20 human-readable", "Te4/0/20 (human-readable)"),
    ("show interfaces trunk", "ALL TRUNKS"),
    ("show spanning-tree vlan 101", "STP VLAN 101"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
    ("show cdp neighbors", "CDP NEIGHBORS"),
    # -- Multicast (L2 snooping on DIST-1) --
    ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (BMS1)"),
    ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301 (EUT)"),
    ("show ip igmp snooping vlan 101", "IGMP SNOOPING CONFIG VLAN 101"),
]

DIST1_DURING_CMDS = [
    ("show interfaces TenGigabitEthernet4/0/20 | include line protocol|BW", "Te4/0/20 (ADMIN DOWN — shutdown executed here)"),
    ("show interfaces TenGigabitEthernet4/0/20 human-readable", "Te4/0/20 (human-readable, ADMIN DOWN)"),
    ("show interfaces trunk", "TRUNKS (Te4/0/20 absent)"),
    ("show spanning-tree vlan 101", "STP VLAN 101 (root lost via this port)"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301 (root lost via this port)"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101 (aging)"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301 (aging)"),
    # -- Multicast (snooping state during trunk loss) --
    ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (group may age out)"),
    ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301"),
    ("show logging | include LINK|UPDOWN|LINEPROTO|STP", "SYSLOG (filtered)"),
]

DIST1_POST_CMDS = [
    ("show interfaces TenGigabitEthernet4/0/20", "Te4/0/20 (trunk to L2H-1) — RESTORED"),
    ("show interfaces TenGigabitEthernet4/0/20 human-readable", "Te4/0/20 (human-readable)"),
    ("show interfaces trunk", "ALL TRUNKS"),
    ("show spanning-tree vlan 101", "STP VLAN 101"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
    # -- Multicast (snooping restored) --
    ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (restored)"),
    ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301 (restored)"),
    ("show logging | include LINK|UPDOWN|LINEPROTO|STP", "SYSLOG (filtered)"),
]

# L2-DIST-2 commands (REDUNDANT — stays UP, absorbs STP traffic)
DIST2_BASELINE_CMDS = [
    ("show version | include uptime", "UPTIME"),
    ("show interfaces TenGigabitEthernet1/0/20", "Te1/0/20 (trunk to L2H-1)"),
    ("show interfaces TenGigabitEthernet1/0/20 human-readable", "Te1/0/20 (human-readable)"),
    ("show interfaces trunk", "ALL TRUNKS"),
    ("show spanning-tree vlan 101", "STP VLAN 101"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
    ("show cdp neighbors", "CDP NEIGHBORS"),
    # -- Multicast (L2 snooping on DIST-2) --
    ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (BMS1)"),
    ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301 (EUT)"),
    ("show ip igmp snooping vlan 101", "IGMP SNOOPING CONFIG VLAN 101"),
]

DIST2_DURING_CMDS = [
    ("show interfaces TenGigabitEthernet1/0/20 | include line protocol|BW", "Te1/0/20 (MUST be UP)"),
    ("show interfaces TenGigabitEthernet1/0/20 human-readable", "Te1/0/20 (human-readable)"),
    ("show interfaces trunk", "TRUNKS (Te1/0/20 MUST be present)"),
    ("show spanning-tree vlan 101", "STP VLAN 101 (may become new active path)"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301 (may become new active path)"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
    # -- Multicast (DIST-2 absorbing mcast during failure) --
    ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (absorbing traffic)"),
    ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301"),
    ("show logging | include LINK|UPDOWN|LINEPROTO|STP", "SYSLOG (filtered)"),
]

DIST2_POST_CMDS = [
    ("show interfaces TenGigabitEthernet1/0/20", "Te1/0/20 (trunk to L2H-1)"),
    ("show interfaces TenGigabitEthernet1/0/20 human-readable", "Te1/0/20 (human-readable)"),
    ("show interfaces trunk", "ALL TRUNKS"),
    ("show spanning-tree vlan 101", "STP VLAN 101"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
    # -- Multicast (snooping restored on DIST-2) --
    ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (restored)"),
    ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301 (restored)"),
    ("show logging | include LINK|UPDOWN|LINEPROTO|STP", "SYSLOG (filtered)"),
]

# BC1 commands (fabric side health check — should be unaffected)
BC1_CHECK_CMDS = [
    ("show etherchannel 40 summary", "ETHERCHANNEL 40 SUMMARY"),
    ("show ip ospf neighbor | include 192.168.102.40", "OSPF TO L2H-1"),
    ("show lisp session | include 192.168.102.40", "LISP TO L2H-1"),
    ("show bfd neighbors | include 192.168.40.0", "BFD TO L2H-1"),
    # -- Multicast (BC1 fabric-side mcast health) --
    ("show ip mroute vrf BMS1 225.1.1.1", "MROUTE 225.1.1.1 (VRF BMS1)"),
    ("show ip pim vrf BMS1 neighbor", "PIM NEIGHBORS (VRF BMS1)"),
]

# FS2_L2_9300-1 commands (legacy access switch behind DIST-1)
L2_9300_1_BASELINE_CMDS = [
    ("show version | include uptime", "UPTIME"),
    ("show interfaces trunk", "ALL TRUNKS"),
    ("show spanning-tree vlan 101", "STP VLAN 101"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
    ("show cdp neighbors", "CDP NEIGHBORS"),
    ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (BMS1)"),
    ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301 (EUT)"),
]

L2_9300_1_DURING_CMDS = [
    ("show interfaces trunk", "TRUNKS"),
    ("show spanning-tree vlan 101", "STP VLAN 101 (topology change?)"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301 (topology change?)"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
    ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101"),
    ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301"),
    ("show logging | include LINK|UPDOWN|LINEPROTO|STP|TCN", "SYSLOG (filtered)"),
]

L2_9300_1_POST_CMDS = [
    ("show interfaces trunk", "TRUNKS"),
    ("show spanning-tree vlan 101", "STP VLAN 101 (restored)"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301 (restored)"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
    ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (restored)"),
    ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301 (restored)"),
    ("show logging | include LINK|UPDOWN|LINEPROTO|STP|TCN", "SYSLOG (filtered)"),
]

# FS2_L2_9300-2 commands (legacy access switch behind DIST-2)
L2_9300_2_BASELINE_CMDS = [
    ("show version | include uptime", "UPTIME"),
    ("show interfaces trunk", "ALL TRUNKS"),
    ("show spanning-tree vlan 101", "STP VLAN 101"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
    ("show cdp neighbors", "CDP NEIGHBORS"),
    ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (BMS1)"),
    ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301 (EUT)"),
]

L2_9300_2_DURING_CMDS = [
    ("show interfaces trunk", "TRUNKS"),
    ("show spanning-tree vlan 101", "STP VLAN 101 (topology change?)"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301 (topology change?)"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
    ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101"),
    ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301"),
    ("show logging | include LINK|UPDOWN|LINEPROTO|STP|TCN", "SYSLOG (filtered)"),
]

L2_9300_2_POST_CMDS = [
    ("show interfaces trunk", "TRUNKS"),
    ("show spanning-tree vlan 101", "STP VLAN 101 (restored)"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301 (restored)"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
    ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (restored)"),
    ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301 (restored)"),
    ("show logging | include LINK|UPDOWN|LINEPROTO|STP|TCN", "SYSLOG (filtered)"),
]


# =============================================================================
# PHASE 1: STEADY STATE BASELINE
# =============================================================================

def phase1(iter_dir, iteration):
    banner(f"PHASE 1: STEADY STATE BASELINE  (Iteration {iteration})")
    print(f"  Timestamp: {ts()}")
    print()
    print("  TOPOLOGY (Distribution Side Shutdown — REVERSE of standard TC 07-04):")
    print("    L2-DIST-1 --Te4/0/20 (L2 trunk)--> FS2_L2H-1 Te4/0/20   <-- DIST-1 SIDE SHUT")
    print("    L2-DIST-2 --Te1/0/20 (L2 trunk)--> FS2_L2H-1 Te4/0/21   <-- REDUNDANT (stays UP)")
    print()
    print("    VLANs: 101 (BMS1, 10.5.28.0/22) + 1301 (EUT, 10.5.20.0/22)")
    print("    STP Root: FS2_L2H-1 for both VLANs")
    print("    Trunk type: Independent L2 trunks (no port-channel)")
    print()
    print("  DIFFERENCE from standard TC 07-04:")
    print("    Standard:  Shutdown Te4/0/20 on FS2_L2H-1 (L2 Border side)")
    print("    This test: Shutdown Te4/0/20 on L2-DIST-1 (Distribution side)")
    print("    Same trunk, opposite end — validates remote-end link failure.")
    print()
    print("  KEY OBSERVATION:")
    print("    When DIST-1 shuts its port, L2H-1 Te4/0/20 sees link-down")
    print("    (not admin-down). CC may raise an issue for link-down vs")
    print("    the zero issues seen for admin-shutdown in standard TC 07-04.")
    print()

    # ---- Step 1.0: Clear logs ----
    banner("STEP 1.0: CLEARING LOGS ON ALL DEVICES", '-')
    for dev, alt, name in [(L2H1_TACACS, L2H1_LOCAL, 'L2H-1'), (DIST1, None, 'L2-DIST-1'), (DIST2, None, 'L2-DIST-2'), (L2_9300_1, None, 'L2_9300-1'), (L2_9300_2, None, 'L2_9300-2')]:
        try:
            conn = connect(dev, try_alt=alt)
            conn.send_command_timing("clear logging", strip_command=False)
            conn.send_command_timing("", strip_command=False)
            print(f"    {name}: logs cleared")
            safe_disconnect(conn)
        except Exception as e:
            print(f"    {name}: WARNING - could not clear logs: {e}")
    print()

    # ---- Step 1.1: Spirent ----
    banner("STEP 1.1: SPIRENT TRAFFIC BASELINE", '-')
    print("  ACTION REQUIRED:")
    print("    1. Open Spirent GUI (172.31.0.101)")
    print("    2. Verify ALL streams running (green icons)")
    print("    3. Verify 0 dead streams")
    print("    4. Clear counters -> wait 60 seconds")
    print("    5. Verify Frame Loss = 0, Loss % = 0.000%")
    print(f"    6. Screenshot: Iter{iteration}_Pre_Spirent_Baseline.png")
    pause("Take Spirent baseline screenshot, then press ENTER")

    # ---- Step 1.2: Catalyst Center ----
    banner("STEP 1.2: CATALYST CENTER BASELINE", '-')
    print("  ACTION REQUIRED:")
    print("    1. Open CC: https://172.31.229.151")
    print("    2. Provision > Inventory > FS2_L2H_1")
    print("       - Verify: Reachable, Health >= 80%")
    print(f"    3. Screenshot: Iter{iteration}_Pre_CC_L2H1_Health.png")
    print()
    print("    NOTE: CC Inventory interface status is NOT real-time.")
    print("    It reflects the last device synchronization cycle.")
    print("    CLI output is the authoritative real-time source.")
    print()
    print("    4. Assurance > Health")
    print(f"    5. Screenshot: Iter{iteration}_Pre_CC_Health.png")
    pause("Take Catalyst Center baseline screenshots, then press ENTER")

    # ---- Step 1.3: L2H-1 CLI Baseline ----
    banner("STEP 1.3: CLI BASELINE - FS2_L2H-1 (172.31.0.194)", '-')
    collect_commands(L2H1_TACACS, L2H1_FULL_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Pre_L2H1_Baseline.txt"),
        try_alt=L2H1_LOCAL)

    # ---- Step 1.4: L2-DIST-1 CLI Baseline ----
    banner("STEP 1.4: CLI BASELINE - L2-DIST-1 (172.31.0.193) — DUT", '-')
    collect_commands(DIST1, DIST1_BASELINE_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Pre_DIST1_Baseline.txt"))

    # ---- Step 1.5: L2-DIST-2 CLI Baseline ----
    banner("STEP 1.5: CLI BASELINE - L2-DIST-2 (172.31.0.180)", '-')
    collect_commands(DIST2, DIST2_BASELINE_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Pre_DIST2_Baseline.txt"))

    # ---- Step 1.6: BC1 Fabric Health ----
    banner("STEP 1.6: CLI BASELINE - FS2_BC1 (172.31.2.0) FABRIC HEALTH", '-')
    collect_commands(BC1, BC1_CHECK_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Pre_BC1_Health.txt"),
        try_alt=BC1_ALT)

    # ---- Step 1.7: FS2_L2_9300-1 CLI Baseline ----
    banner("STEP 1.7: CLI BASELINE - FS2_L2_9300-1 (172.31.0.179)", '-')
    collect_commands(L2_9300_1, L2_9300_1_BASELINE_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Pre_L2_9300-1_Baseline.txt"))

    # ---- Step 1.8: FS2_L2_9300-2 CLI Baseline ----
    banner("STEP 1.8: CLI BASELINE - FS2_L2_9300-2 (172.31.0.178)", '-')
    collect_commands(L2_9300_2, L2_9300_2_BASELINE_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Pre_L2_9300-2_Baseline.txt"))

    # ---- Phase 1 Gate ----
    banner("PHASE 1 GATE CHECK", '*')
    print("  Verify ALL of the following before proceeding:")
    print("    [ ] Spirent: 0.000% loss, 0 dead streams")
    print("    [ ] CC: L2H-1 Reachable, health >= 80%")
    print("    [ ] L2H-1: Te4/0/20 UP (trunk to L2-DIST-1)")
    print("    [ ] L2H-1: Te4/0/21 UP (trunk to L2-DIST-2, redundant path)")
    print("    [ ] L2H-1: STP Forwarding on both Te4/0/20 and Te4/0/21")
    print("    [ ] L2H-1: MAC addresses learned on VLAN 101 & 1301")
    print("    [ ] L2H-1: SVIs VLAN 101 + 1301 UP")
    print("    [ ] L2H-1: Po40(RU) + Po41(RU) — fabric side healthy")
    print("    [ ] L2H-1: OSPF FULL to both BCs, BFD UP to both")
    print("    [ ] L2H-1: 2 LISP sessions established")
    print("    [ ] L2H-1: Multicast mroute 225.1.1.1 present, PIM neighbors UP")
    print("    [ ] L2-DIST-1: Te4/0/20 UP, trunking VLANs 101/1301")
    print("    [ ] L2-DIST-2: Te1/0/20 UP, trunking VLANs 101/1301")
    print("    [ ] L2_9300-1: IGMP snooping groups on VLAN 101/1301")
    print("    [ ] L2_9300-2: IGMP snooping groups on VLAN 101/1301")
    print("    [ ] BC1: OSPF/LISP/BFD to L2H-1 UP")
    pause("Confirm all checks PASS, then press ENTER to proceed to PHASE 2")


# =============================================================================
# PHASE 2: FAILURE EVENT - SHUTDOWN Te4/0/20 ON L2-DIST-1
# =============================================================================

def phase2(iter_dir, iteration):
    banner(f"PHASE 2: FAILURE EVENT - SHUTDOWN Te4/0/20 ON L2-DIST-1 (Iteration {iteration})")
    print(f"  Timestamp: {ts()}")
    print()
    print("  TARGET: TenGigabitEthernet4/0/20 on L2-DIST-1 (172.31.0.193)")
    print("  ACTION: shutdown Te4/0/20 on L2-DIST-1 (distribution switch side)")
    print()
    print("  EXPECTED BEHAVIOR:")
    print("    X  L2-DIST-1 Te4/0/20 goes ADMIN DOWN (shutdown executed here)")
    print("    X  L2H-1 Te4/0/20 sees LINK DOWN (remote end shut, not local admin-down)")
    print("    X  STP reconverges — traffic shifts to Te4/0/21 via L2-DIST-2")
    print("    X  Packet loss during STP convergence (measured via Spirent)")
    print()
    print("    OK Te4/0/21 stays UP (trunk to L2-DIST-2 provides redundancy)")
    print("    OK SVIs VLAN 101/1301 remain UP on L2H-1")
    print("    OK Po40 + Po41 REMAIN UP (fabric side unaffected)")
    print("    OK OSPF/BFD/LISP to BCs remain operational")
    print()
    print("  CC BEHAVIOR NOTE:")
    print("    L2H-1 Te4/0/20 will show as LINK DOWN (not admin-down).")
    print("    CC may raise an issue for this — compare with standard TC 07-04")
    print("    where admin-shutdown on L2H-1 raised zero issues.")
    print()
    pause("Ready to SHUTDOWN Te4/0/20 on L2-DIST-1? Press ENTER to execute")

    # ---- Step 2.1: Execute Shutdown on L2-DIST-1 ----
    banner("STEP 2.1: EXECUTING SHUTDOWN OF Te4/0/20 ON L2-DIST-1", '-')
    conn_dist1 = connect_dist1()

    shutdown_time = datetime.datetime.now()
    print(f"\n  >>> SHUTDOWN Te4/0/20 on L2-DIST-1 at {shutdown_time.strftime('%H:%M:%S')} <<<\n")

    config_output = conn_dist1.send_config_set([
        'interface TenGigabitEthernet4/0/20',
        'shutdown'
    ])
    print(config_output)
    safe_disconnect(conn_dist1)

    # ---- Step 2.2: Immediate Verification on L2H-1 ----
    banner("STEP 2.2: IMMEDIATE VERIFICATION ON L2H-1", '-')
    print("  Waiting 5 seconds for link down + STP convergence start...")
    time.sleep(5)
    print(f"  Verification at: {ts()}")

    conn = connect_l2h1()

    sub_banner("L2H-1 Te4/0/20 status (should be DOWN — remote end shut)")
    te20_out = run_cmd(conn, "show interfaces TenGigabitEthernet4/0/20 | include line protocol|BW")

    sub_banner("L2H-1 Te4/0/21 status (MUST remain UP)")
    run_cmd(conn, "show interfaces TenGigabitEthernet4/0/21 | include line protocol|BW")

    sub_banner("Trunk status (Te4/0/21 MUST be present)")
    run_cmd(conn, "show interfaces trunk | include Te4")

    sub_banner("Fabric side check - Po40 + Po41")
    run_cmd(conn, "show etherchannel summary")

    sub_banner("OSPF (MUST remain FULL to both BCs)")
    ospf_out = run_cmd(conn, "show ip ospf neighbor")

    sub_banner("BFD (MUST remain UP)")
    run_cmd(conn, "show bfd neighbors")

    sub_banner("LISP (MUST remain 2/2)")
    run_cmd(conn, "show lisp session")

    safe_disconnect(conn)

    print()
    print("  !!! CRITICAL VERIFICATION !!!")
    print("  Expected State on L2H-1:")
    print("    X  Te4/0/20: DOWN (line protocol down — remote end shut)")
    print("         NOTE: NOT 'administratively down' — this is LINK DOWN")
    print("    OK Te4/0/21: UP (redundant trunk to L2-DIST-2)")
    print("    OK Po40 + Po41: UP (RU)")
    print("    OK OSPF: FULL to both 192.168.40.1 and 192.168.41.1")
    print("    OK BFD: UP to both BCs")
    print("    OK LISP: 2/2 established")

    if 'down' in te20_out.lower() and 'administratively down' not in te20_out.lower():
        print(f"\n  >>> CONFIRMED: L2H-1 Te4/0/20 shows LINK DOWN (not admin-down) <<<")
    elif 'administratively down' in te20_out.lower():
        print(f"\n  !!! UNEXPECTED: Shows admin-down on L2H-1 — verify correct device was shut")
    elif 'up' in te20_out.lower():
        print(f"\n  !!! WARNING: Te4/0/20 still UP — link down may be delayed, wait and re-check")

    if 'FULL' in ospf_out:
        full_count = ospf_out.count('FULL')
        print(f"\n  >>> FABRIC HEALTHY: {full_count} OSPF FULL adjacencies maintained <<<")
    else:
        print("\n  !!! WARNING: No OSPF FULL adjacencies found — investigate!")

    # ---- Step 2.3: Spirent Convergence ----
    banner("STEP 2.3: SPIRENT CONVERGENCE MEASUREMENT", '-')
    print("  EXPECTED: Measurable packet loss during STP convergence,")
    print("  then traffic recovers via Te4/0/21 -> L2-DIST-2 path.")
    print()
    print("  ACTION REQUIRED:")
    print("    1. Watch Spirent GUI — note dead/dropped streams")
    print("    2. Monitor for 3 minutes")
    print("    3. Record dead stream count and which streams affected")
    print(f"    4. Screenshot: Iter{iteration}_During_Spirent_Convergence.png")
    print()
    print("    5. STOP traffic after 3 minutes")
    print(f"    6. Export DB: Iter{iteration}_During_Spirent.tcc")
    print("    7. Upload to PLA: http://spirent-pla.cisco.com")
    print(f"    8. Download Excel: Iter{iteration}_PLA_Convergence.xlsx")
    print(f"    9. Screenshot PLA: Iter{iteration}_PLA_Analysis.png")
    pause("Complete Spirent convergence measurement, then press ENTER")

    # ---- Step 2.4: L2H-1 During CLI ----
    banner("STEP 2.4: L2H-1 DURING-FAILURE CLI", '-')
    collect_commands(L2H1_TACACS, L2H1_DURING_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_During_L2H1_Failure.txt"),
        try_alt=L2H1_LOCAL)

    # ---- Step 2.5: L2-DIST-1 During CLI (DUT — shutdown executed here) ----
    banner("STEP 2.5: L2-DIST-1 DURING-FAILURE CLI (DUT — shutdown here)", '-')
    collect_commands(DIST1, DIST1_DURING_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_During_DIST1_Status.txt"))

    # ---- Step 2.6: L2-DIST-2 During CLI (redundant, absorbing traffic) ----
    banner("STEP 2.6: L2-DIST-2 DURING-FAILURE CLI (REDUNDANT PATH)", '-')
    collect_commands(DIST2, DIST2_DURING_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_During_DIST2_Status.txt"))

    # ---- Step 2.7: BC1 During CLI ----
    banner("STEP 2.7: BC1 FABRIC HEALTH DURING FAILURE", '-')
    print("  BC1 MUST still see L2H-1 — failure is on distribution side only")
    collect_commands(BC1, BC1_CHECK_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_During_BC1_Health.txt"),
        try_alt=BC1_ALT)

    # ---- Step 2.8: FS2_L2_9300-1 During CLI ----
    banner("STEP 2.8: FS2_L2_9300-1 DURING FAILURE (172.31.0.179)", '-')
    print("  Legacy access switch behind L2-DIST-1 — may see STP topology change")
    collect_commands(L2_9300_1, L2_9300_1_DURING_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_During_L2_9300-1_Status.txt"))

    # ---- Step 2.9: FS2_L2_9300-2 During CLI ----
    banner("STEP 2.9: FS2_L2_9300-2 DURING FAILURE (172.31.0.178)", '-')
    print("  Legacy access switch behind L2-DIST-2 — should be unaffected")
    collect_commands(L2_9300_2, L2_9300_2_DURING_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_During_L2_9300-2_Status.txt"))

    # ---- Step 2.10: CC During ----
    banner("STEP 2.10: CATALYST CENTER DURING FAILURE", '-')
    print("  ACTION REQUIRED:")
    print("    1. Provision > Inventory > FS2_L2H_1")
    print("       - Expected: Still Reachable (fabric side unaffected)")
    print("       - CHECK: Does CC raise an issue for Te4/0/20 LINK DOWN?")
    print("         (Compare with standard TC 07-04 where admin-shutdown = 0 issues)")
    print(f"    2. Screenshot: Iter{iteration}_During_CC_Status.png")
    print()
    print("    3. Also check Assurance > Issues")
    print("       - Note any issue raised for Te4/0/20 link-down")
    print(f"    4. Screenshot: Iter{iteration}_During_CC_Issues.png")
    pause("Take CC during-failure screenshots (capture any issues), then press ENTER to RECOVERY")


# =============================================================================
# PHASE 3: RECOVERY - RESTORE Te4/0/20 ON L2-DIST-1
# =============================================================================

def phase3(iter_dir, iteration):
    banner(f"PHASE 3: RECOVERY - RESTORE Te4/0/20 ON L2-DIST-1 (Iteration {iteration})")
    print(f"  Timestamp: {ts()}")
    print()
    print("  ACTION: no shutdown Te4/0/20 on L2-DIST-1 (restore trunk)")
    print("  EXPECTED: Trunk comes up, STP converges, both paths resume.")
    pause("Ready to RESTORE Te4/0/20 on L2-DIST-1? Press ENTER to execute")

    # ---- Step 3.1: Execute Recovery on L2-DIST-1 ----
    banner("STEP 3.1: EXECUTING RECOVERY (no shutdown Te4/0/20 on L2-DIST-1)", '-')
    conn_dist1 = connect_dist1()

    recovery_time = datetime.datetime.now()
    print(f"\n  >>> NO SHUTDOWN Te4/0/20 on L2-DIST-1 at {recovery_time.strftime('%H:%M:%S')} <<<\n")

    config_output = conn_dist1.send_config_set([
        'interface TenGigabitEthernet4/0/20',
        'no shutdown'
    ])
    print(config_output)
    safe_disconnect(conn_dist1)

    # ---- Step 3.2: Monitor Link Up on L2H-1 ----
    banner("STEP 3.2: MONITORING L2H-1 Te4/0/20 LINK UP + STP CONVERGENCE", '-')
    print("  Checking every 5s for up to 60s...")
    conn = connect_l2h1()
    link_up = False
    stp_fwd = False
    for t in range(5, 65, 5):
        time.sleep(5)
        now = datetime.datetime.now().strftime('%H:%M:%S')
        try:
            result = conn.send_command(
                "show interfaces TenGigabitEthernet4/0/20 | include line protocol",
                read_timeout=15)
        except Exception:
            safe_disconnect(conn)
            conn = connect_l2h1()
            result = conn.send_command(
                "show interfaces TenGigabitEthernet4/0/20 | include line protocol",
                read_timeout=15)
        status = result.strip()
        print(f"  T+{t:2d}s ({now}): {status}")

        if 'up' in status.lower() and 'line protocol is up' in status.lower() and not link_up:
            link_up = True
            print(f"  >>> L2H-1 Te4/0/20 LINK UP at T+{t}s (remote end restored) <<<")

        if link_up and not stp_fwd:
            try:
                stp = conn.send_command(
                    "show spanning-tree vlan 101 | include Te4/0/20",
                    read_timeout=15)
            except Exception:
                stp = ""
            if 'FWD' in stp or 'Desg' in stp:
                stp_fwd = True
                print(f"  >>> STP FORWARDING at T+{t}s <<<")
                print(f"      {stp.strip()}")

    if not link_up:
        print("  WARNING: L2H-1 Te4/0/20 not UP after 60s — check L2-DIST-1!")
    if link_up and not stp_fwd:
        print("  WARNING: STP not forwarding after 60s — may still be learning")
        try:
            stp_full = conn.send_command("show spanning-tree vlan 101", read_timeout=15)
            print(stp_full)
        except Exception:
            pass

    # ---- Step 3.3: Verify Trunk Restored ----
    banner("STEP 3.3: VERIFY BOTH TRUNKS RESTORED", '-')
    time.sleep(5)
    try:
        trunk_out = run_cmd(conn, "show interfaces trunk")
        if 'Te4/0/20' in trunk_out and 'Te4/0/21' in trunk_out:
            print("\n  >>> BOTH TRUNKS ACTIVE: Te4/0/20 + Te4/0/21 <<<")
        elif 'Te4/0/20' in trunk_out:
            print("\n  >>> Te4/0/20 trunk restored (Te4/0/21 check separately)")
        else:
            print("\n  !!! WARNING: Te4/0/20 not in trunk output yet")
    except Exception:
        print("  Connection issue — will capture in post-recovery CLI")

    safe_disconnect(conn)

    # ---- Step 3.4: Spirent Post-Recovery ----
    banner("STEP 3.4: SPIRENT POST-RECOVERY VALIDATION", '-')
    print("  ACTION REQUIRED:")
    print("    1. START Spirent traffic (if stopped)")
    print("    2. Clear counters, wait 60 seconds")
    print("    3. Verify: Loss % = 0.000%, Dead Streams = 0")
    print("    4. ALL streams must be alive (including L2 handoff)")
    print(f"    5. Screenshot: Iter{iteration}_Post_Spirent_Restored.png")
    pause("Take Spirent post-recovery screenshot, then press ENTER")

    # ---- Step 3.5-3.8: Post-Recovery CLI ----
    banner("STEP 3.5: L2H-1 POST-RECOVERY CLI", '-')
    collect_commands(L2H1_TACACS, L2H1_FULL_CMDS + [
        ("show logging | include LINK|UPDOWN|LINEPROTO|STP", "SYSLOG (filtered)"),
    ], os.path.join(iter_dir, f"Iter{iteration}_Post_L2H1_Validation.txt"),
        try_alt=L2H1_LOCAL)

    banner("STEP 3.6: L2-DIST-1 POST-RECOVERY CLI", '-')
    collect_commands(DIST1, DIST1_POST_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Post_DIST1_Validation.txt"))

    banner("STEP 3.7: L2-DIST-2 POST-RECOVERY CLI", '-')
    collect_commands(DIST2, DIST2_POST_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Post_DIST2_Validation.txt"))

    banner("STEP 3.8: BC1 FABRIC HEALTH POST-RECOVERY", '-')
    collect_commands(BC1, BC1_CHECK_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Post_BC1_Health.txt"),
        try_alt=BC1_ALT)

    banner("STEP 3.9: FS2_L2_9300-1 POST-RECOVERY CLI", '-')
    collect_commands(L2_9300_1, L2_9300_1_POST_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Post_L2_9300-1_Validation.txt"))

    banner("STEP 3.10: FS2_L2_9300-2 POST-RECOVERY CLI", '-')
    collect_commands(L2_9300_2, L2_9300_2_POST_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Post_L2_9300-2_Validation.txt"))

    # ---- Step 3.11: CC Post-Recovery ----
    banner("STEP 3.11: CATALYST CENTER POST-RECOVERY", '-')
    print("  ACTION REQUIRED:")
    print("    1. Provision > Inventory > FS2_L2H_1 - Verify Reachable")
    print("       NOTE: Interface status reflects last sync, not real-time")
    print("    2. Check: Did the link-down issue auto-resolve?")
    print(f"    3. Screenshot: Iter{iteration}_Post_CC_L2H1_Health.png")
    print("    4. Assurance > Health >= 80%")
    print(f"    5. Screenshot: Iter{iteration}_Post_CC_Health.png")
    pause("Take CC post-recovery screenshots, then press ENTER")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='TC 07-04 (Dist Side): Shutdown Te4/0/20 on L2-DIST-1 instead of L2H-1')
    parser.add_argument('--iter', type=int, default=1, choices=[1, 2, 3],
                        help='Iteration number (1, 2, or 3)')
    args = parser.parse_args()
    iteration = args.iter

    banner("TC 07-04 (DIST SIDE): Link Failure — Distribution Switch End")
    print(f"  Iteration: {iteration}")
    print(f"  Start Time: {ts()}")
    print()
    print("  DUT:              L2-DIST-1 (172.31.0.193)")
    print("  Target Interface: Te4/0/20 on L2-DIST-1 (trunk to L2H-1)")
    print("  Redundant Path:   Te1/0/20 on L2-DIST-2 (trunk to L2H-1 Te4/0/21)")
    print()
    print("  TOPOLOGY:")
    print("    L2-DIST-1 --Te4/0/20--> FS2_L2H-1 Te4/0/20  <-- DIST-1 SIDE SHUT")
    print("    L2-DIST-2 --Te1/0/20--> FS2_L2H-1 Te4/0/21  <-- STAYS UP (redundant)")
    print()
    print("    VLANs: 101 (BMS1) + 1301 (EUT)")
    print("    STP Root: FS2_L2H-1")
    print("    Trunk type: Independent 10G L2 trunks (no LACP)")
    print()
    print("  DIFFERENCE FROM STANDARD TC 07-04:")
    print("    Standard:  shutdown on FS2_L2H-1 → L2H-1 shows admin-down → CC: 0 issues")
    print("    This test: shutdown on L2-DIST-1 → L2H-1 sees link-down  → CC: may raise issue")
    print()
    print("  This validates that the SAME trunk failure behaves identically regardless")
    print("  of which end initiates the shutdown. Key comparison point: CC issue behavior.")
    print()

    iter_dir = os.path.join(TC_DIR, "DistSide", f"Iter{iteration}_CLI")
    os.makedirs(iter_dir, exist_ok=True)
    img_dir = os.path.join(TC_DIR, "DistSide", "Images", f"Iteration{iteration}")
    os.makedirs(img_dir, exist_ok=True)
    print(f"  CLI directory: {iter_dir}")
    print(f"  Screenshot directory: {img_dir}")

    pause(f"Ready to begin Iteration {iteration}? Ensure VPN connected and devices reachable")

    phase1(iter_dir, iteration)
    phase2(iter_dir, iteration)
    phase3(iter_dir, iteration)

    # ---- Summary ----
    banner(f"ITERATION {iteration} COMPLETE")
    print(f"  End Time: {ts()}")
    print()
    print("  RESULTS CHECKLIST:")
    print("    [ ] L2-DIST-1 Te4/0/20 went ADMIN DOWN (shutdown executed on DIST-1)")
    print("    [ ] L2H-1 Te4/0/20 went DOWN (LINK DOWN, not admin-down)")
    print("    [ ] Te4/0/21 REMAINED UP — redundant path active (CRITICAL)")
    print("    [ ] STP reconverged traffic via Te4/0/21 to L2-DIST-2")
    print("    [ ] Packet loss measured during STP convergence (Spirent/PLA)")
    print("    [ ] Po40 + Po41 REMAINED UP (CRITICAL — fabric unaffected)")
    print("    [ ] OSPF FULL to BOTH BCs during failure (CRITICAL)")
    print("    [ ] BFD UP to both BCs during failure (CRITICAL)")
    print("    [ ] LISP 2/2 established during failure (CRITICAL)")
    print("    [ ] SVIs VLAN 101/1301 remained UP on L2H-1")
    print("    [ ] CC: Check if issue raised for link-down (vs 0 for admin-shutdown)")
    print("    [ ] Multicast: mroute 225.1.1.1 present in VRF BMS1 during failure")
    print("    [ ] Multicast: MFIB HW counters incrementing (forwarding active)")
    print("    [ ] Multicast: PIM neighbors UP in VRF BMS1 during failure")
    print("    [ ] Multicast: IGMP snooping group 225.1.1.1 on VLAN 101")
    print("    [ ] Multicast: DIST-2 IGMP snooping absorbing traffic during failure")
    print("    [ ] L2_9300-1: STP topology change notification received")
    print("    [ ] L2_9300-2: Unaffected (behind DIST-2, redundant path)")
    print("    [ ] Te4/0/20 restored after no shutdown on L2-DIST-1")
    print("    [ ] Both trunks active (Te4/0/20 + Te4/0/21)")
    print("    [ ] STP converged to Forwarding on Te4/0/20")
    print("    [ ] Spirent 0.000% loss after recovery (unicast + multicast)")
    print("    [ ] Multicast: mroute/MFIB/PIM/IGMP restored to baseline")
    print("    [ ] All metrics restored to baseline")
    print()
    print("  COMPARISON WITH STANDARD TC 07-04:")
    print("    Standard (L2H-1 admin-shut): CC Issues = 0 (admin-shutdown = intentional)")
    print("    This test (DIST-1 shut):     CC Issues = ??? (link-down = possible fault)")
    print("    >>> Document any difference in CC issue behavior <<<")
    print()
    print("  CLI EVIDENCE:")
    for f in sorted(os.listdir(iter_dir)):
        fpath = os.path.join(iter_dir, f)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            print(f"    {f} ({size:,} bytes)")
    print()

    if iteration < 3:
        print(f"  Next: python3 run_tc_07-04_dist_side.py --iter {iteration + 1}")
    else:
        print("  ALL 3 ITERATIONS COMPLETE.")
        print("  Next: Generate Word report and CXTM results.")
        print("  Compare CC issue behavior with standard TC 07-04 results.")

    print()


if __name__ == '__main__':
    main()
