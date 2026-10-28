# Student Enrollment Funnel & A/B Testing Dashboard

**Status: Planned — implementation has not started.**

An independent portfolio project for a fictional online university, designed to explore enrollment funnels, marketing channel efficiency, and a simulated landing-page experiment.

## Business questions

- Which marketing channels generate inquiries and enrollments at the lowest cost?
- Where do prospective students drop out between their first visit and enrollment?
- Does a simplified inquiry form change visitor-to-inquiry conversion in a simulated randomized experiment?
- How do channel, device, and program relate to enrollment probability?

## Planned data

Generate a reproducible synthetic dataset of approximately 10,000 fictional prospective students over six months. This is a target dataset size, not a completed analysis count.

- Prospect table: anonymous prospect ID, first-visit date, first-touch channel, campaign, device, program, experiment assignment, and funnel-stage timestamps.
- Campaign cost table: date, campaign, channel, and spend.
- No real student records or personal information.
- Document the data-generation assumptions, random seed, observation window, and missing-data rules.

Use one row per prospect for conversion denominators. Keep campaign spend at its original grain to avoid duplicating costs when joining prospect records. Define channel attribution explicitly as first touch. Give cohorts equal follow-up time before comparing enrollment rates.

## Planned implementation

| Component | Planned work |
| --- | --- |
| SQL | Validate data, calculate stage conversion and drop-off, summarize cohorts, and calculate cost per inquiry and enrollment. |
| Python | Generate data, check quality, analyze the simulated experiment, and fit a logistic regression. |
| Statistics | Report the experiment's conversion rates, absolute percentage-point difference, relative lift, confidence interval, and hypothesis-test result. |
| Regression | Examine enrollment associations using only pre-outcome features; use a held-out evaluation set and report model limitations. |
| Tableau | Build executive overview, funnel/channel, and experiment dashboard views with date, channel, and program filters. |

## Simulated experiment design

- Unit of randomization: unique prospect, with persistent assignment.
- Control: standard inquiry form.
- Treatment: simplified inquiry form.
- Primary outcome: inquiry submitted within a predefined window after first visit.
- Assign the variant before generating outcomes; keep assignment independent of channel and device.
- Specify sample size, analysis window, significance threshold, and test before inspecting results.
- Check assignment balance and sample-ratio mismatch.
- Analyze prospects in their assigned groups; report uncertainty even if the result is inconclusive.
- Synthetic findings demonstrate analysis methods and do not establish real-world causal impact.

## Planned deliverables

- Reproducible data-generation script and data dictionary.
- SQL analysis queries and Python notebook.
- Tableau-ready CSV exports.
- Tableau workbook and a Tableau Public link once published.
- A short business brief with computed findings, limitations, and recommendations.

## Completion criteria

- [ ] Generate and validate synthetic data.
- [ ] Complete SQL funnel and campaign-cost analysis.
- [ ] Complete the simulated A/B test with uncertainty estimates.
- [ ] Fit and evaluate logistic regression.
- [ ] Build and verify the Tableau dashboard.
- [ ] Publish reproducible analysis and document findings.

## Honest portfolio presentation

This page is a project proposal. No completed dashboard, measured lift, cost savings, or business results are claimed. SQL, Python, and Tableau are the planned stack, not evidence of completed work. Adobe Analytics, Google Analytics, and Databricks are not part of this proposal.

When implementation is complete, replace planned descriptions with verified work and calculated results. Keep the synthetic-data and simulated-experiment disclosures visible.
