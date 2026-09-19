import os
import numpy as np
import pytest

from entropy_arena.attacks.demos import (
    untemper, attack_mersenne_twister, attack_randu, attack_time_seeded, mt_clone_from_bytes)
from entropy_arena.analysis.structure_tests import (
    binary_matrix_rank, dft_spectral, approximate_entropy, linear_complexity,
    strided_linear_complexity)
from entropy_arena.methods.computational.mersenne_twister import MersenneTwister
from entropy_arena.methods.computational.prng_family import RanduMethod
from entropy_arena.methods.computational.secrets_csprng import SecretsMethod


def test_untemper_inverts_temper():
    def temper(y):
        y ^= y >> 11
        y ^= (y << 7) & 0x9D2C5680
        y ^= (y << 15) & 0xEFC60000
        return y ^ (y >> 18)
    for v in (0, 1, 0xDEADBEEF, 0xFFFFFFFF, 123456789):
        assert untemper(temper(v)) == v


def test_mt_clone_predicts_future_output():
    r = attack_mersenne_twister(MersenneTwister(seed=None))
    assert r["success"]


def test_mt_attack_fails_on_csprng():
    class C:
        def generate(self, n):
            return SecretsMethod().generate(n)
    assert not attack_mersenne_twister(C())["success"]


def test_randu_state_recovery():
    assert attack_randu(RanduMethod())["success"]


def test_time_seeded_bruteforce():
    assert attack_time_seeded(window_seconds=3000)["success"]


def test_structure_tests_pass_random_and_flag_periodic():
    rnd = os.urandom(8192)
    for f in (binary_matrix_rank, dft_spectral, approximate_entropy, linear_complexity):
        assert f(rnd)["pass"] or f(os.urandom(8192))["pass"]     # tolera 1% de falsos rechazos
    per = np.tile([0, 1, 1, 0, 1, 0, 0, 0], 8192).astype(np.uint8)  # 65536 bits periódicos
    assert not linear_complexity(per)["pass"]
    assert not dft_spectral(per)["pass"]
    assert not approximate_entropy(per)["pass"]


def test_strided_linear_complexity_exposes_mt_only():
    n = 45000 * 32 // 8
    mt = strided_linear_complexity(MersenneTwister().generate(n).data)
    assert mt["statistic"] == 19937 and not mt["pass"]
    assert strided_linear_complexity(SecretsMethod().generate(n).data)["pass"]
