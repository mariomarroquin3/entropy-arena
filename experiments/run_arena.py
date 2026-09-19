import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entropy_arena.methods.computational.secrets_csprng import SecretsMethod
from entropy_arena.methods.computational.os_urandom import OsUrandomMethod
from entropy_arena.methods.computational.mersenne_twister import MersenneTwister
from entropy_arena.methods.computational.uuid4 import UUID4Method
from entropy_arena.methods.mathematical.brownian_motion import BrownianMotionMethod
from entropy_arena.methods.mathematical.logistic_map import LogisticMapMethod
from entropy_arena.methods.mathematical.lorenz_attractor import LorenzAttractorMethod
from entropy_arena.methods.mathematical.cellular_automata import Rule30Method
from entropy_arena.methods.physical_manual.dice_rolls import ManualDiceRolls
from entropy_arena.methods.physical_manual.coin_flips import ManualCoinFlips
from entropy_arena.methods.hybrid.coin_von_neumann import CoinVonNeumann
from entropy_arena.methods.computational.prng_family import RanduMethod, Pcg64Method
from entropy_arena.methods.mathematical.pi_digits import PiBitsMethod
from entropy_arena.methods.physical_manual.cpu_jitter import CpuJitterMethod
from entropy_arena.methods.hybrid.xor_combiner import XorCombiner
from entropy_arena.arena.runner import Arena
from entropy_arena.arena.leaderboard import print_leaderboard, save_results
from entropy_arena.analysis.visualizations import plot_arena_ranking, plot_metric_matrix


def main():
    data_dir = ROOT / "data" / "manual_rolls"
    results_dir = ROOT / "data" / "results"

    arena = Arena(nbytes=12500, n_samples=100, results_dir=str(results_dir))

    arena.register(SecretsMethod())
    arena.register(OsUrandomMethod())
    arena.register(UUID4Method())
    arena.register(MersenneTwister(seed=None))
    arena.register(MersenneTwister(seed=42))

    arena.register(BrownianMotionMethod())
    arena.register(LogisticMapMethod())
    arena.register(LorenzAttractorMethod())
    arena.register(Rule30Method())
    arena.register(PiBitsMethod())
    arena.register(RanduMethod())
    arena.register(Pcg64Method())
    arena.register(CpuJitterMethod())
    arena.register(CpuJitterMethod(conditioned=True))
    arena.register(XorCombiner([MersenneTwister(seed=42), BrownianMotionMethod(), CpuJitterMethod(conditioned=True)]))
    arena.register(XorCombiner([MersenneTwister(seed=42), OsUrandomMethod()]))

    dice_csv = data_dir / "dice.csv"
    coins_csv = data_dir / "coins.csv"
    if dice_csv.exists():
        arena.register(ManualDiceRolls(csv_path=str(dice_csv)))
    if coins_csv.exists():
        arena.register(ManualCoinFlips(csv_path=str(coins_csv)))
        arena.register(CoinVonNeumann(csv_path=str(coins_csv)))

    results = arena.run()
    print_leaderboard(results)
    save_results(results, results_dir / "leaderboard.json")

    plot_arena_ranking(results, results_dir / "ranking.png")
    plot_metric_matrix(results, results_dir / "metric_matrix.png")
    print(f"[viz] Gráficos guardados en {results_dir}/")


if __name__ == "__main__":
    main()
