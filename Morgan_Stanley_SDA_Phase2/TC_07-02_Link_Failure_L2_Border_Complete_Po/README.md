# TC 07-02: Link Failure from L2 Border Port-Channel to Fabric BC Node

## Overview

**Test Case:** Complete Port-Channel failure between L2 Border (FS2_L2H-1) and Border Controller (FS2_BC1)

**Difference from TC 07-01:**
- **TC 07-01**: Shutdown ONE member (Te4/0/1) → Po40 stays UP with reduced bandwidth (hitless)
- **TC 07-02**: Shutdown BOTH members (Te4/0/1 AND Te4/0/2) → Po40 goes DOWN (traffic loss expected)

## Test Objective

Validate SDA fabric resilience when the **ENTIRE** LACP Port-Channel bundle to a Border Controller fails. This simulates a complete link failure scenario (e.g., fiber cut, upstream switch failure, multiple port failures).

## Expected Behavior

### During Failure (Phase 2)
- ✅ Po40 goes DOWN (no bundled members)
- ✅ OSPF adjacency to BC1 goes DOWN
- ✅ LISP session to BC1 goes DOWN
- ✅ Packet loss occurs during convergence
- ✅ Dead flows detected (streams stop forwarding)
- ⏱️ Convergence time measured via Spirent PLA

### During Recovery (Phase 3)
- ✅ Both members restore (no shutdown)
- ✅ LACP rebundles (10-30 seconds typical)
- ✅ OSPF adjacency restores to FULL (15-30 seconds)
- ✅ LISP sessions reestablish (10-30 seconds)
- ✅ Traffic fully restored (0.000% loss)
- ✅ All baseline metrics restored

## Files in this Directory

### Test Documentation
- `TC-07-02_CXTM.txt` - Complete test case description
- `TC-07-02_Execution_Plan.txt` - Copy/paste execution guide
- `README.md` - This file

### Automation
- `run_tc_07-02.py` - Python automation script (requires netmiko)

### Evidence Collection (After Execution)
```
Iter1_CLI/
  ├── Iter1_Pre_L2H1_Baseline.txt
  ├── Iter1_Pre_BC1_Baseline.txt
  ├── Iter1_During_L2H1_Failure.txt
  ├── Iter1_During_BC1_Status.txt
  ├── Iter1_Post_L2H1_Validation.txt
  └── Iter1_Post_BC1_Validation.txt

Iter1_Images/
  ├── Iter1_Pre_Spirent_Baseline.png
  ├── Iter1_Pre_CC_L2H1_Health.png
  ├── Iter1_Pre_CC_Network_Health.png
  ├── Iter1_During_Spirent_Convergence.png
  ├── Iter1_During_CC_L2H1_Status.png
  ├── Iter1_Post_Spirent_Restored.png
  ├── Iter1_Post_CC_L2H1_Health.png
  └── Iter1_Post_CC_Network_Health.png

Spirent_DB/
  ├── Iter1_During_Spirent_DB.tcc
  ├── Iter1_PLA_Convergence_Analysis.xlsx
  └── Iter1_PLA_Analysis.png
```

## Prerequisites

### Software
- Python 3.6+ with netmiko installed:
  ```bash
  pip install netmiko
  ```

### Lab Access
- VPN connected to MS SDA Phase 2 testbed
- SSH access to devices:
  - FS2_L2H-1: 172.31.0.194 (admin1/CXlabs.123)
  - FS2_BC1: 172.31.2.0 (admin1/CXlabs.123)
- Spirent GUI access: 172.31.0.101
- Catalyst Center: https://172.31.229.151 (admin/CXlabs.123)
- Spirent PLA account: http://spirent-pla.cisco.com

### Baseline Requirements (GATE)
- Spirent: 0.000% packet loss, 0 dead streams
- CC: FS2_L2H_1 health >= 80%, Reachable
- L2H-1: Po40 UP, both members bundled (P state)
- L2H-1: 2 LISP sessions UP, OSPF FULL to BC1
- BC1: Po40 UP, both members bundled

## Usage

### Option 1: Automated Execution (Recommended)

```bash
# Navigate to test directory
cd "/Users/wbenbark/MS_SVS_SDA_Phase2/Test Case Logs/07-02_Link_Failure_From_L2_Border_PortChannel_to_Fabric_BC_Node"

# Run Iteration 1
python3 run_tc_07-02.py --iter 1

# Run Iteration 2
python3 run_tc_07-02.py --iter 2

# Run Iteration 3
python3 run_tc_07-02.py --iter 3
```

The script will:
- Pause at each step for GUI screenshots
- Automatically collect CLI outputs
- Save evidence to `Iter{n}_CLI/` directories
- Provide clear instructions for Spirent PLA analysis

### Option 2: Manual Execution

Use `TC-07-02_Execution_Plan.txt` as a copy/paste guide. This is useful if:
- Automation script fails
- You need more control over timing
- You want to manually troubleshoot issues

## Critical Steps

### 1. Spirent Convergence Analysis (MANDATORY)

Unlike TC 07-01 (hitless), TC 07-02 **WILL** cause packet loss. You MUST:

1. **Stop traffic** after 3 minutes of monitoring
2. **Export Spirent DB** to .tcc file
3. **Upload to PLA**: http://spirent-pla.cisco.com
4. **Download Excel report** with convergence data
5. **Screenshot PLA results**

The PLA analysis provides:
- Total frames lost
- Dead flows count
- Flows with drops count
- MAX/MIN/AVG convergence times per stream

### 2. OSPF Convergence Monitoring

Po40 going DOWN causes OSPF adjacency to tear down. Monitor:
- OSPF neighbor state transitions
- SPF recalculation logs
- Convergence time to FULL state

### 3. LISP Session Monitoring

LISP TCP sessions to BC1 will drop. Monitor:
- Session state changes (Up → Down → Up)
- Session reestablishment time
- Map-cache entries remain valid

## Expected Results

### Convergence Times (Typical)

| Metric | Expected Range | Notes |
|--------|---------------|-------|
| Po40 Down Detection | Immediate | LACP detects no bundled members |
| OSPF Adjacency Down | 1-10s | Dead timer or BFD |
| Packet Loss Duration | 3-10s | Until alternate path or recovery |
| Dead Flows | 50-200 | Depends on traffic patterns |
| LACP Rebundle Time | 10-30s | After no shutdown |
| OSPF Convergence | 15-30s | To FULL state |
| LISP Session Restore | 10-30s | TCP 3-way handshake |
| Total Recovery Time | 30-60s | All protocols reconverged |

### Pass Criteria

**PASS if:**
- Po40 goes DOWN when both members shut (EXPECTED)
- OSPF adjacency goes DOWN (EXPECTED)
- Convergence measured and documented
- Po40 restores after no shutdown
- OSPF restores to FULL
- LISP sessions reestablish
- Post-recovery: 0.000% loss
- All metrics restored to baseline
- Results consistent across 3 iterations (+/- 20%)

**FAIL if:**
- Po40 stays UP after shutting both members (UNEXPECTED)
- Po40 fails to restore after no shutdown
- LACP rebundle fails
- OSPF fails to converge
- LISP sessions fail to reestablish
- Permanent dead flows after recovery
- Metrics do not restore to baseline

## Comparison: TC 07-01 vs TC 07-02

| Aspect | TC 07-01 (Single Member) | TC 07-02 (Entire Po) |
|--------|--------------------------|----------------------|
| **Failure** | Shutdown Te4/0/1 only | Shutdown Te4/0/1 AND Te4/0/2 |
| **Po40 Status** | Stays UP (reduced BW) | Goes DOWN (no members) |
| **OSPF Adjacency** | Stays FULL (no change) | Goes DOWN (expected) |
| **LISP Sessions** | Remain UP (no change) | Go DOWN (expected) |
| **Packet Loss** | 0.000% (hitless) | Expected (3-10s typical) |
| **Dead Flows** | 0 (expected) | Expected (50-200) |
| **Convergence** | None (Po stays up) | Required (failover/recovery) |
| **PLA Analysis** | Optional (verify 0%) | **MANDATORY** (measure times) |
| **Severity** | Low (graceful degr.) | High (complete failure) |
| **Recovery** | Rebundle one member | Rebundle both + OSPF + LISP |

## Troubleshooting

### Po40 Fails to Rebundle After Recovery

```bash
# On L2H-1
show etherchannel 40 summary
show lacp 40 counters
show lacp 40 neighbor

# Check physical interfaces
show interfaces Te4/0/1
show interfaces Te4/0/2

# On BC1
show etherchannel 40 summary
show lacp 40 counters
```

Common causes:
- Physical link still down (check optics)
- LACP mismatch (mode/timer)
- Configuration error

### OSPF Fails to Converge

```bash
# Check OSPF neighbor state
show ip ospf neighbor detail

# Check OSPF interface
show ip ospf interface Port-channel40

# Check for authentication mismatch
show logging | include OSPF
```

### LISP Sessions Fail to Reestablish

```bash
# Check LISP sessions
show lisp session
show lisp session verbose

# Check IP reachability to BC1/BC2
ping 192.168.100.1 source loopback0
ping 192.168.100.2 source loopback0

# Check routing
show ip route 192.168.100.1
```

### Spirent Traffic Doesn't Restore

- Wait full 60 seconds after OSPF/LISP converge
- Check routing: `show ip route summary`
- Check CTS: `show cts role-based counters` (look for denies)
- Verify VXLAN: `show lisp instance-id * ethernet server`

## Rollback

If test must be aborted at any point:

```bash
# On FS2_L2H-1
conf t
interface range TenGigabitEthernet4/0/1 - 2
no shutdown
end

# Wait 30 seconds
show etherchannel 40 summary
# Verify: Po40 UP with both members

# Wait for OSPF
show ip ospf neighbor
# Verify: FULL to BC1

# Wait for LISP
show lisp session
# Verify: Both sessions UP
```

## Deliverables

After completing all 3 iterations:

### CLI Evidence
- 6 files per iteration × 3 iterations = 18 CLI files
- Pre/During/Post for both L2H-1 and BC1

### Screenshots
- 8 screenshots per iteration × 3 = 24 screenshots
- Phase 1: Baseline (3)
- Phase 2: Convergence (2)
- Phase 3: Recovery (3)

### Spirent Analysis
- 3 .tcc files (one per iteration)
- 3 PLA Excel reports
- 3 PLA screenshots

### Final Report
- Word document with all evidence embedded
- Convergence summary Excel (3 iterations comparison)
- CXTM results file

## Support

- Lab Issues: Contact SVS lab support
- Test Questions: Refer to CXTM and Execution Plan
- Cisco TAC: Only if defects found (record case number)

## Related Test Cases

- **TC 07-01**: Single Po member failure (hitless)
- **TC 07-03**: TBD - Border Controller complete failure
- **TC 07-04**: TBD - L2 Border complete failure (both uplinks)

## Notes

This test validates the **worst-case scenario** for L2 Border uplink failure - complete loss of connectivity to one Border Controller. In production, this would simulate:
- Fiber bundle cut (both strands)
- Upstream switch complete failure
- Power loss to switch
- Multiple simultaneous port failures

The test confirms that traffic can reconverge after catastrophic link failure and that all protocols (LACP, OSPF, LISP) properly detect and recover from the failure.

**IMPORTANT**: This test WILL cause traffic loss. Coordinate with stakeholders before running in production-like environments.
