#!/usr/bin/env python3
"""
TC 07-03: Link Failure From L2 Border Physical Link to Other BC Node
DUAL-HOMED TOPOLOGY - Po41 shutdown with Po40 providing redundancy

Mirror of TC 07-02 retest but shutting the OPPOSITE port-channel:
  TC 07-02 retest: Shut Po40 (BC1), Po41 (BC2) provides redundancy
  TC 07-03:        Shut Po41 (BC2), Po40 (BC1) provides redundancy

This validates that dual-homing works in BOTH directions — either path
can independently sustain full traffic when the other fails.

Topology:
  FS2_L2H-1 --Po40--> FS2_BC1 (192.168.40.0/31)  <-- REDUNDANT PATH (stays UP)
  FS2_L2H-1 --Po41--> FS2_BC2 (192.168.41.0/31)  <-- WILL BE SHUT DOWN

Usage: python3 run_tc_07-03.py [--iter 1|2|3]
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

BC1 = {
    'device_type': 'cisco_ios',
    'host': '172.31.2.0',
    'username': 'admin1',
    'password': 'CXlabs.123',
    'timeout': 30,
    'name': 'FS2_BC1',
}

BC2 = {
    'device_type': 'cisco_ios',
    'host': '172.31.2.2',
    'username': 'admin1',
    'password': 'CXlabs.123',
    'timeout': 30,
    'name': 'FS2_BC2',
}

BC2_ALT = {
    'device_type': 'cisco_ios',
    'host': '172.31.2.2',
    'username': 'dnac_admin_tacacs',
    'password': 'CXlabs.123',
    'timeout': 30,
    'name': 'FS2_BC2',
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
    print(f"  Connecting to {name} ({host})...", end=' ', flush=True)
    dev = {k: v for k, v in device_info.items() if k != 'name'}
    try:
        conn = ConnectHandler(**dev)
        prompt = conn.find_prompt()
        print(f"OK [{prompt}]")
        return conn
    except Exception as e:
        if try_alt:
            print(f"FAILED, trying alternate credentials...")
            print(f"  Connecting to {name} ({host}) with {try_alt['username']}...", end=' ', flush=True)
            dev_alt = {k: v for k, v in try_alt.items() if k != 'name'}
            conn = ConnectHandler(**dev_alt)
            prompt = conn.find_prompt()
            print(f"OK [{prompt}]")
            return conn
        else:
            raise

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
# COMMON COMMAND SETS
# =============================================================================

# L2H-1 full collection (baseline and post-recovery)
L2H1_FULL_CMDS = [
    ("show version | include uptime", "UPTIME"),
    ("show etherchannel summary", "ALL ETHERCHANNELS"),
    ("show etherchannel 40 summary", "ETHERCHANNEL 40 SUMMARY"),
    ("show etherchannel 41 summary", "ETHERCHANNEL 41 SUMMARY"),
    ("show interfaces Port-channel40", "Po40 INTERFACE"),
    ("show interfaces Port-channel40 human-readable", "Po40 INTERFACE (human-readable)"),
    ("show interfaces Port-channel41", "Po41 INTERFACE"),
    ("show interfaces Port-channel41 human-readable", "Po41 INTERFACE (human-readable)"),
    ("show interfaces TenGigabitEthernet4/0/1", "Te4/0/1 (Po40 member)"),
    ("show interfaces TenGigabitEthernet4/0/1 human-readable", "Te4/0/1 (Po40 member) (human-readable)"),
    ("show interfaces TenGigabitEthernet4/0/2", "Te4/0/2 (Po40 member)"),
    ("show interfaces TenGigabitEthernet4/0/2 human-readable", "Te4/0/2 (Po40 member) (human-readable)"),
    ("show interfaces TenGigabitEthernet4/0/3", "Te4/0/3 (Po41 member)"),
    ("show interfaces TenGigabitEthernet4/0/3 human-readable", "Te4/0/3 (Po41 member) (human-readable)"),
    ("show interfaces TenGigabitEthernet4/0/4", "Te4/0/4 (Po41 member)"),
    ("show interfaces TenGigabitEthernet4/0/4 human-readable", "Te4/0/4 (Po41 member) (human-readable)"),
    ("show lacp 40 neighbor", "LACP 40 NEIGHBOR"),
    ("show lacp 41 neighbor", "LACP 41 NEIGHBOR"),
    ("show ip ospf neighbor", "OSPF NEIGHBORS"),
    ("show ip route ospf | include 192.168", "OSPF ROUTES (ECMP paths)"),
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

# L2H-1 during-failure (Po41 DOWN, Po40 UP)
L2H1_DURING_CMDS = [
    ("show etherchannel summary", "ALL ETHERCHANNELS"),
    ("show etherchannel 40 summary", "ETHERCHANNEL 40 (UP)"),
    ("show etherchannel 41 summary", "ETHERCHANNEL 41 (DOWN)"),
    ("show interfaces Port-channel40", "Po40 INTERFACE (UP)"),
    ("show interfaces Port-channel40 human-readable", "Po40 INTERFACE (UP) (human-readable)"),
    ("show interfaces Port-channel41", "Po41 INTERFACE (DOWN)"),
    ("show interfaces Port-channel41 human-readable", "Po41 INTERFACE (DOWN) (human-readable)"),
    ("show interfaces TenGigabitEthernet4/0/1", "Te4/0/1 (Po40 - UP)"),
    ("show interfaces TenGigabitEthernet4/0/1 human-readable", "Te4/0/1 (Po40 - UP) (human-readable)"),
    ("show interfaces TenGigabitEthernet4/0/2", "Te4/0/2 (Po40 - UP)"),
    ("show interfaces TenGigabitEthernet4/0/2 human-readable", "Te4/0/2 (Po40 - UP) (human-readable)"),
    ("show interfaces TenGigabitEthernet4/0/3", "Te4/0/3 (DOWN)"),
    ("show interfaces TenGigabitEthernet4/0/3 human-readable", "Te4/0/3 (DOWN) (human-readable)"),
    ("show interfaces TenGigabitEthernet4/0/4", "Te4/0/4 (DOWN)"),
    ("show interfaces TenGigabitEthernet4/0/4 human-readable", "Te4/0/4 (DOWN) (human-readable)"),
    ("show lacp 40 counters", "LACP 40 COUNTERS"),
    ("show lacp 41 counters", "LACP 41 COUNTERS"),
    ("show ip ospf neighbor", "OSPF NEIGHBORS (BC1 MUST BE FULL)"),
    ("show ip route ospf | include 192.168", "OSPF ROUTES (via Po40 only)"),
    ("show bfd neighbors", "BFD SESSIONS (BC1 MUST BE UP)"),
    ("show lisp session", "LISP SESSIONS"),
    ("show ip route summary", "ROUTE SUMMARY"),
    ("show cts role-based counters", "CTS COUNTERS"),
    # -- Multicast verification during failure --
    ("show ip mroute vrf BMS1 225.1.1.1", "MROUTE 225.1.1.1 (MUST still have entries)"),
    ("show ip mfib vrf BMS1 225.1.1.1", "MFIB 225.1.1.1 HW COUNTERS (check forwarding)"),
    ("show ip pim vrf BMS1 neighbor", "PIM NEIGHBORS (VRF BMS1)"),
    ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (group 225.1.1.1)"),
    ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301"),
    ("show logging | include OSPF|LACP|BFD", "SYSLOG (filtered)"),
]

# BC1 commands (Po40 side - stays UP during this test)
BC1_BASELINE_CMDS = [
    ("show version | include uptime", "UPTIME"),
    ("show etherchannel 40 summary", "ETHERCHANNEL 40 SUMMARY"),
    ("show interfaces Port-channel40", "Po40 INTERFACE"),
    ("show interfaces Port-channel40 human-readable", "Po40 INTERFACE (human-readable)"),
    ("show lacp 40 counters", "LACP COUNTERS"),
    ("show ip ospf neighbor", "OSPF NEIGHBORS"),
    ("show ip bgp summary", "BGP SUMMARY"),
    ("show lisp session", "LISP SESSIONS"),
    ("show bfd neighbors", "BFD SESSIONS"),
    # -- Multicast --
    ("show ip mroute vrf BMS1 225.1.1.1", "MROUTE 225.1.1.1 (VRF BMS1)"),
    ("show ip pim vrf BMS1 neighbor", "PIM NEIGHBORS (VRF BMS1)"),
]

BC1_DURING_CMDS = [
    ("show etherchannel 40 summary", "ETHERCHANNEL 40 (MUST BE UP)"),
    ("show interfaces Port-channel40", "Po40 INTERFACE (MUST BE UP)"),
    ("show interfaces Port-channel40 human-readable", "Po40 INTERFACE (MUST BE UP) (human-readable)"),
    ("show lacp 40 counters", "LACP COUNTERS"),
    ("show ip ospf neighbor | include 192.168.102.40", "OSPF TO L2H-1 (MUST BE FULL)"),
    ("show bfd neighbors | include 192.168.102.40", "BFD TO L2H-1 (MUST BE UP)"),
    ("show lisp session | include 192.168.102.40", "LISP TO L2H-1"),
    ("show ip route ospf | begin Gateway", "OSPF ROUTES (traffic via Po40)"),
    # -- Multicast --
    ("show ip mroute vrf BMS1 225.1.1.1", "MROUTE 225.1.1.1 (MUST still have entries)"),
    ("show ip pim vrf BMS1 neighbor", "PIM NEIGHBORS (VRF BMS1)"),
    ("show logging | include OSPF|LACP|BFD", "SYSLOG (filtered)"),
]

BC1_POST_CMDS = [
    ("show etherchannel 40 summary", "ETHERCHANNEL SUMMARY"),
    ("show interfaces Port-channel40", "Po40 INTERFACE"),
    ("show interfaces Port-channel40 human-readable", "Po40 INTERFACE (human-readable)"),
    ("show lacp 40 counters", "LACP COUNTERS"),
    ("show ip ospf neighbor", "OSPF NEIGHBORS"),
    ("show ip bgp summary", "BGP SUMMARY"),
    ("show lisp session", "LISP SESSIONS"),
    ("show bfd neighbors", "BFD SESSIONS"),
    # -- Multicast --
    ("show ip mroute vrf BMS1 225.1.1.1", "MROUTE 225.1.1.1 (VRF BMS1)"),
    ("show ip pim vrf BMS1 neighbor", "PIM NEIGHBORS (VRF BMS1)"),
    ("show logging | include OSPF|LACP", "SYSLOG (filtered)"),
]

# BC2 commands (Po41 side - goes DOWN during this test)
BC2_BASELINE_CMDS = [
    ("show version | include uptime", "UPTIME"),
    ("show etherchannel 41 summary", "ETHERCHANNEL 41 SUMMARY"),
    ("show interfaces Port-channel41", "Po41 INTERFACE"),
    ("show interfaces Port-channel41 human-readable", "Po41 INTERFACE (human-readable)"),
    ("show lacp 41 counters", "LACP COUNTERS"),
    ("show ip ospf neighbor", "OSPF NEIGHBORS"),
    ("show ip bgp summary", "BGP SUMMARY"),
    ("show lisp session", "LISP SESSIONS"),
    ("show bfd neighbors", "BFD SESSIONS"),
    # -- Multicast --
    ("show ip mroute vrf BMS1 225.1.1.1", "MROUTE 225.1.1.1 (VRF BMS1)"),
    ("show ip pim vrf BMS1 neighbor", "PIM NEIGHBORS (VRF BMS1)"),
]

BC2_DURING_CMDS = [
    ("show etherchannel 41 summary", "ETHERCHANNEL 41 (DOWN)"),
    ("show interfaces Port-channel41 | include line protocol|BW", "Po41 STATUS (DOWN)"),
    ("show interfaces Port-channel41 human-readable", "Po41 INTERFACE (DOWN) (human-readable)"),
    ("show lacp 41 counters", "LACP COUNTERS"),
    ("show ip ospf neighbor | include 192.168.102.40", "OSPF TO L2H-1 (DOWN)"),
    ("show lisp session | include 192.168.102.40", "LISP TO L2H-1"),
    # -- Multicast --
    ("show ip mroute vrf BMS1 225.1.1.1", "MROUTE 225.1.1.1 (may lose L2H-1 path)"),
    ("show ip pim vrf BMS1 neighbor", "PIM NEIGHBORS (VRF BMS1)"),
    ("show logging | include OSPF|LACP", "SYSLOG (filtered)"),
]

BC2_POST_CMDS = [
    ("show etherchannel 41 summary", "ETHERCHANNEL 41 SUMMARY"),
    ("show interfaces Port-channel41", "Po41 INTERFACE"),
    ("show interfaces Port-channel41 human-readable", "Po41 INTERFACE (human-readable)"),
    ("show lacp 41 counters", "LACP COUNTERS"),
    ("show ip ospf neighbor", "OSPF NEIGHBORS"),
    ("show ip bgp summary", "BGP SUMMARY"),
    ("show lisp session", "LISP SESSIONS"),
    ("show bfd neighbors", "BFD SESSIONS"),
    # -- Multicast --
    ("show ip mroute vrf BMS1 225.1.1.1", "MROUTE 225.1.1.1 (VRF BMS1)"),
    ("show ip pim vrf BMS1 neighbor", "PIM NEIGHBORS (VRF BMS1)"),
    ("show logging | include OSPF|LACP", "SYSLOG (filtered)"),
]

# FS2_L2_9300-1 commands (legacy access switch)
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

# FS2_L2_9300-2 commands (legacy access switch)
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
    print("  DUAL-HOMED TOPOLOGY:")
    print("    FS2_L2H-1 --Po40--> FS2_BC1 (192.168.40.0/31) <-- stays UP")
    print("    FS2_L2H-1 --Po41--> FS2_BC2 (192.168.41.0/31) <-- WILL BE SHUT")
    print("    Expected: ECMP load-balancing across both paths")
    print()

    # ---- Step 1.0: Clear logs on all devices ----
    banner("STEP 1.0: CLEARING LOGS ON ALL DEVICES", '-')
    print("  Clearing syslog buffers for clean evidence collection...")
    for dev, alt, name in [(L2H1_TACACS, None, 'L2H-1'), (BC1, None, 'BC1'), (BC2, BC2_ALT, 'BC2'), (L2_9300_1, None, 'L2_9300-1'), (L2_9300_2, None, 'L2_9300-2')]:
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
    print("    3. Check for dead streams (must be 0)")
    print("    4. Clear counters -> wait 60 seconds")
    print("    5. Verify Frame Loss = 0, Loss % = 0.000%")
    print(f"    6. Screenshot: Iter{iteration}_Pre_Spirent_Baseline.png")
    pause("Take Spirent baseline screenshot, then press ENTER")

    # ---- Step 1.2: Catalyst Center ----
    banner("STEP 1.2: CATALYST CENTER - L2H-1 HEALTH", '-')
    print("  ACTION REQUIRED:")
    print("    1. Open CC: https://172.31.229.151")
    print("    2. Provision > Inventory > FS2_L2H_1")
    print("       - Verify: Reachable, Health >= 80%")
    print(f"    3. Screenshot: Iter{iteration}_Pre_CC_L2H1_Health.png")
    print()
    print("    4. Assurance > Health")
    print("       - Record: Network Health, Client Health")
    print(f"    5. Screenshot: Iter{iteration}_Pre_CC_Network_Health.png")
    pause("Take Catalyst Center baseline screenshots, then press ENTER")

    # ---- Step 1.3: L2H-1 CLI Baseline ----
    banner("STEP 1.3: CLI BASELINE - FS2_L2H-1 (172.31.0.194)", '-')
    collect_commands(L2H1_TACACS, L2H1_FULL_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Pre_L2H1_Baseline.txt"))

    # ---- Step 1.4: BC1 CLI Baseline ----
    banner("STEP 1.4: CLI BASELINE - FS2_BC1 (172.31.2.0)", '-')
    collect_commands(BC1, BC1_BASELINE_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Pre_BC1_Baseline.txt"))

    # ---- Step 1.5: BC2 CLI Baseline ----
    banner("STEP 1.5: CLI BASELINE - FS2_BC2 (172.31.2.2)", '-')
    collect_commands(BC2, BC2_BASELINE_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Pre_BC2_Baseline.txt"),
        try_alt=BC2_ALT)

    # ---- Step 1.6: FS2_L2_9300-1 CLI Baseline ----
    banner("STEP 1.6: CLI BASELINE - FS2_L2_9300-1 (172.31.0.179)", '-')
    collect_commands(L2_9300_1, L2_9300_1_BASELINE_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Pre_L2_9300-1_Baseline.txt"))

    # ---- Step 1.7: FS2_L2_9300-2 CLI Baseline ----
    banner("STEP 1.7: CLI BASELINE - FS2_L2_9300-2 (172.31.0.178)", '-')
    collect_commands(L2_9300_2, L2_9300_2_BASELINE_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Pre_L2_9300-2_Baseline.txt"))

    # ---- Phase 1 Gate ----
    banner("PHASE 1 GATE CHECK", '*')
    print("  Verify ALL of the following before proceeding:")
    print("    [ ] Spirent: 0.000% loss, 0 dead streams")
    print("    [ ] CC: L2H-1 health >= 80%, 0 critical alarms")
    print("    [ ] L2H-1: Po40 UP with Te4/0/1(P) + Te4/0/2(P)")
    print("    [ ] L2H-1: Po41 UP with Te4/0/3(P) + Te4/0/4(P)")
    print("    [ ] L2H-1: OSPF FULL to BOTH BC1 (192.168.40.1) and BC2 (192.168.41.1)")
    print("    [ ] L2H-1: BFD UP to both BCs")
    print("    [ ] L2H-1: ECMP routes visible (equal cost via Po40 and Po41)")
    print("    [ ] L2H-1: 2 LISP sessions UP")
    print("    [ ] L2H-1: Multicast mroute 225.1.1.1 present, PIM neighbors UP")
    print("    [ ] BC1: Po40 UP, OSPF FULL to L2H-1")
    print("    [ ] BC2: Po41 UP, OSPF FULL to L2H-1")
    print("    [ ] L2_9300-1: IGMP snooping groups on VLAN 101/1301")
    print("    [ ] L2_9300-2: IGMP snooping groups on VLAN 101/1301")
    print("    [ ] CLI baselines saved (5 files)")
    pause("Confirm all checks PASS, then press ENTER to proceed to PHASE 2")


# =============================================================================
# PHASE 2: FAILURE EVENT - SHUTDOWN Po41 (Te4/0/3 + Te4/0/4)
# =============================================================================

def phase2(iter_dir, iteration):
    banner(f"PHASE 2: FAILURE EVENT - SHUTDOWN Po41 (Iteration {iteration})")
    print(f"  Timestamp: {ts()}")
    print()
    print("  TARGET: TenGigabitEthernet4/0/3 AND TenGigabitEthernet4/0/4 on FS2_L2H-1")
    print("  ACTION: shutdown BOTH Po41 members (Po41 goes DOWN)")
    print()
    print("  EXPECTED BEHAVIOR:")
    print("    X  Po41 goes DOWN (to BC2)")
    print("    OK Po40 stays UP (to BC1)")
    print("    OK OSPF to BC1 remains FULL")
    print("    OK Traffic continues via Po40")
    print()
    print("  NOTE: This is the MIRROR of TC 07-02 retest (which shut Po40).")
    print("  Together they prove dual-homing works in both directions.")
    pause("Ready to SHUTDOWN Po41? Press ENTER to execute")

    # ---- Step 2.1: Execute Shutdown ----
    banner("STEP 2.1: EXECUTING SHUTDOWN OF Po41 MEMBERS", '-')
    conn = connect(L2H1_TACACS)

    try:
        conn.enable()
        print("  Entered enable mode")
    except Exception:
        print("  Already in enable mode or enable not needed")

    shutdown_time = datetime.datetime.now()
    print(f"\n  >>> SHUTDOWN Po41 MEMBERS at {shutdown_time.strftime('%H:%M:%S')} <<<\n")

    config_output = conn.send_config_set([
        'interface range TenGigabitEthernet4/0/3 - 4',
        'shutdown'
    ])
    print(config_output)

    safe_disconnect(conn)
    print("  Disconnected post-shutdown (will reconnect for verification)")

    # ---- Step 2.2: Immediate Verification ----
    banner("STEP 2.2: IMMEDIATE VERIFICATION - Po40 REDUNDANCY CHECK", '-')
    print("  Waiting 5 seconds for convergence, then reconnecting...")
    time.sleep(5)
    print(f"  Verification at: {ts()}")

    conn = connect(L2H1_TACACS)

    sub_banner("show etherchannel summary")
    run_cmd(conn, "show etherchannel summary")

    sub_banner("show interfaces Port-channel41 | status")
    run_cmd(conn, "show interfaces Port-channel41 | include line protocol|BW")

    sub_banner("show interfaces Port-channel40 | status")
    run_cmd(conn, "show interfaces Port-channel40 | include line protocol|BW")

    sub_banner("show ip ospf neighbor")
    ospf_out = run_cmd(conn, "show ip ospf neighbor")

    sub_banner("show bfd neighbors")
    run_cmd(conn, "show bfd neighbors")

    safe_disconnect(conn)

    print()
    print("  !!! CRITICAL VERIFICATION !!!")
    print("  Expected State:")
    print("    X  Po41: DOWN (protocol down) - EXPECTED")
    print("    OK Po40: UP (to BC1) - MUST BE UP")
    print("    X  OSPF to BC2 (192.168.41.1): DOWN - EXPECTED")
    print("    OK OSPF to BC1 (192.168.40.1): FULL - MUST BE FULL")
    print("    OK BFD to BC1: UP - MUST BE UP")
    print()

    if 'FULL' in ospf_out and '192.168.40.1' in ospf_out:
        print("  >>> SUCCESS: OSPF to BC1 is FULL - Po40 providing redundancy!")
    else:
        print("  !!! WARNING: OSPF to BC1 not showing FULL - investigate!")

    # ---- Step 2.3: Spirent Convergence ----
    banner("STEP 2.3: SPIRENT CONVERGENCE MEASUREMENT", '-')
    print("  DUAL-HOMED EXPECTATION: Hitless or sub-second convergence")
    print()
    print("  ACTION REQUIRED:")
    print("    1. Watch Spirent GUI - should show minimal or ZERO loss")
    print("    2. Monitor for 3 minutes to observe convergence behavior")
    print("    3. Record dead streams (expect ZERO or minimal)")
    print(f"    4. Screenshot: Iter{iteration}_During_Spirent_Convergence.png")
    print()
    print("    5. After 3 minutes: STOP TRAFFIC")
    print(f"    6. Export Spirent DB: Iter{iteration}_During_Spirent_DB.tcc")
    print()
    print("    7. Upload to PLA: http://spirent-pla.cisco.com")
    print(f"       - Download Excel: Iter{iteration}_PLA_Convergence_Analysis.xlsx")
    print(f"    8. Screenshot PLA: Iter{iteration}_PLA_Analysis.png")
    pause("Complete Spirent convergence measurement, then press ENTER")

    # ---- Step 2.4: L2H-1 During-Failure CLI ----
    banner("STEP 2.4: L2H-1 DURING-FAILURE CLI", '-')
    collect_commands(L2H1_TACACS, L2H1_DURING_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_During_L2H1_Failure.txt"))

    # ---- Step 2.5: BC1 During-Failure (CRITICAL - must stay UP) ----
    banner("STEP 2.5: BC1 DURING-FAILURE STATUS (Po40 REDUNDANCY)", '-')
    print("  BC1 Po40 MUST remain UP - this validates dual-homing success")
    collect_commands(BC1, BC1_DURING_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_During_BC1_Status.txt"))

    # ---- Step 2.6: BC2 During-Failure ----
    banner("STEP 2.6: BC2 DURING-FAILURE STATUS", '-')
    collect_commands(BC2, BC2_DURING_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_During_BC2_Status.txt"),
        try_alt=BC2_ALT)

    # ---- Step 2.7: FS2_L2_9300-1 During ----
    banner("STEP 2.7: FS2_L2_9300-1 DURING FAILURE (172.31.0.179)", '-')
    collect_commands(L2_9300_1, L2_9300_1_DURING_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_During_L2_9300-1_Status.txt"))

    # ---- Step 2.8: FS2_L2_9300-2 During ----
    banner("STEP 2.8: FS2_L2_9300-2 DURING FAILURE (172.31.0.178)", '-')
    collect_commands(L2_9300_2, L2_9300_2_DURING_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_During_L2_9300-2_Status.txt"))

    # ---- Step 2.9: CC During-Failure ----
    banner("STEP 2.9: CATALYST CENTER DURING-FAILURE", '-')
    print("  ACTION REQUIRED:")
    print("    1. Provision > Inventory > FS2_L2H_1")
    print("       - Expected: Still Reachable (via Po40)")
    print(f"    2. Screenshot: Iter{iteration}_During_CC_L2H1_Status.png")
    pause("Take CC during-failure screenshot, then press ENTER to proceed to RECOVERY")


# =============================================================================
# PHASE 3: RECOVERY - RESTORE Po41
# =============================================================================

def phase3(iter_dir, iteration):
    banner(f"PHASE 3: RECOVERY - RESTORE Po41 (Iteration {iteration})")
    print(f"  Timestamp: {ts()}")
    print()
    print("  ACTION: no shutdown Te4/0/3-4 on L2H-1 (restore Po41)")
    print("  EXPECTED: Po41 restores, ECMP resumes across both Po40 and Po41")
    pause("Ready to RESTORE Po41? Press ENTER to execute")

    # ---- Step 3.1: Execute Recovery ----
    banner("STEP 3.1: EXECUTING RECOVERY (no shutdown Po41)", '-')
    conn = connect(L2H1_TACACS)

    try:
        conn.enable()
        print("  Entered enable mode")
    except Exception:
        print("  Already in enable mode or enable not needed")

    recovery_time = datetime.datetime.now()
    print(f"\n  >>> NO SHUTDOWN Po41 at {recovery_time.strftime('%H:%M:%S')} <<<\n")

    config_output = conn.send_config_set([
        'interface range TenGigabitEthernet4/0/3 - 4',
        'no shutdown'
    ])
    print(config_output)

    # ---- Step 3.2: Monitor Po41 Rebundle ----
    banner("STEP 3.2: MONITORING PORT-CHANNEL 41 REBUNDLE", '-')
    print("  Checking every 5s for up to 60s...")
    rebundled = False
    for t in range(5, 65, 5):
        time.sleep(5)
        now = datetime.datetime.now().strftime('%H:%M:%S')
        try:
            result = conn.send_command("show etherchannel 41 summary | include Po41|Te4", read_timeout=15)
        except Exception:
            safe_disconnect(conn)
            conn = connect(L2H1_TACACS)
            result = conn.send_command("show etherchannel 41 summary | include Po41|Te4", read_timeout=15)
        status = result.strip()
        print(f"  T+{t:2d}s ({now}): {status}")
        if 'Te4/0/3(P)' in status and 'Te4/0/4(P)' in status and not rebundled:
            rebundled = True
            print(f"  >>> Po41 FULLY BUNDLED in <= {t} seconds <<<")

    if not rebundled:
        print("  WARNING: Po41 not fully bundled after 60s!")
        try:
            result = conn.send_command("show etherchannel 41 summary", read_timeout=15)
            print(result)
        except Exception:
            pass

    # ---- Step 3.3: Monitor OSPF to BC2 ----
    banner("STEP 3.3: MONITORING OSPF ADJACENCY TO BC2 RESTORATION", '-')
    print("  Checking every 10s for up to 60s...")
    ospf_full = False
    for t in range(10, 70, 10):
        time.sleep(10)
        now = datetime.datetime.now().strftime('%H:%M:%S')
        try:
            result = conn.send_command("show ip ospf neighbor | include 192.168.41.1", read_timeout=15)
        except Exception:
            safe_disconnect(conn)
            conn = connect(L2H1_TACACS)
            result = conn.send_command("show ip ospf neighbor | include 192.168.41.1", read_timeout=15)
        status = result.strip()
        print(f"  T+{t:2d}s ({now}): {status}")
        if 'FULL' in status and not ospf_full:
            ospf_full = True
            print(f"  >>> OSPF TO BC2 FULL in <= {t} seconds <<<")

    if not ospf_full:
        print("  WARNING: OSPF to BC2 not FULL after 60s!")
        try:
            print(conn.send_command("show ip ospf neighbor", read_timeout=15))
        except Exception:
            pass

    # ---- Step 3.4: Verify ECMP ----
    banner("STEP 3.4: VERIFY ECMP LOAD-BALANCING RESTORATION", '-')
    time.sleep(5)
    try:
        ecmp_routes = run_cmd(conn, "show ip route ospf | include 192.168")
        if 'Port-channel40' in ecmp_routes and 'Port-channel41' in ecmp_routes:
            print("\n  >>> ECMP RESTORED (routes via both Po40 and Po41) <<<")
        else:
            print("\n  !!! WARNING: ECMP not showing both port-channels")

        print()
        run_cmd(conn, "show bfd neighbors")
        print()
        lisp = run_cmd(conn, "show lisp session")
        if 'Up' in lisp:
            print("  >>> LISP SESSIONS UP <<<")
    except Exception:
        print("  Connection lost - will capture in post-recovery CLI")

    safe_disconnect(conn)

    # ---- Step 3.5: Spirent Post-Recovery ----
    banner("STEP 3.5: SPIRENT POST-RECOVERY VALIDATION", '-')
    print("  ACTION REQUIRED:")
    print("    1. START Spirent traffic (if stopped)")
    print("    2. Clear counters, wait 60 seconds")
    print("    3. Verify: Loss % = 0.000%, Dead Streams = 0")
    print(f"    4. Screenshot: Iter{iteration}_Post_Spirent_Restored.png")
    pause("Take Spirent post-recovery screenshot, then press ENTER")

    # ---- Step 3.6-3.8: Post-Recovery CLI ----
    banner("STEP 3.6: L2H-1 FULL POST-RECOVERY VALIDATION", '-')
    collect_commands(L2H1_TACACS, L2H1_FULL_CMDS + [
        ("show logging | include OSPF|LACP|BFD", "SYSLOG (filtered)"),
    ], os.path.join(iter_dir, f"Iter{iteration}_Post_L2H1_Validation.txt"))

    banner("STEP 3.7: BC1 POST-RECOVERY VALIDATION", '-')
    collect_commands(BC1, BC1_POST_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Post_BC1_Validation.txt"))

    banner("STEP 3.8: BC2 POST-RECOVERY VALIDATION", '-')
    collect_commands(BC2, BC2_POST_CMDS,
        os.path.join(iter_dir, f"Iter{iteration}_Post_BC2_Validation.txt"),
        try_alt=BC2_ALT)

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
    print(f"    2. Screenshot: Iter{iteration}_Post_CC_L2H1_Health.png")
    print("    3. Assurance > Health - Verify >= 80%")
    print(f"    4. Screenshot: Iter{iteration}_Post_CC_Network_Health.png")
    pause("Take CC post-recovery screenshots, then press ENTER")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='TC 07-03 - Link Failure L2 Border Po41 to Other BC')
    parser.add_argument('--iter', type=int, default=1, choices=[1, 2, 3],
                        help='Iteration number (1, 2, or 3)')
    args = parser.parse_args()
    iteration = args.iter

    banner("TC 07-03: Link Failure L2 Border Po41 - DUAL-HOMED TOPOLOGY")
    print(f"  Iteration: {iteration}")
    print(f"  Start Time: {ts()}")
    print(f"  Primary DUT: FS2_L2H-1 (172.31.0.194)")
    print(f"  Target: Po41 (Te4/0/3-4) to FS2_BC2")
    print(f"  Redundancy: Po40 (Te4/0/1-2) to FS2_BC1")
    print()
    print("  TOPOLOGY:")
    print("    FS2_L2H-1 --Po40--> FS2_BC1 (192.168.40.0/31) <-- REDUNDANT PATH")
    print("    FS2_L2H-1 --Po41--> FS2_BC2 (192.168.41.0/31) <-- WILL BE SHUT DOWN")
    print()
    print("  This is the mirror of TC 07-02 retest:")
    print("    TC 07-02 retest: Shut Po40, Po41 provides redundancy")
    print("    TC 07-03:        Shut Po41, Po40 provides redundancy")
    print()

    iter_dir = os.path.join(TC_DIR, f"Iter{iteration}_CLI")
    os.makedirs(iter_dir, exist_ok=True)
    print(f"  Output directory: {iter_dir}")

    pause(f"Ready to begin Iteration {iteration}? Ensure VPN connected and devices reachable")

    phase1(iter_dir, iteration)
    phase2(iter_dir, iteration)
    phase3(iter_dir, iteration)

    # ---- Summary ----
    banner(f"ITERATION {iteration} COMPLETE")
    print(f"  End Time: {ts()}")
    print()
    print("  RESULTS CHECKLIST:")
    print("    [ ] Po41 went DOWN during shutdown (EXPECTED)")
    print("    [ ] Po40 REMAINED UP during Po41 failure (CRITICAL)")
    print("    [ ] OSPF to BC2 went DOWN (EXPECTED)")
    print("    [ ] OSPF to BC1 stayed FULL (CRITICAL)")
    print("    [ ] BFD to BC1 stayed UP (CRITICAL)")
    print("    [ ] Multicast: mroute 225.1.1.1 present in VRF BMS1 during failure")
    print("    [ ] Multicast: MFIB HW counters incrementing (forwarding active)")
    print("    [ ] Multicast: PIM neighbors UP via Po40 during failure")
    print("    [ ] Multicast: IGMP snooping group 225.1.1.1 on VLAN 101")
    print("    [ ] L2_9300-1: STP/IGMP snooping state captured")
    print("    [ ] L2_9300-2: STP/IGMP snooping state captured")
    print("    [ ] Spirent: Minimal packet loss or HITLESS (unicast + multicast)")
    print("    [ ] Po41 restored with both members bundled")
    print("    [ ] OSPF to BC2 restored to FULL")
    print("    [ ] ECMP resumed (routes via both Po40 and Po41)")
    print("    [ ] Multicast: mroute/MFIB/PIM/IGMP restored to baseline")
    print()
    print("  CLI EVIDENCE:")
    for f in sorted(os.listdir(iter_dir)):
        fpath = os.path.join(iter_dir, f)
        size = os.path.getsize(fpath)
        print(f"    {f} ({size:,} bytes)")
    print()

    if iteration < 3:
        print(f"  Next: python3 run_tc_07-03.py --iter {iteration + 1}")
    else:
        print("  ALL 3 ITERATIONS COMPLETE.")
        print("  Next: Generate Word report and CXTM results.")

    print()


if __name__ == '__main__':
    main()
