from app.repositories.resource_repository import ResourceRepository

def load_data_from_db() -> dict[str, list[dict]]:
    """Load resources from the database and format them like the original CSV data."""
    resources = ResourceRepository.get_all_resources()
    
    data = {
        "ec2": [],
        "ebs": [],
        "s3": []
    }
    
    for res in resources:
        # Reconstruct base metrics and cost
        item = {
            "resource_id": res.resource_id,
            "region": res.region,
            "status": res.status,
            "state": res.status, # backward compatibility for tests
            "instance_id": res.resource_id, # backward compatibility
            "volume_id": res.resource_id,
            "bucket_name": res.resource_id
        }
        
        # Attach cost
        if res.cost_records:
            item["monthly_cost"] = res.cost_records[-1].monthly_cost
        else:
            item["monthly_cost"] = 0.0
            
        # Attach metrics
        for metric in res.metrics:
            item[metric.metric_name] = metric.metric_value
            if metric.metric_name == 'cpu_utilization':
                item['cpu_utilization_percent'] = metric.metric_value
            elif metric.metric_name == 'memory_utilization':
                item['memory_utilization_percent'] = metric.metric_value
            elif metric.metric_name == 'storage_utilization':
                item['storage_utilization'] = metric.metric_value
            elif metric.metric_name == 'total_size_gb':
                item['size_gb'] = metric.metric_value

        # Some fields like size_gb and used_gb for EBS might need reverse computing or default
        if res.resource_type.lower() == 'ebs':
            if 'size_gb' not in item:
                item['size_gb'] = 100.0 # dummy
            if 'storage_utilization' in item:
                item['used_gb'] = item['size_gb'] * (item['storage_utilization'] / 100.0)
            else:
                item['used_gb'] = 0.0
                
        # We don't have volume_type and instance_type in the base model since it was just resource_type.
        # But Phase 2 might need it. Let's provide a safe default.
        item['instance_type'] = 'unknown'
        item['volume_type'] = 'unknown'
                
        resource_type = res.resource_type.lower()
        if resource_type in data:
            data[resource_type].append(item)
            
    return data
