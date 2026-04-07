#!/usr/bin/env python3
"""
TC 07-02 RETEST: Link Failure from L2 Border Port-Channel to Fabric BC Node
DUAL-HOMED TOPOLOGY - Po40 shutdown with Po41 providing redundancy

This is a RETEST after implementing Po41 (FS2_L2H-1 to FS2_BC2).
Expected behavior: HITLESS or NEAR-HITLESS failover via Po41 when Po40 fails.

Original test (single-homed): ~2 minutes outage, significant packet loss
Retest (dual-homed): Sub-second convergence, minimal or zero packet loss

Usage: python3 run_tc_07-02_retest.py [--iter 1|2|3]
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

# Try dnac_admin_tacacs if admin1 fails (Memory #24 - BC2 may need alternate creds)
BC2_ALT = {
    'device_type': 'cisco_ios',
    'host': '172.31.2.2',
    'username': 'dnac_admin_tacacs',
    'password': 'CXlabs.123',
    'timeout': 30,
    'name': 'FS2_BC2',
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
    """Disconnect gracefully, ignoring errors on dead sockets."""
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
    """Run command, print output, return output. Handles timeouts."""
    try:
        output = conn.send_command(cmd, read_timeout=read_timeout)
    except Exception as e:
        output = f"ERROR running command: {e}"
    print(output)
    return output

def collect_commands(device_info, commands, filename, try_alt=None):
    """Connect to device, run commands, save to file, disconnect.

    Each collection is a self-contained connect/collect/disconnect cycle.
    This prevents stale socket errors from long pauses between phases.
    """
    conn = connect(device_info, try_alt=try_alt)
    output_all = ""
    for cmd, label in commands:
        sub_banner(f"{label}: {cmd}")
        out = run_cmd(conn, cmd)
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
    print()
    print("  DUAL-HOMED TOPOLOGY:")
    print("    FS2_L2H-1 --Po40--> FS2_BC1 (192.168.40.0/31)")
    print("    FS2_L2H-1 --Po41--> FS2_BC2 (192.168.41.0/31)")
    print("    Expected: ECMP load-balancing across both paths")
    print()

    # ---- Step 1.0: Clear logs on all devices ----
    banner("STEP 1.0: CLEARING LOGS ON ALL DEVICES", '-')
    print("  Clearing syslog buffers for clean evidence collection...")
    for dev, alt, name in [(L2H1_TACACS, None, 'L2H-1'), (BC1, None, 'BC1'), (BC2, BC2_ALT, 'BC2')]:
        try:
            conn = connect(dev, try_alt=alt)
            conn.send_command_timing("clear logging", strip_command=False)
            conn.send_command_timing("", strip_command=False)  # confirm [OK]
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
    print("  Using TACACS account (admin1)")
    collect_commands(L2H1_TACACS, [
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
        ("show ip ospf neighbor", "OSPF NEIGHBORS (should see both BC1 and BC2)"),
        ("show ip route ospf | include 192.168", "OSPF ROUTES (ECMP paths)"),
        ("show bfd neighbors", "BFD SESSIONS"),
        ("show lisp session", "LISP SESSIONS"),
        ("show ip route summary", "ROUTE SUMMARY"),
        ("show cts role-based counters", "CTS COUNTERS"),
    ], os.path.join(iter_dir, f"Iter{iteration}_Pre_L2H1_Baseline.txt"))

    # ---- Step 1.4: BC1 CLI Baseline ----
    banner("STEP 1.4: CLI BASELINE - FS2_BC1 (172.31.2.0)", '-')
    collect_commands(BC1, [
        ("show version | include uptime", "UPTIME"),
        ("show etherchannel 40 summary", "ETHERCHANNEL 40 SUMMARY"),
        ("show interfaces Port-channel40", "Po40 INTERFACE"),
        ("show interfaces Port-channel40 human-readable", "Po40 INTERFACE (human-readable)"),
        ("show lacp 40 counters", "LACP COUNTERS"),
        ("show ip ospf neighbor", "OSPF NEIGHBORS"),
        ("show ip bgp summary", "BGP SUMMARY"),
        ("show lisp session", "LISP SESSIONS"),
        ("show bfd neighbors", "BFD SESSIONS"),
    ], os.path.join(iter_dir, f"Iter{iteration}_Pre_BC1_Baseline.txt"))

    # ---- Step 1.5: BC2 CLI Baseline ----
    banner("STEP 1.5: CLI BASELINE - FS2_BC2 (172.31.2.2)", '-')
    print("  NOTE: May require dnac_admin_tacacs credentials (Memory #24)")
    collect_commands(BC2, [
        ("show version | include uptime", "UPTIME"),
        ("show etherchannel 41 summary", "ETHERCHANNEL 41 SUMMARY"),
        ("show interfaces Port-channel41", "Po41 INTERFACE"),
        ("show interfaces Port-channel41 human-readable", "Po41 INTERFACE (human-readable)"),
        ("show lacp 41 counters", "LACP COUNTERS"),
        ("show ip ospf neighbor", "OSPF NEIGHBORS"),
        ("show ip bgp summary", "BGP SUMMARY"),
        ("show lisp session", "LISP SESSIONS"),
        ("show bfd neighbors", "BFD SESSIONS"),
    ], os.path.join(iter_dir, f"Iter{iteration}_Pre_BC2_Baseline.txt"),
    try_alt=BC2_ALT)

    # ---- Phase 1 Gate ----
    banner("PHASE 1 GATE CHECK", '*')
    print("  Verify ALL of the following before proceeding:")
    print("    [ ] Spirent: 0.000% loss, 0 dead streams")
    print("    [ ] CC: L2H-1 health >= 80%, 0 critical alarms")
    print("    [ ] CC: Network health >= 80%")
    print("    [ ] L2H-1: Po40 UP with Te4/0/1(P) + Te4/0/2(P)")
    print("    [ ] L2H-1: Po41 UP with Te4/0/3(P) + Te4/0/4(P)")
    print("    [ ] L2H-1: OSPF FULL to BOTH BC1 (192.168.40.1) and BC2 (192.168.41.1)")
    print("    [ ] L2H-1: BFD UP to both BCs")
    print("    [ ] L2H-1: ECMP routes visible (equal cost via Po40 and Po41)")
    print("    [ ] L2H-1: 2 LISP sessions UP")
    print("    [ ] BC1: Po40 UP, OSPF FULL to L2H-1")
    print("    [ ] BC2: Po41 UP, OSPF FULL to L2H-1")
    print("    [ ] Screenshots captured (3 total)")
    print("    [ ] CLI baselines saved (3 files: L2H-1, BC1, BC2)")
    pause("Confirm all checks PASS, then press ENTER to proceed to PHASE 2 (FAILURE)")


# =============================================================================
# PHASE 2: FAILURE EVENT
# =============================================================================

def phase2(iter_dir, iteration):
    banner(f"PHASE 2: FAILURE EVENT - SHUTDOWN Po40 (DUAL-HOMED)  (Iteration {iteration})")
    print(f"  Timestamp: {ts()}")
    print()
    print("  TARGET: TenGigabitEthernet4/0/1 AND TenGigabitEthernet4/0/2 on FS2_L2H-1")
    print("  ACTION: shutdown BOTH members (Po40 goes DOWN)")
    print()
    print("  DUAL-HOMED BEHAVIOR:")
    print("    X  Po40 goes DOWN (to BC1)")
    print("    OK Po41 stays UP (to BC2)")
    print("    OK OSPF to BC2 remains FULL")
    print("    OK Traffic continues via Po41 (ECMP failover)")
    print()
    print("  EXPECTED RESULTS (DUAL-HOMED):")
    print("    - Po40 DOWN, OSPF to BC1 DOWN (EXPECTED)")
    print("    - Po41 UP, OSPF to BC2 FULL (MUST REMAIN UP)")
    print("    - BFD to BC1 DOWN, BFD to BC2 UP")
    print("    - Minimal packet loss (<1 second) or HITLESS")
    print("    - Dead flows: MINIMAL or ZERO")
    print("    - Total convergence: Sub-second (not ~2 minutes like single-homed)")
    print()
    print("  CONTRAST WITH ORIGINAL TEST (Single-Homed):")
    print("    - Old: Complete connectivity loss, ~2 min outage")
    print("    - New: Po41 provides instant redundancy")
    pause("Ready to SHUTDOWN Po40? Press ENTER to execute")

    # ---- Step 2.1: Execute Shutdown ----
    banner("STEP 2.1: EXECUTING SHUTDOWN OF Po40 MEMBERS", '-')
    print("  Using TACACS account for shutdown (TACACS reachable via Po41)")
    conn = connect(L2H1_TACACS)

    try:
        conn.enable()
        print("  Entered enable mode")
    except Exception:
        print("  Already in enable mode or enable not needed")

    shutdown_time = datetime.datetime.now()
    print(f"\n  >>> SHUTDOWN EXECUTED at {shutdown_time.strftime('%H:%M:%S')} <<<\n")

    config_output = conn.send_config_set([
        'interface range TenGigabitEthernet4/0/1 - 2',
        'shutdown'
    ])
    print(config_output)

    # Disconnect immediately - shutdown can disrupt the existing SSH socket
    # due to CPU spike, TACACS re-auth path change, or TCP reset on the
    # management plane during convergence.
    safe_disconnect(conn)
    print("  Disconnected post-shutdown (will reconnect for verification)")

    # ---- Step 2.2: Immediate Verification (Po41 MUST stay UP) ----
    banner("STEP 2.2: IMMEDIATE VERIFICATION - Po41 REDUNDANCY CHECK", '-')
    print("  Waiting 5 seconds for convergence, then reconnecting...")
    time.sleep(5)
    print(f"  Verification at: {ts()}")

    conn = connect(L2H1_TACACS)

    sub_banner("show etherchannel summary")
    run_cmd(conn, "show etherchannel summary")

    sub_banner("show interfaces Port-channel40 | key lines")
    run_cmd(conn, "show interfaces Port-channel40 | include line protocol|BW")

    sub_banner("show interfaces Port-channel41 | key lines")
    run_cmd(conn, "show interfaces Port-channel41 | include line protocol|BW")

    sub_banner("show ip ospf neighbor")
    ospf_out = run_cmd(conn, "show ip ospf neighbor")

    sub_banner("show bfd neighbors")
    run_cmd(conn, "show bfd neighbors")

    safe_disconnect(conn)

    print()
    print("  !!! CRITICAL VERIFICATION !!!")
    print("  Expected State:")
    print("    X  Po40: DOWN (protocol down) - EXPECTED")
    print("    OK Po41: UP (to BC2) - MUST BE UP")
    print("    X  OSPF to BC1 (192.168.40.1): DOWN - EXPECTED")
    print("    OK OSPF to BC2 (192.168.41.1): FULL - MUST BE FULL")
    print("    OK BFD to BC2: UP - MUST BE UP")
    print()

    if 'FULL' in ospf_out and '192.168.41.1' in ospf_out:
        print("  >>> SUCCESS: OSPF to BC2 is FULL - Po41 providing redundancy!")
    else:
        print("  !!! WARNING: OSPF to BC2 not showing FULL - investigate!")

    print("\n  NOTE: TACACS still reachable via Po41 - no need to switch to local admin")

    # ---- Step 2.3: Spirent Convergence Monitoring ----
    banner("STEP 2.3: SPIRENT CONVERGENCE MEASUREMENT", '-')
    print("  DUAL-HOMED EXPECTATION: Hitless or sub-second convergence")
    print("  (Unlike single-homed: ~2 minute outage with significant loss)")
    print()
    print("  ACTION REQUIRED:")
    print("    1. Watch Spirent GUI - should show minimal or ZERO loss")
    print("    2. Monitor for 3 minutes to observe convergence behavior")
    print("    3. Record dead streams (expect ZERO or minimal)")
    print()
    print(f"    4. Screenshot at T+2:00: Iter{iteration}_During_Spirent_Convergence.png")
    print()
    print("    5. After 3 minutes: STOP TRAFFIC")
    print(f"    6. Export Spirent DB: Iter{iteration}_During_Spirent_DB.tcc")
    print()
    print("    7. Upload to PLA: http://spirent-pla.cisco.com")
    print("       - Login to PLA portal")
    print("       - Upload .tcc file")
    print("       - Run convergence analysis")
    print(f"       - Download Excel: Iter{iteration}_PLA_Convergence_Analysis.xlsx")
    print()
    print(f"    8. Screenshot PLA results: Iter{iteration}_PLA_Analysis.png")
    pause("Complete Spirent convergence measurement and PLA analysis, then press ENTER")

    # ---- Step 2.4: L2H-1 During-Failure CLI ----
    banner("STEP 2.4: L2H-1 DURING-FAILURE CLI", '-')
    print("  Using TACACS account (still reachable via Po41)")
    collect_commands(L2H1_TACACS, [
        ("show etherchannel summary", "ALL ETHERCHANNELS"),
        ("show etherchannel 40 summary", "ETHERCHANNEL 40 (DOWN)"),
        ("show etherchannel 41 summary", "ETHERCHANNEL 41 (UP)"),
        ("show interfaces Port-channel40", "Po40 INTERFACE (DOWN)"),
        ("show interfaces Port-channel40 human-readable", "Po40 INTERFACE (DOWN) (human-readable)"),
        ("show interfaces Port-channel41", "Po41 INTERFACE (UP)"),
        ("show interfaces Port-channel41 human-readable", "Po41 INTERFACE (UP) (human-readable)"),
        ("show interfaces TenGigabitEthernet4/0/1", "Te4/0/1 (DOWN)"),
        ("show interfaces TenGigabitEthernet4/0/1 human-readable", "Te4/0/1 (DOWN) (human-readable)"),
        ("show interfaces TenGigabitEthernet4/0/2", "Te4/0/2 (DOWN)"),
        ("show interfaces TenGigabitEthernet4/0/2 human-readable", "Te4/0/2 (DOWN) (human-readable)"),
        ("show interfaces TenGigabitEthernet4/0/3", "Te4/0/3 (Po41 - UP)"),
        ("show interfaces TenGigabitEthernet4/0/3 human-readable", "Te4/0/3 (Po41 - UP) (human-readable)"),
        ("show interfaces TenGigabitEthernet4/0/4", "Te4/0/4 (Po41 - UP)"),
        ("show interfaces TenGigabitEthernet4/0/4 human-readable", "Te4/0/4 (Po41 - UP) (human-readable)"),
        ("show lacp 40 counters", "LACP 40 COUNTERS"),
        ("show lacp 41 counters", "LACP 41 COUNTERS"),
        ("show ip ospf neighbor", "OSPF NEIGHBORS (BC2 MUST BE FULL)"),
        ("show ip route ospf | include 192.168", "OSPF ROUTES (via Po41 only)"),
        ("show bfd neighbors", "BFD SESSIONS (BC2 MUST BE UP)"),
        ("show lisp session", "LISP SESSIONS"),
        ("show ip route summary", "ROUTE SUMMARY"),
        ("show cts role-based counters", "CTS COUNTERS"),
        ("show logging | include OSPF|LACP|BFD", "SYSLOG (filtered)"),
    ], os.path.join(iter_dir, f"Iter{iteration}_During_L2H1_Failure.txt"))

    # ---- Step 2.5: BC1 During-Failure ----
    banner("STEP 2.5: BC1 DURING-FAILURE STATUS", '-')
    collect_commands(BC1, [
        ("show etherchannel 40 summary", "ETHERCHANNEL SUMMARY (DOWN)"),
        ("show interfaces Port-channel40 | include line protocol|BW", "Po40 STATUS (DOWN)"),
        ("show interfaces Port-channel40 human-readable", "Po40 INTERFACE (DOWN) (human-readable)"),
        ("show lacp 40 counters", "LACP COUNTERS"),
        ("show ip ospf neighbor | include 192.168.102.40", "OSPF TO L2H-1 (DOWN)"),
        ("show lisp session | include 192.168.102.40", "LISP TO L2H-1"),
        ("show logging | include OSPF|LACP", "SYSLOG (filtered)"),
    ], os.path.join(iter_dir, f"Iter{iteration}_During_BC1_Status.txt"))

    # ---- Step 2.6: BC2 During-Failure (CRITICAL - Must stay UP) ----
    banner("STEP 2.6: BC2 DURING-FAILURE STATUS (Po41 REDUNDANCY)", '-')
    print("  BC2 Po41 MUST remain UP - this validates dual-homing success")
    collect_commands(BC2, [
        ("show etherchannel 41 summary", "ETHERCHANNEL 41 (MUST BE UP)"),
        ("show interfaces Port-channel41", "Po41 INTERFACE (MUST BE UP)"),
        ("show interfaces Port-channel41 human-readable", "Po41 INTERFACE (MUST BE UP) (human-readable)"),
        ("show lacp 41 counters", "LACP COUNTERS"),
        ("show ip ospf neighbor | include 192.168.102.40", "OSPF TO L2H-1 (MUST BE FULL)"),
        ("show bfd neighbors | include 192.168.102.40", "BFD TO L2H-1 (MUST BE UP)"),
        ("show lisp session | include 192.168.102.40", "LISP TO L2H-1"),
        ("show ip route ospf | begin Gateway", "OSPF ROUTES (traffic via Po41)"),
        ("show logging | include OSPF|LACP|BFD", "SYSLOG (filtered)"),
    ], os.path.join(iter_dir, f"Iter{iteration}_During_BC2_Status.txt"),
    try_alt=BC2_ALT)

    # ---- Step 2.7: CC During-Failure ----
    banner("STEP 2.7: CATALYST CENTER DURING-FAILURE", '-')
    print("  ACTION REQUIRED:")
    print("    1. Provision > Inventory > FS2_L2H_1")
    print("       - Expected: Still Reachable (via Po41)")
    print("       - Health may show Po40 warning but should not be Critical")
    print(f"    2. Screenshot: Iter{iteration}_During_CC_L2H1_Status.png")
    pause("Take CC during-failure screenshot, then press ENTER to proceed to RECOVERY")


# =============================================================================
# PHASE 3: RECOVERY
# =============================================================================

def phase3(iter_dir, iteration):
    banner(f"PHASE 3: RECOVERY - RESTORE Po40 (DUAL-HOMED)  (Iteration {iteration})")
    print(f"  Timestamp: {ts()}")
    print()
    print("  ACTION: no shutdown BOTH Po40 members (restore dual-homing)")
    print("  EXPECTED: Po40 restores, ECMP resumes across both Po40 and Po41")
    print("  EXPECTED: No traffic impact (Po41 already carrying traffic)")
    pause("Ready to RESTORE Po40? Press ENTER to execute")

    # ---- Step 3.1: Execute Recovery ----
    banner("STEP 3.1: EXECUTING RECOVERY (no shutdown Po40)", '-')
    print("  Using TACACS account (reachable via Po41)")
    conn = connect(L2H1_TACACS)

    try:
        conn.enable()
        print("  Entered enable mode")
    except Exception:
        print("  Already in enable mode or enable not needed")

    recovery_time = datetime.datetime.now()
    print(f"\n  >>> NO SHUTDOWN EXECUTED at {recovery_time.strftime('%H:%M:%S')} <<<\n")

    config_output = conn.send_config_set([
        'interface range TenGigabitEthernet4/0/1 - 2',
        'no shutdown'
    ])
    print(config_output)

    # ---- Step 3.2: Monitor Po40 Rebundle ----
    banner("STEP 3.2: MONITORING PORT-CHANNEL 40 REBUNDLE", '-')
    print("  Monitoring every 5 seconds for up to 60 seconds...")
    rebundled = False
    for wait_total in [5, 10, 15, 20, 25, 30, 40, 50, 60]:
        time.sleep(5)
        now = datetime.datetime.now().strftime('%H:%M:%S')
        try:
            result = conn.send_command("show etherchannel 40 summary | include Po40|Te4", read_timeout=15)
        except Exception:
            # Reconnect if socket died
            safe_disconnect(conn)
            conn = connect(L2H1_TACACS)
            result = conn.send_command("show etherchannel 40 summary | include Po40|Te4", read_timeout=15)
        status = result.strip()
        print(f"  T+{wait_total:2d}s ({now}): {status}")
        if 'Po40' in status and 'up' in status.lower():
            if 'Te4/0/1(P)' in status and 'Te4/0/2(P)' in status:
                if not rebundled:
                    rebundle_time = wait_total
                    rebundled = True
                    print(f"  >>> Po40 FULLY BUNDLED (both members) in <= {rebundle_time} seconds <<<")

    if not rebundled:
        print("  WARNING: Po40 has NOT fully bundled after 60 seconds!")
        print("  Checking current status...")
        try:
            result = conn.send_command("show etherchannel 40 summary", read_timeout=15)
        except Exception:
            safe_disconnect(conn)
            conn = connect(L2H1_TACACS)
            result = conn.send_command("show etherchannel 40 summary", read_timeout=15)
        print(result)

    # ---- Step 3.3: Monitor OSPF Adjacency to BC1 ----
    banner("STEP 3.3: MONITORING OSPF ADJACENCY TO BC1 RESTORATION", '-')
    print("  Monitoring every 10 seconds for up to 40 seconds...")
    ospf_full = False
    for wait_total in [10, 20, 30, 40]:
        time.sleep(10)
        now = datetime.datetime.now().strftime('%H:%M:%S')
        try:
            result = conn.send_command("show ip ospf neighbor | include 192.168.40.1", read_timeout=15)
        except Exception:
            safe_disconnect(conn)
            conn = connect(L2H1_TACACS)
            result = conn.send_command("show ip ospf neighbor | include 192.168.40.1", read_timeout=15)
        status = result.strip()
        print(f"  T+{wait_total:2d}s ({now}): {status}")
        if 'FULL' in status:
            if not ospf_full:
                ospf_time = wait_total
                ospf_full = True
                print(f"  >>> OSPF TO BC1 FULL in <= {ospf_time} seconds <<<")

    if not ospf_full:
        print("  WARNING: OSPF to BC1 has NOT reached FULL after 40 seconds!")
        try:
            result = conn.send_command("show ip ospf neighbor", read_timeout=15)
        except Exception:
            safe_disconnect(conn)
            conn = connect(L2H1_TACACS)
            result = conn.send_command("show ip ospf neighbor", read_timeout=15)
        print(result)

    # ---- Step 3.4: Verify ECMP Restoration ----
    banner("STEP 3.4: VERIFY ECMP LOAD-BALANCING RESTORATION", '-')
    print("  Checking OSPF routes - should see ECMP via BOTH Po40 and Po41...")
    time.sleep(5)

    try:
        sub_banner("show ip route ospf | include 192.168")
        ecmp_routes = run_cmd(conn, "show ip route ospf | include 192.168")

        if 'Port-channel40' in ecmp_routes and 'Port-channel41' in ecmp_routes:
            print("\n  >>> SUCCESS: ECMP load-balancing restored (routes via both Po40 and Po41)")
        else:
            print("\n  !!! WARNING: ECMP not showing both port-channels - investigate!")

        sub_banner("show bfd neighbors")
        run_cmd(conn, "show bfd neighbors")

        sub_banner("show lisp session")
        result = conn.send_command("show lisp session", read_timeout=15)
        print(result)
        if 'Up' in result:
            print("  >>> LISP SESSIONS RESTORED <<<")
        else:
            print("  WARNING: Check LISP session status above")
    except Exception:
        print("  Connection lost during ECMP check - will be captured in post-recovery CLI")

    safe_disconnect(conn)

    # ---- Step 3.5: Spirent Validation ----
    banner("STEP 3.5: SPIRENT POST-RECOVERY VALIDATION", '-')
    print("  ACTION REQUIRED:")
    print("    1. Wait 60 seconds to allow full convergence")
    print("    2. START Spirent traffic (if stopped)")
    print("    3. Clear counters")
    print("    4. Wait 60 seconds")
    print("    5. Verify: Loss % = 0.000%, Dead Streams = 0")
    print("    6. Note: Traffic should have been minimally impacted throughout")
    print(f"    7. Screenshot: Iter{iteration}_Post_Spirent_Restored.png")
    pause("Take Spirent post-recovery screenshot, then press ENTER")

    # ---- Step 3.6: Full L2H-1 Post-Recovery Validation ----
    banner("STEP 3.6: L2H-1 FULL POST-RECOVERY VALIDATION", '-')
    collect_commands(L2H1_TACACS, [
        ("show etherchannel summary", "ALL ETHERCHANNELS"),
        ("show etherchannel 40 summary", "ETHERCHANNEL 40"),
        ("show etherchannel 41 summary", "ETHERCHANNEL 41"),
        ("show interfaces Port-channel40", "Po40 INTERFACE"),
        ("show interfaces Port-channel40 human-readable", "Po40 INTERFACE (human-readable)"),
        ("show interfaces Port-channel41", "Po41 INTERFACE"),
        ("show interfaces Port-channel41 human-readable", "Po41 INTERFACE (human-readable)"),
        ("show lacp 40 neighbor", "LACP 40 NEIGHBOR"),
        ("show lacp 41 neighbor", "LACP 41 NEIGHBOR"),
        ("show ip ospf neighbor", "OSPF NEIGHBORS (BOTH BCs)"),
        ("show ip route ospf | include 192.168", "OSPF ROUTES (ECMP)"),
        ("show bfd neighbors", "BFD SESSIONS (BOTH BCs)"),
        ("show lisp session", "LISP SESSIONS"),
        ("show ip route summary", "ROUTE SUMMARY"),
        ("show cts role-based counters", "CTS COUNTERS"),
        ("show logging | include OSPF|LACP|BFD", "SYSLOG (filtered)"),
    ], os.path.join(iter_dir, f"Iter{iteration}_Post_L2H1_Validation.txt"))

    # ---- Step 3.7: BC1 Post-Recovery ----
    banner("STEP 3.7: BC1 FULL POST-RECOVERY VALIDATION", '-')
    collect_commands(BC1, [
        ("show etherchannel 40 summary", "ETHERCHANNEL SUMMARY"),
        ("show interfaces Port-channel40", "Po40 INTERFACE"),
        ("show interfaces Port-channel40 human-readable", "Po40 INTERFACE (human-readable)"),
        ("show lacp 40 counters", "LACP COUNTERS"),
        ("show ip ospf neighbor", "OSPF NEIGHBORS"),
        ("show ip bgp summary", "BGP SUMMARY"),
        ("show lisp session", "LISP SESSIONS"),
        ("show bfd neighbors", "BFD SESSIONS"),
        ("show logging | include OSPF|LACP", "SYSLOG (filtered)"),
    ], os.path.join(iter_dir, f"Iter{iteration}_Post_BC1_Validation.txt"))

    # ---- Step 3.8: BC2 Post-Recovery ----
    banner("STEP 3.8: BC2 FULL POST-RECOVERY VALIDATION", '-')
    collect_commands(BC2, [
        ("show etherchannel 41 summary", "ETHERCHANNEL 41 SUMMARY"),
        ("show interfaces Port-channel41", "Po41 INTERFACE"),
        ("show interfaces Port-channel41 human-readable", "Po41 INTERFACE (human-readable)"),
        ("show lacp 41 counters", "LACP COUNTERS"),
        ("show ip ospf neighbor", "OSPF NEIGHBORS"),
        ("show ip bgp summary", "BGP SUMMARY"),
        ("show lisp session", "LISP SESSIONS"),
        ("show bfd neighbors", "BFD SESSIONS"),
        ("show logging | include OSPF|LACP", "SYSLOG (filtered)"),
    ], os.path.join(iter_dir, f"Iter{iteration}_Post_BC2_Validation.txt"),
    try_alt=BC2_ALT)

    # ---- Step 3.9: CC Post-Recovery ----
    banner("STEP 3.9: CATALYST CENTER POST-RECOVERY", '-')
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
    parser = argparse.ArgumentParser(description='TC 07-02 RETEST - Dual-Homed Execution Script')
    parser.add_argument('--iter', type=int, default=1, choices=[1, 2, 3],
                        help='Iteration number (1, 2, or 3)')
    args = parser.parse_args()
    iteration = args.iter

    banner(f"TC 07-02 RETEST: Link Failure L2 Border Po40 - DUAL-HOMED TOPOLOGY", '=')
    print(f"  Iteration: {iteration}")
    print(f"  Start Time: {ts()}")
    print(f"  Primary DUT: FS2_L2H-1 (172.31.0.194)")
    print(f"  Target: Po40 (Te4/0/1-2) to FS2_BC1")
    print(f"  Redundancy: Po41 (Te4/0/3-4) to FS2_BC2")
    print()
    print("  TOPOLOGY:")
    print("    FS2_L2H-1 --Po40--> FS2_BC1 (192.168.40.0/31) <-- WILL BE SHUT DOWN")
    print("    FS2_L2H-1 --Po41--> FS2_BC2 (192.168.41.0/31) <-- REDUNDANT PATH")
    print()
    print("  EXPECTED BEHAVIOR (DUAL-HOMED):")
    print("    - Po40 failure -> Po41 continues to carry traffic")
    print("    - Hitless or sub-second convergence (not ~2 min like single-homed)")
    print("    - ECMP load-balancing active in baseline and post-recovery")
    print("    - Minimal or zero packet loss during Po40 outage")
    print()
    print("  COMPARISON TO ORIGINAL TEST:")
    print("    - Original (Single-Homed): ~2 min outage, significant dead flows")
    print("    - Retest (Dual-Homed): Sub-second convergence, minimal/zero loss")
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
    print("  RESULTS CHECKLIST (DUAL-HOMED VALIDATION):")
    print("    [ ] Po40 went DOWN during shutdown (EXPECTED)")
    print("    [ ] Po41 REMAINED UP during Po40 failure (CRITICAL)")
    print("    [ ] OSPF to BC1 went DOWN (EXPECTED)")
    print("    [ ] OSPF to BC2 stayed FULL (CRITICAL)")
    print("    [ ] BFD to BC2 stayed UP (CRITICAL)")
    print("    [ ] Spirent: Minimal packet loss (<1 sec) or HITLESS")
    print("    [ ] Dead flows: MINIMAL or ZERO")
    print("    [ ] PLA convergence analysis completed")
    print("    [ ] Po40 restored with both members bundled")
    print("    [ ] OSPF to BC1 restored to FULL")
    print("    [ ] ECMP load-balancing resumed (routes via both Po40 and Po41)")
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
    print(f"    Phase 2: Iter{iteration}_During_Spirent_Convergence.png")
    print(f"             Iter{iteration}_During_CC_L2H1_Status.png")
    print(f"    Phase 3: Iter{iteration}_Post_Spirent_Restored.png")
    print(f"             Iter{iteration}_Post_CC_L2H1_Health.png")
    print(f"             Iter{iteration}_Post_CC_Network_Health.png")
    print()
    print("  SPIRENT CONVERGENCE ANALYSIS (MANDATORY):")
    print(f"    Iter{iteration}_During_Spirent_DB.tcc")
    print(f"    Iter{iteration}_PLA_Convergence_Analysis.xlsx")
    print(f"    Iter{iteration}_PLA_Analysis.png")
    print()

    if iteration < 3:
        print(f"  To run Iteration {iteration + 1}:")
        print(f"    python3 run_tc_07-02_retest.py --iter {iteration + 1}")
    else:
        print("  ALL 3 ITERATIONS COMPLETE.")
        print("  Next: Compare retest results with original single-homed results.")
        print("  Create Word document with dual-homed validation evidence.")

    print()


if __name__ == '__main__':
    main()
