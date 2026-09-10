from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from cognitive.kernel import CognitiveKernel
from cognitive.resilience import ResilienceStore
from learning.body_schema_002 import Observation, TrainingRow
from learning.resilience_001_agent import RecoveryAgent, state_digest, restore_neural


def rows():
    return [TrainingRow(Observation(65. + i, .1, 90., 120., 0.), 68. + i) for i in range(64)]


def agent():
    return RecoveryAgent(183749, 239843, device='cpu', updates=2)


def test_supervisor_recalls_by_observation_without_a_context_label():
    a = agent()
    a.learner.update(rows())
    a.archives = [deepcopy(a.learner.state())]
    observations = [r.observation for r in rows()]
    target = a.learner.predict(observations)
    a.trials = 12; a.reference = [.1] * 6; a.streak = 1
    event = {'alarm': False, 'goal_opened': False, 'goal_closed': False}
    a._observe(2., .35, observations, target, event)
    assert event['alarm'] and event['response'] == 'recall' and a.recovering
    for _ in range(3):
        event = {'goal_closed': False}
        a._observe(.1, .35, observations, target, event)
    assert not a.recovering and event['goal_closed']


def test_complete_supervisor_checkpoint_keeps_archives_and_next_update():
    a = agent()
    for _ in range(8): a.update(rows())
    restored = RecoveryAgent.restore(deepcopy(a.state()), 'cpu')
    assert len(a.archives) == len(restored.archives) == 1
    a.update(rows()); restored.update(rows())
    assert state_digest(a.state()) == state_digest(restored.state())
    assert len(a.learner.memory_x) <= 256


def test_recalled_optimizer_cannot_mutate_the_saved_archive():
    a = agent()
    a.learner.update(rows())
    archive = deepcopy(a.learner.state())
    before = state_digest(archive)
    recalled = restore_neural(archive, 'cpu')
    recalled.update(rows())
    assert state_digest(archive) == before


@pytest.mark.parametrize('point,committed', [('after_publication', False), ('before_commit', False), ('after_commit', True)])
def test_kernel_restart_after_interruption_never_applies_experience_twice(tmp_path, point, committed):
    database = tmp_path / 'memory.sqlite'
    with CognitiveKernel(database) as kernel:
        store = ResilienceStore(kernel, tmp_path / 'artifacts', 'life', 'contract', 'cpu')
        original = store.initialize(agent())
        expected = RecoveryAgent.restore(deepcopy(original.state()), 'cpu')
        expected.update(rows())
        def fail(stage):
            if stage == point: raise RuntimeError('injected interruption')
        with pytest.raises(RuntimeError): store.apply('experience-0', rows(), fail)
    with CognitiveKernel(database) as kernel:
        store = ResilienceStore(kernel, tmp_path / 'artifacts', 'life', 'contract', 'cpu')
        result, event, applied = store.apply('experience-0', rows())
        assert applied == (not committed)
        assert state_digest(result.state()) == state_digest(expected.state())
        assert np.array_equal(store.predict([r.observation for r in rows()]), expected.predict([r.observation for r in rows()]))
        assert kernel.memory.connection.execute('SELECT count(*) FROM resilience_experiences').fetchone()[0] == 1
        assert kernel.memory.validated_model('resilience/life') is None
        with pytest.raises(ValueError, match='content'):
            store.apply('experience-0', [replace(r, next_angle=r.next_angle + 1) for r in rows()])


def test_tampered_checkpoint_and_changed_contract_are_rejected(tmp_path):
    with CognitiveKernel(tmp_path / 'memory.sqlite') as kernel:
        store = ResilienceStore(kernel, tmp_path / 'artifacts', 'life', 'contract', 'cpu')
        store.initialize(agent())
        with pytest.raises(ValueError, match='contract'):
            ResilienceStore(kernel, tmp_path / 'artifacts', 'life', 'changed', 'cpu').load()
        from pathlib import Path
        path = Path(store._state()['artifact'])
        with path.open('ab') as stream: stream.write(b'tamper')
        with pytest.raises(ValueError, match='integrity'): store.load()
