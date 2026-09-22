from models import *

project = Project(
    project_name='PumpDesign AI Test Project',
    location='Lahore, Pakistan',
    jurisdiction='Punjab',
    authority='Test Authority',
    building_type='Apartment',
)

design = Design(
    project_id='TEST-001',
    application=PumpApplication.TRANSFER,
    scenario='UGT → OHT',
    inputs=[DesignInput(name='OHT Capacity', value=25000, unit='US gal')],
)

assert project.project_name == 'PumpDesign AI Test Project'
assert design.application == PumpApplication.TRANSFER
assert design.inputs[0].value == 25000
print('STEP 1 MODEL VALIDATION: PASS')
print('Project:', project.project_name)
print('Application:', design.application.value)
print('Scenario:', design.scenario)
