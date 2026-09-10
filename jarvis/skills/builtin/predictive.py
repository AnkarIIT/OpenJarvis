from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler

from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class PredictiveSkill:
    name: str = "predictive"
    description: str = "Build predictive models from your data: train, predict, evaluate scenarios."
    version: str = "1.0.0"
    author: str = "OpenJarvis"

    def __init__(self, settings=None):
        self.settings = settings
        self.models: dict[str, Any] = {}
        self.scalers: dict[str, Any] = {}
        self.training_data: dict[str, Any] = {}

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="predict_train",
                description="Train a predictive model from CSV/JSON data. Usage: predict_train --file data.csv --target column_name --model linear|rf|gb",
                handler=self._train,
                skill_name=self.name,
            ),
            SkillCommand(
                name="predict_predict",
                description="Make predictions using a trained model. Usage: predict_predict --model model_name --input '{\"feature1\": value}'",
                handler=self._predict,
                skill_name=self.name,
            ),
            SkillCommand(
                name="predict_evaluate",
                description="Evaluate model accuracy with cross-validation and metrics.",
                handler=self._evaluate,
                skill_name=self.name,
            ),
            SkillCommand(
                name="predict_scenario",
                description='Run a "what-if" scenario: change input values and see predicted outcomes.',
                handler=self._scenario,
                skill_name=self.name,
            ),
            SkillCommand(
                name="predict_list_models",
                description="List all trained models and their status.",
                handler=self._list,
                skill_name=self.name,
            ),
            SkillCommand(
                name="predict_importance",
                description="Show feature importance for tree-based models.",
                handler=self._importance,
                skill_name=self.name,
            ),
        ]

    async def initialize(self, settings) -> None:
        self.settings = settings

    async def _train(self, file: str = "", target: str = "", model_type: str = "rf") -> str:
        if not file:
            return "Error: --file is required"
        if not target:
            return "Error: --target is required"

        path = Path(file)
        if not path.exists():
            return f"Error: File not found: {path}"

        try:
            import pandas as pd
        except ImportError:
            return "Error: pandas not installed. Run: pip install pandas"

        df = pd.read_csv(file)
        if target not in df.columns:
            return f"Error: Column '{target}' not found. Available: {list(df.columns)}"

        X = df.drop(columns=[target])
        y = df[target]

        # Drop non-numeric columns
        X = X.select_dtypes(include=[np.number])
        if X.empty:
            return "Error: No numeric features found in data"

        # Handle NaN
        X = X.fillna(X.mean())
        y = y.fillna(y.mean())

        # Train model
        if model_type == "linear":
            model = LinearRegression()
        elif model_type == "rf":
            model = RandomForestRegressor(n_estimators=100, random_state=42)
        elif model_type == "gb":
            model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        else:
            return f"Error: Unknown model type '{model_type}'. Use: linear, rf, gb"

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model.fit(X_train_scaled, y_train)
        train_score = model.score(X_train_scaled, y_train)
        test_score = model.score(X_test_scaled, y_test)

        model_name = f"{Path(file).stem}_{model_type}"
        self.models[model_name] = model
        self.scalers[model_name] = scaler
        self.training_data[model_name] = {
            "file": str(path),
            "target": target,
            "features": list(X.columns),
            "train_score": train_score,
            "test_score": test_score,
            "rows": len(df),
            "model_type": model_type,
        }

        return (
            f"Model trained: {model_name}\n"
            f"Type: {model_type} | Data: {len(df)} rows | Features: {len(X.columns)}\n"
            f"Train R²: {train_score:.4f} | Test R²: {test_score:.4f}"
        )

    async def _predict(self, model: str = "", input_data: str = "") -> str:
        if model not in self.models:
            return f"Error: Model '{model}' not found. Use: predict_list_models"

        try:
            features = json.loads(input_data) if input_data else {}
        except json.JSONDecodeError:
            return "Error: Invalid JSON in --input"

        m = self.models[model]
        scaler = self.scalers[model]
        feature_names = self.training_data[model]["features"]

        # Build feature vector in correct order
        values = []
        for feat in feature_names:
            if feat in features:
                values.append(features[feat])
            else:
                return f"Error: Missing feature '{feat}'. Available: {feature_names}"

        X = np.array([values])
        X_scaled = scaler.transform(X)
        prediction = m.predict(X_scaled)[0]

        return f"Prediction: {prediction:.4f}"

    async def _evaluate(self, model: str = "") -> str:
        if model not in self.models:
            return f"Error: Model '{model}' not found."

        info = self.training_data[model]
        m = self.models[model]
        scaler = self.scalers[model]

        try:
            import pandas as pd
            df = pd.read_csv(info["file"])
            target = info["target"]
            X = df.select_dtypes(include=[np.number]).fillna(df.select_dtypes(include=[np.number]).mean())
            y = df[target]
            X_scaled = scaler.transform(X)

            scores = cross_val_score(m, X_scaled, y, cv=5, scoring="r2")
            return (
                f"Cross-validation R² scores for {model}:\n"
                f"  Mean: {scores.mean():.4f} ± {scores.std():.4f}\n"
                f"  Fold scores: {[f'{s:.4f}' for s in scores]}\n"
                f"  Training R²: {info['train_score']:.4f}\n"
                f"  Test R²: {info['test_score']:.4f}"
            )
        except Exception as e:
            return f"Evaluation error: {e}"

    async def _scenario(self, model: str = "", changes: str = "") -> str:
        if model not in self.models:
            return f"Error: Model '{model}' not found."

        try:
            change_dict = json.loads(changes) if changes else {}
        except json.JSONDecodeError:
            return "Error: Invalid JSON in --changes"

        info = self.training_data[model]
        m = self.models[model]
        scaler = self.scalers[model]
        feature_names = info["features"]

        # Build base feature vector
        import pandas as pd
        df = pd.read_csv(info["file"])
        base_values = []
        for feat in feature_names:
            if feat in change_dict:
                base_values.append(change_dict[feat])
            else:
                base_values.append(df[feat].mean())

        X = np.array([base_values])
        X_scaled = scaler.transform(X)
        base_pred = m.predict(X_scaled)[0]

        # Now predict with all changes
        final_values = [change_dict.get(feat, df[feat].mean()) for feat in feature_names]
        X_final = np.array([final_values])
        X_final_scaled = scaler.transform(X_final)
        final_pred = m.predict(X_final_scaled)[0]

        diff = final_pred - base_pred
        pct = (diff / base_pred * 100) if base_pred != 0 else 0

        result_lines = [f"What-if scenario for {model}:"]
        result_lines.append(f"  Base prediction: {base_pred:.4f}")
        result_lines.append(f"  After changes: {final_pred:.4f}")
        result_lines.append(f"  Delta: {diff:+.4f} ({pct:+.1f}%)")
        result_lines.append(f"")
        result_lines.append("Changes applied:")
        for k, v in change_dict.items():
            base_val = df[k].mean() if k in df.columns else "?"
            result_lines.append(f"  {k}: {base_val} → {v}")

        return "\n".join(result_lines)

    async def _list(self) -> str:
        if not self.models:
            return "No trained models yet. Use: predict_train"
        lines = ["Trained Models:"]
        for name, info in self.training_data.items():
            lines.append(
                f"  {name}: {info['model_type']} | {info['rows']} rows | "
                f"R²={info['test_score']:.4f}"
            )
        return "\n".join(lines)

    async def _importance(self, model: str = "") -> str:
        if model not in self.models:
            return f"Error: Model '{model}' not found."

        m = self.models[model]
        info = self.training_data[model]
        feature_names = info["features"]

        if hasattr(m, "feature_importances_"):
            importances = m.feature_importances_
            sorted_idx = np.argsort(importances)[::-1]
            lines = [f"Feature Importance for {model}:"]
            for i, idx in enumerate(sorted_idx[:10]):
                lines.append(f"  {i+1}. {feature_names[idx]}: {importances[idx]:.4f}")
            return "\n".join(lines)
        else:
            return f"Model {model} has no feature importance (try tree-based models: rf, gb)"
