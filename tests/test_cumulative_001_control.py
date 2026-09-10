from dataclasses import asdict
from learning.body_schema_002 import Observation,Ridge
from learning.cumulative_001_control import plan_action


def test_planner_is_bounded_and_does_not_mutate_observed_state():
    o=Observation(70.,-2.,75.,125.,-5.)
    before=asdict(o); model=Ridge.initial('F'); version=model.version
    command,trace=plan_action(model,o,137.5)
    assert 30<=command<=150
    assert asdict(o)==before and model.version==version
    assert len(trace['candidates'])==len(trace['costs'])
    assert command in trace['candidates']


def test_planner_holds_an_already_reached_goal():
    command,_=plan_action(Ridge.initial('F'),Observation(90.,0.,90.,90.,0.),90.)
    assert command==90.
