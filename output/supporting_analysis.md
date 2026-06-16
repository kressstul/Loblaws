# Supporting analysis - Loblaw Discount Division case

## Assumptions

- The division-level view uses the workbook row `TOTAL DISCOUNT DIVISION (NATIONAL)` to avoid double-counting banner rows.
- Regional share maps discount banners to the closest regional industry market: Maxi to Quebec, No Frills Atlantic to Atlantic, No Frills and RCSS Ontario to Ontario, and No Frills and RCSS West to West.
- The SQL task's third-week logic groups by the month embedded in `Period`, matching the prompt's example that April's third week is `WE Apr 18 20`.
- Data is fictitious per the case prompt; recommendations are directional and intended for a 15-minute discussion.

## Key outputs

- Discount Division sales were $25.4B in 2020, up 6.8%, versus industry growth of 11.0%.
- National share declined from 18.0% to 17.3%, a -0.7 pts change.
- Promo penetration was 35.2%, matching the national industry but down from 36.1% in 2019.
- E-commerce sales grew 207% to 4.6% of sales, still below industry penetration of 5.0%.

## Regional scorecard

| Region | 2020 sales | YoY growth | 2020 share | Share change |
| --- | ---: | ---: | ---: | ---: |
| Atlantic | $0.4B | 38.4% | 4.6% | +1.0 pts |
| Quebec | $3.3B | 6.6% | 15.5% | -0.6 pts |
| Ontario | $7.7B | 2.9% | 12.2% | -1.0 pts |
| West | $14.0B | 8.4% | 26.2% | -0.6 pts |

## SQL task numeric answers

1. Average weekly sales for Maxi in 2020: $61.5M.
2. Promo penetration by industry market in 2020:
   - TOTAL ATLANTIC MARKET: 35.5%
   - TOTAL NATIONAL MARKET: 35.2%
   - TOTAL ONTARIO MARKET: 33.5%
   - TOTAL QUEBEC MARKET: 33.1%
   - TOTAL WEST MARKET: 35.5%
3. Highest E-Commerce Sales week by Discount Market:
   - MAXI BANNER QUEBEC: WE Mar 14 20, $3.5M
   - NO FRILLS ATLANTIC: WE Mar 14 20, $0.4M
   - NO FRILLS ONTARIO: WE Mar 14 20, $6.7M
   - NO FRILLS TOTAL WEST: WE Mar 14 20, $2.1M
   - RCSS ONTARIO: WE Mar 14 20, $1.9M
   - RCSS TOTAL WEST: WE Mar 14 20, $15.3M
   - TOTAL DISCOUNT DIVISION (NATIONAL): WE Mar 14 20, $30.4M
4. No Frills Ontario third week of each month and 2019 sales:
   - Jan: WE Jan 18 20, $111.2M
   - Feb: WE Feb 15 20, $112.4M
   - Mar: WE Mar 21 20, $113.3M
   - Apr: WE Apr 18 20, $118.8M
   - May: WE May 16 20, $114.4M
   - Jun: WE Jun 20 20, $109.6M
   - Jul: WE Jul 18 20, $109.5M
   - Aug: WE Aug 15 20, $103.2M
   - Sep: WE Sep 19 20, $107.7M
   - Oct: WE Oct 17 20, $98.4M
   - Nov: WE Nov 21 20, $109.4M
   - Dec: WE Dec 19 20, $121.9M
5. No Frills Ontario market share on WE Jun 27 20 relative to Total Ontario Market: 9.6% ($115.6M / $1.21B).
