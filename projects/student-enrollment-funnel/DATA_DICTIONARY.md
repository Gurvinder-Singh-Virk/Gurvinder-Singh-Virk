# Data dictionary and assumptions

All data are fabricated. Dates are historical simulation dates, not actual student activity. Generation uses NumPy seed `20261028`.

## Prospects: one row per unique fictional visitor

| Field | Type / meaning |
| --- | --- |
| prospect_id | Unique synthetic ID; no person or identity mapping |
| first_visit | Acquisition date, uniformly drawn January 1–June 30, 2025 |
| channel | First-touch Paid Search, Paid Social, Organic Search, Email, or Referral |
| device | Desktop or Mobile, known at first visit |
| program | Business, Data Science, or Healthcare, assumed known at first visit |
| variant | A standard form or B simplified form, independent Bernoulli 50/50 assignment |
| inquiry | 1 if inquiry submitted within seven days, otherwise 0 |
| application | 1 if application after inquiry, otherwise 0 |
| admitted | 1 if admission after application, otherwise 0 |
| enrolled | 1 if enrollment after admission, otherwise 0 |
| inquiry_date | First visit + 0–6 days if inquiry=1; blank otherwise |
| application_date | Inquiry + 1–20 days if application=1; blank otherwise |
| admission_date | Application + 1–10 days if admitted=1; blank otherwise |
| enrollment_date | Admission + 1–30 days if enrolled=1; blank otherwise |

The maximum modeled path is 66 days. All cohorts receive at least 90 days of observation through September 28, 2025. Acquisition-month reporting follows visitors through that window, rather than counting enrollments by the calendar month in which they happened.

Traffic proportions: 30% paid search, 25% paid social, 22% organic, 13% email, 10% referral. Device: 43% desktop, 57% mobile. Program: 40% business, 35% data science, 25% healthcare. These are arbitrary assumptions.

Inquiry baseline is a logistic function with intercept −1.55, channel offsets [0.15, −0.25, 0.25, 0.45, 0.30] in the channel order above, program offsets [0, 0.25, 0.10], and −0.20 for mobile. B adds 0.03 to the resulting probability. Applications use a logistic function with intercept −0.10 plus channel and program offsets, conditional on inquiry. Admission probability is 0.72 conditional on application. Enrollment probability uses intercept −0.15 plus channel/program offsets, conditional on admission.

These relationships manufacture a useful demonstration. Channel rankings and treatment lift must not be represented as discovered real-world effects. All non-converters have blank later-stage dates by construction; these blanks are structural, not data errors.

## Campaign costs: one row per day × channel

| Field | Type / meaning |
| --- | --- |
| date | Daily cost date, January–June 2025 |
| channel | Same first-touch channel labels as prospects |
| spend | Synthetic USD acquisition cost, rounded to cents |

Base daily budgets are $220 paid search, $150 paid social, $80 organic, $45 email, and $30 referral, each multiplied by an independent uniform factor from 0.8 to 1.2. Organic/owned/referral budgets represent illustrative content, labor, and program costs; this is not a claim that these channels carry media charges.

All generated channel cost is assigned to this cohort universe, with no external campaigns. Cost has no device, program, or experiment allocation. Aggregate both data sources to month × channel before joining. First-touch cost per enrollment is descriptive, not a measure of incrementality, revenue, ROI, or student lifetime value.

## Output conventions

- `_rate`: proportion from 0 to 1; format as a percentage.
- `_pp`: percentage-point difference; already multiplied by 100.
- `_pct`: percentage number; already multiplied by 100.
- `cost_per_*`: USD per outcome, null when denominator is zero.
- Model odds ratios: exponentiated regularized coefficients relative to reference categories; no inferential confidence intervals are claimed.
