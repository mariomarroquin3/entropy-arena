"""Demostración: fuentes que 'parecen' aleatorias y se rompen en segundos."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entropy_arena.attacks.demos import (attack_mersenne_twister, attack_randu,
                                         attack_pi_offset, attack_time_seeded)
from entropy_arena.methods.computational.mersenne_twister import MersenneTwister
from entropy_arena.methods.computational.prng_family import RanduMethod
from entropy_arena.methods.mathematical.pi_digits import PiBitsMethod
from entropy_arena.methods.computational.secrets_csprng import SecretsMethod


def main():
    results = [
        attack_mersenne_twister(MersenneTwister(seed=None)),
        attack_randu(RanduMethod()),
        attack_pi_offset(PiBitsMethod()),
        attack_time_seeded(),
    ]
    print(f"\n{'Ataque':<34} {'Observado':>10} {'Éxito':>7} {'Tiempo':>9}")
    print("-" * 64)
    for r in results:
        obs = r.get("observed_bytes", r.get("search_space", "-"))
        print(f"{r['attack']:<34} {str(obs):>10} {'SÍ' if r['success'] else 'no':>7} {r['seconds']:>8.2f}s")
    print("\nControl: contra secrets/os.urandom no existe un ataque equivalente; "
          "observar 2496 bytes no ayuda a predecir el siguiente.")
    ctrl = attack_mersenne_twister(_Csprng())
    print(f"  ataque MT aplicado a secrets -> éxito: {ctrl['success']}")


class _Csprng:
    """Adaptador para aplicar el ataque MT (que asume estado MT) a un CSPRNG: debe fallar."""
    def generate(self, n):
        return SecretsMethod().generate(n)


if __name__ == "__main__":
    main()
