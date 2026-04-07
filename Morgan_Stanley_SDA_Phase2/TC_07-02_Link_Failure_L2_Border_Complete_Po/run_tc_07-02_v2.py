#!/usr/bin/env python3
"""
TC 07-02: Link Failure from L2 Border Port-Channel to Fabric BC Node
ROBUST VERSION - Handles TACACS fallback automatically

Usage: python3 run_tc_07-02_v2.py [--iter 1|2|3]
"""

import os
import sys
import datetime
import time
import argparse
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException

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

def connect_smart(device_info_tacacs, device_info_local):
    """
    Smart connection with TACACS fallback.
    Tries TACACS first (admin1), falls back to local admin if TACACS unreachable.
    """
    name = device_info_tacacs['name']
    host = device_info_tacacs['host']

    # Try TACACS first
    print(f"  Connecting to {name} ({host})...", end=' ', flush=True)
    dev_tacacs = {k: v for k, v in device_info_tacacs.items() if k != 'name'}
    try:
        conn = ConnectHandler(**dev_tacacs)
        prompt = conn.find_prompt()
        print(f"OK [{prompt}] (TACACS: admin1)")
        return conn, 'tacacs'
    except NetmikoAuthenticationException:
        print("TACACS failed, trying local admin...", end=' ', flush=True)
        dev_local = {k: v for k, v in device_info_local.items() if k != 'name'}
        try:
            conn = ConnectHandler(**dev_local)
            # Explicitly enter enable mode for local admin
            try:
                conn.enable()
                prompt = conn.find_prompt()
                print(f"OK [{prompt}] (LOCAL: admin)")
                return conn, 'local'
            except:
                prompt = conn.find_prompt()
                print(f"OK [{prompt}] (LOCAL: admin, already enabled)")
                return conn, 'local'
        except Exception as e:
            print(f"FAILED - {e}")
            raise

def connect(device_info):
    """Connect to device, return netmiko connection."""
    name = device_info['name']
    host = device_info['host']
    print(f"  Connecting to {name} ({host})...", end=' ', flush=True)
    dev = {k: v for k, v in device_info.items() if k != 'name'}
    conn = ConnectHandler(**dev)
    prompt = conn.find_prompt()
    print(f"OK [{prompt}]")
    return conn

def run_and_print(conn, cmd):
    """Run command, print output, return output."""
    output = conn.send_command(cmd, read_timeout=120)
    print(output)
    return output

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
    conn, auth_type = connect_smart(L2H1_TACACS, L2H1_LOCAL)

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
    ]

    output_all = ""
    for cmd, label in commands:
        sub_banner(f"{label}: {cmd}")
        out = run_and_print(conn, cmd)
        output_all += f"\n--- {label}: {cmd} ---\n{out}\n"

    conn.disconnect()
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
    ]

    output_all = ""
    for cmd, label in commands:
        sub_banner(f"{label}: {cmd}")
        out = run_and_print(conn, cmd)
        output_all += f"\n--- {label}: {cmd} ---\n{out}\n"

    conn.disconnect()
    save_output(os.path.join(iter_dir, f"Iter{iteration}_Pre_BC1_Baseline.txt"), output_all)

    # ---- Phase 1 Gate ----
    banner("PHASE 1 GATE CHECK", '*')
    print("  Verify ALL of the following before proceeding:")
    print("    [ ] Spirent: 0.000% loss, 0 dead streams")
    print("    [ ] CC: L2H-1 health >= 80%, 0 critical alarms")
    print("    [ ] CC: Network health >= 80%")
    print("    [ ] L2H-1: Po40 UP, Te4/0/1(P) + Te4/0/2(P)")
    print("    [ ] L2H-1: 2 LISP sessions UP, OSPF FULL to BC1")
    print("    [ ] BC1: Po40 UP, Fif1/0/13(P) + Fif1/0/14(P)")
    print("    [ ] Screenshots captured (3 total)")
    print("    [ ] CLI baselines saved (2 files)")
    pause("Confirm all checks PASS, then press ENTER to proceed to PHASE 2 (FAILURE)")


# =============================================================================
# PHASE 2: FAILURE EVENT
# =============================================================================

def phase2(iter_dir, iteration):
    banner(f"PHASE 2: FAILURE EVENT - SHUTDOWN ENTIRE PORT-CHANNEL  (Iteration {iteration})")
    print(f"  Timestamp: {ts()}")
    print()
    print("  TARGET: TenGigabitEthernet4/0/1 AND TenGigabitEthernet4/0/2 on FS2_L2H-1")
    print("  ACTION: shutdown BOTH members (COMPLETE Port-Channel failure)")
    print("  EXPECTED: Po40 goes DOWN (protocol down)")
    print("  EXPECTED: OSPF adjacency DOWN, LISP session to BC1 DOWN")
    print("  EXPECTED: Packet loss and dead flows during failure")
    print()
    print("  !!! WARNING: This will cause traffic interruption !!!")
    pause("Ready to SHUTDOWN BOTH MEMBERS? Press ENTER to execute")

    # ---- Step 2.1: Execute Shutdown ----
    banner("STEP 2.1: EXECUTING SHUTDOWN OF BOTH MEMBERS", '-')
    conn, auth_type = connect_smart(L2H1_TACACS, L2H1_LOCAL)
    print(f"  Authentication: {auth_type.upper()}")

    shutdown_time = datetime.datetime.now()
    print(f"\n  >>> SHUTDOWN EXECUTED at {shutdown_time.strftime('%H:%M:%S')} <<<\n")

    config_output = conn.send_config_set([
        'interface range TenGigabitEthernet4/0/1 - 2',
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
    run_and_print(conn, "show interfaces Port-channel40 | include line protocol|BW")

    sub_banner("show interfaces Te4/0/1 | status")
    run_and_print(conn, "show interfaces TenGigabitEthernet4/0/1 | include line protocol")

    sub_banner("show interfaces Te4/0/2 | status")
    run_and_print(conn, "show interfaces TenGigabitEthernet4/0/2 | include line protocol")

    print()
    print("  !!! VERIFY: Po40 should be DOWN (protocol down) !!!")
    print("  !!! This is EXPECTED and CORRECT for TC 07-02 !!!")

    # Disconnect to avoid timeout during long Spirent analysis
    conn.disconnect()
    print("\n  Disconnected from L2H-1 (will reconnect after Spirent analysis)")

    # ---- Step 2.3: Spirent Convergence Monitoring ----
    banner("STEP 2.3: SPIRENT CONVERGENCE MEASUREMENT", '-')
    print("  !!! CRITICAL: Packet loss WILL occur - this is EXPECTED !!!")
    print()
    print("  ACTION REQUIRED:")
    print("    1. Watch Spirent GUI - packet loss will spike")
    print("    2. Monitor for 3 minutes to observe convergence")
    print("    3. Record dead streams and loss percentage")
    print()
    print("    4. Screenshot at T+2:00: Iter{iteration}_During_Spirent_Convergence.png")
    print()
    print("    5. After 3 minutes: STOP TRAFFIC")
    print("    6. Export Spirent DB: Iter{iteration}_During_Spirent_DB.tcc")
    print()
    print("    7. Upload to PLA: http://spirent-pla.cisco.com")
    print("       - Login to PLA portal")
    print("       - Upload .tcc file")
    print("       - Run convergence analysis")
    print("       - Download Excel: Iter{iteration}_PLA_Convergence_Analysis.xlsx")
    print()
    print("    8. Screenshot PLA results: Iter{iteration}_PLA_Analysis.png")
    pause("Complete Spirent convergence measurement and PLA analysis, then press ENTER")

    # ---- Step 2.4: L2H-1 During-Failure CLI ----
    banner("STEP 2.4: L2H-1 DURING-FAILURE CLI", '-')
    print("  Po40 is DOWN - TACACS likely unreachable, will try both auth methods")
    conn, auth_type = connect_smart(L2H1_TACACS, L2H1_LOCAL)
    print(f"  Authentication: {auth_type.upper()}")

    commands = [
        ("show etherchannel 40 summary", "ETHERCHANNEL SUMMARY"),
        ("show etherchannel 40 detail", "ETHERCHANNEL DETAIL"),
        ("show interfaces Port-channel40", "Po40 INTERFACE (DOWN)"),
        ("show interfaces TenGigabitEthernet4/0/1", "Te4/0/1 INTERFACE (DOWN)"),
        ("show interfaces TenGigabitEthernet4/0/2", "Te4/0/2 INTERFACE (DOWN)"),
        ("show lacp 40 counters", "LACP COUNTERS"),
        ("show ip ospf neighbor", "OSPF NEIGHBORS"),
        ("show lisp session", "LISP SESSIONS"),
        ("show ip route summary", "ROUTE SUMMARY"),
        ("show cts role-based counters", "CTS COUNTERS"),
        ("show logging", "SYSLOG"),
    ]

    output_all = ""
    for cmd, label in commands:
        sub_banner(f"{label}: {cmd}")
        out = run_and_print(conn, cmd)
        output_all += f"\n--- {label}: {cmd} ---\n{out}\n"

    conn.disconnect()
    save_output(os.path.join(iter_dir, f"Iter{iteration}_During_L2H1_Failure.txt"), output_all)

    # ---- Step 2.5: BC1 During-Failure ----
    banner("STEP 2.5: BC1 DURING-FAILURE STATUS", '-')
    conn = connect(BC1)

    commands = [
        ("show etherchannel 40 summary", "ETHERCHANNEL SUMMARY"),
        ("show interfaces Port-channel40 | include line protocol|BW", "Po40 STATUS"),
        ("show lacp 40 counters", "LACP COUNTERS"),
        ("show ip ospf neighbor | include 192.168.102.40", "OSPF TO L2H-1"),
        ("show lisp session | include 192.168.102.40", "LISP TO L2H-1"),
        ("show logging", "SYSLOG"),
    ]

    output_all = ""
    for cmd, label in commands:
        sub_banner(f"{label}: {cmd}")
        out = run_and_print(conn, cmd)
        output_all += f"\n--- {label}: {cmd} ---\n{out}\n"

    conn.disconnect()
    save_output(os.path.join(iter_dir, f"Iter{iteration}_During_BC1_Status.txt"), output_all)

    # ---- Step 2.6: CC During-Failure ----
    banner("STEP 2.6: CATALYST CENTER DURING-FAILURE", '-')
    print("  ACTION REQUIRED:")
    print("    1. Provision > Inventory > FS2_L2H_1")
    print("       - Record: Reachability, Health Score")
    print("       - Expected: Degraded or Partial")
    print(f"    2. Screenshot: Iter{iteration}_During_CC_L2H1_Status.png")
    pause("Take CC during-failure screenshot, then press ENTER to proceed to RECOVERY")


# =============================================================================
# PHASE 3: RECOVERY
# =============================================================================

def phase3(iter_dir, iteration):
    banner(f"PHASE 3: RECOVERY - RESTORE ENTIRE PORT-CHANNEL  (Iteration {iteration})")
    print(f"  Timestamp: {ts()}")
    print()
    print("  ACTION: no shutdown BOTH members (restore Port-Channel)")
    print("  EXPECTED: Po40 UP with both members, OSPF FULL, LISP sessions UP")
    pause("Ready to RESTORE BOTH MEMBERS? Press ENTER to execute")

    # ---- Step 3.1: Execute Recovery ----
    banner("STEP 3.1: EXECUTING RECOVERY (no shutdown both)", '-')
    print("  Po40 is DOWN - TACACS likely unreachable, will try both auth methods")
    conn, auth_type = connect_smart(L2H1_TACACS, L2H1_LOCAL)
    print(f"  Authentication: {auth_type.upper()}")

    recovery_time = datetime.datetime.now()
    print(f"\n  >>> NO SHUTDOWN EXECUTED at {recovery_time.strftime('%H:%M:%S')} <<<\n")

    config_output = conn.send_config_set([
        'interface range TenGigabitEthernet4/0/1 - 2',
        'no shutdown'
    ])
    print(config_output)

    # ---- Step 3.2: Monitor Po40 Rebundle ----
    banner("STEP 3.2: MONITORING PORT-CHANNEL REBUNDLE", '-')
    print("  Monitoring every 5 seconds for up to 60 seconds...")
    rebundled = False
    for wait_total in [5, 10, 15, 20, 25, 30, 40, 50, 60]:
        time.sleep(5)
        now = datetime.datetime.now().strftime('%H:%M:%S')
        result = conn.send_command("show etherchannel 40 summary | include Po40|Te4")
        status = result.strip()
        print(f"  T+{wait_total:2d}s ({now}): {status}")
        if 'Po40' in status and 'RU' in status:
            if 'Te4/0/1(P)' in status and 'Te4/0/2(P)' in status:
                if not rebundled:
                    rebundle_time = wait_total
                    rebundled = True
                    print(f"  >>> Po40 FULLY BUNDLED (both members) in <= {rebundle_time} seconds <<<")

    if not rebundled:
        print("  WARNING: Po40 has NOT fully bundled after 60 seconds!")
        print("  Checking current status...")
        result = conn.send_command("show etherchannel 40 summary")
        print(result)

    # ---- Step 3.3: Monitor OSPF Adjacency ----
    banner("STEP 3.3: MONITORING OSPF ADJACENCY RESTORATION", '-')
    print("  Monitoring every 10 seconds for up to 40 seconds...")
    ospf_full = False
    for wait_total in [10, 20, 30, 40]:
        time.sleep(10)
        now = datetime.datetime.now().strftime('%H:%M:%S')
        result = conn.send_command("show ip ospf neighbor | include 192.168.40.1")
        status = result.strip()
        print(f"  T+{wait_total:2d}s ({now}): {status}")
        if 'FULL' in status:
            if not ospf_full:
                ospf_time = wait_total
                ospf_full = True
                print(f"  >>> OSPF ADJACENCY FULL in <= {ospf_time} seconds <<<")

    if not ospf_full:
        print("  WARNING: OSPF has NOT reached FULL after 40 seconds!")
        result = conn.send_command("show ip ospf neighbor")
        print(result)

    # ---- Step 3.4: Monitor LISP Sessions ----
    banner("STEP 3.4: MONITORING LISP SESSION RESTORATION", '-')
    print("  Checking LISP sessions...")
    time.sleep(10)
    result = conn.send_command("show lisp session")
    print(result)
    if 'Up' in result:
        print("  >>> LISP SESSIONS RESTORED <<<")
    else:
        print("  WARNING: Check LISP session status above")

    # Disconnect - Po40 is now up, TACACS should be reachable
    conn.disconnect()
    print("\n  Disconnected from L2H-1 (Po40 restored, TACACS should be reachable)")

    # ---- Step 3.5: Spirent Validation ----
    banner("STEP 3.5: SPIRENT POST-RECOVERY VALIDATION", '-')
    print("  ACTION REQUIRED:")
    print("    1. Wait 60 seconds to allow full convergence")
    print("    2. START Spirent traffic")
    print("    3. Clear counters")
    print("    4. Wait 60 seconds")
    print("    5. Verify: Loss % = 0.000%, Dead Streams = 0")
    print(f"    6. Screenshot: Iter{iteration}_Post_Spirent_Restored.png")
    pause("Take Spirent post-recovery screenshot, then press ENTER")

    # ---- Step 3.6: Full L2H-1 Post-Recovery Validation ----
    banner("STEP 3.6: L2H-1 FULL POST-RECOVERY VALIDATION", '-')
    print("  Po40 restored - TACACS should be reachable now")
    conn, auth_type = connect_smart(L2H1_TACACS, L2H1_LOCAL)
    print(f"  Authentication: {auth_type.upper()}")

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
        ("show logging", "SYSLOG"),
    ]

    output_all = ""
    for cmd, label in commands:
        sub_banner(f"{label}: {cmd}")
        out = run_and_print(conn, cmd)
        output_all += f"\n--- {label}: {cmd} ---\n{out}\n"

    conn.disconnect()
    save_output(os.path.join(iter_dir, f"Iter{iteration}_Post_L2H1_Validation.txt"), output_all)

    # ---- Step 3.7: BC1 Post-Recovery ----
    banner("STEP 3.7: BC1 FULL POST-RECOVERY VALIDATION", '-')
    conn = connect(BC1)

    commands = [
        ("show etherchannel 40 summary", "ETHERCHANNEL SUMMARY"),
        ("show interfaces Port-channel40 | include line protocol|BW", "Po40 STATUS"),
        ("show lacp 40 counters", "LACP COUNTERS"),
        ("show ip ospf neighbor", "OSPF NEIGHBORS"),
        ("show ip bgp summary", "BGP SUMMARY"),
        ("show lisp session", "LISP SESSIONS"),
        ("show logging", "SYSLOG"),
    ]

    output_all = ""
    for cmd, label in commands:
        sub_banner(f"{label}: {cmd}")
        out = run_and_print(conn, cmd)
        output_all += f"\n--- {label}: {cmd} ---\n{out}\n"

    conn.disconnect()
    save_output(os.path.join(iter_dir, f"Iter{iteration}_Post_BC1_Validation.txt"), output_all)

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
    parser = argparse.ArgumentParser(description='TC 07-02 Execution Script v2 (Robust)')
    parser.add_argument('--iter', type=int, default=1, choices=[1, 2, 3],
                        help='Iteration number (1, 2, or 3)')
    args = parser.parse_args()
    iteration = args.iter

    banner(f"TC 07-02: Link Failure L2 Border ENTIRE Port-Channel to Fabric BC", '=')
    print(f"  VERSION: 2.0 (Robust - Auto TACACS fallback)")
    print(f"  Iteration: {iteration}")
    print(f"  Start Time: {ts()}")
    print(f"  Primary DUT: FS2_L2H-1 (172.31.0.194)")
    print(f"  Target: BOTH Te4/0/1 AND Te4/0/2 (entire Po40)")
    print(f"  Peer: FS2_BC1 (172.31.2.0)")
    print()
    print("  AUTHENTICATION LOGIC:")
    print("    - Tries TACACS first (admin1) - works when Po40 UP")
    print("    - Falls back to local (admin) - works when Po40 DOWN")
    print("    - Automatically switches based on connectivity")
    print()
    print("  !!! WARNING: Complete Port-Channel failure - traffic loss expected !!!")
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
    print("    [ ] Po40 went DOWN during both member shutdown (EXPECTED)")
    print("    [ ] OSPF adjacency to BC1 went DOWN (EXPECTED)")
    print("    [ ] LISP session to BC1 went DOWN (EXPECTED)")
    print("    [ ] Spirent convergence measured (PLA Excel downloaded)")
    print("    [ ] Po40 restored with both members bundled")
    print("    [ ] OSPF adjacency restored to FULL")
    print("    [ ] LISP sessions restored")
    print("    [ ] Spirent post-recovery: 0.000% loss")
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
        print(f"    python3 run_tc_07-02_v2.py --iter {iteration + 1}")
    else:
        print("  ALL 3 ITERATIONS COMPLETE.")
        print("  Next: Create Word document deliverable.")

    print()


if __name__ == '__main__':
    main()
