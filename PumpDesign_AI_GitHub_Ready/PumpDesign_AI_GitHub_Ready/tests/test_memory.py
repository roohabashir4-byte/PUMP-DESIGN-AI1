from pathlib import Path
from memory.database import MemoryDB
from memory.projects import ProjectMemory
from memory.revisions import changed_parameters, create_design_revision

def test_project_design_persistence(tmp_path: Path):
    db = MemoryDB(tmp_path / 'memory.sqlite3')
    svc = ProjectMemory(db)
    inputs = {'project_name':'Demo','location':'Lahore','jurisdiction':'Punjab','building_type':'Apartment','required_transfer_time':{'value':90,'unit':'min'}}
    pid, did = svc.save_project_and_design(inputs, 'TRANSFER', {'status':'CALCULATED','pump_duty':{'flow':100}})
    assert db.get_project(pid)['project_name'] == 'Demo'
    design = db.get_design(did)
    assert design['inputs']['project_name'] == 'Demo'
    assert design['result']['status'] == 'CALCULATED'

def test_revision_detects_changes(tmp_path: Path):
    db = MemoryDB(tmp_path / 'memory.sqlite3')
    svc = ProjectMemory(db)
    old={'project_name':'Demo','transfer_time':90}
    pid,did=svc.save_project_and_design(old,'TRANSFER',{'status':'CALCULATED'})
    new={'project_name':'Demo','transfer_time':120}
    assert changed_parameters(old,new)['transfer_time']['old']==90
    n=create_design_revision(db,did,'Changed transfer time',old,new,{'status':'CALCULATED'})
    assert n == 1
    assert db.list_revisions(did)[0]['changed_parameters']['transfer_time']['new']==120

def test_revision_requires_actual_change(tmp_path: Path):
    db=MemoryDB(tmp_path/'memory.sqlite3')
    svc=ProjectMemory(db)
    inputs={'project_name':'Demo','location':'Lahore','building_type':'Apartment'}
    _,did=svc.save_project_and_design(inputs,'TRANSFER',{'status':'CALCULATED'})
    try:
        create_design_revision(db,did,'No change',inputs,dict(inputs),{'status':'CALCULATED'})
        assert False
    except ValueError as exc:
        assert 'No design input changes' in str(exc)
