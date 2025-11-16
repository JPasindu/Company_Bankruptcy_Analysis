"""
Bankruptcy Prediction Service - Flask Integration Ready
Optimized for extracted_financial_data.json -> combined_data structure
"""

import pandas as pd
import numpy as np
import json
import joblib
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')

# ================================================================
# FLASK-READY BANKRUPTCY PREDICTOR CLASS
# ================================================================

class BankruptcyPredictorFromForm:
    """
    Flask-ready bankruptcy predictor that can be easily integrated into existing Flask apps
    Uses financial data from JSON input instead of hardcoded base financials
    Loads model fresh for every prediction to prevent caching
    """
    
    def __init__(self, model_path="model/bankruptcy_model.pkl"):
        """Initialize with model path - model is loaded on demand"""
        self.model_path = model_path
        self.model = None
        # Don't load model here - load fresh for each prediction
    
    def load_model(self):
        """Load the trained bankruptcy prediction model - fresh load every time"""
        try:
            # Clear any previous model
            self.model = None
            
            # Load the model fresh
            self.model = joblib.load(self.model_path)
            print(f"✅ Loaded model from: {self.model_path}")
        except FileNotFoundError:
            print(f"⚠️  Model file not found: {self.model_path}")
            self.model = self._create_dummy_model()
    
    def _create_dummy_model(self):
        """Create a dummy model for testing when real model not available"""
        from sklearn.ensemble import RandomForestClassifier
        
        dummy_model = RandomForestClassifier(n_estimators=10, random_state=42)
        X_dummy = np.random.rand(100, 17)
        y_dummy = np.random.randint(0, 2, 100)
        dummy_model.fit(X_dummy, y_dummy)
        return dummy_model
    
    def compute_features(self, financial_data):
        """
        Compute all features in correct order for model prediction
        Args:
            financial_data: Dictionary of financial values
        Returns:
            pandas DataFrame with features in correct order
        """
        # Add small epsilon to prevent division by zero
        eps = 1e-9
        raw = financial_data

        # Calculate features in the EXACT order your model expects
        debt_ratio = (raw['total_liabilities'] / (raw['total_assets'] + eps)) * 100
        retained_earnings_to_assets = raw['retained_earnings'] / (raw['total_assets'] + eps)
        working_capital_to_assets = (raw['current_assets'] - raw['current_liabilities']) / (raw['total_assets'] + eps)
        cash_to_assets = raw['cash'] / (raw['total_assets'] + eps)
        current_ratio = raw['current_assets'] / (raw['current_liabilities'] + eps)
        inventory_to_current_liabilities = raw['inventory'] / (raw['current_liabilities'] + eps)
        current_assets_to_total_assets = raw['current_assets'] / (raw['total_assets'] + eps)
        
        # TIER 2 features
        tax_rate = raw['tax_expense'] / (abs(raw['net_income']) + raw['tax_expense'] + eps)
        roa = raw['operating_income'] / (raw['total_assets'] + eps)
        
        # Handle negative net income scenario
        if raw['net_income'] <= 0:
            income_to_expense_ratio = 0.5  # Conservative value for struggling company
        else:
            income_to_expense_ratio = raw['revenue'] / (raw['revenue'] - raw['net_income'] + eps)
        
        equity = raw['total_assets'] - raw['total_liabilities']
        debt_to_equity = raw['total_liabilities'] / (equity + eps) if equity > 0 else 10.0  # Cap high values
        
        fixed_assets_turnover = raw['revenue'] / (abs(raw['ppe']) + eps)
        net_worth_turnover = raw['revenue'] / (equity + eps) if equity > 0 else 0
        borrowing_dependency = raw['total_liabilities'] / (raw['total_assets'] + eps)
        
        # Handle negative interest coverage
        if raw['interest_expense'] <= 0:
            interest_coverage = 1.0
        else:
            interest_coverage = raw['operating_income'] / (raw['interest_expense'] + eps)
        
        profit_margin = raw['net_income'] / (raw['revenue'] + eps)
        asset_turnover = raw['revenue'] / (raw['total_assets'] + eps)
     
        # Create features array in the EXACT order your model was trained on
        features_array = np.array([[
            debt_ratio, 
            retained_earnings_to_assets, 
            working_capital_to_assets,
            cash_to_assets, 
            current_ratio, 
            inventory_to_current_liabilities,
            current_assets_to_total_assets, 
            tax_rate, 
            roa, 
            income_to_expense_ratio,
            debt_to_equity, 
            fixed_assets_turnover, 
            net_worth_turnover,
            borrowing_dependency, 
            interest_coverage, 
            profit_margin, 
            asset_turnover
        ]])
        
        # Convert to DataFrame with proper column names
        feature_names = [
            'debt_ratio', 'retained_earnings_to_assets', 'working_capital_to_assets',
            'cash_to_assets', 'current_ratio', 'inventory_to_current_liabilities',
            'current_assets_to_total_assets', 'tax_rate', 'roa', 'income_to_expense_ratio',
            'debt_to_equity', 'fixed_assets_turnover', 'net_worth_turnover',
            'borrowing_dependency', 'interest_coverage', 'profit_margin', 'asset_turnover'
        ]
        
        return pd.DataFrame(features_array, columns=feature_names)
    
    def predict_bankruptcy(self, financial_data):
        """
        Make bankruptcy prediction for given financial data
        Loads model fresh for every prediction
        Args:
            financial_data: Dictionary of financial values (required)
        Returns:
            Dictionary with prediction results
        """
        if financial_data is None:
            return {
                'status': 'error',
                'message': 'Financial data is required'
            }
        
        # Load model fresh for this prediction
        self.load_model()
        
        # Compute features
        features_df = self.compute_features(financial_data)
        print('>>>>>>>>>>>>>>>>>>>>>')
        print(features_df)
        
        # Make prediction
        if hasattr(self.model, 'predict_proba'):
            probabilities = self.model.predict_proba(features_df)[0]
            bankruptcy_probability = probabilities[1] if len(probabilities) > 1 else probabilities[0]
            prediction = self.model.predict(features_df)[0]
        else:
            prediction = self.model.predict(features_df)[0]
            bankruptcy_probability = float(prediction)
        
        risk_level = self._get_risk_level(bankruptcy_probability)
        
        return {
            'prediction': int(prediction),
            'bankruptcy_probability': float(bankruptcy_probability),
            'safe_probability': float(1 - bankruptcy_probability),
            'risk_level': risk_level,
            'recommendation': self._get_recommendation(risk_level),
            'risk_percentage': round(bankruptcy_probability * 100, 2),
            'status': 'success'
        }
    
    def _get_risk_level(self, probability):
        """Categorize bankruptcy risk level"""
        if probability < 0.2:
            return "LOW"
        elif probability < 0.5:
            return "LOW"
        elif probability < 0.7:
            return "HIGH"
        else:
            return "HIGH"
    
    def _get_recommendation(self, risk_level):
        """Provide recommendation based on risk level"""
        recommendations = {
            "LOW": "Company shows good financial health. Continue monitoring.",
            "MODERATE": "Some financial concerns. Recommend closer monitoring and cash flow management.",
            "HIGH": "Significant bankruptcy risk. Immediate action required to improve liquidity and reduce debt.",
            "CRITICAL": "Severe bankruptcy risk. Urgent restructuring needed. Consider professional consultation."
        }
        return recommendations.get(risk_level, "Unable to assess")
    
    def process_user_inputs(self, base_financials, form_data):
        """
        Process form inputs and update financials for scenario analysis
        Args:
            base_financials: Base financial data dictionary
            form_data: Flask request.form dictionary
        Returns:
            Updated financial data dictionary
        """
        # Start with base financials
        updated_financials = base_financials.copy()
        print("Base financials:", updated_financials)

        print('--------')
        print(form_data)
        print('----')
        # Read user inputs (if provided)
        new_loan = float(form_data.get("new_loan", 0))
        debt_repayment = float(form_data.get("debt_repayment", 0))
        new_asset_purchase = float(form_data.get("new_asset_purchase", 0))
        revenue_update = float(form_data.get("revenue_update", 0))
        expense_update = float(form_data.get("expense_update", 0))
        tax_payment = float(form_data.get("tax_payment", 0))
        retained_earnings_update = float(form_data.get("retained_earnings_update", 0))

        # Apply user actions with better financial logic
        updated_financials["total_liabilities"] += new_loan - debt_repayment
        updated_financials["cash"] += new_loan - debt_repayment - new_asset_purchase - tax_payment
        
        # Update PPE (should be positive for most companies)
        updated_financials["ppe"] = max(0, updated_financials["ppe"] + new_asset_purchase)
        
        updated_financials["revenue"] += revenue_update
        
        # Update net income considering both revenue and expenses
        updated_financials["net_income"] += revenue_update * 0.15 - expense_update  # Assume 15% margin
        
        updated_financials["retained_earnings"] += retained_earnings_update + updated_financials["net_income"] * 0.7  # 70% retention
        updated_financials["tax_expense"] += tax_payment
        
        # Ensure current assets include cash and inventory
        updated_financials["current_assets"] = (updated_financials["cash"] + 
                                            updated_financials["inventory"] + 
                                            max(0, updated_financials["current_assets"] - 
                                                updated_financials["cash"] - 
                                                updated_financials["inventory"]))

        print("After Fackation:", updated_financials)

        return updated_financials
    
    def _extract_financial_data(self, data):
        """Extract financial data from JSON structure"""
        if 'combined_data' in data:
            return data['combined_data']
        else:
            return data

    def analyze_financial_data(self, financial_data):
        """
        Analyze financial data directly
        Loads model fresh for every analysis
        Args:
            financial_data: Dictionary of financial values
        Returns:
            Analysis results dictionary
        """
        return self.predict_bankruptcy(financial_data)

    def analyze_from_json(self, json_file_path):
        """
        Analyze financial data from JSON file
        Loads model fresh for every analysis
        Args:
            json_file_path: Path to JSON file with financial data
        Returns:
            Analysis results dictionary
        """
        try:
            with open(json_file_path, "r") as file:
                data = json.load(file)
            
            # Extract financial data from JSON structure
            financial_data = self._extract_financial_data(data)
            
            return self.analyze_financial_data(financial_data)
            
        except FileNotFoundError:
            return {'status': 'error', 'message': 'JSON file not found'}
        except json.JSONDecodeError:
            return {'status': 'error', 'message': 'Invalid JSON format'}
        except Exception as e:
            return {'status': 'error', 'message': f'Analysis failed: {str(e)}'}


