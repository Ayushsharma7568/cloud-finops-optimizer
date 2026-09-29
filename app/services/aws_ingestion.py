"""AWS Database Ingestion Service.

Coordinates AWS discovery services and integrates them into the PostgreSQL
database layer using the Repository pattern.
"""

import logging
from app.services.aws_ec2_discovery import discover_ec2_instances
from app.services.aws_ebs_discovery import discover_ebs_volumes
from app.services.aws_cloudwatch import CloudWatchService
from app.repositories.resource_repository import ResourceRepository

logger = logging.getLogger(__name__)


def sync_aws_resources():
    """Sync all AWS resources from configured region to the local database.
    
    1. Discovers EC2 instances and EBS volumes via Boto3.
    2. Maps the normalized outputs to the ResourceRepository.
    3. Handles creations and updates idempotently.
    
    Returns:
        dict: A summary of the synchronization results.
    """
    logger.info("Starting AWS resource database synchronization...")
    
    results = {
        "ec2_instances_processed": 0,
        "ebs_volumes_processed": 0,
        "errors": []
    }
    
    # 1. Sync EC2
    try:
        ec2_resources = discover_ec2_instances()
        for ec2 in ec2_resources:
            _ingest_resource(ec2)
            results["ec2_instances_processed"] += 1
    except Exception as e:
        logger.error(f"Failed to sync EC2 instances: {e}")
        results["errors"].append(str(e))
        
    # 2. Sync EBS
    try:
        ebs_resources = discover_ebs_volumes()
        for ebs in ebs_resources:
            _ingest_resource(ebs)
            results["ebs_volumes_processed"] += 1
    except Exception as e:
        logger.error(f"Failed to sync EBS volumes: {e}")
        results["errors"].append(str(e))
        
    logger.info("Sync complete. %d EC2 instances, %d EBS volumes processed.", 
                results["ec2_instances_processed"], results["ebs_volumes_processed"])
    
    return results


def _ingest_resource(normalized_aws_data: dict):
    """Upsert a single normalized AWS resource into the database and add metadata."""
    resource_id = normalized_aws_data["resource_id"]
    resource_type = normalized_aws_data["resource_type"]
    region = normalized_aws_data["region"]
    state = normalized_aws_data["state"]
    metadata = normalized_aws_data.get("metadata", {})
    
    # Upsert the base resource (creates or updates status/region/type idempotently)
    db_resource = ResourceRepository.upsert_resource(
        resource_id=resource_id,
        resource_type=resource_type,
        region=region,
        status=state
    )
    
    # Optionally store useful AWS metadata as metrics.
    if resource_type == "ec2_instance":
        # Fetch CloudWatch CPU utilization
        try:
            cw_service = CloudWatchService()
            cpu_data = cw_service.get_ec2_cpu_utilization(resource_id)
            if cpu_data.get("average_cpu") is not None:
                ResourceRepository.upsert_metric(
                    resource_db_id=db_resource.id,
                    metric_name=cpu_data["metric_name"],
                    metric_value=float(cpu_data["average_cpu"])
                )
        except Exception as e:
            logger.error(f"Failed to fetch CloudWatch metrics for {resource_id}: {e}")
            
    elif resource_type == "ebs_volume":
        if "size_gb" in metadata and metadata["size_gb"] is not None:
            # We can store the size as a metric if we want, but currently not required
            # ResourceRepository.add_metric(db_resource.id, 'volume_size_gb', float(metadata["size_gb"]))
            pass

    return db_resource
