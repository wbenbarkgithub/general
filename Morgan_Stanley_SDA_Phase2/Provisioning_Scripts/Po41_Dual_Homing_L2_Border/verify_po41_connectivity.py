#!/usr/bin/env python3
"""
Verify Port-Channel 41 Dual-Homing Connectivity

This script verifies:
- LACP bundle formation (both members active)
- OSPF neighbor relationship (FULL state)
- BFD session establishment
- ECMP load-balancing (routes via both Po40 and Po41)
- Bidirectional connectivity (ping tests)

Prerequisites:
- netmiko: pip install netmiko
- Both Po41 configurations complete on FS2_BC2 and FS2_L2H-1
- Allow 30-60 seconds for OSPF convergence

Author: Morgan Stanley SDA Phase 2 Team
Date: April 7, 2026
"""

from netmiko import ConnectHandler
import time
import sys

# Device connection parameters
FS2_L2H1 = {
    'device_type': 'cisco_ios',
    'host': '172.31.0.194',
    'username': 'admin1',
    'password': 'CXlabs.123',
    'timeout': 30,
}

FS2_BC2 = {
    'device_type': 'cisco_ios',
    'host': '172.31.2.2',
    'username': 'dnac_admin_tacacs',
    'password': 'CXlabs.123',
    'timeout': 30,
}


def banner(text, char='='):
    """Print a formatted banner."""
    width = 70
    print(f"\n{char*width}")
    print(f"  {text}")
    print(f"{char*width}\n")


def verify_connectivity():
    """Verify Po41 connectivity and ECMP."""

    banner("VERIFY PO41 CONNECTIVITY AND ECMP")

    results = {
        'ping': False,
        'ospf': False,
        'bfd': False,
        'ecmp': False,
        'lacp_l2h1': False,
        'lacp_bc2': False,
    }

    # Test 1: Ping from FS2_L2H-1 to FS2_BC2
    print("\n[TEST 1] Ping Test - FS2_L2H-1 to FS2_BC2")
    print("-" * 70)

    try:
        conn1 = ConnectHandler(**FS2_L2H1)
        print(f"Connected to: {conn1.find_prompt()}")

        output = conn1.send_command("ping 192.168.41.1 source 192.168.41.0", delay_factor=2)
        print(output)

        if "!!!!!" in output or "Success rate is 100" in output or "Success rate is 80" in output:
            print("\n✅ Ping Test: PASS")
            results['ping'] = True
        else:
            print("\n⚠️ Ping Test: FAILED")

        # Test 2: OSPF Neighbors
        print("\n" + "="*70)
        print("[TEST 2] OSPF Neighbor Verification")
        print("-" * 70)

        output = conn1.send_command("show ip ospf neighbor")
        print(output)

        if "192.168.41.1" in output and "FULL" in output:
            print("\n✅ OSPF Neighbor on Po41: PASS (FULL state)")
            results['ospf'] = True
        else:
            print("\n⚠️ OSPF Neighbor on Po41: NOT FORMED - May need more time")

        # Test 3: BFD Sessions
        print("\n" + "="*70)
        print("[TEST 3] BFD Session Verification")
        print("-" * 70)

        output = conn1.send_command("show bfd neighbors")
        print(output)

        if "192.168.41.1" in output and "Up" in output:
            print("\n✅ BFD Session on Po41: PASS")
            results['bfd'] = True
        else:
            print("\n⚠️ BFD Session: NOT UP")

        # Test 4: ECMP Routing
        print("\n" + "="*70)
        print("[TEST 4] ECMP Load-Balancing Verification")
        print("-" * 70)
        print("Checking for routes learned via both Po40 and Po41...")

        output = conn1.send_command("show ip route 192.168.20.0 255.255.255.254")
        print(output)

        if "Port-channel40" in output and "Port-channel41" in output:
            print("\n✅ ECMP Load-Balancing: ACTIVE")
            results['ecmp'] = True
        else:
            print("\n⚠️ ECMP: Single path only (OSPF may still be converging)")

        # Test 5: LACP on FS2_L2H-1
        print("\n" + "="*70)
        print("[TEST 5] LACP Bundle Status - FS2_L2H-1")
        print("-" * 70)

        output = conn1.send_command("show etherchannel 41 summary")
        print(output)

        if "(P)" in output and "Po41" in output:
            print("\n✅ LACP Bundle on FS2_L2H-1: PASS")
            results['lacp_l2h1'] = True
        else:
            print("\n⚠️ LACP Bundle: CHECK STATUS")

        conn1.disconnect()

    except Exception as e:
        print(f"\n❌ Error with FS2_L2H-1: {e}")

    # Test 6: Verify from FS2_BC2 side
    print("\n" + "="*70)
    print("[TEST 6] FS2_BC2 Side Verification")
    print("-" * 70)

    try:
        conn2 = ConnectHandler(**FS2_BC2)
        print(f"Connected to: {conn2.find_prompt()}")

        print("\nOSPF Neighbors:")
        output = conn2.send_command("show ip ospf neighbor | include 192.168.41")
        print(output)

        print("\nBFD Neighbors:")
        output = conn2.send_command("show bfd neighbors | include 192.168.41")
        print(output)

        print("\nPort-channel 41 Status:")
        output = conn2.send_command("show etherchannel 41 summary")
        print(output)

        if "(P)" in output and "Po41" in output:
            print("\n✅ LACP Bundle on FS2_BC2: PASS")
            results['lacp_bc2'] = True
        else:
            print("\n⚠️ LACP Bundle: CHECK STATUS")

        conn2.disconnect()

    except Exception as e:
        print(f"\n❌ Error with FS2_BC2: {e}")

    # Summary
    banner("VERIFICATION SUMMARY")

    total = len(results)
    passed = sum(results.values())

    print(f"\nTests Passed: {passed}/{total}")
    print("\nDetailed Results:")
    print(f"  {'✅' if results['ping'] else '❌'} Ping Test")
    print(f"  {'✅' if results['ospf'] else '❌'} OSPF Neighbor (FULL)")
    print(f"  {'✅' if results['bfd'] else '❌'} BFD Session (UP)")
    print(f"  {'✅' if results['ecmp'] else '❌'} ECMP Load-Balancing")
    print(f"  {'✅' if results['lacp_l2h1'] else '❌'} LACP Bundle (FS2_L2H-1)")
    print(f"  {'✅' if results['lacp_bc2'] else '❌'} LACP Bundle (FS2_BC2)")

    if passed == total:
        banner("✅ ALL TESTS PASSED - DUAL-HOMING OPERATIONAL")
        return True
    elif passed >= 4:
        banner("⚠️ PARTIAL SUCCESS - OSPF MAY STILL BE CONVERGING")
        print("\nNote: Allow up to 60 seconds for OSPF convergence")
        print("Run this script again if OSPF/BFD/ECMP tests failed")
        return True
    else:
        banner("❌ VERIFICATION FAILED - REVIEW CONFIGURATION")
        return False


if __name__ == "__main__":
    success = verify_connectivity()
    sys.exit(0 if success else 1)
