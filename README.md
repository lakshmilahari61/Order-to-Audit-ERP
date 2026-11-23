# Order-to-Audit ERP System for Small Food Manufacturer

**Project for NIT Tiruchirappalli Centre for Digital Infrastructure Winter Internship 2026**

---

## 1. Problem Statement & Overview
A small South Indian packaged food manufacturer (producing Murukku, Mixture, Chips, and Sweets) requires a unified ERP system. Previously, operational disconnects between field sales and shop-floor manufacturing led to:
- Stockouts and unfulfillable orders.
- Unmonitored material waste and yield loss during batch frying and packaging.
- Inaccurate cost estimation without overhead attribution.
- Inconsistent tax calculations between intra-state and inter-state GST.
- Fragmented records without an immutable audit trail.

This **Order-to-Audit System** provides an end-to-end relational ERP connecting:
1. **Sales Workflow**: Salesman order entry $\rightarrow$ Admin stock verification $\rightarrow$ Approval $\rightarrow$ GST Invoicing $\rightarrow$ Warehouse Dispatch $\rightarrow$ Customer Payment Collections $\rightarrow$ Receivables Tracking.
2. **Production Workflow**: Supplier Purchase $\rightarrow$ Raw Material Inventory $\rightarrow$ BOM-based Issuance $\rightarrow$ Production Run $\rightarrow$ Output & Scrap Recording $\rightarrow$ Finished Goods Increase $\rightarrow$ Direct Costing $\rightarrow$ Variance Analysis.

Both workflows share a **single, immutable transaction ledger** where direct balance overwriting is strictly prohibited:
$$\text{Closing Stock} = \text{Opening Stock} + \text{Receipts} - \text{Issues} - \text{Sales/Dispatches} \pm \text{Adjustments}$$

---

## 2. Technology Stack
- **Backend Framework**: Python 3.12 Flask
- **Relational ORM**: SQLAlchemy 2.0 & Flask-SQLAlchemy 3.1
- **Database**: SQLite (ACID-compliant with strict foreign keys and transactional rollbacks)
- **Mathematical Precision**: Python `decimal.Decimal` (No floating-point math for money or inventory)
- **Authentication**: Flask-Login with Werkzeug PBKDF2 SHA-256 password hashing
- **PDF Generation**: ReportLab 5.1 for formal GST Tax Invoices
- **Data Export Engine**: Pandas 3.1 and OpenPyXL 3.1 for CSV and Excel workbooks
- **Automated Testing**: Pytest 9.2 (Unit tests, route guards, calculations, benchmark assertions)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5.3 (Navy/charcoal theme, teal/blue accents), Chart.js 4.4

---

## 3. Architecture & Project Layout

```
order_to_audit/
├── app/
│   ├── __init__.py               # Flask app factory, custom Jinja filters (currency, qty), DB setup
│   ├── models.py                 # 25 normalized relational database entities
│   ├── services/
│   │   ├── inventory_service.py  # Stock ledger movements, WAC calculation, stock availability checks
│   │   ├── production_service.py # BOM explosion, variance calculations, overhead costing, cost/pkt
│   │   ├── sales_service.py      # Order creation, customer pricing, shortage detection, approval flow
│   │   ├── billing_service.py    # GST tax arithmetic (CGST/SGST/IGST), ReportLab PDF rendering
│   │   ├── payment_service.py    # Payment receipts, overpayment prevention, customer receivables
│   │   └── report_service.py     # 15 statutory registers, ledger extracts, CSV/Excel exporters
│   ├── routes/
│   │   ├── auth.py               # Authentication and @role_required RBAC decorators
│   │   ├── dashboard.py          # Role-specific consoles (Owner, Admin, Production, Sales, Auditor)
│   │   ├── master.py             # CRUD for Products, Customers, Suppliers, Materials, BOM recipes
│   │   ├── purchases.py          # Supplier purchase entries and WAC updates
│   │   ├── production.py         # Batch production runs and floor issuance
│   │   ├── sales.py              # Salesman order submission and admin review
│   │   ├── billing.py            # Invoice listing, viewing, and PDF generation
│   │   ├── dispatch.py           # Physical warehouse dispatch and atomic inventory deduction
│   │   ├── payments.py           # Customer receipt collections and aging
│   │   ├── reports.py            # Universal reporting console with date filters and export
│   │   └── benchmark.py          # One-click NIT benchmark scenario runner and verification table
│   ├── templates/                # Bootstrap 5 responsive templates
│   └── static/                   # Custom styling and client scripts
├── scripts/
│   ├── seed_data.py              # Clean database reset and demo data seeding
│   └── run_benchmark.py          # Standalone CLI runner asserting the 18 benchmark steps
├── tests/                        # Full Pytest automated test suite
├── config.py                     # Configuration settings
├── run.py                        # Server entry point
└── requirements.txt              # Pinned Python package dependencies
```

---

## 4. User Roles & Demo Credentials

| Role | Username | Password | Key Capabilities |
|---|---|---|---|
| **Admin** | `admin` | `admin123` | Full operational control, order verification/approval, master data, dispatch, and billing |
| **Salesman (A)** | `salesman` | `sales123` | Mobile-friendly catalog, product pricing, customer selection, order submission |
| **Salesman (B)** | `salesman_b` | `sales123` | Field order placement for inter-state accounts |
| **Production Supervisor**| `production` | `prod123` | BOM recipes, material receipts, batch execution, output/scrap entry, variance alerts |
| **Auditor / Accountant** | `auditor` | `audit123` | Strict read-only access, tax summaries, 15 audit registers, CSV/Excel report exports |
| **Owner** | `owner` | `owner123` | Executive dashboard, KPIs, Chart.js visualizations, variance alerts, unit margins |

---

## 5. Setup & Running Locally on Windows

### Step 1: Open Terminal in Project Directory
```powershell
cd C:\Users\HP\.gemini\antigravity\scratch\order_to_audit
```

### Step 2: Activate the Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```
*(If script execution is disabled in PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` or activate using `.\venv\Scripts\activate.bat`)*

### Step 3: Install Dependencies (Already Pre-installed)
```powershell
pip install -r requirements.txt
```

### Step 4: Initialize and Seed the Database
```powershell
python scripts/seed_data.py
```

### Step 5: Start the Web Server
```powershell
python run.py
```
Open your web browser and navigate to: **`http://127.0.0.1:5000`**

---

## 6. Mandatory NIT Trichy Benchmark Verification

The system includes a standalone automated benchmark runner that executes the 18 steps and verifies all 14 mandatory figures down to the exact decimal point.

### Running via Command Line (CLI):
```powershell
python scripts/run_benchmark.py
```

### CLI Verification Output:
```
================================================================================
 NIT TIRUCHIRAPPALLI WINTER INTERNSHIP 2026 — ERP BENCHMARK RUNNER
================================================================================
[1/3] Resetting and seeding demo database...
[2/3] Executing 18 benchmark scenario steps...
[3/3] Performing automated benchmark assertions...

--------------------------------------------------------------------------------
METRIC                           | EXPECTED        | ACTUAL          | STATUS
--------------------------------------------------------------------------------
Flour closing balance            | 120 kg          | 120.0000 kg     | [ PASS ]
Oil closing balance              | 19.5 L          | 19.5000 L       | [ PASS ]
Pouches closing balance          | 306 pieces      | 306.0000 pieces | [ PASS ]
Cartons closing balance          | 21 pieces       | 21.0000 pieces  | [ PASS ]
Finished goods after dispatch    | 88 packets      | 88.0000 packets | [ PASS ]
Yield variance %                 | -6.00%          | -6.00%          | [ PASS ]
Oil consumption variance %       | +5.00%          | 5.00%           | [ PASS ]
Retailer A taxable amount        | Rs. 7,500.00    | Rs. 7500.00     | [ PASS ]
CGST (2.5%)                      | Rs. 187.50      | Rs. 187.50      | [ PASS ]
SGST (2.5%)                      | Rs. 187.50      | Rs. 187.50      | [ PASS ]
Invoice total                    | Rs. 7,875.00    | Rs. 7875.00     | [ PASS ]
Retailer A outstanding balance   | Rs. 3,875.00    | Rs. 3875.00     | [ PASS ]
Distributor B stock shortage     | 32 packets      | 32.00 packets   | [ PASS ]
Cost per packet                  | Rs. 31.14       | Rs. 31.1436     | [ PASS ]
--------------------------------------------------------------------------------

>>> ALL BENCHMARK ASSERTIONS PASSED! 100% RECONCILIATION ACHIEVED! <<<
Valuation Method: Weighted Average Cost (WAC)
Costing Breakdown: RM Rs. 3,435.00 + Packaging Rs. 620.00 + Labour Rs. 1,200.00 + Power/Gas Rs. 600.00 = Total Rs. 5,855.00
Cost per packet: Rs. 5,855.00 / 188 good packets = Rs. 31.1436/pkt
```

### Running via Web Interface:
1. Log in as `admin` (or any role) and click the **"NIT Benchmark 2026"** link in the sidebar or top bar.
2. Click **"Reset & Run NIT Benchmark"**.
3. View the live comparison table highlighting all 14 passes with complete formulas and calculation rationale.

---

## 7. Business Logic & Methodologies

### A. Inventory Valuation: Weighted Average Cost (WAC)
Whenever new material is purchased, the system recomputes the unit valuation rate dynamically:
$$\text{New WAC} = \frac{(\text{Existing Stock} \times \text{Current WAC}) + (\text{Purchased Qty} \times \text{Purchase Rate})}{\text{Existing Stock} + \text{Purchased Qty}}$$

*Benchmark Example (Flour)*:
- Opening stock: 100 kg @ ₹42.00/kg = ₹4,200.00
- New purchase: 60 kg @ ₹45.00/kg = ₹2,700.00
- New WAC = $(4200 + 2700) / (100 + 60) = 6900 / 160 = \mathbf{₹43.1250/\text{kg}}$

### B. Production Costing & Overhead Allocation
Cost per packet captures direct raw material consumption, packaging material consumption, direct factory labour, and power & gas fuel expenses:
$$\text{Total Production Cost} = \text{RM Cost} + \text{Packaging Cost} + \text{Labour Expense} + \text{Power/Gas Expense}$$
$$\text{Cost per Packet} = \frac{\text{Total Production Cost}}{\text{Actual Good Packets Produced}}$$

*Benchmark Example (Murukku 200g Batch)*:
- Raw Materials:
  - Flour: 40 kg @ ₹43.125 = ₹1,725.00
  - Cooking oil: 10.5 L @ ₹140.00 = ₹1,470.00
  - Spice mix: 1.2 kg @ ₹200.00 = ₹240.00
  - *Total Raw Materials*: ₹3,435.00
- Packaging Materials:
  - Pouches: 188 good + 6 damaged = 194 pcs @ ₹2.50 = ₹485.00
  - Cartons: 9 pcs @ ₹15.00 = ₹135.00
  - *Total Packaging*: ₹620.00
- Direct Overheads:
  - Labour expense: ₹1,200.00
  - Gas & power expense: ₹600.00
- *Total Batch Cost*: ₹3,435 + ₹620 + ₹1,200 + ₹600 = **₹5,855.00**
- *Good Packets Produced*: 188
- *Cost per Packet*: $₹5,855.00 / 188 = \mathbf{₹31.1436/\text{pkt}}$ (≈ ₹31.14)
- *Selling Price*: ₹50.00 | *Unit Gross Margin*: **₹18.86 (37.7%)**

### C. Variance Formulas & Alerting (±3% Configured Tolerance)
$$\text{Material Consumption Variance \%} = \frac{\text{Actual Consumption} - \text{Planned Consumption}}{\text{Planned Consumption}} \times 100$$
$$\text{Yield Variance \%} = \frac{\text{Actual Output} - \text{Expected Output}}{\text{Expected Output}} \times 100$$

- **Oil Consumption Variance**: $\frac{10.5 - 10.0}{10.0} \times 100 = \mathbf{+5.00\%}$ ($\rightarrow$ **ALERT triggered!**)
- **Batch Yield Variance**: $\frac{188 - 200}{200} \times 100 = \mathbf{-6.00\%}$ ($\rightarrow$ **ALERT triggered!**)

### D. GST Invoicing Rules (Prototype GST System)
- **Intra-state (Tamil Nadu $\rightarrow$ Tamil Nadu)**:
  - CGST: 2.5% | SGST: 2.5% | IGST: 0.0%
- **Inter-state (Tamil Nadu $\rightarrow$ Karnataka / Other)**:
  - CGST: 0.0% | SGST: 0.0% | IGST: 5.0%

All calculations use Python `decimal.Decimal` with 2 decimal places (`ROUND_HALF_UP`). Floating-point arithmetic is strictly avoided.

---

## 8. Automated Testing Suite

Execute the entire test suite via Pytest:
```powershell
python -m pytest tests/ -v
```

Tests include:
- `test_auth.py`: Authentication, session lifecycle, and role permission guards.
- `test_inventory.py`: Immutable ledger additions, WAC recomputations, and negative stock prevention.
- `test_production.py`: BOM explosion, actual consumption, packaging damage, yield variance, and packet costing.
- `test_gst_billing.py`: Intra-state (CGST+SGST) vs Inter-state (IGST) tax determinations.
- `test_sales_dispatch.py`: Order submission, stock deduction on dispatch, and shortage blocking.
- `test_payments.py`: Customer payments, invoice status updates, and overpayment prevention.
- `test_benchmark_scenario.py`: Complete automated test of all 18 NIT Trichy benchmark steps.

---

## 9. Assumptions & Known Limitations
1. **Prototype GST**: Dummy GST numbers and company details are used for evaluation purposes; not connected to the government GSTN portal.
2. **Sequential Invoicing**: Invoices are numbered sequentially within each calendar year (`INV-YYYY-XXXX`). Once issued, invoices cannot be modified retroactively.
3. **No Direct Balance Overwrites**: Stock can only change through verifiable transactions (`PURCHASE`, `PRODUCTION_ISSUE`, `PRODUCTION_OUTPUT`, `DISPATCH`).
4. **Single Currency**: Standard Indian Rupee (INR / ₹) decimal arithmetic throughout.
