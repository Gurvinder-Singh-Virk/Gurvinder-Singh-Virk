-- SQLite. Count each prospect once; aggregate costs BEFORE joining.
-- Acquisition cohorts have 90 days of follow-up. Attribution: first touch.
-- name: monthly_channel
WITH audience AS (
 SELECT substr(first_visit,1,7) AS cohort_month, channel,
 COUNT(*) AS visitors, SUM(inquiry) AS inquiries,
 SUM(application) AS applications, SUM(admitted) AS admissions,
 SUM(enrolled) AS enrollments
 FROM prospects GROUP BY 1,2
), costs AS (
 SELECT substr(date,1,7) AS cohort_month, channel, SUM(spend) AS spend
 FROM campaign_costs GROUP BY 1,2
)
SELECT a.*, ROUND(c.spend,2) AS spend,
 1.0*inquiries/visitors AS inquiry_rate,
 1.0*enrollments/visitors AS enrollment_rate,
 c.spend/NULLIF(inquiries,0) AS cost_per_inquiry,
 c.spend/NULLIF(enrollments,0) AS cost_per_enrollment
FROM audience a JOIN costs c USING(cohort_month,channel)
ORDER BY cohort_month, channel;

-- name: experiment_counts
SELECT variant, COUNT(*) AS visitors, SUM(inquiry) AS inquiries,
 1.0*SUM(inquiry)/COUNT(*) AS inquiry_rate
FROM prospects GROUP BY variant ORDER BY variant;

-- name: segment_funnel
SELECT substr(first_visit,1,7) AS cohort_month, channel, device, program,
 COUNT(*) AS visitors, SUM(inquiry) AS inquiries,
 SUM(application) AS applications, SUM(admitted) AS admissions,
 SUM(enrolled) AS enrollments
FROM prospects GROUP BY 1,2,3,4 ORDER BY 1,2,3,4;
