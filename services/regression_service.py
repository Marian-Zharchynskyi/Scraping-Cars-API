from typing import Dict, Any, Union
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RegressionMetrics:
    r_squared: float
    adj_r_squared: float
    f_statistic: float
    f_pvalue: float
    aic: float
    bic: float
    coefficients: Dict[str, float]
    p_values: Dict[str, float]
    conf_int: Dict[str, tuple[float, float]]


class RegressionResultsWrapper:
    def __init__(self, results: Any):
        self._results = results

    def __getattr__(self, name: str) -> Any:
        return getattr(self._results, name)

    @property
    def results(self) -> Any:
        return self._results


class RegressionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.model = None
        self._results_wrapper = None
        self.target_variable = None
        self.feature_variables = None
        self.marketplace_id = None
        self.logger = logging.getLogger(__name__)

    @property
    def results(self) -> Any:
        if self._results_wrapper is None:
            msg = "Model has not been fitted yet."
            raise ValueError(msg)
        return self._results_wrapper.results

    @results.setter
    def results(self, value: Any) -> None:
        self._results_wrapper = value

    async def train_model(self, request: Any) -> Dict[str, Any]:
        from models.scraped_car import ScrapedCar
        from models.regression_model import RegressionModel as DBRegressionModel

        try:
            self.target_variable = request.target_variable
            self.feature_variables = request.feature_variables
            self.marketplace_id = request.marketplace_id

            stmt = select(ScrapedCar).where(ScrapedCar.marketplace_id == self.marketplace_id)

            if hasattr(request, "car_brands") and request.car_brands:
                from sqlalchemy import or_

                stmt = stmt.where(or_(*[ScrapedCar.car_title.ilike(f"%{brand}%") for brand in request.car_brands]))

            result = await self.db.execute(stmt)
            data = result.scalars().all()

            if not data:
                raise ValueError("No data found for the specified criteria")

            df = pd.DataFrame(
                [
                    {
                        "price": float(car.price) if car.price and car.price.replace(".", "").isdigit() else None,
                        "year": car.year,
                        "mileage": car.mileage,
                        "engine_volume": float(car.engine_capacity.replace(" л", "").replace(",", "."))
                        if car.engine_capacity
                        and car.engine_capacity.replace(".", "").replace(",", "").replace(" л", "").isdigit()
                        else None,
                        "search_position": idx + 1,
                    }
                    for idx, car in enumerate(data)
                    if car.price and car.price.replace(".", "").isdigit()
                ]
            )

            df = df.dropna()

            if len(df) < 10:
                raise ValueError(f"Not enough valid samples for training. Found {len(df)} samples.")

            X = df[request.feature_variables]
            y = df[request.target_variable]

            self.fit_linear_regression(X, y)

            results = self.results

            model_params = results.params.to_dict()
            intercept = float(model_params.pop("const", 0))

            model_summary = {
                "dep_variable": self.target_variable,
                "model": "OLS",
                "method": "Least Squares",
                "no_observations": len(X),
                "df_model": results.df_model,
                "df_resid": results.df_resid,
                "nobs": results.nobs,
                "df": results.df_model,
                "aic": results.aic if hasattr(results, "aic") else None,
                "bic": results.bic if hasattr(results, "bic") else None,
            }

            db_model = DBRegressionModel(
                name=f"{self.target_variable}_predictor",
                target_variable=self.target_variable,
                feature_variables=self.feature_variables,
                coefficients=model_params,
                intercept=intercept,
                r_squared=float(results.rsquared),
                adj_r_squared=float(results.rsquared_adj) if hasattr(results, "rsquared_adj") else None,
                f_statistic=float(results.fvalue) if hasattr(results, "fvalue") else None,
                f_p_value=float(results.f_pvalue) if hasattr(results, "f_pvalue") else None,
                n_observations=len(X),
                model_summary=model_summary,
                standard_errors=results.bse.to_dict() if hasattr(results, "bse") else {},
                t_statistics=results.tvalues.to_dict() if hasattr(results, "tvalues") else {},
                p_values=results.pvalues.to_dict() if hasattr(results, "pvalues") else {},
                confidence_intervals={k: (v[0], v[1]) for k, v in results.conf_int().to_dict("index").items()}
                if hasattr(results, "conf_int")
                else {},
                marketplace_id=self.marketplace_id,
                description=f"Auto-generated model for {self.target_variable}",
            )
            self.db.add(db_model)
            await self.db.commit()
            await self.db.refresh(db_model)

            response = {
                "success": True,
                "model_id": db_model.id,
                "r_squared": float(results.rsquared),
                "adj_r_squared": float(results.rsquared_adj) if hasattr(results, "rsquared_adj") else None,
                "f_statistic": float(results.fvalue) if hasattr(results, "fvalue") else None,
                "f_p_value": float(results.f_pvalue) if hasattr(results, "f_pvalue") else None,
                "n_observations": int(len(X)),
                "coefficients": {k: float(v) for k, v in model_params.items()},
                "intercept": float(intercept),
                "standard_errors": {k: float(v) for k, v in results.bse.to_dict().items()}
                if hasattr(results, "bse")
                else {},
                "t_statistics": {k: float(v) for k, v in results.tvalues.to_dict().items()}
                if hasattr(results, "tvalues")
                else {},
                "p_values": {k: float(v) for k, v in results.pvalues.to_dict().items()}
                if hasattr(results, "pvalues")
                else {},
                "confidence_intervals": {
                    k: (float(v[0]), float(v[1])) for k, v in results.conf_int().to_dict("index").items()
                }
                if hasattr(results, "conf_int")
                else {},
                "message": "Model trained and saved successfully",
            }
            return response

        except Exception as e:
            await self.db.rollback()
            import traceback

            error_traceback = traceback.format_exc()
            self.logger.error(f"Error training model: {str(e)}\n{error_traceback}")
            return {
                "success": False,
                "error": f"Failed to train model: {str(e)}",
                "traceback": error_traceback.split("\n"),
            }

    async def predict(self, request: Any) -> Dict[str, Any]:
        from models.regression_model import RegressionModel as DBRegressionModel

        try:
            if hasattr(request, "model_id") and request.model_id:
                stmt = select(DBRegressionModel).where(
                    DBRegressionModel.id == request.model_id, DBRegressionModel.is_active == True
                )
            elif (
                hasattr(request, "target_variable")
                and hasattr(request, "marketplace_id")
                and request.target_variable
                and request.marketplace_id
            ):
                stmt = (
                    select(DBRegressionModel)
                    .where(
                        DBRegressionModel.target_variable == request.target_variable,
                        DBRegressionModel.marketplace_id == request.marketplace_id,
                        DBRegressionModel.is_active == True,
                    )
                    .order_by(DBRegressionModel.created_at.desc())
                    .limit(1)
                )
            else:
                raise ValueError("Either model_id or both target_variable and marketplace_id must be provided")

            result = await self.db.execute(stmt)
            model = result.scalars().first()

            if not model:
                raise ValueError("No trained model found for the specified criteria")

            input_features = {}
            for feature in model.feature_variables:
                if feature not in request.features:
                    raise ValueError(f"Missing required feature: {feature}")
                input_features[feature] = request.features[feature]

            X = pd.DataFrame([input_features])

            if "const" in model.coefficients:
                X = sm.add_constant(X)

            prediction = model.intercept
            for feature, coef in model.coefficients.items():
                if feature != "const":
                    prediction += coef * X[feature].values[0]

            return {
                "success": True,
                "prediction": float(prediction),
                "model_id": model.id,
                "features_used": input_features,
            }

        except Exception as e:
            logger.error(f"Error making prediction: {str(e)}", exc_info=True)
            return {"success": False, "error": f"Failed to make prediction: {str(e)}"}

    def fit_linear_regression(
        self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray], add_constant: bool = True
    ) -> Dict[str, Any]:
        try:
            if not isinstance(X, (pd.DataFrame, pd.Series)):
                X = pd.DataFrame(X)
            if not isinstance(y, (pd.Series, pd.DataFrame)):
                y = pd.Series(y)

            self.feature_names = X.columns.tolist() if hasattr(X, "columns") else [f"x{i}" for i in range(X.shape[1])]

            if add_constant:
                X = sm.add_constant(X)
                self.feature_names = ["const"] + self.feature_names

            model = sm.OLS(y, X)
            results = model.fit()

            self.model = model
            self._results_wrapper = RegressionResultsWrapper(results)

            if not hasattr(results, "rsquared") or results.rsquared is None:
                raise ValueError("Regression results are invalid")

            metrics_dict = {
                "r_squared": results.rsquared,
                "adj_r_squared": results.rsquared_adj,
                "f_statistic": float(results.fvalue),
                "f_pvalue": float(results.f_pvalue),
                "aic": results.aic,
                "bic": results.bic,
                "coefficients": dict(zip(self.feature_names, results.params)),
                "p_values": dict(zip(self.feature_names, results.pvalues)),
                "conf_int": {
                    col: (float(ci[0]), float(ci[1])) for col, ci in zip(self.feature_names, results.conf_int().values)
                },
            }

            metrics = RegressionMetrics(**metrics_dict)

            summary_tables = results.summary().tables
            summary = summary_tables[1].as_html() if len(summary_tables) > 1 else ""

            return {
                "success": True,
                "summary": summary,
                "metrics": metrics,
                "model_params": results.params.to_dict(),
                "residuals": results.resid.tolist(),
                "fitted_values": results.fittedvalues.tolist(),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def make_prediction(self, X: Union[pd.DataFrame, np.ndarray]) -> Dict:
        if not hasattr(self, "_results_wrapper") or self._results_wrapper is None:
            return {"success": False, "error": "Model has not been fitted yet"}

        try:
            if not isinstance(X, (pd.DataFrame, pd.Series)):
                X = pd.DataFrame(X)

            if (
                self.model is not None
                and hasattr(self.model, "exog")
                and self.model.exog is not None
                and hasattr(self.model, "exog_names")
                and self.model.exog_names is not None
                and "const" in self.model.exog_names
            ):
                X = sm.add_constant(X, has_constant="add")

            predictions = self.results.get_prediction(X)
            pred_summary = predictions.summary_frame()

            return {
                "success": True,
                "predictions": predictions.predicted_mean.tolist(),
                "prediction_intervals": {
                    "mean_ci_lower": pred_summary["mean_ci_lower"].tolist(),
                    "mean_ci_upper": pred_summary["mean_ci_upper"].tolist(),
                    "obs_ci_lower": pred_summary["obs_ci_lower"].tolist(),
                    "obs_ci_upper": pred_summary["obs_ci_upper"].tolist(),
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_model_importance(self, model_id: int) -> Dict[str, Any]:
        from models.regression_model import RegressionModel as DBRegressionModel

        try:
            stmt = select(DBRegressionModel).where(
                DBRegressionModel.id == model_id, DBRegressionModel.is_active == True
            )
            result = await self.db.execute(stmt)
            model = result.scalars().first()

            if not model:
                raise ValueError(f"No active model found with ID {model_id}")

            coefficients = model.coefficients.copy() if model.coefficients else {}
            t_stats = getattr(model, "t_statistics", {}) or {}
            p_values = getattr(model, "p_values", {}) or {}
            std_errors = getattr(model, "standard_errors", {}) or {}
            conf_intervals = getattr(model, "confidence_intervals", {}) or {}

            if coefficients is not None:
                coefficients.pop("const", None)
            if t_stats is not None:
                t_stats.pop("const", None)
            if p_values is not None:
                p_values.pop("const", None)
            if std_errors is not None:
                std_errors.pop("const", None)
            if conf_intervals is not None:
                conf_intervals.pop("const", None)

            if not coefficients:
                return {"success": False, "error": "No feature coefficients found in the model"}

            abs_coefficients = {k: abs(v) for k, v in coefficients.items()}
            total_importance = sum(abs_coefficients.values())

            if total_importance > 0:
                feature_importance = {k: v / total_importance for k, v in abs_coefficients.items()}
            else:
                feature_importance = {k: 0 for k in abs_coefficients}

            feature_analysis = {}
            for feature in coefficients.keys():
                coef = coefficients[feature]
                t_stat = t_stats.get(feature, 0)
                p_val = p_values.get(feature, 1.0)
                std_err = std_errors.get(feature, 0)
                ci_lower, ci_upper = conf_intervals.get(feature, (0, 0))

                significance = []
                if p_val < 0.01:
                    significance.append("дуже високо значимий (p < 0.01)")
                elif p_val < 0.05:
                    significance.append("значимий (p < 0.05)")
                elif p_val < 0.1:
                    significance.append("слабко значимий (p < 0.1)")
                else:
                    significance.append("незначимий (p >= 0.1)")

                interpretation = [
                    f"# {feature}",
                    f"Коефіцієнт: {coef:.4f} (Ст. помилка: {std_err:.4f})",
                    f"t-статистика: {t_stat:.4f}",
                    f"p-значення: {p_val:.4f} - {significance[0]}",
                    f"95% Довірчий інтервал: [{ci_lower:.4f}, {ci_upper:.4f}]",
                    "",
                    "## Інтерпретація:",
                    f"- За незмінних інших факторів, збільшення {feature} на одиницю пов'язане "
                    f"з {'зростанням' if coef > 0 else 'зменшенням'} цільової змінної на {abs(coef):.4f}.",
                ]

                if abs(t_stat) < 1.645:
                    interpretation.append("- Коефіцієнт не є статистично значущим на рівні 10% (|t| < 1.645).")
                else:
                    interpretation.append(
                        f"- Коефіцієнт є статистично значущим на рівні 10% (|t| = {abs(t_stat):.4f} > 1.645)."
                    )

                if ci_lower * ci_upper > 0:
                    interpretation.append(
                        f"- З імовірністю 95% справжній ефект {feature} знаходиться між {ci_lower:.4f} та {ci_upper:.4f}."
                    )
                else:
                    interpretation.append(
                        "- 95% довірчий інтервал містить нуль, що вказує на можливу статистичну незначимість ефекту."
                    )

                feature_analysis[feature] = "\n".join(interpretation)

            return {
                "success": True,
                "model_id": model_id,
                "feature_importance": feature_importance,
                "coefficients": coefficients,
                "intercept": model.intercept,
                "t_statistics": t_stats,
                "p_values": p_values,
                "standard_errors": std_errors,
                "confidence_intervals": conf_intervals,
                "feature_analysis": feature_analysis,
                "model_summary": {
                    "r_squared": model.r_squared,
                    "adj_r_squared": getattr(model, "adj_r_squared", None),
                    "f_statistic": getattr(model, "f_statistic", None),
                    "f_p_value": getattr(model, "f_p_value", None),
                    "n_observations": getattr(model, "n_observations", None),
                },
            }

        except Exception as e:
            logger.error(f"Error getting model importance: {str(e)}", exc_info=True)
            return {"success": False, "error": f"Failed to get model importance: {str(e)}"}

    async def get_coefficients_plot(self, model_id: int) -> bytes:
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            from io import BytesIO

            importance_data = await self.get_model_importance(model_id)
            if not importance_data["success"]:
                raise ValueError(importance_data.get("error", "Failed to get model importance"))

            features = list(importance_data["coefficients"].keys())
            coefficients = list(importance_data["coefficients"].values())
            importance = [importance_data["feature_importance"].get(f, 0) for f in features]

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))

            sns.barplot(x=coefficients, y=features, ax=ax1, palette="viridis")
            ax1.axvline(x=0, color="red", linestyle="--")
            ax1.set_title("Regression Coefficients")
            ax1.set_xlabel("Coefficient Value")
            ax1.set_ylabel("Features")

            for i, v in enumerate(coefficients):
                ax1.text(v, i, f" {v:.2f}", color="black", va="center")

            sns.barplot(x=importance, y=features, ax=ax2, palette="rocket")
            ax2.set_title("Feature Importance (Normalized)")
            ax2.set_xlabel("Relative Importance (0-1)")
            ax2.set_ylabel("")

            for i, v in enumerate(importance):
                ax2.text(v, i, f" {v:.2f}", color="black", va="center")

            plt.tight_layout()

            img = BytesIO()
            plt.savefig(img, format="png", dpi=100, bbox_inches="tight")
            plt.close(fig)
            img.seek(0)

            return img.getvalue()

        except Exception as e:
            logger.error(f"Error generating coefficients plot: {str(e)}", exc_info=True)
            raise

    def get_diagnostic_plots(self) -> Dict:
        try:
            try:
                import matplotlib.pyplot as plt
            except ImportError:
                return {
                    "success": False,
                    "error": "matplotlib is required for diagnostic plots. Install with: pip install matplotlib",
                }

            try:
                import statsmodels.graphics.regressionplots as sm_plots

                _ = sm_plots
            except ImportError:
                return {"success": False, "error": "statsmodels.graphics is required for diagnostic plots"}

            if self.results is None:
                return {"success": False, "error": "Model has not been fitted yet"}

            import tempfile
            import os

            temp_dir = tempfile.mkdtemp()
            plot_paths = {}

            plt.figure(figsize=(10, 6))
            plt.scatter(self.results.fittedvalues, self.results.resid, alpha=0.6)
            plt.axhline(y=0, color="r", linestyle="--")
            plt.xlabel("Fitted values")
            plt.ylabel("Residuals")
            plt.title("Residuals vs Fitted")
            residuals_path = os.path.join(temp_dir, "residuals_vs_fitted.png")
            plt.savefig(residuals_path)
            plt.close()
            plot_paths["residuals_vs_fitted"] = residuals_path

            plt.figure(figsize=(10, 6))
            sm.qqplot(self.results.resid, line="s", ax=plt.gca())
            plt.title("Q-Q Plot of Residuals")
            qq_path = os.path.join(temp_dir, "qq_plot.png")
            plt.savefig(qq_path)
            plt.close()
            plot_paths["qq_plot"] = qq_path

            plt.figure(figsize=(10, 6))
            plt.scatter(
                self.results.fittedvalues,
                np.sqrt(np.abs(self.results.get_influence().resid_studentized_internal)),
                alpha=0.6,
            )
            plt.xlabel("Fitted values")
            plt.ylabel("Sqrt(|Standardized Residuals|)")
            plt.title("Scale-Location Plot")
            scale_loc_path = os.path.join(temp_dir, "scale_location.png")
            plt.savefig(scale_loc_path)
            plt.close()
            plot_paths["scale_location"] = scale_loc_path

            return {"success": True, "plot_paths": plot_paths}

        except Exception as e:
            return {"success": False, "error": f"Error generating diagnostic plots: {str(e)}"}
