import os
import sys

import mlflow
from dotenv import load_dotenv


GRR_EXPERIMENT_NAME = "grr_studies"
SPC_EXPERIMENT_NAME = "spc_models"


def configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def get_or_create_experiment(name: str) -> str:
    experiment = mlflow.get_experiment_by_name(name)
    if experiment is not None:
        return experiment.experiment_id

    return mlflow.create_experiment(name)


def main() -> None:
    configure_console_encoding()
    load_dotenv()

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)

    grr_experiment_id = get_or_create_experiment(GRR_EXPERIMENT_NAME)
    spc_experiment_id = get_or_create_experiment(SPC_EXPERIMENT_NAME)

    print(f"{GRR_EXPERIMENT_NAME} experiment ID: {grr_experiment_id}")
    print(f"{SPC_EXPERIMENT_NAME} experiment ID: {spc_experiment_id}")

    with mlflow.start_run(experiment_id=grr_experiment_id) as run:
        mlflow.log_params(
            {
                "equipment_id": "CMM-001-TEST",
                "n_operators": 3,
                "n_parts": 10,
                "n_trials": 3,
                "method": "xbar_r",
            }
        )
        mlflow.log_metrics(
            {
                "ev": 0.015,
                "av": 0.008,
                "pv": 0.120,
                "grr_pct": 18.5,
                "ndc": 9,
            }
        )
        mlflow.set_tags(
            {
                "status": "conditional",
                "run_type": "synthetic_test",
                "equipment_id": "CMM-001-TEST",
            }
        )
        run_id = run.info.run_id

    retrieved_run = mlflow.get_run(run_id)
    assert retrieved_run.data.metrics["grr_pct"] == 18.5

    print(f"Setup complete. Run ID: {run_id}")
    print(f"View at: {tracking_uri.rstrip('/')}/#/experiments/{grr_experiment_id}/runs/{run_id}")


if __name__ == "__main__":
    main()
