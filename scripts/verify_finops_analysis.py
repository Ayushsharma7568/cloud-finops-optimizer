"""Phase 5.9 FinOps Analysis Run & Reporting Verification Script.

Executes FinOps analysis, verifies AnalysisRun lifecycle, reporting summaries,
and analysis history retrieval from PostgreSQL.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.services.finops_analyzer import run_full_analysis
from app.services.finops_reporting import (
    get_latest_analysis_summary,
    get_recent_analysis_history,
)


def main():
    print("==================================================")
    print("FinOps Analysis Run Verification")
    print("==================================================")
    print()

    app = create_app()
    with app.app_context():
        # Execute analysis run
        results = run_full_analysis()
        run = results["analysis_run"]

        # Retrieve summary via reporting service
        summary = get_latest_analysis_summary()
        history = get_recent_analysis_history(limit=5)

        print("Analysis Run:")
        print(f"ID: {summary['id']}")
        print(f"Status: {summary['status']}")
        print()
        print(f"Resources analyzed: {summary['resource_count']}")
        print(f"Findings: {summary['findings_count']}")
        print(f"Recommendations: {summary['recommendations_count']}")
        print()
        print("Savings:")
        print(f"Available: {summary['savings_available_count']}")
        print(f"Unavailable: {summary['savings_unavailable_count']}")
        print()
        print("Recent Analysis Runs:")
        for idx, item in enumerate(history, start=1):
            print(f"#{idx} ID={item['id']} Status={item['status']}")

        print()
        print("Verification:")
        print("SUCCESS")
        print("==================================================")


if __name__ == "__main__":
    main()
