# FS2_L2H-1 Dual-Homing Implementation - Port-Channel 41

**Date:** April 7, 2026  
**Status:** ✅ Tested and Validated  
**Implementation Time:** ~30 minutes  

## Overview

This folder contains automated Python scripts to implement **dual-homed redundancy** for FS2_L2H-1 (Layer 2 Border) by adding a second port-channel (Po41) to FS2_BC2. This eliminates the single point of failure that existed with only Po40 to FS2_BC1.

### Topology - Before and After

**Before (Single-Homed):**
```
FS2_L2H-1 ----Po40 (Te4/0/1-2)----> FS2_BC1
                                      |
                                      | (Fabric connectivity)
                                      |
                  FS2_BC2 <-----------+
```

**After (Dual-Homed with ECMP):**
```
              ┌─ Po40 (Te4/0/1-2) ──> FS2_BC1 (192.168.40.1)
              |                           |
FS2_L2H-1 ────┤                           | (Fabric connectivity)
              |                           |
              └─ Po41 (Te4/0/3-4) ──> FS2_BC2 (192.168.41.1)
```

## Benefits

- **Redundancy:** No single point of failure
- **ECMP Load-Balancing:** Traffic distributed across both Border Controllers
- **Fast Failover:** BFD detects failures in 2.25 seconds
- **Zero Downtime:** Automatic failover via alternate path
- **Increased Capacity:** 20 Gbps aggregate bandwidth (2x 10G port-channels)

## Files in This Directory

| File | Description |
|------|-------------|
| `configure_fs2_bc2_po41.py` | Configure FS2_BC2 side (run first) |
| `configure_fs2_l2h1_po41.py` | Configure FS2_L2H-1 side (run second) |
| `verify_po41_connectivity.py` | Verify OSPF, BFD, ECMP, and connectivity |
| `README.md` | This file |
| `IMPLEMENTATION_GUIDE.md` | Detailed step-by-step implementation guide |

## Quick Start

### Prerequisites

1. **Python 3.6+** installed
2. **Netmiko library**: `pip install netmiko`
3. **Network connectivity** to both devices
4. **Valid credentials**:
   - FS2_BC2: `dnac_admin_tacacs` / `CXlabs.123`
   - FS2_L2H-1: `admin1` / `CXlabs.123`

### Implementation Steps

**Step 1: Configure FS2_BC2 (safer first - no existing connection)**
```bash
python3 configure_fs2_bc2_po41.py
```

**Step 2: Configure FS2_L2H-1**
```bash
python3 configure_fs2_l2h1_po41.py
```

**Step 3: Verify Connectivity**
```bash
# Wait 30-60 seconds for OSPF convergence, then:
python3 verify_po41_connectivity.py
```

### Expected Output

If successful, verification will show:
- ✅ Ping Test: PASS
- ✅ OSPF Neighbor (FULL)
- ✅ BFD Session (UP)
- ✅ ECMP Load-Balancing (both paths active)
- ✅ LACP Bundle (both sides)

## Technical Details

### Configuration Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Port-Channel Number** | 41 | Sequential after Po40 |
| **IP Addressing** | 192.168.41.0/31 | L2H-1: .0, BC2: .1 |
| **LACP Mode** | Active | Both sides initiate |
| **LACP Rate** | Fast (1 second) | Quick failure detection |
| **MTU** | 9100 | Jumbo frames |
| **OSPF Area** | 0.0.0.0 | Backbone area |
| **OSPF Cost** | 100 | Equal to Po40 for ECMP |
| **OSPF Auth** | MD5 (area-level) | Shared with Po40 |
| **BFD Interval** | 750ms | Tx/Rx interval |
| **BFD Multiplier** | 3 | 2.25s detection time |
| **Multicast** | PIM sparse-mode | Match Po40 |

### Interface Mapping

| Device | Interfaces | Description |
|--------|------------|-------------|
| **FS2_L2H-1** | Te4/0/3 | Member of Po41 to BC2 |
| **FS2_L2H-1** | Te4/0/4 | Member of Po41 to BC2 |
| **FS2_BC2** | Fif2/0/13 | Member of Po41 to L2H-1 |
| **FS2_BC2** | Fif2/0/14 | Member of Po41 to L2H-1 |

**Note:** These interfaces were pre-configured with descriptions indicating this connectivity was previously planned.

## Troubleshooting

### OSPF Neighbor Not Forming

**Symptom:** OSPF neighbor stuck in INIT or not appearing

**Common Causes:**
1. **Passive Interface:** Po41 may be passive by default
   - **Fix:** Included in `configure_fs2_l2h1_po41.py` script
   - Manual: `router ospf 1` → `no passive-interface Port-channel41`

2. **Authentication Mismatch:** FS2_BC2 missing area-level MD5
   - **Fix:** Included in `configure_fs2_bc2_po41.py` script
   - Manual: `router ospf 1` → `area 0 authentication message-digest`

3. **Timing:** OSPF needs 30-60 seconds to converge
   - **Fix:** Wait and re-run verification script

### LACP Bundle Not Forming

**Symptom:** Interfaces show (D) down or (w) waiting

**Check:**
```bash
show etherchannel 41 summary
show lacp 41 neighbor
```

**Common Causes:**
- Speed mismatch (should auto-negotiate to 10G)
- Missing service-policy on one side
- Physical cable not connected

### BFD Session Not Establishing

**Symptom:** BFD shows Down or not appearing

**Common Causes:**
- OSPF neighbor not FULL (BFD requires OSPF first)
- BFD not enabled globally: `router ospf 1` → `bfd all-interfaces`

## Rollback Procedure

If you need to remove Po41 configuration:

**On FS2_L2H-1:**
```
configure terminal
no interface Port-channel41
default interface TenGigabitEthernet4/0/3
default interface TenGigabitEthernet4/0/4
router ospf 1
  passive-interface Port-channel41
exit
write memory
```

**On FS2_BC2:**
```
configure terminal
no interface Port-channel41
default interface FiftyGigE2/0/13
default interface FiftyGigE2/0/14
write memory
```

## Validation Checklist

After implementation, verify:

- [ ] Port-channel 41 UP/UP on both devices
- [ ] Both LACP members active (P flag)
- [ ] OSPF neighbor FULL state
- [ ] BFD session UP
- [ ] Ping 192.168.41.0 ↔ 192.168.41.1 successful
- [ ] Routes showing ECMP (both Po40 and Po41)
- [ ] No impact to existing Po40 traffic
- [ ] Configurations saved (`write memory`)

## Related Test Cases

- **TC 07-01:** Link Failure L2 Border Po Member (single member failure)
- **TC 07-02:** Link Failure L2 Border Complete Po (complete Po40 failure)
- **TC 09-01:** L2 Border Catalyst Center Configuration + Traffic Validation
- **TC 01-11:** L2 Border Handoff Verification

## References

- Implementation Plan: `/Users/wbenbark/.claude/plans/glimmering-gliding-kurzweil.md`
- Implementation Summary: `Test Case Logs/07-02_Link_Failure_From_L2_Border_PortChannel_to_Fabric_BC_Node/Po41_Implementation_20260407_115546/IMPLEMENTATION_SUMMARY.md`
- Device Backups: `Device_Backup/2026-04-07/`
- Memory Entry: Project #48 - FS2_L2H-1 Dual-Homing

## Support

For questions or issues:
- Review the detailed `IMPLEMENTATION_GUIDE.md`
- Check the verification output for specific failures
- Consult the implementation logs in TC 07-02 directory

---

**Last Updated:** April 7, 2026  
**Author:** Morgan Stanley SDA Phase 2 Team  
**Status:** Production Ready ✅
