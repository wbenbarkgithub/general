# TC 07-04: Link Failure from L2 Border to Distribution Switch

**Test Type:** Negative Test Case - Phase 07 L2 Border Validation  
**Topology:** L2 Border with Dual L2 Trunks to Legacy Distribution Switches  
**Failure Target:** Te4/0/20 trunk to L2-DIST-1 (STP failover to L2-DIST-2)  
**Expected Behavior:** STP convergence with minimal packet loss, fabric side unaffected  
**Scripts:** Two variants — L2 Border side (`run_tc_07-04.py`) and Distribution side (`run_tc_07-04_dist_side.py`)  

---

## Overview

TC 07-04 completes the Phase 07 L2 Border negative test suite by validating **legacy Layer 2 distribution switch failover** using **Spanning Tree Protocol (STP)**. This test is fundamentally different from TC 07-02 and TC 07-03:

| Test Case | Failure Type | Failover Mechanism | Protocol |
|-----------|--------------|-------------------|----------|
| **TC 07-02** | Po40 to BC1 | OSPF/ECMP to BC2 | Layer 3 (OSPF/LISP) |
| **TC 07-03** | Po41 to BC2 | OSPF/ECMP to BC1 | Layer 3 (OSPF/LISP) |
| **TC 07-04** | Te4/0/20 to DIST-1 | STP to DIST-2 | Layer 2 (STP) |
| **TC 07-04 (Dist Side)** | Te4/0/20 shut from DIST-1 | STP to DIST-2 | Layer 2 (STP) |

**Key Difference:** TC 07-04 tests **Layer 2 trunk redundancy** to legacy non-SDA distribution switches, while TC 07-02/07-03 test **Layer 3 ECMP redundancy** to SDA Border Controllers.

### Two Script Variants

TC 07-04 includes **two complementary scripts** that shut the same trunk from opposite ends:

| Script | Shutdown Device | L2H-1 Sees | CC Behavior |
|--------|----------------|------------|-------------|
| `run_tc_07-04.py` | FS2_L2H-1 (L2 Border side) | Admin-down (local) | 0 issues (intentional) |
| `run_tc_07-04_dist_side.py` | L2-DIST-1 (Distribution side) | Link-down (remote) | May raise issue (fault) |

**Why both?** Shutting from the L2 Border side produces an admin-down event (CC treats as intentional). Shutting from the Distribution side produces a link-down event (CC may treat as a fault). Both must converge via STP to Te4/0/21, but CC issue behavior differs — documenting this difference validates CC's fault detection accuracy.

The dist_side variant also collects from **7 devices** (L2H-1, L2-DIST-1, L2-DIST-2, FS2_BC1, FS2_L2_9300-1, FS2_L2_9300-2) including the two legacy access switches behind the distribution tier, and adds **multicast verification** (PIM, MFIB, IGMP snooping) at each phase.

---

## Topology

```
                    ┌─────────────────────┐
                    │   Catalyst Center   │
                    │    172.31.0.197     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
    ┌─────────▼────────┐           ┌──────────▼────────┐
    │   FS2_BC1        │           │   FS2_BC2         │
    │   C9606R         │           │   C9606R          │
    │   172.31.2.0     │           │   172.31.2.2      │
    └────────┬─────────┘           └─────────┬─────────┘
             │ Po40                          │ Po41
             │ [FABRIC SIDE]                 │ [FABRIC SIDE]
             │                               │
             └───────────────┬───────────────┘
                             │
                   ┌─────────▼─────────┐
                   │   FS2_L2H-1       │
                   │   C9404R          │
                   │   172.31.0.194    │
                   │   L2 Border       │
                   └─────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │ [LEGACY L2 SIDE]            │
              │ Te4/0/20            Te4/0/21│
              │ [WILL SHUT]         [STAYS UP]
              │                              │
    ┌─────────▼────────┐          ┌─────────▼────────┐
    │  L2-DIST-1       │          │  L2-DIST-2       │
    │  C9404R          │          │  C9404R          │
    │  172.31.0.193    │          │  172.31.0.180    │
    │  Legacy Site     │          │  Legacy Site     │
    └────────┬─────────┘          └────────┬─────────┘
             │                              │
    ┌────────▼─────────┐          ┌────────▼─────────┐
    │ FS2_L2_9300-1    │          │ FS2_L2_9300-2    │
    │ C9300-48S        │          │ C9300-48U        │
    │ 172.31.0.179     │          │ 172.31.0.178     │
    │ Legacy Access    │          │ Legacy Access    │
    └──────────────────┘          └──────────────────┘
```

> **Dist Side variant** (`run_tc_07-04_dist_side.py`): Shuts Te4/0/20 on **L2-DIST-1** instead of FS2_L2H-1. L2H-1 sees link-down (not admin-down). Also collects from FS2_L2_9300-1 and FS2_L2_9300-2.

### Interface Configuration

| Device | Interface | Connected To | Type | VLANs | Auth |
|--------|-----------|--------------|------|-------|------|
| FS2_L2H-1 | Te4/0/20 | L2-DIST-1 Te4/0/20 | L2 Trunk | 101, 1301 | TACACS/local |
| FS2_L2H-1 | Te4/0/21 | L2-DIST-2 Te1/0/20 | L2 Trunk | 101, 1301 | TACACS/local |
| L2-DIST-1 | Te4/0/20 | FS2_L2H-1 Te4/0/20 | L2 Trunk | 101, 1301 | Local only |
| L2-DIST-2 | Te1/0/20 | FS2_L2H-1 Te4/0/21 | L2 Trunk | 101, 1301 | Local only |
| FS2_L2_9300-1 | Trunk | L2-DIST-1 | L2 Access | 101, 1301 | Local only |
| FS2_L2_9300-2 | Trunk | L2-DIST-2 | L2 Access | 101, 1301 | Local only |

**CRITICAL:** Distribution and access switches use **local authentication ONLY** (admin/CXlabs.123). They are NOT in ISE or TACACS.

### VLANs Under Test

- **VLAN 101** (BMS1): 10.5.28.0/22 (1,024 addresses)
- **VLAN 1301** (EUT): 10.5.20.0/22 (1,024 addresses)

**STP Configuration:**
- Root Bridge: FS2_L2H-1 for both VLANs (STP priority 4096 or lower)
- Both trunks: ACTIVE (not LACP, no port-channel)
- Failover: STP reconverges to Te4/0/21 when Te4/0/20 fails

---

## Test Scenario

### Phase 1: Steady State Baseline

**Both L2 trunks operational:**
- Te4/0/20: UP (will be shut down)
- Te4/0/21: UP (will provide redundancy)
- STP: FS2_L2H-1 is root for VLANs 101, 1301
- DIST-1 and DIST-2 both forwarding
- Fabric side (Po40/Po41): Both UP, ECMP active
- Spirent: 400+ streams alive, 0% loss

### Phase 2: Failure Event - Shutdown Te4/0/20

**Standard (`run_tc_07-04.py`):** `interface TenGigabitEthernet4/0/20` → `shutdown` on FS2_L2H-1  
**Dist Side (`run_tc_07-04_dist_side.py`):** `interface TenGigabitEthernet4/0/20` → `shutdown` on L2-DIST-1

**Expected STP Convergence Behavior:**
1. Te4/0/20 goes down immediately
2. STP detects topology change (TCN BPDU)
3. L2-DIST-1 loses uplink, transitions ports to LISTENING → LEARNING → FORWARDING
4. Traffic shifts to Te4/0/21 via L2-DIST-2
5. **Expected convergence:** 2-30 seconds (standard STP timers)
6. **Expected packet loss:** Measurable during STP convergence (not hitless like OSPF/ECMP)

**During Failure State:**
- Te4/0/20: Protocol Down (failed trunk)
- Te4/0/21: UP (carrying all L2 traffic to legacy site)
- STP: L2-DIST-2 becomes primary path
- **Fabric side MUST remain stable:**
  - Po40/Po41: Both UP (no impact)
  - OSPF: Both BC1 and BC2 adjacencies FULL
  - LISP: Both sessions UP
  - BFD: Both sessions UP

**Key Validation Points:**
- STP convergence time (measured via Spirent)
- Packet loss during STP transition
- MAC address table flush/relearn
- No impact to fabric side (Po40/Po41 stability)

### Phase 3: Recovery - Restore Te4/0/20

**Command:** `interface TenGigabitEthernet4/0/20` → `no shutdown`

**Expected Recovery Behavior:**
1. Te4/0/20 comes up
2. STP reconverges, both trunks active again
3. Traffic may redistribute across both trunks (depends on STP path costs)
4. MAC address tables reconverge
5. Spirent: All streams return to baseline

---

## Prerequisites

### Hardware Requirements

- **FS2_L2H-1** (172.31.0.194) - Catalyst 9404R - L2 Border Device
- **L2-DIST-1** (172.31.0.193) - Catalyst 9404R - Legacy Distribution Switch
- **L2-DIST-2** (172.31.0.180) - Catalyst 9404R/9600R - Legacy Distribution Switch
- **FS2_BC1** (172.31.2.0) - Catalyst 9606R - Border Controller (health monitoring)
- **Spirent STCv** (172.31.0.22:8088) - Traffic generator

### Software Requirements

- **IOS-XE:** 17.15.04 (or documented version)
- **Python:** 3.7+
- **Python Libraries:** `netmiko` (install via `pip3 install netmiko`)

### Topology Requirements

✅ Te4/0/20 and Te4/0/21 both operational (L2 trunks)  
✅ VLANs 101 and 1301 allowed on both trunks  
✅ STP root: FS2_L2H-1 for both VLANs  
✅ Legacy distribution switches reachable (172.31.0.193, 172.31.0.180)  
✅ Fabric side stable (Po40/Po41, OSPF, LISP)  

### Credentials

| Device | Primary | Fallback | Notes |
|--------|---------|----------|-------|
| FS2_L2H-1 | admin1/CXlabs.123 | admin/CXlabs.123 | Script has auto-fallback |
| L2-DIST-1 | admin/CXlabs.123 | N/A | **LOCAL AUTH ONLY (no TACACS)** |
| L2-DIST-2 | admin/CXlabs.123 | N/A | **LOCAL AUTH ONLY (no TACACS)** |
| FS2_BC1 | admin1/CXlabs.123 | dnac_admin_tacacs/CXlabs.123 | May need alternate creds |
| FS2_L2_9300-1 | admin/CXlabs.123 | N/A | **LOCAL AUTH ONLY** (dist_side only) |
| FS2_L2_9300-2 | admin/CXlabs.123 | N/A | **LOCAL AUTH ONLY** (dist_side only) |

**CRITICAL:** Distribution and access switches are legacy devices NOT provisioned in ISE/TACACS. Scripts use `admin/CXlabs.123` directly.

### Traffic Validation

✅ Spirent GUI accessible at http://172.31.0.22:8088  
✅ Baseline traffic: 400+ streams alive, 0% loss  
✅ Spirent PLA tool available at http://spirent-pla.cisco.com  
✅ Streams crossing L2 Border to legacy site identified (VLANs 101, 1301)  

---

## Usage

### Basic Usage — L2 Border Side (Standard)

```bash
# Shutdown Te4/0/20 on FS2_L2H-1 (L2 Border side)
python3 run_tc_07-04.py --iter 1
python3 run_tc_07-04.py --iter 2
python3 run_tc_07-04.py --iter 3
```

### Basic Usage — Distribution Side (Reverse)

```bash
# Shutdown Te4/0/20 on L2-DIST-1 (Distribution switch side)
python3 run_tc_07-04_dist_side.py --iter 1
python3 run_tc_07-04_dist_side.py --iter 2
python3 run_tc_07-04_dist_side.py --iter 3
```

**Dist Side differences:**
- Shuts the **same trunk** but from the **opposite end** (L2-DIST-1 instead of L2H-1)
- L2H-1 sees **link-down** (not admin-down) — CC may raise an issue
- Collects from **7 devices** including FS2_L2_9300-1 and FS2_L2_9300-2 (legacy access)
- Includes **multicast verification** (PIM, MFIB, IGMP snooping) at each phase
- CLI evidence saved to `DistSide/Iter{N}_CLI/` subdirectory
- Screenshots saved to `DistSide/Images/Iteration{N}/`

### Script Workflow

1. **Pre-Test Validation:**
   - Connects to 5 devices: L2H-1, DIST-1, DIST-2, BC1 (health check)
   - Handles TACACS authentication on L2H-1 with automatic fallback to local
   - Uses local-only authentication for DIST-1 and DIST-2
   - Collects baseline CLI outputs and saves to `Iter{N}_CLI/` directory

2. **Manual Pause Points:**
   - Script pauses and asks you to take Spirent screenshots (baseline)
   - Script pauses and asks you to take Catalyst Center screenshots
   - Press ENTER when ready to continue

3. **Failure Event:**
   - Script shuts down Te4/0/20 on FS2_L2H-1
   - Script waits 10 seconds for STP convergence (longer than OSPF tests due to STP timers)
   - Script collects "during failure" CLI outputs

4. **Manual Evidence Collection:**
   - Script pauses for you to capture Spirent failure screenshots
   - Take screenshots showing STP convergence time, packet loss
   - Monitor L2-DIST-1 (should be isolated) and L2-DIST-2 (should be active)

5. **Recovery:**
   - Script restores Te4/0/20 (no shutdown)
   - Script waits 15 seconds for STP reconvergence
   - Script collects "post recovery" CLI outputs

6. **Final Evidence:**
   - Script pauses for you to capture Spirent recovery screenshots
   - Verify all streams returned to baseline

### CLI Outputs Collected

**Per device:**

**FS2_L2H-1 (L2 Border):**
- `show version`, `show inventory`
- `show interface Te4/0/20` (failed trunk)
- `show interface Te4/0/21` (redundant trunk)
- `show spanning-tree vlan 101`, `show spanning-tree vlan 1301`
- `show port-channel summary` (Po40/Po41 health)
- `show ip ospf neighbor` (BC1/BC2 adjacencies)
- `show lisp session` (BC1/BC2 sessions)
- `show bfd neighbors` (BC1/BC2 BFD)

**L2-DIST-1 (Target of failed trunk):**
- `show interface Te1/1/1` (uplink to L2H-1 Te4/0/20)
- `show spanning-tree vlan 101`, `show spanning-tree vlan 1301`
- `show mac address-table vlan 101`, `show mac address-table vlan 1301`

**L2-DIST-2 (Redundant path):**
- `show interface Te1/1/1` (uplink to L2H-1 Te4/0/21)
- `show spanning-tree vlan 101`, `show spanning-tree vlan 1301`
- `show mac address-table vlan 101`, `show mac address-table vlan 1301`

**FS2_BC1 (Fabric health check):**
- `show ip ospf neighbor` (verify no impact to fabric)
- `show lisp session` (verify no impact to fabric)
- `show port-channel summary` (Po40 health)

**Standard script (`run_tc_07-04.py`) saved to:**
- `Iter1_CLI/` - Iteration 1 evidence
- `Iter2_CLI/` - Iteration 2 evidence
- `Iter3_CLI/` - Iteration 3 evidence

**Dist Side script (`run_tc_07-04_dist_side.py`) saved to:**
- `DistSide/Iter1_CLI/` - Iteration 1 evidence (18 files per iteration)
- `DistSide/Iter2_CLI/` - Iteration 2 evidence
- `DistSide/Iter3_CLI/` - Iteration 3 evidence

**Dist Side additional collections per device:**

**FS2_L2_9300-1 (Legacy access behind DIST-1):** *(dist_side only)*
- `show interfaces trunk`, `show spanning-tree vlan 101/1301`
- `show mac address-table vlan 101/1301`, `show cdp neighbors`
- `show ip igmp snooping groups vlan 101/1301`
- STP topology change notifications during failure

**FS2_L2_9300-2 (Legacy access behind DIST-2):** *(dist_side only)*
- Same commands as 9300-1, verifies unaffected by failure

**Multicast verification (all devices, dist_side only):**
- `show ip mroute vrf BMS1 225.1.1.1`, `show ip mfib vrf BMS1 225.1.1.1`
- `show ip pim vrf BMS1 neighbor`, `show ip pim vrf BMS1 rp mapping`
- `show ip igmp snooping groups vlan 101/1301`

### Evidence Collection

**Manual screenshots required:**
1. Spirent baseline (before shutdown)
2. Catalyst Center health (before shutdown)
3. Spirent during failure (STP convergence time, packet loss)
4. Catalyst Center health during failure (may show warning)
5. Spirent post-recovery (all streams alive)
6. Catalyst Center health post-recovery (all devices healthy)

**Repeat for each iteration** (18+ screenshots total across 3 iterations)

---

## Expected Results

### Success Criteria

| Metric | Target | Pass Threshold | Notes |
|--------|--------|----------------|-------|
| **STP Convergence Time** | 2-30 seconds | <50 seconds | STP standard timers (slower than OSPF) |
| **Packet Loss** | <5% | <10% | Measurable loss during STP transition (NOT hitless) |
| **Te4/0/21 Traffic Shift** | Yes | Yes | All L2 traffic shifts to DIST-2 |
| **Fabric Side Stability** | 100% | 100% | Po40/Po41, OSPF, LISP, BFD unaffected |
| **Device Stability** | No crashes | No crashes | All devices stable |

**IMPORTANT:** This test is **NOT hitless** like TC 07-02/07-03. STP convergence takes 2-30 seconds, resulting in measurable packet loss. This is **expected behavior** for Layer 2 failover.

### Consistency Validation

Run **3 iterations** and verify:
- All 3 iterations pass individual success criteria
- STP convergence time varies by ≤20% across iterations
- Packet loss varies by ≤20% across iterations
- Fabric side (Po40/Po41, OSPF, LISP) stable in all iterations

### Comparison to TC 07-02/07-03

| Metric | TC 07-02/07-03 (L3 ECMP) | TC 07-04 (L2 STP) | Why Different? |
|--------|--------------------------|-------------------|----------------|
| **Convergence** | <1 second | 2-30 seconds | OSPF/ECMP vs. STP timers |
| **Packet Loss** | <1% | <5% | Hitless L3 vs. disruptive L2 |
| **Mechanism** | OSPF reroute | STP reconverge | Protocol difference |
| **Scope** | Fabric (BC1/BC2) | Legacy site (DIST-1/DIST-2) | Different failure domain |

**Key Insight:** TC 07-04 validates that **fabric side remains stable** during legacy L2 site failures, proving isolation between SDA fabric and legacy L2 domains.

---

## Troubleshooting

### Common Issues

#### 1. Cannot Connect to L2-DIST-1 or L2-DIST-2

**Symptom:** Script fails to connect with "Authentication failed"  
**Resolution:**
- Distribution switches use **LOCAL AUTH ONLY** (no TACACS)
- Credentials: `admin/CXlabs.123` (hardcoded in script)
- Verify: `ssh admin@172.31.0.193` and `ssh admin@172.31.0.180`
- If password changed, update script `DIST1` and `DIST2` dictionaries

#### 2. STP Convergence >50 Seconds

**Symptom:** Spirent shows extended outage  
**Resolution:**
- Check STP timers: `show spanning-tree vlan 101`
- Verify FS2_L2H-1 is root: `show spanning-tree root`
- Check for STP PortFast or RSTP: `show spanning-tree summary`
- Consider enabling RSTP if using classic STP (not typically done mid-test)

#### 3. Fabric Side Impacted (Po40/Po41 Flap)

**Symptom:** OSPF or LISP sessions drop during L2 trunk failure  
**Resolution:**
- **STOP TEST** - This indicates cross-domain issue
- Verify Te4/0/20 shutdown only affects L2 trunks, not Po40/Po41
- Check for shared physical resources (transceivers, linecards)
- Review L2H-1 logs: `show logging | include Te4/0/20|Po40|Po41`

#### 4. No Traffic Shift to L2-DIST-2

**Symptom:** Spirent shows 100% loss even after STP converges  
**Resolution:**
- Verify Te4/0/21 is UP: `show interface Te4/0/21`
- Check STP on L2-DIST-2: `show spanning-tree vlan 101 101 1301`
- Verify MAC address table: `show mac address-table vlan 101`
- Check for VLAN pruning on trunk: `show interfaces trunk`
- Verify end-to-end L2 connectivity: `ping` from DIST-2 to endpoints

#### 5. L2H-1 TACACS Reconnect Fails (Iter1 Known Issue)

**Symptom:** Script crashes at Step 2.2 during TACACS reconnect  
**Resolution:**
- Use `continue_iter1.py` script to resume from Step 2.2
- Or manually use local credentials: `ssh admin@172.31.0.194`
- Script has been updated with `connect_l2h1()` fallback function
- If TACACS down, use local credentials throughout

#### 6. Catalyst Center Raises "Interface Down" Alert

**Symptom:** CC shows critical alert for Te4/0/20 down  
**Resolution:**
- **This is expected behavior**
- CC monitors interface state and raises alerts for link down
- **IMPORTANT:** CC distinguishes admin-shutdown from fault
- Admin-shutdown (intentional) vs. physical failure (fault)
- No remediation needed, document that alert is expected

---

## Deliverables

1. **CLI Evidence:** `Iter1_CLI/`, `Iter2_CLI/`, `Iter3_CLI/`
   - 13 outputs per iteration (L2H-1: 8, DIST-1: 3, DIST-2: 3, BC1: 3)
   - 39 files total across 3 iterations

2. **Spirent Screenshots:** `Images/` folder
   - Iteration1: 6 screenshots
   - Iteration2: 6 screenshots
   - Iteration3: 6 screenshots
   - Total: 18+ screenshots

3. **CXTM Results:** `TC-07-04_CXTM_Results.txt`
   - PASS/FAIL determination
   - STP convergence metrics
   - 3-iteration consistency validation

4. **Spirent Database:** `Spirent_DB/` (optional)
   - .tcc files for each iteration
   - PLA results

---

## Key Differences from TC 07-02/07-03

| Aspect | TC 07-02/07-03 | TC 07-04 |
|--------|----------------|----------|
| **Failure Domain** | SDA Fabric (Border Controllers) | Legacy L2 Site (Distribution Switches) |
| **Protocol** | OSPF/LISP (Layer 3) | STP (Layer 2) |
| **Convergence** | <1 second (hitless) | 2-30 seconds (disruptive) |
| **Packet Loss** | <1% | <5% |
| **Devices Tested** | 3 (L2H-1, BC1, BC2) | 4 (L2H-1, DIST-1, DIST-2, BC1) |
| **Authentication** | TACACS with fallback | Local only (DIST switches) |
| **Redundancy Type** | ECMP (dual-homed) | STP (dual trunk) |
| **Impact Scope** | Fabric traffic | Legacy site traffic only |

**Critical Insight:** TC 07-04 proves that **SDA fabric remains stable** when legacy L2 site experiences failures, validating proper isolation and resilience of the SDA infrastructure.

---

## Files in This Directory

| File | Purpose | Size |
|------|---------|------|
| `run_tc_07-04.py` | Main automation — shutdown on L2H-1 (L2 Border side) | 766 lines |
| `run_tc_07-04_dist_side.py` | Reverse variant — shutdown on L2-DIST-1 (Distribution side) | 974 lines |
| `continue_iter1.py` | Recovery script for Iter1 TACACS issue | 525 lines |
| `README.md` | Comprehensive documentation | This file |
| `TC-07-04_CXTM.txt` | Test case specification | 22 KB |
| `00_START_HERE.txt` | Quick start guide | |

---

## Related Test Cases

| Test ID | Description | Relationship |
|---------|-------------|--------------|
| **TC 07-01** | Link Failure L2 Border Po Member | Single member link failure |
| **TC 07-02** | Link Failure L2 Border Complete Po | Original single-homed test |
| **TC 07-02 Retest** | Dual-Homed Po40 Failure | L3 ECMP to BC2 |
| **TC 07-03** | Dual-Homed Po41 Failure | L3 ECMP to BC1 |
| **TC 07-04** | Link Failure to Distribution Switch | L2 STP to legacy site |

**Complete Phase 07 Coverage:**
- TC 07-01: LACP member resilience
- TC 07-02 Retest + TC 07-03: SDA fabric ECMP resilience (bidirectional)
- TC 07-04: Legacy L2 site STP resilience

---

## Local Working Directory

**Location:** `/Users/wbenbark/MS_SVS_SDA_Phase2/Test Case Logs/07-04_Link_Failure_From_L2_Border_to_Distribution_Switch/`

**Contents:**
- `run_tc_07-04.py` - Main script (766 lines)
- `continue_iter1.py` - Recovery helper (525 lines)
- `TC-07-04_CXTM.txt` - Test specification (22 KB)
- `Iter1_CLI/`, `Iter2_CLI/`, `Iter3_CLI/` - CLI evidence (3 iterations complete)
- `Images/` - Spirent screenshots
- `Spirent_DB/` - Spirent .tcc files

---

## Quick Start

```bash
# Clone repo
git clone https://github.com/wbenbarkgithub/general.git
cd general/Morgan_Stanley_SDA_Phase2/TC_07-04_Link_Failure_L2_Border_to_Dist_Switch

# Install dependencies
pip3 install netmiko

# === Standard Test (shutdown on L2 Border side) ===
python3 run_tc_07-04.py --iter 1
python3 run_tc_07-04.py --iter 2
python3 run_tc_07-04.py --iter 3

# === Dist Side Test (shutdown on Distribution switch side) ===
python3 run_tc_07-04_dist_side.py --iter 1
python3 run_tc_07-04_dist_side.py --iter 2
python3 run_tc_07-04_dist_side.py --iter 3

# If Iter1 crashes at TACACS reconnect:
python3 continue_iter1.py
```

**Manual Steps During Script Execution:**
1. Take Spirent screenshots at each PAUSE (baseline, failure, recovery)
2. Take Catalyst Center screenshots
3. Monitor STP convergence time via Spirent PLA
4. Save screenshots to `Images/Iteration{N}/` folders

---

## Support

### Documentation References

- **CXTM Format:** `TC-07-04_CXTM.txt`
- **Memory References:**
  - Memory #17: Negative Test Cases Framework
  - Memory #24: TACACS credential issues
  - Memory #46: TC 07-01 (LACP member failure)
  - Memory #47: TC 07-02 (Complete Po failure, dual-homing)
  - Memory #50: TC 07-03 (Mirror test, bidirectional validation)

### GitHub Repository

https://github.com/wbenbarkgithub/general/tree/main/Morgan_Stanley_SDA_Phase2/TC_07-04_Link_Failure_L2_Border_to_Dist_Switch

---

## License

Internal Morgan Stanley SDA Phase 2 testbed validation. Not for external distribution.

---

**Last Updated:** April 9, 2026  
**Tested By:** SVS Lab Team  
**Test Status:** ✅ PASS (3 iterations completed, STP convergence <30s, fabric stable)  
**Dist Side Status:** ✅ Added — shutdown from L2-DIST-1 with multicast + legacy access switch verification
