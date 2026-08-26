import sys
import os
from pathlib import Path

# Add project root to python path so we can import app modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.services.data_loader import load_ec2_data, load_ebs_data, load_s3_data
from app.repositories.resource_repository import ResourceRepository

def seed_database():
    app = create_app()
    with app.app_context():
        # Create all tables if they don't exist
        db.create_all()

        print("Seeding EC2 Data...")
        ec2_data = load_ec2_data()
        for item in ec2_data:
            resource = ResourceRepository.upsert_resource(
                resource_id=item['resource_id'],
                resource_type='EC2',
                region=item['region'],
                status=item['status']
            )
            # Add cost record
            ResourceRepository.add_cost_record(resource.id, item['monthly_cost'])
            # Add metrics
            ResourceRepository.add_metric(resource.id, 'cpu_utilization', item['cpu_utilization'])
            ResourceRepository.add_metric(resource.id, 'memory_utilization', item['memory_utilization'])

        print("Seeding EBS Data...")
        ebs_data = load_ebs_data()
        for item in ebs_data:
            resource = ResourceRepository.upsert_resource(
                resource_id=item['volume_id'],
                resource_type='EBS',
                region=item['region'],
                status=item['status']
            )
            ResourceRepository.add_cost_record(resource.id, item['monthly_cost'])
            # Compute utilization % as a metric
            utilization = (item['used_gb'] / item['size_gb']) * 100 if item['size_gb'] > 0 else 0
            ResourceRepository.add_metric(resource.id, 'storage_utilization', utilization)

        print("Seeding S3 Data...")
        s3_data = load_s3_data()
        for item in s3_data:
            resource = ResourceRepository.upsert_resource(
                resource_id=item['bucket_name'],
                resource_type='S3',
                region=item['region'],
                status='available' # S3 doesn't have state in our mock
            )
            ResourceRepository.add_cost_record(resource.id, item['monthly_cost'])
            ResourceRepository.add_metric(resource.id, 'total_size_gb', item['storage_gb'])

        print("Database seeding completed.")

if __name__ == '__main__':
    seed_database()
