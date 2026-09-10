import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from research_planning import assess_plan


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.plan={'schema_version':1,'source_nature':'synthetic',
            'constraints':{'months_available':12,'prohibited_methods':['randomized_experiment']},
            'resources':[{'id':'interviews','description':'Interviews','source':'Scenario',
                          'availability':'available','permission':'confirmed'},
                         {'id':'logs','description':'Promised logs','source':'Oral commitment',
                          'availability':'uncertain','permission':'pending'}],
            'routes':[{'id':'process','question':'How does learning change?','claim_scope':'Interpretive process',
                       'minimum_evidence':'Episodes and counterexamples','fallback':'Narrow to reported experiences',
                       'methods':['interviews'],'requires':['interviews'],'estimated_months':10}]}

    def test_promised_logs_cannot_make_route_ready(self):
        self.plan['routes'][0]['requires'].append('logs')
        result=assess_plan(self.plan)
        self.assertEqual(result['routes'][0]['resource_status'],'conditional')
        self.assertEqual(result['source_nature'],'synthetic')
        self.plan['resources'][1]['availability']='available'
        self.assertEqual(assess_plan(self.plan)['routes'][0]['resource_status'],'conditional')
        self.plan['resources'][1]['permission']='confirmed'
        self.assertEqual(assess_plan(self.plan)['routes'][0]['resource_status'],'ready_for_planning')

    def test_lost_optional_logs_do_not_block_independent_route(self):
        quantitative=copy.deepcopy(self.plan['routes'][0]);quantitative.update(id='quant',requires=['logs'])
        self.plan['routes'].append(quantitative)
        self.plan['resources'][1]['availability']='unavailable'
        results=assess_plan(self.plan)['routes']
        self.assertEqual([r['resource_status'] for r in results],['ready_for_planning','blocked'])

    def test_method_and_time_constraints_are_not_overridden_by_available_data(self):
        self.plan['routes'][0].update(methods=['randomized_experiment'],estimated_months=13)
        result=assess_plan(self.plan)['routes'][0]
        self.assertEqual(result['resource_status'],'blocked')
        self.assertEqual({r['type'] for r in result['blockers']},{'prohibited_method','time_exceeds_declared_budget'})

    def test_invalid_dependencies_and_estimates_fail(self):
        for change in [{'requires':['unknown']},{'estimated_months':float('nan')},{'estimated_months':True}]:
            plan=copy.deepcopy(self.plan);plan['routes'][0].update(change)
            with self.subTest(change=change):
                with self.assertRaises(ValueError):assess_plan(plan)
        self.plan['resources'].append(copy.deepcopy(self.plan['resources'][0]))
        with self.assertRaises(ValueError):assess_plan(self.plan)


if __name__=='__main__':unittest.main()
