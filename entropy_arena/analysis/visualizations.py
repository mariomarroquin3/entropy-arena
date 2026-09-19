from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_byte_histogram(data: bytes, title: str, out_path: Path):
    arr = np.frombuffer(data, dtype=np.uint8)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.hist(arr, bins=64, color="steelblue", edgecolor="black")
    ax.set_title(title)
    ax.set_xlabel("Byte value (0-255)")
    ax.set_ylabel("Frecuencia")
    ax.axhline(len(arr) / 256, color="red", linestyle="--", label="Esperado uniforme")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_arena_ranking(results: list, out_path: Path):
    names = [r["method"] for r in results]
    scores = [r["score"] for r in results]
    order = np.argsort(scores)
    names = [names[i] for i in order]
    scores = [scores[i] for i in order]
    colors = ["#c0392b" if results[i]["deterministic"] else "#27ae60"
              for i in order]
    fig, ax = plt.subplots(figsize=(10, max(4, 0.35 * len(names))))
    ax.barh(names, scores, color=colors)
    ax.set_xlabel("Calidad estadística (0-100), NO entropía real")
    ax.set_title("Entropy Arena — Ranking")
    ax.set_xlim(0, 100)
    for i, s in enumerate(scores):
        ax.text(s + 1, i, f"{s:.1f}", va="center")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_metric_matrix(results: list, out_path: Path):
    metrics = ["shannon", "min_entropy", "collision", "compress",
               "monobit_p", "runs_p", "chi2_bytes_p"]
    labels = [r["method"] for r in results]
    mat = np.array([[r["metrics"].get(m, 0.0) for m in metrics] for r in results])
    fig, ax = plt.subplots(figsize=(1.2 * len(metrics) + 3, 0.4 * len(labels) + 2))
    im = ax.imshow(mat, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(metrics, rotation=45, ha="right")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center",
                    color="white" if mat[i, j] < mat.max() * 0.6 else "black",
                    fontsize=8)
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
