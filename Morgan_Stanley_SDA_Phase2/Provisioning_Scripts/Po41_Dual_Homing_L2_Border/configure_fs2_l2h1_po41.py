#!/usr/bin/env python3
"""
Configure Port-Channel 41 on FS2_L2H-1 for Dual-Homing to FS2_BC2

This script configures:
- Physical interfaces Te4/0/3-4
- Port-channel 41 with LACP
- IP addressing (192.168.41.0/31)
- OSPF Area 0 with MD5 authentication
- BFD for fast failure detection
- Removes passive-interface restriction

Prerequisites:
- netmiko: pip install netmiko
- Network connectivity to FS2_L2H-1 (172.31.0.194)
- Valid credentials (admin1)
- FS2_BC2 Po41 already configured (run configure_fs2_bc2_po41.py first)

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
    'timeout': 60,
}

# OSPF MD5 key from existing Po40 configuration
OSPF_MD5_KEY = '01300F175804485E731F'


def banner(text, char='='):
    """Print a formatted banner."""
    width = 70
    print(f"\n{char*width}")
    print(f"  {text}")
    print(f"{char*width}\n")


def configure_fs2_l2h1():
    """Configure FS2_L2H-1 with Po41 to FS2_BC2."""

    banner("CONFIGURE FS2_L2H-1 PORT-CHANNEL 41")

    try:
        print("[1/6] Connecting to FS2_L2H-1 (172.31.0.194)...")
        conn = ConnectHandler(**FS2_L2H1)
        print(f"     Connected: {conn.find_prompt()}")

        # Check current interface status
        print("\n[2/6] Checking current interface status...")
        output = conn.send_command("show interfaces status | include Te4/0/[34]")
        print(output)

        # Configure physical interfaces
        print("\n[3/6] Configuring physical interfaces Te4/0/3 and Te4/0/4...")
        physical_config = [
            "default interface TenGigabitEthernet4/0/3",
            "default interface TenGigabitEthernet4/0/4",
            "interface TenGigabitEthernet4/0/3",
            "description to FS2_BC2 Fif2/0/13",
            "no switchport",
            "mtu 9100",
            "no ip address",
            "channel-group 41 mode active",
            "lacp rate fast",
            "service-policy output DNA-dscp#APIC_QOS_Q_OUT",
            "no shutdown",
            "exit",
            "interface TenGigabitEthernet4/0/4",
            "description to FS2_BC2 Fif2/0/14",
            "no switchport",
            "mtu 9100",
            "no ip address",
            "channel-group 41 mode active",
            "lacp rate fast",
            "service-policy output DNA-dscp#APIC_QOS_Q_OUT",
            "no shutdown",
            "exit",
        ]

        output = conn.send_config_set(physical_config)
        print(output)

        # Configure Port-channel 41
        print("\n[4/6] Configuring Port-channel 41...")
        po_config = [
            "interface Port-channel41",
            "description connectivity to FS2_BC2",
            "no switchport",
            "mtu 9100",
            "ip address 192.168.41.0 255.255.255.254",
            "no ip redirects",
            "no ip proxy-arp",
            "ip pim sparse-mode",
            f"ip ospf message-digest-key 1 md5 7 {OSPF_MD5_KEY}",
            "ip ospf network point-to-point",
            "ip ospf 1 area 0.0.0.0",
            "ip ospf cost 100",
            "bfd interval 750 min_rx 750 multiplier 3",
            "no bfd echo",
            "exit",
        ]

        output = conn.send_config_set(po_config)
        print(output)

        # Remove passive-interface restriction
        print("\n[5/6] Removing OSPF passive-interface for Po41...")
        ospf_config = [
            "router ospf 1",
            "no passive-interface Port-channel41",
            "exit",
        ]

        output = conn.send_config_set(ospf_config)
        print(output)

        # Verification
        banner("VERIFICATION - FS2_L2H-1", '-')

        time.sleep(5)  # Wait for LACP to form

        print("\n[CHECK 1] Interface status:")
        output = conn.send_command("show interfaces status | include Te4/0/[34]|Po4")
        print(output)

        print("\n[CHECK 2] Port-channel summary (both Po40 and Po41):")
        output = conn.send_command("show etherchannel summary | include Po4")
        print(output)

        print("\n[CHECK 3] LACP neighbor:")
        output = conn.send_command("show lacp neighbor | begin Channel")
        print(output)

        print("\n[CHECK 4] Port-channel 41 config:")
        output = conn.send_command("show run interface Port-channel41")
        print(output)

        # Save configuration
        print("\n[6/6] Saving configuration...")
        output = conn.send_command("write memory", read_timeout=30)
        print(output)

        conn.disconnect()

        banner("✅ FS2_L2H-1 CONFIGURATION COMPLETE")
        print("\nNext Step: Run verify_po41_connectivity.py to verify OSPF/BFD/ECMP")
        print("\nNote: OSPF neighbor formation may take 30-60 seconds")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = configure_fs2_l2h1()
    sys.exit(0 if success else 1)
