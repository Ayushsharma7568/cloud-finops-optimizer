import sys
import os

# Add the project root to the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.aws_ec2_discovery import discover_ec2_instances
from app.services.aws_cloudwatch import CloudWatchService
from botocore.exceptions import ClientError, EndpointConnectionError

def run_verification():
    print("Starting CloudWatch EC2 Metrics Verification...")
    
    instances = discover_ec2_instances()
    if not instances:
        print("No EC2 instances found in the account.")
        return

    cw_service = CloudWatchService()
    
    checked = 0
    with_data = 0
    without_data = 0
    errors = 0

    print(f"Found {len(instances)} EC2 instances. Fetching metrics...")

    for inst in instances:
        instance_id = inst.get('resource_id')
        checked += 1
        try:
            metrics = cw_service.get_ec2_cpu_utilization(instance_id)
            if metrics.get('datapoint_count', 0) > 0:
                with_data += 1
                print(f"[{instance_id}] Metric: {metrics['average_cpu']:.2f}% (Datapoints: {metrics['datapoint_count']})")
            else:
                without_data += 1
                print(f"[{instance_id}] Metric: None (No Datapoints)")
        except Exception as e:
            errors += 1
            print(f"[{instance_id}] ERROR: {e}")

    print("\n--- Verification Summary ---")
    print(f"Instances checked:         {checked}")
    print(f"Instances with data:       {with_data}")
    print(f"Instances without data:    {without_data}")
    print(f"AWS errors encountered:    {errors}")

if __name__ == '__main__':
    run_verification()
