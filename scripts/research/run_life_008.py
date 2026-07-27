"""Run or resume the bounded LIFE-008 endurance qualification."""

from __future__ import annotations

import json
from pathlib import Path

from cognitive.competence import EXECUTED_TRACKING_METRIC, UpperBoundCriterion
from cognitive.endurance import EnduranceConfig, run_endurance_campaign
from cognitive.experiments import SafeExperimentCatalog
from cognitive.models import ExperimentSignals, ExperimentSpec, SafetyContext
from cognitive.needs import CompetenceNeedRoute, PersistentNeedActivator
from cognitive.supervisor import (
    CompetenceEvaluationRoute,
    PersistentDevelopmentSupervisor,
)
from sim3d.life_executor import BoundedMujocoExecutor


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data" / "processed" / "experiments" / "life_008_endurance"


def build_catalog() -> SafeExperimentCatalog:
    return SafeExperimentCatalog(
        [
            ExperimentSpec(
                "diagnose-servo",
                "diagnose_bounded_servo",
                max_predicted_risk=0.5,
                max_motor_cost=0.8,
                max_proposals_per_session=100,
            )
        ]
    )


def build_supervisor(data_root: Path) -> PersistentDevelopmentSupervisor:
    prior = ExperimentSignals(
        epistemic_gain=0.9,
        learning_progress=0.2,
        novelty=0.2,
        controllability=0.5,
        predicted_risk=0.0,
        motor_cost=0.1,
    )
    route = CompetenceNeedRoute(
        competence_name="bounded_servo_tracking",
        cold_start_signals={"diagnose-servo": prior},
        unknown_experiments=("diagnose-servo",),
        learning_experiments=("diagnose-servo",),
        candidate_experiments=("diagnose-servo",),
        validated_experiments=("diagnose-servo",),
        regressed_experiments=("diagnose-servo",),
    )
    evaluation = CompetenceEvaluationRoute(
        competence_name="bounded_servo_tracking",
        criterion=UpperBoundCriterion(
            EXECUTED_TRACKING_METRIC,
            validation_upper_bound=9.0,
            regression_upper_bound=15.0,
            min_samples=2,
        ),
        window_size=2,
        model_version="analytic-tracking-v1",
    )
    return PersistentDevelopmentSupervisor(
        PersistentNeedActivator((route,)),
        BoundedMujocoExecutor(data_root),
        evaluations={"diagnose-servo": evaluation},
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data_root = OUTPUT / "j0"
    report = run_endurance_campaign(
        OUTPUT / "memory.sqlite3",
        data_root,
        catalog=build_catalog(),
        supervisor=build_supervisor(data_root),
        safety=SafetyContext(
            emergency_stop=False,
            hardware_healthy=True,
            model_update_in_progress=False,
            quota_state="ok",
            allowed_primitives=frozenset({"diagnose_bounded_servo"}),
        ),
        config=EnduranceConfig(),
        report_path=OUTPUT / "report.json",
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
