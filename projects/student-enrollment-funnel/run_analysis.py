"""Reproducible synthetic enrollment case study. Run from any directory.

This is a simulation, not an actual university campaign or deployed experiment.
All output paths are relative to this script. Requires Python 3.11+.
"""
from pathlib import Path
import gzip
import html
import json
import re
import sqlite3
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import expit
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss

ROOT = Path(__file__).resolve().parent
SEED, N = 20261028, 10000
CHANNELS = ['Paid Search', 'Paid Social', 'Organic Search', 'Email', 'Referral']
STAGES = ['visitors', 'inquiries', 'applications', 'admissions', 'enrollments']
EXPERIMENT = {
 'unit': 'unique synthetic prospect', 'allocation': 'independent 50/50 Bernoulli',
 'primary_outcome': 'inquiry within 7 days of first visit',
 'control': 'A: standard form', 'treatment': 'B: simplified form',
 'sample_size': N, 'alpha': 0.05, 'srm_threshold': 0.01,
 'test': 'two-sided pooled two-proportion z test',
 'difference_ci': '95% Newcombe interval from Wilson score bounds',
 'analysis': 'intention-to-treat, fixed sample; no peeking or subgroup significance claims',
 'cohort_start': '2025-01-01', 'cohort_end': '2025-06-30',
 'followup_days': 90, 'data_cutoff': '2025-09-28',
 'planning_assumptions': '20% baseline; 3 percentage-point absolute MDE; 80% power',
}


def generate():
    rng = np.random.default_rng(SEED)
    p = pd.DataFrame({'prospect_id': [f'P{i:05d}' for i in range(1, N+1)]})
    p['first_visit'] = pd.Timestamp('2025-01-01') + pd.to_timedelta(rng.integers(0,181,N),unit='D')
    p['channel'] = rng.choice(CHANNELS,N,p=[.30,.25,.22,.13,.10])
    p['device'] = rng.choice(['Desktop','Mobile'],N,p=[.43,.57])
    p['program'] = rng.choice(['Business','Data Science','Healthcare'],N,p=[.40,.35,.25])
    p['variant'] = np.where(rng.random(N)<.5,'A','B')
    # Assumed relationships are deliberately encoded, not discovered market facts.
    channel_effect = p.channel.map(dict(zip(CHANNELS,[.15,-.25,.25,.45,.30])))
    program_effect = p.program.map({'Business':0,'Data Science':.25,'Healthcare':.10})
    inquiry_prob = np.clip(expit(-1.55+channel_effect+program_effect-.20*(p.device=='Mobile'))
                           +.03*(p.variant=='B'),.01,.99)
    p['inquiry'] = (rng.random(N)<inquiry_prob).astype(int)
    p['application'] = (p.inquiry.astype(bool) & (rng.random(N)<expit(-.10+channel_effect+program_effect))).astype(int)
    p['admitted'] = (p.application.astype(bool) & (rng.random(N)<.72)).astype(int)
    p['enrolled'] = (p.admitted.astype(bool) & (rng.random(N)<expit(-.15+channel_effect+program_effect))).astype(int)
    previous = p.first_visit
    for flag, col, low, high in [('inquiry','inquiry_date',0,7),('application','application_date',1,21),
                                  ('admitted','admission_date',1,11),('enrolled','enrollment_date',1,31)]:
        dates = previous+pd.to_timedelta(rng.integers(low,high,N),unit='D')
        p[col] = dates.where(p[flag].eq(1))
        previous = p[col]
    costs = []
    # Independent illustrative daily budgets; owned/organic channels include content/labor cost.
    for date in pd.date_range('2025-01-01','2025-06-30'):
        for channel, base in zip(CHANNELS,[220,150,80,45,30]):
            costs.append((date,channel,round(float(base*rng.uniform(.8,1.2)),2)))
    c = pd.DataFrame(costs,columns=['date','channel','spend'])
    return p,c


def validate(p,c):
    assert len(p)==N and p.prospect_id.is_unique, 'Duplicate/missing prospects'
    assert not p[['prospect_id','first_visit','channel','device','program','variant']].isna().any().any()
    assert set(p.variant)=={'A','B'}
    assert p.first_visit.between('2025-01-01','2025-06-30').all()
    assert (pd.Timestamp(EXPERIMENT['data_cutoff'])-p.first_visit).dt.days.ge(90).all()
    previous = pd.Series(1,index=p.index)
    previous_date = p.first_visit
    for flag,col in [('inquiry','inquiry_date'),('application','application_date'),('admitted','admission_date'),('enrolled','enrollment_date')]:
        assert p[flag].isin([0,1]).all() and p[flag].le(previous).all(), 'Broken funnel hierarchy'
        assert p[col].notna().equals(p[flag].eq(1)), 'Date/flag disagreement'
        assert (p.loc[p[flag].eq(1),col]>=previous_date.loc[p[flag].eq(1)]).all()
        assert ((p.loc[p[flag].eq(1),col]-p.loc[p[flag].eq(1),'first_visit']).dt.days<=90).all()
        previous,previous_date = p[flag],p[col]
    assert (p.loc[p.inquiry.eq(1),'inquiry_date']-p.loc[p.inquiry.eq(1),'first_visit']).dt.days.lt(7).all()
    assert len(c)==181*len(CHANNELS) and not c.duplicated(['date','channel']).any()
    assert c.spend.ge(0).all() and c.spend.notna().all()


def sql_exports(p,c):
    conn = sqlite3.connect(ROOT/'data/enrollment.sqlite')
    p.to_sql('prospects',conn,if_exists='replace',index=False)
    c.to_sql('campaign_costs',conn,if_exists='replace',index=False)
    queries = re.findall(r'-- name: (\w+)\n(.*?;)',(ROOT/'analysis.sql').read_text(),re.S)
    tables = {name:pd.read_sql_query(query,conn) for name,query in queries}
    conn.close()
    m = tables['monthly_channel']
    # Independently reconcile SQL totals against row-level Pandas counts and source spend.
    assert int(m.visitors.sum())==len(p)
    for source,target in [('inquiry','inquiries'),('application','applications'),('admitted','admissions'),('enrolled','enrollments')]:
        assert int(m[target].sum())==int(p[source].sum())
    assert np.isclose(m.spend.sum(),c.spend.sum(),atol=.005)
    check=p.assign(cohort_month=p.first_visit.dt.strftime('%Y-%m')).groupby(['cohort_month','channel']).enrolled.sum()
    assert m.set_index(['cohort_month','channel']).enrollments.sort_index().equals(check.sort_index().rename('enrollments'))
    for name,t in tables.items():
        t.to_csv(ROOT/f'tableau/{name}.csv',index=False,float_format='%.8f')
    long = m.melt(id_vars=['cohort_month','channel'],value_vars=STAGES,var_name='stage',value_name='prospects')
    long['stage_order']=long.stage.map({s:i+1 for i,s in enumerate(STAGES)})
    long.to_csv(ROOT/'tableau/funnel_long.csv',index=False)
    return tables


def experiment(p):
    groups = p.groupby('variant').inquiry.agg(['count','sum']).reindex(['A','B'])
    n=groups['count'].to_numpy(); k=groups['sum'].to_numpy(); rate=k/n
    pooled=k.sum()/n.sum()
    se=np.sqrt(pooled*(1-pooled)*np.sum(1/n))
    z=(rate[1]-rate[0])/se
    pvalue=float(2*stats.norm.sf(abs(z)))
    bounds=[stats.binomtest(int(ki),int(ni)).proportion_ci(method='wilson') for ki,ni in zip(k,n)]
    diff=float(rate[1]-rate[0])
    low=diff-np.sqrt((rate[1]-bounds[1].low)**2+(bounds[0].high-rate[0])**2)
    high=diff+np.sqrt((bounds[1].high-rate[1])**2+(rate[0]-bounds[0].low)**2)
    srm=float(stats.chisquare(n,f_exp=np.repeat(n.sum()/2,2)).pvalue)
    z_alpha=stats.norm.ppf(.975); z_power=stats.norm.ppf(.8)
    baseline,other=.20,.23; mean=(baseline+other)/2
    planned=int(np.ceil(((z_alpha*np.sqrt(2*mean*(1-mean))+z_power*np.sqrt(baseline*(1-baseline)+other*(1-other)))**2)/(.03**2)))
    summary={'control_n':int(n[0]),'treatment_n':int(n[1]),'control_inquiries':int(k[0]),'treatment_inquiries':int(k[1]),
             'control_rate':float(rate[0]),'treatment_rate':float(rate[1]),'absolute_lift_pp':diff*100,
             'relative_lift_pct':float(diff/rate[0]*100),'ci_low_pp':float(low*100),'ci_high_pp':float(high*100),
             'z_statistic':float(z),'p_value':pvalue,'srm_p_value':srm,'planned_n_per_arm':planned,
             'decision':'positive simulated effect' if pvalue<.05 and diff>0 and srm>=.01 else 'inconclusive or failed allocation check'}
    rows=[]
    for i,variant in enumerate(['A','B']):
        rows.append({'variant':variant,'visitors':int(n[i]),'inquiries':int(k[i]),'inquiry_rate':rate[i],
                     'rate_ci_low':bounds[i].low,'rate_ci_high':bounds[i].high,**summary})
    pd.DataFrame(rows).to_csv(ROOT/'tableau/experiment_results.csv',index=False,float_format='%.8f')
    # Descriptive allocation balance. Do not run post-hoc subgroup outcome tests.
    balance=[]
    for feature in ['channel','device','program']:
        ct=pd.crosstab(p[feature],p.variant)
        for level,row in ct.iterrows():
            balance.append({'feature':feature,'level':level,'A_n':int(row.A),'B_n':int(row.B),
                            'A_share':row.A/n[0],'B_share':row.B/n[1]})
    pd.DataFrame(balance).to_csv(ROOT/'results/randomization_balance.csv',index=False,float_format='%.8f')
    return summary


def regression(p):
    features=['channel','device','program','variant']
    X=p[features]; y=p.enrolled
    train,test=train_test_split(np.arange(len(p)),test_size=.25,random_state=SEED,stratify=y)
    encoder=ColumnTransformer([('categories',OneHotEncoder(drop='first',handle_unknown='error'),features)])
    model=make_pipeline(encoder,LogisticRegression(max_iter=2000,C=1.0,solver='lbfgs'))
    model.fit(X.iloc[train],y.iloc[train])
    pred=model.predict_proba(X.iloc[test])[:,1]
    baseline=np.full(len(test),y.iloc[train].mean())
    metrics={'train_n':len(train),'test_n':len(test),'test_enrollments':int(y.iloc[test].sum()),
             'test_prevalence':float(y.iloc[test].mean()),'roc_auc':float(roc_auc_score(y.iloc[test],pred)),
             'average_precision':float(average_precision_score(y.iloc[test],pred)),
             'brier_score':float(brier_score_loss(y.iloc[test],pred)),
             'baseline_brier':float(brier_score_loss(y.iloc[test],baseline)),
             'log_loss':float(log_loss(y.iloc[test],pred)), 'baseline_log_loss':float(log_loss(y.iloc[test],baseline))}
    names=model[0].get_feature_names_out()
    coefs=model[1].coef_[0]
    rows=pd.DataFrame({'feature':names,'coefficient':coefs,'odds_ratio':np.exp(coefs)})
    rows.to_csv(ROOT/'results/model_coefficients.csv',index=False,float_format='%.8f')
    refs={feature:str(cats[0]) for feature,cats in zip(features,model[0].named_transformers_['categories'].categories_)}
    metrics['reference_categories']=refs
    assert not set(train)&set(test) and len(train)+len(test)==N
    assert 0<=metrics['roc_auc']<=1 and np.isfinite(pred).all()
    return metrics


def charts(tables,ab):
    plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold'})
    m=tables['monthly_channel']; totals=m[STAGES].sum()
    fig,axs=plt.subplots(1,3,figsize=(16,5),layout='constrained')
    fig.suptitle('Student enrollment analytics | SYNTHETIC DATA',fontsize=19,fontweight='bold')
    axs[0].barh([s.title() for s in STAGES],totals,color=['#174b66','#206684','#2b85a0','#47a5b5','#77c9c7'])
    axs[0].invert_yaxis(); axs[0].set_title('Enrollment funnel'); axs[0].set_xlabel('Prospects')
    for i,v in enumerate(totals): axs[0].text(v+100,i,f'{v:,}',va='center',fontsize=10)
    axs[0].set_xlim(0,N*1.25)
    channel=m.groupby('channel')[['spend','enrollments']].sum()
    cpe=(channel.spend/channel.enrollments).sort_values()
    axs[1].barh(cpe.index,cpe,color='#206684');axs[1].invert_yaxis()
    axs[1].set_title('Cost per enrollment');axs[1].set_xlabel('Illustrative cost ($)')
    rates=np.array([ab['control_rate'],ab['treatment_rate']])*100
    axs[2].bar(['A: standard','B: simplified'],rates,color=['#a2b5c2','#24a69b'])
    axs[2].set_title('Simulated form experiment');axs[2].set_ylabel('7-day inquiry conversion (%)')
    axs[2].set_ylim(0,max(rates)*1.35)
    for i,v in enumerate(rates):axs[2].text(i,v+.5,f'{v:.2f}%',ha='center')
    fig.savefig(ROOT/'results/overview.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3),layout='constrained')
    ax.errorbar(ab['absolute_lift_pp'],0,xerr=[[ab['absolute_lift_pp']-ab['ci_low_pp']],[ab['ci_high_pp']-ab['absolute_lift_pp']]],fmt='o',capsize=8,color='#206684')
    ax.axvline(0,color='#777',ls='--');ax.set_yticks([])
    ax.set_xlabel('B minus A inquiry conversion (percentage points)')
    ax.set_title('Simulated A/B test | 95% Newcombe confidence interval')
    fig.savefig(ROOT/'results/experiment_interval.png',dpi=160);plt.close(fig)


def write_report(tables,ab,model):
    m=tables['monthly_channel']; totals=m[STAGES].sum(); spend=float(m.spend.sum())
    c=m.groupby('channel')[['spend','visitors','inquiries','enrollments']].sum()
    c['cost_per_enrollment']=c.spend/c.enrollments
    best=c.cost_per_enrollment.idxmin()
    report=f'''# Business brief: Student Enrollment Funnel & A/B Testing

**Independent portfolio case study · synthetic data · simulated experiment**

## Executive findings

- Analyzed {N:,} fictional prospects acquired January–June 2025, each with 90 days of follow-up through September 28, 2025.
- Observed {int(totals.inquiries):,} inquiries and {int(totals.enrollments):,} enrollments: {totals.enrollments/N:.2%} visitor-to-enrollment conversion.
- Illustrative acquisition costs totaled ${spend:,.2f}, or ${spend/totals.enrollments:,.2f} per enrollment.
- {best} had the lowest modeled cost per enrollment (${c.loc[best,'cost_per_enrollment']:,.2f}). Costs include assigned content/labor budgets for owned channels.
- Simulated form B converted {ab['treatment_rate']:.2%} versus {ab['control_rate']:.2%} for A: {ab['absolute_lift_pp']:.2f} percentage points ({ab['relative_lift_pct']:.1f}% relative lift).
- The 95% interval for B minus A was [{ab['ci_low_pp']:.2f}, {ab['ci_high_pp']:.2f}] percentage points; two-sided p={ab['p_value']:.5f}. Allocation check p={ab['srm_p_value']:.4f}. Decision: **{ab['decision']}**.

## Interpretation and next decisions

The visitor-to-inquiry stage has the greatest proportional loss. Investigate landing-page relevance and form friction first. The simulated experiment illustrates how to evaluate a simplified form; a real rollout would require an actual randomized test and downstream enrollment/lead-quality guardrails. No real university should change its budget based on these synthetic results.

Channel comparisons are descriptive. First-touch attribution and assumed budgets determine the apparent efficiency; they do not measure incremental marketing impact. A practical next step would be a small real-world channel experiment, with cost and enrollment tracked over a full follow-up window.

## Regression evaluation

L2-regularized logistic regression used channel, device, program, and assigned variant—all available at first visit. The split was fixed at 75% train / 25% test and stratified by enrollment. No inquiry/application/admission features were used, avoiding outcome leakage.

- Held-out set: {model['test_n']:,} prospects, {model['test_enrollments']} enrollments; prevalence {model['test_prevalence']:.2%}.
- ROC AUC: {model['roc_auc']:.3f}; average precision: {model['average_precision']:.3f} (prevalence reference: {model['test_prevalence']:.3f}).
- Brier score: {model['brier_score']:.4f}, versus intercept-only baseline {model['baseline_brier']:.4f}; lower is better.
- Log loss: {model['log_loss']:.4f}, versus baseline {model['baseline_log_loss']:.4f}; lower is better.

Predictive discrimination is limited. This model is an explanatory portfolio baseline, not suitable for automated admissions or outreach decisions. Coefficients describe associations within the simulation; regularized odds ratios are not causal effects or significance tests. Reference categories: {json.dumps(model['reference_categories'],sort_keys=True)}.

## Experiment methods and limits

The analysis plan is declared in code before data generation: unique-prospect randomization, 50/50 assignment, inquiry within seven days as the sole primary outcome, fixed N={N:,}, two-sided alpha=.05, and a sample-ratio-mismatch threshold of .01. A planning approximation for a 20% baseline, 3-point absolute effect, and 80% power calls for {ab['planned_n_per_arm']:,} prospects per arm; this is an assumption-based calculation, not post-hoc power.

The comparison uses a pooled two-proportion z test. Individual rate bounds use Wilson intervals; the difference uses Newcombe's combination of Wilson bounds. No multiple post-hoc subgroup tests or outcome-driven reruns were used. The seed is fixed. The generator explicitly encodes a 3-point inquiry uplift for B, so this exercise demonstrates correct analysis of an assumed mechanism, not evidence that a real form works.

## Validation

Checks passed for unique prospects, mandatory fields, binary outcomes, ordered stage timestamps, seven-day inquiry outcomes, complete 90-day follow-up, unique daily channel costs, SQL/Pandas stage-count reconciliation, exact spend reconciliation within rounding tolerance, and disjoint train/test records. See validation.json and automated tests.

## Delivery status

Python analysis, SQL, reproducible data, notebook, static results, and Tableau-ready exports are complete. A native Tableau workbook and Tableau Public publication are **not yet created**. The dashboard guide documents the remaining authoring steps.
'''
    (ROOT/'results/business_brief.md').write_text(report)
    # Standalone static report: exact computed outputs; no dashboard publishing claim.
    body=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Student enrollment analytics</title>
<style>body{{margin:0;background:#edf3f7;color:#17334a;font:16px/1.6 system-ui}}main{{max-width:1120px;margin:40px auto;padding:32px;background:white;border-radius:16px}}h1{{font-size:34px;line-height:1.2}}.tag{{color:#15766b;font-weight:700;letter-spacing:.08em}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px}}.card{{padding:20px;background:#edf5f7;border-radius:10px}}strong{{font-size:28px;display:block}}img{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:10px;text-align:right;border-bottom:1px solid #ddd}}td:first-child,th:first-child{{text-align:left}}a{{color:#176b85}}@media(max-width:700px){{main{{margin:0;padding:18px}}h1{{font-size:27px}}table{{font-size:11px}}td,th{{padding:5px}}}}</style><main>
<p class="tag">INDEPENDENT CASE STUDY · SYNTHETIC DATA</p><h1>From first visit to enrollment</h1>
<p>Marketing funnel performance and a simulated randomized form experiment. Acquisition: January–June 2025; 90-day follow-up.</p>
<div class="grid"><div class="card">Visitors<strong>{N:,}</strong></div><div class="card">Enrollments<strong>{int(totals.enrollments):,}</strong></div><div class="card">Enrollment rate<strong>{totals.enrollments/N:.2%}</strong></div><div class="card">Cost / enrollment<strong>${spend/totals.enrollments:,.2f}</strong></div></div>
<img src="overview.png" alt="Enrollment funnel, cost per enrollment by channel, and simulated experiment conversion rates">
<h2>Does a simpler form improve inquiries?</h2><p>Form B: {ab['treatment_rate']:.2%}; form A: {ab['control_rate']:.2%}. Difference: <b>{ab['absolute_lift_pp']:.2f} percentage points</b> ({ab['relative_lift_pct']:.1f}% relative). 95% interval: {ab['ci_low_pp']:.2f} to {ab['ci_high_pp']:.2f} points. Two-sided p={ab['p_value']:.5f}.</p>
<img src="experiment_interval.png" alt="Confidence interval for treatment-minus-control conversion difference">
<h2>Channel economics</h2>{c.round(2).to_html(border=0)}
<h2>What to do next</h2><p>Investigate visitor-to-inquiry friction. In a real setting, validate the form with a randomized test and enrollment-quality guardrails. Compare channels using incremental impact before changing budgets.</p>
<h2>Model quality</h2><p>Held-out ROC AUC {model['roc_auc']:.3f}; average precision {model['average_precision']:.3f}; enrollment prevalence {model['test_prevalence']:.3f}. Brier score {model['brier_score']:.4f}, versus baseline {model['baseline_brier']:.4f}. The model has limited discrimination and is a baseline, not a deployed decision system.</p>
<h2>Read this honestly</h2><p>All prospects and costs are fabricated. A treatment effect is intentionally encoded in the generator. These results demonstrate analytical methods and are not measured business impact. This is a static Python report; a Tableau workbook/publication remains to be authored.</p>
<p><a href="business_brief.md">Business brief</a> · <a href="../TABLEAU_GUIDE.md">Tableau build guide</a> · <a href="../README.md">Methods and reproduction</a></p></main></html>'''
    (ROOT/'results/report.html').write_text(body)
    return {'prospects':N,'inquiries':int(totals.inquiries),'enrollments':int(totals.enrollments),'spend':spend,'best_channel':best,'best_channel_cpe':float(c.loc[best,'cost_per_enrollment'])}


def main():
    for d in ['data','tableau','results']: (ROOT/d).mkdir(exist_ok=True)
    (ROOT/'results/experiment_plan.json').write_text(json.dumps(EXPERIMENT,indent=2)+'\n')
    p,c=generate();validate(p,c)
    p.to_csv(ROOT/'data/prospects.csv',index=False,date_format='%Y-%m-%d')
    c.to_csv(ROOT/'data/campaign_costs.csv',index=False,date_format='%Y-%m-%d')
    # Deterministic compressed raw data is also committed for direct download.
    for filename in ['prospects.csv','campaign_costs.csv']:
        with open(ROOT/f'data/{filename}.gz','wb') as stream:
            stream.write(gzip.compress((ROOT/f'data/{filename}').read_bytes(),mtime=0))
    tables=sql_exports(p,c);ab=experiment(p);model=regression(p);charts(tables,ab)
    overview=write_report(tables,ab,model)
    results={'seed':SEED,'overview':overview,'experiment':ab,'model':model}
    (ROOT/'results/metrics.json').write_text(json.dumps(results,indent=2)+'\n')
    (ROOT/'results/validation.json').write_text(json.dumps({'passed':True,'checks':['unique prospect IDs','required fields','binary and nested stages','ordered stage dates','7-day inquiry window','90-day cohort maturity','unique daily channel costs','SQL/Pandas stage reconciliation','SQL/Pandas group reconciliation','no duplicated spend','disjoint model split'],'prospect_rows':len(p),'cost_rows':len(c)},indent=2)+'\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
