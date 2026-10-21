"""Basic contracts; full 3000-case benchmark runs separately in CI."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from lab030 import ACTIONS, SCENARIOS, BeanQ, fixture, scoped, evaluate, features

class Lab030Contracts(unittest.TestCase):
    def test_all_oracle_scenarios(self):
        for i,kind in enumerate(SCENARIOS):
            item=fixture(i,20261020)
            self.assertEqual(item["scenario"],kind)
            found,review=scoped(item["line"])
            self.assertEqual(found,item["expected"])
            self.assertEqual(review,item["needs_review"])
    def test_false_balloons_and_bad_tolerances_cost_reward(self):
        expected=[[2.5,2.495,2.51]]
        perfect=evaluate(expected,expected)
        wrong=evaluate(expected,[[2.5,2.48,2.52]])
        extra=evaluate(expected,expected+[[0.005,0.0,0.01]])
        self.assertGreater(perfect["reward"],wrong["reward"])
        self.assertGreater(perfect["reward"],extra["reward"])
        self.assertEqual(extra["false_balloons"],1)
    def test_q_learning_uses_reward_and_remembers_state(self):
        agent=BeanQ(10)
        s=features("WIDTH 2.500 +.010/-.005 LENGTH 4.000 +.020/-.010")
        self.assertEqual(agent.choose(s,0),0)
        agent.learn(s,1,4.)
        self.assertEqual(agent.choose(s,0),1)
        self.assertEqual(agent.scoreboard()["games"],1)
        self.assertGreater(agent.q[s][1],agent.q[s][0])
    def test_scoped_marks_unknown_note_for_review(self):
        item=fixture(6,20261020)
        proposed,reviewed=scoped(item["line"])
        self.assertTrue(reviewed)
        self.assertTrue(evaluate(item["expected"],proposed,True,reviewed)["exact"])

if __name__=="__main__":unittest.main()
