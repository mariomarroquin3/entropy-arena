"""Vectores de ejemplo de NIST SP 800-22 rev1a (§2) para validar los tests."""
import numpy as np
import pytest

from entropy_arena.analysis.statistical_tests import monobit_test, runs_test
from entropy_arena.analysis.nist_lite import (
    frequency_within_block, cumulative_sums, longest_run_of_ones)

E100 = np.array([int(c) for c in
    "1100100100001111110110101010001000100001011010001100001000110100"
    "110001001100011001100010100010111000"], dtype=np.uint8)
E128 = np.array([int(c) for c in
    "1100110000010101011011000100110011100000000000100100110101010001"
    "000100111101011010000000110101111100110011100110110001011001 0010".replace(" ", "")],
    dtype=np.uint8)


def test_monobit():
    assert monobit_test(E100)["p_value"] == pytest.approx(0.109599, abs=1e-5)


def test_runs():
    assert runs_test(E100)["p_value"] == pytest.approx(0.500798, abs=1e-5)


def test_block_frequency():
    r = frequency_within_block(E100, block_size=10)
    assert r["p_value"] == pytest.approx(0.706438, abs=1e-5)


def test_cusum():
    assert cumulative_sums(E100, 0)["p_value"] == pytest.approx(0.219194, abs=1e-5)
    assert cumulative_sums(E100, 1)["p_value"] == pytest.approx(0.114866, abs=1e-5)


def test_longest_run():
    # Vector de 128 bits transcrito de memoria (no idéntico al de NIST), así que se
    # contrasta con un cálculo independiente: v = (5, 8, 3, 0) por bloque de 8 bits.
    from scipy.stats import chi2
    pi = np.array([0.2148, 0.3672, 0.2305, 0.1875])
    v = np.array([5, 8, 3, 0])
    expected = chi2.sf(np.sum((v - 16 * pi) ** 2 / (16 * pi)), 3)
    assert longest_run_of_ones(E128)["p_value"] == pytest.approx(expected, abs=1e-9)


def test_monobit_no_uint8_overflow():
    # regresión: 2*bits-1 en uint8 desbordaba y daba p≈1 para datos sesgados
    assert monobit_test(b"\xff" * 1000)["pass"] is False
