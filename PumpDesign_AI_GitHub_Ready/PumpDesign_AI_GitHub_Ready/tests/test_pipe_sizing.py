from calculations.pipe_sizing import PipeRegistry, size_pipe_candidates, select_first_acceptable
from calculations.units import M3S_PER_GPM


def test_registry_has_four_material_families():
    reg = PipeRegistry()
    assert {"MS/carbon steel", "PVC-U", "HDPE/PE100", "PP-R"}.issubset(set(reg.materials()))
    assert len(reg.records) > 100


def test_actual_id_is_less_than_od():
    reg = PipeRegistry()
    assert all(r.inside_diameter_m < r.outside_diameter_m for r in reg.records)
    assert all(r.inside_diameter_m > 0 for r in reg.records)


def test_candidate_generation_uses_actual_id():
    reg = PipeRegistry()
    q = 277.7777778 * M3S_PER_GPM
    candidates = size_pipe_candidates(q, "MS/carbon steel", registry=reg, velocity_max_mps=2.0)
    assert candidates
    assert all(c.velocity_mps > 0 for c in candidates)
    selected = select_first_acceptable(candidates)
    assert selected is not None
    assert selected.velocity_mps <= 2.0


def test_no_hidden_selection_without_velocity_criterion():
    reg = PipeRegistry()
    candidates = size_pipe_candidates(0.01, "PVC-U", registry=reg)
    assert select_first_acceptable(candidates) is None
    assert all(c.velocity_status == "NOT_CHECKED" for c in candidates)


def test_hazen_williams_loss_is_optional_and_deterministic():
    reg = PipeRegistry()
    candidates = size_pipe_candidates(
        0.01, "HDPE/PE100", registry=reg, velocity_max_mps=2.0,
        hazen_williams_c=150, length_m=100, schedule_or_sdr="SDR 11"
    )
    assert candidates
    assert all(c.head_loss_m is not None for c in candidates)
