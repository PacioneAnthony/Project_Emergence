"""Publish measured results, including strict monitor failures, without rerunning lives."""
import hashlib
import json
from pathlib import Path
import sqlite3
import numpy as np
from learning.cumulative_001_data import ROOT
from learning.resilience_002_budget import OUTPUT


def publish():
    research=ROOT/'docs/research'
    def read(name): return json.loads((research/name).read_bytes())
    dev=read('resilience_002_dev_v2_results.json'); val=read('resilience_002_validation_v2_results.json')
    audit=read('resilience_002_validation_v2_audit.json'); diag=read('resilience_002_validation_v2_diagnostics.json')
    a=val['aggregate']; names={'cycle':'Cycle fixe','uniform':'Uniforme','need':'Selon besoin'}
    n=a['need']; mon=audit['monitor_all_checkpoints']['need']; pair=diag['paired_life_comparison']
    cases=val['heldout_cases']; count=len(val['per_life']); final_cases=count*12
    gain=val['active_gain_vs_cycle']*100
    strict=mon['strict_honesty_pass'] and n['closure_coverage']>=.5
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(15,4.7)); colors={'cycle':'#61798e','uniform':'#b38b38','need':'#137e74'}
    for p in names:
        values=[diag['curves'][phase][label][p]['oracle_fraction']*100 for phase in ['initial','perturbed','return'] for label in ['0','6','final']]
        axes[0].plot(range(9),values,'o-',color=colors[p],label=names[p])
        axes[1].plot(range(count),[v[p]['final_success']*100 for v in val['per_life'].values()],'o-',color=colors[p],label=names[p])
    axes[0].set_xticks(range(9),['I0','I6','If','P0','P6','Pf','R0','R6','Rf']); axes[0].set_ylim(0,103)
    axes[0].set_title('Utilité / maximum disponible'); axes[0].set_ylabel('% moyen par vie'); axes[0].legend(fontsize=8)
    axes[1].axhline(70,color='#b84e48',ls=':',label='Seuil minimum par vie'); axes[1].set_ylim(0,103)
    axes[1].set_xticks(range(count)); axes[1].set_title('Réussite finale après rupture'); axes[1].set_xlabel('Vie de validation'); axes[1].legend(fontsize=8)
    x=np.arange(3)
    axes[2].bar(x-.18,[a[p]['closure_coverage']*100 for p in names],.36,label='Besoin clos après apprentissage',color='#137e74')
    axes[2].bar(x+.18,[(audit['monitor_all_checkpoints'][p]['all_contradiction_rate'] or 0)*100 for p in names],.36,label='États clos contredits (tous points)',color='#b84e48')
    axes[2].set_xticks(x,list(names.values())); axes[2].set_ylim(0,103); axes[2].set_title('Moniteur : couverture et contradictions'); axes[2].set_ylabel('%'); axes[2].legend(fontsize=7.5)
    fig.suptitle(f'RESILIENCE-002 v2 — {count} nouvelles vies de validation',fontweight='bold')
    fig.text(.5,.01,'I : initial ; P : perturbation ; R : retour. 0 : avant nouvelle expérience ; 6 : après six essais ; f : fin.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.045,1,.95]); fig.savefig(research/'resilience_002_progress.png',dpi=160); plt.close(fig)
    rows='\n'.join(f'| {names[p]} | {a[p]["final_success"]*100:.2f} % | {a[p]["worst_life_success"]*100:.2f} % | {a[p]["final_oracle_fraction"]*100:.2f} % | {a[p]["post_rupture_utility"]:.3f}° |' for p in names)
    gates='\n'.join(f'| {label} | {"Passe" if result else "Échoue"} |' for label,result in [
        ('Récupération : moyenne, pire vie et utilité',n['recovery_pass']),
        ('Sélection active : gain ≥10 % contre cycle',val['active_selection_pass']),
        ('Moniteur global : <10 % de contradictions et couverture ≥50 %',strict)])
    worst=min(val['per_life'],key=lambda life:val['per_life'][life]['need']['final_oracle_fraction'])
    worst_metrics=val['per_life'][worst]['need']
    delays=[d for row in diag['per_life'].values() for d in row['policies']['need']['detection_delays'] if d is not None]
    initial_alarms=sum(row['policies']['need']['initial_alarms'] for row in diag['per_life'].values())
    with sqlite3.connect(OUTPUT/'budget.sqlite') as db:
        budget=db.execute('SELECT status,count(*),sum(charged) FROM attempts GROUP BY status').fetchall()
    body=f'''# RESILIENCE-002 — apprendre depuis ses résultats et choisir ses expériences

2026-09-10 · D-058 / D-059 · simulation MuJoCo, apprentissage CUDA sur RTX 5080.

**La récupération fonctionnelle {"passe" if n['recovery_pass'] else "ne passe pas"} ses critères sur {count} nouveaux corps.
Le choix actif {"passe" if val['active_selection_pass'] else "ne passe pas"} le seuil de gain prévu.
Le moniteur global {"passe" if strict else "reste non qualifié"}.**
La résilience générale et l'autonomie ouverte du noyau ne sont pas acquises.

![Résultats complets avec les contradictions du moniteur](resilience_002_progress.png)

## Validation sur douze vies neuves

Même recette que les six vies de développement ; nouveaux corps, poids initiaux,
graines et instants de rupture. Trois politiques disposent chacune d'un corps
physique continu, du même budget et du même modèle. Seule la sélection de catégorie
change. Le noyau reçoit ses observations et résultats vécus, sans paramètres cachés,
étiquettes de phase ou récompenses du juge.

| Politique | Réussite finale après rupture | Pire vie | Utilité finale / oracle | Utilité pendant récupération |
|---|---:|---:|---:|---:|
{rows}

L'utilité récompense la distance atteinte à l'échéance demandée, à 2° près.
La réussite finale comporte {final_cases} décisions, regroupées en {count} vies.
L'utilité pendant récupération moyenne les checkpoints 6 et fin, avec poids égal
par vie. Le gain actif contre le cycle fixe est **{gain:+.2f} %**, contre un seuil
prévu de +10 %. La stratégie active fait mieux dans {pair['need_better']} vies,
égalité dans {pair['tie']}, moins bien dans {pair['need_worse']} : son effet n'est
pas uniforme. Ces seuils sont des repères expérimentaux, pas une preuve statistique
de généralité. La moyenne des fractions oracle n'est pas un ratio global pondéré.

| Porte confirmatoire | Verdict |
|---|---|
{gates}

Le corps ayant la plus faible fraction d'utilité finale pour `need`, `{worst}`,
atteint {worst_metrics['final_oracle_fraction']*100:.2f} % de l'oracle et réussit
{worst_metrics['final_success']*100:.2f} % de ses choix. Ce cas reste dans les moyennes.
Le banc diffère de RESILIENCE-001 : aucune supériorité chiffrée entre les deux cycles
n'est déduite de leurs moyennes.

Le gain de développement (+17,77 % sur six vies) ne se reproduit pas : il devient
{gain:+.2f} % en validation. Décision : conserver le cycle fixe comme référence
simple pour la suite ; ne pas promouvoir ce sélecteur actif. Le témoin cycle passe
les portes de récupération sur cette validation, mais avait échoué à la porte
d'utilité en développement : il n'est pas déclaré robuste universellement.

## Avancée concrète dans le noyau

`FunctionalStore` persiste ensemble la décision d'expérience, les prévisions et
promesses formulées avant action, les résultats vécus et le checkpoint complet.
Poids, Adam, RNG d'entraînement et de sélection, mémoire, historique et besoin
survivent à la réouverture. Les résultats alimentent 32 exemples par essai, jamais
les futurs contrefactuels du juge. {val['exact_restarts']} reprises interprocessus
reproduisent l'état, le prochain choix et la prochaine mise à jour sur une branche
non engagée de données déjà vécues. Les corps restent en mémoire ; leurs pas sont
suspendus pendant cette sonde, sans remise à zéro ni preuve de fonctionnement temps réel.

Le choix selon besoin utilise la couverture des catégories et leurs erreurs vécues.
Il est donc lié à l'expérience propre, mais les trois catégories, le score et les
règles de clôture sont écrits. Ce n'est pas encore la découverte autonome de buts,
de concepts corporels ou d'interactions humaines. Le registre garde des candidates
expérimentales ; aucune activation universelle ou changement matériel.

## Échecs et portée du moniteur

La v1 a échoué techniquement après deux commits : un score NumPy ne se rechargeait
pas avec `weights_only=True`. Sources et vie partielle sont conservées. V2 convertit
ce score en `float` natif ; une régression teste quatre décisions et relectures.
Il n'y a eu aucun changement de formule d'apprentissage pour cette correction.

Le code d'analyse gelé compte l'honnêteté après apprentissage :
{n['contradicted']}/{n['closed']} checkpoints clos contredits, couverture
{n['closure_coverage']*100:.2f} %. Mais le protocole en prose n'excluait pas les
checkpoints immédiatement après rupture. L'audit les réintègre :
**{mon['all_contradicted']}/{mon['all_closed']} états clos contredits
({(mon['all_contradiction_rate'] or 0)*100:.2f} %)**, dont
{mon['phase_zero_contradicted']} avant nouvelle expérience et
{mon['post_learning_contradicted']} après apprentissage. La porte stricte prévaut.
Le booléen `monitor_pass` de l'analyse restreinte ne vaut pas qualification globale.

Un changement caché ne peut pas être anticipé sans indice ; le résultat montre
précisément que le besoin clos n'est pas une garantie intemporelle. Au retour d'un
corps rapide, un choix trop petit peut réussir tout en gaspillant l'essentiel de
la capacité disponible : réussite, utilité et connaissance de ses limites doivent
rester séparées. Aucun échec n'est effacé par la précision du modèle.

Le cas `validation/v2/life-03` expose un mécanisme concret : après le ralentissement,
la politique active choisit finalement 5° sur 23,333° disponibles, tout en réussissant
ses 12 actions. Sa marge globale atteint 3,515°, donc aucune cible ne satisfait le
seuil de promesse à 2° et toutes les décisions utilisent le repli vers la plus petite.
Une alarme tardive, sur une expérience de grande amplitude alors que la dynamique
n'a pas rechangé, vient de vider le rejeu et les preuves récentes. Le cycle fixe
atteint 16,667°. Cette trace montre un couplage fragile entre sélection, alarme et
marge globale ; elle ne suffit pas à attribuer toute la perte à un seul composant.
Les comptes de catégories sont proches entre politiques : leur total seul
n'explique pas l'effet de l'ordre des expériences et des réinitialisations.

Le détecteur du choix actif déclenche après {min(delays) if delays else '—'} à
{max(delays) if delays else '—'} essais pour les {len(delays)}/{count*2} changements
qu'il signale ; un essai représente 128 pas, soit 2,56 secondes simulées.
Il produit aussi {initial_alarms} alarmes dans les phases initiales sans changement
physique imposé. Ces diagnostics sont descriptifs et n'ajoutent pas de porte
ajustée après accès aux résultats.

## Traçabilité et suite

358 tests passent en 25,32 s ; interruptions après publication, avant commit et
après commit, idempotence, contenu divergent, annonces réécrites, prochaine sélection,
alias de checkpoint et continuité physique sont couverts. Le reçu donne les
versions du runtime et les empreintes des sources. L'audit vérifie
{audit['kernel_experiences_checked']} expériences du noyau et leur contenu exact,
{val['interaction_steps']['need']} pas physiques et {val['updates']['need']} updates
pour chacune des trois politiques. {cases} situations tenues à part,
{val['policy_evaluations']} décisions corrélées, {len(val['artifact_sha256'])} fichiers
bruts/checkpoints inventoriés par SHA-256. Les 375 artefacts historiques vérifiés
sont inchangés. Données locales sous `data/processed/experiments/resilience_002`,
exclues de Git : conserver ce dossier.

La suite doit distinguer compétence estimée, preuve récente et besoin d'exploration,
puis évaluer la récupération sur d'autres perturbations et distributions d'expérience.
Un nouveau protocole et de nouvelles banques précéderont toute modification ; ces
vies de validation ne doivent pas devenir un terrain de réglage. Les résultats
permettent de retenir les capacités ayant passé leurs portes, avec leurs limites.

Documents : [journal](resilience_002_log.md), [protocole](resilience_002_preregistration.md),
[validation fixée avant calcul](resilience_002_validation_v2.md),
[résultats détaillés](resilience_002_validation_v2_results.json),
[audit strict](resilience_002_validation_v2_audit.json),
[diagnostics par vie](resilience_002_validation_v2_diagnostics.json),
[tests](resilience_002_tests_receipt.json).
'''
    (research/'resilience_002_results.md').write_text(body,encoding='utf-8')
    sources=['learning/resilience_002_publish.py','learning/resilience_002_diagnostics.py','learning/resilience_002_audit.py',
             'docs/research/resilience_002_results.md','docs/research/resilience_002_progress.png']
    (research/'resilience_002_publication_receipt.json').write_text(json.dumps({'sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
        'budget_snapshot_includes_current_reservation':budget,'development_manifest':dev['manifest'],'validation_manifest':val['manifest']},indent=2),encoding='utf-8')
    print(json.dumps({'recovery':n['recovery_pass'],'selection':val['active_selection_pass'],'strict_monitor':strict,'active_gain_percent':gain,
                     'report':str(research/'resilience_002_results.md')},indent=2))


if __name__=='__main__': publish()
