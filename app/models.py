from app import db
from datetime import datetime


class Resource(db.Model):
    """Cloud resource model."""

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.String(100), unique=True, nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)  # EC2, S3, EBS
    region = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="active")
    cpu_utilization = db.Column(db.Float, default=0.0)
    memory_utilization = db.Column(db.Float, default=0.0)
    monthly_cost = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Resource {self.resource_id} ({self.resource_type})>"


class CostRecord(db.Model):
    """Cost record model."""

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.String(100), db.ForeignKey("resource.resource_id"))
    service = db.Column(db.String(50), nullable=False)
    cost = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CostRecord {self.service} ${self.cost}>"


class Recommendation(db.Model):
    """Optimization recommendation model."""

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.String(100), db.ForeignKey("resource.resource_id"))
    recommendation_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    estimated_savings = db.Column(db.Float, default=0.0)
    priority = db.Column(db.String(20), default="medium")  # low, medium, high
    status = db.Column(db.String(20), default="pending")  # pending, applied, dismissed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Recommendation {self.recommendation_type} - ${self.estimated_savings}>"
