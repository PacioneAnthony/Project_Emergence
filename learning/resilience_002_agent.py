"""Functional outcome learning and endogenous selection from a bounded catalog."""
from copy import deepcopy
import numpy as np
from learning.cumulative_001_neural import torch
from learning.body_schema_002 import Observation, features


def inputs(observations, horizons):
    return np.array([np.r_[features(o, 'F'), h / 8.] for o, h in zip(observations, horizons)], dtype=np.float32)


def priors(observations, horizons):
    return np.array([np.clip(o.angle + np.clip(o.target-o.angle, -12*h, 12*h), 10, 170)
                     for o, h in zip(observations, horizons)], dtype=np.float32)


class FunctionalAgent:
    def __init__(self, initialization, batches, selection, policy='need', device='cuda', updates=64):
        if policy not in ['need', 'cycle', 'uniform']: raise ValueError('policy')
        torch.manual_seed(initialization)
        self.model = torch.nn.Sequential(torch.nn.Linear(14,64), torch.nn.ReLU(), torch.nn.Linear(64,64), torch.nn.ReLU(), torch.nn.Linear(64,1)).to(device)
        torch.nn.init.zeros_(self.model[-1].weight); torch.nn.init.zeros_(self.model[-1].bias)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=.001)
        self.generator = torch.Generator(device=device).manual_seed(batches)
        self.selector = np.random.default_rng(selection)
        self.initialization, self.batches, self.selection = initialization, batches, selection
        self.policy, self.device, self.updates = policy, device, updates
        self.memory_x = torch.empty((0,14),device=device); self.memory_y = torch.empty((0,),device=device)
        self.outcomes = []; self.decisions = []; self.trials = 0; self.total_updates = 0
        self.need_open = True; self.events = []

    def predict(self, observations, horizons):
        if len(observations) != len(horizons) or any(not np.isfinite(h) or h != int(h) or h < 1 or h > 8 for h in horizons): raise ValueError('horizon')
        x = torch.as_tensor(inputs(observations, horizons),device=self.device)
        with torch.no_grad(): result = self.model(x).squeeze(-1).cpu().numpy()
        return np.clip(priors(observations,horizons)+12*result,10,170)

    def margin(self):
        if len(self.outcomes) < 8: return 2.
        return max(.25,float(np.quantile([r['error'] for r in self.outcomes[-16:]],.9)))

    def select(self):
        groups = [[r['error'] for r in self.outcomes if r['band']==b] for b in range(3)]
        counts = [len(g) for g in groups]
        scores = [float(min(5.,float(np.median(g[-4:]))/2) + 2/np.sqrt(len(g))) if g else None for g in groups]
        if self.policy == 'cycle': band = self.trials % 3
        elif self.policy == 'uniform': band = int(self.selector.integers(3))
        elif 0 in counts: band = counts.index(0)
        elif len(self.decisions)>=2 and self.decisions[-1]['band']==self.decisions[-2]['band']:
            previous = self.decisions[-1]['band']
            band = min((b for b in range(3) if b!=previous),key=lambda b:(counts[b],b))
        else: band = max(range(3),key=lambda b:(scores[b],-b))
        decision = {'trial':self.trials,'band':band,'counts':counts,'scores':scores,'policy':self.policy}
        self.decisions.append(decision)
        return decision

    def announce(self, observation, horizon):
        predicted = float(self.predict([observation],[horizon])[0]); margin = self.margin()
        return {'predicted':predicted,'margin':margin,'promised':abs(predicted-observation.target)+margin<=2.}

    def update(self, episodes):
        if len(episodes)!=4 or any(len(e['angles'])!=8 or e['horizon'] not in [4,6,8] or
                                  e['band'] not in [0,1,2] or not np.all(np.isfinite(e['angles'])) for e in episodes):
            raise ValueError('invalid lived trial')
        observed = []
        for e in episodes:
            actual = e['angles'][e['horizon']-1]
            error = abs(actual-e['announcement']['predicted'])
            observed.append({'band':e['band'],'error':error,'promised':e['announcement']['promised'],
                             'success':abs(actual-e['observation']['target'])<=2.})
        reference = float(np.median([r['error'] for r in self.outcomes[-12:]])) if self.outcomes else 1.
        alarm = self.trials>=6 and max(r['error'] for r in observed)>max(3.,4*reference)
        if alarm:
            self.memory_x=self.memory_x[:0].clone(); self.memory_y=self.memory_y[:0].clone(); self.outcomes=[]
        before = self.need_open
        self.outcomes=(self.outcomes+observed)[-24:]
        groups=[sum(r['band']==b for r in self.outcomes) for b in range(3)]
        promises=[r for r in self.outcomes if r['promised']]
        qualified = (len(self.outcomes)>=12 and min(groups)>=2 and
                     float(np.quantile([r['error'] for r in self.outcomes],.9))<=2. and
                     sum(r['success'] for r in promises)>=3 and all(r['success'] for r in promises))
        self.need_open = not qualified
        obs=[]; horizons=[]; targets=[]
        for e in episodes:
            o=Observation(**e['observation'])
            for h, target in enumerate(e['angles'],1): obs.append(o); horizons.append(h); targets.append(target)
        x=torch.as_tensor(inputs(obs,horizons),device=self.device)
        y=torch.as_tensor((np.array(targets,dtype=np.float32)-priors(obs,horizons))/12,device=self.device)
        for _ in range(self.updates):
            old=len(self.memory_x)>0; n=64 if old else 128
            ix=torch.randint(len(x),(n,),generator=self.generator,device=self.device); bx,by=x[ix],y[ix]
            if old:
                ix=torch.randint(len(self.memory_x),(64,),generator=self.generator,device=self.device)
                bx=torch.cat([bx,self.memory_x[ix]]); by=torch.cat([by,self.memory_y[ix]])
            self.optimizer.zero_grad(set_to_none=True)
            loss=((self.model(bx).squeeze(-1)-by)**2).mean(); loss.backward(); self.optimizer.step()
            self.total_updates+=1
        self.memory_x=torch.cat([self.memory_x,x])[-256:].clone(); self.memory_y=torch.cat([self.memory_y,y])[-256:].clone()
        self.trials+=1
        event={'trial':self.trials,'alarm':alarm,'need_open':self.need_open,'opened':not before and self.need_open,
               'closed':before and not self.need_open,'outcomes':observed,'margin':self.margin(),'counts':groups}
        self.events.append(event)
        return event

    def state(self):
        return {'format':'functional-agent-v1','initialization':self.initialization,'batches':self.batches,'selection':self.selection,
                'policy':self.policy,'updates':self.updates,'model':deepcopy(self.model.state_dict()),
                'optimizer':deepcopy(self.optimizer.state_dict()),'rng':self.generator.get_state().clone(),
                'selector':deepcopy(self.selector.bit_generator.state),'memory_x':self.memory_x.clone(),'memory_y':self.memory_y.clone(),
                **{k:deepcopy(getattr(self,k)) for k in ['outcomes','decisions','trials','total_updates','need_open','events']}}

    @classmethod
    def restore(cls,p,device='cuda'):
        if p['format']!='functional-agent-v1': raise ValueError('functional format')
        p=deepcopy(p)
        a=cls(p['initialization'],p['batches'],p['selection'],p['policy'],device,p['updates'])
        a.model.load_state_dict(p['model']); a.optimizer.load_state_dict(p['optimizer']); a.generator.set_state(p['rng'].cpu())
        a.selector.bit_generator.state=p['selector']; a.memory_x=p['memory_x'].to(device); a.memory_y=p['memory_y'].to(device)
        for k in ['outcomes','decisions','trials','total_updates','need_open','events']: setattr(a,k,p[k])
        return a
