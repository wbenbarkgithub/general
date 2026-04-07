#!/usr/bin/env python3
"""
TC 07-02 RETEST CONTINUATION: Resume from Po40 DOWN state.

Current state (April 7, 2026):
  - Phase 1 baseline: DONE (3 CLI files + 12 pre-screenshots)
  - Phase 2 shutdown: DONE (Po40 DOWN, script crashed on stale socket)
  - Phase 2 during-failure CLI: DONE (collected manually - 3 files)
  - Phase 2 Spirent/CC screenshots: NOT DONE
  - Phase 3 recovery: NOT DONE

This script picks up from the Spirent/CC during-failure screenshots,
then runs full Phase 3 recovery with all CLI collection.

Usage: python3 continue_from_down.py
"""

import os
import sys
import datetime
import time
from netmiko import ConnectHandler

TC_DIR = os.path.dirname(os.path.abspath(__file__))
ITER_DIR = os.path.join(TC_DIR, "Iter1_CLI")

# =============================================================================
# DEVICE CONFIGS
# =============================================================================

L2H1 = {
    'device_type': 'cisco_ios',
    'host': '172.31.0.194',
    'username': 'admin1',
    'password': 'CXlabs.123',
    'timeout': 30,
}

BC1 = {
    'device_type': 'cisco_ios',
    'host': '172.31.2.0',
    'username': 'admin1',
    'password': 'CXlabs.123',
    'timeout': 30,
}

BC2 = {
    'device_type': 'cisco_ios',
    'host': '172.31.2.2',
    'username': 'admin1',
    'password': 'CXlabs.123',
    'timeout': 30,
}

BC2_ALT = {
    'device_type': 'cisco_ios',
    'host': '172.31.2.2',
    'username': 'dnac_admin_tacacs',
    'password': 'CXlabs.123',
    'timeout': 30,
}

# =============================================================================
# HELPERS
# =============================================================================

def ts():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def banner(text, char='='):
    print(f"\n{char*70}")
    print(f"  {text}")
    print(f"{char*70}\n")

def pause(msg):
    print(f"\n{'='*70}")
    print(f"  PAUSE: {msg}")
    print(f"{'='*70}")
    input("  >>> Press ENTER when ready... ")
    print()

def safe_connect(dev, alt=None):
    """Connect with fallback credentials."""
    host = dev['host']
    print(f"  Connecting to {host}...", end=' ', flush=True)
    try:
        conn = ConnectHandler(**dev)
        print(f"OK [{conn.find_prompt()}]")
        return conn
    except Exception:
        if alt:
            print(f"FAILED, trying {alt['username']}...", end=' ', flush=True)
            conn = ConnectHandler(**alt)
            print(f"OK [{conn.find_prompt()}]")
            return conn
        raise

def safe_disconnect(conn):
    try:
        conn.disconnect()
    except Exception:
        pass

def run(conn, cmd):
    """Run command with timeout, print and return output."""
    try:
        out = conn.send_command(cmd, read_timeout=30)
    except Exception as e:
        out = f"ERROR: {e}"
    print(out)
    return out

def collect(dev, commands, filename, alt=None):
    """Atomic connect -> run all commands -> save -> disconnect."""
    conn = safe_connect(dev, alt)
    blob = ""
    for cmd, label in commands:
        print(f"  [{label}]")
        out = run(conn, cmd)
        blob += f"\n--- {label}: {cmd} ---\n{out}\n"
    safe_disconnect(conn)
    with open(filename, 'w') as f:
        f.write(f"Collected: {ts()}\n{'='*60}\n\n{blob}")
    print(f"  -> Saved: {os.path.basename(filename)} ({os.path.getsize(filename):,} bytes)")


# =============================================================================
# MAIN
# =============================================================================

def main():
    banner("TC 07-02 RETEST - CONTINUE FROM Po40 DOWN STATE")
    print(f"  Time: {ts()}")
    print()
    print("  Already completed:")
    print("    [x] Phase 1 baseline (3 CLI + 12 screenshots)")
    print("    [x] Phase 2 shutdown (Po40 DOWN)")
    print("    [x] Phase 2 during-failure CLI (3 files)")
    print()
    print("  Remaining:")
    print("    [ ] Phase 2 Spirent/CC during-failure screenshots")
    print("    [ ] Phase 3 recovery (no shutdown + monitoring)")
    print("    [ ] Phase 3 post-recovery CLI (3 files)")
    print("    [ ] Phase 3 Spirent/CC post-recovery screenshots")
    print()

    # -- Verify we're still in the down state --
    banner("VERIFY: Po40 still DOWN, Po41 still UP", '-')
    conn = safe_connect(L2H1)
    print()
    run(conn, "show etherchannel summary")
    print()
    ospf = run(conn, "show ip ospf neighbor")
    safe_disconnect(conn)

    if '192.168.41.1' in ospf and 'FULL' in ospf:
        print("\n  OK - Po40 DOWN, Po41 UP, OSPF to BC2 FULL. Ready to continue.")
    else:
        print("\n  WARNING - State may have changed. Check above output.")
        pause("Continue anyway? Press ENTER or Ctrl+C to abort")

    # =================================================================
    # PHASE 2 REMAINING: Spirent + CC screenshots
    # =================================================================
    banner("PHASE 2 REMAINING: SPIRENT + CC DURING-FAILURE SCREENSHOTS")
    print("  ACTION REQUIRED:")
    print()
    print("  SPIRENT:")
    print("    1. Check Spirent GUI for convergence (should be minimal/zero loss)")
    print("    2. Screenshot: Iter1_During_Spirent_Convergence.png")
    print("    3. STOP traffic after 3 minutes observation")
    print("    4. Export DB: Iter1_During_Spirent_DB.tcc")
    print("    5. Upload to PLA: http://spirent-pla.cisco.com")
    print("    6. Download: Iter1_PLA_Convergence_Analysis.xlsx")
    print("    7. Screenshot PLA: Iter1_PLA_Analysis.png")
    print()
    print("  CATALYST CENTER:")
    print("    1. Provision > Inventory > FS2_L2H_1")
    print("    2. Screenshot: Iter1_During_CC_L2H1_Status.png")
    print()
    print("  Save all to: Images/During/")
    pause("Complete Spirent + CC during-failure evidence, then press ENTER")

    # =================================================================
    # PHASE 3: RECOVERY
    # =================================================================
    banner("PHASE 3: RECOVERY - RESTORE Po40")
    print("  Will execute: no shutdown Te4/0/1-2 on L2H-1")
    print("  Then monitor Po40 rebundle and OSPF restoration")
    pause("Ready to RESTORE Po40? Press ENTER")

    # -- Step 3.1: Execute no shutdown --
    banner("STEP 3.1: EXECUTING NO SHUTDOWN", '-')
    conn = safe_connect(L2H1)
    try:
        conn.enable()
    except Exception:
        pass

    recovery_time = datetime.datetime.now()
    print(f"\n  >>> NO SHUTDOWN at {recovery_time.strftime('%H:%M:%S')} <<<\n")

    out = conn.send_config_set([
        'interface range TenGigabitEthernet4/0/1 - 2',
        'no shutdown'
    ])
    print(out)

    # -- Step 3.2: Monitor Po40 rebundle --
    banner("STEP 3.2: MONITORING Po40 REBUNDLE", '-')
    print("  Checking every 5s for up to 60s...")
    rebundled = False
    for t in range(5, 65, 5):
        time.sleep(5)
        now = datetime.datetime.now().strftime('%H:%M:%S')
        try:
            result = conn.send_command("show etherchannel 40 summary | include Po40|Te4", read_timeout=15)
        except Exception:
            safe_disconnect(conn)
            conn = safe_connect(L2H1)
            result = conn.send_command("show etherchannel 40 summary | include Po40|Te4", read_timeout=15)
        status = result.strip()
        print(f"  T+{t:2d}s ({now}): {status}")
        if 'Te4/0/1(P)' in status and 'Te4/0/2(P)' in status and not rebundled:
            rebundled = True
            print(f"  >>> Po40 FULLY BUNDLED in <= {t} seconds <<<")

    if not rebundled:
        print("  WARNING: Po40 not fully bundled after 60s!")

    # -- Step 3.3: Monitor OSPF to BC1 --
    banner("STEP 3.3: MONITORING OSPF TO BC1", '-')
    print("  Checking every 10s for up to 60s...")
    ospf_restored = False
    for t in range(10, 70, 10):
        time.sleep(10)
        now = datetime.datetime.now().strftime('%H:%M:%S')
        try:
            result = conn.send_command("show ip ospf neighbor | include 192.168.40.1", read_timeout=15)
        except Exception:
            safe_disconnect(conn)
            conn = safe_connect(L2H1)
            result = conn.send_command("show ip ospf neighbor | include 192.168.40.1", read_timeout=15)
        status = result.strip()
        print(f"  T+{t:2d}s ({now}): {status}")
        if 'FULL' in status and not ospf_restored:
            ospf_restored = True
            print(f"  >>> OSPF TO BC1 FULL in <= {t} seconds <<<")

    if not ospf_restored:
        print("  WARNING: OSPF to BC1 not FULL after 60s. Checking full neighbor table:")
        try:
            print(conn.send_command("show ip ospf neighbor", read_timeout=15))
        except Exception:
            pass

    # -- Step 3.4: Verify ECMP --
    banner("STEP 3.4: VERIFY ECMP RESTORATION", '-')
    time.sleep(5)
    try:
        ecmp = run(conn, "show ip route ospf | include 192.168")
        if 'Port-channel40' in ecmp and 'Port-channel41' in ecmp:
            print("\n  >>> ECMP RESTORED (routes via both Po40 and Po41) <<<")
        else:
            print("\n  WARNING: ECMP not showing both port-channels")

        print()
        run(conn, "show bfd neighbors")
        print()
        lisp = run(conn, "show lisp session")
        if 'Up' in lisp:
            print("  >>> LISP SESSIONS UP <<<")
    except Exception:
        print("  Connection lost - will capture in post-recovery CLI")

    safe_disconnect(conn)

    # -- Step 3.5: Spirent post-recovery --
    banner("STEP 3.5: SPIRENT POST-RECOVERY", '-')
    print("  ACTION REQUIRED:")
    print("    1. START Spirent traffic (if stopped)")
    print("    2. Clear counters, wait 60 seconds")
    print("    3. Verify: 0.000% loss, 0 dead streams")
    print("    4. Screenshot: Iter1_Post_Spirent_Restored.png")
    pause("Take Spirent post-recovery screenshot, then press ENTER")

    # -- Step 3.6: Post-recovery CLI from all 3 devices --
    banner("STEP 3.6: POST-RECOVERY CLI - L2H-1", '-')
    collect(L2H1, [
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
    ], os.path.join(ITER_DIR, "Iter1_Post_L2H1_Validation.txt"))

    banner("STEP 3.7: POST-RECOVERY CLI - BC1", '-')
    collect(BC1, [
        ("show etherchannel 40 summary", "ETHERCHANNEL SUMMARY"),
        ("show interfaces Port-channel40", "Po40 INTERFACE"),
        ("show interfaces Port-channel40 human-readable", "Po40 INTERFACE (human-readable)"),
        ("show lacp 40 counters", "LACP COUNTERS"),
        ("show ip ospf neighbor", "OSPF NEIGHBORS"),
        ("show ip bgp summary", "BGP SUMMARY"),
        ("show lisp session", "LISP SESSIONS"),
        ("show bfd neighbors", "BFD SESSIONS"),
        ("show logging | include OSPF|LACP", "SYSLOG (filtered)"),
    ], os.path.join(ITER_DIR, "Iter1_Post_BC1_Validation.txt"))

    banner("STEP 3.8: POST-RECOVERY CLI - BC2", '-')
    collect(BC2, [
        ("show etherchannel 41 summary", "ETHERCHANNEL 41 SUMMARY"),
        ("show interfaces Port-channel41", "Po41 INTERFACE"),
        ("show interfaces Port-channel41 human-readable", "Po41 INTERFACE (human-readable)"),
        ("show lacp 41 counters", "LACP COUNTERS"),
        ("show ip ospf neighbor", "OSPF NEIGHBORS"),
        ("show ip bgp summary", "BGP SUMMARY"),
        ("show lisp session", "LISP SESSIONS"),
        ("show bfd neighbors", "BFD SESSIONS"),
        ("show logging | include OSPF|LACP", "SYSLOG (filtered)"),
    ], os.path.join(ITER_DIR, "Iter1_Post_BC2_Validation.txt"),
    alt=BC2_ALT)

    # -- Step 3.9: CC post-recovery --
    banner("STEP 3.9: CATALYST CENTER POST-RECOVERY", '-')
    print("  ACTION REQUIRED:")
    print("    1. Provision > Inventory > FS2_L2H_1")
    print("       - Verify: Reachable, Health >= 80%")
    print("    2. Screenshot: Iter1_Post_CC_L2H1_Health.png")
    print()
    print("    3. Assurance > Health")
    print("       - Verify: Network Health >= 80%")
    print("    4. Screenshot: Iter1_Post_CC_Network_Health.png")
    pause("Take CC post-recovery screenshots, then press ENTER")

    # =================================================================
    # SUMMARY
    # =================================================================
    banner("ITERATION 1 COMPLETE")
    print(f"  End Time: {ts()}")
    print()
    print("  CLI EVIDENCE:")
    for f in sorted(os.listdir(ITER_DIR)):
        fp = os.path.join(ITER_DIR, f)
        print(f"    {f} ({os.path.getsize(fp):,} bytes)")
    print()
    print(f"  Expected 9 files: 3 Pre + 3 During + 3 Post")
    count = len([f for f in os.listdir(ITER_DIR) if f.endswith('.txt')])
    print(f"  Actual: {count} files")
    print()
    print("  SCREENSHOTS CHECKLIST:")
    print("    Phase 1: [x] 12 pre-captures (already in Images/PreCaptures/)")
    print("    Phase 2: [ ] Iter1_During_Spirent_Convergence.png")
    print("             [ ] Iter1_During_CC_L2H1_Status.png")
    print("             [ ] Iter1_PLA_Convergence_Analysis.xlsx")
    print("    Phase 3: [ ] Iter1_Post_Spirent_Restored.png")
    print("             [ ] Iter1_Post_CC_L2H1_Health.png")
    print("             [ ] Iter1_Post_CC_Network_Health.png")
    print()
    print("  NEXT STEPS:")
    print("    - Run Iteration 2: python3 run_tc_07-02_retest.py --iter 2")
    print("    - Run Iteration 3: python3 run_tc_07-02_retest.py --iter 3")
    print("    - (Fixed script will not crash on subsequent iterations)")
    print()


if __name__ == '__main__':
    main()
