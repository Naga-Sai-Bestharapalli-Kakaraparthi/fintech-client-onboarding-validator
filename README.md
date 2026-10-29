# Fintech Client Onboarding Data Validation & Error Reconciliation Tool

A production-grade Python script built with **Pandas** and **Pydantic** designed to validate, sanitize, and reconcile corporate expense and card allocation sheets uploaded by clients during onboarding.

## 🚀 What It Does
When corporate clients upload messy spreadsheets during onboarding, typos, negative amounts, missing email formatting, or blank department codes can easily crash backend databases or skew dashboard metrics. 

This script acts as an automated data guardrail:
1. **Ingests & Normalizes:** Reads incoming tabular client data (or generates synthetic records with intentional edge cases for testing).
2. **Strict Schema Validation:** Leverages **Pydantic** type models to enforce business rules (e.g., positive transaction amounts, valid email syntax, non-null department codes).
3. **Automated Reconciliation:** Clean rows are separated for immediate ingestion, while faulty rows are isolated into a structured error ledger.
4. **Actionable Exports:** Generates clean data files and developer-friendly error reports so support teams can troubleshoot client issues in seconds.

---

## 🛠️ Tech Stack
* **Python**
* **Pandas** (Data manipulation and CSV handling)
* **Pydantic** (Robust data parsing and runtime rule validation)

---

## 📂 Project Structure
```text
├── validator.py                # Core data ingestion, validation, and reconciliation logic
├── clean_onboarding_data.csv   # Output: Validated clean records ready for downstream systems
└── error_report.json           # Output: Row-level audit trail detailing exact errors for support teams
