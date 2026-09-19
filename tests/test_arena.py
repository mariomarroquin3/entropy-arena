import os
import pytest

from entropy_arena.arena.scoring import (
    mcv_min_entropy, aggregate_test, compute_metrics, verdict)
from entropy_arena.arena.runner import Arena
from entropy_arena.methods.computational.os_urandom import OsUrandomMethod
from entropy_arena.methods.computational.prng_family import RanduMethod, Pcg64Method
from entropy_arena.methods.mathematical.pi_digits import pi_fixed
from entropy_arena.methods.hybrid.xor_combiner import XorCombiner
from entropy_arena.methods.mathematical.cellular_automata import Rule30Method


def test_mcv_bounds():
    assert mcv_min_entropy(b"\x00" * 1000) == pytest.approx(0.0, abs=1e-9)
    assert 6.5 < mcv_min_entropy(os.urandom(12500)) < 8.0


def test_aggregate_uniform_pvalues_pass():
    import numpy as np
    pv = np.linspace(0.005, 0.995, 100)
    assert aggregate_test(list(pv))["uniformity_ok"]
    assert not aggregate_test([0.0] * 100)["ok"]


def test_verdicts():
    assert verdict(100, 256) == "APTO"
    assert verdict(100, 0).startswith("IMITA")
    assert verdict(10, 0).startswith("FALLA")


def test_pi_prefix():
    assert hex(pi_fixed(64))[:12] == "0x3243f6a888"


def test_randu_recurrence():
    s = RanduMethod().generate(50)
    assert len(s.data) == 50 and s.bits_claimed == 30.0


def test_xor_length_and_bits():
    x = XorCombiner([OsUrandomMethod(), Pcg64Method()])
    s = x.generate(64)
    assert len(s.data) == 64 and s.bits_claimed == 512.0


def test_rule30_length():
    assert len(Rule30Method().generate(32).data) == 32


def test_urandom_is_apto_and_randu_not():
    arena = Arena(nbytes=2500, n_samples=60, results_dir="data/results")
    arena.register(OsUrandomMethod()).register(RanduMethod())
    res = {r["method"]: r for r in arena.run()}
    assert res["os.urandom"]["verdict"] in ("APTO",) or res["os.urandom"]["score"] >= 65
    assert res["randu_lcg"]["real_bits"] < 128


def test_sp800_90b_estimators():
    import numpy as np
    from entropy_arena.analysis.sp800_90b import min_entropy_per_bit
    rng = np.random.default_rng(1)
    rnd = min_entropy_per_bit(os.urandom(12500))
    assert len(rnd) == 11 and rnd["min"] > 0.25      # 10 estimadores + mínimo
    periodic = min_entropy_per_bit(np.tile([0, 1, 1, 0], 25000).astype(np.uint8))
    assert periodic["min"] < 0.05
    # el estimador nunca debe superar la min-entropy verdadera (aprox.) de una fuente sesgada
    biased = min_entropy_per_bit((rng.random(100000) < 0.7).astype(np.uint8))
    assert 0.25 < biased["min"] <= 0.52
    # fuente con memoria: P(repetir)=0.8 => min-entropy verdadera 0.322 bits/bit
    r, b = rng.random(60000), [0]
    for i in range(1, 60000):
        b.append(b[-1] if r[i] < 0.8 else 1 - b[-1])
    sticky = min_entropy_per_bit(np.array(b, dtype=np.uint8))
    assert sticky["min"] <= 0.36
    assert sticky["mcv"] > 0.9   # MCV solo, ciego a la memoria: por eso hace falta el mínimo


def test_local_run_bound_monotonic():
    from entropy_arena.analysis.sp800_90b import _local_p
    assert 0.5 < _local_p(30000, 12) < _local_p(30000, 16) < _local_p(30000, 25) < 1.0


def test_manual_reports():
    from entropy_arena.manual_input.quality import dice_report, coin_report
    import random
    rolls = [random.randint(1, 6) for _ in range(300)]
    r = dice_report(rolls)
    assert r["bits_measured"] < r["bits_nominal"] and r["chi2_p"] is not None
    assert coin_report(["H"] * 100)["bits_measured"] == 0.0


def test_dice_method_claims_measured_bits():
    from entropy_arena.methods.physical_manual.dice_rolls import ManualDiceRolls
    import random
    rolls = [random.randint(1, 6) for _ in range(100)]
    s = ManualDiceRolls(rolls=rolls).generate(32)
    assert 0 < s.bits_claimed < 100 * 2.585


def test_uuid4_does_not_overclaim():
    from entropy_arena.methods.computational.uuid4 import UUID4Method
    assert UUID4Method().generate(32).bits_claimed == pytest.approx(32 * 8 * 122 / 128)


def test_logistic_fixed_x0_claims_no_entropy():
    from entropy_arena.methods.mathematical.logistic_map import LogisticMapMethod
    assert LogisticMapMethod(x0=0.3).generate(8).bits_claimed == 0.0


def test_plots_and_metric_keys(tmp_path):
    from entropy_arena.analysis.visualizations import plot_metric_matrix, plot_arena_ranking
    arena = Arena(nbytes=1000, n_samples=8, results_dir=str(tmp_path))
    arena.register(OsUrandomMethod())
    res = arena.run()
    assert "chi2_bytes_p" in res[0]["metrics"]
    plot_metric_matrix(res, tmp_path / "m.png")
    plot_arena_ranking(res, tmp_path / "r.png")
    assert (tmp_path / "m.png").exists()


def test_vault_rejects_duplicate_keys():
    from entropy_arena.wallet.multisig_builder import build_multisig_vault
    from entropy_arena.methods.physical_manual.dice_rolls import ManualDiceRolls
    import random
    rolls = [random.randint(1, 6) for _ in range(200)]
    d = ManualDiceRolls(rolls=rolls)
    with pytest.raises(ValueError):
        build_multisig_vault([d, d, d])


def test_lrs_flags_deterministic_sequence():
    import numpy as np
    from entropy_arena.analysis.sp800_90b import lrs
    assert lrs(np.tile([0, 1, 1, 0], 25000).astype(np.uint8)) < 0.05
