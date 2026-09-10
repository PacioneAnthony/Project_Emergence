from dataclasses import replace
import json
import numpy as np
import pytest
from learning.cumulative_001_data import commands,build_manifest,encode
from learning.cumulative_001_neural import NeuralLearner,torch
from learning.body_schema_002 import Observation,TrainingRow


def rows():
    return [TrainingRow(Observation(float(60+i),.1,90.,120.,0.),float(62+i)) for i in range(24)]


def test_domains_and_fresh_provenance():
    a,b,c=[commands(d,445566+i) for i,d in enumerate(['A','B','C'])]
    assert len(a)==len(b)==len(c)==64 and a[-8:]==[90.]*8
    assert min(a)>=30 and max(a)<=90 and min(b)>=90 and max(b)<=150
    m=build_manifest(); seen=[]
    for life in m['lives'].values():
        seen.extend([life['body'],life['initialization'],life['batches']])
        for t in life['trials'].values(): seen.extend(t.values())
    assert len(seen)==len(set(seen))


def test_neural_prediction_cannot_read_future_labels():
    original=rows(); altered=[TrainingRow(r.observation,r.next_angle+20) for r in original]
    model=NeuralLearner(42,23,False,device='cpu',updates=2)
    model.update(original)
    assert np.array_equal(model.predict([r.observation for r in original]),model.predict([r.observation for r in altered]))
    assert not np.array_equal(encode(original)[1],encode(altered)[1])


def test_replay_does_not_see_future_and_updates_are_matched():
    naive=NeuralLearner(42,23,False,device='cpu',updates=2)
    replay=NeuralLearner(42,23,True,device='cpu',updates=2)
    assert naive.parameter_digest()==replay.parameter_digest()
    assert len(replay.memory_x)==0
    naive.update(rows()); replay.update(rows())
    assert naive.parameter_digest()==replay.parameter_digest()
    assert len(replay.memory_x)==24 and len(naive.memory_x)==0
    naive.update(rows()); replay.update(rows())
    assert naive.update_count==replay.update_count==4 and len(replay.memory_x)==48


@pytest.mark.parametrize('replay',[False,True])
def test_complete_checkpoint_restores_optimizer_rng_and_next_update(tmp_path,replay):
    model=NeuralLearner(42,23,replay,device='cpu',updates=3)
    model.update(rows()); path=tmp_path/'model.pt'; model.save(path)
    restored=NeuralLearner.load(path,device='cpu')
    assert model.parameter_digest()==restored.parameter_digest()
    assert torch.equal(model.generator.get_state(),restored.generator.get_state())
    model.update(rows()); restored.update(rows())
    assert model.parameter_digest()==restored.parameter_digest()
    assert torch.equal(model.generator.get_state(),restored.generator.get_state())
    assert model.trials==restored.trials==2
