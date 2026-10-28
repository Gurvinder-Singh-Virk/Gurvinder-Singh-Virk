"""Independent checks for the analytical risks in this case study."""
import re
import sqlite3
import unittest

import numpy as np
import pandas as pd
from scipy import stats
import run_analysis as analysis


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p,cls.c=analysis.generate()

    def test_seed_reproduces_every_record(self):
        p,c=analysis.generate()
        pd.testing.assert_frame_equal(self.p,p)
        pd.testing.assert_frame_equal(self.c,c)

    def test_complete_followup_and_stage_integrity(self):
        analysis.validate(self.p,self.c)

    def test_duplicate_prospect_is_rejected(self):
        p=self.p.copy();p.loc[1,'prospect_id']=p.loc[0,'prospect_id']
        with self.assertRaises(AssertionError):analysis.validate(p,self.c)

    def test_impossible_stage_is_rejected(self):
        p=self.p.copy();idx=p.index[p.inquiry.eq(0)][0]
        p.loc[idx,'enrolled']=1
        with self.assertRaises(AssertionError):analysis.validate(p,self.c)

    def test_spend_is_not_multiplied_and_zero_denominators_are_null(self):
        # Two visitors on one channel; two spend rows. Naive joining would double costs.
        conn=sqlite3.connect(':memory:')
        pd.DataFrame({'first_visit':['2025-01-01','2025-01-02'],
            'channel':['Email','Email'],'inquiry':[0,0],'application':[0,0],
            'admitted':[0,0],'enrolled':[0,0]}).to_sql('prospects',conn,index=False)
        pd.DataFrame({'date':['2025-01-01','2025-01-02'],
            'channel':['Email','Email'],'spend':[10.,20.]}).to_sql('campaign_costs',conn,index=False)
        query=dict(re.findall(r'-- name: (\w+)\n(.*?;)',(analysis.ROOT/'analysis.sql').read_text(),re.S))['monthly_channel']
        row=pd.read_sql_query(query,conn).iloc[0]
        conn.close()
        self.assertEqual(row.visitors,2);self.assertEqual(row.spend,30.)
        self.assertTrue(pd.isna(row.cost_per_inquiry));self.assertTrue(pd.isna(row.cost_per_enrollment))

    def test_z_test_matches_independent_chi_square(self):
        g=self.p.groupby('variant').inquiry.agg(['sum','count']).reindex(['A','B'])
        k=g['sum'].to_numpy();n=g['count'].to_numpy();r=k/n
        pooled=k.sum()/n.sum()
        z=(r[1]-r[0])/np.sqrt(pooled*(1-pooled)*np.sum(1/n))
        table=np.column_stack([k,n-k])
        chi2,pvalue,_,_=stats.chi2_contingency(table,correction=False)
        self.assertAlmostEqual(chi2,z*z,places=10)
        self.assertAlmostEqual(pvalue,2*stats.norm.sf(abs(z)),places=12)


if __name__=='__main__':unittest.main(verbosity=2)
