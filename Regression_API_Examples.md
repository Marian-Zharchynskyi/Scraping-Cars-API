# Regression API - Приклади запитів

## Базовий URL

```
http://localhost:8000
```

## 1. Навчання моделі (POST /api/regression/train/)

### Приклад 1: Модель для прогнозування ціни

```json
{
  "target_variable": "price",
  "feature_variables": ["year", "mileage", "engine_volume", "fuel_type"],
  "marketplace_id": 1,
  "car_brands": ["BMW", "Audi", "Mercedes"],
  "test_size": 0.2,
  "random_state": 42
}
```

### Приклад 2: Модель для прогнозування позиції в пошуку

```json
{
  "target_variable": "search_position",
  "feature_variables": ["price", "year", "mileage", "brand_popularity"],
  "marketplace_id": 2,
  "car_brands": ["Toyota", "Honda", "Nissan"],
  "test_size": 0.3,
  "random_state": 123
}
```

### Приклад 3: Модель без фільтрації за марками

```json
{
  "target_variable": "price",
  "feature_variables": ["year", "mileage", "engine_volume"],
  "marketplace_id": 1,
  "test_size": 0.25,
  "random_state": 42
}
```

## 2. Прогнозування (POST /api/regression/predict/)

### Приклад 1: Прогноз ціни BMW

```json
{
  "target_variable": "price",
  "features": {
    "year": 2020,
    "mileage": 50000,
    "engine_volume": 2.0,
    "fuel_type": "petrol"
  },
  "marketplace_id": 1,
  "model_id": 1
}
```

### Приклад 2: Прогноз без вказання конкретної моделі

```json
{
  "target_variable": "price",
  "features": {
    "year": 2018,
    "mileage": 80000,
    "engine_volume": 1.6
  },
  "marketplace_id": 1
}
```

### Приклад 3: Прогноз позиції в пошуку

```json
{
  "target_variable": "search_position",
  "features": {
    "price": 25000,
    "year": 2019,
    "mileage": 60000,
    "brand_popularity": 0.8
  },
  "marketplace_id": 2
}
```

## 3. Отримання списку моделей (GET /api/regression/models/)

### Приклад 1: Всі активні моделі

```
GET /api/regression/models/?is_active=true
```

### Приклад 2: Моделі для конкретного майданчику

```
GET /api/regression/models/?marketplace_id=1&is_active=true
```

### Приклад 3: Пагінація

```
GET /api/regression/models/?skip=10&limit=5
```

### Приклад 4: Всі моделі (без фільтрів)

```
GET /api/regression/models/
```

## 4. Отримання моделі за ID (GET /api/regression/models/{model_id})

### Приклад

```
GET /api/regression/models/1
```

## 5. Оновлення моделі (PUT /api/regression/models/{model_id})

### Приклад 1: Оновлення назви та опису

```json
{
  "name": "Покращена модель ціни BMW",
  "description": "Модель для прогнозування ціни BMW з урахуванням додаткових факторів"
}
```

### Приклад 2: Деактивація моделі

```json
{
  "is_active": false
}
```

### Приклад 3: Повне оновлення

```json
{
  "name": "Нова назва моделі",
  "is_active": true,
  "description": "Оновлений опис моделі"
}
```

## 6. Видалення моделі (DELETE /api/regression/models/{model_id})

### Приклад

```
DELETE /api/regression/models/1
```

## 7. Важливість ознак (GET /api/regression/models/{model_id}/importance)

### Приклад

```
GET /api/regression/models/1/importance
```

## 8. Графік коефіцієнтів (GET /api/regression/models/{model_id}/coefficients-plot)

### Приклад

```
GET /api/regression/models/1/coefficients-plot
```

## Приклади відповідей

### Успішне навчання моделі

```json
{
  "success": true,
  "model_id": 1,
  "r_squared": 0.85,
  "adj_r_squared": 0.84,
  "f_statistic": 156.7,
  "f_p_value": 0.001,
  "n_observations": 1000,
  "coefficients": {
    "const": 5000.0,
    "year": 250.5,
    "mileage": -0.05,
    "engine_volume": 1500.0
  },
  "intercept": 5000.0,
  "standard_errors": {
    "const": 500.0,
    "year": 25.0,
    "mileage": 0.01,
    "engine_volume": 150.0
  },
  "t_statistics": {
    "const": 10.0,
    "year": 10.02,
    "mileage": -5.0,
    "engine_volume": 10.0
  },
  "p_values": {
    "const": 0.001,
    "year": 0.001,
    "mileage": 0.001,
    "engine_volume": 0.001
  },
  "confidence_intervals": {
    "const": [4020.0, 5980.0],
    "year": [201.5, 299.5],
    "mileage": [-0.07, -0.03],
    "engine_volume": [1200.0, 1800.0]
  },
  "message": "Model trained successfully"
}
```

### Успішний прогноз

```json
{
  "success": true,
  "prediction": 28500.0,
  "model_id": 1,
  "features_used": {
    "year": 2020,
    "mileage": 50000,
    "engine_volume": 2.0
  }
}
```

### Список моделей

```json
[
  {
    "id": 1,
    "name": "Модель ціни BMW",
    "target_variable": "price",
    "feature_variables": ["year", "mileage", "engine_volume"],
    "marketplace_id": 1,
    "description": "Модель для прогнозування ціни BMW",
    "coefficients": {...},
    "intercept": 5000.0,
    "r_squared": 0.85,
    "is_active": true,
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  }
]
```

### Важливість ознак

```json
{
  "success": true,
  "data": {
    "model_id": 1,
    "feature_importance": {
      "year": 0.45,
      "mileage": 0.30,
      "engine_volume": 0.25
    },
    "coefficients": {...},
    "feature_analysis": {
      "year": "# year\nКоефіцієнт: 250.5000 (Ст. помилка: 25.0000)\nt-статистика: 10.0200\np-значення: 0.0010 - дуже високо значимий (p < 0.01)\n95% Довірчий інтервал: [201.5000, 299.5000]\n\n## Інтерпретація:\n- За незмінних інших факторів, збільшення year на одиницю пов'язане з зростанням цільової змінної на 250.5000.\n- Коефіцієнт є статистично значущим на рівні 10% (|t| = 10.0200 > 1.645).\n- З імовірністю 95% справжній ефект year знаходиться між 201.5000 та 299.5000."
    }
  }
}
```

## Коди помилок

### 400 Bad Request

```json
{
  "detail": "Failed to train model: Invalid feature variables"
}
```

### 404 Not Found

```json
{
  "detail": "Model with ID 999 not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Error training model: Database connection failed"
}
```
