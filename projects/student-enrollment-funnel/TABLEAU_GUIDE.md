# Tableau dashboard build guide

**Status: data and specification ready; native Tableau workbook/publication not yet created.**

The included static report is generated in Python. It is not a Tableau dashboard. Tableau accepts CSV text files: [official connection documentation](https://help.tableau.com/current/pro/desktop/en-us/examples_text.htm).

## Files and grains

| File | One row represents | Use |
| --- | --- | --- |
| `tableau/monthly_channel.csv` | Acquisition month × first-touch channel | Overview, trends, channel costs |
| `tableau/funnel_long.csv` | Acquisition month × channel × stage | Funnel counts |
| `tableau/segment_funnel.csv` | Month × channel × device × program | Segment drill-down; no cost fields |
| `tableau/experiment_results.csv` | One randomized variant | Full-sample experiment; no cohort/channel filters |
| `tableau/experiment_counts.csv` | One randomized variant | Raw experiment denominators |

Use separate data sources for these files. Do **not** physically join them: different grains would duplicate spend and counts. Do not add device/program filters to campaign costs because spend has no device/program attribution. Do not apply dashboard cohort/channel filters to the fixed full-sample experiment results.

## Workbook layout

Create three dashboard tabs, 1200 × 850 pixels. Use navy `#174B66`, teal `#24A69B`, and light gray `#EDF3F7`. Add this subtitle to each: **Synthetic university data · simulated experiment · independent case study**.

### 1. Executive overview

Connect to `monthly_channel.csv` using the Text File connector (or upload CSV in web authoring). Treat `cohort_month` as a date by converting `YYYY-MM` to a month-start date, or retain it as a discrete string sorted ascending. Treat counts and spend as numeric measures.

- KPI cards: SUM(visitors), SUM(inquiries), SUM(enrollments), enrollment rate, cost per enrollment.
- Line chart: cohort month on Columns, enrollment rate on Rows.
- Horizontal bar chart: channel on Rows, cost per enrollment on Columns; sort ascending.
- Tooltip: spend, visitor count, enrollments, and rate.
- Filters: cohort month and channel, applied to worksheets using this source.

Calculated fields (compute ratios from totals, **never average monthly rates**):

```text
Enrollment Rate = SUM([enrollments]) / SUM([visitors])
Inquiry Rate = SUM([inquiries]) / SUM([visitors])
Cost per Inquiry = IF SUM([inquiries]) > 0 THEN SUM([spend]) / SUM([inquiries]) END
Cost per Enrollment = IF SUM([enrollments]) > 0 THEN SUM([spend]) / SUM([enrollments]) END
```

Format rates as percentages, spend/CPE as currency, counts as integers.

### 2. Enrollment funnel

Connect separately to `funnel_long.csv`. Put stage on Rows, SUM(prospects) on Columns, and sort by MIN(stage_order), ascending. Use bars with count labels. Filter by cohort month and channel.

Stage counts are nested, so **SUM(prospects) across stages is not a population total**. Do not create a KPI from that sum. Use the overview source for total visitors.

For a second worksheet use `monthly_channel.csv`, with these calculated fields:

```text
Inquiry to Application = SUM([applications]) / SUM([inquiries])
Application to Admission = SUM([admissions]) / SUM([applications])
Admission to Enrollment = SUM([enrollments]) / SUM([admissions])
```

Guard against zero denominators with the IF pattern above. Keep filters aligned manually across the two sources. Use `segment_funnel.csv` for an optional device/program view and state that cost is unavailable at this grain.

### 3. Simulated experiment

Connect to `experiment_results.csv` separately. Show variant on Columns and MIN(inquiry_rate) on Rows. Add rate_ci_low/high as reference bands or an interval worksheet. Include visitor and inquiry denominators in tooltips.

The overall difference, p-value, and SRM fields are repeated on both rows. Display **MIN**, not SUM, for these summary fields. Difference/lower/upper fields ending `_pp` are already in percentage points: show as plain numbers with a `pp` label, **not** percentage formatting. `relative_lift_pct` is already a percentage number (17.98), so label it `%` without multiplying by 100. Rates ending `_rate` are proportions and should use percentage formatting.

Display the difference interval, two-sided p-value, and sample-ratio-mismatch p-value. Add a prominent note: **Treatment uplift is encoded in synthetic data; this is not a real experiment.** Keep this dashboard unfiltered; segment inference would require a separate analysis plan.

## Acceptance checks

With no filters, the dashboard must show 10,000 visitors, 2,100 inquiries, 454 enrollments, $94,760.04 spend, and 4.54% enrollment conversion. Overall cost per enrollment should be $208.72.

The experiment must show A: 4,979 visitors / 959 inquiries (19.26%) and B: 5,021 / 1,141 (22.72%). B minus A is 3.46 pp, with a 95% interval of 1.87–5.06 pp. Compare exact values with `results/metrics.json`.

Before publishing, verify a single-channel filter by summing its six monthly rows. Ensure the experiment does not change when overview filters change. Confirm tooltips show denominators and synthetic-data labels remain visible.

Save the workbook and publish from your own Tableau account when verified. Add its real link to the project README only after publication. [Tableau Public FAQ](https://help.tableau.com/current/pro/desktop/en-us/public_faq.htm).
