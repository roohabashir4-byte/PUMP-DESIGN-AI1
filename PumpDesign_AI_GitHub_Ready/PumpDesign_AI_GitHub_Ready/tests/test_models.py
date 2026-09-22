from models import Project, Design, PumpApplication, Calculation, ValidationResult, ValidationStatus

def test_models():
    p = Project(project_name='Test', location='Pakistan', building_type='Apartment')
    d = Design(project_id='P1', application=PumpApplication.TRANSFER, scenario='UGT to OHT')
    c = Calculation(name='Flow', formula='Q=V/t', result=10, unit='gpm')
    v = ValidationResult(name='Example', status=ValidationStatus.PASS, message='Pass')
    assert p.project_name == 'Test'
    assert d.application == PumpApplication.TRANSFER
    assert c.result == 10
    assert v.status == ValidationStatus.PASS
