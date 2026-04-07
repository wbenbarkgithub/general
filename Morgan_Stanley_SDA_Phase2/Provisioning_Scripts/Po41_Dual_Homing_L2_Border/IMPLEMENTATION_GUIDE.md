# FS2_L2H-1 Dual-Homing Implementation Guide

**Comprehensive Step-by-Step Instructions**

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Pre-Implementation Checklist](#pre-implementation-checklist)
4. [Phase 1: Configure FS2_BC2](#phase-1-configure-fs2_bc2)
5. [Phase 2: Configure FS2_L2H-1](#phase-2-configure-fs2_l2h1)
6. [Phase 3: Verification](#phase-3-verification)
7. [Troubleshooting](#troubleshooting)
8. [Post-Implementation Tasks](#post-implementation-tasks)

---

## Overview

This guide provides detailed instructions for implementing dual-homed redundancy for FS2_L2H-1 by adding Port-Channel 41 to FS2_BC2.

**Implementation Time:** 20-30 minutes  
**Risk Level:** Low (no impact to existing Po40)  
**Reversibility:** High (can rollback easily)

---

## Prerequisites

### Software Requirements

1. **Python 3.6 or higher**
   ```bash
   python3 --version
   ```

2. **Netmiko library**
   ```bash
   pip install netmiko
   ```

### Network Requirements

- Network connectivity to:
  - FS2_BC2: 172.31.2.2
  - FS2_L2H-1: 172.31.0.194
- Valid credentials (tested and working)

### Access Requirements

- **FS2_BC2 Credentials:**
  - Primary: `dnac_admin_tacacs` / `CXlabs.123`
  - Fallback: `admin1` / `CXlabs.123`

- **FS2_L2H-1 Credentials:**
  - `admin1` / `CXlabs.123`

### Physical Cabling

Verify physical connections exist between:
- FS2_L2H-1 Te4/0/3 ↔ FS2_BC2 Fif2/0/13
- FS2_L2H-1 Te4/0/4 ↔ FS2_BC2 Fif2/0/14

---

## Pre-Implementation Checklist

**IMPORTANT:** Complete these checks before starting

- [ ] Verify no active test cases or traffic validation in progress
- [ ] Confirm FS2_BC1 Po40 is stable and UP
  ```bash
  ssh admin1@172.31.0.194 "show etherchannel 40 summary"
  ```
- [ ] Take fresh device backups (optional but recommended)
- [ ] Confirm console/OOB access is available if needed
- [ ] Coordinate with other testbed users
- [ ] Review the OSPF MD5 key (used by scripts: `01300F175804485E731F`)

---

## Phase 1: Configure FS2_BC2

**Why First?** FS2_BC2 has no existing connection to FS2_L2H-1, so this is the safer device to configure first.

### Step 1.1: Download Scripts

```bash
cd /tmp
git clone https://github.com/wbenbarkgithub/general.git
cd general/Morgan_Stanley_SDA_Phase2/Provisioning_Scripts/Po41_Dual_Homing_L2_Border/
```

### Step 1.2: Review Configuration Script

```bash
cat configure_fs2_bc2_po41.py
```

Verify the script parameters:
- IP: 172.31.2.2
- Username: dnac_admin_tacacs
- Po41 IP: 192.168.41.1/31

### Step 1.3: Run Configuration Script

```bash
python3 configure_fs2_bc2_po41.py
```

**Expected Output:**
```
======================================================================
  CONFIGURE FS2_BC2 PORT-CHANNEL 41
======================================================================

[1/5] Connecting to FS2_BC2 (172.31.2.2)...
     Connected: FS2_C9600X_BC2#

[2/5] Checking current interface status...
Fif2/0/13    "connecting to Te4 notconnect   routed       full    10G
Fif2/0/14                       connected    1            full    10G

[3/5] Configuring physical interfaces Fif2/0/13 and Fif2/0/14...
[Configuration output...]

[4/5] Configuring Port-channel 41...
[Configuration output...]

[5/5] Configuring OSPF area authentication...
[Configuration output...]

======================================================================
  VERIFICATION - FS2_BC2
======================================================================

[CHECK 1] Interface status:
Po41         connectivity to FS notconnect   routed       auto   auto

[CHECK 2] Port-channel summary:
41     Po41(RD)        LACP        Fif2/0/13(D)    Fif2/0/14(w)

[CHECK 3] Port-channel 41 config:
interface Port-channel41
 description connectivity to FS2_L2H-1
 ip address 192.168.41.1 255.255.255.254
 [... full config ...]

[SAVE] Saving configuration...
[OK]

======================================================================
  ✅ FS2_BC2 CONFIGURATION COMPLETE
======================================================================
```

### Step 1.4: Verify FS2_BC2 Status

At this point, Po41 will show:
- Status: **DOWN** (expected - waiting for FS2_L2H-1)
- Members: Fif2/0/13(D), Fif2/0/14(w) - waiting for LACP neighbor

This is **normal and expected**.

---

## Phase 2: Configure FS2_L2H-1

### Step 2.1: Review Configuration Script

```bash
cat configure_fs2_l2h1_po41.py
```

Verify the script parameters:
- IP: 172.31.0.194
- Username: admin1
- Po41 IP: 192.168.41.0/31

### Step 2.2: Run Configuration Script

```bash
python3 configure_fs2_l2h1_po41.py
```

**Expected Output:**
```
======================================================================
  CONFIGURE FS2_L2H-1 PORT-CHANNEL 41
======================================================================

[1/6] Connecting to FS2_L2H-1 (172.31.0.194)...
     Connected: FS2_L2H_1#

[2/6] Checking current interface status...
Te4/0/3      "connecting to Fif disabled     routed       full    10G
Te4/0/4                         connected    1            full    10G

[3/6] Configuring physical interfaces Te4/0/3 and Te4/0/4...
[Configuration output...]

[4/6] Configuring Port-channel 41...
[Configuration output...]

[5/6] Removing OSPF passive-interface for Po41...
[Configuration output...]

======================================================================
  VERIFICATION - FS2_L2H-1
======================================================================

[CHECK 1] Interface status:
Te4/0/3      to FS2_BC2 Fif2/0/ connected    routed       full    10G
Te4/0/4      to FS2_BC2 Fif2/0/ connected    routed       full    10G
Po41         connectivity to FS connected    routed     a-full  a-10G

[CHECK 2] Port-channel summary (both Po40 and Po41):
40     Po40(RU)        LACP        Te4/0/1(P)      Te4/0/2(P)
41     Po41(RU)        LACP        Te4/0/3(P)      Te4/0/4(P)

[CHECK 3] LACP neighbor:
Channel group 41 neighbors
Port          Flags  Priority  Dev ID          Age  key    Key    Number  State
Te4/0/3       FA     32768     3c57.3104.14c0   0s  0x0    0x29   0x20E   0x3F
Te4/0/4       FA     32768     3c57.3104.14c0   0s  0x0    0x29   0x20F   0x3F

[CHECK 4] Port-channel 41 config:
[... full config ...]

[6/6] Saving configuration...
[OK]

======================================================================
  ✅ FS2_L2H-1 CONFIGURATION COMPLETE
======================================================================
```

### Step 2.3: Key Indicators

✅ **Po41(RU)** - Port-channel is UP!  
✅ **(P)** flags - Both members bundled  
✅ **LACP neighbor** - FS2_BC2 visible (MAC: 3c57.3104.14c0)  
✅ **Both Po40 and Po41** - Operating simultaneously

---

## Phase 3: Verification

### Step 3.1: Wait for OSPF Convergence

**IMPORTANT:** Allow 30-60 seconds for OSPF neighbor to form before verification.

```bash
# Wait 60 seconds
sleep 60
```

### Step 3.2: Run Verification Script

```bash
python3 verify_po41_connectivity.py
```

**Expected Output (Success):**
```
======================================================================
  VERIFY PO41 CONNECTIVITY AND ECMP
======================================================================

[TEST 1] Ping Test - FS2_L2H-1 to FS2_BC2
----------------------------------------------------------------------
Connected to: FS2_L2H_1#
Success rate is 100 percent (5/5), round-trip min/avg/max = 1/1/1 ms

✅ Ping Test: PASS

[TEST 2] OSPF Neighbor Verification
----------------------------------------------------------------------
Neighbor ID     Pri   State           Dead Time   Address         Interface
192.168.100.2     0   FULL/  -        00:00:33    192.168.41.1    Port-channel41
192.168.100.1     0   FULL/  -        00:00:30    192.168.40.1    Port-channel40

✅ OSPF Neighbor on Po41: PASS (FULL state)

[TEST 3] BFD Session Verification
----------------------------------------------------------------------
IPv4 Sessions
NeighAddr                              LD/RD         RH/RS     State     Int
192.168.40.1                            1/44         Up        Up        Po40
192.168.41.1                            2/12         Up        Up        Po41

✅ BFD Session on Po41: PASS

[TEST 4] ECMP Load-Balancing Verification
----------------------------------------------------------------------
Routing entry for 192.168.20.0/31
  Routing Descriptor Blocks:
  * 192.168.41.1, via Port-channel41
      Route metric is 105, traffic share count is 1
    192.168.40.1, via Port-channel40
      Route metric is 105, traffic share count is 1

✅ ECMP Load-Balancing: ACTIVE

[TEST 5] LACP Bundle Status - FS2_L2H-1
----------------------------------------------------------------------
41     Po41(RU)        LACP        Te4/0/3(P)      Te4/0/4(P)

✅ LACP Bundle on FS2_L2H-1: PASS

[TEST 6] FS2_BC2 Side Verification
----------------------------------------------------------------------
[... similar output ...]

✅ LACP Bundle on FS2_BC2: PASS

======================================================================
  VERIFICATION SUMMARY
======================================================================

Tests Passed: 6/6

Detailed Results:
  ✅ Ping Test
  ✅ OSPF Neighbor (FULL)
  ✅ BFD Session (UP)
  ✅ ECMP Load-Balancing
  ✅ LACP Bundle (FS2_L2H-1)
  ✅ LACP Bundle (FS2_BC2)

======================================================================
  ✅ ALL TESTS PASSED - DUAL-HOMING OPERATIONAL
======================================================================
```

### Step 3.3: Manual Verification (Optional)

If you want to verify manually:

**On FS2_L2H-1:**
```bash
ssh admin1@172.31.0.194

show etherchannel summary | include Po4
show ip ospf neighbor
show bfd neighbors
show ip route 192.168.20.0 255.255.255.254
```

**On FS2_BC2:**
```bash
ssh dnac_admin_tacacs@172.31.2.2

show etherchannel 41 summary
show ip ospf neighbor | include 192.168.41
show bfd neighbors | include 192.168.41
```

---

## Troubleshooting

### Issue 1: OSPF Neighbor Not Forming

**Symptoms:**
- `show ip ospf neighbor` doesn't show 192.168.41.1 or 192.168.41.0
- OSPF stuck in INIT state

**Diagnosis:**
```bash
# On FS2_L2H-1
show ip ospf interface Port-channel41 | include Passive

# Check for "No Hellos (Passive interface)"
```

**Resolution:**
```bash
# Already fixed by script, but manual fix:
configure terminal
router ospf 1
 no passive-interface Port-channel41
exit
write memory
```

Wait 30 seconds and check again.

---

### Issue 2: Authentication Mismatch

**Symptoms:**
- OSPF neighbor appears but doesn't reach FULL state
- Syslog shows authentication errors

**Diagnosis:**
```bash
# On FS2_BC2
show run | section router ospf
# Look for "area 0 authentication message-digest"
```

**Resolution:**
```bash
# Already fixed by script, but manual fix:
configure terminal
router ospf 1
 area 0 authentication message-digest
exit
write memory
```

---

### Issue 3: LACP Not Bundling

**Symptoms:**
- Interfaces show (D) down or (w) waiting
- Po41 shows down

**Diagnosis:**
```bash
show etherchannel 41 detail
show lacp 41 neighbor
```

**Common Causes:**
1. **Physical cable not connected:** Check both ends
2. **Speed mismatch:** Should auto-negotiate to 10G
3. **Service policy missing:** Already applied by script

**Resolution:**
- Verify physical connections
- Check `show interfaces Fif2/0/13 status` and `Te4/0/3 status`
- If needed: `default interface` and re-run script

---

### Issue 4: BFD Session Not Establishing

**Symptoms:**
- `show bfd neighbors` doesn't show 192.168.41.1

**Common Cause:**
- OSPF must be FULL before BFD establishes

**Resolution:**
1. Fix OSPF first (see Issue 1)
2. Verify `bfd all-interfaces` in OSPF process:
   ```bash
   show run | section router ospf
   ```
3. Wait for OSPF to reach FULL, then BFD will come up automatically

---

## Post-Implementation Tasks

### Task 1: Verify No Impact to Existing Traffic

Check that Po40 is still operational:

```bash
ssh admin1@172.31.0.194 "show interfaces Port-channel40 | include packets"
```

Should show continuous packet counters (no drops).

### Task 2: Test Failover (Optional)

Simulate Po40 failure to verify Po41 takes over:

```bash
# On FS2_L2H-1
configure terminal
interface Port-channel40
 shutdown
exit

# Wait 10 seconds, then verify traffic via Po41
show ip route ospf | include 192.168.20.0

# Restore Po40
configure terminal
interface Port-channel40
 no shutdown
exit
write memory
```

### Task 3: Update Documentation

- [ ] Update topology diagrams with Po41
- [ ] Add Po41 to IP address inventory (192.168.41.0/31)
- [ ] Update test case documentation (TC 07-02, TC 09-01, TC 01-11)
- [ ] Update memory entry #48 from PLANNED → COMPLETED

### Task 4: Capture Fresh Backups

```bash
# Backups already saved by scripts, but to capture again:
ssh admin1@172.31.0.194 "show run" > FS2_L2H-1_$(date +%Y%m%d).txt
ssh dnac_admin_tacacs@172.31.2.2 "show run" > FS2_BC2_$(date +%Y%m%d).txt
```

---

## Success Criteria - Final Checklist

Implementation is successful when ALL of these are true:

- [ ] Port-channel 41 shows UP/UP on both devices
- [ ] Both LACP members show (P) bundled status
- [ ] OSPF neighbors show FULL state on Po41
- [ ] BFD sessions show UP on Po41
- [ ] Ping test 192.168.41.0 ↔ 192.168.41.1 succeeds
- [ ] Routes show ECMP (both Po40 and Po41 as next-hops)
- [ ] Po40 still operational (no impact)
- [ ] Configurations saved with `write memory`
- [ ] Verification script shows 6/6 tests passed

---

## Rollback Procedure

If you need to remove Po41 configuration completely:

### Rollback Step 1: FS2_L2H-1

```bash
ssh admin1@172.31.0.194

configure terminal
no interface Port-channel41
default interface TenGigabitEthernet4/0/3
default interface TenGigabitEthernet4/0/4
router ospf 1
 passive-interface Port-channel41
exit
write memory
```

### Rollback Step 2: FS2_BC2

```bash
ssh dnac_admin_tacacs@172.31.2.2

configure terminal
no interface Port-channel41
default interface FiftyGigE2/0/13
default interface FiftyGigE2/0/14
write memory
```

### Rollback Verification

```bash
# On both devices
show etherchannel summary | include Po41
# Should return no results

show ip ospf neighbor
# Should only show Po40 neighbor
```

---

## Appendix: Manual Configuration (Without Scripts)

If you prefer to configure manually instead of using Python scripts, see the full CLI commands in the `configure_fs2_bc2_po41.py` and `configure_fs2_l2h1_po41.py` scripts. The scripts essentially automate the exact CLI commands you would type.

---

**Document Version:** 1.0  
**Last Updated:** April 7, 2026  
**Author:** Morgan Stanley SDA Phase 2 Team
