#!/usr/bin/env python3
"""
Configure Port-Channel 41 on FS2_BC2 for Dual-Homing to FS2_L2H-1

This script configures:
- Physical interfaces Fif2/0/13-14
- Port-channel 41 with LACP
- IP addressing (192.168.41.1/31)
- OSPF Area 0 with MD5 authentication
- BFD for fast failure detection

Prerequisites:
- netmiko: pip install netmiko
- Network connectivity to FS2_BC2 (172.31.2.2)
- Valid credentials (admin1 or dnac_admin_tacacs)

Author: Morgan Stanley SDA Phase 2 Team
Date: April 7, 2026
"""

from netmiko import ConnectHandler
import time
import sys

# Device connection parameters
FS2_BC2 = {
    'device_type': 'cisco_ios',
    'host': '172.31.2.2',
    'username': 'dnac_admin_tacacs',  # Use 'admin1' if this fails
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


def configure_fs2_bc2():
    """Configure FS2_BC2 with Po41 to FS2_L2H-1."""

    banner("CONFIGURE FS2_BC2 PORT-CHANNEL 41")

    try:
        print("[1/5] Connecting to FS2_BC2 (172.31.2.2)...")
        conn = ConnectHandler(**FS2_BC2)
        print(f"     Connected: {conn.find_prompt()}")

        # Check current interface status
        print("\n[2/5] Checking current interface status...")
        output = conn.send_command("show interfaces status | include Fif2/0/1[34]")
        print(output)

        # Configure physical interfaces
        print("\n[3/5] Configuring physical interfaces Fif2/0/13 and Fif2/0/14...")
        physical_config = [
            "default interface FiftyGigE2/0/13",
            "default interface FiftyGigE2/0/14",
            "interface FiftyGigE2/0/13",
            "description to FS2_L2H-1 Te4/0/3",
            "no switchport",
            "mtu 9100",
            "no ip address",
            "channel-group 41 mode active",
            "lacp rate fast",
            "service-policy output DNA-dscp#APIC_QOS_Q_OUT",
            "no shutdown",
            "exit",
            "interface FiftyGigE2/0/14",
            "description to FS2_L2H-1 Te4/0/4",
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
        print("\n[4/5] Configuring Port-channel 41...")
        po_config = [
            "interface Port-channel41",
            "description connectivity to FS2_L2H-1",
            "no switchport",
            "mtu 9100",
            "ip address 192.168.41.1 255.255.255.254",
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

        # Add OSPF area authentication
        print("\n[5/5] Configuring OSPF area authentication...")
        ospf_config = [
            "router ospf 1",
            "area 0 authentication message-digest",
            "exit",
        ]

        output = conn.send_config_set(ospf_config)
        print(output)

        # Verification
        banner("VERIFICATION - FS2_BC2", '-')

        time.sleep(3)

        print("\n[CHECK 1] Interface status:")
        output = conn.send_command("show interfaces status | include Fif2/0/1[34]|Po41")
        print(output)

        print("\n[CHECK 2] Port-channel summary:")
        output = conn.send_command("show etherchannel summary | include Po41")
        print(output)

        print("\n[CHECK 3] Port-channel 41 config:")
        output = conn.send_command("show run interface Port-channel41")
        print(output)

        # Save configuration
        print("\n[SAVE] Saving configuration...")
        output = conn.send_command("write memory", read_timeout=30)
        print(output)

        conn.disconnect()

        banner("✅ FS2_BC2 CONFIGURATION COMPLETE")
        print("\nNext Step: Run configure_fs2_l2h1_po41.py to complete dual-homing setup")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = configure_fs2_bc2()
    sys.exit(0 if success else 1)
