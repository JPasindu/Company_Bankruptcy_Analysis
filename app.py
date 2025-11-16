"""
Flask Application for Financial Statement Extraction and Bankruptcy Analysis
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Optional

from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, send_file
from werkzeug.utils import secure_filename
import pandas as pd

from services.BankruptcyFromForm import BankruptcyPredictorFromForm


# ============================================================================
# APPLICATION CONFIGURATION
# ============================================================================

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')  # Use env var in production
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# File handling configuration
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)


# ============================================================================
# FINANCIAL STATEMENT EXTRACTOR CLASS
# ============================================================================

class FinancialStatementExtractor:
    """
    Extracts financial data from uploaded Excel/CSV files.
    Automatically detects statement types and maps values to standard variables.
    """
    
    def __init__(self, mapping_file: Optional[str] = None):
        """Initialize with keyword mapping rules."""
        if mapping_file and os.path.exists(mapping_file):
            with open(mapping_file, 'r') as f:
                self.mapping = json.load(f)
        else:
            self.mapping = self._get_default_mapping()
        
        self.statement_types = self._get_statement_type_keywords()
    
    @staticmethod
    def _get_default_mapping() -> Dict[str, List[str]]:
        """Get default keyword mapping for financial data extraction."""
        return {
            "total_assets": ["Total Assets", "Assets Total", "Total Asset"],
            "total_liabilities": ["Total Liabilities", "Liabilities Total", "Total Liab"],
            "current_assets": ["Current Assets", "Total Current Assets"],
            "current_liabilities": ["Current Liabilities", "Total Current Liabilities"],
            "cash": ["Cash", "Cash and Cash Equivalents", "Cash & Equivalents"],
            "revenue": ["Revenue", "Sales", "Turnover", "Total Revenue"],
            "net_income": ["Net Income", "Profit After Tax", "Net Profit", "Earnings"],
            "retained_earnings": ["Retained Earnings", "Retained Profit"],
            "interest_expense": ["Interest Expense", "Finance Cost", "Interest Cost"],
            "tax_expense": ["Tax Expense", "Income Tax", "Tax"],
            "inventory": ["Inventory", "Stock", "Inventories"],
            "ppe": ["Property, Plant & Equipment", "Fixed Assets", "PP&E", "PPE"],
            "operating_income": ["Operating Income", "EBIT", "Operating Profit"],
            "share_capital": ["Share Capital", "Capital Stock", "Paid-up Capital"],
            "dividends": ["Dividends", "Dividend Paid"]
        }
    
    @staticmethod
    def _get_statement_type_keywords() -> Dict[str, List[str]]:
        """Get keywords for detecting financial statement types."""
        return {
            "balance_sheet": ["balance sheet", "statement of financial position", "assets", "liabilities"],
            "income_statement": ["income statement", "profit and loss", "p&l", "revenue", "expenses"],
            "cash_flow": ["cash flow", "statement of cash flows", "operating activities"],
            "retained_earnings": ["retained earnings", "statement of retained earnings"],
            "equity": ["equity", "shareholders equity", "statement of equity"]
        }
    
    def detect_statement_type(self, df: pd.DataFrame, filename: str) -> str:
        """
        Detect the type of financial statement based on content and filename.
        
        Args:
            df: DataFrame containing the statement
            filename: Name of the uploaded file
            
        Returns:
            Statement type as string
        """
        filename_lower = filename.lower()
        content = ' '.join(df.astype(str).values.flatten()).lower()
        
        scores = {}
        for stmt_type, keywords in self.statement_types.items():
            score = sum(5 for keyword in keywords if keyword in filename_lower)
            score += sum(1 for keyword in keywords if keyword in content)
            scores[stmt_type] = score
        
        detected_type = max(scores, key=scores.get)
        return detected_type if scores[detected_type] > 0 else "unknown"
    
    def extract_values(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Extract financial values from a DataFrame using keyword mapping.
        
        Args:
            df: DataFrame containing financial data
            
        Returns:
            Dictionary of extracted values
        """
        if df.shape[1] < 2:
            return {}
        
        extracted = {}
        first_col = df.iloc[:, 0].astype(str)
        
        for key, keywords in self.mapping.items():
            for keyword in keywords:
                matches = df[first_col.str.contains(keyword, case=False, na=False, regex=False)]
                
                if not matches.empty:
                    try:
                        value_col = matches.iloc[0, 1]
                        if pd.notna(value_col):
                            # Clean and convert to float
                            value_str = str(value_col).replace(',', '').replace('$', '').replace('(', '-').replace(')', '')
                            extracted[key] = float(value_str)
                            break
                    except (ValueError, IndexError):
                        continue
        
        return extracted
    
    def process_file(self, filepath: str) -> Dict:
        """
        Process a single financial statement file.
        
        Args:
            filepath: Path to the Excel or CSV file
            
        Returns:
            Dictionary containing statement type and extracted values
        """
        filename = os.path.basename(filepath)
        file_ext = os.path.splitext(filename)[1].lower()
        
        try:
            if file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(filepath)
            elif file_ext == '.csv':
                df = pd.read_csv(filepath)
            else:
                return {"filename": filename, "error": f"Unsupported file type: {file_ext}"}
        except Exception as e:
            return {"filename": filename, "error": f"Failed to read file: {str(e)}"}
        
        stmt_type = self.detect_statement_type(df, filename)
        extracted_values = self.extract_values(df)
        
        return {
            "filename": filename,
            "statement_type": stmt_type,
            "extracted_values": extracted_values
        }
    
    def process_multiple_files(self, filepaths: List[str]) -> Dict:
        """
        Process multiple financial statement files and merge results.
        
        Args:
            filepaths: List of file paths to process
            
        Returns:
            Combined dictionary of all extracted values
        """
        all_results = []
        combined_data = {}
        
        for filepath in filepaths:
            result = self.process_file(filepath)
            all_results.append(result)
            
            if "extracted_values" in result:
                combined_data.update(result["extracted_values"])
        
        return {
            "individual_results": all_results,
            "combined_data": combined_data,
            "summary": self.generate_summary(combined_data)
        }
    
    def generate_summary(self, data: Dict) -> Dict:
        """
        Generate a summary of extracted data with validation.
        
        Args:
            data: Dictionary of extracted financial values
            
        Returns:
            Summary with missing values and basic validation
        """
        required_fields = [
            'total_assets', 'total_liabilities', 'current_assets', 
            'current_liabilities', 'cash', 'retained_earnings',
            'revenue', 'net_income', 'tax_expense', 'operating_income',
            'interest_expense', 'inventory', 'ppe'
        ]
        
        missing = [field for field in required_fields if field not in data]
        extracted = [field for field in required_fields if field in data]
        
        warnings = []
        
        # Validate equity
        if "total_assets" in data and "total_liabilities" in data:
            equity = data["total_assets"] - data["total_liabilities"]
            if equity < 0:
                warnings.append("⚠️ Negative equity detected (Liabilities > Assets)")
        
        # Validate current ratio
        if "current_assets" in data and "current_liabilities" in data:
            if data["current_liabilities"] != 0:
                current_ratio = data["current_assets"] / data["current_liabilities"]
                if current_ratio < 1:
                    warnings.append(f"⚠️ Low current ratio: {current_ratio:.2f}")
        
        return {
            "extracted_count": len(data),
            "extracted_fields": extracted,
            "missing_fields": missing,
            "warnings": warnings
        }
    
    def save_results(self, results: Dict, output_file: str) -> Optional[str]:
        """
        Save extraction results to JSON file.
        
        Args:
            results: Dictionary of extraction results
            output_file: Output filename
            
        Returns:
            Path to saved file or None if failed
        """
        try:
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            if not output_file.endswith('.json'):
                output_file += '.json'
                
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            
            print(f"Results successfully saved to: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"Error saving results to {output_file}: {str(e)}")
            
            # Fallback: save to current directory
            fallback_file = "fallback_extracted_financial_data.json"
            try:
                with open(fallback_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=4, ensure_ascii=False)
                print(f"Results saved to fallback location: {fallback_file}")
                return fallback_file
            except Exception as e2:
                print(f"Critical error: Could not save results anywhere: {str(e2)}")
                return None


# ============================================================================
# INITIALIZE SERVICES
# ============================================================================

extractor = FinancialStatementExtractor()

# DO NOT initialize these globally - they cache predictions!
# bankruptcy_service = BankruptcyService()
# bankruptcy_predictor = BankruptcyPredictorFromForm("model/bankruptcy_model.pkl")



def get_bankruptcy_predictor():
    """
    Create a fresh instance of bankruptcy predictor for each request.
    This prevents prediction caching issues.
    """
    return BankruptcyPredictorFromForm("model/bankruptcy_model.pkl")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_latest_results_path() -> str:
    """Get path to latest results JSON file."""
    return os.path.join(RESULTS_FOLDER, 'latest_results.json')


# ============================================================================
# ROUTES - MAIN PAGES
# ============================================================================

@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/debug/check-data')
def debug_check_data():
    """Debug endpoint to check what data is currently loaded."""
    json_file_path = get_latest_results_path()
    
    if not os.path.exists(json_file_path):
        return jsonify({'error': 'No data file found'})
    
    # Read the file
    with open(json_file_path, 'r') as f:
        data = json.load(f)
    
    return jsonify({
        'file_path': json_file_path,
        'file_modified': datetime.fromtimestamp(os.path.getmtime(json_file_path)).isoformat(),
        'combined_data_keys': list(data.get('combined_data', {}).keys()),
        'combined_data_values': {k: v for k, v in list(data.get('combined_data', {}).items())[:5]},
        'individual_results_count': len(data.get('individual_results', []))
    })


@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy', 
        'message': 'Financial Statement Extractor is running'
    })


# ============================================================================
# ROUTES - FILE UPLOAD AND EXTRACTION
# ============================================================================

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file upload and process financial statements."""
    if 'files' not in request.files:
        flash('No files selected', 'error')
        return redirect(url_for('index'))
    
    files = request.files.getlist('files')
    if not files or not files[0].filename:
        flash('No files selected', 'error')
        return redirect(url_for('index'))
    
    # Save uploaded files
    uploaded_files = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            uploaded_files.append(filepath)
        else:
            flash(f'File {file.filename} has invalid format. Allowed: xlsx, xls, csv', 'error')
    
    if not uploaded_files:
        flash('No valid files uploaded', 'error')
        return redirect(url_for('index'))
    
    # Process files
    try:
        results = extractor.process_multiple_files(uploaded_files)
        
        # Generate timestamp for unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(RESULTS_FOLDER, f'extracted_financial_data_{timestamp}.json')
        
        # Save results
        extractor.save_results(results, output_file)
        extractor.save_results(results, get_latest_results_path())
        
        return render_template('results.html', results=results)
    
    except Exception as e:
        flash(f'Error processing files: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/download-results')
def download_results():
    """Download extracted results as JSON."""
    results_file = get_latest_results_path()
    
    if os.path.exists(results_file):
        return send_file(
            results_file, 
            as_attachment=True, 
            download_name='financial_data_extraction.json'
        )
    else:
        flash('No results available for download', 'error')
        return redirect(url_for('index'))


# ============================================================================
# ROUTES - BANKRUPTCY ANALYSIS
# ============================================================================

@app.route('/bankruptcy-analysis', methods=['GET', 'POST'])
def bankruptcy_analysis():
    """
    Unified bankruptcy analysis endpoint.
    GET: Render the analysis page
    POST: Run analysis (either base prediction or with form modifications)
    """
    if request.method == 'GET':
        return render_template('bankruptcy_analysis.html')
    
    # POST request handling
    try:
        json_file_path = get_latest_results_path()
        
        # Check if results file exists
        if not os.path.exists(json_file_path):
            return jsonify({
                'status': 'error',
                'message': 'No financial data found. Please upload financial statements first.'
            }), 400
        
        # FORCE RELOAD: Read the file fresh every time (no caching!)
        print(f"\n{'='*60}")
        print(f"🔍 BANKRUPTCY ANALYSIS REQUEST")
        print(f"{'='*60}")
        print(f"Reading file: {json_file_path}")
        print(f"File modified time: {datetime.fromtimestamp(os.path.getmtime(json_file_path))}")
        
        with open(json_file_path, 'r') as f:
            file_data = json.load(f)
        
        print(f"Loaded data keys: {file_data.keys()}")
        if 'combined_data' in file_data:
            print(f"Combined data: {file_data['combined_data']}")
        
        # Check if this is a form submission with modifications
        request_data = request.get_json() if request.is_json else {}
        print(f"Request data: {request_data}")
        
        # If form data is provided (non-empty and has actual values), use the form predictor
        has_modifications = any(
            float(v) != 0 for v in request_data.values() 
            if v and str(v).replace('.', '').replace('-', '').replace('0', '')
        )
        
        # CREATE FRESH INSTANCES FOR EACH REQUEST
        bankruptcy_predictor = get_bankruptcy_predictor()

        if has_modifications:
            print("📝 Using MODIFIED analysis with form inputs")
            # Apply user modifications
            base_financials = bankruptcy_predictor._extract_financial_data(file_data)
            print(f"Base financials: {base_financials}")
            updated_financials = bankruptcy_predictor.process_user_inputs(base_financials, request_data)
            print(f"Updated financials: {updated_financials}")
            results = bankruptcy_predictor.predict_bankruptcy(updated_financials)
        else:
            print("📊 Using BASE analysis (no modifications)")
            base_financials = bankruptcy_predictor._extract_financial_data(file_data)
            print(f"Base financials: {base_financials}")
            updated_financials = bankruptcy_predictor.process_user_inputs(base_financials, request_data)
            print(f"Updated financials: {updated_financials}")
            results = bankruptcy_predictor.predict_bankruptcy(updated_financials)
        
        print(f"\n🎯 ANALYSIS RESULT:")
        print(f"   Risk Level: {results.get('risk_level', 'N/A')}")
        print(f"   Safe Probability: {results.get('safe_probability', 'N/A')}")
        print(f"   Bankruptcy Probability: {results.get('bankruptcy_probability', 'N/A')}")
        print(f"{'='*60}\n")
        
        return jsonify(results)
        
    except FileNotFoundError:
        return jsonify({
            'status': 'error',
            'message': 'Financial data file not found. Please upload statements first.'
        }), 404
    except Exception as e:
        print(f"❌ Bankruptcy analysis error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'Analysis failed: {str(e)}'
        }), 400


@app.route('/bankruptcy-results')
def bankruptcy_results():
    """Display bankruptcy analysis results."""
    return render_template('bankruptcy_results.html')


# ============================================================================
# ROUTES - API ENDPOINTS
# ============================================================================

@app.route('/api/extract', methods=['POST'])
def api_extract():
    """API endpoint for programmatic financial data extraction."""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    uploaded_files = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            uploaded_files.append(filepath)
    
    if not uploaded_files:
        return jsonify({'error': 'No valid files provided'}), 400
    
    try:
        results = extractor.process_multiple_files(uploaded_files)
        
        # Clean up uploaded files
        for filepath in uploaded_files:
            if os.path.exists(filepath):
                os.remove(filepath)
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500





# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)