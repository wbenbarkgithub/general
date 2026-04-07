# TC 07-02 Retest - Created Files Summary

**Date:** April 7, 2026  
**Status:** Ready for Execution  
**Purpose:** Retest TC 07-02 with dual-homed topology (Po40 + Po41)

---

## Files Created in `/retest/` Folder

### 1. `run_tc_07-02_retest.py` (Executable)
- **Size:** ~25 KB
- **Purpose:** Automated test execution script for dual-homed topology
- **Key Updates:**
  - Added BC2 device configuration and connection handling
  - Enhanced CLI collection (9 files per iteration vs. 6)
  - ECMP verification commands added
  - Po41 monitoring throughout all phases
  - Updated expectations (hitless vs. 2-minute outage)
  - Alternate credentials for BC2 (dnac_admin_tacacs fallback)

**New Device Collection:**
- FS2_L2H-1 (172.31.0.194) - L2 Border with dual port-channels
- FS2_BC1 (172.31.2.0) - Border Controller for Po40
- FS2_BC2 (172.31.2.2) - Border Controller for Po41 (**NEW**)

**New Commands:**
- `show etherchannel 41 summary` - Po41 status
- `show interfaces Port-channel41` - Po41 details
- `show lacp 41 neighbor/counters` - LACP for Po41
- `show ip route ospf | include 192.168` - ECMP verification
- `show bfd neighbors` - BFD sessions to both BCs

**Updated Expectations:**
- Po41 MUST stay UP during Po40 failure (CRITICAL)
- OSPF to BC2 MUST stay FULL
- BFD to BC2 MUST stay UP
- Minimal packet loss (<1 sec) vs. 3-10 sec single-homed
- Dead flows: 0-10 vs. 50-200+ single-homed
- TACACS accessible via Po41 (no local admin needed)

---

### 2. `README.md` (Comprehensive Documentation)
- **Size:** ~18 KB
- **Purpose:** Complete retest documentation with comparison analysis
- **Sections:**
  - Why This Retest? (topology change explanation)
  - Key Differences from Original Test (detailed comparison table)
  - Script Changes (enhanced device collection)
  - New Commands Added (dual port-channel monitoring)
  - Updated Expectations (phase-by-phase breakdown)
  - Prerequisites (network topology verification)
  - Quick Start (execution commands)
  - Expected Results Checklist (pass/fail criteria)
  - Evidence Collection (9 CLI files per iteration)
  - Success Criteria (dual-homing validation)
  - Troubleshooting (specific to dual-homed scenarios)
  - Comparison Analysis (metrics table)
  - Deliverables (report structure)
  - Related Documentation (links to Po41 implementation)

**Key Comparison Table:**

| Aspect | Original (Single-Homed) | Retest (Dual-Homed) |
|--------|-------------------------|---------------------|
| Topology | Po40 only | Po40 + Po41 (ECMP) |
| Po40 Failure Impact | Total loss | Po41 continues traffic |
| Convergence Time | ~2 minutes | Sub-second |
| Packet Loss | 3-10 seconds | <1 second or hitless |
| Dead Flows | 50-200+ | Minimal or ZERO |
| OSPF During Failure | All DOWN | BC2 remains FULL |
| BFD During Failure | All DOWN | BC2 remains UP |
| TACACS Access | Local admin required | TACACS works via Po41 |
| Expected Improvement | Baseline | ~120x faster |

---

### 3. `00_START_HERE.txt` (Quick Start Guide)
- **Size:** ~10 KB
- **Purpose:** Quick reference for test execution
- **Sections:**
  - What's in this folder
  - Why this retest? (topology change summary)
  - Expected behavior (dual-homed)
  - Quick start (3-step process with pre-validation)
  - Comparison table (single vs. dual homed)
  - Test phases breakdown
  - Critical differences from original test
  - Success criteria (dual-homing specific)
  - Evidence collection (9 CLI files per iteration)
  - Troubleshooting
  - Rollback procedures
  - Expected convergence times
  - Final deliverables
  - Related documents

**Pre-Validation Step:**
Before running retest, verify dual-homing:
```bash
ssh admin1@172.31.0.194
show etherchannel summary        # Both Po40 and Po41 UP?
show ip ospf neighbor            # Both BC1 and BC2 FULL?
show ip route ospf | include 192.168.20.0  # ECMP visible?
```

---

### 4. `RETEST_SUMMARY.md` (This File)
- **Purpose:** Summary of all files created and changes made
- **Sections:**
  - Files created
  - Key script changes
  - Execution differences
  - Evidence changes
  - Next steps

---

## Key Script Changes Summary

### Device Configuration
```python
# ADDED: BC2 device configuration
BC2 = {
    'device_type': 'cisco_ios',
    'host': '172.31.2.2',
    'username': 'admin1',
    'password': 'CXlabs.123',
    'timeout': 30,
    'name': 'FS2_BC2',
}

# ADDED: BC2 alternate credentials (Memory #24)
BC2_ALT = {
    'device_type': 'cisco_ios',
    'host': '172.31.2.2',
    'username': 'dnac_admin_tacacs',
    'password': 'CXlabs.123',
    'timeout': 30,
    'name': 'FS2_BC2',
}
```

### Collection Function Enhancement
```python
def connect(device_info, try_alt=None):
    """Connect with automatic fallback to alternate credentials"""
    # Tries primary credentials first
    # Auto-retries with try_alt if connection fails
    # Handles BC2 credential rejection gracefully
```

### Phase 1 (Baseline) - ADDED BC2 Collection
```python
# NEW: Step 1.5 - BC2 CLI Baseline
- Full CLI collection from FS2_BC2
- Po41 status verification
- OSPF/BFD to L2H-1 verification
- Output: Iter{n}_Pre_BC2_Baseline.txt
```

### Phase 2 (Failure) - ADDED BC2 Monitoring
```python
# NEW: Step 2.6 - BC2 During-Failure Status
- CRITICAL: Verify Po41 stays UP
- CRITICAL: Verify OSPF to L2H-1 stays FULL
- CRITICAL: Verify BFD to L2H-1 stays UP
- Output: Iter{n}_During_BC2_Status.txt
```

### Phase 3 (Recovery) - ADDED BC2 Validation
```python
# NEW: Step 3.8 - BC2 Full Post-Recovery Validation
- Verify Po41 continued operation
- Verify OSPF/BFD remained stable
- Confirm ECMP load-balancing
- Output: Iter{n}_Post_BC2_Validation.txt
```

---

## Execution Differences

### Original Test (Single-Homed)
```bash
# 2 devices: L2H-1, BC1
# 6 CLI files per iteration
# ~2 minute outage expected
# Local admin required during failure
python3 ../run_tc_07-02.py --iter 1
```

### Retest (Dual-Homed)
```bash
# 3 devices: L2H-1, BC1, BC2
# 9 CLI files per iteration
# Sub-second convergence expected
# TACACS accessible throughout
python3 run_tc_07-02_retest.py --iter 1
```

---

## Evidence Changes

### Original Test Evidence (Per Iteration)
- **CLI Files:** 6 (L2H-1 × 3, BC1 × 3)
- **Screenshots:** 8
- **Spirent:** 3 files
- **Total:** 17 files per iteration

### Retest Evidence (Per Iteration)
- **CLI Files:** 9 (L2H-1 × 3, BC1 × 3, BC2 × 3)
- **Screenshots:** 8
- **Spirent:** 3 files
- **Total:** 20 files per iteration

### Total Evidence Comparison
- **Original (3 iterations):** 51 files
- **Retest (3 iterations):** 60 files
- **Increase:** +9 files (BC2 collection)

---

## Critical Validation Points (Dual-Homed)

### During Po40 Failure (Phase 2)
These MUST all pass for dual-homing to be considered successful:

1. **Po41 Status:** MUST stay UP ✓
2. **OSPF to BC2:** MUST stay FULL ✓
3. **BFD to BC2:** MUST stay UP ✓
4. **TACACS Access:** MUST remain accessible via Po41 ✓
5. **Packet Loss:** < 1 second or HITLESS ✓
6. **Dead Flows:** Minimal (0-10) not 50-200+ ✓
7. **Convergence Time:** Sub-second not ~2 minutes ✓

If ANY of these FAIL → Dual-homing is NOT working, ABORT test

---

## Expected Improvement Metrics

### Convergence Time
- **Original:** ~2 minutes (LACP ~13s, OSPF ~10s, LISP ~80s)
- **Retest:** Sub-second (Po41 already converged)
- **Improvement:** ~120x faster

### Packet Loss Duration
- **Original:** 3-10 seconds
- **Retest:** <1 second or hitless
- **Improvement:** ~5-10x reduction

### Dead Flows
- **Original:** 50-200+
- **Retest:** 0-10
- **Improvement:** ~95%+ reduction

### Traffic Availability
- **Original:** 0% during ~2 minute outage
- **Retest:** 99%+ (brief or no interruption)
- **Improvement:** Near-continuous availability

---

## Next Steps

### 1. Pre-Test Validation (5 minutes)
Verify dual-homing before starting:
```bash
ssh admin1@172.31.0.194  # FS2_L2H-1

# Check both port-channels UP
show etherchannel summary

# Check OSPF to both BCs
show ip ospf neighbor
  → 192.168.40.1 (BC1) - FULL
  → 192.168.41.1 (BC2) - FULL

# Check ECMP routing
show ip route ospf | include 192.168.20.0
  → Should show [110/105] via both Po40 and Po41

# Check BFD to both BCs
show bfd neighbors
  → Both sessions UP
```

### 2. Execute Retest (75-120 minutes)
```bash
cd "/Users/wbenbark/MS_SVS_SDA_Phase2/Test Case Logs/07-02_Link_Failure_From_L2_Border_PortChannel_to_Fabric_BC_Node/retest"

python3 run_tc_07-02_retest.py --iter 1
python3 run_tc_07-02_retest.py --iter 2
python3 run_tc_07-02_retest.py --iter 3
```

### 3. Comparative Analysis (30-60 minutes)
After completing all 3 iterations:
- Compare retest convergence times vs. original
- Calculate improvement percentages
- Analyze dead flows reduction
- Document ECMP behavior

### 4. Final Report (1-2 hours)
Create Word document with:
- Executive Summary: Single-homed vs. Dual-homed comparison
- Before/After topology diagrams
- Side-by-side results tables
- All CLI evidence embedded
- All screenshots embedded
- PLA convergence data comparison
- Conclusion: Quantified improvement (~120x faster)

---

## Success Indicators

### You'll know the retest is successful if:
1. ✅ Po41 stayed UP during entire Po40 failure
2. ✅ OSPF to BC2 stayed FULL during entire failure
3. ✅ BFD to BC2 stayed UP during entire failure
4. ✅ Packet loss < 1 second (vs. 3-10 sec original)
5. ✅ Dead flows < 10 (vs. 50-200+ original)
6. ✅ Convergence sub-second (vs. ~2 min original)
7. ✅ TACACS accessible throughout (vs. local admin required)
8. ✅ ECMP resumes after recovery (dual-path load-balancing)
9. ✅ Results consistent across 3 iterations (±20%)
10. ✅ Clear improvement vs. original single-homed test

---

## Folder Structure

```
07-02_Link_Failure_From_L2_Border_PortChannel_to_Fabric_BC_Node/
├── retest/                                    ← NEW FOLDER
│   ├── 00_START_HERE.txt                      ← Quick start guide
│   ├── README.md                              ← Comprehensive docs
│   ├── RETEST_SUMMARY.md                      ← This file
│   ├── run_tc_07-02_retest.py                 ← Updated script (executable)
│   └── [After execution:]
│       ├── Iter1_CLI/ (9 files)
│       ├── Iter2_CLI/ (9 files)
│       └── Iter3_CLI/ (9 files)
│
├── Po41_Implementation_20260407_115546/       ← Po41 deployment evidence
├── DUAL_HOMING_ENHANCEMENT_Po41_Implementation.md
├── run_tc_07-02.py                            ← Original script (single-homed)
├── Iter1_CLI/, Iter2_CLI/, Iter3_CLI/         ← Original test results
├── TC-07-02_Complete_Port_Channel_Failure_Report_20260407.docx
└── [Other original test files...]
```

---

## Related Documentation

### Po41 Implementation (April 7, 2026)
- `../Po41_Implementation_20260407_115546/IMPLEMENTATION_SUMMARY.md`
- `../DUAL_HOMING_ENHANCEMENT_Po41_Implementation.md`
- Evidence: Po41 UP, OSPF FULL, BFD UP, ECMP active

### Original Test Results (Single-Homed)
- `../TC-07-02_Complete_Port_Channel_Failure_Report_20260407.docx`
- `../Iter1_CLI/`, `../Iter2_CLI/`, `../Iter3_CLI/`
- Results: ~2 min outage, 50-200+ dead flows

### Test Case Documentation
- `./README.md` - This retest documentation
- `../TC-07-02_CXTM.txt` - Original test case
- `../README.md` - Original test documentation

---

## Contact & Support

**Test Case:** TC 07-02 (SDA Master Tracker)  
**Related Test:** TC 07-01 (Single member failure - hitless)  
**Project:** Morgan Stanley SDA Phase 2 - SVS Testbed  
**Lab Location:** US RTP S10-360, Row P, Racks 18-25

**For Issues:**
- Po41 implementation: Review `DUAL_HOMING_ENHANCEMENT_Po41_Implementation.md`
- Script errors: Check `00_START_HERE.txt` troubleshooting section
- Lab access: Verify VPN and device reachability
- Spirent PLA: http://spirent-pla.cisco.com

---

**Document Version:** 1.0  
**Created:** April 7, 2026  
**Author:** Claude Code (Anthropic)  
**Status:** READY FOR EXECUTION

---

## Retest Ready Checklist

Before executing retest, confirm:
- [ ] Po41 implementation completed (✅ completed 11:56 AM today)
- [ ] Po41 operational (LACP UP, OSPF FULL, BFD UP)
- [ ] ECMP active (routes via both Po40 and Po41)
- [ ] BC2 accessible (SSH via admin1 or dnac_admin_tacacs)
- [ ] Spirent traffic profile ready (same as original test)
- [ ] VPN connected to SVS lab
- [ ] Python netmiko installed (`pip install netmiko`)
- [ ] Original test results available for comparison
- [ ] Time allocated: 75-120 minutes (3 iterations)

**All checks passed? Execute:**
```bash
cd "/Users/wbenbark/MS_SVS_SDA_Phase2/Test Case Logs/07-02_Link_Failure_From_L2_Border_PortChannel_to_Fabric_BC_Node/retest"
python3 run_tc_07-02_retest.py --iter 1
```

**Good luck with your retest! Expected outcome: ~120x improvement over single-homed topology.** 🚀
