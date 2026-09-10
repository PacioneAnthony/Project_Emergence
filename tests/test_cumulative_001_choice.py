from dataclasses import asdict
from learning.body_schema_002 import Observation,Ridge
from learning.cumulative_001_choice import choose,predict_candidates


def test_selects_maximum_value_only_among_predicted_feasible_actions():
    o=Observation(90.,0.,90.,90.,0.)
    assert choose(o,[95.,120.,150.],[95.,118.,135.])==1
    assert choose(o,[95.,120.,150.],[90.,90.,90.])==0


def test_terminal_predictions_do_not_mutate_initial_state():
    o=Observation(90.,0.,90.,90.,0.); before=asdict(o)
    pred=predict_candidates(Ridge.initial('F'),o,[60.,95.,150.],1)
    assert pred==[78.,95.,102.]
    assert asdict(o)==before
