# Business brief: Student Enrollment Funnel & A/B Testing

**Independent portfolio case study · synthetic data · simulated experiment**

## Executive findings

- Analyzed 10,000 fictional prospects acquired January–June 2025, each with 90 days of follow-up through September 28, 2025.
- Observed 2,100 inquiries and 454 enrollments: 4.54% visitor-to-enrollment conversion.
- Illustrative acquisition costs totaled $94,760.04, or $208.72 per enrollment.
- Email had the lowest modeled cost per enrollment ($78.14). Costs include assigned content/labor budgets for owned channels.
- Simulated form B converted 22.72% versus 19.26% for A: 3.46 percentage points (18.0% relative lift).
- The 95% interval for B minus A was [1.87, 5.06] percentage points; two-sided p=0.00002. Allocation check p=0.6745. Decision: **positive simulated effect**.

## Interpretation and next decisions

The visitor-to-inquiry stage has the greatest proportional loss. Investigate landing-page relevance and form friction first. The simulated experiment illustrates how to evaluate a simplified form; a real rollout would require an actual randomized test and downstream enrollment/lead-quality guardrails. No real university should change its budget based on these synthetic results.

Channel comparisons are descriptive. First-touch attribution and assumed budgets determine the apparent efficiency; they do not measure incremental marketing impact. A practical next step would be a small real-world channel experiment, with cost and enrollment tracked over a full follow-up window.

## Regression evaluation

L2-regularized logistic regression used channel, device, program, and assigned variant—all available at first visit. The split was fixed at 75% train / 25% test and stratified by enrollment. No inquiry/application/admission features were used, avoiding outcome leakage.

- Held-out set: 2,500 prospects, 114 enrollments; prevalence 4.56%.
- ROC AUC: 0.631; average precision: 0.079 (prevalence reference: 0.046).
- Brier score: 0.0431, versus intercept-only baseline 0.0435; lower is better.
- Log loss: 0.1807, versus baseline 0.1854; lower is better.

Predictive discrimination is limited. This model is an explanatory portfolio baseline, not suitable for automated admissions or outreach decisions. Coefficients describe associations within the simulation; regularized odds ratios are not causal effects or significance tests. Reference categories: {"channel": "Email", "device": "Desktop", "program": "Business", "variant": "A"}.

## Experiment methods and limits

The analysis plan is declared in code before data generation: unique-prospect randomization, 50/50 assignment, inquiry within seven days as the sole primary outcome, fixed N=10,000, two-sided alpha=.05, and a sample-ratio-mismatch threshold of .01. A planning approximation for a 20% baseline, 3-point absolute effect, and 80% power calls for 2,943 prospects per arm; this is an assumption-based calculation, not post-hoc power.

The comparison uses a pooled two-proportion z test. Individual rate bounds use Wilson intervals; the difference uses Newcombe's combination of Wilson bounds. No multiple post-hoc subgroup tests or outcome-driven reruns were used. The seed is fixed. The generator explicitly encodes a 3-point inquiry uplift for B, so this exercise demonstrates correct analysis of an assumed mechanism, not evidence that a real form works.

## Validation

Checks passed for unique prospects, mandatory fields, binary outcomes, ordered stage timestamps, seven-day inquiry outcomes, complete 90-day follow-up, unique daily channel costs, SQL/Pandas stage-count reconciliation, exact spend reconciliation within rounding tolerance, and disjoint train/test records. See validation.json and automated tests.

## Delivery status

Python analysis, SQL, reproducible data, notebook, static results, and Tableau-ready exports are complete. A native Tableau workbook and Tableau Public publication are **not yet created**. The dashboard guide documents the remaining authoring steps.
