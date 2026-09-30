"""Phase 5.7 FinOps Data Correlation Verification Script.

Loads current PostgreSQL resource, CloudWatch metric, and Cost Explorer data,
verifies data correlation, and confirms that account-level costs are preserved
separately without generating fake resource-level costs.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.services.db_loader import load_finops_correlation_summary


def main():
    print("==================================================")
    print("FinOps Data Correlation Verification")
    print("==================================================")
    print()

    app = create_app()
    with app.app_context():
        summary = load_finops_correlation_summary()
        data = summary["data"]
        metrics = data["summary_metrics"]

        print(f"AWS Resources: {metrics['total_resources']}")
        print()
        print("EC2:")
        print(f"  Total: {metrics['ec2_total']}")
        print(f"  Running: {metrics['ec2_running']}")
        print(f"  Stopped: {metrics['ec2_stopped']}")
        print()
        print("CloudWatch CPU:")
        print(f"  With data: {metrics['ec2_with_cpu_data']}")
        print(f"  Without data: {metrics['ec2_without_cpu_data']}")
        print()
        print("AWS Account Cost:")
        print(f"  Periods: {metrics['account_cost_periods']}")
        print(f"  Total: ${data['account_cost']:.10f}".rstrip('0').rstrip('.') + " USD")
        print()
        print("Resource/Cost relationship:")
        preserved_str = "YES" if summary["account_cost_preserved_separately"] else "NO"
        fake_costs_str = "YES" if summary["fake_resource_costs_detected"] else "NO"
        print(f"  Account-level cost preserved separately: {preserved_str}")
        print(f"  Fake resource-level cost generated: {fake_costs_str}")
        print()
        print("--------------------------------------------------")
        print("FinOps data loading:")
        print("  SUCCESS")
        print("==================================================")


if __name__ == "__main__":
    main()
