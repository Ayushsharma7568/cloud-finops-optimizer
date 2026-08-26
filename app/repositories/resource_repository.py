from app.extensions import db
from app.models import Resource, ResourceMetric, CostRecord
from sqlalchemy.exc import IntegrityError

class ResourceRepository:
    """Repository for handling database operations for resources, metrics, and costs."""

    @staticmethod
    def get_all_resources():
        """Retrieve all resources."""
        return Resource.query.all()
        
    @staticmethod
    def get_resource_by_external_id(resource_id):
        """Retrieve a specific resource by its cloud ID."""
        return Resource.query.filter_by(resource_id=resource_id).first()

    @staticmethod
    def upsert_resource(resource_id, resource_type, region, status):
        """Insert a resource or update its metadata if it exists."""
        resource = Resource.query.filter_by(resource_id=resource_id).first()
        if not resource:
            resource = Resource(
                resource_id=resource_id,
                resource_type=resource_type,
                region=region,
                status=status
            )
            db.session.add(resource)
        else:
            resource.resource_type = resource_type
            resource.region = region
            resource.status = status
            
        try:
            db.session.commit()
            return resource
        except IntegrityError:
            db.session.rollback()
            # Race condition, re-fetch
            return Resource.query.filter_by(resource_id=resource_id).first()

    @staticmethod
    def add_metric(resource_db_id, metric_name, metric_value):
        """Add a metric record for a resource."""
        metric = ResourceMetric(
            resource_id=resource_db_id,
            metric_name=metric_name,
            metric_value=metric_value
        )
        db.session.add(metric)
        db.session.commit()
        return metric

    @staticmethod
    def add_cost_record(resource_db_id, monthly_cost):
        """Add a cost record for a resource."""
        cost = CostRecord(
            resource_id=resource_db_id,
            monthly_cost=monthly_cost
        )
        db.session.add(cost)
        db.session.commit()
        return cost
