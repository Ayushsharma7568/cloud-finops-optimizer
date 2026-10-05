from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        """Securely hash and store the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password against stored password hash."""
        return check_password_hash(self.password_hash, password)


class Resource(db.Model):
    __tablename__ = 'resources'

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=False)
    region = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    metrics = db.relationship('ResourceMetric', back_populates='resource', cascade="all, delete-orphan")
    cost_records = db.relationship('CostRecord', back_populates='resource', cascade="all, delete-orphan")
    findings = db.relationship('OptimizationFinding', back_populates='resource', cascade="all, delete-orphan")


class ResourceMetric(db.Model):
    __tablename__ = 'resource_metrics'

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False)
    metric_name = db.Column(db.String(100), nullable=False)
    metric_value = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    resource = db.relationship('Resource', back_populates='metrics')


class CostRecord(db.Model):
    __tablename__ = 'cost_records'

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False)
    monthly_cost = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    resource = db.relationship('Resource', back_populates='cost_records')


class AnalysisRun(db.Model):
    __tablename__ = 'analysis_runs'

    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='RUNNING')
    resource_count = db.Column(db.Integer, default=0)
    total_monthly_cost = db.Column(db.Float, default=0.0)
    potential_monthly_savings = db.Column(db.Float, default=0.0)
    error_message = db.Column(db.Text, nullable=True)

    findings = db.relationship('OptimizationFinding', back_populates='analysis_run', cascade="all, delete-orphan")


class OptimizationFinding(db.Model):
    __tablename__ = 'optimization_findings'

    id = db.Column(db.Integer, primary_key=True)
    analysis_run_id = db.Column(db.Integer, db.ForeignKey('analysis_runs.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False)
    issue_type = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(50), nullable=False)
    estimated_monthly_savings = db.Column(db.Float, default=0.0)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    analysis_run = db.relationship('AnalysisRun', back_populates='findings')
    resource = db.relationship('Resource', back_populates='findings')
    recommendations = db.relationship('Recommendation', back_populates='finding', cascade="all, delete-orphan")


class Recommendation(db.Model):
    __tablename__ = 'recommendations'

    id = db.Column(db.Integer, primary_key=True)
    finding_id = db.Column(db.Integer, db.ForeignKey('optimization_findings.id'), nullable=False)
    action_category = db.Column(db.String(100), nullable=False)
    recommendation_text = db.Column(db.Text, nullable=False)
    confidence = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.Integer, default=0) # e.g. 1, 2, 3...
    estimated_monthly_savings = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    finding = db.relationship('OptimizationFinding', back_populates='recommendations')
