from dataclasses import replace
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from cognitive.kernel import CognitiveKernel
from cognitive.body_forecast import BodyForecastStore
from learning.body_schema_002 import (Observation,TrainingRow,Ridge,Learner,CalibratedEnsemble,
    InnovationMonitor,features,fit,rollout,digest,canonical,promotion_gate)
from learning.body_schema_002_budget import Budget
from learning.body_schema_002_experiment import plans,content_checks,score


def synthetic(seed=4,n=64):
    rng=np.random.default_rng(seed)
    rows=[]
    for i in range(n):
        angle=float(rng.uniform(45,135)); target=float(rng.uniform(45,135)); delta=float(rng.uniform(-4,4))
        o=Observation(angle,delta,90.,target,0.)
        rows.append(TrainingRow(o,float(np.clip(angle+.1*(target-angle)+.2*delta,10,170))))
    return rows


def rule():
    return {'every_trials':3,'per_active_margin_deg':.1,'fixed_prior_cumulative_margin_deg':.2,
            'absolute_mae_cap_deg':10.,'min_global_gain_deg':.001}


def learner(kind='F'):
    return Learner(kind,{'anchor':synthetic(6)},rule())


def proof(model):
    return {'model_version':model.version,'level':'development','usage_passed':True,'reception_passed':True}


def test_causal_type_and_fixed_frequency():
    with pytest.raises(ValueError): Observation(90,0,90,90,0,dt=.04)
    with pytest.raises(ValueError): Observation(float('nan'),0,90,90,0)
    with pytest.raises(TypeError): Ridge.initial('F').predict({'angle':90,'ramp_class':'plateau'})
    with pytest.raises(TypeError): Ridge.initial('F').predict(TrainingRow(Observation(90,0,90,90,0),91))


@pytest.mark.parametrize('kind',['F','B13','B3'])
def test_ridge_synthetic_generalization_and_restoration(kind):
    model,diagnostic=fit(synthetic(),kind)
    restored=Ridge.restore(json.loads(canonical(model.payload())))
    test=synthetic(14)
    assert [model.predict(r.observation) for r in test]==[restored.predict(r.observation) for r in test]
    assert diagnostic['condition_regularized']<1e6
    if kind=='F':
        old=np.mean([abs(Ridge.initial(kind).predict(r.observation)-r.next_angle) for r in test])
        new=np.mean([abs(model.predict(r.observation)-r.next_angle) for r in test])
        assert new<old*.5


@pytest.mark.parametrize('kind',['B13','B3'])
def test_without_action_invariance_including_fit_prior_and_rollout(kind):
    rows=synthetic()
    mutated=[TrainingRow(replace(r.observation,target=160.,previous_target=10.,previous_command_delta=-150.),r.next_angle) for r in rows]
    a,_=fit(rows,kind); b,_=fit(mutated,kind)
    assert a.payload()==b.payload()
    assert all(np.array_equal(features(r.observation,kind),features(s.observation,kind)) for r,s in zip(rows,mutated))
    assert Ridge.initial(kind).predict(rows[0].observation)==rows[0].observation.angle
    empty,_=fit(rows,kind,np.zeros(len(rows)))
    assert empty.payload()==Ridge.initial(kind).payload()
    assert rollout(a,rows[0].observation,[30,90,150,90])==rollout(b,mutated[0].observation,[150,90,30,90])


def test_normalization_uses_only_learning_and_eval_is_frozen():
    model,_=fit(synthetic(),'F'); before=model.payload()
    rows=synthetic(2)
    original=score(model,rows,5)
    altered=[TrainingRow(r.observation,r.next_angle+3) for r in rows]
    assert score(model,altered,5)!=original
    assert model.payload()==before
    assert rollout(model,rows[0].observation,[r.observation.target for r in rows])==rollout(model,altered[0].observation,[r.observation.target for r in altered])


def test_calibration_invariance_rebuilt_and_negative_control():
    rows=synthetic(); members=tuple(fit(synthetic(i),'F')[0] for i in range(16))
    def build(tag,leaky=False):
        # Privileged envelope never goes to calibration, only authorized rows do.
        envelope={'rows':rows,'ramp_class':tag,'regime':tag,'fault':tag,'seed':tag}
        calibrated=CalibratedEnsemble.calibrate(members,envelope['rows'])
        if leaky: calibrated=replace(calibrated,residual_sigma=calibrated.residual_sigma*(3 if tag=='ramp' else 1))
        return calibrated
    a,b=build('ramp'),build('plateau')
    assert a.payload()==b.payload()
    restored=CalibratedEnsemble.restore(json.loads(canonical(a.payload())))
    assert a.predict(rows[0].observation)==restored.predict(rows[0].observation)
    def invariant(first,second): assert first.predict(rows[0].observation)==second.predict(rows[0].observation)
    with pytest.raises(AssertionError): invariant(build('ramp',True),build('plateau',True))
    # A genuinely changed consequence changes the judge error, not the frozen interval.
    pred=a.predict(rows[0].observation)
    assert abs(pred['mean']-rows[0].next_angle)!=abs(pred['mean']-rows[0].next_angle-10)


def test_monitor_restores_window_and_first_alarm_is_not_relabelled():
    monitor=InnovationMonitor(.5)
    prediction={'mean':90.,'halfwidth':1.}
    for _ in range(4): monitor.observe(prediction,91.)
    assert monitor.first_alarm==4  # before intervention at step 9: remains a false alarm
    restored=InnovationMonitor.restore(monitor.payload())
    for _ in range(8):
        assert restored.observe(prediction,95.)==monitor.observe(prediction,95.)
    assert restored.first_alarm==4
    assert InnovationMonitor(.5).window==[]


def test_refused_candidate_keeps_all_learning_data():
    obj=learner(); obj.rule['absolute_mae_cap_deg']=0.
    old=obj.active.version
    for _ in range(6): obj.update(synthetic())
    assert obj.active.version==old
    assert obj.candidate.version!=old
    assert len(obj.trials)==6
    restored=Learner.restore(json.loads(canonical(obj.payload())))
    assert restored.payload()==obj.payload()


def test_fixed_reference_blocks_cumulative_local_regressions():
    r=rule(); r['min_global_gain_deg']=.01; r['absolute_mae_cap_deg']=20.
    reference={'global':5.,'one':4.,'two':6.}; active=dict(reference)
    accepted=0
    for _ in range(10):
        candidate={'one':active['one']+.08,'two':active['two']-.2}
        candidate['global']=(candidate['one']+candidate['two'])/2
        if not promotion_gate(candidate,active,reference,r): break
        accepted+=1; active=candidate
    assert accepted==2
    assert active['one']<=4.2


def test_branch_restore_does_not_mutate_input_snapshot():
    original=learner()
    for _ in range(3): original.update(synthetic())
    snapshot=original.payload(); frozen=digest(snapshot)
    branch=Learner.restore(snapshot); branch.update(synthetic(8))
    assert digest(snapshot)==frozen
    assert digest(original.payload())==frozen


@pytest.mark.parametrize('stage',['after_publication','before_trial_commit','after_trial_commit','after_cycle_progress'])
def test_atomic_trial_recovery_and_old_replay(tmp_path,stage):
    def interrupt(at):
        if at==stage: raise RuntimeError('injected crash')
    with CognitiveKernel(tmp_path/'memory.sqlite') as kernel:
        store=BodyForecastStore(kernel,tmp_path/'artifacts','run','contract'); store.initialize(learner())
        with pytest.raises(RuntimeError): store.apply('run/0',synthetic(),interrupt=interrupt)
    with CognitiveKernel(tmp_path/'memory.sqlite') as kernel:
        store=BodyForecastStore(kernel,tmp_path/'artifacts','run','contract')
        store.apply('run/0',synthetic()); store.apply('run/1',synthetic(8)); store.apply('run/2',synthetic(9))
        before=digest(store.load().payload()); _,changed=store.apply('run/0',synthetic())
        assert not changed and digest(store.load().payload())==before
        assert store.reconcile()==3
        with pytest.raises(ValueError): store.apply('run/0',synthetic(15))
        # Same data at a genuinely different logical position is another trial.
        store.apply('run/3',synthetic()); assert len(store.load().trials)==4
        assert kernel.memory.integrity_check()=='ok'


@pytest.mark.parametrize('stage',['after_activation_publication','before_activation_commit','after_activation_commit'])
def test_atomic_activation_and_capacity_dependencies(tmp_path,stage):
    def interrupt(at):
        if at==stage: raise RuntimeError('injected crash')
    with CognitiveKernel(tmp_path/'memory.sqlite') as kernel:
        store=BodyForecastStore(kernel,tmp_path/'artifacts','run','contract'); store.initialize(learner())
        for i in range(3): obj,_=store.apply(f'run/{i}',synthetic(i))
        evidence=proof(obj.active)
        with pytest.raises(RuntimeError): store.activate(evidence,interrupt=interrupt)
        package=store.activate(evidence)
        assert package==store.activate(evidence)
        assert store.capabilities()['body_forecast_calibration']=='not_qualified'
        assert store.capabilities()['body_forecast_detection']=='not_qualified'
        prediction=store.active_prediction(synthetic()[0].observation)
        assert prediction['model']==obj.active.version and prediction['package']==package
        assert kernel.memory.connection.execute('SELECT count(*) FROM body_r2_proofs').fetchone()[0]==5


def test_corrupt_artifact_and_changed_contract_are_rejected(tmp_path):
    with CognitiveKernel(tmp_path/'memory.sqlite') as kernel:
        store=BodyForecastStore(kernel,tmp_path/'artifacts','run','contract'); store.initialize(learner())
        with pytest.raises(ValueError): BodyForecastStore(kernel,tmp_path/'artifacts','run','other').load()
        with pytest.raises(ValueError): store.activate({'model_version':'wrong','level':'development'})
        row=kernel.memory.connection.execute('SELECT artifact FROM body_r2_state').fetchone()
        Path(row['artifact']).write_text('{}')
        with pytest.raises(ValueError): store.load()


def test_cross_process_predict_and_next_update_match(tmp_path):
    database=tmp_path/'memory.sqlite'; artifacts=tmp_path/'artifacts'
    with CognitiveKernel(database) as kernel:
        store=BodyForecastStore(kernel,artifacts,'run','contract'); store.initialize(learner())
        for i in range(3): obj,_=store.apply(f'run/{i}',synthetic(i))
        before=obj.payload()
    rows=synthetic(25); o=rows[0].observation
    request={'database':str(database),'artifacts':str(artifacts),'run':'run','contract':'contract',
             'observation':o.__dict__,'next_rows':[r.payload() for r in rows]}
    request_path=tmp_path/'request.json'; response_path=tmp_path/'response.json'; request_path.write_bytes(canonical(request))
    subprocess.run([sys.executable,'-m','learning.body_schema_002_experiment','--restore-probe',str(request_path),str(response_path)],check=True,timeout=30)
    restored=json.loads(response_path.read_bytes()); obj.update(rows)
    assert restored=={'payload_digest':digest(before),'prediction':Ridge.restore(before['active']).predict(o),'next_payload_digest':digest(obj.payload())}


def test_plan_content_hash_ignores_metadata():
    definitions=plans(); assert len(definitions)==48
    assert {role:sum(p['role']==role for p in definitions) for role in ['protection','calibration','learning','evaluation']}==dict(protection=3,calibration=6,learning=24,evaluation=15)
    # Same trajectory under different names/roles must be detected.
    a=dict(definitions[0]); b=dict(a,id='other',role='evaluation')
    rows=synthetic(n=32)
    result=content_checks({a['id']:rows,b['id']:rows},[a,b])
    assert not result['passed'] and len(result['collisions'])==2
    assert len(range(32-25+1))==8


def test_budget_preserves_lost_attempt_and_refuses_changed_limits(tmp_path):
    path=tmp_path/'budget.sqlite'; budget=Budget(path,total=2,per_invocation=1)
    _,allowance=budget.reserve(['never started'],'test')
    assert allowance==1 and Budget(path,total=2,per_invocation=1).used()==1
    budget.reserve(['second'],'test')
    with pytest.raises(RuntimeError): budget.reserve(['third'],'test')
    with pytest.raises(ValueError): Budget(path,total=3,per_invocation=1)


def test_budget_kills_blocked_computation_and_charges_it(tmp_path):
    budget=Budget(tmp_path/'budget.sqlite',total=3,per_invocation=1)
    result=budget.run([sys.executable,'-c','import time; time.sleep(20)'],'test',tmp_path/'output.log')
    assert result['timeout'] and result['seconds']<3
    assert budget.used()>0
