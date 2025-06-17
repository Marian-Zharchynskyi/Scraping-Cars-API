from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from typing import Any, TypeVar, Generic, Dict, Union
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging

# Type aliases
ArrayLike = Union[np.ndarray, pd.Series, pd.DataFrame]
T = TypeVar('T', bound='RegressionResultsWrapper')  # Type variable for statsmodels results

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RegressionMetrics:
    """Container for regression model metrics."""
    r_squared: float
    adj_r_squared: float
    f_statistic: float
    f_pvalue: float
    aic: float
    bic: float
    coefficients: Dict[str, float]
    p_values: Dict[str, float]
    conf_int: Dict[str, tuple[float, float]]

class RegressionResultsWrapper(Generic[T]):
    """Wrapper class for statsmodels regression results with proper typing."""
    def __init__(self, results: T):
        self._results = results
    
    def __getattr__(self, name: str) -> Any:
        return getattr(self._results, name)
    
    @property
    def results(self) -> T:
        return self._results


class RegressionService:
    """
    A service class for performing regression analysis using statsmodels.
    Provides methods for training models, making predictions, and managing model persistence.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the regression service with a database session.
        
        Args:
            db: SQLAlchemy async database session
        """
        self.db = db
        self.model = None
        self._results_wrapper = None  # Initialize the private variable
        self.target_variable = None
        self.feature_variables = None
        self.marketplace_id = None
        self.logger = logging.getLogger(__name__)

    @property
    def results(self) -> Any:
        """Get the fitted regression results."""
        if self._results_wrapper is None:
            msg = "Model has not been fitted yet."
            raise ValueError(msg)
        return self._results_wrapper.results
        
    @results.setter
    def results(self, value: Any) -> None:
        """Set the regression results wrapper."""
        self._results_wrapper = value
    
    async def train_model(self, request: Any) -> Dict[str, Any]:
        """
        Train a regression model based on the provided request.
        
        Args:
            request: ModelTrainingRequest containing training parameters
            
        Returns:
            Dict containing training results and model information
        """
        from models.scraped_car import ScrapedCar
        from models.regression_model import RegressionModel as DBRegressionModel
        
        try:
            self.target_variable = request.target_variable
            self.feature_variables = request.feature_variables
            self.marketplace_id = request.marketplace_id
            
            # Query data from scraped_cars table using async
            stmt = select(ScrapedCar).where(
                ScrapedCar.marketplace_id == self.marketplace_id
            )
            
            if hasattr(request, 'car_brands') and request.car_brands:
                from sqlalchemy import or_
                stmt = stmt.where(
                    or_(*[ScrapedCar.car_title.ilike(f'%{brand}%') for brand in request.car_brands])
                )
                
            result = await self.db.execute(stmt)
            data = result.scalars().all()
            
            if not data:
                raise ValueError("No data found for the specified criteria")
                
            # Convert to DataFrame
            df = pd.DataFrame([{
                'price': float(car.price) if car.price and car.price.replace('.', '').isdigit() else None,
                'year': car.year,
                'mileage': car.mileage,
                'engine_volume': float(car.engine_capacity.replace(' л', '').replace(',', '.')) if car.engine_capacity and car.engine_capacity.replace('.', '').replace(',', '').replace(' л', '').isdigit() else None,
                'search_position': idx + 1  # Assuming position is the order in the results
            } for idx, car in enumerate(data) if car.price and car.price.replace('.', '').isdigit()])
            
            # Drop rows with missing values
            df = df.dropna()
            
            if len(df) < 10:  # Minimum number of samples required
                raise ValueError(f"Not enough valid samples for training. Found {len(df)} samples.")
            
            # Prepare features and target
            X = df[request.feature_variables]
            y = df[request.target_variable]
            
            # Fit the model
            self.fit_linear_regression(X, y)
            
            # Get the results once to avoid multiple property calls
            results = self.results
            
            # Extract model statistics
            model_params = results.params.to_dict()
            intercept = float(model_params.pop('const', 0))
            
            # Create model summary dictionary
            model_summary = {
                'dep_variable': self.target_variable,
                'model': 'OLS',
                'method': 'Least Squares',
                'no_observations': len(X),
                'df_model': results.df_model,
                'df_resid': results.df_resid,
                'nobs': results.nobs,
                'df': results.df_model,
                'aic': results.aic if hasattr(results, 'aic') else None,
                'bic': results.bic if hasattr(results, 'bic') else None,
            }
            
            # Save model to database with all metrics
            db_model = DBRegressionModel(
                name=f"{self.target_variable}_predictor",
                target_variable=self.target_variable,
                feature_variables=self.feature_variables,
                coefficients=model_params,
                intercept=intercept,
                r_squared=float(results.rsquared),
                adj_r_squared=float(results.rsquared_adj) if hasattr(results, 'rsquared_adj') else None,
                f_statistic=float(results.fvalue) if hasattr(results, 'fvalue') else None,
                f_p_value=float(results.f_pvalue) if hasattr(results, 'f_pvalue') else None,
                n_observations=len(X),
                model_summary=model_summary,
                standard_errors=results.bse.to_dict() if hasattr(results, 'bse') else {},
                t_statistics=results.tvalues.to_dict() if hasattr(results, 'tvalues') else {},
                p_values=results.pvalues.to_dict() if hasattr(results, 'pvalues') else {},
                confidence_intervals={
                    k: (v[0], v[1]) 
                    for k, v in results.conf_int().to_dict('index').items()
                } if hasattr(results, 'conf_int') else {},
                marketplace_id=self.marketplace_id,
                description=f"Auto-generated model for {self.target_variable}"
            )
            self.db.add(db_model)
            await self.db.commit()
            await self.db.refresh(db_model)
            
            # Prepare the response according to ModelTrainingResponse schema
            response = {
                'success': True,
                'model_id': db_model.id,
                'r_squared': float(results.rsquared),
                'adj_r_squared': float(results.rsquared_adj) if hasattr(results, 'rsquared_adj') else None,
                'f_statistic': float(results.fvalue) if hasattr(results, 'fvalue') else None,
                'f_p_value': float(results.f_pvalue) if hasattr(results, 'f_pvalue') else None,
                'n_observations': int(len(X)),  # Convert to int as per schema
                'coefficients': {k: float(v) for k, v in model_params.items()},
                'intercept': float(intercept),
                'standard_errors': {k: float(v) for k, v in results.bse.to_dict().items()} if hasattr(results, 'bse') else {},
                't_statistics': {k: float(v) for k, v in results.tvalues.to_dict().items()} if hasattr(results, 'tvalues') else {},
                'p_values': {k: float(v) for k, v in results.pvalues.to_dict().items()} if hasattr(results, 'pvalues') else {},
                'confidence_intervals': {
                    k: (float(v[0]), float(v[1])) 
                    for k, v in results.conf_int().to_dict('index').items()
                } if hasattr(results, 'conf_int') else {},
                'message': 'Model trained and saved successfully'
            }
            return response
            
        except Exception as e:
            await self.db.rollback()
            import traceback
            error_traceback = traceback.format_exc()
            self.logger.error(f"Error training model: {str(e)}\n{error_traceback}")
            return {
                'success': False,
                'error': f"Failed to train model: {str(e)}",
                'traceback': error_traceback.split('\n')  # Include full traceback for debugging
            }
    
    async def predict(self, request: Any) -> Dict[str, Any]:
        """
        Make a prediction using a trained regression model.
        
        Args:
            request: ModelPredictionRequest containing prediction parameters
            
        Returns:
            Dict containing prediction results
        """
        # Import models locally to avoid circular imports
        from models.regression_model import RegressionModel as DBRegressionModel
        
        try:
            # First try to get model by ID if provided
            if hasattr(request, 'model_id') and request.model_id:
                stmt = select(DBRegressionModel).where(
                    DBRegressionModel.id == request.model_id,
                    DBRegressionModel.is_active == True
                )
            # Fall back to target_variable and marketplace_id if no model_id
            elif hasattr(request, 'target_variable') and hasattr(request, 'marketplace_id') and request.target_variable and request.marketplace_id:
                stmt = select(DBRegressionModel).where(
                    DBRegressionModel.target_variable == request.target_variable,
                    DBRegressionModel.marketplace_id == request.marketplace_id,
                    DBRegressionModel.is_active == True
                ).order_by(DBRegressionModel.created_at.desc()).limit(1)
            else:
                raise ValueError("Either model_id or both target_variable and marketplace_id must be provided")
            
            result = await self.db.execute(stmt)
            model = result.scalars().first()
            
            if not model:
                raise ValueError("No trained model found for the specified criteria")
            
            # Prepare input features
            input_features = {}
            for feature in model.feature_variables:
                if feature not in request.features:
                    raise ValueError(f"Missing required feature: {feature}")
                input_features[feature] = request.features[feature]
            
            # Convert to DataFrame for prediction
            X = pd.DataFrame([input_features])
            
            # Add constant if model was trained with one
            if 'const' in model.coefficients:
                X = sm.add_constant(X)
            
            # Make prediction
            prediction = model.intercept
            for feature, coef in model.coefficients.items():
                if feature != 'const':
                    prediction += coef * X[feature].iloc[0]
            
            return {
                'success': True,
                'prediction': float(prediction),
                'model_id': model.id,
                'features_used': input_features
            }
            
        except Exception as e:
            logger.error(f"Error making prediction: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Failed to make prediction: {str(e)}"
            }

    def fit_linear_regression(self, 
                            X: Union[pd.DataFrame, np.ndarray], 
                            y: Union[pd.Series, np.ndarray],
                            add_constant: bool = True) -> Dict[str, Any]:
        """
        Fit a linear regression model to the data.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target variable (n_samples,)
            add_constant: Whether to add a constant term to the model

        Returns:
            dict: Dictionary containing model summary and metrics
        """
        try:
            # Convert to pandas DataFrame/Series if not already
            if not isinstance(X, (pd.DataFrame, pd.Series)):
                X = pd.DataFrame(X)
            if not isinstance(y, (pd.Series, pd.DataFrame)):
                y = pd.Series(y)

            # Store feature names
            self.feature_names = X.columns.tolist() if hasattr(X, 'columns') else [f'x{i}' for i in range(X.shape[1])]
            
            # Add constant if specified
            if add_constant:
                X = sm.add_constant(X)
                self.feature_names = ['const'] + self.feature_names

            # Fit the model
            model = sm.OLS(y, X)
            results = model.fit()
            
            # Store model and results
            self.model = model
            self._results_wrapper = RegressionResultsWrapper(results)
            
            # Get result attributes with type checking
            if not hasattr(results, 'rsquared') or results.rsquared is None:
                raise ValueError("Regression results are invalid")
                
            # Prepare metrics
            metrics_dict = {
                'r_squared': results.rsquared,
                'adj_r_squared': results.rsquared_adj,
                'f_statistic': float(results.fvalue),
                'f_pvalue': float(results.f_pvalue),
                'aic': results.aic,
                'bic': results.bic,
                'coefficients': dict(zip(self.feature_names, results.params)),
                'p_values': dict(zip(self.feature_names, results.pvalues)),
                'conf_int': {
                    col: (float(ci[0]), float(ci[1])) 
                    for col, ci in zip(self.feature_names, results.conf_int().values)
                }
            }
            
            # Create metrics object
            metrics = RegressionMetrics(**metrics_dict)
            
            # Get summary
            summary_tables = results.summary().tables
            summary = summary_tables[1].as_html() if len(summary_tables) > 1 else ""
            
            return {
                'success': True,
                'summary': summary,
                'metrics': metrics,
                'model_params': results.params.to_dict(),
                'residuals': results.resid.tolist(),
                'fitted_values': results.fittedvalues.tolist()
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def make_prediction(self, X: Union[pd.DataFrame, np.ndarray]) -> Dict:
        """
        Make predictions using the fitted model.

        Args:
            X: Feature matrix for prediction (n_samples, n_features)

        Returns:
            dict: Dictionary containing predictions and prediction intervals
        """
        if not hasattr(self, '_results_wrapper') or self._results_wrapper is None:
            return {'success': False, 'error': 'Model has not been fitted yet'}

        try:
            # Convert to pandas DataFrame if not already
            if not isinstance(X, (pd.DataFrame, pd.Series)):
                X = pd.DataFrame(X)


            # Add constant if the model was trained with one
            if (self.model is not None and 
                hasattr(self.model, 'exog') and 
                self.model.exog is not None and 
                hasattr(self.model, 'exog_names') and 
                self.model.exog_names is not None and 
                'const' in self.model.exog_names):
                X = sm.add_constant(X, has_constant='add')

            # Make predictions
            predictions = self.results.get_prediction(X)
            pred_summary = predictions.summary_frame()

            return {
                'success': True,
                'predictions': predictions.predicted_mean.tolist(),
                'prediction_intervals': {
                    'mean_ci_lower': pred_summary['mean_ci_lower'].tolist(),
                    'mean_ci_upper': pred_summary['mean_ci_upper'].tolist(),
                    'obs_ci_lower': pred_summary['obs_ci_lower'].tolist(),
                    'obs_ci_upper': pred_summary['obs_ci_upper'].tolist()
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def get_model_importance(self, model_id: int) -> Dict[str, Any]:
        """
        Get feature importance for a trained regression model.
        
        Args:
            model_id: ID of the trained model
            
        Returns:
            Dict containing feature importance metrics
        """
        from models.regression_model import RegressionModel as DBRegressionModel
        
        try:
            # Get the model from database
            stmt = select(DBRegressionModel).where(
                DBRegressionModel.id == model_id,
                DBRegressionModel.is_active == True
            )
            result = await self.db.execute(stmt)
            model = result.scalars().first()
            
            if not model:
                raise ValueError(f"No active model found with ID {model_id}")
            
            # Calculate relative importance (absolute values of coefficients, normalized to sum to 1)
            coefficients = model.coefficients
            
            # Remove 'const' if present
            coefficients.pop('const', None)
            
            if not coefficients:
                return {
                    'success': False,
                    'error': 'No feature coefficients found in the model'
                }
            
            # Calculate absolute values of coefficients
            abs_coefficients = {k: abs(v) for k, v in coefficients.items()}
            total_importance = sum(abs_coefficients.values())
            
            # Normalize to get relative importance (sum to 1)
            if total_importance > 0:
                feature_importance = {k: v / total_importance for k, v in abs_coefficients.items()}
            else:
                feature_importance = {k: 0 for k in abs_coefficients}
            
            return {
                'success': True,
                'model_id': model_id,
                'feature_importance': feature_importance,
                'coefficients': coefficients,
                'intercept': model.intercept
            }
            
        except Exception as e:
            logger.error(f"Error getting model importance: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Failed to get model importance: {str(e)}"
            }
    
    async def get_coefficients_plot(self, model_id: int) -> bytes:
        """
        Generate a bar plot of regression coefficients and their importance.
        
        Args:
            model_id: ID of the model to visualize
            
        Returns:
            bytes: PNG image data of the plot
        """
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            from io import BytesIO
            
            # Get model importance data
            importance_data = await self.get_model_importance(model_id)
            if not importance_data['success']:
                raise ValueError(importance_data.get('error', 'Failed to get model importance'))
            
            # Prepare data for plotting
            features = list(importance_data['coefficients'].keys())
            coefficients = list(importance_data['coefficients'].values())
            importance = [importance_data['feature_importance'].get(f, 0) for f in features]
            
            # Create figure with two subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
            
            # Plot coefficients
            sns.barplot(x=coefficients, y=features, ax=ax1, palette='viridis')
            ax1.axvline(x=0, color='red', linestyle='--')
            ax1.set_title('Regression Coefficients')
            ax1.set_xlabel('Coefficient Value')
            ax1.set_ylabel('Features')
            
            # Add coefficient values on bars
            for i, v in enumerate(coefficients):
                ax1.text(v, i, f' {v:.2f}', color='black', va='center')
            
            # Plot feature importance
            sns.barplot(x=importance, y=features, ax=ax2, palette='rocket')
            ax2.set_title('Feature Importance (Normalized)')
            ax2.set_xlabel('Relative Importance (0-1)')
            ax2.set_ylabel('')
            
            # Add importance values on bars
            for i, v in enumerate(importance):
                ax2.text(v, i, f' {v:.2f}', color='black', va='center')
            
            plt.tight_layout()
            
            # Save plot to bytes
            img = BytesIO()
            plt.savefig(img, format='png', dpi=100, bbox_inches='tight')
            plt.close(fig)
            img.seek(0)
            
            return img.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating coefficients plot: {str(e)}", exc_info=True)
            raise
    
    def get_diagnostic_plots(self) -> Dict:
        """
        Generate diagnostic plots for the regression model.
        
        Returns:
            dict: Dictionary containing paths to generated plot images
        """
        try:
            # Import plotting libraries only when needed
            try:
                import matplotlib.pyplot as plt  # type: ignore
            except ImportError:
                return {'success': False, 'error': 'matplotlib is required for diagnostic plots. Install with: pip install matplotlib'}
            
            try:
                import statsmodels.graphics.regressionplots as sm_plots  # type: ignore
                _ = sm_plots  # Avoid unused import warning
            except ImportError:
                return {'success': False, 'error': 'statsmodels.graphics is required for diagnostic plots'}
            
            if self.results is None:
                return {'success': False, 'error': 'Model has not been fitted yet'}

            # Create a temporary directory for plots
            import tempfile
            import os
            
            temp_dir = tempfile.mkdtemp()
            plot_paths = {}
            
            # Residuals vs Fitted plot
            plt.figure(figsize=(10, 6))
            plt.scatter(self.results.fittedvalues, self.results.resid, alpha=0.6)
            plt.axhline(y=0, color='r', linestyle='--')
            plt.xlabel('Fitted values')
            plt.ylabel('Residuals')
            plt.title('Residuals vs Fitted')
            residuals_path = os.path.join(temp_dir, 'residuals_vs_fitted.png')
            plt.savefig(residuals_path)
            plt.close()
            plot_paths['residuals_vs_fitted'] = residuals_path
            
            # Q-Q plot
            plt.figure(figsize=(10, 6))
            sm.qqplot(self.results.resid, line='s', ax=plt.gca())
            plt.title('Q-Q Plot of Residuals')
            qq_path = os.path.join(temp_dir, 'qq_plot.png')
            plt.savefig(qq_path)
            plt.close()
            plot_paths['qq_plot'] = qq_path
            
            # Scale-Location plot
            plt.figure(figsize=(10, 6))
            plt.scatter(self.results.fittedvalues, np.sqrt(np.abs(self.results.get_influence().resid_studentized_internal)), alpha=0.6)
            plt.xlabel('Fitted values')
            plt.ylabel('Sqrt(|Standardized Residuals|)')
            plt.title('Scale-Location Plot')
            scale_loc_path = os.path.join(temp_dir, 'scale_location.png')
            plt.savefig(scale_loc_path)
            plt.close()
            plot_paths['scale_location'] = scale_loc_path
            
            return {
                'success': True,
                'plot_paths': plot_paths
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error generating diagnostic plots: {str(e)}'
            }
