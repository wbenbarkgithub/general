# TC 07-02 RETEST - Dual-Homed Topology Validation

**Created:** April 7, 2026 | **Updated:** April 9, 2026  
**Status:** PASS (3 iterations completed April 7-9, 2026)  
**Purpose:** Retest TC 07-02 after implementing Po41 dual-homing to FS2_BC2

---

## Why This Retest?

### Topology Change

**Original Test (Completed Earlier Today):**
```
FS2_L2H-1 ----Po40 (Te4/0/1-2)----> FS2_BC1 ONLY
```
- **Single point of failure**
- Po40 shutdown → **Complete connectivity loss**
- Recovery time: **~2 minutes** (LACP ~13s, OSPF ~10s, LISP ~80s)
- Significant dead flows and packet loss

**NEW Topology (After Po41 Implementation):**
```
              ┌─ Po40 (Te4/0/1-2) ──> FS2_BC1 (192.168.40.0/31)
              |
FS2_L2H-1 ────┤
              |
              └─ Po41 (Te4/0/3-4) ──> FS2_BC2 (192.168.41.0/31)
```
- **Dual-homed with ECMP load-balancing**
- Po40 shutdown → **Po41 provides instant redundancy**
- Expected convergence: **Sub-second or hitless**
- Expected dead flows: **Minimal or ZERO**

---

## Key Differences from Original Test

| Aspect | Original (Single-Homed) | Retest (Dual-Homed) |
|--------|-------------------------|---------------------|
| **Topology** | Po40 only | Po40 + Po41 (ECMP) |
| **Po40 Failure Impact** | Total loss | Po41 continues traffic |
| **Convergence Time** | ~2 minutes | Sub-second |
| **Packet Loss** | 3-10 seconds | <1 second or hitless |
| **Dead Flows** | 50-200+ | Minimal or ZERO |
| **OSPF During Failure** | All DOWN | BC2 remains FULL |
| **BFD During Failure** | All DOWN | BC2 remains UP |
| **TACACS Access** | Local admin required | TACACS works via Po41 |
| **Expected Result** | Graceful recovery | Near-instant failover |

---

## Script Changes

### Enhanced Device Collection (v2.0 — April 8-9, 2026)

**Original:** Collected from FS2_L2H-1 and FS2_BC1 only  
**Updated (v2.0):** Collects from **5 devices:**
1. **FS2_L2H-1** (172.31.0.194) - L2 Border with dual port-channels
2. **FS2_BC1** (172.31.2.0) - Border Controller for Po40
3. **FS2_BC2** (172.31.2.2) - Border Controller for Po41
4. **FS2_L2_9300-1** (172.31.0.179) - Legacy L2 switch (STP/IGMP snooping) (**NEW v2.0**)
5. **FS2_L2_9300-2** (172.31.0.178) - Legacy L2 switch (STP/IGMP snooping) (**NEW v2.0**)

### New Commands Added

**Dual Port-Channel Monitoring:**
- `show etherchannel 41 summary` - Monitor Po41 status
- `show interfaces Port-channel41` - Po41 interface details
- `show lacp 41 neighbor/counters` - LACP for Po41

**ECMP Verification:**
- `show ip route ospf | include 192.168` - Verify dual paths
- `show bfd neighbors` - BFD sessions to both BCs

**Multicast Verification (v2.0):**
- `show ip mroute vrf BMS1 225.1.1.1` - Multicast route table (all phases)
- `show ip mfib vrf BMS1 225.1.1.1` - MFIB hardware counters (forwarding proof)
- `show ip pim vrf BMS1 neighbor` - PIM neighbors during failure
- `show ip igmp snooping groups vlan 101` - IGMP snooping on BMS1 VLAN
- `show ip igmp snooping groups vlan 1301` - IGMP snooping on EUT VLAN

**L2_9300 Switch Collection (v2.0):**
- `show spanning-tree vlan 101/1301` - STP topology during failure
- `show mac address-table vlan 101/1301` - MAC table changes
- `show ip igmp snooping groups vlan 101/1301` - IGMP snooping state
- `show logging | include STP|TCN` - STP topology change events

**BC2-Specific Collection:**
- Full CLI collection from FS2_BC2 during all phases
- Verify Po41 stays UP during Po40 failure

### Updated Expectations

**Phase 1 (Baseline):**
- Verify BOTH Po40 and Po41 are UP
- Verify OSPF FULL to BOTH BC1 and BC2
- Verify ECMP routing (equal cost via both paths)
- Verify BFD sessions to both BCs
- Verify multicast mroute 225.1.1.1 present in VRF BMS1 (v2.0)
- Verify L2_9300-1/2 IGMP snooping groups on VLAN 101/1301 (v2.0)

**Phase 2 (Failure):**
- Po40 goes DOWN ✓ (expected)
- **Po41 MUST stay UP** ✓ (CRITICAL - validates dual-homing)
- OSPF to BC1 goes DOWN ✓ (expected)
- **OSPF to BC2 stays FULL** ✓ (CRITICAL)
- **BFD to BC2 stays UP** ✓ (CRITICAL)
- TACACS remains accessible via Po41 (no need for local admin)
- Minimal packet loss (<1 sec) or HITLESS
- Dead flows: MINIMAL or ZERO
- Multicast: mroute/MFIB/PIM maintained via Po41 (v2.0)
- L2_9300: STP topology changes and IGMP snooping captured (v2.0)

**Phase 3 (Recovery):**
- Po40 restores normally
- ECMP resumes (traffic via both Po40 and Po41)
- No traffic impact during recovery (Po41 already carrying load)
- Multicast: mroute/MFIB/PIM/IGMP restored to baseline (v2.0)

---

## Prerequisites

### Network Topology
- FS2_L2H-1 Po41 configured to FS2_BC2 ✅ (completed April 7, 2026 at 11:56 AM)
- OSPF adjacency on Po41: FULL ✅
- BFD session on Po41: UP ✅
- ECMP load-balancing: ACTIVE ✅

### Lab Access
- VPN connected to SVS lab
- SSH access to:
  - FS2_L2H-1: 172.31.0.194 (admin1/CXlabs.123)
  - FS2_BC1: 172.31.2.0 (admin1/CXlabs.123)
  - FS2_BC2: 172.31.2.2 (admin1 or dnac_admin_tacacs/CXlabs.123)
- Spirent GUI: 172.31.0.101
- Catalyst Center: https://172.31.229.151
- Spirent PLA: http://spirent-pla.cisco.com

### Software Requirements
```bash
pip install netmiko
```

---

## Quick Start

### Run Retest

```bash
cd "/Users/wbenbark/MS_SVS_SDA_Phase2/Test Case Logs/07-02_Link_Failure_From_L2_Border_PortChannel_to_Fabric_BC_Node/retest"

# Iteration 1
python3 run_tc_07-02_retest.py --iter 1

# Iteration 2
python3 run_tc_07-02_retest.py --iter 2

# Iteration 3
python3 run_tc_07-02_retest.py --iter 3
```

### Execution Time
- **Per iteration:** 25-40 minutes
- **Total (3 iterations):** 75-120 minutes

---

## Expected Results Checklist

### ✅ Dual-Homing Validation (PASS Criteria)

**Baseline (Phase 1):**
- [ ] Po40 UP with 2 members to BC1
- [ ] Po41 UP with 2 members to BC2
- [ ] OSPF FULL to both BC1 (192.168.40.1) and BC2 (192.168.41.1)
- [ ] BFD UP to both BCs
- [ ] ECMP routes visible (equal cost via Po40 and Po41)
- [ ] 2 LISP sessions UP
- [ ] Spirent: 0.000% loss

**During Po40 Failure (Phase 2):**
- [ ] Po40 goes DOWN (EXPECTED)
- [ ] **Po41 stays UP** (CRITICAL - validates dual-homing)
- [ ] OSPF to BC1 goes DOWN (EXPECTED)
- [ ] **OSPF to BC2 stays FULL** (CRITICAL)
- [ ] **BFD to BC2 stays UP** (CRITICAL)
- [ ] TACACS accessible via Po41 (no local admin needed)
- [ ] Spirent: Minimal loss (<1 sec) or HITLESS
- [ ] Dead flows: MINIMAL or ZERO
- [ ] PLA convergence analysis: Sub-second

**Recovery (Phase 3):**
- [ ] Po40 restores with 2 members
- [ ] OSPF to BC1 restores to FULL
- [ ] ECMP resumes (routes via both Po40 and Po41)
- [ ] Spirent: 0.000% loss restored
- [ ] All baseline metrics restored

---

## Evidence Collection

### CLI Files (15 per iteration — v2.0)

**Baseline (5 files):**
- `Iter{n}_Pre_L2H1_Baseline.txt` - FS2_L2H-1 pre-test state (incl. multicast)
- `Iter{n}_Pre_BC1_Baseline.txt` - FS2_BC1 pre-test state (incl. multicast)
- `Iter{n}_Pre_BC2_Baseline.txt` - FS2_BC2 pre-test state (incl. multicast)
- `Iter{n}_Pre_L2_9300-1_Baseline.txt` - L2 switch STP/IGMP baseline (**NEW v2.0**)
- `Iter{n}_Pre_L2_9300-2_Baseline.txt` - L2 switch STP/IGMP baseline (**NEW v2.0**)

**During Failure (5 files):**
- `Iter{n}_During_L2H1_Failure.txt` - L2H-1 with Po40 DOWN, Po41 UP (incl. multicast)
- `Iter{n}_During_BC1_Status.txt` - BC1 with Po40 DOWN (incl. multicast)
- `Iter{n}_During_BC2_Status.txt` - BC2 with Po41 UP (incl. multicast, **CRITICAL**)
- `Iter{n}_During_L2_9300-1_Status.txt` - L2 switch STP/IGMP during failure (**NEW v2.0**)
- `Iter{n}_During_L2_9300-2_Status.txt` - L2 switch STP/IGMP during failure (**NEW v2.0**)

**Post Recovery (5 files):**
- `Iter{n}_Post_L2H1_Validation.txt` - L2H-1 with ECMP restored (incl. multicast)
- `Iter{n}_Post_BC1_Validation.txt` - BC1 with Po40 restored (incl. multicast)
- `Iter{n}_Post_BC2_Validation.txt` - BC2 with Po41 continuing (incl. multicast)
- `Iter{n}_Post_L2_9300-1_Validation.txt` - L2 switch STP/IGMP restored (**NEW v2.0**)
- `Iter{n}_Post_L2_9300-2_Validation.txt` - L2 switch STP/IGMP restored (**NEW v2.0**)

### Screenshots (8 per iteration)
Same as original test:
- Phase 1: Spirent baseline, CC L2H-1 health, CC network health
- Phase 2: Spirent convergence, CC L2H-1 status during failure
- Phase 3: Spirent restored, CC L2H-1 health, CC network health

### Spirent Analysis (3 files per iteration)
- `Iter{n}_During_Spirent_DB.tcc` - Spirent database export
- `Iter{n}_PLA_Convergence_Analysis.xlsx` - PLA analysis Excel
- `Iter{n}_PLA_Analysis.png` - PLA screenshot

**Total evidence per iteration:** 26 files (15 CLI + 8 screenshots + 3 Spirent)  
**Total evidence (3 iterations):** 78 files

---

## Success Criteria

### Primary Objective
Validate that **dual-homing eliminates the ~2-minute outage** observed in the original single-homed test.

### Pass Criteria
1. **Po41 redundancy works:**
   - Po41 stays UP during entire Po40 failure
   - OSPF to BC2 stays FULL
   - BFD to BC2 stays UP
   - Traffic continues via Po41

2. **Convergence improvement:**
   - Packet loss < 1 second (vs. 3-10 seconds single-homed)
   - Dead flows: minimal or ZERO (vs. 50-200+ single-homed)
   - Total convergence: sub-second (vs. ~2 minutes single-homed)

3. **ECMP behavior:**
   - Baseline: Traffic distributed across Po40 and Po41
   - Failure: Traffic shifts to Po41 only
   - Recovery: Traffic resumes ECMP distribution

4. **Consistency:**
   - Results consistent across 3 iterations (±20%)

### Fail Criteria
- Po41 goes DOWN during Po40 failure (dual-homing failed)
- OSPF to BC2 goes DOWN during Po40 failure
- Convergence time > 5 seconds
- Dead flows comparable to single-homed test (50+)
- ECMP does not resume after Po40 recovery

---

## Troubleshooting

### Po41 Goes DOWN During Po40 Failure
**Root Cause:** Dual-homing not working correctly  
**Actions:**
1. Check Po41 LACP: `show lacp 41 neighbor` on both L2H-1 and BC2
2. Check OSPF config: `show ip ospf interface Po41`
3. Check BFD: `show bfd neighbors`
4. Verify IP addressing: 192.168.41.0/31
5. **ABORT TEST** and fix dual-homing before continuing

### BC2 SSH Fails with admin1
**Root Cause:** Memory #24 - Some devices require alternate credentials  
**Solution:** Script auto-retries with `dnac_admin_tacacs` username

### ECMP Not Working in Baseline
**Root Cause:** OSPF cost mismatch between Po40 and Po41  
**Actions:**
1. Check: `show ip route ospf | include 192.168`
2. Verify equal costs on both paths (should be cost 105 via BCs)
3. Check OSPF interface costs: `show ip ospf interface Po40` and `Po41`

### TACACS Still Requires Local Admin
**Root Cause:** Po41 not providing connectivity  
**Actions:**
1. Verify Po41 is UP: `show interfaces Po41`
2. Check routing: `ping 10.40.60.1 source lo0` (TACACS server)
3. If Po41 is DOWN, this is a **CRITICAL FAILURE** - abort test

---

## Comparison Analysis

After completing all 3 iterations, create comparative analysis:

### Metrics to Compare

| Metric | Original (Single) | Retest (Dual) | Improvement |
|--------|-------------------|---------------|-------------|
| **Po Redundancy** | None | Po41 to BC2 | Instant failover |
| **Convergence Time** | ~2 minutes | Sub-second | ~120x faster |
| **Packet Loss Duration** | 3-10 seconds | <1 second | ~5-10x reduction |
| **Dead Flows** | 50-200+ | 0-10 | ~95%+ reduction |
| **OSPF Recovery** | 10-30 seconds | Already converged | Instant |
| **LISP Recovery** | 80+ seconds | N/A (stays up) | N/A |
| **TACACS Access** | Lost (local admin) | Maintained | Available |

---

## Deliverables

### Technical Report
Create Word document with:
1. Executive Summary - Single-homed vs. Dual-homed comparison
2. Topology Before/After diagrams
3. Test Results Summary - 3 iterations each configuration
4. Convergence Analysis - PLA data comparison
5. All CLI evidence embedded
6. All screenshots embedded
7. Conclusion and recommendations

### CXTM Update
Update TC 07-02 CXTM with:
- Retest date and topology change
- New expected results (hitless vs. 2-minute outage)
- Dual-homing validation pass/fail
- Reference to Po41 implementation (April 7, 2026)

---

## Related Documentation

**Po41 Implementation:**
- `/Users/wbenbark/MS_SVS_SDA_Phase2/Test Case Logs/07-02_Link_Failure_From_L2_Border_PortChannel_to_Fabric_BC_Node/Po41_Implementation_20260407_115546/`
- `DUAL_HOMING_ENHANCEMENT_Po41_Implementation.md`
- `IMPLEMENTATION_SUMMARY.md`

**Original Test Results:**
- `../TC-07-02_Complete_Port_Channel_Failure_Report_20260407.docx`
- `../Iter1_CLI/`, `../Iter2_CLI/`, `../Iter3_CLI/`
- `../TC-07-02_CXTM_Results.txt`

**Test Case Documentation:**
- `../TC-07-02_CXTM.txt` - Original test case
- `../TC-07-02_Execution_Plan.txt` - Manual execution guide
- `../README.md` - Original test documentation

**Memory References:**
- Memory #48: `project_fs2_l2h_dual_homing.md` - Project tracking
- Memory #24: `feedback_tacacs_credentials.md` - BC2 credential workarounds

---

## Notes

1. **Test Timing:** Run retest ASAP while original results are fresh for accurate comparison

2. **No Changes to Spirent:** Spirent traffic profiles remain unchanged from original test

3. **BC2 Credentials:** Script handles potential TACACS credential rejection automatically

4. **TACACS Access:** Unlike original test, TACACS remains accessible via Po41 during Po40 failure - no need to switch to local admin account

5. **Test Validity:** This retest validates the Po41 dual-homing enhancement and quantifies the improvement over single-homed topology

---

**Document Version:** 2.0  
**Created:** April 7, 2026 | **Updated:** April 9, 2026  
**Author:** Claude Code (Anthropic)  
**Project:** Morgan Stanley SDA Phase 2 - TC 07-02 Retest (Dual-Homed)

### Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | April 7, 2026 | Initial retest script (3 devices: L2H-1, BC1, BC2) |
| 2.0 | April 8-9, 2026 | Added multicast 225.1.1.1 verification (mroute/MFIB/PIM/IGMP) across all phases. Added L2_9300-1 and L2_9300-2 collection (STP topology, IGMP snooping, MAC tables). 5 devices, 15 CLI files per iteration. Updated CXTM to unified format (PASS). |
