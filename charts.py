import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def build_weight_chart(weights, goal=None, title="Прогресс веса"):
    """
    weights: список кортежей (date_str 'YYYY-MM-DD', weight)
    goal: желаемый вес (опционально)
    Возвращает BytesIO с PNG или None.
    """
    if len(weights) < 2:
        return None

    dates = [datetime.fromisoformat(w[0]).date() for w in weights]
    values = [w[1] for w in weights]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(dates, values, marker="o", color="#4CAF50", linewidth=2, label="Вес")

    if goal:
        ax.axhline(y=goal, color="#FF5722", linestyle="--", linewidth=1.5,
                   label=f"Цель {goal} кг")

    ax.set_title(title, fontsize=14)
    ax.set_xlabel("Дата")
    ax.set_ylabel("Вес, кг")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.autofmt_xdate()

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf
