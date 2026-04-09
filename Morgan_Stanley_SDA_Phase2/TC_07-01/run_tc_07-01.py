#!/usr/bin/env python3
"""
TC 07-01: Link Failure from L2 Border PortChannel Member to Fabric BC Node
Interactive execution script - pauses at each step for GUI screenshot capture.

Version: 2.0
Date:    April 8, 2026

Changelog:
  v1.0 (April 6, 2026)  - Initial release: 3-device collection (L2H-1, BC1, BC2),
                           LACP member shutdown (Te4/0/1), Po40 stays UP
  v2.0 (April 8, 2026)  - Added FS2_L2_9300-1/9300-2 legacy access switch collection
                           (STP, IGMP snooping, MAC tables, topology change notifications)
                         - Added multicast verification on L2H-1/BC1/BC2 (PIM neighbors,
                           mroute 225.1.1.1, MFIB HW counters, IGMP snooping VRF BMS1)
                         - Added robustness improvements (connection retry, error handling)
                         - 675 lines, 5-device collection

Usage: python3 run_tc_07-01.py [--iter 1|2|3]
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

L2H1 = {
    'device_type': 'cisco_ios',
    'host': '172.31.0.194',
    'username': 'admin1',
    'password': 'CXlabs.123',
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
    """Pause and wait for tester to press Enter."""
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
    """Connect to device, return netmiko connection."""
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
            print(f"FAILED, trying {try_alt['username']}...")
            print(f"  Connecting to {name} ({host}) with {try_alt['username']}...", end=' ', flush=True)
            dev_alt = {k: v for k, v in try_alt.items() if k != 'name'}
            conn = ConnectHandler(**dev_alt)
            prompt = conn.find_prompt()
            print(f"OK [{prompt}]")
            return conn
        else:
            raise

def run_and_print(conn, cmd):
    """Run command, print output, return output."""
    try:
        output = conn.send_command(cmd, read_timeout=30)
    except Exception as e:
        output = f"ERROR running command: {e}"
    print(output)
    return output

def collect_commands(device_info, commands, filename, try_alt=None):
    """Connect to device, run commands, save to file, disconnect."""
    conn = connect(device_info, try_alt=try_alt)
    output_all = ""
    for cmd, label in commands:
        sub_banner(f"{label}: {cmd}")
        out = run_and_print(conn, cmd)
        output_all += f"\n--- {label}: {cmd} ---\n{out}\n"
    safe_disconnect(conn)
    save_output(filename, output_all)

def save_output(filename, content):
    """Save content to file in the CLI directory."""
    with open(filename, 'w') as f:
        f.write(f"Collected: {ts()}\n{'='*60}\n\n")
        f.write(content)
    size = os.path.getsize(filename)
    print(f"  Saved: {os.path.basename(filename)} ({size:,} bytes)")


# =============================================================================
# PHASE 1: STEADY STATE BASELINE
# =============================================================================

def phase1(iter_dir, iteration):
    banner(f"PHASE 1: STEADY STATE BASELINE  (Iteration {iteration})")
    print(f"  Timestamp: {ts()}")

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
    conn = connect(L2H1)

    commands = [
        ("show version | include uptime", "UPTIME"),
        ("show etherchannel 40 summary", "ETHERCHANNEL SUMMARY"),
        ("show etherchannel 40 detail", "ETHERCHANNEL DETAIL"),
        ("show interfaces Port-channel40", "Po40 INTERFACE"),
        ("show interfaces TenGigabitEthernet4/0/1", "Te4/0/1 INTERFACE"),
        ("show interfaces TenGigabitEthernet4/0/2", "Te4/0/2 INTERFACE"),
        ("show lacp 40 counters", "LACP COUNTERS"),
        ("show lacp 40 neighbor", "LACP NEIGHBOR"),
        ("show ip ospf neighbor", "OSPF NEIGHBORS"),
        ("show lisp session", "LISP SESSIONS"),
        ("show ip route summary", "ROUTE SUMMARY"),
        ("show cts role-based counters", "CTS COUNTERS"),
        # -- Multicast --
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

    output_all = ""
    for cmd, label in commands:
        sub_banner(f"{label}: {cmd}")
        out = run_and_print(conn, cmd)
        output_all += f"\n--- {label}: {cmd} ---\n{out}\n"

    safe_disconnect(conn)
    save_output(os.path.join(iter_dir, f"Iter{iteration}_Pre_L2H1_Baseline.txt"), output_all)

    # ---- Step 1.4: BC1 CLI Baseline ----
    banner("STEP 1.4: CLI BASELINE - FS2_BC1 (172.31.2.0)", '-')
    conn = connect(BC1)

    commands = [
        ("show version | include uptime", "UPTIME"),
        ("show etherchannel 40 summary", "ETHERCHANNEL SUMMARY"),
        ("show interfaces Port-channel40 | include line protocol|BW|packets input|packets output", "Po40 KEY STATS"),
        ("show lacp 40 counters", "LACP COUNTERS"),
        ("show ip ospf neighbor", "OSPF NEIGHBORS"),
        ("show ip bgp summary", "BGP SUMMARY"),
        ("show lisp session", "LISP SESSIONS"),
        # -- Multicast --
        ("show ip mroute vrf BMS1 225.1.1.1", "MROUTE 225.1.1.1 (VRF BMS1)"),
        ("show ip pim vrf BMS1 neighbor", "PIM NEIGHBORS (VRF BMS1)"),
    ]

    output_all = ""
    for cmd, label in commands:
        sub_banner(f"{label}: {cmd}")
        out = run_and_print(conn, cmd)
        output_all += f"\n--- {label}: {cmd} ---\n{out}\n"

    safe_disconnect(conn)
    save_output(os.path.join(iter_dir, f"Iter{iteration}_Pre_BC1_Baseline.txt"), output_all)

    # ---- Step 1.5: FS2_L2_9300-1 CLI Baseline ----
    banner("STEP 1.5: CLI BASELINE - FS2_L2_9300-1 (172.31.0.179)", '-')
    collect_commands(L2_9300_1, [
        ("show version | include uptime", "UPTIME"),
        ("show interfaces trunk", "ALL TRUNKS"),
        ("show spanning-tree vlan 101", "STP VLAN 101"),
        ("show spanning-tree vlan 1301", "STP VLAN 1301"),
        ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
        ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
        ("show cdp neighbors", "CDP NEIGHBORS"),
        ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (BMS1)"),
        ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301 (EUT)"),
    ], os.path.join(iter_dir, f"Iter{iteration}_Pre_L2_9300-1_Baseline.txt"))

    # ---- Step 1.6: FS2_L2_9300-2 CLI Baseline ----
    banner("STEP 1.6: CLI BASELINE - FS2_L2_9300-2 (172.31.0.178)", '-')
    collect_commands(L2_9300_2, [
        ("show version | include uptime", "UPTIME"),
        ("show interfaces trunk", "ALL TRUNKS"),
        ("show spanning-tree vlan 101", "STP VLAN 101"),
        ("show spanning-tree vlan 1301", "STP VLAN 1301"),
        ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
        ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
        ("show cdp neighbors", "CDP NEIGHBORS"),
        ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (BMS1)"),
        ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301 (EUT)"),
    ], os.path.join(iter_dir, f"Iter{iteration}_Pre_L2_9300-2_Baseline.txt"))

    # ---- Phase 1 Gate ----
    banner("PHASE 1 GATE CHECK", '*')
    print("  Verify ALL of the following before proceeding:")
    print("    [ ] Spirent: 0.000% loss, 0 dead streams")
    print("    [ ] CC: L2H-1 health >= 80%, 0 critical alarms")
    print("    [ ] CC: Network health >= 80%")
    print("    [ ] L2H-1: Po40 UP, Te4/0/1(P) + Te4/0/2(P)")
    print("    [ ] L2H-1: 2 LISP sessions UP, OSPF FULL to BC1")
    print("    [ ] L2H-1: Multicast mroute 225.1.1.1 present, PIM neighbors UP")
    print("    [ ] BC1: Po40 UP, Fif1/0/13(P) + Fif1/0/14(P)")
    print("    [ ] L2_9300-1: IGMP snooping groups on VLAN 101/1301")
    print("    [ ] L2_9300-2: IGMP snooping groups on VLAN 101/1301")
    print("    [ ] Screenshots captured (3 total)")
    print("    [ ] CLI baselines saved (4 files)")
    pause("Confirm all checks PASS, then press ENTER to proceed to PHASE 2 (FAILURE)")


# =============================================================================
# PHASE 2: FAILURE EVENT
# =============================================================================

def phase2(iter_dir, iteration):
    banner(f"PHASE 2: FAILURE EVENT - SHUTDOWN Te4/0/1  (Iteration {iteration})")
    print(f"  Timestamp: {ts()}")
    print()
    print("  TARGET: TenGigabitEthernet4/0/1 on FS2_L2H-1")
    print("  ACTION: shutdown (LACP member removal)")
    print("  EXPECTED: Po40 stays UP with Te4/0/2 only, BW drops to 10G")
    pause("Ready to SHUTDOWN Te4/0/1? Press ENTER to execute")

    # ---- Step 2.1: Execute Shutdown ----
    banner("STEP 2.1: EXECUTING SHUTDOWN", '-')
    conn = connect(L2H1)

    shutdown_time = datetime.datetime.now()
    print(f"\n  >>> SHUTDOWN EXECUTED at {shutdown_time.strftime('%H:%M:%S')} <<<\n")

    config_output = conn.send_config_set([
        'interface TenGigabitEthernet4/0/1',
        'shutdown'
    ])
    print(config_output)

    # ---- Step 2.2: Immediate Verification ----
    banner("STEP 2.2: IMMEDIATE VERIFICATION", '-')
    time.sleep(3)
    print(f"  Verification at: {ts()}")

    sub_banner("show etherchannel 40 summary")
    run_and_print(conn, "show etherchannel 40 summary")

    sub_banner("show interfaces Port-channel40 | key lines")
    run_and_print(conn, "show interfaces Port-channel40 | include line protocol|BW|Members")

    sub_banner("show interfaces Te4/0/1 | status")
    run_and_print(conn, "show interfaces TenGigabitEthernet4/0/1 | include line protocol")

    sub_banner("show interfaces Te4/0/2 | status")
    run_and_print(conn, "show interfaces TenGigabitEthernet4/0/2 | include line protocol")

    print()
    print("  VERIFY: Po40 should be UP with only Te4/0/2 bundled.")
    print("  VERIFY: BW should be 10000000 Kbit (10G, halved).")

    # ---- Step 2.3: Spirent Monitoring ----
    banner("STEP 2.3: SPIRENT TRAFFIC MONITORING", '-')
    print("  ACTION REQUIRED:")
    print("    1. Check Spirent GUI NOW - monitor for packet loss")
    print("    2. Watch for 2-3 minutes")
    print("    3. Expected: 0.000% loss (hitless LACP member removal)")
    print()
    print("    IF LOSS > 0.001%:")
    print("      a. STOP traffic")
    print("      b. Export Spirent DB (.tcc)")
    print("      c. Upload to PLA: http://spirent-pla.cisco.com")
    print()
    print(f"    4. Screenshot: Iter{iteration}_During_Spirent_Monitor.png")
    pause("Take Spirent during-failure screenshot, then press ENTER")

    # ---- Step 2.4: L2H-1 During-Failure CLI ----
    banner("STEP 2.4: L2H-1 DURING-FAILURE CLI", '-')

    commands = [
        ("show etherchannel 40 summary", "ETHERCHANNEL SUMMARY"),
        ("show etherchannel 40 detail", "ETHERCHANNEL DETAIL"),
        ("show interfaces Port-channel40", "Po40 INTERFACE"),
        ("show interfaces TenGigabitEthernet4/0/1", "Te4/0/1 INTERFACE (DOWN)"),
        ("show interfaces TenGigabitEthernet4/0/2", "Te4/0/2 INTERFACE (SURVIVING)"),
        ("show lacp 40 counters", "LACP COUNTERS"),
        ("show ip ospf neighbor", "OSPF NEIGHBORS"),
        ("show lisp session", "LISP SESSIONS"),
        ("show ip route summary", "ROUTE SUMMARY"),
        ("show cts role-based counters", "CTS COUNTERS"),
        # -- Multicast during failure --
        ("show ip mroute vrf BMS1 225.1.1.1", "MROUTE 225.1.1.1 (MUST still have entries)"),
        ("show ip mfib vrf BMS1 225.1.1.1", "MFIB 225.1.1.1 HW COUNTERS (check forwarding)"),
        ("show ip pim vrf BMS1 neighbor", "PIM NEIGHBORS (VRF BMS1)"),
        ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (group 225.1.1.1)"),
        ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301"),
    ]

    output_all = ""
    for cmd, label in commands:
        sub_banner(f"{label}: {cmd}")
        out = run_and_print(conn, cmd)
        output_all += f"\n--- {label}: {cmd} ---\n{out}\n"

    safe_disconnect(conn)
    save_output(os.path.join(iter_dir, f"Iter{iteration}_During_L2H1_Failure.txt"), output_all)

    # ---- Step 2.5: BC1 During-Failure ----
    banner("STEP 2.5: BC1 DURING-FAILURE STATUS", '-')
    conn = connect(BC1)

    commands = [
        ("show etherchannel 40 summary", "ETHERCHANNEL SUMMARY"),
        ("show interfaces Port-channel40 | include line protocol|BW|Members", "Po40 KEY STATS"),
        ("show lacp 40 counters", "LACP COUNTERS"),
        ("show ip ospf neighbor | include Port-channel40", "OSPF TO L2H-1"),
        ("show lisp session | include 192.168.102.40", "LISP TO L2H-1"),
        # -- Multicast --
        ("show ip mroute vrf BMS1 225.1.1.1", "MROUTE 225.1.1.1 (VRF BMS1)"),
        ("show ip pim vrf BMS1 neighbor", "PIM NEIGHBORS (VRF BMS1)"),
    ]

    output_all = ""
    for cmd, label in commands:
        sub_banner(f"{label}: {cmd}")
        out = run_and_print(conn, cmd)
        output_all += f"\n--- {label}: {cmd} ---\n{out}\n"

    safe_disconnect(conn)
    save_output(os.path.join(iter_dir, f"Iter{iteration}_During_BC1_Status.txt"), output_all)

    # ---- Step 2.6: FS2_L2_9300-1 During ----
    banner("STEP 2.6: FS2_L2_9300-1 DURING FAILURE (172.31.0.179)", '-')
    collect_commands(L2_9300_1, [
        ("show interfaces trunk", "TRUNKS"),
        ("show spanning-tree vlan 101", "STP VLAN 101 (topology change?)"),
        ("show spanning-tree vlan 1301", "STP VLAN 1301 (topology change?)"),
        ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
        ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
        ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101"),
        ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301"),
        ("show logging | include LINK|UPDOWN|LINEPROTO|STP|TCN", "SYSLOG (filtered)"),
    ], os.path.join(iter_dir, f"Iter{iteration}_During_L2_9300-1_Status.txt"))

    # ---- Step 2.7: FS2_L2_9300-2 During ----
    banner("STEP 2.7: FS2_L2_9300-2 DURING FAILURE (172.31.0.178)", '-')
    collect_commands(L2_9300_2, [
        ("show interfaces trunk", "TRUNKS"),
        ("show spanning-tree vlan 101", "STP VLAN 101 (topology change?)"),
        ("show spanning-tree vlan 1301", "STP VLAN 1301 (topology change?)"),
        ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
        ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
        ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101"),
        ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301"),
        ("show logging | include LINK|UPDOWN|LINEPROTO|STP|TCN", "SYSLOG (filtered)"),
    ], os.path.join(iter_dir, f"Iter{iteration}_During_L2_9300-2_Status.txt"))

    # ---- Step 2.8: CC During-Failure ----
    banner("STEP 2.8: CATALYST CENTER DURING-FAILURE", '-')
    print("  ACTION REQUIRED:")
    print("    1. Provision > Inventory > FS2_L2H_1")
    print("       - Record: Reachability, Health Score")
    print(f"    2. Screenshot: Iter{iteration}_During_CC_L2H1_Status.png")
    pause("Take CC during-failure screenshot, then press ENTER to proceed to RECOVERY")


# =============================================================================
# PHASE 3: RECOVERY
# =============================================================================

def phase3(iter_dir, iteration):
    banner(f"PHASE 3: RECOVERY - RESTORE Te4/0/1  (Iteration {iteration})")
    print(f"  Timestamp: {ts()}")
    print()
    print("  ACTION: no shutdown Te4/0/1 (LACP member re-add)")
    print("  EXPECTED: Te4/0/1 re-bundles into Po40, BW restored to 20G")
    pause("Ready to RESTORE Te4/0/1? Press ENTER to execute")

    # ---- Step 3.1: Execute Recovery ----
    banner("STEP 3.1: EXECUTING RECOVERY (no shutdown)", '-')
    conn = connect(L2H1)

    recovery_time = datetime.datetime.now()
    print(f"\n  >>> NO SHUTDOWN EXECUTED at {recovery_time.strftime('%H:%M:%S')} <<<\n")

    config_output = conn.send_config_set([
        'interface TenGigabitEthernet4/0/1',
        'no shutdown'
    ])
    print(config_output)

    # ---- Step 3.2: Monitor Rebundle ----
    banner("STEP 3.2: MONITORING LACP REBUNDLE", '-')
    rebundled = False
    for wait_total in [5, 10, 15, 20, 30]:
        time.sleep(5)
        now = datetime.datetime.now().strftime('%H:%M:%S')
        result = conn.send_command("show etherchannel 40 summary | include Po40|Te4")
        status = result.strip()
        print(f"  T+{wait_total:2d}s ({now}): {status}")
        if 'Te4/0/1(P)' in status and 'Te4/0/2(P)' in status:
            if not rebundled:
                rebundle_time = wait_total
                rebundled = True
                print(f"  >>> Te4/0/1 REBUNDLED in <= {rebundle_time} seconds <<<")

    if not rebundled:
        print("  WARNING: Te4/0/1 has NOT rebundled after 30 seconds!")
        print("  Waiting an additional 30 seconds...")
        time.sleep(30)
        result = conn.send_command("show etherchannel 40 summary | include Po40|Te4")
        print(f"  T+60s: {result.strip()}")

    # ---- Step 3.3: Spirent Validation ----
    banner("STEP 3.3: SPIRENT POST-RECOVERY VALIDATION", '-')
    print("  ACTION REQUIRED:")
    print("    1. Check Spirent GUI - verify 0.000% loss")
    print("    2. Verify 0 dead streams")
    print("    3. If traffic was stopped: restart, clear counters, wait 60s")
    print(f"    4. Screenshot: Iter{iteration}_Post_Spirent_Restored.png")
    pause("Take Spirent post-recovery screenshot, then press ENTER")

    # ---- Step 3.4: Full L2H-1 Post-Recovery Validation ----
    banner("STEP 3.4: L2H-1 FULL POST-RECOVERY VALIDATION", '-')

    commands = [
        ("show etherchannel 40 summary", "ETHERCHANNEL SUMMARY"),
        ("show etherchannel 40 detail", "ETHERCHANNEL DETAIL"),
        ("show interfaces Port-channel40", "Po40 INTERFACE"),
        ("show interfaces TenGigabitEthernet4/0/1", "Te4/0/1 INTERFACE"),
        ("show interfaces TenGigabitEthernet4/0/2", "Te4/0/2 INTERFACE"),
        ("show lacp 40 counters", "LACP COUNTERS"),
        ("show lacp 40 neighbor", "LACP NEIGHBOR"),
        ("show ip ospf neighbor", "OSPF NEIGHBORS"),
        ("show lisp session", "LISP SESSIONS"),
        ("show ip route summary", "ROUTE SUMMARY"),
        ("show cts role-based counters", "CTS COUNTERS"),
        # -- Multicast --
        ("show ip mroute vrf BMS1 225.1.1.1", "MROUTE 225.1.1.1 (VRF BMS1)"),
        ("show ip mfib vrf BMS1 225.1.1.1", "MFIB 225.1.1.1 HW COUNTERS (VRF BMS1)"),
        ("show ip pim vrf BMS1 neighbor", "PIM NEIGHBORS (VRF BMS1)"),
        ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (restored)"),
        ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301 (restored)"),
    ]

    output_all = ""
    for cmd, label in commands:
        sub_banner(f"{label}: {cmd}")
        out = run_and_print(conn, cmd)
        output_all += f"\n--- {label}: {cmd} ---\n{out}\n"

    safe_disconnect(conn)
    save_output(os.path.join(iter_dir, f"Iter{iteration}_Post_L2H1_Validation.txt"), output_all)

    # ---- Step 3.5: BC1 Post-Recovery ----
    banner("STEP 3.5: BC1 FULL POST-RECOVERY VALIDATION", '-')
    conn = connect(BC1)

    commands = [
        ("show etherchannel 40 summary", "ETHERCHANNEL SUMMARY"),
        ("show interfaces Port-channel40 | include line protocol|BW|Members", "Po40 KEY STATS"),
        ("show lacp 40 counters", "LACP COUNTERS"),
        ("show ip ospf neighbor", "OSPF NEIGHBORS"),
        ("show ip bgp summary", "BGP SUMMARY"),
        ("show lisp session", "LISP SESSIONS"),
        # -- Multicast --
        ("show ip mroute vrf BMS1 225.1.1.1", "MROUTE 225.1.1.1 (VRF BMS1)"),
        ("show ip pim vrf BMS1 neighbor", "PIM NEIGHBORS (VRF BMS1)"),
    ]

    output_all = ""
    for cmd, label in commands:
        sub_banner(f"{label}: {cmd}")
        out = run_and_print(conn, cmd)
        output_all += f"\n--- {label}: {cmd} ---\n{out}\n"

    safe_disconnect(conn)
    save_output(os.path.join(iter_dir, f"Iter{iteration}_Post_BC1_Validation.txt"), output_all)

    # ---- Step 3.6: FS2_L2_9300-1 Post-Recovery ----
    banner("STEP 3.6: FS2_L2_9300-1 POST-RECOVERY CLI", '-')
    collect_commands(L2_9300_1, [
        ("show interfaces trunk", "TRUNKS"),
        ("show spanning-tree vlan 101", "STP VLAN 101 (restored)"),
        ("show spanning-tree vlan 1301", "STP VLAN 1301 (restored)"),
        ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
        ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
        ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (restored)"),
        ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301 (restored)"),
        ("show logging | include LINK|UPDOWN|LINEPROTO|STP|TCN", "SYSLOG (filtered)"),
    ], os.path.join(iter_dir, f"Iter{iteration}_Post_L2_9300-1_Validation.txt"))

    # ---- Step 3.7: FS2_L2_9300-2 Post-Recovery ----
    banner("STEP 3.7: FS2_L2_9300-2 POST-RECOVERY CLI", '-')
    collect_commands(L2_9300_2, [
        ("show interfaces trunk", "TRUNKS"),
        ("show spanning-tree vlan 101", "STP VLAN 101 (restored)"),
        ("show spanning-tree vlan 1301", "STP VLAN 1301 (restored)"),
        ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
        ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
        ("show ip igmp snooping groups vlan 101", "IGMP SNOOPING VLAN 101 (restored)"),
        ("show ip igmp snooping groups vlan 1301", "IGMP SNOOPING VLAN 1301 (restored)"),
        ("show logging | include LINK|UPDOWN|LINEPROTO|STP|TCN", "SYSLOG (filtered)"),
    ], os.path.join(iter_dir, f"Iter{iteration}_Post_L2_9300-2_Validation.txt"))

    # ---- Step 3.8: CC Post-Recovery ----
    banner("STEP 3.8: CATALYST CENTER POST-RECOVERY", '-')
    print("  ACTION REQUIRED:")
    print("    1. Provision > Inventory > FS2_L2H_1")
    print("       - Verify: Reachable, Health >= 80%")
    print(f"    2. Screenshot: Iter{iteration}_Post_CC_L2H1_Health.png")
    print()
    print("    3. Assurance > Health")
    print("       - Verify: Network Health >= 80%")
    print(f"    4. Screenshot: Iter{iteration}_Post_CC_Network_Health.png")
    pause("Take CC post-recovery screenshots, then press ENTER")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='TC 07-01 Execution Script')
    parser.add_argument('--iter', type=int, default=1, choices=[1, 2, 3],
                        help='Iteration number (1, 2, or 3)')
    args = parser.parse_args()
    iteration = args.iter

    banner(f"TC 07-01: Link Failure L2 Border Po Member to Fabric BC", '=')
    print(f"  Iteration: {iteration}")
    print(f"  Start Time: {ts()}")
    print(f"  Primary DUT: FS2_L2H-1 (172.31.0.194)")
    print(f"  Target: TenGigabitEthernet4/0/1 (member of Po40)")
    print(f"  Peer: FS2_BC1 (172.31.2.0)")
    print()

    # Create iteration directory
    iter_dir = os.path.join(TC_DIR, f"Iter{iteration}_CLI")
    os.makedirs(iter_dir, exist_ok=True)
    print(f"  Output directory: {iter_dir}")

    pause(f"Ready to begin Iteration {iteration}? Ensure VPN connected and devices reachable")

    # Execute phases
    phase1(iter_dir, iteration)
    phase2(iter_dir, iteration)
    phase3(iter_dir, iteration)

    # ---- Iteration Summary ----
    banner(f"ITERATION {iteration} COMPLETE", '=')
    print(f"  End Time: {ts()}")
    print()
    print("  RESULTS CHECKLIST:")
    print("    [ ] Po40 stayed UP during member shutdown")
    print("    [ ] Spirent: 0.000% loss (or <= 0.001%) — unicast + multicast")
    print("    [ ] Zero dead flows")
    print("    [ ] LISP sessions maintained throughout")
    print("    [ ] OSPF adjacency never flapped")
    print("    [ ] Multicast: mroute 225.1.1.1 present in VRF BMS1 during failure")
    print("    [ ] Multicast: MFIB HW counters incrementing (forwarding active)")
    print("    [ ] Multicast: PIM neighbors UP during failure")
    print("    [ ] Multicast: IGMP snooping group 225.1.1.1 on VLAN 101")
    print("    [ ] L2_9300-1: STP/IGMP snooping state captured")
    print("    [ ] L2_9300-2: STP/IGMP snooping state captured")
    print("    [ ] Te4/0/1 re-bundled via LACP")
    print("    [ ] Multicast: mroute/MFIB/PIM/IGMP restored to baseline")
    print("    [ ] All metrics match Phase 1 baseline")
    print()
    print("  CLI EVIDENCE:")
    for f in sorted(os.listdir(iter_dir)):
        fpath = os.path.join(iter_dir, f)
        size = os.path.getsize(fpath)
        print(f"    {f} ({size:,} bytes)")
    print()
    print("  SCREENSHOTS NEEDED (8 total):")
    print(f"    Phase 1: Iter{iteration}_Pre_Spirent_Baseline.png")
    print(f"             Iter{iteration}_Pre_CC_L2H1_Health.png")
    print(f"             Iter{iteration}_Pre_CC_Network_Health.png")
    print(f"    Phase 2: Iter{iteration}_During_Spirent_Monitor.png")
    print(f"             Iter{iteration}_During_CC_L2H1_Status.png")
    print(f"    Phase 3: Iter{iteration}_Post_Spirent_Restored.png")
    print(f"             Iter{iteration}_Post_CC_L2H1_Health.png")
    print(f"             Iter{iteration}_Post_CC_Network_Health.png")
    print()

    if iteration < 3:
        print(f"  To run Iteration {iteration + 1}:")
        print(f"    python3 run_tc_07-01.py --iter {iteration + 1}")
    else:
        print("  ALL 3 ITERATIONS COMPLETE.")
        print("  Next: Create Word document deliverable.")

    print()


if __name__ == '__main__':
    main()
