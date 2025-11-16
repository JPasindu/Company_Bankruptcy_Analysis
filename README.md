---

# **Bankruptcy Risk Analyzer**

### *financial statement analysis & bankruptcy risk prediction*

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-App-green.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)
![Model](https://img.shields.io/badge/ML-Bankruptcy%20Prediction-purple.svg)


**Bankruptcy Risk Analyzer** is an end-to-end web application that automates financial data extraction, computes key financial indicators, predicts bankruptcy risk using a pretrained machine learning model, and supports day-to-day business decision-making.

---
## 🛠️ Built With

- **Python 3.10+**
- **Flask** (backend web framework)
- **scikit-learn / XGBoost** (ML model)
- **Pandas & NumPy** (data processing)
- **HTML/CSS + Bootstrap** (UI)
- **OpenPyXL / Pandas ExcelReader** (file extraction)


## **🔍 What This App Does**

### **1. Upload Financial Statements**

Users can upload standard company financial statements such as:

* **Balance Sheet**
* **Income Statement**
* **Cash Flow Statement**
* **Statement of Retained Earnings**

---

### **2. Automated Financial Data Extraction**

The system extracts all required financial fields automatically, including:

* Revenue
* Total Assets
* Total Liabilities
* Current Assets
* Current Liabilities
* Cash & Equivalents
* Operating Income
* Tax Expense
* Net Income
* Retained Earnings
* Inventory
* Interest Expense
* PPE

---

### **3. Feature Engineering**

The backend computes all necessary financial ratios and engineered variables used by the model, including features:

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
---

### **4. Bankruptcy Risk Prediction**

Using your **pretrained machine learning model**, the app generates:

* Bankruptcy probability
* Risk level (Low/High)
* Key contributing factors

---

### **5. Decision Support**

The app provides actionable insights that help users with day-to-day financial decision-making, such as:

* Cash flow risks
* Solvency alerts
* Performance trends
* Operational risk indicators
* Recommended next steps

---

## **🚀 Features**

* User-friendly financial statement uploader
* Automatic data extraction & validation
* Backend-computed model features
* ML-based bankruptcy risk prediction
* Helping financial decision making

---
## 🔧 Installation

1. Clone the repository  
```bash
git clone https://github.com/your-username/Bankruptcy-Risk-Analyzer.git
cd Bankruptcy-Risk-Analyzer
```
2. Create a virtual environment
```
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```
3. Install dependencies
```
pip install -r requirements.txt
```
4. Run the Flask app
```
python app.py
```

## **📁 Repository Structure **

```
Bankruptcy-Risk-Analyzer/
|
|── Data/
│   ├── DatasetLink.txt/
|
├── Documents/
|   ├── Project - ML 2.pdf/
| 
├── model/
│   ├── bankruptcy_model.pkl/        
│
├── services/
│   ├── BankruptcyFromForm.py
|
├── templates/
│   ├── results.html/
│   ├── index.html/
│   └── base.html/
│   └── bankruptcy_analysis.html/
|
├── results/
├── uploads/
├── app.py
├── README.md
└── requirements.txt
```

---