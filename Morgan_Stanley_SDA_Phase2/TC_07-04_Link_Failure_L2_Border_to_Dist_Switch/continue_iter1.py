#!/usr/bin/env python3
"""
TC 07-04 Iteration 1 — CONTINUE from crash point.

Crash occurred: Step 2.2 (reconnect to L2H-1 after shutdown of Te4/0/20)
Already completed: Phase 1 baseline (all 4 Pre files), Te4/0/20 SHUTDOWN at 20:45:36
Remaining: Step 2.2 verification, Steps 2.3-2.8, Phase 3 recovery

Te4/0/20 is currently SHUT DOWN on FS2_L2H-1.
"""

import os
import datetime
import time
from netmiko import ConnectHandler

TC_DIR = os.path.dirname(os.path.abspath(__file__))
ITER_DIR = os.path.join(TC_DIR, "Iter1_CLI")
ITERATION = 1

# =============================================================================
# DEVICE CREDENTIALS
# =============================================================================

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
    print(f"\n{char*70}")
    print(f"  {text}")
    print(f"{char*70}\n")

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
    return connect(L2H1_TACACS, try_alt=L2H1_LOCAL)

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
    with open(filename, 'w') as f:
        f.write(f"Collected: {ts()}\n{'='*60}\n\n")
        f.write(output_all)
    size = os.path.getsize(filename)
    print(f"  Saved: {os.path.basename(filename)} ({size:,} bytes)")

# =============================================================================
# COMMAND SETS
# =============================================================================

L2H1_DURING_CMDS = [
    ("show interfaces TenGigabitEthernet4/0/20 | include line protocol|BW", "Te4/0/20 STATUS (DOWN)"),
    ("show interfaces TenGigabitEthernet4/0/20 human-readable", "Te4/0/20 (human-readable, DOWN)"),
    ("show interfaces TenGigabitEthernet4/0/21 | include line protocol|BW", "Te4/0/21 STATUS (UP - redundant)"),
    ("show interfaces TenGigabitEthernet4/0/21 human-readable", "Te4/0/21 (human-readable, UP)"),
    ("show interfaces trunk", "TRUNKS (Te4/0/21 MUST be present)"),
    ("show spanning-tree vlan 101", "STP VLAN 101 (reconverged via Te4/0/21)"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301 (reconverged via Te4/0/21)"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
    ("show interfaces vlan 101", "SVI VLAN 101 (should stay UP)"),
    ("show interfaces vlan 1301", "SVI VLAN 1301 (should stay UP)"),
    ("show etherchannel summary", "ETHERCHANNELS (MUST be RU)"),
    ("show interfaces Port-channel40 | include line protocol|BW|5 minute", "Po40 (MUST be UP)"),
    ("show interfaces Port-channel41 | include line protocol|BW|5 minute", "Po41 (MUST be UP)"),
    ("show ip ospf neighbor", "OSPF (MUST be FULL to both BCs)"),
    ("show bfd neighbors", "BFD (MUST be UP to both BCs)"),
    ("show lisp session", "LISP (MUST be 2/2 established)"),
    ("show ip route summary", "ROUTE SUMMARY"),
    ("show cts role-based counters", "CTS COUNTERS"),
    ("show logging | include LINK|UPDOWN|LINEPROTO|STP", "SYSLOG (filtered)"),
]

L2H1_FULL_CMDS = [
    ("show version | include uptime", "UPTIME"),
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
    ("show etherchannel summary", "ALL ETHERCHANNELS"),
    ("show interfaces Port-channel40 | include line protocol|BW|5 minute", "Po40 STATUS"),
    ("show interfaces Port-channel41 | include line protocol|BW|5 minute", "Po41 STATUS"),
    ("show ip ospf neighbor", "OSPF NEIGHBORS"),
    ("show bfd neighbors", "BFD SESSIONS"),
    ("show lisp session", "LISP SESSIONS"),
    ("show ip route summary", "ROUTE SUMMARY"),
    ("show cts role-based counters", "CTS COUNTERS"),
]

DIST1_DURING_CMDS = [
    ("show interfaces TenGigabitEthernet4/0/20 | include line protocol|BW", "Te4/0/20 (DOWN)"),
    ("show interfaces TenGigabitEthernet4/0/20 human-readable", "Te4/0/20 (human-readable, DOWN)"),
    ("show interfaces trunk", "TRUNKS (Te4/0/20 absent)"),
    ("show spanning-tree vlan 101", "STP VLAN 101 (root lost)"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301 (root lost)"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101 (aging)"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301 (aging)"),
    ("show logging | include LINK|UPDOWN|LINEPROTO|STP", "SYSLOG (filtered)"),
]

DIST2_DURING_CMDS = [
    ("show interfaces TenGigabitEthernet1/0/20 | include line protocol|BW", "Te1/0/20 (MUST be UP)"),
    ("show interfaces TenGigabitEthernet1/0/20 human-readable", "Te1/0/20 (human-readable)"),
    ("show interfaces trunk", "TRUNKS (Te1/0/20 MUST be present)"),
    ("show spanning-tree vlan 101", "STP VLAN 101 (may become new active path)"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301 (may become new active path)"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
    ("show logging | include LINK|UPDOWN|LINEPROTO|STP", "SYSLOG (filtered)"),
]

BC1_CHECK_CMDS = [
    ("show etherchannel 40 summary", "ETHERCHANNEL 40 SUMMARY"),
    ("show ip ospf neighbor | include 192.168.102.40", "OSPF TO L2H-1"),
    ("show lisp session | include 192.168.102.40", "LISP TO L2H-1"),
    ("show bfd neighbors | include 192.168.40.0", "BFD TO L2H-1"),
]

DIST1_POST_CMDS = [
    ("show interfaces TenGigabitEthernet4/0/20", "Te4/0/20 (trunk to L2H-1)"),
    ("show interfaces TenGigabitEthernet4/0/20 human-readable", "Te4/0/20 (human-readable)"),
    ("show interfaces trunk", "ALL TRUNKS"),
    ("show spanning-tree vlan 101", "STP VLAN 101"),
    ("show spanning-tree vlan 1301", "STP VLAN 1301"),
    ("show mac address-table vlan 101", "MAC TABLE VLAN 101"),
    ("show mac address-table vlan 1301", "MAC TABLE VLAN 1301"),
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
    ("show logging | include LINK|UPDOWN|LINEPROTO|STP", "SYSLOG (filtered)"),
]


# =============================================================================
# MAIN — RESUME FROM STEP 2.2
# =============================================================================

def main():
    banner("TC 07-04 ITER 1 — CONTINUING FROM CRASH POINT")
    print(f"  Resume Time: {ts()}")
    print(f"  Te4/0/20 was SHUTDOWN at 20:45:36")
    print(f"  Phase 1 baseline: COMPLETE (4 Pre files)")
    print(f"  Resuming at: Step 2.2 Immediate Verification")
    print()

    # ---- Step 2.2: Immediate Verification ----
    banner("STEP 2.2: IMMEDIATE VERIFICATION (RESUMED)", '-')
    print(f"  Verification at: {ts()}")

    conn = connect_l2h1()

    sub_banner("Te4/0/20 status (should be admin down)")
    run_cmd(conn, "show interfaces TenGigabitEthernet4/0/20 | include line protocol|BW")

    sub_banner("Te4/0/21 status (MUST remain UP)")
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
    print("  Expected State:")
    print("    X  Te4/0/20: admin down, line protocol down")
    print("    OK Te4/0/21: UP (redundant trunk to L2-DIST-2)")
    print("    OK Po40 + Po41: UP (RU)")
    print("    OK OSPF: FULL to both BCs")
    print("    OK BFD: UP to both BCs")
    print("    OK LISP: 2/2 established")

    if 'FULL' in ospf_out:
        full_count = ospf_out.count('FULL')
        print(f"\n  >>> FABRIC HEALTHY: {full_count} OSPF FULL adjacencies maintained <<<")
    else:
        print("\n  !!! WARNING: No OSPF FULL adjacencies found — investigate!")

    # ---- Step 2.3: Spirent Convergence ----
    banner("STEP 2.3: SPIRENT CONVERGENCE MEASUREMENT", '-')
    print("  NOTE: Te4/0/20 has been down since 20:45:36.")
    print("  STP should have already converged via Te4/0/21.")
    print()
    print("  ACTION REQUIRED:")
    print("    1. Check Spirent GUI — note current stream status")
    print("    2. Record dead/dropped streams (if any)")
    print(f"    3. Screenshot: Iter1_During_Spirent_Convergence.png")
    print()
    print("    4. STOP traffic")
    print(f"    5. Export DB: Iter1_During_Spirent.tcc")
    print("    6. Upload to PLA: http://spirent-pla.cisco.com")
    print(f"    7. Download Excel: Iter1_PLA_Convergence.xlsx")
    print(f"    8. Screenshot PLA: Iter1_PLA_Analysis.png")
    pause("Complete Spirent measurement, then press ENTER")

    # ---- Step 2.4: L2H-1 During CLI ----
    banner("STEP 2.4: L2H-1 DURING-FAILURE CLI", '-')
    collect_commands(L2H1_TACACS, L2H1_DURING_CMDS,
        os.path.join(ITER_DIR, "Iter1_During_L2H1_Failure.txt"),
        try_alt=L2H1_LOCAL)

    # ---- Step 2.5: L2-DIST-1 During CLI ----
    banner("STEP 2.5: L2-DIST-1 DURING-FAILURE CLI (AFFECTED)", '-')
    collect_commands(DIST1, DIST1_DURING_CMDS,
        os.path.join(ITER_DIR, "Iter1_During_DIST1_Status.txt"))

    # ---- Step 2.6: L2-DIST-2 During CLI ----
    banner("STEP 2.6: L2-DIST-2 DURING-FAILURE CLI (REDUNDANT PATH)", '-')
    collect_commands(DIST2, DIST2_DURING_CMDS,
        os.path.join(ITER_DIR, "Iter1_During_DIST2_Status.txt"))

    # ---- Step 2.7: BC1 During CLI ----
    banner("STEP 2.7: BC1 FABRIC HEALTH DURING FAILURE", '-')
    collect_commands(BC1, BC1_CHECK_CMDS,
        os.path.join(ITER_DIR, "Iter1_During_BC1_Health.txt"),
        try_alt=BC1_ALT)

    # ---- Step 2.8: CC During ----
    banner("STEP 2.8: CATALYST CENTER DURING FAILURE", '-')
    print("  ACTION REQUIRED:")
    print("    1. Provision > Inventory > FS2_L2H_1")
    print("       - Expected: Still Reachable (fabric side unaffected)")
    print("       - NOTE: Interface status is NOT real-time (last sync)")
    print("    2. Screenshot: Iter1_During_CC_Status.png")
    pause("Take CC during-failure screenshot, then press ENTER to RECOVERY")

    # ==== PHASE 3: RECOVERY ====
    banner("PHASE 3: RECOVERY - RESTORE Te4/0/20 (Iteration 1)")
    print(f"  Timestamp: {ts()}")
    print()
    print("  ACTION: no shutdown Te4/0/20 on L2H-1")
    print("  EXPECTED: Trunk comes up, STP converges, both trunks active.")
    pause("Ready to RESTORE Te4/0/20? Press ENTER to execute")

    # ---- Step 3.1: Execute Recovery ----
    banner("STEP 3.1: EXECUTING RECOVERY (no shutdown Te4/0/20)", '-')
    conn = connect_l2h1()

    try:
        conn.enable()
    except Exception:
        pass

    recovery_time = datetime.datetime.now()
    print(f"\n  >>> NO SHUTDOWN Te4/0/20 at {recovery_time.strftime('%H:%M:%S')} <<<\n")

    config_output = conn.send_config_set([
        'interface TenGigabitEthernet4/0/20',
        'no shutdown'
    ])
    print(config_output)

    # ---- Step 3.2: Monitor Link Up + STP ----
    banner("STEP 3.2: MONITORING Te4/0/20 LINK UP + STP CONVERGENCE", '-')
    print("  Checking every 5s for up to 60s...")
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
            print(f"  >>> Te4/0/20 LINK UP at T+{t}s <<<")

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
        print("  WARNING: Te4/0/20 not UP after 60s — check interface!")
    if link_up and not stp_fwd:
        print("  WARNING: STP not forwarding after 60s — may still be learning")
        try:
            print(conn.send_command("show spanning-tree vlan 101", read_timeout=15))
        except Exception:
            pass

    # ---- Step 3.3: Verify Trunks ----
    banner("STEP 3.3: VERIFY BOTH TRUNKS RESTORED", '-')
    time.sleep(5)
    try:
        trunk_out = run_cmd(conn, "show interfaces trunk")
        if 'Te4/0/20' in trunk_out and 'Te4/0/21' in trunk_out:
            print("\n  >>> BOTH TRUNKS ACTIVE: Te4/0/20 + Te4/0/21 <<<")
        elif 'Te4/0/20' in trunk_out:
            print("\n  >>> Te4/0/20 trunk restored")
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
    print("    5. Screenshot: Iter1_Post_Spirent_Restored.png")
    pause("Take Spirent post-recovery screenshot, then press ENTER")

    # ---- Step 3.5-3.8: Post-Recovery CLI ----
    banner("STEP 3.5: L2H-1 POST-RECOVERY CLI", '-')
    collect_commands(L2H1_TACACS, L2H1_FULL_CMDS + [
        ("show logging | include LINK|UPDOWN|LINEPROTO|STP", "SYSLOG (filtered)"),
    ], os.path.join(ITER_DIR, "Iter1_Post_L2H1_Validation.txt"),
        try_alt=L2H1_LOCAL)

    banner("STEP 3.6: L2-DIST-1 POST-RECOVERY CLI", '-')
    collect_commands(DIST1, DIST1_POST_CMDS,
        os.path.join(ITER_DIR, "Iter1_Post_DIST1_Validation.txt"))

    banner("STEP 3.7: L2-DIST-2 POST-RECOVERY CLI", '-')
    collect_commands(DIST2, DIST2_POST_CMDS,
        os.path.join(ITER_DIR, "Iter1_Post_DIST2_Validation.txt"))

    banner("STEP 3.8: BC1 FABRIC HEALTH POST-RECOVERY", '-')
    collect_commands(BC1, BC1_CHECK_CMDS,
        os.path.join(ITER_DIR, "Iter1_Post_BC1_Health.txt"),
        try_alt=BC1_ALT)

    # ---- Step 3.9: CC Post-Recovery ----
    banner("STEP 3.9: CATALYST CENTER POST-RECOVERY", '-')
    print("  ACTION REQUIRED:")
    print("    1. Provision > Inventory > FS2_L2H_1 - Verify Reachable")
    print("       NOTE: Interface status reflects last sync, not real-time")
    print("    2. Screenshot: Iter1_Post_CC_L2H1_Health.png")
    print("    3. Assurance > Health >= 80%")
    print("    4. Screenshot: Iter1_Post_CC_Health.png")
    pause("Take CC post-recovery screenshots, then press ENTER")

    # ---- Summary ----
    banner("ITERATION 1 COMPLETE")
    print(f"  End Time: {ts()}")
    print()
    print("  RESULTS CHECKLIST:")
    print("    [ ] Te4/0/20 went DOWN during shutdown (EXPECTED)")
    print("    [ ] Te4/0/21 REMAINED UP — redundant path active (CRITICAL)")
    print("    [ ] STP reconverged traffic via Te4/0/21 to L2-DIST-2")
    print("    [ ] Packet loss measured during STP convergence (Spirent/PLA)")
    print("    [ ] Po40 + Po41 REMAINED UP (CRITICAL — fabric unaffected)")
    print("    [ ] OSPF FULL to BOTH BCs during failure (CRITICAL)")
    print("    [ ] BFD UP to both BCs during failure (CRITICAL)")
    print("    [ ] LISP 2/2 established during failure (CRITICAL)")
    print("    [ ] Te4/0/20 restored after no shutdown")
    print("    [ ] Both trunks active (Te4/0/20 + Te4/0/21)")
    print("    [ ] STP converged to Forwarding on Te4/0/20")
    print("    [ ] Spirent 0.000% loss after recovery")
    print()
    print("  CLI EVIDENCE:")
    for f in sorted(os.listdir(ITER_DIR)):
        fpath = os.path.join(ITER_DIR, f)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            print(f"    {f} ({size:,} bytes)")
    print()
    print("  Next: python3 run_tc_07-04.py --iter 2")
    print()


if __name__ == '__main__':
    main()
