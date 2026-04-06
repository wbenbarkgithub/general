# Morgan Stanley SDA Phase 2 - Test Automation Scripts

**Project:** Morgan Stanley SDA Phase 2  
**Author:** wbenbark  
**Lab:** Cisco RTP S10-360, Row P, Racks 18-25  
**Date:** 2026

## Overview

This repository contains automated test scripts and documentation for the Morgan Stanley SDA Phase 2 project. The project involves validating Cisco Software-Defined Access (SDA) fabric deployment across multiple data center and fabric sites with focus on scalability, resiliency, and negative testing scenarios.

## Testbed Architecture

### Sites
- **Fabric Site 1 (FS1):** 2 Border Controllers, 2 Fabric Edges
- **Fabric Site 2 (FS2):** 2 Border Controllers, 6 Fabric Edges, 1 L2 Border
- **Data Site 1 (DC1/FS4):** 2 Border Controllers, 4 Nexus 9000 (EDMZ/IDMZ)
- **Data Site 2 (DC2/FS5):** 2 Border Controllers, 4 Nexus 9000 (EDMZ/IDMZ)
- **Transit:** 4 Transit Control Plane nodes
- **Legacy L2 Site:** 4 distribution/access switches

### Infrastructure
- **Catalyst Center:** 2.3.7.9-70301 (HA pair - DC1 Active, DC2 Standby)
- **ISE:** 3.2-P7 (4 physical + 14 virtual PSNs, TACACS+ device admin)
- **IOS-XE:** 17.15.4 + 4 SMUs (25 managed devices)
- **VXLAN/LISP:** 82 EIDs, 62 SGTs, 2,142 endpoints
- **TrustSec:** SGT-based segmentation with SGACL enforcement

### Key Features Validated
- SDA fabric provisioning and scale (2,500 endpoint target)
- ISE TACACS+ device administration (20 devices)
- TrustSec SGT propagation and SGACL enforcement
- Inter-DC EDMZ iBGP routing (4 VRFs)
- L2 Border handoff with legacy sites
- Multicast forwarding (TC 01-12, TC 09-05)
- IOS-XE SWIM upgrades and SMU patching
- Negative testing: link failures, node failures, convergence measurement

## Test Cases in this Repository

### TC 07-01: Link Failure from L2 Border PortChannel Member to Fabric BC Node
**Phase:** 07 - Negative Testing - Layer 2 Border  
**CXTM ID:** 1872836  
**Status:** ✅ Ready for Execution

Validates LACP Port-Channel resilience when a single member link fails between FS2_L2H-1 (L2 Border) and FS2_BC1 (Border Controller). Tests graceful LACP member removal with zero packet loss and sub-30-second recovery.

**Files:**
- `TC_07-01/run_tc_07-01.py` - Automated execution script
- `TC_07-01/TC-07-01_Execution_Plan.txt` - Manual execution guide
- `TC_07-01/TC-07-01_CXTM.txt` - Test case specification
- `TC_07-01/README.md` - Detailed documentation

[More test cases to be added...]

## Repository Structure

```
Morgan_Stanley_SDA_Phase2/
├── README.md                    # This file
├── TC_07-01/                    # Link failure testing
│   ├── README.md
│   ├── run_tc_07-01.py
│   ├── TC-07-01_Execution_Plan.txt
│   └── TC-07-01_CXTM.txt
└── [Future test cases...]
```

## Prerequisites

### Network Access
- VPN connected to lab environment (172.31.x.x reachable)
- SSH access to all testbed devices
- Catalyst Center GUI: https://172.31.229.151 (admin/CXlabs.123)
- Spirent TestCenter: 172.31.0.101

### Software Requirements
- Python 3.x
- netmiko library: `pip install netmiko`
- paramiko (dependency of netmiko)
- Git (for cloning repository)

### Device Credentials
- **IOS-XE SDA Nodes:** admin1 / CXlabs.123
- **Nexus 9000 (EDMZ/IDMZ):** admin / CXlabs.123
- **Legacy Switches:** admin / CXlabs.123
- **Catalyst Center:** admin / CXlabs.123

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/wbenbarkgithub/general.git
cd general/Morgan_Stanley_SDA_Phase2
```

### 2. Install Dependencies
```bash
pip install netmiko
```

### 3. Run a Test Case
```bash
# Example: TC 07-01
cd TC_07-01
python3 run_tc_07-01.py --iter 1
```

### 4. Follow On-Screen Prompts
Scripts include interactive prompts for:
- Spirent GUI screenshot capture
- Catalyst Center GUI screenshot capture
- Verification gate checks
- Results recording

## Test Execution Workflow

All test cases follow a consistent 3-phase workflow:

### Phase 1: Steady State Baseline
1. Verify Spirent traffic (0.000% loss - GATE)
2. Verify Catalyst Center health (≥80%)
3. Collect CLI baselines from all relevant devices
4. Validate all control plane protocols (OSPF, BGP, LISP)

### Phase 2: Failure Event
1. Introduce failure (shutdown, reload, etc.)
2. Immediate verification (within 10 seconds)
3. Monitor Spirent for convergence (typically 3 minutes)
4. Collect during-failure CLI evidence
5. Export Spirent DB if packet loss detected

### Phase 3: Recovery
1. Remove failure condition (restore config)
2. Monitor protocol convergence
3. Validate Spirent traffic restored (0.000% loss)
4. Collect post-recovery CLI evidence
5. Compare all metrics to Phase 1 baseline

### Iteration Consistency
- Run each test 3 times (Iter1, Iter2, Iter3)
- Results must be within ±20% variance
- All 3 iterations must PASS for overall PASS

## Convergence Measurement

All negative test cases use Spirent PLA (Packet Loss Analyzer) for precise convergence measurement:

- **Tool:** http://spirent-pla.cisco.com
- **Metrics:** Dead flows, flows with drops, MAX/MIN/AVG convergence time
- **Export Format:** .tcc (Spirent DB), .xlsx (PLA analysis)
- **Threshold:** ≤0.001% packet loss for PASS

## Device Access Reference

### Fabric Site 2 (Primary Test Site)
| Device | Role | IP | Platform | Credentials |
|--------|------|-----|----------|-------------|
| FS2_L2H-1 | L2 Border | 172.31.0.194 | C9404R | admin1/CXlabs.123 |
| FS2_BC1 | Border Controller | 172.31.2.0 | C9606R | admin1/CXlabs.123 |
| FS2_BC2 | Border Controller | 172.31.2.2 | C9606R | admin1/CXlabs.123 |
| FS2_FE1 | Fabric Edge | 172.31.2.10 | C9300-48UXM | admin1/CXlabs.123 |
| FS2_FE2 | Fabric Edge | 172.31.2.5 | C9407R | admin1/CXlabs.123 |
| FS2_FE3 | Fabric Edge | 172.31.2.6 | C9500-48Y4C | admin1/CXlabs.123 |
| FS2_FE4 | Fabric Edge | 172.31.2.7 | C9300X-48HX | admin1/CXlabs.123 |
| FS2_FE5 | Fabric Edge | 172.31.2.9 | C9300-48U | admin/CXlabs.123 |
| FS2_FE5-2 | Fabric Edge | 172.31.2.11 | C9300X-48HX | admin1/CXlabs.123 |
| FS2_FE6 | Fabric Edge | 172.31.2.12 | C9300-48UXM | admin1/CXlabs.123 |

### Fabric Site 1
| Device | Role | IP | Platform | Credentials |
|--------|------|-----|----------|-------------|
| FS1_BC_1 | Border Controller | 172.31.0.189 | C9600X | admin1/CXlabs.123 |
| FS1_BC_2 | Border Controller | 172.31.0.188 | C9600X | admin1/CXlabs.123 |
| FS1_FE_1 | Fabric Edge | 172.31.0.185 | C9300-48UXM | admin1/CXlabs.123 |
| FS1_FE_2 | Fabric Edge | 172.31.0.184 | C9300X-48HX | admin1/CXlabs.123 |

Complete device inventory: See `/Device_Access/ssh.morgan.stanley.svs.sda.csv`

## Known Issues

### TACACS+ Credentials
5 devices require alternate credentials due to TACACS+ user assignment:
- **FS1_BC_1, FS2_BC1, FS2_BC2, FS2_FE5-2:** Use `dnac_admin_tacacs` (not admin1)
- **FS2_FE3:** Use `admin2` (not admin1)

See: `feedback_tacacs_credentials.md` in project memory

### N9K-2 Transit Forwarding
FS2_BC1 uplinks to N9K-2 are shut (workaround for transit forwarding issue). N9K-1 is sole EDMZ path.

### FS2_BC1 Post-SWIM
TAC Case 700533184 open for dead flows after SWIM upgrade. Awaiting CSCwo79838 fix.

## Project Documentation

Full project documentation available in:
- `/Users/wbenbark/MS_SVS_SDA_Phase2/Documentation/`
- `/Users/wbenbark/MS_SVS_SDA_Phase2/Test Case Logs/`
- `/Users/wbenbark/.claude/projects/-Users-wbenbark/memory/` (Claude Code memory)

## Contributing

This is a private project repository for Morgan Stanley SDA Phase 2 testing. Updates and new test cases added by wbenbark.

## Support

For questions or issues:
- **GitHub Issues:** https://github.com/wbenbarkgithub/general/issues
- **Project Owner:** wbenbark
- **Lab Access:** Cisco RTP S10-360, Row P, Racks 18-25

## Related Repositories

- **File Transfer Scripts:** [scp-transfer-scripts](../scp-transfer-scripts/) - SFTP/SCP utilities for lab file transfers
- **Main Project Docs:** Local filesystem at `/Users/wbenbark/MS_SVS_SDA_Phase2/`

## License

Private project - Morgan Stanley SDA Phase 2 internal use.

---

**Last Updated:** April 6, 2026  
**Version:** 1.0  
**Author:** wbenbark
