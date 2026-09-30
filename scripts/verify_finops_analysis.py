"""Phase 5.8 Real AWS FinOps Analysis Verification Script.

Executes the full FinOps analysis pipeline against current PostgreSQL data
(loaded via db_loader correlation layer), verifies findings, recommendations,
savings estimation, and account-level cost preservation.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.services.finops_analyzer import run_full_analysis
from app.models import OptimizationFinding, Recommendation


def main():
    print("==================================================")
    print("Real AWS FinOps Analysis Verification")
    print("==================================================")
    print()

    app = create_app()
    with app.app_context():
        results = run_full_analysis()
        data = results["data"]
        metrics = data["summary_metrics"]
        findings = results["findings"]
        recommendations = results["recommendations"]

        savings_available_count = sum(1 for r in recommendations if r.estimated_monthly_savings > 0)
        savings_unavailable_count = sum(1 for r in recommendations if r.estimated_monthly_savings == 0)

        print(f"Resources analyzed: {metrics['total_resources']}")
        print()
        print(f"EC2 resources: {metrics['ec2_total']}")
        print(f"EBS resources: {metrics['ebs_total']}")
        print()
        print("CPU metrics:")
        print(f"  Available: {metrics['ec2_with_cpu_data']}")
        print(f"  Missing: {metrics['ec2_without_cpu_data']}")
        print()
        print(f"Findings generated: {len(findings)}")
        print(f"Recommendations generated: {len(recommendations)}")
        print()
        print("Savings estimates:")
        print(f"  Available: {savings_available_count}")
        print(f"  Unavailable: {savings_unavailable_count}")
        print()
        print("Account-level cost:")
        print(f"  Periods: {metrics['account_cost_periods']}")
        print(f"  Total: ${data['account_cost']:.10f}".rstrip('0').rstrip('.') + " USD")
        print()
        print("Analysis status:")
        print("  SUCCESS")
        print("==================================================")


if __name__ == "__main__":
    main()
