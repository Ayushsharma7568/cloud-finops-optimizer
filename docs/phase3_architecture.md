# Phase 3 — Recommendation Engine

## 1. Objective
Phase 3 transforms the technical optimization findings identified in Phase 2 into clear, prioritized, actionable recommendations. Instead of simply reporting that a resource is underutilized, the system now explains *why*, suggests a specific *action*, and assigns a *confidence level* to the recommendation.

## 2. Recommendation Engine Architecture

```
Cost Analysis → Waste Detector → Recommendation Engine → Savings Calculator → Flask Dashboard
```

The Recommendation Engine (`app/services/recommendation_engine.py`) consumes the `OptimizationFinding` objects and maps them to `Recommendation` objects. It does not recalculate savings or re-read CSV files.

## 3. Recommendation Structure
Each recommendation contains:
- **Core Identifiers**: `resource_id`, `resource_type`, `issue_type`
- **Impact Metrics**: `severity`, `current_monthly_cost`, `estimated_optimized_monthly_cost`, `estimated_monthly_savings`, `estimated_annual_savings`
- **Actionability**:
  - `action_category`: A standardized enum (e.g., `DOWNSIZE`, `REVIEW_AND_TERMINATE`)
  - `confidence`: The certainty of the recommendation based on available mock data (`HIGH`, `MEDIUM`, `LOW`)
  - `reason`: A human-readable explanation of why the resource was flagged
  - `recommendation`: A clear, actionable suggestion for the user

## 4. Issue → Recommendation Mapping
| Issue Type | Action Category | Confidence | Rationale |
|---|---|---|---|
| `UNDERUTILIZED_EC2` | `DOWNSIZE` | MEDIUM | CPU/Memory is low, but we lack long-term historical data to be fully confident. |
| `STOPPED_EC2` | `REVIEW_AND_TERMINATE` | HIGH | The instance is explicitly stopped, incurring unnecessary associated costs. |
| `UNDERUTILIZED_EBS` | `RESIZE_STORAGE` | MEDIUM | Storage is mostly empty, but future capacity needs are unknown. |
| `UNATTACHED_EBS` | `REVIEW_AND_DELETE` | HIGH | The volume is not attached to any compute resource, making it highly likely to be wasted. |

*(S3 is intentionally excluded as the mock dataset lacks access frequency or lifecycle data required to make sound optimization recommendations.)*

## 5. Action Categories
- `DOWNSIZE`: Reduce the compute capacity of a resource.
- `REVIEW_AND_TERMINATE`: Stop incurring costs for a compute resource that is no longer needed.
- `RESIZE_STORAGE`: Reduce the allocated storage capacity to better match actual usage.
- `REVIEW_AND_DELETE`: Permanently remove an unused storage resource.

## 6. Severity vs. Confidence
- **Severity** indicates the *potential impact* (i.e., how much money could be saved). It is based purely on the estimated monthly savings.
- **Confidence** indicates the *certainty* of the recommendation. For example, an unattached EBS volume might have a LOW severity (if it's very small) but a HIGH confidence (because it's definitively unused).

## 7. Prioritization Logic
Recommendations are sorted to surface the most critical actions first:
1. **Severity**: `HIGH` before `MEDIUM` before `LOW`.
2. **Impact**: Within the same severity level, recommendations are sorted descending by `estimated_monthly_savings`.

## 8. Dashboard Changes
The dashboard has been updated to reflect Phase 3 features:
- **Optimization Overview**: Added counts for Medium and Low priority items.
- **Top Recommendation**: A highlighted section showcasing the single highest-impact recommendation.
- **Action Categories**: A breakdown of recommendations by the required action.
- **Recommended Actions Table**: Replaces the Phase 2 findings table, now including the `Action` category, `Confidence` badge, and explicit `Recommendation` text.

## 9. Current Limitations
- Recommendations rely on static, rule-based mappings without historical context.
- Estimated savings still use the simplified mock pricing assumptions from Phase 2.
- The system does not implement any actual cloud resource modification.

## 10. Why AI/LLM is intentionally not used yet
At this stage, the problem domain (rules-based waste detection) can be solved deterministically. Introducing an LLM would add unnecessary complexity, latency, non-determinism, and cost without providing significant additional value for these specific, well-defined issues.
