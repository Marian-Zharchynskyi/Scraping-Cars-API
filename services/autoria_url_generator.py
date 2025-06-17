import json
from pathlib import Path
from typing import Optional, Dict


class AutoriaUrlGenerator:
    def __init__(self):
        self.brands: Dict[str, int] = {}
        self.models: Dict[str, int] = {}
        self._load_mappings()

    def _load_mappings(self):
        """Load brand and model mappings from JSON files"""
        base_path = Path(__file__).parent.parent

        # Load brands
        with open(base_path / "autoria_brands.json", "r", encoding="utf-8") as f:
            brands_data = json.load(f)
            self.brands = {brand["name"].lower(): brand["value"] for brand in brands_data}

        # Load models
        with open(base_path / "autoria_models.json", "r", encoding="utf-8") as f:
            models_data = json.load(f)
            self.models = {model["name"].lower(): model["value"] for model in models_data}

    def get_brand_id(self, brand_name: str) -> Optional[int]:
        """Get brand ID from brand name"""
        return self.brands.get(brand_name.lower())

    def get_model_id(self, model_name: str) -> Optional[int]:
        """Get model ID from model name"""
        return self.models.get(model_name.lower())
