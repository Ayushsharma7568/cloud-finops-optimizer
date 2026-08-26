import pytest
from app import create_app
from app.extensions import db
from app.repositories.resource_repository import ResourceRepository
from app.services.db_loader import load_data_from_db
from app.services.cost_analysis import generate_summary
from app.services.waste_detector import detect_findings
from app.services.recommendation_engine import generate_recommendations

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


def test_full_database_pipeline(app):
    """Test loading data from DB, running the FinOps engine, and getting correct outputs."""
    with app.app_context():
        # Setup a dummy DB resource
        res = ResourceRepository.upsert_resource('i-full-test', 'EC2', 'us-east-1', 'running')
        ResourceRepository.add_cost_record(res.id, 20.0)
        # Add metrics so it gets flagged as underutilized (CPU 5%, Mem 5%)
        ResourceRepository.add_metric(res.id, 'cpu_utilization', 5.0)
        ResourceRepository.add_metric(res.id, 'memory_utilization', 5.0)
        
        # Load from DB
        data = load_data_from_db()
        assert 'ec2' in data
        assert len(data['ec2']) == 1
        assert data['ec2'][0]['resource_id'] == 'i-full-test'
        assert data['ec2'][0]['monthly_cost'] == 20.0
        assert data['ec2'][0]['cpu_utilization_percent'] == 5.0
        
        # Run Summary
        summary = generate_summary(data)
        assert summary['costs']['total'] == 20.0
        
        # Run Waste Detector
        findings = detect_findings(data)
        assert len(findings) == 1
        assert findings[0].issue_type == 'UNDERUTILIZED_EC2'
        
        # Run Recommendations
        recs = generate_recommendations(findings)
        assert len(recs) == 1
        assert recs[0].action_category.name == 'DOWNSIZE'
        assert recs[0].estimated_monthly_savings == 10.0  # mock 50% savings
