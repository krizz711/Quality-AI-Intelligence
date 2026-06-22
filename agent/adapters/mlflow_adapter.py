"""MLflow adapter — logs experiments, registers models, runs predictions via MLflow."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import mlflow

from agent.adapters.base import MLToolAdapter

logger = logging.getLogger(__name__)


class MLflowAdapter(MLToolAdapter):
    """MLflow implementation of the ML tool adapter interface.

    Usage::

        adapter = MLflowAdapter(tracking_uri="http://localhost:5000")
        run_id = await adapter.log_experiment(
            "grr_studies", "study-xyz",
            params={"method": "xbar_r"},
            metrics={"grr_pct": 12.3, "ndc": 7},
        )
    """

    def __init__(self, tracking_uri: str = "http://localhost:5000") -> None:
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)

    async def log_experiment(
        self,
        experiment_name: str,
        run_name: str,
        params: dict[str, Any],
        metrics: dict[str, float],
        artifacts: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
    ) -> str:
        def _sync() -> str:
            mlflow.set_experiment(experiment_name)
            with mlflow.start_run(run_name=run_name) as run:
                if params:
                    mlflow.log_params(params)
                if metrics:
                    mlflow.log_metrics(metrics)
                if tags:
                    for k, v in tags.items():
                        mlflow.set_tag(k, v)
                if artifacts:
                    for name, content in artifacts.items():
                        mlflow.log_text(str(content), name)
                return run.info.run_id

        try:
            run_id = await asyncio.to_thread(_sync)
            logger.info("MLflow: logged run %s in experiment %s", run_id, experiment_name)
            return run_id
        except Exception:
            logger.exception("MLflow log_experiment failed")
            return ""

    async def register_model(
        self,
        model_name: str,
        model_artifact: Any,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        def _sync() -> str:
            result = mlflow.register_model(
                model_uri=str(model_artifact),
                name=model_name,
                tags=metadata or {},
            )
            return str(result.version)

        try:
            version = await asyncio.to_thread(_sync)
            logger.info("MLflow: registered model %s version %s", model_name, version)
            return version
        except Exception:
            logger.exception("MLflow register_model failed")
            return ""

    async def get_prediction(
        self,
        model_name: str,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        def _sync() -> dict[str, Any]:
            model = mlflow.pyfunc.load_model(f"models:/{model_name}/latest")
            import pandas as pd

            df = pd.DataFrame([input_data])
            prediction = model.predict(df)
            return {"prediction": prediction.tolist() if hasattr(prediction, "tolist") else list(prediction)}

        try:
            return await asyncio.to_thread(_sync)
        except Exception:
            logger.exception("MLflow get_prediction failed")
            return {"error": "prediction failed"}
