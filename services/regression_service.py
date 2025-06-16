import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
from fastapi import HTTPException
from pandas import DataFrame, Series
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sqlalchemy.orm import Session

from crud.regression_model import create_model, get_active_model, get_model
from models.scraped_car import ScrapedCar
from schemas.regression_model import ModelPredictionRequest, ModelTrainingRequest

logger = logging.getLogger(__name__)

class RegressionService:
    def __init__(self, db: Session):
        self.db = db
    
    def _prepare_data(
        self,
        marketplace_id: Optional[int],
        target_variable: str,
        feature_variables: List[str],
        car_brands: Optional[List[str]] = None
    ) -> Tuple[DataFrame, Series]:
        
        from sqlalchemy import or_
        
        try:
            # Перевіряємо наявність колонок у моделі
            valid_columns = [col.name for col in ScrapedCar.__table__.columns]
            missing_columns = [col for col in [target_variable] + feature_variables 
                             if col not in valid_columns]
            
            if missing_columns:
                raise ValueError(f"Наступні колонки не знайдені: {', '.join(missing_columns)}")
            
            # Створюємо базовий запит
            query = self.db.query(ScrapedCar)
            
            # Застосовуємо фільтр за маркетплейсом, якщо вказано
            if marketplace_id is not None:
                query = query.filter(ScrapedCar.marketplace_id == marketplace_id)
            
            # Застосовуємо фільтр за маркою, якщо вказано
            if car_brands:
                brand_conditions = []
                for brand in car_brands:
                    brand_lower = brand.lower().strip()
                    brand_conditions.append(ScrapedCar.car_title.ilike(f"{brand_lower}%"))
                    brand_conditions.append(ScrapedCar.car_title.ilike(f"% {brand_lower}%"))
                query = query.filter(or_(*brand_conditions))
            
            # Отримуємо тільки необхідні колонки
            columns_to_select = [getattr(ScrapedCar, col) for col in [target_variable] + feature_variables]
            query = query.with_entities(*columns_to_select)
            
            # Виконуємо запит і отримуємо результати
            results = query.all()
            
            if not results:
                brands_str = f" для марок: {', '.join(car_brands)}" if car_brands else ""
                raise ValueError(f"Не знайдено даних для навчання моделі{brands_str}")
            
            # Конвертуємо результати у DataFrame
            df = pd.DataFrame(
                [dict(zip([target_variable] + feature_variables, row)) 
                 for row in results]
            )
            
            # Видаляємо рядки з відсутніми значеннями
            df = df.dropna()
            
            if df.empty:
                raise ValueError("Після видалення відсутніх значень залишилося 0 рядків")
            
            # Функція для конвертації значень у числовий формат
            def to_numeric_series(s: pd.Series) -> pd.Series:
                if pd.api.types.is_numeric_dtype(s):
                    return s
                return pd.to_numeric(
                    s.astype(str).str.replace(r'[^\d.]', '', regex=True), 
                    errors='coerce'
                )
            
            # Конвертуємо цільову змінну та ознаки
            y = to_numeric_series(df[target_variable])
            X = df[feature_variables].apply(to_numeric_series)
            
            # Видаляємо рядки з NaN, які могли з'явитись після конвертації
            valid_mask = ~(X.isna().any(axis=1) | y.isna())
            X = X[valid_mask]
            y = y[valid_mask]
            
            if X.empty:
                raise ValueError("Після конвертації типів залишилося 0 рядків")
            
            # Логуємо кількість знайдених записів
            logger.info(f"Знайдено {len(X)} записів для аналізу")
            if car_brands:
                logger.info(f"Фільтрація за марками: {', '.join(car_brands)}")
                
            return X, y
            
        except Exception as e:
            logger.error(f"Помилка при підготовці даних: {str(e)}", exc_info=True)
            raise ValueError(f"Помилка при підготовці даних: {str(e)}") from e
    
    def train_model(self, training_request: ModelTrainingRequest) -> Dict[str, Any]:
        
        try:
            logger.info(f"Початок навчання моделі для цільової змінної: {training_request.target_variable}")
            
            # Підготовка даних з урахуванням фільтрів
            X, y = self._prepare_data(
                marketplace_id=training_request.marketplace_id,
                target_variable=training_request.target_variable,
                feature_variables=training_request.feature_variables,
                car_brands=training_request.car_brands
            )
            
            # Розподіл на навчальну та тестову вибірки
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, 
                test_size=training_request.test_size,
                random_state=training_request.random_state
            )
            
            logger.info(f"Розмір навчальної вибірки: {len(X_train)}, тестової: {len(X_test)}")
            
            # Навчання моделі
            model = LinearRegression()
            model.fit(X_train, y_train)
            
            # Оцінка моделі
            y_pred = model.predict(X_test)
            r2 = r2_score(y_test, y_pred)
            mse = mean_squared_error(y_test, y_pred)
            
            # Створення словника з даними моделі
            model_data = {
                'name': f"Regression model for {training_request.target_variable}",
                'target_variable': training_request.target_variable,
                'feature_variables': training_request.feature_variables,
                'marketplace_id': training_request.marketplace_id,
                'car_brands': training_request.car_brands,
                'coefficients': dict(zip(training_request.feature_variables, model.coef_)),
                'intercept': float(model.intercept_),
                'r_squared': float(r2),
                'mse': float(mse),
                'n_samples': len(X),
                'feature_names': training_request.feature_variables
            }
            
            # Зберігаємо модель у базі даних
            db_model = create_model(self.db, model_data)
            self.db.commit()
            
            # Обчислюємо важливість ознак
            feature_importance = self._get_feature_importance(
                dict(zip(training_request.feature_variables, model.coef_))
            )
            
            return {
                'model_id': db_model.id,
                'model_name': db_model.name,
                'target_variable': db_model.target_variable,
                'r_squared': r2,
                'mse': mse,
                'n_samples': len(X),
                'feature_importance': feature_importance,
                'car_brands': training_request.car_brands,
                'marketplace_id': training_request.marketplace_id
            }
            
        except Exception as e:
            error_msg = f"Помилка при навчанні моделі: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg) from e
    
    def predict(self, prediction_request: ModelPredictionRequest) -> Dict[str, Any]:
        
        # Отримуємо активну модель для цільової змінної та маркетплейсу
        model = get_active_model(
            self.db,
            target_variable=prediction_request.target_variable,
            marketplace_id=prediction_request.marketplace_id
        )
        
        if not model:
            raise ValueError(f"No active model found for target variable '{prediction_request.target_variable}' "
                              f"and marketplace_id={prediction_request.marketplace_id}")
        
        # Перевіряємо, чи всі необхідні ознаки надані
        missing_features = set(model.feature_variables) - set(prediction_request.features.keys())
        if missing_features:
            raise ValueError(f"Missing required features: {', '.join(missing_features)}")
        
        try:
            # Створюємо DataFrame з ознаками для прогнозування
            X_pred = pd.DataFrame([prediction_request.features])
            
            # Створюємо та налаштовуємо модель зі збереженими параметрами
            model_sklearn = LinearRegression()
            
            # Встановлюємо параметри моделі
            model_sklearn.coef_ = np.array([model.coefficients[feature] for feature in model.feature_variables])
            model_sklearn.intercept_ = model.intercept
            
            # Робимо прогноз
            prediction = model_sklearn.predict(X_pred[model.feature_variables])[0]
            
            return {
                "prediction": float(prediction),
                "model_id": model.id,
                "model_name": model.name,
                "target_variable": model.target_variable,
                "features_used": prediction_request.features,
                "r_squared": model.r_squared
            }
            
        except Exception as e:
            logger.error(f"Помилка при прогнозуванні: {str(e)}")
            raise
    
    def _get_feature_importance(self, coefficients: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        
        if not coefficients:
            return {}
            
        # Обчислюємо загальну важливість як суму абсолютних значень коефіцієнтів
        total_importance = sum(abs(coef) for coef in coefficients.values() if coef is not None)
        
        # Обчислюємо важливість кожної ознаки
        feature_importance = {}
        
        for feature, coef in coefficients.items():
            if coef is not None:  # Пропускаємо None значення
                abs_importance = abs(coef)
                relative_importance = (abs_importance / total_importance) * 100 if total_importance > 0 else 0
                
                feature_importance[feature] = {
                    'coefficient': float(coef),
                    'absolute_importance': float(abs_importance),
                    'relative_importance': float(relative_importance)
                }
        
        # Сортуємо за важливістю (за спаданням)
        sorted_importance = dict(
            sorted(feature_importance.items(), key=lambda x: x[1]['absolute_importance'], reverse=True)
        )
        
        return sorted_importance
    
    def get_model_importance(self, model_id: int) -> Dict[str, Any]:
        
        model = get_model(self.db, model_id)
        
        if not model:
            raise HTTPException(
                status_code=404,
                detail=f"Model with ID {model_id} not found"
            )
        
        # Отримуємо коефіцієнти та назви ознак
        coefficients = model.coefficients
        feature_names = model.feature_variables
        
        if not isinstance(coefficients, dict):
            # Якщо коефіцієнти збережено не у вигляді словника
            if isinstance(coefficients, list):
                coefficients = {name: coef for name, coef in zip(feature_names, coefficients)}
            else:
                coefficients = {}
        
        # Отримуємо відсортований словник важливості ознак
        feature_importance = self._get_feature_importance(coefficients)
        
        return {
            "model_id": model.id,
            "model_name": model.name,
            "target_variable": model.target_variable,
            "feature_importance": feature_importance,  # Використовуємо змінну feature_importance замість sorted_importance
            "r_squared": float(model.r_squared) if hasattr(model, 'r_squared') else None
        }
