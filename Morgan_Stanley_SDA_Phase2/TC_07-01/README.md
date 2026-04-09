# TC 07-01: Link Failure from L2 Border PortChannel Member to Fabric BC Node

**Project:** Morgan Stanley SDA Phase 2  
**Phase:** 07 - Negative Testing - Layer 2 Border  
**CXTM ID:** 1872836  
**Author:** wbenbark  
**Date:** April 2026  
**Status:** PASS (3 iterations completed April 9, 2026)  
**Version:** 2.1 (Updated April 9, 2026)

## Overview

This test case validates that shutting down a single LACP Port-Channel member link between the L2 Border node (FS2_L2H-1) and the Fabric Border Controller (FS2_BC1) does NOT bring down the Port-Channel bundle, and that L2 handoff traffic experiences zero or near-zero packet loss.

## Test Topology

```
FS2_L2H-1 (L2 Border)                FS2_BC1 (Border Controller)
C9404R / 172.31.0.194                 C9606R / 172.31.2.0

Te4/0/1  ─────────────────────── Fif1/0/13
    \                                /
Po40 (LACP, L3)                   Po40 (LACP, L3)
192.168.40.0/31                   192.168.40.1/31
    /                                \
Te4/0/2  ─────────────────────── Fif1/0/14
```

## Files in this Directory

### 1. `run_tc_07-01.py` (Automated Execution Script)

Interactive Python script that automates TC 07-01 test execution with built-in pauses for GUI screenshot capture.

**Features:**
- 3-phase workflow (Baseline → Failure → Recovery)
- Automated CLI collection from L2H-1, BC1, and both L2 9300 switches
- Multicast validation (PIM, mroute, MFIB, IGMP snooping) across all phases
- Alternate credential fallback (dnac_admin_tacacs) for BC1
- Interactive prompts for Spirent and Catalyst Center screenshots
- Iteration support (run 3 times for consistency validation)
- Real-time LACP rebundle monitoring
- Robust error handling with safe disconnect and read timeouts
- Automatic file organization per iteration

**Requirements:**
```bash
pip install netmiko
```

**Usage:**
```bash
# Iteration 1
python3 run_tc_07-01.py --iter 1

# Iteration 2
python3 run_tc_07-01.py --iter 2

# Iteration 3
python3 run_tc_07-01.py --iter 3
```

**Device Access:**
- FS2_L2H-1: 172.31.0.194 (admin1/CXlabs.123)
- FS2_BC1: 172.31.2.0 (admin1/CXlabs.123, fallback: dnac_admin_tacacs)
- FS2_L2_9300-1: 172.31.0.179 (admin/CXlabs.123)
- FS2_L2_9300-2: 172.31.0.178 (admin/CXlabs.123)

**Output Files (per iteration):**
- `Iter{n}_Pre_L2H1_Baseline.txt` - Phase 1 L2H-1 CLI baseline (incl. multicast)
- `Iter{n}_Pre_BC1_Baseline.txt` - Phase 1 BC1 CLI baseline (incl. multicast)
- `Iter{n}_Pre_L2_9300-1_Baseline.txt` - Phase 1 L2 9300-1 baseline (STP, IGMP, trunks)
- `Iter{n}_Pre_L2_9300-2_Baseline.txt` - Phase 1 L2 9300-2 baseline (STP, IGMP, trunks)
- `Iter{n}_During_L2H1_Failure.txt` - Phase 2 L2H-1 during failure (incl. multicast)
- `Iter{n}_During_BC1_Status.txt` - Phase 2 BC1 during failure (incl. multicast)
- `Iter{n}_During_L2_9300-1_Status.txt` - Phase 2 L2 9300-1 during failure (STP, syslog)
- `Iter{n}_During_L2_9300-2_Status.txt` - Phase 2 L2 9300-2 during failure (STP, syslog)
- `Iter{n}_Post_L2H1_Validation.txt` - Phase 3 L2H-1 post-recovery (incl. multicast)
- `Iter{n}_Post_BC1_Validation.txt` - Phase 3 BC1 post-recovery (incl. multicast)
- `Iter{n}_Post_L2_9300-1_Validation.txt` - Phase 3 L2 9300-1 post-recovery
- `Iter{n}_Post_L2_9300-2_Validation.txt` - Phase 3 L2 9300-2 post-recovery

### 2. `TC-07-01_Execution_Plan.txt` (Manual Execution Guide)

Copy/paste-ready execution plan for manual testing. Use this if you prefer manual CLI execution or if the Python script is unavailable.

**Includes:**
- Device access quick reference
- Prerequisites checklist
- Complete Phase 1/2/3 CLI commands (ready to copy/paste)
- Results recording tables
- 3-iteration comparison matrix
- Rollback procedures

### 3. `TC-07-01_CXTM.txt` (Test Case Specification)

Comprehensive test case documentation including:
- Test description and objectives
- Detailed topology diagram
- Pass/fail criteria
- Technical notes (LACP behavior, hash redistribution, LISP/OSPF impact)
- Deliverables checklist

### 4. `TC-07-01_CXTM_Results.txt` (Execution Results — PASS)

Unified-format execution results from April 9, 2026 run:
- Executive summary with pass/fail determination
- 3-iteration convergence data
- Multicast verification results (225.1.1.1 VRF BMS1)
- L2_9300 STP/IGMP snooping observations

## Test Phases

### Phase 1: Steady State Baseline
1. Verify Spirent 0.000% packet loss (GATE - must pass)
2. Verify Catalyst Center L2H-1 health ≥ 80%
3. Collect CLI baseline from L2H-1 and BC1 (including multicast: PIM, mroute, MFIB, IGMP)
4. Collect CLI baseline from FS2_L2_9300-1 and FS2_L2_9300-2 (STP, trunks, MAC, IGMP snooping)
5. Validate Po40 UP with both members bundled

### Phase 2: Failure Event
1. Shutdown `TenGigabitEthernet4/0/1` on FS2_L2H-1
2. Verify Po40 stays UP with single member (Te4/0/2)
3. Monitor Spirent for 3 minutes (expect 0.000% loss)
4. Collect during-failure CLI from L2H-1 and BC1 (including multicast state)
5. Collect during-failure CLI from L2 9300 switches (STP topology changes, syslog)
6. Verify LISP sessions, OSPF adjacency, and multicast forwarding remain stable

### Phase 3: Recovery
1. Restore `TenGigabitEthernet4/0/1` (no shutdown)
2. Verify LACP rebundle (expect < 30 seconds)
3. Validate Spirent 0.000% loss
4. Collect post-recovery CLI from all 4 devices (including multicast restoration)
5. Compare all metrics to Phase 1 baseline

## Expected Results

**PASS Criteria:**
- ✅ Po40 remains UP during member shutdown (bandwidth reduces 20G → 10G)
- ✅ Spirent 0.000% packet loss (or ≤ 0.001% transient micro-loss) — unicast + multicast
- ✅ Zero dead flows
- ✅ LISP sessions remain established
- ✅ OSPF adjacency stable (no flap)
- ✅ Multicast: mroute 225.1.1.1 present in VRF BMS1 during failure
- ✅ Multicast: MFIB HW counters incrementing (forwarding active)
- ✅ Multicast: PIM neighbors UP during failure
- ✅ Multicast: IGMP snooping group 225.1.1.1 on VLAN 101
- ✅ L2 switches: STP/IGMP snooping state captured across all phases
- ✅ LACP rebundle < 30 seconds after restoration
- ✅ All metrics (including multicast) restored to baseline
- ✅ Results consistent across 3 iterations (±20%)

## Quick Start

### Option 1: Automated (Recommended)
```bash
# Clone repo
git clone https://github.com/wbenbarkgithub/general.git
cd general/Morgan_Stanley_SDA_Phase2/TC_07-01

# Install dependencies
pip install netmiko

# Run iteration 1
python3 run_tc_07-01.py --iter 1

# Follow on-screen prompts for:
#   - Spirent screenshots (3 per iteration)
#   - Catalyst Center screenshots (5 per iteration)

# Run iterations 2 and 3
python3 run_tc_07-01.py --iter 2
python3 run_tc_07-01.py --iter 3
```

### Option 2: Manual
```bash
# Open execution plan
cat TC-07-01_Execution_Plan.txt

# SSH to devices manually
ssh admin1@172.31.0.194  # FS2_L2H-1
ssh admin1@172.31.2.0    # FS2_BC1

# Copy/paste commands from execution plan
# Save outputs manually
```

## Prerequisites

- ✅ VPN connected to lab (172.31.x.x reachable)
- ✅ SSH access to FS2_L2H-1, FS2_BC1, FS2_L2_9300-1, and FS2_L2_9300-2
- ✅ Spirent GUI open (172.31.0.101)
- ✅ Catalyst Center GUI open (https://172.31.229.151)
- ✅ Spirent baseline: 0.000% loss (MANDATORY GATE)
- ✅ Python 3.x with netmiko (for automated script)

## Technical Details

**Port-Channel Configuration:**
- Channel Group: 40
- Protocol: LACP
- Layer: 3 (Routed)
- IP: 192.168.40.0/31 (L2H-1) / 192.168.40.1/31 (BC1)
- Bandwidth: 20 Gbps aggregate (2x 10G)

**Current Traffic Load:**
- ~360 Mbps inbound on Po40
- 172 L2 handoff streams (BMS VLAN 101, EUT VLAN 1301)
- Well within single-member capacity (10 Gbps)

**LACP Behavior:**
- Graceful member removal (final LACPDU sent before shutdown)
- Hash redistribution to surviving member (near-instantaneous)
- No OSPF flap (Po40 stays UP)
- No LISP session impact (TCP sessions remain established)

**Multicast Validation (v2.0):**
- PIM neighbors in VRF BMS1 validated across all phases
- mroute 225.1.1.1 presence confirmed during failure
- MFIB hardware counters checked for active forwarding
- IGMP snooping groups on VLAN 101 (BMS1) and VLAN 1301 (EUT)

**L2 Switch Validation (v2.0):**
- FS2_L2_9300-1 and FS2_L2_9300-2 STP topology change detection
- MAC address table monitoring across failure/recovery
- Syslog capture (LINK/UPDOWN/LINEPROTO/STP/TCN events)

## Related Test Cases

- **TC 07-02:** Link failure from both PortChannel members (dual failure)
- **TC 07-03:** PortChannel complete shutdown
- **TC 09-01:** L2 Border Catalyst Center configuration validation

## Support

For questions or issues:
- GitHub: https://github.com/wbenbarkgithub/general/issues
- Test Case Owner: wbenbark
- Lab Location: RTP S10-360, Row P, Racks 18-25

## References

- Cisco SDA Design Guide
- LACP (IEEE 802.3ad)
- Catalyst Center 2.3.7.9 Documentation
- Morgan Stanley SDA Phase 2 Project Documentation

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | April 6, 2026 | Initial release: 3-device collection (L2H-1, BC1, BC2), LACP member shutdown |
| 2.0 | April 8, 2026 | Added L2_9300-1/2 collection (STP, IGMP snooping, MAC tables). Added multicast verification (PIM, mroute 225.1.1.1, MFIB HW counters). 5-device, 12 CLI files/iteration. |
| 2.1 | April 9, 2026 | Clean script (removed embedded changelog header). Added unified CXTM_Results.txt (PASS). Status updated to PASS after 3 successful iterations. |
