# TC 07-03: Link Failure from L2 Border Physical Link to Other BC Node

**Test Type:** Negative Test Case - Link Failure Validation  
**Topology:** Dual-Homed L2 Border with Redundant Port-Channels (Po40 + Po41)  
**Failure Target:** Po41 (to FS2_BC2) - Mirror test of TC 07-02  
**Expected Behavior:** HITLESS or NEAR-HITLESS failover via Po40 redundancy  
**Script Version:** v2.0 — 5-device collection with multicast verification (872 lines)  

---

## Overview

TC 07-03 is the **mirror test** of TC 07-02 Retest, validating that dual-homing redundancy works **bidirectionally**:

| Test Case | Failed Path | Redundant Path | Purpose |
|-----------|-------------|----------------|---------|
| **TC 07-02 Retest** | Po40 (to BC1) | Po41 (to BC2) | Validates BC2 redundancy |
| **TC 07-03** | Po41 (to BC2) | Po40 (to BC1) | Validates BC1 redundancy |

By running both tests, we prove that either path can independently sustain full traffic when the other fails, demonstrating true bidirectional resilience.

### Test Evolution

```
Original TC 07-02 (Single-Homed):
  FS2_L2H-1 --Po40--> FS2_BC1 ONLY
  Po40 failure → ~2 minute outage, significant packet loss

TC 07-02 Retest (Dual-Homed):
  FS2_L2H-1 --Po40--> FS2_BC1  [SHUT DOWN]
  FS2_L2H-1 --Po41--> FS2_BC2  [REDUNDANT PATH]
  Po40 failure → <1 second convergence, minimal loss

TC 07-03 (This Test - Dual-Homed Mirror):
  FS2_L2H-1 --Po40--> FS2_BC1  [REDUNDANT PATH]
  FS2_L2H-1 --Po41--> FS2_BC2  [SHUT DOWN]
  Po41 failure → <1 second convergence, minimal loss
```

---

## Topology

```
                   ┌────────────────────────────┐
                   │   Catalyst Center (CC)     │
                   │     172.31.0.197           │
                   └────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
    ┌─────────▼────────┐          ┌──────────▼────────┐
    │   FS2_BC1        │          │   FS2_BC2         │
    │   C9606R         │          │   C9606R          │
    │   172.31.2.0     │          │   172.31.2.2      │
    │   Border Control │          │   Border Control  │
    └────────┬─────────┘          └─────────┬─────────┘
             │ Po40                          │ Po41
             │ Te2/0/1-2                     │ Te3/0/1-2
             │ 192.168.40.0/31    [TARGET]  │ 192.168.41.0/31
             │ [STAYS UP]                    │ [WILL BE SHUT]
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
              │ Te4/0/20            Te4/0/21│
              │                              │
    ┌─────────▼────────┐          ┌─────────▼────────┐
    │  L2-DIST-1       │          │  L2-DIST-2       │
    │  C9404R          │          │  C9404R          │
    │  172.31.0.193    │          │  172.31.0.180    │
    └────────┬─────────┘          └────────┬─────────┘
             │                              │
    ┌────────▼─────────┐          ┌────────▼─────────┐
    │ FS2_L2_9300-1    │          │ FS2_L2_9300-2    │
    │ C9300-48S        │          │ C9300-48U        │
    │ 172.31.0.179     │          │ 172.31.0.178     │
    │ Legacy Access    │          │ Legacy Access    │
    └──────────────────┘          └──────────────────┘
```

> **v2.0 Enhancement:** Script now also collects from FS2_L2_9300-1 and FS2_L2_9300-2 (legacy access switches behind the distribution tier) to capture STP topology changes and IGMP snooping state during the fabric-side failure event.

### Addressing

| Device | Interface | IP Address | Peer |
|--------|-----------|------------|------|
| FS2_L2H-1 | Po40 | 192.168.40.1/31 | FS2_BC1 |
| FS2_BC1 | Po40 | 192.168.40.0/31 | FS2_L2H-1 |
| FS2_L2H-1 | Po41 | 192.168.41.1/31 | FS2_BC2 |
| FS2_BC2 | Po41 | 192.168.41.0/31 | FS2_L2H-1 |

### VLANs Tested

- **VLAN 101** (BMS): SGT 2001
- **VLAN 102** (Critical): SGT 5002
- **VLAN 103** (EUT): SGT 5001

---

## Test Scenario

### Phase 1: Steady State Baseline

**Both paths operational (ECMP):**
- Po40 (to BC1): UP, carrying traffic
- Po41 (to BC2): UP, carrying traffic
- OSPF: 2 neighbors (BC1 + BC2) in FULL state
- LISP: 2 sessions UP
- Routes: ECMP via both 192.168.40.0 (BC1) and 192.168.41.0 (BC2)
- Spirent: 400+ streams alive, 0% loss

### Phase 2: Failure Event - Shutdown Po41

**Command:** `interface Port-channel41` → `shutdown`

**Expected Convergence Behavior:**
1. Po41 goes protocol down immediately
2. LACP detects member interface failure
3. OSPF adjacency to BC2 drops (dead interval or immediate detection)
4. LISP session to BC2 closes
5. Routing table updates: Remove BC2 path, use BC1 only
6. Traffic shifts to Po40 (BC1 path)
7. **Target convergence: <1 second**
8. **Target packet loss: <1%**

**During Failure State:**
- Po40: UP (carrying all traffic)
- Po41: Protocol Down
- OSPF: 1 neighbor (BC1 only)
- LISP: 1 session (BC1 only)
- Routes: Single path via 192.168.40.0 (BC1)
- Spirent: Should show brief dead flows, then recovery

### Phase 3: Recovery - Restore Po41

**Command:** `interface Port-channel41` → `no shutdown`

**Expected Recovery Behavior:**
1. Po41 member interfaces come up
2. LACP re-negotiates bundle
3. OSPF adjacency to BC2 re-establishes (~10-30 seconds)
4. LISP session to BC2 re-registers
5. ECMP restored: Routes via both BC1 and BC2
6. Traffic balanced across both paths
7. Spirent: All streams return to baseline (100% alive)

---

## Prerequisites

### Hardware Requirements

- **FS2_L2H-1** (172.31.0.194) - Catalyst 9404R - L2 Border Device
- **FS2_BC1** (172.31.2.0) - Catalyst 9606R - Border Controller 1
- **FS2_BC2** (172.31.2.2) - Catalyst 9606R - Border Controller 2
- **FS2_L2_9300-1** (172.31.0.179) - Catalyst 9300-48S - Legacy Access (behind DIST-1)
- **FS2_L2_9300-2** (172.31.0.178) - Catalyst 9300-48U - Legacy Access (behind DIST-2)
- **Spirent STCv** (172.31.0.22:8088) - Traffic generator
- **Catalyst Center** (172.31.0.197) - SDA controller

### Software Requirements

- **IOS-XE:** 17.15.04 (or documented version)
- **Python:** 3.7+
- **Python Libraries:** `netmiko` (install via `pip3 install netmiko`)

### Topology Requirements

✅ Dual-homed topology deployed (Po40 + Po41 both operational)  
✅ OSPF neighbors: L2H-1 adjacencies to both BC1 and BC2 in FULL state  
✅ LISP sessions: L2H-1 registered with both BC1 and BC2  
✅ ECMP routing: Traffic load-balanced across both paths  
✅ VLANs 101, 102, 103 provisioned and passing traffic  

### Credentials

| Device | Primary | Fallback | Notes |
|--------|---------|----------|-------|
| FS2_L2H-1 | admin1/CXlabs.123 | admin/CXlabs.123 | Script has auto-fallback |
| FS2_BC1 | admin1/CXlabs.123 | N/A | No known issues |
| FS2_BC2 | admin1/CXlabs.123 | dnac_admin_tacacs/CXlabs.123 | May need alternate creds |
| FS2_L2_9300-1 | admin/CXlabs.123 | N/A | **LOCAL AUTH ONLY** (no TACACS) |
| FS2_L2_9300-2 | admin/CXlabs.123 | N/A | **LOCAL AUTH ONLY** (no TACACS) |

### Traffic Validation

✅ Spirent GUI accessible at http://172.31.0.22:8088  
✅ Baseline traffic: 400+ streams alive, 0% loss  
✅ Spirent PLA tool available at http://spirent-pla.cisco.com  
✅ At least one stream identified crossing L2 Border (VLAN 101 BMS preferred)  

---

## Usage

### Basic Usage

```bash
# Run single iteration
python3 run_tc_07-03.py --iter 1

# Run all three iterations (recommended for ±20% consistency validation)
python3 run_tc_07-03.py --iter 1
python3 run_tc_07-03.py --iter 2
python3 run_tc_07-03.py --iter 3
```

### Script Workflow

1. **Pre-Test Validation:**
   - Clears syslog buffers on all 5 devices for clean evidence collection
   - Connects to all 5 devices (L2H-1, BC1, BC2, L2_9300-1, L2_9300-2)
   - Handles TACACS authentication with automatic fallback to local credentials
   - Collects baseline CLI outputs (including multicast) and saves to `Iter{N}_CLI/` directory

2. **Manual Pause Points:**
   - Script pauses and asks you to take Spirent screenshots (baseline)
   - Script pauses and asks you to take Catalyst Center screenshots
   - Press ENTER when ready to continue

3. **Failure Event:**
   - Script shuts down Po41 on FS2_L2H-1
   - Script waits 5 seconds for initial convergence
   - Script collects "during failure" CLI outputs

4. **Manual Evidence Collection:**
   - Script pauses for you to capture Spirent failure screenshots
   - Take screenshots showing dead flows, convergence metrics

5. **Recovery:**
   - Script restores Po41 (no shutdown)
   - Script waits 30 seconds for OSPF/LISP convergence
   - Script collects "post recovery" CLI outputs

6. **Final Evidence:**
   - Script pauses for you to capture Spirent recovery screenshots
   - Verify all streams returned to baseline

### CLI Outputs Collected

**FS2_L2H-1 (L2 Border):**
- Port-channel status (Po40/Po41, all members Te4/0/1-4, human-readable)
- LACP neighbor/counter details
- OSPF, BFD, LISP sessions, CTS counters, route summary
- **Multicast:** PIM neighbors, RP mapping, mroute 225.1.1.1, MFIB HW counters, IGMP snooping (VRF BMS1)

**FS2_BC1 / FS2_BC2 (Border Controllers):**
- Port-channel, LACP, OSPF, BGP, LISP, BFD
- **Multicast:** mroute 225.1.1.1, PIM neighbors (VRF BMS1)

**FS2_L2_9300-1 / FS2_L2_9300-2 (Legacy Access Switches):**
- Trunk interfaces, STP VLAN 101/1301, MAC address tables
- CDP neighbors, IGMP snooping groups VLAN 101/1301
- STP topology change notifications (during/post phases)

**Saved to:**
- `Iter1_CLI/` - Iteration 1 evidence (15 files: 5 devices x 3 phases)
- `Iter2_CLI/` - Iteration 2 evidence
- `Iter3_CLI/` - Iteration 3 evidence

### Evidence Collection

**Manual screenshots required:**
1. Spirent baseline (before shutdown)
2. Catalyst Center health (before shutdown)
3. Spirent during failure (dead flows, PLA metrics)
4. Catalyst Center health during failure (may show warning)
5. Spirent post-recovery (all streams alive)
6. Catalyst Center health post-recovery (all devices healthy)

**Repeat for each iteration** (18+ screenshots total across 3 iterations)

---

## Expected Results

### Success Criteria

| Metric | Target | Pass Threshold | Original (Single-Homed) |
|--------|--------|----------------|-------------------------|
| **Convergence Time** | <1 second | <5 seconds | ~120 seconds |
| **Packet Loss** | <0.1% | <1% | Significant |
| **Dead Flows** | 0 | <10 | Many |
| **ECMP Recovery** | Yes | Yes | N/A (no ECMP) |
| **Device Stability** | No crashes | No crashes | No crashes |

### Consistency Validation

Run **3 iterations** and verify:
- All 3 iterations pass individual success criteria
- Convergence time varies by ≤20% across iterations
- Packet loss varies by ≤20% across iterations

### Comparison to TC 07-02

| Metric | TC 07-02 Retest (Po40 Fail) | TC 07-03 (Po41 Fail) | Status |
|--------|------------------------------|----------------------|--------|
| Convergence | <1 second | <1 second | Should match |
| Packet Loss | <1% | <1% | Should match |
| Improvement | >99% vs original | >99% vs original | Should match |
| Bidirectional Redundancy | ✅ BC2 redundancy proven | ✅ BC1 redundancy proven | ✅ Complete |

---

## Troubleshooting

### Common Issues

#### 1. BC2 Connection Fails (admin1 rejected)

**Symptom:** Script fails to connect to FS2_BC2 with admin1  
**Resolution:**
- Script has built-in fallback to `dnac_admin_tacacs`
- If both fail, manually edit `BC2_ALT` credentials in script
- Refer to Memory #24 for known credential issues

#### 2. Po41 Won't Shut Down (Error Message)

**Symptom:** `shutdown` command fails on Po41  
**Resolution:**
- Verify no critical services depend on Po41 exclusively
- Check CLI restrictions: `show parser command`
- Try member interface shutdown: `interface Te1/0/19` → `shutdown`

#### 3. Convergence >5 Seconds

**Symptom:** Spirent shows extended outage  
**Resolution:**
- Check OSPF timers: `show ip ospf interface Po40`
- Verify OSPF hello/dead intervals (should be 10s/40s or tuned faster)
- Check LISP timers: `show run | section lisp`
- Validate Po40 bundle operational: `show port-channel 40 summary`

#### 4. No Failover to Po40 (Traffic Still Lost)

**Symptom:** Traffic doesn't shift to BC1 when Po41 fails  
**Resolution:**
- **STOP TEST** - This is a topology issue
- Verify Po40 physical connectivity: `show interface Te1/0/17-18`
- Check OSPF adjacency to BC1: `show ip ospf neighbor`
- Verify routes via BC1 exist: `show ip route vrf * | include 192.168.40`
- Check LISP session to BC1: `show lisp session`

#### 5. ECMP Not Restored After Recovery

**Symptom:** Only one path active post-recovery  
**Resolution:**
- Wait additional 60 seconds for full OSPF convergence
- Verify both OSPF neighbors FULL: `show ip ospf neighbor`
- Check CEF load balancing: `show ip cef vrf <vrf_name>`
- Verify LISP both sessions UP: `show lisp session`
- Check Po41 bundle status: `show port-channel 41 summary` (should show P)

#### 6. Script Hangs at "Connecting to..."

**Symptom:** Script timeout during device connection  
**Resolution:**
- Verify SSH reachability: `ssh -v admin1@172.31.0.194`
- Check TACACS: `test aaa group MSTACACS admin1 CXlabs.123 new-code`
- If TACACS down, script will auto-fallback after 30 seconds
- Manually use local credentials (admin/CXlabs.123) if needed

---

## Report Generation

### Automated Report

```bash
python3 generate_report.py
```

**Generates:** `TC-07-03_Link_Failure_L2_Border_to_Other_BC_Report.docx`

**Contents:**
- Test overview and topology
- Embedded CLI outputs from all 3 iterations
- Placeholders for Spirent screenshots (manually insert)
- Convergence metrics analysis
- Comparison to TC 07-02 and original single-homed test

### Manual Report Elements

You must manually:
1. Insert Spirent screenshots into Word document
2. Add Spirent PLA metrics (dead flows, convergence time)
3. Add Catalyst Center health screenshots
4. Update results summary with final PASS/FAIL determination
5. Archive CLI evidence: `zip -r TC_07-03_CLI_Output.zip Iter*_CLI/`

---

## Test Case Mapping

### Related Test Cases

| Test ID | Description | Relationship |
|---------|-------------|--------------|
| **TC 07-01** | Link Failure L2 Border Po Member | Single member link failure (Phase 05) |
| **TC 07-02** | Link Failure L2 Border Complete Po | Original single-homed test (baseline) |
| **TC 07-02 Retest** | Dual-Homed Po40 Failure | Mirror of TC 07-03 (Po40 shutdown) |
| **TC 07-03** | Dual-Homed Po41 Failure | This test (Po41 shutdown) |
| **TC 07-04** | [If applicable] | Additional L2 Border failure scenarios |

### Test Sequence Recommendation

1. Run **TC 07-02 Retest** first (shutdown Po40, validate Po41 redundancy)
2. Run **TC 07-03** second (shutdown Po41, validate Po40 redundancy)
3. Compare results to confirm bidirectional redundancy

---

## Files in This Directory

| File | Purpose | Size |
|------|---------|------|
| `run_tc_07-03.py` | Main automation script (v2.0 — 5-device, multicast) | 872 lines |
| `generate_report.py` | Word report generator | 47 KB |
| `00_START_HERE.txt` | Quick start guide | 7 KB |
| `README.md` | Comprehensive documentation | This file |
| `TC-07-03_CXTM.txt` | Test case specification | 23 KB |
| `TC-07-03_CXTM_Results.txt` | Actual test results | 11 KB |
| `TC-07-03_Execution_Plan.txt` | Step-by-step execution guide | 20 KB |

---

## Key Insights

### Why Run Both TC 07-02 and TC 07-03?

**Bidirectional Redundancy Validation:**
- TC 07-02 proves BC2 can sustain traffic when BC1 path fails
- TC 07-03 proves BC1 can sustain traffic when BC2 path fails
- Together, they prove **either Border Controller can independently handle full load**

**Real-World Scenarios:**
- BC1 maintenance → Traffic flows through BC2
- BC2 failure → Traffic flows through BC1
- Fiber cut to either BC → No customer impact

### Convergence Comparison

```
Original Single-Homed Test (TC 07-02):
  FS2_L2H-1 --Po40--> FS2_BC1 [ONLY PATH]
  Po40 failure → NO REDUNDANCY → ~120 second outage

Dual-Homed Tests (TC 07-02 Retest + TC 07-03):
  FS2_L2H-1 --Po40--> FS2_BC1 [Path A]
  FS2_L2H-1 --Po41--> FS2_BC2 [Path B]
  Either path failure → REDUNDANT PATH AVAILABLE → <1 second outage

Improvement: 99.2% reduction in convergence time (120s → <1s)
```

---

## Support

### Documentation References

- **Design Document:** `DUAL_HOMING_ENHANCEMENT_Po41_Implementation.md` (in Po41 provisioning folder)
- **CXTM Format:** `TC-07-03_CXTM.txt`
- **Memory References:**
  - Memory #11c: GitHub Provisioning Scripts (Po41 implementation)
  - Memory #17: Negative Test Cases Framework (convergence measurement)
  - Memory #24: TACACS credential issues (FS2_BC2 workaround)

### GitHub Repository

https://github.com/wbenbarkgithub/general/tree/main/Morgan_Stanley_SDA_Phase2/TC_07-03_Link_Failure_L2_Border_to_Other_BC

---

## License

Internal Morgan Stanley SDA Phase 2 testbed validation. Not for external distribution.

---

**Last Updated:** April 9, 2026  
**Tested By:** SVS Lab Team  
**Test Status:** ✅ PASS (3 iterations completed, <1s convergence, <1% loss)

### Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | April 7, 2026 | Initial release — 3-device collection (L2H-1, BC1, BC2) |
| v2.0 | April 9, 2026 | Added FS2_L2_9300-1/9300-2 legacy access switch collection, multicast verification (PIM/MFIB/IGMP snooping) on all devices, log clearing on all 5 devices, expanded checklist with multicast items |
