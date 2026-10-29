"""
Fintech Client Onboarding Data Validation & Error Reconciliation Tool
----------------------------------------------------------------------
Validates uploaded corporate expense / card allocation sheets during
client onboarding, separates clean vs. errored records, and exports
reconciliation artefacts for support engineers.

Requirements:
    pip install pandas pydantic
"""

import json
import random
import string
from datetime import datetime

import pandas as pd
from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator


# ---------------------------------------------------------------------------
# 1. Pydantic model -- business rules for a single onboarding row
# ---------------------------------------------------------------------------
class OnboardingRecord(BaseModel):
    employee_id: str = Field(..., min_length=1)
    full_email: EmailStr
    department_code: str = Field(..., min_length=1)
    transaction_amount: float = Field(..., gt=0)

    @field_validator("department_code")
    @classmethod
    def _dept_not_blank(cls, v: str) -> str:
        if v is None or str(v).strip() == "" or str(v).strip().lower() == "nan":
            raise ValueError("department_code must not be empty/null")
        return str(v).strip()

    @field_validator("full_email")
    @classmethod
    def _email_must_contain_at(cls, v: str) -> str:
        # Explicit guard so the error message is friendlier than Pydantic's
        if "@" not in str(v):
            raise ValueError("full_email missing '@' — invalid email format")
        return v


# ---------------------------------------------------------------------------
# 2. Build a synthetic, intentionally-dirty dataset
# ---------------------------------------------------------------------------
def build_dummy_dataset(n_rows: int = 200, seed: int = 42) -> pd.DataFrame:
    random.seed(seed)

    departments = ["FIN", "ENG", "OPS", "SAL", "HR", "LEG", "MKT"]
    domains = ["acme-corp.com", "globex.io", "initech.co", "umbrella.org"]

    rows = []
    for i in range(1, n_rows + 1):
        emp_id = f"EMP{1000 + i}"
        dept = random.choice(departments)
        first = "".join(random.choices(string.ascii_lowercase, k=5))
        last = "".join(random.choices(string.ascii_lowercase, k=6))
        email = f"{first}.{last}@{random.choice(domains)}"
        amount = round(random.uniform(5, 5000), 2)
        rows.append(
            {
                "employee_id": emp_id,
                "full_email": email,
                "department_code": dept,
                "transaction_amount": amount,
            }
        )

    df = pd.DataFrame(rows)

    # --- Inject intentional dirty data ---
    dirty_specs = [
        # negative / zero amounts
        (0,  "transaction_amount", -125.50),
        (3,  "transaction_amount", -0.01),
        (7,  "transaction_amount", 0.0),
        # invalid emails (no '@')
        (1,  "full_email", "john.doe.acme.com"),
        (5,  "full_email", "missing_at_sign"),
        (12, "full_email", "not-an-email"),
        # empty / null department codes
        (2,  "department_code", ""),
        (9,  "department_code", None),
        (15, "department_code", "   "),
        # multiple faults on one row
        (20, "transaction_amount", -50.0),
        (20, "full_email", "bad-email"),
        (20, "department_code", ""),
    ]
    for idx, col, val in dirty_specs:
        if 0 <= idx < len(df):
            df.at[idx, col] = val

    return df


# ---------------------------------------------------------------------------
# 3. Validation / reconciliation
# ---------------------------------------------------------------------------
def reconcile(df: pd.DataFrame):
    clean_records = []
    error_records = []

    for idx, row in df.iterrows():
        payload = {
            "employee_id": row["employee_id"],
            "full_email": row["full_email"],
            "department_code": row["department_code"],
            "transaction_amount": row["transaction_amount"],
        }
        # Normalise NaN / None so Pydantic raises meaningful messages
        payload = {
            k: (None if (isinstance(v, float) and pd.isna(v)) else v)
            for k, v in payload.items()
        }

        try:
            validated = OnboardingRecord(**payload)
            clean_records.append(validated.model_dump())
        except ValidationError as ve:
            reasons = []
            for err in ve.errors():
                loc = ".".join(str(p) for p in err["loc"])
                reasons.append(f"{loc}: {err['msg']}")
            error_records.append(
                {
                    "row_index": int(idx),
                    "employee_id": payload.get("employee_id"),
                    "errors": reasons,
                }
            )

    clean_df = pd.DataFrame(clean_records)
    return clean_df, error_records


# ---------------------------------------------------------------------------
# 4. Export artefacts
# ---------------------------------------------------------------------------
def export_artefacts(clean_df: pd.DataFrame, error_records: list) -> None:
    clean_df.to_csv("clean_onboarding_data.csv", index=False)

    error_payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_errors": len(error_records),
        "errors": error_records,
    }
    with open("error_report.json", "w", encoding="utf-8") as fh:
        json.dump(error_payload, fh, indent=2)


# ---------------------------------------------------------------------------
# 5. Structured operations summary
# ---------------------------------------------------------------------------
def print_summary(total: int, clean: int, errors: int) -> None:
    pct = (errors / total * 100) if total else 0.0
    bar = "=" * 62
    print(f"\n{bar}")
    print(" FINANCIAL ONBOARDING — DATA VALIDATION SUMMARY")
    print(bar)
    print(f" Timestamp            : {datetime.utcnow().isoformat()}Z")
    print(f" Total rows ingested  : {total:>6}")
    print(f" Successful records   : {clean:>6}")
    print(f" Errored records      : {errors:>6}")
    print(f" Failure percentage   : {pct:>6.2f}%")
    print(f"{'-' * 62}")
    print(" Output artefacts")
    print("   • clean_onboarding_data.csv  (validated records)")
    print("   • error_report.json          (row-level failure ledger)")
    print(f"{bar}\n")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def main() -> None:
    print("Building synthetic onboarding dataset with injected dirty data...")
    df = build_dummy_dataset(n_rows=200)

    print("Validating rows against Pydantic business rules...")
    clean_df, error_records = reconcile(df)

    export_artefacts(clean_df, error_records)

    print_summary(total=len(df), clean=len(clean_df), errors=len(error_records))

    # Preview for the operator
    if error_records:
        print("Sample errors (first 3):")
        for rec in error_records[:3]:
            print(f"  row {rec['row_index']:>3} | {rec['employee_id']} | {rec['errors']}")
        print()


if __name__ == "__main__":
    main()
