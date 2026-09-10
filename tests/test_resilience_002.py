from copy import deepcopy
from dataclasses import asdict
import numpy as np
import pytest
from cognitive.kernel import CognitiveKernel
from cognitive.functional_learning import FunctionalStore
from learning.body_schema_002 import Observation
from learning.resilience_001_agent import state_digest
from learning.resilience_002_agent import FunctionalAgent


def agent(policy='need'):
    return FunctionalAgent(183749,239843,982131,policy,'cpu',updates=2)


def trial(a, band):
    result=[]
    for i in range(4):
        o=Observation(80.+i,0.,80.+i,90.+i,0.)
        result.append({'band':band,'observation':asdict(o),'horizon':6,
                       'announcement':a.announce(o,6),'angles':[float(82+i+j) for j in range(8)]})
    return result


def success(band, promised=True):
    return {'band':band,'error':.1,'promised':promised,'success':True}


def test_need_chooses_unseen_then_errors_with_a_starvation_guard():
    a=agent(); assert a.select()['band']==0
    a.outcomes=[success(0)]*4; assert a.select()['band']==1
    a.outcomes+=[success(1)]*4; assert a.select()['band']==2
    a.outcomes+=[{**success(2),'error':10.}]*4
    assert a.select()['band']==2
    assert a.select()['band']==0


def test_low_errors_cannot_close_without_coverage_or_successful_promises():
    a=agent(); a.outcomes=[success(0)]*12
    e=trial(a,0)
    for r in e: r['angles']=[r['announcement']['predicted']]*8
    assert a.update(e)['need_open']
    a.outcomes=[success(i%3,False) for i in range(12)]
    for r in e: r['announcement']['promised']=False
    assert a.update(e)['need_open']


def test_one_broken_promise_reopens_a_functional_need_despite_low_errors():
    a=agent(); a.outcomes=[success(i%3) for i in range(12)]
    e=trial(a,0)
    for r in e: r['angles']=[r['observation']['target']]*8
    assert a.update(e)['closed']
    # A two-degree prediction error straddles the success boundary.
    for r in e:
        r['announcement']['predicted']=r['observation']['target']+1.
        r['announcement']['promised']=True
        r['angles']=[r['observation']['target']+2.1]*8
    event=a.update(e)
    assert event['opened'] and event['need_open'] and not event['alarm']


@pytest.mark.parametrize('policy',['need','cycle','uniform'])
def test_complete_checkpoint_reproduces_next_choice_and_update_without_aliasing(policy):
    a=agent(policy)
    for _ in range(3):
        decision=a.select(); a.update(trial(a,decision['band']))
    archive=a.state(); before=state_digest(archive)
    b=FunctionalAgent.restore(archive,'cpu')
    assert a.select()==b.select()
    episodes=trial(a,a.decisions[-1]['band'])
    a.update(episodes); b.update(episodes)
    assert state_digest(a.state())==state_digest(b.state())
    assert state_digest(archive)==before


@pytest.mark.parametrize('point,committed',[('after_publication',False),('before_commit',False),('after_commit',True)])
def test_atomic_experience_and_decision_survive_interruptions(tmp_path,point,committed):
    database=tmp_path/'kernel.sqlite'
    with CognitiveKernel(database) as k:
        store=FunctionalStore(k,tmp_path/'artifacts','life','contract','cpu')
        original=store.initialize(agent('uniform'))
        expected=FunctionalAgent.restore(original.state(),'cpu')
        decision=expected.select(); episodes=trial(expected,decision['band']); expected.update(episodes)
        def fail(stage):
            if stage==point: raise RuntimeError('injected interruption')
        with pytest.raises(RuntimeError,match='injected'): store.apply('0',decision,episodes,fail)
    with CognitiveKernel(database) as k:
        store=FunctionalStore(k,tmp_path/'artifacts','life','contract','cpu')
        a,event,applied=store.apply('0',decision,episodes)
        assert applied != committed
        assert state_digest(a.state())==state_digest(expected.state())
        obs=[Observation(**r['observation']) for r in episodes]
        assert np.array_equal(store.predict(obs,[6]*4),expected.predict(obs,[6]*4))
        assert k.memory.connection.execute('SELECT count(*) FROM resilience_experiences').fetchone()[0]==1
        assert k.memory.validated_model('functional/life') is None
        changed=deepcopy(episodes); changed[0]['angles'][0]+=1
        with pytest.raises(ValueError,match='content'): store.apply('0',decision,changed)


def test_store_refuses_rewritten_pre_action_prediction_or_unselected_experience(tmp_path):
    with CognitiveKernel(tmp_path/'kernel.sqlite') as k:
        store=FunctionalStore(k,tmp_path/'artifacts','life','contract','cpu')
        a=store.initialize(agent()); decision=a.select(); episodes=trial(a,decision['band'])
        modified=deepcopy(episodes); modified[0]['announcement']['predicted']+=.1
        with pytest.raises(ValueError,match='prediction'): store.apply('0',decision,modified)
        modified=deepcopy(episodes); modified[0]['band']=2
        with pytest.raises(ValueError,match='band'): store.apply('0',decision,modified)
        assert store.load().trials==0


def test_need_scores_remain_safe_to_reload_after_actual_choices(tmp_path):
    with CognitiveKernel(tmp_path/'kernel.sqlite') as k:
        store=FunctionalStore(k,tmp_path/'artifacts','life','contract','cpu')
        store.initialize(agent())
        for i in range(4):
            a=store.load(); decision=a.select(); episodes=trial(a,decision['band'])
            expected=FunctionalAgent.restore(a.state(),'cpu'); expected.update(episodes)
            store.apply(str(i),decision,episodes)
            assert state_digest(store.load().state())==state_digest(expected.state())
        assert any(s is not None for s in store.load().decisions[-1]['scores'])


def test_horizons_and_nonfinite_future_cannot_silently_enter_learning():
    a=agent(); o=Observation(90,0,90,100,0)
    with pytest.raises(ValueError,match='horizon'): a.predict([o],[4.5])
    e=trial(a,0); e[0]['angles'][1]=float('nan')
    with pytest.raises(ValueError,match='trial'): a.update(e)


def test_lived_trial_keeps_physical_continuity_and_equal_interaction_budget():
    from learning.resilience_002 import lived_trial
    class Env:
        def __init__(self): self.step_count=0; self.angle=90.
        def step(self,target):
            from types import SimpleNamespace
            self.step_count+=1; self.angle+=float(np.clip(target-self.angle,-3,3))
            return SimpleNamespace(as5600_deg=self.angle)
    histories=[]
    for policy in ['need','cycle','uniform']:
        a=agent(policy); env=Env(); history=(90.,0.,90.,0.)
        for index in range(2):
            decision=a.select(); e,history=lived_trial(env,history,100001+index,a,decision)
            assert len(e)==4 and all(len(r['angles'])==8 for r in e)
            assert env.step_count==(index+1)*128
            assert history[0]==env.angle
            a.update(e)
        histories.append(env.step_count)
    assert histories==[256]*3
