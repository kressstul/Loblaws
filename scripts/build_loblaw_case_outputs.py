#!/usr/bin/env python3
"""Build the Loblaw discount division case presentation and appendices.

The script intentionally uses only the Python standard library so it can run in
the minimal cloud-agent environment. It parses the XLSX package directly,
computes the case metrics, writes support files, and emits a simple PDF deck.
"""

from __future__ import annotations

import csv
import html
import math
import os
import re
import textwrap
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from typing import Callable, Dict, Iterable, List, Tuple


WORKBOOK_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1Eg5gpOciQ17uUgP4Z0uF83zIw2iIOPvs/export?format=xlsx"
)
WORKBOOK_PATH = "source_data/super_market_strategy_analytics_case.xlsx"
OUTPUT_DIR = "output"
PDF_PATH = os.path.join(OUTPUT_DIR, "loblaw_discount_division_case_presentation.pdf")
METRICS_PATH = os.path.join(OUTPUT_DIR, "metric_summary.csv")
ANALYSIS_PATH = os.path.join(OUTPUT_DIR, "supporting_analysis.md")
SQL_PATH = os.path.join(OUTPUT_DIR, "sql_task_answers.sql")
HTML_PATH = os.path.join(OUTPUT_DIR, "deck_preview.html")
TALKING_POINTS_PATH = os.path.join(OUTPUT_DIR, "slide_talking_points.md")

XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
XLSX_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
MEASURES = [
    "Sales $ 2020",
    "Sales $ 2019",
    "Promo Sales $ 2020",
    "Promo Sales $ 2019",
    "E-Commerce Sales $ 2020",
    "E-Commerce Sales $ 2019",
]


def ensure_workbook() -> None:
    os.makedirs(os.path.dirname(WORKBOOK_PATH), exist_ok=True)
    if os.path.exists(WORKBOOK_PATH):
        return
    with urllib.request.urlopen(WORKBOOK_URL, timeout=60) as response:
        data = response.read()
    with open(WORKBOOK_PATH, "wb") as handle:
        handle.write(data)


def col_to_num(column: str) -> int:
    value = 0
    for char in column:
        value = value * 26 + ord(char) - 64
    return value


def cell_ref(ref: str) -> Tuple[int, int]:
    match = re.match(r"([A-Z]+)(\d+)", ref)
    if not match:
        raise ValueError(f"Invalid cell reference: {ref}")
    return int(match.group(2)), col_to_num(match.group(1))


def load_workbook_sheet_rows() -> Dict[str, List[List[str]]]:
    ensure_workbook()
    with zipfile.ZipFile(WORKBOOK_PATH) as archive:
        shared_strings: List[str] = []
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        for item in root.findall(XLSX_NS + "si"):
            shared_strings.append("".join((t.text or "") for t in item.iter(XLSX_NS + "t")))

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: "xl/" + rel.attrib["Target"] for rel in rels}
        sheet_paths = {
            sheet.attrib["name"]: rel_map[sheet.attrib[XLSX_REL + "id"]]
            for sheet in workbook.find(XLSX_NS + "sheets")
        }

        output: Dict[str, List[List[str]]] = {}
        for sheet_name, sheet_path in sheet_paths.items():
            sheet_root = ET.fromstring(archive.read(sheet_path))
            rows: Dict[int, Dict[int, str]] = defaultdict(dict)
            max_col = 0
            for cell in sheet_root.iter(XLSX_NS + "c"):
                ref = cell.attrib.get("r")
                if not ref:
                    continue
                row_num, col_num = cell_ref(ref)
                max_col = max(max_col, col_num)
                cell_type = cell.attrib.get("t")
                value_node = cell.find(XLSX_NS + "v")
                value = ""
                if cell_type == "s" and value_node is not None:
                    value = shared_strings[int(value_node.text)]
                elif cell_type == "inlineStr":
                    value = "".join((t.text or "") for t in cell.iter(XLSX_NS + "t"))
                elif value_node is not None:
                    value = value_node.text or ""
                if value:
                    rows[row_num][col_num] = value

            output[sheet_name] = [
                [rows[row].get(col, "") for col in range(1, max_col + 1)]
                for row in sorted(rows)
            ]
        return output


def rows_to_records(rows: List[List[str]]) -> List[Dict[str, object]]:
    header = rows[0]
    records: List[Dict[str, object]] = []
    for row in rows[1:]:
        if not row or not row[0]:
            continue
        record: Dict[str, object] = {
            header[idx]: row[idx] if idx < len(row) else "" for idx in range(len(header))
        }
        for measure in MEASURES:
            record[measure] = float(record[measure])
        records.append(record)
    return records


def sum_where(records: Iterable[Dict[str, object]], predicate: Callable[[Dict[str, object]], bool]) -> Dict[str, float]:
    return {
        measure: sum(float(record[measure]) for record in records if predicate(record))
        for measure in MEASURES
    }


def pct(value: float, decimals: int = 1) -> str:
    return f"{value * 100:.{decimals}f}%"


def pts(value: float, decimals: int = 1) -> str:
    return f"{value * 100:+.{decimals}f} pts"


def money_b(value: float, decimals: int = 1) -> str:
    return f"${value / 1_000_000_000:.{decimals}f}B"


def money_m(value: float, decimals: int = 0) -> str:
    return f"${value / 1_000_000:.{decimals}f}M"


def compute_metrics() -> Dict[str, object]:
    sheets = load_workbook_sheet_rows()
    discount = rows_to_records(sheets["Discount Sales by Region Data"])
    industry = rows_to_records(sheets["Industry Sales by Region Data"])

    division = sum_where(
        discount,
        lambda record: record["Discount Market"] == "TOTAL DISCOUNT DIVISION (NATIONAL)",
    )
    industry_national = sum_where(
        industry,
        lambda record: record["Industry Market"] == "TOTAL NATIONAL MARKET",
    )

    banner_names = sorted({str(record["Discount Market"]) for record in discount})
    industry_names = sorted({str(record["Industry Market"]) for record in industry})

    banners = {}
    for banner in banner_names:
        values = sum_where(discount, lambda record, banner=banner: record["Discount Market"] == banner)
        banners[banner] = enrich_values(values)

    industry_markets = {}
    for market in industry_names:
        values = sum_where(industry, lambda record, market=market: record["Industry Market"] == market)
        industry_markets[market] = enrich_values(values)

    region_map = {
        "Atlantic": (["NO FRILLS ATLANTIC"], "TOTAL ATLANTIC MARKET"),
        "Quebec": (["MAXI BANNER QUEBEC"], "TOTAL QUEBEC MARKET"),
        "Ontario": (["NO FRILLS ONTARIO", "RCSS ONTARIO"], "TOTAL ONTARIO MARKET"),
        "West": (["NO FRILLS TOTAL WEST", "RCSS TOTAL WEST"], "TOTAL WEST MARKET"),
    }
    regions = {}
    for region, (region_banners, industry_market) in region_map.items():
        discount_values = sum_where(
            discount,
            lambda record, region_banners=region_banners: record["Discount Market"] in region_banners,
        )
        industry_values = sum_where(
            industry,
            lambda record, industry_market=industry_market: record["Industry Market"] == industry_market,
        )
        enriched = enrich_values(discount_values)
        enriched["share_2020"] = discount_values["Sales $ 2020"] / industry_values["Sales $ 2020"]
        enriched["share_2019"] = discount_values["Sales $ 2019"] / industry_values["Sales $ 2019"]
        enriched["share_delta"] = enriched["share_2020"] - enriched["share_2019"]
        regions[region] = enriched

    ecom_peak = {}
    for record in discount:
        market = str(record["Discount Market"])
        if market not in ecom_peak or float(record["E-Commerce Sales $ 2020"]) > float(
            ecom_peak[market]["E-Commerce Sales $ 2020"]
        ):
            ecom_peak[market] = record

    no_frills_ontario_third_weeks = compute_third_weeks(discount)

    nfo_jun27 = next(
        record
        for record in discount
        if record["Discount Market"] == "NO FRILLS ONTARIO" and record["Period"] == "WE Jun 27 20"
    )
    ontario_jun27 = next(
        record
        for record in industry
        if record["Industry Market"] == "TOTAL ONTARIO MARKET" and record["Period"] == "WE Jun 27 20"
    )

    metrics = {
        "discount": discount,
        "industry": industry,
        "division": enrich_values(division),
        "industry_national": enrich_values(industry_national),
        "banners": banners,
        "industry_markets": industry_markets,
        "regions": regions,
        "ecom_peak": ecom_peak,
        "sql": {
            "maxi_average_weekly_sales_2020": banners["MAXI BANNER QUEBEC"]["sales_2020"] / 53,
            "industry_promo_penetration": {
                market: values["promo_pen_2020"] for market, values in industry_markets.items()
            },
            "ecom_peak": ecom_peak,
            "no_frills_ontario_third_weeks": no_frills_ontario_third_weeks,
            "no_frills_ontario_share_jun27": float(nfo_jun27["Sales $ 2020"])
            / float(ontario_jun27["Sales $ 2020"]),
            "no_frills_ontario_jun27_sales": float(nfo_jun27["Sales $ 2020"]),
            "total_ontario_jun27_sales": float(ontario_jun27["Sales $ 2020"]),
        },
    }

    metrics["division"]["share_2020"] = (
        metrics["division"]["sales_2020"] / metrics["industry_national"]["sales_2020"]
    )
    metrics["division"]["share_2019"] = (
        metrics["division"]["sales_2019"] / metrics["industry_national"]["sales_2019"]
    )
    metrics["division"]["share_delta"] = (
        metrics["division"]["share_2020"] - metrics["division"]["share_2019"]
    )
    return metrics


def enrich_values(values: Dict[str, float]) -> Dict[str, float]:
    return {
        "sales_2020": values["Sales $ 2020"],
        "sales_2019": values["Sales $ 2019"],
        "sales_growth": values["Sales $ 2020"] / values["Sales $ 2019"] - 1,
        "promo_sales_2020": values["Promo Sales $ 2020"],
        "promo_sales_2019": values["Promo Sales $ 2019"],
        "promo_growth": values["Promo Sales $ 2020"] / values["Promo Sales $ 2019"] - 1,
        "promo_pen_2020": values["Promo Sales $ 2020"] / values["Sales $ 2020"],
        "promo_pen_2019": values["Promo Sales $ 2019"] / values["Sales $ 2019"],
        "ecom_sales_2020": values["E-Commerce Sales $ 2020"],
        "ecom_sales_2019": values["E-Commerce Sales $ 2019"],
        "ecom_growth": values["E-Commerce Sales $ 2020"] / values["E-Commerce Sales $ 2019"] - 1,
        "ecom_pen_2020": values["E-Commerce Sales $ 2020"] / values["Sales $ 2020"],
        "ecom_pen_2019": values["E-Commerce Sales $ 2019"] / values["Sales $ 2019"],
    }


def compute_third_weeks(discount: List[Dict[str, object]]) -> List[Dict[str, object]]:
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    by_month: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for record in discount:
        if record["Discount Market"] != "NO FRILLS ONTARIO":
            continue
        match = re.search(r"WE (\w{3}) ", str(record["Period"]))
        if match:
            by_month[match.group(1)].append(record)
    output = []
    for month in month_order:
        rows = by_month[month]
        if len(rows) >= 3:
            row = rows[2]
            output.append(
                {
                    "month": month,
                    "period": row["Period"],
                    "sales_2019": float(row["Sales $ 2019"]),
                }
            )
    return output


def write_metric_summary(metrics: Dict[str, object]) -> None:
    with open(METRICS_PATH, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "level",
                "name",
                "sales_2020",
                "sales_2019",
                "sales_growth",
                "promo_pen_2020",
                "promo_pen_2019",
                "ecom_pen_2020",
                "ecom_growth",
                "share_2020",
                "share_2019",
                "share_delta",
            ]
        )
        write_metric_row(writer, "division", "TOTAL DISCOUNT DIVISION (NATIONAL)", metrics["division"])
        write_metric_row(writer, "industry", "TOTAL NATIONAL MARKET", metrics["industry_national"])
        for name, values in metrics["banners"].items():
            write_metric_row(writer, "banner", name, values)
        for name, values in metrics["regions"].items():
            write_metric_row(writer, "region", name, values)
        for name, values in metrics["industry_markets"].items():
            write_metric_row(writer, "industry_market", name, values)


def write_metric_row(writer: csv.writer, level: str, name: str, values: Dict[str, float]) -> None:
    writer.writerow(
        [
            level,
            name,
            round(values["sales_2020"], 2),
            round(values["sales_2019"], 2),
            round(values["sales_growth"], 6),
            round(values["promo_pen_2020"], 6),
            round(values["promo_pen_2019"], 6),
            round(values["ecom_pen_2020"], 6),
            round(values["ecom_growth"], 6),
            round(values.get("share_2020", 0), 6),
            round(values.get("share_2019", 0), 6),
            round(values.get("share_delta", 0), 6),
        ]
    )


def write_analysis(metrics: Dict[str, object]) -> None:
    division = metrics["division"]
    industry = metrics["industry_national"]
    regions = metrics["regions"]
    sql = metrics["sql"]
    lines = [
        "# Supporting analysis - Loblaw Discount Division case",
        "",
        "## Assumptions",
        "",
        "- The division-level view uses the workbook row `TOTAL DISCOUNT DIVISION (NATIONAL)` to avoid double-counting banner rows.",
        "- Regional share maps discount banners to the closest regional industry market: Maxi to Quebec, No Frills Atlantic to Atlantic, No Frills and RCSS Ontario to Ontario, and No Frills and RCSS West to West.",
        "- The SQL task's third-week logic groups by the month embedded in `Period`, matching the prompt's example that April's third week is `WE Apr 18 20`.",
        "- Data is fictitious per the case prompt; recommendations are directional and intended for a 15-minute discussion.",
        "",
        "## Key outputs",
        "",
        f"- Discount Division sales were {money_b(division['sales_2020'])} in 2020, up {pct(division['sales_growth'])}, versus industry growth of {pct(industry['sales_growth'])}.",
        f"- National share declined from {pct(division['share_2019'])} to {pct(division['share_2020'])}, a {pts(division['share_delta'])} change.",
        f"- Promo penetration was {pct(division['promo_pen_2020'])}, matching the national industry but down from {pct(division['promo_pen_2019'])} in 2019.",
        f"- E-commerce sales grew {pct(division['ecom_growth'], 0)} to {pct(division['ecom_pen_2020'])} of sales, still below industry penetration of {pct(industry['ecom_pen_2020'])}.",
        "",
        "## Regional scorecard",
        "",
        "| Region | 2020 sales | YoY growth | 2020 share | Share change |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for region in ["Atlantic", "Quebec", "Ontario", "West"]:
        values = regions[region]
        lines.append(
            f"| {region} | {money_b(values['sales_2020'])} | {pct(values['sales_growth'])} | "
            f"{pct(values['share_2020'])} | {pts(values['share_delta'])} |"
        )
    lines.extend(
        [
            "",
            "## SQL task numeric answers",
            "",
            f"1. Average weekly sales for Maxi in 2020: {money_m(sql['maxi_average_weekly_sales_2020'], 1)}.",
            "2. Promo penetration by industry market in 2020:",
        ]
    )
    for market, value in sql["industry_promo_penetration"].items():
        lines.append(f"   - {market}: {pct(value)}")
    lines.append("3. Highest E-Commerce Sales week by Discount Market:")
    for market, record in sorted(sql["ecom_peak"].items()):
        lines.append(
            f"   - {market}: {record['Period']}, {money_m(float(record['E-Commerce Sales $ 2020']), 1)}"
        )
    lines.append("4. No Frills Ontario third week of each month and 2019 sales:")
    for item in sql["no_frills_ontario_third_weeks"]:
        lines.append(f"   - {item['month']}: {item['period']}, {money_m(item['sales_2019'], 1)}")
    lines.append(
        "5. No Frills Ontario market share on WE Jun 27 20 relative to Total Ontario Market: "
        f"{pct(sql['no_frills_ontario_share_jun27'])} "
        f"({money_m(sql['no_frills_ontario_jun27_sales'], 1)} / {money_b(sql['total_ontario_jun27_sales'], 2)})."
    )
    lines.append("")
    with open(ANALYSIS_PATH, "w") as handle:
        handle.write("\n".join(lines))


def write_sql(metrics: Dict[str, object]) -> None:
    sql_text = """-- Loblaw Strategy & Analytics Case - SQL task answers
-- Assumptions:
-- 1. discount_sales_by_region has the columns:
--    discount_market, period, sales_2020, sales_2019,
--    promo_sales_2020, promo_sales_2019, e_commerce_sales_2020,
--    e_commerce_sales_2019.
-- 2. industry_sales_by_region has analogous industry_market columns.
-- 3. Date parsing syntax varies by SQL version; functions below show logic.

-- (1) Average weekly sales for Maxi in 2020
SELECT
  AVG(sales_2020) AS avg_weekly_sales_2020
FROM discount_sales_by_region
WHERE discount_market = 'MAXI BANNER QUEBEC';

-- Numeric result from workbook: $61.5M.

-- (2) Promo penetration by Industry Market in 2020
SELECT
  industry_market,
  SUM(promo_sales_2020) / NULLIF(SUM(sales_2020), 0) AS promo_penetration_2020
FROM industry_sales_by_region
GROUP BY industry_market;

-- Numeric results:
-- TOTAL ATLANTIC MARKET: 35.5%
-- TOTAL NATIONAL MARKET: 35.2%
-- TOTAL ONTARIO MARKET: 33.5%
-- TOTAL QUEBEC MARKET: 33.1%
-- TOTAL WEST MARKET: 35.5%

-- (3) By Discount Market, identify the week with the highest E-Com sales in 2020
WITH ranked AS (
  SELECT
    discount_market,
    period,
    e_commerce_sales_2020,
    ROW_NUMBER() OVER (
      PARTITION BY discount_market
      ORDER BY e_commerce_sales_2020 DESC
    ) AS rn
  FROM discount_sales_by_region
)
SELECT
  discount_market,
  period,
  e_commerce_sales_2020
FROM ranked
WHERE rn = 1;

-- (4) For No Frills Ontario, pull the third week of each month and 2019 sales
WITH prepared AS (
  SELECT
    discount_market,
    period,
    sales_2019,
    CAST('20' || SUBSTRING(period FROM 11 FOR 2) || '-' ||
      CASE SUBSTRING(period FROM 4 FOR 3)
        WHEN 'Jan' THEN '01'
        WHEN 'Feb' THEN '02'
        WHEN 'Mar' THEN '03'
        WHEN 'Apr' THEN '04'
        WHEN 'May' THEN '05'
        WHEN 'Jun' THEN '06'
        WHEN 'Jul' THEN '07'
        WHEN 'Aug' THEN '08'
        WHEN 'Sep' THEN '09'
        WHEN 'Oct' THEN '10'
        WHEN 'Nov' THEN '11'
        WHEN 'Dec' THEN '12'
      END || '-' || SUBSTRING(period FROM 8 FOR 2) AS DATE) AS week_end_date
  FROM discount_sales_by_region
  WHERE discount_market = 'NO FRILLS ONTARIO'
),
month_ranked AS (
  SELECT
    discount_market,
    period,
    sales_2019,
    EXTRACT(MONTH FROM week_end_date) AS month_number,
    ROW_NUMBER() OVER (
      PARTITION BY EXTRACT(MONTH FROM week_end_date)
      ORDER BY week_end_date
    ) AS week_in_month
  FROM prepared
  WHERE week_end_date >= DATE '2020-01-01'
    AND week_end_date < DATE '2021-01-01'
)
SELECT
  month_number,
  period,
  sales_2019
FROM month_ranked
WHERE week_in_month = 3;

-- The workbook result matches the prompt example: Apr -> WE Apr 18 20, $118.8M.

-- (5) Using a Join, calculate No Frills Ontario market share on WE Jun 27 20
SELECT
  d.period,
  d.sales_2020 AS no_frills_ontario_sales_2020,
  i.sales_2020 AS total_ontario_market_sales_2020,
  d.sales_2020 / NULLIF(i.sales_2020, 0) AS market_share_2020
FROM discount_sales_by_region d
JOIN industry_sales_by_region i
  ON d.period = i.period
WHERE d.discount_market = 'NO FRILLS ONTARIO'
  AND i.industry_market = 'TOTAL ONTARIO MARKET'
  AND d.period = 'WE Jun 27 20';

-- Numeric result from workbook: 9.6% ($115.6M / $1.21B).
"""
    with open(SQL_PATH, "w") as handle:
        handle.write(sql_text)


def write_html_preview(metrics: Dict[str, object]) -> None:
    """Write a self-contained HTML version for easy local preview."""
    division = metrics["division"]
    industry = metrics["industry_national"]
    regions = metrics["regions"]
    banners = metrics["banners"]

    def esc(value: object) -> str:
        return html.escape(str(value))

    region_rows = []
    for region in ["Atlantic", "Quebec", "Ontario", "West"]:
        values = regions[region]
        delta_class = "good" if values["share_delta"] >= 0 else "bad"
        region_rows.append(
            "<tr>"
            f"<td>{esc(region)}</td>"
            f"<td>{esc(money_b(values['sales_2020']))}</td>"
            f"<td>{esc(pct(values['sales_growth']))}</td>"
            f"<td>{esc(pct(values['share_2020']))}</td>"
            f"<td class=\"{delta_class}\">{esc(pts(values['share_delta']))}</td>"
            "</tr>"
        )

    content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Loblaw Discount Division Case Preview</title>
  <style>
    :root {{
      --blue: #004891;
      --red: #da291c;
      --yellow: #ffd200;
      --ink: #23272c;
      --muted: #66707c;
      --line: #d6dce2;
      --bg: #f4f6f8;
      --good: #218957;
      --bad: #da291c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.35;
    }}
    main {{
      max-width: 1160px;
      margin: 28px auto;
      padding: 0 20px 36px;
    }}
    .note {{
      color: var(--muted);
      margin: 0 0 18px;
    }}
    .slide {{
      position: relative;
      width: 100%;
      min-height: 610px;
      margin: 0 0 28px;
      padding: 42px 56px 52px 76px;
      background: white;
      border: 1px solid var(--line);
      box-shadow: 0 8px 26px rgba(31, 44, 64, 0.12);
      overflow: hidden;
    }}
    .slide::before {{
      content: "";
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 16px;
      background: var(--blue);
    }}
    .slide::after {{
      content: "";
      position: absolute;
      left: 16px;
      top: 0;
      bottom: 0;
      width: 7px;
      background: var(--red);
    }}
    .title-slide {{
      display: flex;
      flex-direction: column;
      justify-content: center;
      min-height: 610px;
    }}
    .title-slide h1 {{
      max-width: 820px;
      font-size: 44px;
      line-height: 1.08;
      margin-bottom: 18px;
    }}
    .eyebrow {{
      color: var(--blue);
      font-size: 15px;
      font-weight: 700;
      letter-spacing: 0.08em;
      margin-bottom: 18px;
      text-transform: uppercase;
    }}
    .title-meta {{
      margin-top: 38px;
      color: var(--muted);
      font-size: 18px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 32px;
      letter-spacing: -0.02em;
    }}
    h2 {{
      margin: 24px 0 12px;
      font-size: 21px;
    }}
    .subtitle {{
      color: var(--muted);
      margin: 0 0 26px;
      padding-bottom: 18px;
      border-bottom: 1px solid var(--line);
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 18px;
      margin: 10px 0 28px;
    }}
    .card {{
      border: 1px solid var(--line);
      background: #f8fafc;
      padding: 20px;
      min-height: 128px;
    }}
    .metric {{
      color: var(--blue);
      font-size: 36px;
      font-weight: 700;
      margin-bottom: 6px;
    }}
    .metric.red {{ color: var(--red); }}
    .label {{
      font-weight: 700;
      margin-bottom: 7px;
    }}
    .callout {{
      margin: 18px 0 24px;
      padding: 16px 20px;
      background: #fff2df;
      border: 1px solid #efc891;
      font-size: 19px;
      font-weight: 700;
    }}
    ul {{
      margin: 10px 0 0 20px;
      padding: 0;
    }}
    li {{ margin: 9px 0; }}
    .two-col {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 44px;
      align-items: start;
    }}
    .bar-row {{
      display: grid;
      grid-template-columns: 150px 1fr 70px;
      gap: 12px;
      align-items: center;
      margin: 22px 0;
      font-weight: 700;
    }}
    .bar-bg {{
      height: 20px;
      background: #e8edf2;
      overflow: hidden;
    }}
    .bar {{
      height: 100%;
      background: var(--blue);
    }}
    .bar.red {{ background: var(--red); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 18px;
    }}
    th {{
      background: var(--blue);
      color: white;
      text-align: left;
      padding: 12px;
    }}
    td {{
      border-bottom: 1px solid var(--line);
      padding: 13px 12px;
    }}
    .good {{ color: var(--good); font-weight: 700; }}
    .bad {{ color: var(--bad); font-weight: 700; }}
    .actions {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-top: 22px;
    }}
    .action {{
      border: 1px solid var(--line);
      background: #f8fafc;
      padding: 18px;
      border-top: 9px solid var(--blue);
      min-height: 330px;
    }}
    .action.red {{ border-top-color: var(--red); }}
    .action.yellow {{ border-top-color: #d87621; }}
    .action.green {{ border-top-color: var(--good); }}
    .appendix-grid {{
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 26px;
      margin-top: 18px;
    }}
    .file-list {{
      border: 1px solid var(--line);
      background: #f8fafc;
      padding: 18px 20px;
    }}
    .file-list code {{
      color: var(--blue);
      font-weight: 700;
    }}
    .thanks {{
      display: flex;
      min-height: 610px;
      flex-direction: column;
      justify-content: center;
      text-align: center;
    }}
    .thanks h1 {{
      color: var(--blue);
      font-size: 58px;
    }}
    .thanks p {{
      margin-left: auto;
      margin-right: auto;
      max-width: 720px;
      font-size: 22px;
      color: var(--muted);
    }}
    .agenda-list {{
      margin-top: 34px;
      display: grid;
      gap: 18px;
    }}
    .agenda-item {{
      display: grid;
      grid-template-columns: 64px 1fr;
      gap: 18px;
      align-items: start;
      padding: 18px 20px;
      border: 1px solid var(--line);
      background: #f8fafc;
    }}
    .agenda-number {{
      display: flex;
      align-items: center;
      justify-content: center;
      width: 46px;
      height: 46px;
      border-radius: 50%;
      background: var(--blue);
      color: white;
      font-weight: 700;
      font-size: 20px;
    }}
    .agenda-item h2 {{
      margin: 0 0 4px;
    }}
    .agenda-item p {{
      margin: 0;
      color: var(--muted);
    }}
    .source {{
      position: absolute;
      left: 76px;
      right: 56px;
      bottom: 20px;
      color: var(--muted);
      font-size: 12px;
    }}
  </style>
</head>
<body>
<main>
  <p class="note">HTML preview of <code>loblaw_discount_division_case_presentation.pdf</code>. Open this file in a browser if the PDF does not render locally.</p>

  <section class="slide title-slide">
    <div class="eyebrow">Strategy & Analytics Case</div>
    <h1>Loblaw Discount Division 2020 Performance Review</h1>
    <p class="subtitle">A 15-minute discussion on performance, priority opportunities, and immediate actions.</p>
    <div class="title-meta">
      Prepared for: Strategy Manager discussion<br>
      Presented by: Krystal Ng<br>
      Context: Discount Division prior to Hard Discount<br>
      Date: June 2026
    </div>
    <div class="source">Source: Super Market Strategy & Analytics Case workbook; fictitious case data.</div>
  </section>

  <section class="slide">
    <h1>Agenda</h1>
    <p class="subtitle">A focused path from headline performance to recommended action.</p>
    <div class="agenda-list">
      <div class="agenda-item"><div class="agenda-number">1</div><div><h2>Executive takeaway</h2><p>How 2020 growth masked national share loss.</p></div></div>
      <div class="agenda-item"><div class="agenda-number">2</div><div><h2>Performance scorecard</h2><p>Sales, promo, e-commerce, and industry comparison.</p></div></div>
      <div class="agenda-item"><div class="agenda-number">3</div><div><h2>Priority focus areas</h2><p>Why Ontario/RCSS is the near-term priority and Atlantic is the playbook.</p></div></div>
      <div class="agenda-item"><div class="agenda-number">4</div><div><h2>Actions, KPIs, and Q&A</h2><p>Immediate workstreams, success measures, thank-you, and appendix backup.</p></div></div>
    </div>
    <div class="source">Source: Super Market Strategy & Analytics Case workbook; fictitious case data.</div>
  </section>

  <section class="slide">
    <h1>Discount Division 2020: growth masked share loss</h1>
    <p class="subtitle">Recommended discussion: use 2020 momentum to defend value while closing regional and e-commerce gaps.</p>
    <div class="cards">
      <div class="card"><div class="metric">{esc(money_b(division['sales_2020']))}</div><div class="label">2020 sales</div><p>Sales grew {esc(pct(division['sales_growth']))}, but the market grew {esc(pct(industry['sales_growth']))}.</p></div>
      <div class="card"><div class="metric red">{esc(pct(division['share_2020']))}</div><div class="label">national share</div><p>Share declined {esc(pts(division['share_delta']))} versus 2019.</p></div>
      <div class="card"><div class="metric">{esc(pct(division['ecom_pen_2020']))}</div><div class="label">e-commerce penetration</div><p>E-commerce sales rose {esc(pct(division['ecom_growth'], 0))}, but penetration trails industry by {(industry['ecom_pen_2020'] - division['ecom_pen_2020']) * 100:.1f} pts.</p></div>
    </div>
    <div class="callout">Recommendation: prioritize a share recovery program in Ontario/RCSS while scaling e-commerce capacity and preserving value-price credibility.</div>
    <h2>What management should take away</h2>
    <ul>
      <li>The division captured absolute COVID-era demand, but lost relative position versus a faster-growing market.</li>
      <li>Ontario is the largest actionable issue: combined share fell about 1.0 pt and RCSS Ontario declined 9.6%.</li>
      <li>E-commerce was the biggest growth engine; closing the industry penetration gap is a near-term share lever.</li>
      <li>No Frills Atlantic is a small-base success case and should be mined for transferable execution lessons.</li>
    </ul>
    <div class="source">Source: Super Market Strategy & Analytics Case workbook; fictitious case data.</div>
  </section>

  <section class="slide">
    <h1>Scorecard: growth was strong, relative capture weaker</h1>
    <p class="subtitle">Core issue is not demand generation; it is relative capture of a growing market.</p>
    <div class="two-col">
      <div>
        <h2>Sales growth</h2>
        <div class="bar-row"><span>Discount Division</span><div class="bar-bg"><div class="bar" style="width: {division['sales_growth'] / 0.12 * 100:.1f}%"></div></div><span>{esc(pct(division['sales_growth']))}</span></div>
        <div class="bar-row"><span>Industry</span><div class="bar-bg"><div class="bar red" style="width: {industry['sales_growth'] / 0.12 * 100:.1f}%"></div></div><span>{esc(pct(industry['sales_growth']))}</span></div>
        <p><strong>Net result:</strong> national share moved from {esc(pct(division['share_2019']))} to {esc(pct(division['share_2020']))}. Change: <span class="bad">{esc(pts(division['share_delta']))}</span>.</p>
      </div>
      <div>
        <h2>Key metrics</h2>
        <table>
          <tr><th>Metric</th><th>Discount</th><th>Industry</th></tr>
          <tr><td>Sales growth</td><td>{esc(pct(division['sales_growth']))}</td><td>{esc(pct(industry['sales_growth']))}</td></tr>
          <tr><td>Promo penetration</td><td>{esc(pct(division['promo_pen_2020']))}</td><td>{esc(pct(industry['promo_pen_2020']))}</td></tr>
          <tr><td>E-com penetration</td><td>{esc(pct(division['ecom_pen_2020']))}</td><td>{esc(pct(industry['ecom_pen_2020']))}</td></tr>
          <tr><td>E-com sales growth</td><td>{esc(pct(division['ecom_growth'], 0))}</td><td>{esc(pct(industry['ecom_growth'], 0))}</td></tr>
        </table>
      </div>
    </div>
    <h2>Interpretation</h2>
    <ul>
      <li>Promo penetration matched the market in 2020 and declined versus 2019, so share recovery should not rely only on deeper blanket promotion.</li>
      <li>Every discount market hit peak e-commerce sales in WE Mar 14 20, indicating a capacity and fulfillment stress test during the demand spike.</li>
      <li>E-commerce penetration is already material at 4.6%; the issue is converting rapid adoption into sustainable market-share capture.</li>
    </ul>
    <div class="source">Source: Super Market Strategy & Analytics Case workbook; fictitious case data.</div>
  </section>

  <section class="slide">
    <h1>Focus areas: Ontario/RCSS priority; Atlantic playbook</h1>
    <p class="subtitle">Regional lens shows the largest value pool also contains the clearest share leak.</p>
    <table>
      <tr><th>Region</th><th>2020 sales</th><th>YoY</th><th>Share</th><th>Share change</th></tr>
      {''.join(region_rows)}
    </table>
    <div class="two-col">
      <div>
        <h2>Ontario detail</h2>
        <ul>
          <li>No Frills Ontario: {esc(pct(banners['NO FRILLS ONTARIO']['sales_growth']))} sales growth.</li>
          <li>RCSS Ontario: <span class="bad">{esc(pct(banners['RCSS ONTARIO']['sales_growth']))}</span> sales growth.</li>
        </ul>
      </div>
      <div>
        <h2>E-commerce lens</h2>
        <ul>
          <li>Division penetration: {esc(pct(division['ecom_pen_2020']))}; industry: {esc(pct(industry['ecom_pen_2020']))}.</li>
          <li>Treat e-commerce as a share lever, not only a channel KPI.</li>
        </ul>
      </div>
    </div>
    <div class="source">Source: Super Market Strategy & Analytics Case workbook; fictitious case data.</div>
  </section>

  <section class="slide">
    <h1>Immediate actions and KPIs</h1>
    <p class="subtitle">Breadth-first opportunity set for the leadership team; validate with store, customer, and margin detail.</p>
    <div class="actions">
      <div class="action red"><h2>1. Ontario share reset</h2><ul><li>Deep dive RCSS Ontario stores, assortment, price gaps, and out-of-stock drivers.</li><li>Localize value communication and traffic-driving categories where share loss is highest.</li><li>KPI: weekly Ontario share, RCSS Ontario YoY sales, traffic, and basket size.</li></ul></div>
      <div class="action"><h2>2. E-commerce capacity</h2><ul><li>Expand pickup/delivery slot availability around high-demand stores and peak weeks.</li><li>Improve substitution quality and availability on known online baskets.</li><li>KPI: e-com penetration gap to industry, fulfillment rate, repeat online shoppers.</li></ul></div>
      <div class="action yellow"><h2>3. Value and promo discipline</h2><ul><li>Protect key value items and sharpen promo where competitive gaps are visible.</li><li>Shift from blanket depth to targeted, margin-aware offers by market and trip mission.</li><li>KPI: price index, promo ROI, gross margin mix, customer retention.</li></ul></div>
      <div class="action green"><h2>4. Scale what works</h2><ul><li>Study No Frills Atlantic growth drivers: local execution, offer, labor model, and competitive context.</li><li>Replicate transferable practices in comparable smaller-base markets.</li><li>KPI: market-specific share lift, sales per store, and execution scorecards.</li></ul></div>
    </div>
    <div class="callout">Next data cuts: store-count normalization, margin, price index, loyalty cohorts, online capacity, and competitor density.</div>
    <div class="source">Source: Super Market Strategy & Analytics Case workbook; fictitious case data.</div>
  </section>

  <section class="slide thanks">
    <h1>Thank you</h1>
    <p>Discussion prompts: Which Ontario diagnostic should we prioritize first? What e-commerce constraint is most urgent? What additional data would most change the recommendation?</p>
    <div class="source">Source: Super Market Strategy & Analytics Case workbook; fictitious case data.</div>
  </section>

  <section class="slide">
    <h1>Appendix: supporting analysis files</h1>
    <p class="subtitle">Use these files to validate the story, answer SQL questions, and reproduce the deck.</p>
    <div class="appendix-grid">
      <div>
        <h2>What to review</h2>
        <div class="file-list">
          <p><code>supporting_analysis.md</code><br>Assumptions, key outputs, regional scorecard, and SQL numeric answers.</p>
          <p><code>metric_summary.csv</code><br>Machine-readable KPI summary by division, banner, region, and industry market.</p>
          <p><code>sql_task_answers.sql</code><br>SQL logic for the five case questions, with workbook-derived numeric results.</p>
          <p><code>super_market_strategy_analytics_case.xlsx</code><br>Downloaded source workbook used for all calculations.</p>
          <p><code>build_loblaw_case_outputs.py</code><br>Reproducible standard-library generator for the PDF, HTML, notes, and appendices.</p>
        </div>
      </div>
      <div>
        <h2>Analysis highlights</h2>
        <ul>
          <li>Division row used to avoid double-counting banner rows.</li>
          <li>Regional share maps banners to closest industry markets.</li>
          <li>Third-week SQL logic follows the month embedded in the week-ending label.</li>
          <li>Recommendations are directional because the case data is fictitious and excludes margin, store count, and customer-level detail.</li>
        </ul>
      </div>
    </div>
    <div class="source">Source: Super Market Strategy & Analytics Case workbook; fictitious case data.</div>
  </section>
</main>
</body>
</html>
"""
    with open(HTML_PATH, "w") as handle:
        handle.write(content)


def write_talking_points(metrics: Dict[str, object]) -> None:
    division = metrics["division"]
    industry = metrics["industry_national"]
    regions = metrics["regions"]
    banners = metrics["banners"]
    content = f"""# Slide talking points - Loblaw Discount Division case

Use this as a 15-minute speaker guide. The title, agenda, appendix, and thank-you pages are brief framing/transition slides; the core strategy discussion remains the four analysis slides.

## Slide 1 - Title page

**Core message:** Set context quickly: this is a focused Discount Division performance review, not a full enterprise strategy.

- Introduce the case scope: Discount Division performance in 2020, prior to Hard Discount.
- Preview the structure: headline performance, KPI diagnosis, regional focus, immediate actions, and appendix.
- Transition: "I will use a short agenda to frame how the story builds."

## Slide 2 - Agenda

**Core message:** Orient the audience to the storyline before moving into the analysis.

- Explain that the presentation moves from the executive takeaway to diagnostics, focus areas, and actions.
- Keep this slide brief; it is a navigation slide, not an analysis slide.
- Mention that the appendix sits after the thank-you slide as backup for calculations, assumptions, and SQL logic.
- Transition: "Starting with the headline, the division grew, but the market grew faster."

## Slide 3 - Discount Division 2020: growth masked share loss

**Core message:** The business grew in absolute dollars, but underperformed the broader market, so the strategic question is share recovery rather than demand creation.

- Open with the headline: Discount Division delivered {money_b(division['sales_2020'])} in 2020 sales and grew {pct(division['sales_growth'])}.
- Immediately contrast that with industry growth of {pct(industry['sales_growth'])}; this is why growth alone is not enough to call the year a win.
- Point out the national share decline from {pct(division['share_2019'])} to {pct(division['share_2020'])}, or {pts(division['share_delta'])}.
- Frame the recommendation: recover share in Ontario/RCSS, scale e-commerce, and maintain value credibility.
- Transition: "To understand where to act, I first looked at whether the gap was broad-based or concentrated."

## Slide 4 - Scorecard: growth was strong, relative capture weaker

**Core message:** The division's main issue was weaker relative capture of a growing market, not weak category demand.

- Walk through the sales-growth comparison: Discount Division at {pct(division['sales_growth'])} versus industry at {pct(industry['sales_growth'])}.
- Note that promo penetration was {pct(division['promo_pen_2020'])}, matching the national industry, and down from {pct(division['promo_pen_2019'])} in 2019.
- Explain implication: the answer should not simply be "promote more"; it should be more targeted value and promo discipline.
- Highlight e-commerce: division e-commerce sales grew {pct(division['ecom_growth'], 0)} and reached {pct(division['ecom_pen_2020'])} penetration, but industry was {pct(industry['ecom_pen_2020'])}.
- Mention that every discount market peaked in e-commerce sales during WE Mar 14 20, suggesting a stress point around capacity and fulfillment.
- Transition: "The national average hides a clear regional priority."

## Slide 5 - Focus areas: Ontario/RCSS priority; Atlantic playbook

**Core message:** Ontario is the largest immediate problem, while Atlantic is a small-base success case worth learning from.

- Start with the regional table: Ontario sales grew only {pct(regions['Ontario']['sales_growth'])}, and share declined {pts(regions['Ontario']['share_delta'])}.
- Explain why Ontario matters: it is a large market and the decline is concentrated enough to warrant dedicated management attention.
- Call out banner-level split: No Frills Ontario grew {pct(banners['NO FRILLS ONTARIO']['sales_growth'])}, while RCSS Ontario declined {pct(banners['RCSS ONTARIO']['sales_growth'])}.
- Position RCSS Ontario as the first diagnostic deep dive: stores, assortment, price gaps, availability, and local competitive pressure.
- Balance the story with Atlantic: No Frills Atlantic grew {pct(banners['NO FRILLS ATLANTIC']['sales_growth'])} and gained share, so it can provide execution lessons.
- Transition: "Based on this, I would organize action into four immediate workstreams."

## Slide 6 - Immediate actions and KPIs

**Core message:** The response should combine targeted share recovery, e-commerce execution, value discipline, and scaling proven local playbooks.

- Ontario share reset: deep dive RCSS Ontario store performance, price perception, out-of-stocks, assortment, and competitor overlap.
- E-commerce capacity: improve pickup/delivery slot availability, substitution quality, and fulfillment reliability in high-demand stores.
- Value and promo discipline: protect key value items, but move from broad discounting to targeted offers with clear promo ROI.
- Scale what works: study No Frills Atlantic's local execution and decide what is transferable to similar markets.
- Emphasize KPIs: weekly regional share, RCSS Ontario sales/traffic/basket, e-commerce penetration gap, fulfillment rate, price index, promo ROI, and margin mix.
- Close with data needs: store-count normalization, margin, loyalty cohorts, online capacity, competitor density, and price-index detail.

## Slide 7 - Thank you

**Core message:** Close with a clear invitation for discussion and next-step prioritization.

- Thank the audience and invite questions.
- Offer three prompts if Q&A needs structure: Ontario diagnostic priority, most urgent e-commerce constraint, and highest-value incremental data cut.
- Reinforce that the recommendations are directional and should be validated with margin, store-count, price-index, and customer-level data.

## Slide 8 - Appendix: supporting analysis files

**Core message:** The appendix provides the audit trail for assumptions, calculations, SQL logic, and reproducibility after the main close.

- Point to `supporting_analysis.md` for assumptions, key outputs, the regional scorecard, and numeric SQL answers.
- Point to `metric_summary.csv` for the KPI table by division, banner, region, and industry market.
- Point to `sql_task_answers.sql` for the five requested SQL queries and the workbook-derived outputs.
- Mention that `super_market_strategy_analytics_case.xlsx` is the source data and `build_loblaw_case_outputs.py` regenerates all outputs.
- Use this slide only if asked for detail during Q&A; it is intentionally placed after the thank-you slide as backup.

## Suggested 15-minute flow

- Slide 1: 1 minute - title, context, and agenda.
- Slide 2: 1 minute - agenda and story arc.
- Slide 3: 3 minutes - headline, problem framing, recommendation.
- Slide 4: 3 minutes - KPI diagnosis and why "more promo" is not the only answer.
- Slide 5: 3 minutes - regional and banner prioritization.
- Slide 6: 2 minutes - actions, KPIs, and next analysis.
- Slide 7: 1 minute - thank-you/Q&A transition.
- Slide 8: backup - appendix pointer if asked for supporting detail.
- Buffer: 1 minute - assumptions and Q&A setup.
"""
    with open(TALKING_POINTS_PATH, "w") as handle:
        handle.write(content)


class PdfPage:
    def __init__(self, width: int = 960, height: int = 540) -> None:
        self.width = width
        self.height = height
        self.ops: List[str] = []

    def rgb(self, r: int, g: int, b: int) -> Tuple[float, float, float]:
        return (r / 255, g / 255, b / 255)

    def set_fill(self, color: Tuple[int, int, int]) -> None:
        r, g, b = self.rgb(*color)
        self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg")

    def set_stroke(self, color: Tuple[int, int, int], width: float = 1) -> None:
        r, g, b = self.rgb(*color)
        self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} RG {width:.2f} w")

    def rect(self, x: float, y: float, w: float, h: float, fill: Tuple[int, int, int] | None = None,
             stroke: Tuple[int, int, int] | None = None, stroke_width: float = 1) -> None:
        if fill:
            self.set_fill(fill)
        if stroke:
            self.set_stroke(stroke, stroke_width)
        pdf_y = self.height - y - h
        op = "B" if fill and stroke else "f" if fill else "S"
        self.ops.append(f"{x:.2f} {pdf_y:.2f} {w:.2f} {h:.2f} re {op}")

    def line(self, x1: float, y1: float, x2: float, y2: float, color: Tuple[int, int, int],
             width: float = 1) -> None:
        self.set_stroke(color, width)
        self.ops.append(
            f"{x1:.2f} {self.height - y1:.2f} m {x2:.2f} {self.height - y2:.2f} l S"
        )

    def text(self, x: float, y: float, text: str, size: int = 16, bold: bool = False,
             color: Tuple[int, int, int] = (30, 30, 30)) -> None:
        self.set_fill(color)
        font = "/F2" if bold else "/F1"
        pdf_y = self.height - y - size
        self.ops.append(f"BT {font} {size} Tf {x:.2f} {pdf_y:.2f} Td ({escape_pdf(text)}) Tj ET")

    def wrapped_text(self, x: float, y: float, text: str, width: float, size: int = 14,
                     bold: bool = False, color: Tuple[int, int, int] = (30, 30, 30),
                     leading: float | None = None) -> float:
        if leading is None:
            leading = size * 1.28
        max_chars = max(8, int(width / (size * 0.54)))
        lines: List[str] = []
        for para in text.split("\n"):
            lines.extend(textwrap.wrap(para, max_chars) or [""])
        current = y
        for line in lines:
            self.text(x, current, line, size=size, bold=bold, color=color)
            current += leading
        return current

    def bullet_list(self, x: float, y: float, items: List[str], width: float, size: int = 14,
                    color: Tuple[int, int, int] = (30, 30, 30), bullet_color: Tuple[int, int, int] = (218, 41, 28)) -> float:
        current = y
        for item in items:
            self.text(x, current, "-", size=size, bold=True, color=bullet_color)
            current = self.wrapped_text(x + 18, current, item, width - 18, size=size, color=color)
            current += 5
        return current

    def content(self) -> bytes:
        return ("\n".join(self.ops) + "\n").encode("latin-1", errors="replace")


def escape_pdf(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class PdfDocument:
    def __init__(self) -> None:
        self.pages: List[PdfPage] = []

    def add_page(self, page: PdfPage) -> None:
        self.pages.append(page)

    def save(self, path: str) -> None:
        objects: Dict[int, bytes] = {}
        page_object_numbers = []
        objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        objects[4] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"
        next_obj = 5
        for page in self.pages:
            page_obj = next_obj
            content_obj = next_obj + 1
            page_object_numbers.append(page_obj)
            stream = page.content()
            objects[content_obj] = (
                f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
                + stream
                + b"endstream"
            )
            objects[page_obj] = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page.width} {page.height}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
                f"/Contents {content_obj} 0 R >>"
            ).encode("latin-1")
            next_obj += 2
        kids = " ".join(f"{obj} 0 R" for obj in page_object_numbers)
        objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_numbers)} >>".encode("latin-1")
        objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"

        max_obj = max(objects)
        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0] * (max_obj + 1)
        for obj_num in range(1, max_obj + 1):
            offsets[obj_num] = len(output)
            output.extend(f"{obj_num} 0 obj\n".encode("latin-1"))
            output.extend(objects[obj_num])
            output.extend(b"\nendobj\n")
        xref_start = len(output)
        output.extend(f"xref\n0 {max_obj + 1}\n".encode("latin-1"))
        output.extend(b"0000000000 65535 f\n")
        for obj_num in range(1, max_obj + 1):
            output.extend(f"{offsets[obj_num]:010d} 00000 n\n".encode("latin-1"))
        output.extend(
            f"trailer\n<< /Size {max_obj + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode(
                "latin-1"
            )
        )
        with open(path, "wb") as handle:
            handle.write(output)


BLUE = (0, 72, 145)
RED = (218, 41, 28)
YELLOW = (255, 210, 0)
DARK = (35, 39, 44)
GREY = (103, 112, 124)
LIGHT_GREY = (236, 239, 242)
MID_GREY = (200, 206, 213)
GREEN = (40, 140, 90)
ORANGE = (218, 118, 33)


def slide_base(title: str, subtitle: str = "") -> PdfPage:
    page = PdfPage()
    page.rect(0, 0, page.width, page.height, fill=(255, 255, 255))
    page.rect(0, 0, 14, page.height, fill=BLUE)
    page.rect(14, 0, 6, page.height, fill=RED)
    page.text(45, 24, title, size=26, bold=True, color=DARK)
    if subtitle:
        page.text(46, 58, subtitle, size=12, color=GREY)
    page.line(45, 84, 915, 84, MID_GREY, width=0.7)
    page.text(45, 510, "Source: Super Market Strategy & Analytics Case workbook; fictitious case data.", size=8, color=GREY)
    return page


def card(page: PdfPage, x: float, y: float, w: float, h: float, headline: str, label: str, note: str,
         color: Tuple[int, int, int] = BLUE) -> None:
    page.rect(x, y, w, h, fill=(248, 250, 252), stroke=MID_GREY, stroke_width=0.8)
    page.text(x + 18, y + 16, headline, size=28, bold=True, color=color)
    page.text(x + 18, y + 52, label, size=13, bold=True, color=DARK)
    page.wrapped_text(x + 18, y + 75, note, w - 36, size=10, color=GREY)


def draw_bar(page: PdfPage, x: float, y: float, label: str, value: float, max_value: float,
             color: Tuple[int, int, int], width: float = 260) -> None:
    page.text(x, y, label, size=12, bold=True, color=DARK)
    page.rect(x + 145, y + 2, width, 16, fill=LIGHT_GREY)
    page.rect(x + 145, y + 2, width * value / max_value, 16, fill=color)
    page.text(x + 145 + width + 10, y, pct(value), size=12, bold=True, color=color)


def write_pdf(metrics: Dict[str, object]) -> None:
    division = metrics["division"]
    industry = metrics["industry_national"]
    regions = metrics["regions"]
    banners = metrics["banners"]

    doc = PdfDocument()

    # Title page
    page = PdfPage()
    page.rect(0, 0, page.width, page.height, fill=(255, 255, 255))
    page.rect(0, 0, 112, page.height, fill=BLUE)
    page.rect(112, 0, 12, page.height, fill=RED)
    page.rect(162, 102, 690, 2, fill=YELLOW)
    page.text(162, 130, "STRATEGY & ANALYTICS CASE", size=13, bold=True, color=BLUE)
    page.wrapped_text(
        162,
        170,
        "Loblaw Discount Division 2020 Performance Review",
        710,
        size=36,
        bold=True,
        color=DARK,
        leading=42,
    )
    page.wrapped_text(
        162,
        278,
        "A 15-minute discussion on performance, priority opportunities, and immediate actions.",
        650,
        size=18,
        color=GREY,
        leading=24,
    )
    page.rect(162, 352, 430, 124, fill=(248, 250, 252), stroke=MID_GREY, stroke_width=0.8)
    page.text(184, 382, "Prepared for", size=11, bold=True, color=GREY)
    page.text(184, 406, "Strategy Manager discussion", size=16, bold=True, color=DARK)
    page.text(184, 432, "Presented by: Krystal Ng", size=11, color=GREY)
    page.text(184, 452, "Context: Discount Division prior to Hard Discount", size=11, color=GREY)
    page.text(184, 472, "Date: June 2026", size=11, color=GREY)
    page.text(162, 506, "Source: Super Market Strategy & Analytics Case workbook; fictitious case data.", size=8, color=GREY)
    doc.add_page(page)

    # Agenda
    page = slide_base(
        "Agenda",
        "A focused path from headline performance to recommended action.",
    )
    agenda_items = [
        ("1", "Executive takeaway", "How 2020 growth masked national share loss."),
        ("2", "Performance scorecard", "Sales, promo, e-commerce, and industry comparison."),
        ("3", "Priority focus areas", "Why Ontario/RCSS is the near-term priority and Atlantic is the playbook."),
        ("4", "Actions, KPIs, and Q&A", "Immediate workstreams, success measures, thank-you, and appendix backup."),
    ]
    y = 122
    for number, title, description in agenda_items:
        page.rect(70, y, 820, 74, fill=(248, 250, 252), stroke=MID_GREY, stroke_width=0.8)
        page.rect(94, y + 17, 40, 40, fill=BLUE)
        page.text(108, y + 27, number, size=18, bold=True, color=(255, 255, 255))
        page.text(160, y + 17, title, size=17, bold=True, color=DARK)
        page.wrapped_text(160, y + 43, description, 650, size=12, color=GREY, leading=16)
        y += 86
    doc.add_page(page)

    # Strategy slide 1
    page = slide_base(
        "Discount Division 2020: growth masked share loss",
        "Recommended discussion: use 2020 momentum to defend value while closing regional and e-commerce gaps.",
    )
    card(
        page,
        58,
        112,
        250,
        112,
        money_b(division["sales_2020"]),
        "2020 sales",
        f"Sales grew {pct(division['sales_growth'])}, but the market grew {pct(industry['sales_growth'])}.",
        BLUE,
    )
    card(
        page,
        355,
        112,
        250,
        112,
        pct(division["share_2020"]),
        "national share",
        f"Share declined {pts(division['share_delta'])} versus 2019.",
        RED,
    )
    card(
        page,
        652,
        112,
        250,
        112,
        pct(division["ecom_pen_2020"]),
        "e-commerce penetration",
        f"E-commerce sales rose {pct(division['ecom_growth'], 0)}, but penetration trails industry by {(industry['ecom_pen_2020'] - division['ecom_pen_2020']) * 100:.1f} pts.",
        BLUE,
    )
    page.rect(58, 258, 844, 52, fill=(255, 246, 232), stroke=(242, 201, 146), stroke_width=0.8)
    page.wrapped_text(
        78,
        275,
        "Recommendation: prioritize a share recovery program in Ontario/RCSS while scaling e-commerce capacity and preserving value-price credibility.",
        805,
        size=16,
        bold=True,
        color=DARK,
    )
    page.text(58, 342, "What management should take away", size=17, bold=True, color=DARK)
    page.bullet_list(
        75,
        374,
        [
            "The division captured absolute COVID-era demand, but lost relative position versus a faster-growing market.",
            "Ontario is the largest actionable issue: combined share fell about 1.0 pt and RCSS Ontario declined 9.6%.",
            "E-commerce was the biggest growth engine; closing the industry penetration gap is a near-term share lever.",
            "No Frills Atlantic is a small-base success case and should be mined for transferable execution lessons.",
        ],
        width=805,
        size=13,
    )
    doc.add_page(page)

    # Strategy slide 2
    page = slide_base(
        "Scorecard: growth was strong, relative capture weaker",
        "Core issue is not demand generation; it is relative capture of a growing market.",
    )
    page.text(60, 116, "Sales growth", size=16, bold=True, color=DARK)
    draw_bar(page, 70, 154, "Discount Division", division["sales_growth"], 0.12, BLUE)
    draw_bar(page, 70, 198, "Industry", industry["sales_growth"], 0.12, RED)
    page.text(72, 245, f"Net result: national share moved from {pct(division['share_2019'])} to {pct(division['share_2020'])}.", size=13, bold=True, color=DARK)
    page.text(72, 270, f"Change: {pts(division['share_delta'])}.", size=13, bold=True, color=RED)

    page.rect(555, 118, 340, 220, fill=(248, 250, 252), stroke=MID_GREY, stroke_width=0.8)
    page.text(575, 140, "Metric", size=11, bold=True, color=GREY)
    page.text(695, 140, "Discount", size=11, bold=True, color=GREY)
    page.text(805, 140, "Industry", size=11, bold=True, color=GREY)
    rows = [
        ("Sales growth", pct(division["sales_growth"]), pct(industry["sales_growth"])),
        ("Promo penetration", pct(division["promo_pen_2020"]), pct(industry["promo_pen_2020"])),
        ("E-com penetration", pct(division["ecom_pen_2020"]), pct(industry["ecom_pen_2020"])),
        ("E-com sales growth", pct(division["ecom_growth"], 0), pct(industry["ecom_growth"], 0)),
    ]
    y = 174
    for label, d_value, i_value in rows:
        page.text(575, y, label, size=12, color=DARK)
        page.text(705, y, d_value, size=12, bold=True, color=BLUE)
        page.text(815, y, i_value, size=12, bold=True, color=RED if label == "Sales growth" else DARK)
        y += 40

    page.text(60, 365, "Interpretation", size=16, bold=True, color=DARK)
    page.bullet_list(
        78,
        397,
        [
            "Promo penetration matched the market in 2020 and declined versus 2019, so share recovery should not rely only on deeper blanket promotion.",
            "Every discount market hit peak e-commerce sales in WE Mar 14 20, indicating a capacity and fulfillment stress test during the demand spike.",
            "E-commerce penetration is already material at 4.6%; the issue is converting rapid adoption into sustainable market-share capture.",
        ],
        width=805,
        size=12,
    )
    doc.add_page(page)

    # Strategy slide 3
    page = slide_base(
        "Focus areas: Ontario/RCSS priority; Atlantic playbook",
        "Regional lens shows the largest value pool also contains the clearest share leak.",
    )
    headers = ["Region", "2020 sales", "YoY", "Share", "Share chg.", "Readout"]
    xs = [60, 175, 290, 390, 492, 620]
    widths = [110, 105, 80, 80, 105, 275]
    y0 = 122
    page.rect(55, y0 - 8, 850, 34, fill=BLUE)
    for idx, header in enumerate(headers):
        page.text(xs[idx], y0, header, size=11, bold=True, color=(255, 255, 255))
    readouts = {
        "Atlantic": "Small base, strong momentum; mine No Frills playbook.",
        "Quebec": "Maxi grew, but lagged market share capture.",
        "Ontario": "Largest problem: combined share down and RCSS -9.6%.",
        "West": "Largest base; protect share while pushing e-com.",
    }
    row_y = 168
    for region in ["Atlantic", "Quebec", "Ontario", "West"]:
        values = regions[region]
        page.rect(55, row_y - 10, 850, 44, fill=(250, 251, 253) if row_y % 2 == 0 else (255, 255, 255), stroke=(230, 234, 238), stroke_width=0.5)
        delta_color = GREEN if values["share_delta"] >= 0 else RED
        page.text(xs[0], row_y, region, size=12, bold=True, color=DARK)
        page.text(xs[1], row_y, money_b(values["sales_2020"]), size=12, color=DARK)
        page.text(xs[2], row_y, pct(values["sales_growth"]), size=12, bold=True, color=GREEN if values["sales_growth"] > 0.1 else DARK)
        page.text(xs[3], row_y, pct(values["share_2020"]), size=12, color=DARK)
        page.text(xs[4], row_y, pts(values["share_delta"]), size=12, bold=True, color=delta_color)
        page.wrapped_text(xs[5], row_y - 1, readouts[region], widths[5], size=11, color=DARK)
        row_y += 58
    page.rect(58, 410, 398, 52, fill=(248, 250, 252), stroke=MID_GREY, stroke_width=0.8)
    page.text(78, 426, "Ontario detail", size=13, bold=True, color=DARK)
    page.text(78, 450, f"No Frills Ontario: {pct(banners['NO FRILLS ONTARIO']['sales_growth'])} sales growth.", size=11, color=DARK)
    page.text(78, 470, f"RCSS Ontario: {pct(banners['RCSS ONTARIO']['sales_growth'])} sales growth.", size=11, bold=True, color=RED)
    page.rect(504, 410, 398, 52, fill=(248, 250, 252), stroke=MID_GREY, stroke_width=0.8)
    page.text(524, 426, "E-commerce lens", size=13, bold=True, color=DARK)
    page.text(524, 450, "Division penetration: " + pct(division["ecom_pen_2020"]) + "; industry: " + pct(industry["ecom_pen_2020"]) + ".", size=11, color=DARK)
    page.text(524, 470, "Treat e-commerce as a share lever, not only a channel KPI.", size=11, color=DARK)
    doc.add_page(page)

    # Strategy slide 4
    page = slide_base(
        "Immediate actions and KPIs",
        "Breadth-first opportunity set for the leadership team; validate with store, customer, and margin detail.",
    )
    actions = [
        (
            "1. Ontario share reset",
            [
                "Deep dive RCSS Ontario stores, assortment, price gaps, and out-of-stock drivers.",
                "Localize value communication and traffic-driving categories where share loss is highest.",
                "KPI: weekly Ontario share, RCSS Ontario YoY sales, traffic, and basket size.",
            ],
            RED,
        ),
        (
            "2. E-commerce capacity",
            [
                "Expand pickup/delivery slot availability around high-demand stores and peak weeks.",
                "Improve substitution quality and availability on known online baskets.",
                "KPI: e-com penetration gap to industry, fulfillment rate, repeat online shoppers.",
            ],
            BLUE,
        ),
        (
            "3. Value and promo discipline",
            [
                "Protect key value items and sharpen promo where competitive gaps are visible.",
                "Shift from blanket depth to targeted, margin-aware offers by market and trip mission.",
                "KPI: price index, promo ROI, gross margin mix, customer retention.",
            ],
            ORANGE,
        ),
        (
            "4. Scale what works",
            [
                "Study No Frills Atlantic growth drivers: local execution, offer, labor model, and competitive context.",
                "Replicate transferable practices in comparable smaller-base markets.",
                "KPI: market-specific share lift, sales per store, and execution scorecards.",
            ],
            GREEN,
        ),
    ]
    x_positions = [58, 282, 506, 730]
    for idx, (title, bullets, color) in enumerate(actions):
        x = x_positions[idx]
        page.rect(x, 116, 196, 330, fill=(248, 250, 252), stroke=MID_GREY, stroke_width=0.8)
        page.rect(x, 116, 196, 10, fill=color)
        page.wrapped_text(x + 14, 144, title, 168, size=15, bold=True, color=DARK)
        page.bullet_list(x + 14, 194, bullets, 168, size=10, bullet_color=color)
    page.rect(58, 462, 844, 28, fill=(255, 246, 232), stroke=(242, 201, 146), stroke_width=0.8)
    page.text(75, 472, "Next data cuts: store-count normalization, margin, price index, loyalty cohorts, online capacity, and competitor density.", size=11, bold=True, color=DARK)
    doc.add_page(page)

    # Thank-you page
    page = PdfPage()
    page.rect(0, 0, page.width, page.height, fill=(255, 255, 255))
    page.rect(0, 0, 20, page.height, fill=BLUE)
    page.rect(20, 0, 8, page.height, fill=RED)
    page.rect(138, 124, 684, 2, fill=YELLOW)
    page.text(328, 176, "Thank you", size=52, bold=True, color=BLUE)
    page.wrapped_text(
        192,
        260,
        "Discussion prompts: Which Ontario diagnostic should we prioritize first? What e-commerce constraint is most urgent? What additional data would most change the recommendation?",
        600,
        size=17,
        color=DARK,
        leading=25,
    )
    page.text(338, 420, "Questions & discussion", size=18, bold=True, color=RED)
    page.text(45, 510, "Source: Super Market Strategy & Analytics Case workbook; fictitious case data.", size=8, color=GREY)
    doc.add_page(page)

    # Appendix
    page = slide_base(
        "Appendix: supporting analysis files",
        "Use these files to validate the story, answer SQL questions, and reproduce the deck.",
    )
    page.rect(50, 106, 860, 32, fill=BLUE)
    page.text(58, 116, "Supporting file", size=12, bold=True, color=(255, 255, 255))
    page.text(382, 116, "What it highlights", size=12, bold=True, color=(255, 255, 255))
    appendix_rows = [
        ("supporting_analysis.md", "Assumptions, key outputs, regional scorecard, and SQL numeric answers."),
        ("metric_summary.csv", "KPI summary by division, banner, region, and industry market."),
        ("sql_task_answers.sql", "SQL logic for the five case questions and workbook-derived outputs."),
        ("super_market_strategy_analytics_case.xlsx", "Downloaded source workbook used for all calculations."),
        ("build_loblaw_case_outputs.py", "Reproducible generator for the PDF, HTML, notes, and appendices."),
    ]
    row_y = 154
    for idx, (file_name, description) in enumerate(appendix_rows):
        page.rect(50, row_y - 10, 860, 48, fill=(250, 251, 253) if idx % 2 == 0 else (255, 255, 255), stroke=(230, 234, 238), stroke_width=0.5)
        page.text(62, row_y, file_name, size=11, bold=True, color=BLUE)
        page.wrapped_text(382, row_y - 1, description, 490, size=11, color=DARK, leading=14)
        row_y += 58
    page.text(58, 465, "Analysis notes", size=14, bold=True, color=DARK)
    page.bullet_list(
        76,
        488,
        [
            "Division row used to avoid double-counting banner rows.",
            "Recommendations are directional because margin, store-count, price-index, and customer-level data are not included.",
        ],
        width=790,
        size=10,
    )
    doc.add_page(page)

    doc.save(PDF_PATH)


def build_outputs() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    metrics = compute_metrics()
    write_metric_summary(metrics)
    write_analysis(metrics)
    write_sql(metrics)
    write_html_preview(metrics)
    write_talking_points(metrics)
    write_pdf(metrics)


if __name__ == "__main__":
    build_outputs()
