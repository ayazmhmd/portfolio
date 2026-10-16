"""Shared plot style for the portfolio figures and notebook."""
import matplotlib as mpl

INK = "#1e1e1e"
MUTED = "#6b6b6b"
RULE = "#d9d6cf"
BLUE = "#1a4d8f"
ORANGE = "#c0612b"
GREEN = "#3a7d44"
GREY = "#9a9a9a"
PALETTE = [BLUE, ORANGE, GREEN, "#7a5195", "#b8860b", GREY]


def apply():
    mpl.rcParams.update({
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
        "font.family": "DejaVu Serif",
        "font.size": 10.5,
        "axes.edgecolor": RULE,
        "axes.labelcolor": INK,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": "#eeece6",
        "grid.linewidth": 0.8,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "legend.frameon": False,
        "axes.prop_cycle": mpl.cycler(color=PALETTE),
    })
