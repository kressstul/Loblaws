# PSM Technical Round — MLS Feed Operations Analysis

Executive analysis of two sample datasets covering MLS data-feed onboarding and implementation.

## Deliverables

| Path | Description |
|------|-------------|
| [`presentation/PSM_MLS_Feed_Operations_Executive_Briefing.pptx`](presentation/PSM_MLS_Feed_Operations_Executive_Briefing.pptx) | 6-content-slide executive presentation (+ title) |
| [`presentation/FINDINGS.md`](presentation/FINDINGS.md) | Written interpretation, insights, and recommendations |
| [`charts/`](charts/) | Supporting visualizations |
| [`data/sample1_feeds.csv`](data/sample1_feeds.csv) | Reconstructed Sample Data 1 (403 feed requests) |
| [`data/sample2_assets.csv`](data/sample2_assets.csv) | Reconstructed Sample Data 2 (565 MLS feed assets) |

## Quick Verdict

- **Sample 1** tracks broker/MLS **feed activation requests** through a staged approval workflow (columns Q–X).
- **Sample 2** tracks **MLS feed implementation assets** (contracting method + days open).
- They share MLS identity and IDX/Back Office/VOW product types; Sample 1 requests run on Sample 2 infrastructure.

## Key Numbers

- Sample 1: **67.7%** Approved–Complete · **98-day** median cycle · **102** in-flight
- Sample 2: **17-day** median days-open · electronic channels ~**2×** faster than hard copy / member-initiated
- Back Office underperforms IDX in **both** datasets
