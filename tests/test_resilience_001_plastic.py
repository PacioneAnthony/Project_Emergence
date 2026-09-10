from copy import deepcopy
from cognitive.kernel import CognitiveKernel
from cognitive.resilience_plastic import PlasticResilienceStore
from learning.body_schema_002 import Observation, TrainingRow
from learning.resilience_001_plastic import PlasticRecoveryAgent
from learning.resilience_001_agent import state_digest


def surprise_rows():
    return [TrainingRow(Observation(80., 0., 120., 120., 0.), 81.)] * 64


def prepared():
    a = PlasticRecoveryAgent(219348, 429387, device='cpu', updates=2)
    a.trials = 12
    a.reference = [.1] * 6
    return a


def test_large_surprise_triggers_bounded_plasticity_without_phase():
    a = prepared()
    event = a.update(surprise_rows())
    assert event['alarm'] and event['goal_opened']
    assert a.plastic_remaining == 2 and not a.learner.replay
    assert len(a.learner.memory_x) == 64
    a.update(surprise_rows()); a.update(surprise_rows())
    assert a.plastic_remaining == 0 and a.learner.replay
    assert len(a.learner.memory_x) == 192
    assert a.total_updates == 6


def test_service_restart_during_plasticity_reproduces_complete_next_update(tmp_path):
    with CognitiveKernel(tmp_path / 'kernel.sqlite') as kernel:
        store = PlasticResilienceStore(kernel, tmp_path / 'artifacts', 'plastic', 'contract', 'cpu')
        store.initialize(prepared())
        a, _, _ = store.apply('first', surprise_rows())
        expected = PlasticRecoveryAgent.restore(deepcopy(a.state()), 'cpu')
        expected.update(surprise_rows())
    with CognitiveKernel(tmp_path / 'kernel.sqlite') as kernel:
        store = PlasticResilienceStore(kernel, tmp_path / 'artifacts', 'plastic', 'contract', 'cpu')
        a, _, _ = store.apply('second', surprise_rows())
        assert state_digest(a.state()) == state_digest(expected.state())
        same, _, applied = store.apply('second', surprise_rows())
        assert not applied and state_digest(same.state()) == state_digest(a.state())
