# PSM Technical Round — Dataset Interpretation & Executive Insights

## Sample Data 1 — Interpretation

**What it tracks:** An MLS **data-feed onboarding / activation pipeline** for a real-estate technology platform.

Each row is a broker feed request against a specific MLS. Column B identifies the MLS. Columns Q–X are **semi-sequential workflow stage timestamps**:

`New → Ready for Compliance → Pending CWS / Pending Broker / Pending MLS → Pending Compliance Mod → Approved–Provisioning → Approved–Complete`

Supporting fields include feed status, agreement channel (Digital Signature via eSign/Trestle/Spark/MLS Grid, broker-initiated, CWS request, automatic), feed access level (IDX / Back Office / VOW), DLM owner, state, display URL / rules / logo / disclaimer, and last-updated metadata.

Brokerage/broker identity is anonymized (`TESTBROKERAGE` / `TESTBROKER`).

**Scale:** 403 requests across 201 unique MLSs (almost always requested as IDX + Back Office pairs).

### Executive insights (Sample 1)

1. **67.7% complete**, **6.7% cancelled**, **102 still in-flight** — solid throughput, but a meaningful open backlog.
2. **Median end-to-end cycle time is 98 days** (New → Approved Complete).
3. **Compliance intake is the biggest time sink** (~58 median days from New → Ready for Compliance).
4. **Broker approval is the live bottleneck** (~14d Pending Broker → Provisioning vs ~3d from Pending MLS); 33 broker-pending + 31 MLS-pending dominate the queue.
5. **Back Office underperforms IDX** (55% vs 80% completion) despite being requested as a twin for nearly every MLS.
6. **Digital Signature (MLS Grid / Trestle)** channels show the highest completion rates (~84–87%).

---

## Sample Data 2 — Interpretation

**What it tracks:** An **MLS feed implementation inventory** — how each MLS data-feed asset was contracted/implemented and how long it stayed open.

Fields: Asset Name (MLS), Feed Type / Data Feed Implementation (Hard Copy, Electronic Trestle, Electronic Grid, CWS Initiated, Member Initiated ± Portal), Feed Product (IDX / Back Office / VOW), and Days Opened (Average).

**Scale:** 565 assets across 325 unique MLSs; overall median days open = 17.

### Executive insights (Sample 2)

1. **Electronic Trestle/Grid are fastest** (median ~12–13 days open) vs Hard Copy (~22) and Member Initiated (~26–38).
2. **Back Office stays open longer** (median 26d) than IDX (13d) — same pattern as Sample 1.
3. **Hard Copy remains ~29% of assets** — clear modernization opportunity.
4. IDX dominates volume (348), then Back Office (154), then VOW (63).

---

## How the Datasets Relate

| Dimension | Sample 1 | Sample 2 |
|-----------|----------|----------|
| Grain | Broker feed *request* / ticket | MLS feed *asset* / implementation |
| Question answered | How does an activation move through approvals? | How was the MLS feed set up, and how long did setup take? |
| Time metric | Stage timestamps (Q–X) | Days opened (average) |
| Join key | MLS name | Asset Name (MLS) |

~140 MLS names overlap. Sample 1 requests run **on top of** Sample 2’s MLS feed infrastructure. Agreement channels and product types (IDX/BO/VOW) align across both. Signals reinforce: electronic methods outperform; Back Office is harder than IDX.

---

## Recommended Actions

1. **Compress compliance intake** — attack the 58-day New→Ready gap with standardized packets and auto-validation.
2. **Clear the broker-approval queue** — SLAs, reminders, self-serve approval paths.
3. **Treat Back Office as its own workstream** — do not manage it as an IDX twin.
4. **Migrate Hard Copy MLS assets to Trestle/Grid** — reduce upstream implementation friction.
