# System Architecture & Design Note — Order-to-Audit ERP

**NIT Tiruchirappalli Centre for Digital Infrastructure Winter Internship 2026**  
**Author**: Full-Stack Software Engineer Applicant  
**Target Domain**: Small South Indian Packaged Food Manufacturer

---

## 1. Relational Schema & Entity Architecture

The database architecture employs a normalized, relational structure across 25 entities:

```
[Users] ──< [Roles]
   │
   ├──< [SalesOrders] ────< [SalesOrderItems] ────> [Products]
   │         │                                         │
   │         └──> [GSTInvoices] ──< [InvoiceItems]     ├──< [BOMs] ──< [BOMItems]
   │                    │                              │                    │
   │                    ├──< [DispatchRecords]         │                    ├──> [RawMaterials]
   │                    └──< [Payments]                │                    └──> [PackagingMaterials]
   │                                                   │
   ├──< [Purchases] ──< [PurchaseItems] ───────────────┼────────────────────┘
   │
   ├──< [ProductionRuns] ──┬──< [ProductionMaterialIssues]
   │                       ├──< [ProductionOutputs]
   │                       └──< [ExpensesOverheads]
   │
   └──< [InventoryTransactions (Immutable Stock Movement Ledger)]
```

### Core Schema Invariants:
1. **Source Document Integrity**: Every transaction in `InventoryTransactions` references its source (`source_doc_type`, `source_doc_id`).
2. **Snapshot Preservation**: `GSTInvoice` captures a static snapshot of customer state, billing address, and tax slabs at issuance to prevent retrospective alteration.
3. **Decimal Arithmetic**: All monetary columns (`Numeric(12, 2)`) and material quantities (`Numeric(10, 4)`) avoid IEEE 754 floating-point inaccuracies.

---

## 2. Immutable Inventory Ledger Approach

To ensure traceability and auditability, users cannot directly edit stock quantities. Current inventory is computed dynamically:
$$\text{Stock Balance} = \sum_{\text{Ledger}} \text{Quantity} \quad (\text{Receipts } > 0, \text{ Issues } < 0)$$

- **Purchases**: `+Quantity` recorded as `transaction_type = 'PURCHASE'`.
- **Production Floor Issues**: `-Quantity` recorded as `transaction_type = 'PRODUCTION_ISSUE'`.
- **Production Output**: `+Quantity` recorded as `transaction_type = 'PRODUCTION_OUTPUT'`.
- **Customer Dispatches**: `-Quantity` recorded as `transaction_type = 'DISPATCH'`.

Every deduction validates against the real-time stock balance. If $\text{Current Stock} + \text{Deduction} < 0$, a `ValueError` is raised, and the database transaction rolls back.

---

## 3. Stock Valuation: Weighted Average Cost (WAC)

Raw materials are valued using Weighted Average Cost updated at each purchase receipt:
$$\text{WAC}_{\text{new}} = \frac{(S_{\text{existing}} \times \text{WAC}_{\text{current}}) + (Q_{\text{purchased}} \times R_{\text{purchase}})}{S_{\text{existing}} + Q_{\text{purchased}}}$$

*Application in Benchmark*:
- Existing: $100\text{ kg} \times ₹42.00 = ₹4,200.00$
- New Purchase: $60\text{ kg} \times ₹45.00 = ₹2,700.00$
- Combined: $160\text{ kg} \rightarrow ₹6,900.00 \implies \mathbf{₹43.125/\text{kg}}$.

---

## 4. BOM Explosion, Costing & Variance Calculations

### Bill of Materials Explosion:
For a production run of $B$ batches of product $P$, the standard requirements are:
$$\text{Planned Qty}_i = \text{Standard Qty}_i \times B \quad \mid \quad \text{Expected Yield} = \text{BOM Yield} \times B$$

### Variance Calculations ($\pm 3\%$ Configured Tolerance):
1. **Material Consumption Variance**:
   $$\text{Variance \%} = \frac{\text{Actual Qty} - \text{Planned Qty}}{\text{Planned Qty}} \times 100$$
   *Benchmark Oil Usage*: $\frac{10.5 - 10.0}{10.0} \times 100 = \mathbf{+5.00\%}$ (**Unfavourable Alert**).

2. **Batch Yield Variance**:
   $$\text{Yield Variance \%} = \frac{\text{Actual Good Output} - \text{Expected Output}}{\text{Expected Output}} \times 100$$
   *Benchmark Yield*: $\frac{188 - 200}{200} \times 100 = \mathbf{-6.00\%}$ (**Shortage Alert**).

3. **Packaging Wastage Separation**:
   Damaged packaging (e.g., 6 torn pouches) is tracked distinctly from dough scrap to isolate operator/machine defects from material quality loss.

### Unit Cost per Packet Allocation:
$$\text{Cost per Packet} = \frac{\text{Direct RM Cost} + \text{Packaging Cost} + \text{Direct Labour} + \text{Power/Gas Overheads}}{\text{Actual Good Packets Produced}}$$
$$\text{Cost/Packet} = \frac{₹3,435.00 + ₹620.00 + ₹1,200.00 + ₹600.00}{188} = \mathbf{₹31.1436/\text{packet}}$$

---

## 5. Sales Verification & Shortage Enforcement

When an order is submitted:
1. The system determines tax jurisdiction:
   - **Intra-state** ($\text{State} = \text{Tamil Nadu}$): CGST $2.5\%$, SGST $2.5\%$.
   - **Inter-state** ($\text{State} \neq \text{Tamil Nadu}$): IGST $5.0\%$.
2. It compares ordered quantities against available finished goods:
   $$\text{Shortage} = \max(0, \text{Ordered Qty} - \text{Available FG Stock})$$
3. In the benchmark scenario, after Retailer A dispatches 150 packets, warehouse inventory is **88 packets**. When Distributor B orders **120 packets**, the system calculates an immediate deficit of **32 packets** and disables approval until a new production run is completed.

---

## 6. Key Design Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| **Immutable Stock Ledger** | Prevents balance tampering and enables audit reconciliation back to day one. | Direct balance overwriting (Rejected: lacks auditability). |
| **Python `Decimal` Precision** | Prevents fractional paisa rounding errors common in float operations. | IEEE 754 floats (Rejected: financial non-compliance). |
| **Atomic Flask/SQLAlchemy Transactions** | Guarantees that stock reduction, dispatch creation, and invoice generation succeed or fail together. | Multi-step uncommitted saves (Rejected: risk of partial states). |
| **ReportLab Vector PDF Invoicing** | Produces clean, professional, standardized PDF tax invoices offline without external dependencies. | Headless Chrome/Weasyprint (Rejected: heavyweight dependencies). |
| **Role-Based Decorator Guards** | Restricts administrative and financial actions server-side regardless of URL manipulation. | Client-side UI hiding only (Rejected: insecure). |
