# Phase 2 — Waste Detection & Optimization

## 1. Objective
Phase 2 builds upon the Phase 1 mock data analysis to identify specific cost-optimization opportunities. It detects waste, assigns severity, estimates mock savings, and presents these findings on the dashboard.

## 2. Architecture & Data Flow

```
CSV Data → data_loader → cost_analysis (Phase 1)
                               ↓
                         waste_detector 
                 (generates OptimizationFindings)
                               ↓
                       savings_calculator
               (aggregates total/annual savings)
                               ↓
                         routes (Flask)
                               ↓
                        index.html (UI)
```

## 3. Supported Issue Types
The `waste_detector` identifies the following structured issues:
- `UNDERUTILIZED_EC2`: Instance CPU or memory is below thresholds.
- `STOPPED_EC2`: Instance is stopped but still incurs potential related costs (e.g., EBS).
- `UNDERUTILIZED_EBS`: Volume allocated size far exceeds used storage.
- `UNATTACHED_EBS`: Volume is available but not attached to an instance.

*(S3 is intentionally excluded as the mock dataset lacks access frequency or lifecycle data required to make sound optimization recommendations.)*

## 4. Severity Logic
Severity is automatically assigned based on the estimated monthly savings, using configurable thresholds in `config.py`:
- **HIGH**: Savings ≥ $50.00/mo
- **MEDIUM**: Savings ≥ $15.00/mo
- **LOW**: Savings < $15.00/mo

## 5. Optimization Finding Structure
Each finding is standardized into an `OptimizationFinding` dataclass containing:
- `resource_id`
- `resource_type` (EC2, EBS)
- `issue_type` (from IssueType Enum)
- `severity` (from Severity Enum)
- `reason` (Why it was flagged)
- `recommended_action` (What to do)
- `current_monthly_cost`
- `estimated_optimized_monthly_cost`
- `estimated_monthly_savings`
- `estimated_annual_savings`

## 6. Mock Pricing Assumptions
To estimate savings without real AWS billing APIs, mock pricing is used (defined in `config.py`):
- **EC2 Downsizing**: Assumes a 50% cost reduction when halving the instance size (`EC2_DOWNSIZE_COST_RATIO = 0.50`).
- **EBS Cost**: Assumes $0.10 per GB/month for rightsizing (`EBS_COST_PER_GB_MONTH = 0.10`).
- **EBS Rightsizing**: When downsizing a volume, adds a 30% headroom buffer over current usage (`EBS_RIGHTSIZING_HEADROOM = 1.30`).

## 7. Savings Calculation
The `savings_calculator.py` service aggregates all findings to produce:
- Total monthly savings
- Total annual savings (monthly × 12)
- Potential savings percentage (savings / total cost × 100)
- Number of total and high-priority opportunities
- Breakdown of savings by service (e.g., EC2 vs EBS)

## 8. Dashboard Output
The Phase 1 dashboard has been extended to include:
- **Optimization Overview**: Summary cards showing total savings, percentage, and counts.
- **Savings by Service**: Cards highlighting where savings are concentrated.
- **Optimization Findings**: A detailed table listing every flagged resource with color-coded severity badges.

## 9. Current Limitations
- **Savings are estimates**: They rely on hard-coded mock pricing ratios, not actual AWS prices.
- **No live APIs**: Recommendations are entirely rule-based on the static CSV mock data.
- **No automatic remediation**: This tool only reports findings; it does not (and cannot) delete or modify real AWS resources.

## 10. What Phase 2 Does NOT Do
- Does **not** integrate with boto3 or real AWS APIs.
- Does **not** use AI/LLMs or machine learning for recommendations.
- Does **not** implement Terraform, CI/CD, Docker, or databases.
- Does **not** modify, stop, or delete any actual cloud resources.
