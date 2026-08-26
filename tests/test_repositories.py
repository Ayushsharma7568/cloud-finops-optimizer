import pytest
from app import create_app
from app.extensions import db
from app.repositories.resource_repository import ResourceRepository
from app.repositories.analysis_repository import AnalysisRepository

@pytest.fixture
def app():
    """Create a Flask app with an in-memory SQLite DB for testing."""
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_upsert_resource(app):
    """Test inserting and updating a resource."""
    with app.app_context():
        # Insert
        res1 = ResourceRepository.upsert_resource('i-123', 'EC2', 'us-east-1', 'running')
        assert res1.id is not None
        assert res1.resource_id == 'i-123'
        
        # Update
        res2 = ResourceRepository.upsert_resource('i-123', 'EC2', 'us-east-1', 'stopped')
        assert res1.id == res2.id
        assert res2.status == 'stopped'
        
        # Verify total resources is 1
        all_res = ResourceRepository.get_all_resources()
        assert len(all_res) == 1

def test_add_metrics_and_costs(app):
    """Test adding metrics and costs to a resource."""
    with app.app_context():
        res = ResourceRepository.upsert_resource('vol-123', 'EBS', 'us-east-1', 'available')
        
        metric = ResourceRepository.add_metric(res.id, 'storage_utilization', 45.0)
        assert metric.id is not None
        assert metric.metric_value == 45.0
        
        cost = ResourceRepository.add_cost_record(res.id, 10.5)
        assert cost.id is not None
        assert cost.monthly_cost == 10.5

def test_analysis_run_lifecycle(app):
    """Test creating, completing, and retrieving an analysis run."""
    with app.app_context():
        # Create
        run = AnalysisRepository.create_analysis_run()
        assert run.status == 'RUNNING'
        assert run.completed_at is None
        
        # Complete
        completed_run = AnalysisRepository.complete_analysis_run(run.id, 5, 100.0, 20.0)
        assert completed_run.status == 'SUCCESS'
        assert completed_run.resource_count == 5
        assert completed_run.completed_at is not None
        
        # Retrieve latest
        latest = AnalysisRepository.get_latest_analysis_run()
        assert latest.id == completed_run.id

def test_save_findings_and_recommendations(app):
    """Test saving findings and recommendations."""
    with app.app_context():
        run = AnalysisRepository.create_analysis_run()
        res = ResourceRepository.upsert_resource('i-123', 'EC2', 'us-east-1', 'running')
        
        finding = AnalysisRepository.save_finding(
            run.id, res.id, 'UNDERUTILIZED_EC2', 'MEDIUM', 5.0, 'Low CPU'
        )
        assert finding.id is not None
        
        rec = AnalysisRepository.save_recommendation(
            finding.id, 'DOWNSIZE', 'Downsize to t3.micro', 'MEDIUM', 1, 5.0
        )
        assert rec.id is not None
        assert rec.finding_id == finding.id
