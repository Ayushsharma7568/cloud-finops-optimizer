"""Phase 5.6 AWS Cost Explorer Verification Script.

Retrieves daily AWS cost data via AWSCostService, syncs records to PostgreSQL database,
and outputs a verification report.
"""

import sys
from pathlib import Path
from decimal import Decimal

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.services.aws_cost import AWSCostService
from app.services.aws_ingestion import sync_aws_costs
from app.models import CostRecord, Resource
from app.services.aws_client import (
    AWSApiError,
    AWSConnectionError,
    AWSCredentialsError,
)

def main():
    print("==================================================")
    print("AWS Cost Explorer Verification")
    print("==================================================")
    print()
    print("Fetching daily AWS costs...")
    print()

    aws_errors = 0
    total_cost = Decimal("0")
    currency = "USD"
    has_estimated = False
    records = []

    try:
        service = AWSCostService()
        records = service.get_daily_costs(days=7)

        for rec in records:
            start = rec["start_date"]
            end = rec["end_date"]
            amount = rec["amount"]
            curr = rec["currency"]
            est = rec["estimated"]

            total_cost += amount
            currency = curr
            if est:
                has_estimated = True

            print(f"{start} -> {end} : ${amount} {curr}" + (" (Estimated)" if est else ""))


    except (AWSCredentialsError, AWSConnectionError, AWSApiError) as e:
        print(f"AWS Error encountered: {e}")
        aws_errors += 1
    except Exception as e:
        print(f"Unexpected Error encountered: {e}")
        aws_errors += 1

    print()
    print("--------------------------------------------------")
    print("Verification Summary")
    print("--------------------------------------------------")
    print(f"Periods retrieved: {len(records)}")
    print(f"Total cost: ${total_cost:.10f}".rstrip('0').rstrip('.'))
    print(f"Currency: {currency}")
    print(f"Estimated data: {'Yes' if has_estimated else 'No'}")
    print(f"AWS errors: {aws_errors}")
    print()

    # Database Persistence Verification
    persisted_count = 0
    db_status = "Skipped (AWS error)"

    if aws_errors == 0:
        try:
            app = create_app()
            with app.app_context():
                print("Persisting cost records to PostgreSQL database...")
                persisted = sync_aws_costs(days=7)
                persisted_count = len(persisted)

                account_res = Resource.query.filter_by(resource_id="AWS_ACCOUNT").first()
                total_in_db = CostRecord.query.filter_by(resource_id=account_res.id).count() if account_res else 0
                db_status = f"Successfully persisted {persisted_count} records (Total in DB for AWS_ACCOUNT: {total_in_db})"
        except Exception as e:
            db_status = f"Database error: {e}"
            aws_errors += 1

    print("--------------------------------------------------")
    print("Database Verification")
    print("--------------------------------------------------")
    print(f"Status: {db_status}")
    print()

    if aws_errors == 0:
        print("Verification completed successfully.")
    else:
        print("Verification completed with errors.")
        sys.exit(1)

if __name__ == "__main__":
    main()
