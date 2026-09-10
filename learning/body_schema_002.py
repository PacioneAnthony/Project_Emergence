"""Causal body forecasting. No simulator state or evaluation annotations enter models."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from copy import deepcopy
import hashlib
import json
from typing import Sequence
import numpy as np

STEP = 360.0 / 4096.0
FORMAT = 'body-forecast-r2-v1'


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


@dataclass(frozen=True)
class Observation:
    angle: float
    delta: float
    previous_target: float
    target: float
    previous_command_delta: float
    dt: float = 0.02

    def __post_init__(self):
        if self.dt != 0.02:
            raise ValueError('r2-v1 requires dt=0.02; no silent change of physical prior')
        if not all(np.isfinite(v) for v in asdict(self).values()):
            raise ValueError('nonfinite observation')


@dataclass(frozen=True)
class TrainingRow:
    observation: Observation
    next_angle: float

    def __post_init__(self):
        if type(self.observation) is not Observation or not np.isfinite(self.next_angle):
            raise ValueError('invalid supervised row')

    def payload(self):
        return {'observation': asdict(self.observation), 'next_angle': float(self.next_angle)}

    @classmethod
    def restore(cls, value):
        return cls(Observation(**value['observation']), value['next_angle'])


def features(o: Observation, kind: str) -> np.ndarray:
    if type(o) is not Observation:
        raise TypeError('predict accepts only causal Observation')
    x, v = (o.angle - 90.) / 80., o.delta / 12.
    if kind == 'B3':
        result = [1, x, v]
    elif kind == 'B13':
        result = [1,x,v,x*x,x*v,v*v,x**3,x*x*v,x*v*v,v**3,x**3*v,x*x*v*v,x*v**3]
    elif kind == 'F':
        error = o.target - o.angle
        command = o.target - o.previous_target
        hold = float(abs(command) < 1e-9)
        reversal = float(command * o.previous_command_delta < 0 and abs(command) >= 1e-9
                         and abs(o.previous_command_delta) >= 1e-9)
        result = [1,error/160,np.clip(error,-12,12)/12,v,command/160,
                  o.previous_command_delta/160,hold,reversal,abs(error)/160,
                  error*abs(error)/160**2,x,hold*v,reversal*v]
    else:
        raise ValueError(kind)
    return np.array(result, dtype=np.float64)


def prior(o: Observation, kind: str) -> float:
    features(o, kind)  # also enforce the causal type at every entry point
    return float(np.clip(o.angle + (np.clip(o.target-o.angle,-12,12) if kind == 'F' else 0),10,170))


@dataclass(frozen=True)
class Ridge:
    kind: str
    weights: tuple[float, ...]
    center: tuple[float, ...]
    scale: tuple[float, ...]

    @classmethod
    def initial(cls, kind):
        n = 3 if kind == 'B3' else 13
        features(Observation(90,0,90,90,0), kind)
        return cls(kind, (0.,)*n, (0.,)*n, (1.,)*n)

    def predict(self, o: Observation) -> float:
        f = (features(o,self.kind)-self.center)/self.scale
        return float(np.clip(prior(o,self.kind)+f@self.weights,10,170))

    def payload(self):
        return {'format': FORMAT, **asdict(self)}

    @property
    def version(self):
        return digest(self.payload())

    @classmethod
    def restore(cls,p):
        if p['format'] != FORMAT:
            raise ValueError('unsupported model format')
        model=cls(p['kind'],tuple(p['weights']),tuple(p['center']),tuple(p['scale']))
        n=len(features(Observation(90,0,90,90,0),model.kind))
        if any(len(x)!=n for x in (model.weights,model.center,model.scale)):
            raise ValueError('invalid feature dimensions')
        if not np.isfinite([model.weights,model.center,model.scale]).all() or min(model.scale)<=0:
            raise ValueError('invalid model values')
        if model.center[0]!=0 or model.scale[0]!=1:
            raise ValueError('intercept normalization')
        return model


def fit(rows: Sequence[TrainingRow], kind: str, row_weights=None):
    if not rows:
        return Ridge.initial(kind), {'empty':True}
    w=np.ones(len(rows)) if row_weights is None else np.asarray(row_weights,dtype=float)
    if w.shape!=(len(rows),) or not np.isfinite(w).all() or (w<0).any():
        raise ValueError('invalid training weights')
    if w.sum()==0:
        return Ridge.initial(kind), {'empty':True}
    design=np.stack([features(r.observation,kind) for r in rows])
    center=np.average(design,axis=0,weights=w)
    scale=np.sqrt(np.average((design-center)**2,axis=0,weights=w))
    center[0]=0; scale[scale<1e-12]=1; scale[0]=1
    normalized=(design-center)/scale
    residual=np.array([r.next_angle-prior(r.observation,kind) for r in rows])
    a=normalized*np.sqrt(w)[:,None]; b=residual*np.sqrt(w)
    penalty=np.eye(a.shape[1]); penalty[0,0]=0
    # Solve the regularized least squares directly, avoiding squared conditioning.
    augmented=np.vstack([a,penalty]); rhs=np.concatenate([b,np.zeros(a.shape[1])])
    weights=np.linalg.lstsq(augmented,rhs,rcond=None)[0]
    model=Ridge(kind,tuple(weights),tuple(center),tuple(scale))
    return model, {'empty':False,'column_max_abs':np.max(abs(design),axis=0).tolist(),
                  'column_scale':scale.tolist(),'condition_regularized':float(np.linalg.cond(augmented)),
                  'training_saturation_fraction':float(np.mean([model.predict(r.observation) in (10.,170.) for r in rows]))}


def rollout(model: Ridge, initial: Observation, commands: Sequence[float]) -> list[float]:
    o=initial; predictions=[]
    for command in commands:
        o=replace(o,target=float(command))
        p=model.predict(o); predictions.append(p)
        o=Observation(p,p-o.angle,o.target,o.target,o.target-o.previous_target,o.dt)
    return predictions


def errors(model, anchors):
    by_motif={k:float(np.mean([abs(model.predict(r.observation)-r.next_angle) for r in rows]))
              for k,rows in anchors.items()}
    return {'global':float(np.mean(list(by_motif.values()))),**by_motif}


def promotion_gate(candidate_errors,active_errors,reference_errors,rule):
    return (all(candidate_errors[k] <= active_errors[k]+rule['per_active_margin_deg']
                and candidate_errors[k] <= reference_errors[k]+rule['fixed_prior_cumulative_margin_deg']
                and candidate_errors[k] <= rule['absolute_mae_cap_deg'] for k in candidate_errors)
            and active_errors['global']-candidate_errors['global'] > rule['min_global_gain_deg'])


class Learner:
    """Candidate data accumulate even when its active version is unchanged."""
    def __init__(self,kind,anchors,rule):
        self.kind=kind; self.anchors=anchors; self.rule=dict(rule)
        self.active=Ridge.initial(kind); self.candidate=self.active
        self.reference=errors(self.active,anchors)
        self.trials=[]; self.history=[]; self.diagnostics={}

    def update(self,rows):
        self.trials.append(list(rows))
        self.candidate,self.diagnostics=fit([r for trial in self.trials for r in trial],self.kind)
        due=len(self.trials)%self.rule['every_trials']==0
        decision={'trial_count':len(self.trials),'due':due,'promoted':False,
                  'candidate_version':self.candidate.version,'active_before':self.active.version}
        if due:
            c,a=errors(self.candidate,self.anchors),errors(self.active,self.anchors)
            decision.update(candidate_errors=c,active_errors=a)
            decision['promoted']=promotion_gate(c,a,self.reference,self.rule)
            if decision['promoted']: self.active=self.candidate
        self.history.append(decision)
        return decision

    def payload(self):
        return deepcopy({'format':FORMAT,'kind':self.kind,'anchors':{k:[r.payload() for r in v] for k,v in self.anchors.items()},
                'rule':self.rule,'active':self.active.payload(),'candidate':self.candidate.payload(),
                'reference':self.reference,'trials':[[r.payload() for r in trial] for trial in self.trials],
                'history':self.history,'diagnostics':self.diagnostics})

    @classmethod
    def restore(cls,p):
        if p['format']!=FORMAT: raise ValueError('unsupported learner format')
        obj=cls(p['kind'],{k:[TrainingRow.restore(r) for r in v] for k,v in p['anchors'].items()},p['rule'])
        if obj.reference != p['reference']: raise ValueError('fixed reference changed')
        obj.active=Ridge.restore(p['active']); obj.candidate=Ridge.restore(p['candidate'])
        obj.trials=[[TrainingRow.restore(r) for r in t] for t in p['trials']]
        obj.history=deepcopy(p['history']); obj.diagnostics=deepcopy(p['diagnostics'])
        if len(obj.trials)!=len(obj.history): raise ValueError('invalid learner cursor')
        return obj


@dataclass(frozen=True)
class CalibratedEnsemble:
    members: tuple[Ridge,...]
    residual_sigma: float
    q: float

    @classmethod
    def calibrate(cls,members,rows):
        if not rows: raise ValueError('empty calibration')
        means=np.array([np.mean([m.predict(r.observation) for m in members]) for r in rows])
        residual=np.array([r.next_angle for r in rows])-means
        spread=max(STEP,1.4826*float(np.median(abs(residual-np.median(residual)))))
        sigmas=np.array([np.sqrt(np.var([m.predict(r.observation) for m in members],ddof=0)+spread**2) for r in rows])
        return cls(tuple(members),spread,float(np.quantile(abs(residual)/sigmas,.9,method='higher')))

    @property
    def version(self): return digest(self.payload())

    def predict(self,o):
        values=[m.predict(o) for m in self.members]
        mean=float(np.mean(values)); sigma=float(np.sqrt(np.var(values,ddof=0)+self.residual_sigma**2))
        return {'mean':mean,'sigma':sigma,'lower':max(10.,mean-self.q*sigma),
                'upper':min(170.,mean+self.q*sigma),'halfwidth':max(STEP,self.q*sigma),'version':self.version}

    def payload(self):
        return {'format':FORMAT,'members':[m.payload() for m in self.members],
                'residual_sigma':self.residual_sigma,'q':self.q}

    @classmethod
    def restore(cls,p):
        if p['format']!=FORMAT or p['residual_sigma']<STEP or p['q']<0:
            raise ValueError('invalid calibration')
        return cls(tuple(Ridge.restore(m) for m in p['members']),p['residual_sigma'],p['q'])


class InnovationMonitor:
    def __init__(self,threshold):
        self.threshold=float(threshold); self.window=[]; self.first_alarm=None; self.count=0

    def observe(self,prediction,observed):
        self.count+=1
        self.window=(self.window+[min(10.,abs(observed-prediction['mean'])/prediction['halfwidth'])])[-4:]
        score=float(np.mean(self.window)) if len(self.window)==4 else None
        if score is not None and score>self.threshold and self.first_alarm is None:
            self.first_alarm=self.count
        return score

    def payload(self): return dict(threshold=self.threshold,window=self.window,first_alarm=self.first_alarm,count=self.count)

    @classmethod
    def restore(cls,p):
        obj=cls(p['threshold']); obj.window=list(p['window']); obj.first_alarm=p['first_alarm']; obj.count=p['count']; return obj
