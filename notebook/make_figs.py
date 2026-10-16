"""Generate the portfolio's own figures: cropping walkthrough and result charts.
Numbers are taken from the manuscripts' tables."""
import sys
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

import figstyle as fs
from mammo_crop import crop_breast
from results_data import FM_CROSS, IEEE_BINARY_MERGED, IEEE_ABLATION_BIN, IEEE_EFFICIENCY

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
OUT.mkdir(parents=True, exist_ok=True)
fs.apply()


def cropping_steps():
    names = [("data/sample_view_a.png", "Right CC"), ("data/sample_view_b.png", "Left CC")]
    fig, axes = plt.subplots(2, 5, figsize=(15, 6.6), gridspec_kw={"width_ratios": [1, 1, 1, 1.15, 0.8]})
    for row, (path, label) in enumerate(names):
        img = cv2.imread(path, 0)
        r = crop_breast(img)
        x0, y0, x1, y1 = r.box
        ax = axes[row]
        ax[0].imshow(img, cmap="gray"); ax[0].set_title(f"1  Input ({label})")
        ax[1].imshow(r.otsu, cmap="gray"); ax[1].set_title("2  Smoothing + Otsu")
        ax[2].imshow(r.mask, cmap="gray"); ax[2].set_title("3  Morphology + largest\n    component")
        # profile
        p = ax[3]
        rows = np.arange(len(r.profile))
        p.plot(r.profile, rows, color=fs.BLUE, lw=1.6)
        p.invert_yaxis()
        p.axhline(r.ref_row, color=fs.ORANGE, lw=1.2, ls="--")
        p.text(r.profile.max() * 0.03, r.ref_row - 8, "widest row", color=fs.ORANGE, fontsize=9)
        p.axhspan(y0, y1, color=fs.BLUE, alpha=0.07)
        p.set_xlabel("tissue extent (px)"); p.set_ylabel("row")
        p.set_title("4  Row-wise extent profile")
        p.grid(True)
        # overlay + crop
        ax[4].imshow(r.image, cmap="gray"); ax[4].set_title("5  Cropped ROI")
        ax[0].add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec=fs.ORANGE, lw=1.6))
        for a in (ax[0], ax[1], ax[2], ax[4]):
            a.set_xticks([]); a.set_yticks([]); a.grid(False)
            for s in a.spines.values():
                s.set_visible(False)
        kept = 100 * r.image.size / img.size
        ax[4].text(0, -0.08, f"{kept:.0f}% of pixels kept", transform=ax[4].transAxes, color=fs.MUTED, fontsize=9)
    fig.suptitle("Boundary-aware breast cropping, step by step", x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "cropping_steps.png")
    plt.close(fig)


def generalization_ieee():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, bb in zip(axes, ["EfficientNet-B3", "ConvNeXt-Base"]):
        d = IEEE_BINARY_MERGED[bb]
        x = np.arange(2)
        w = 0.36
        b1 = ax.bar(x - w / 2, [d["Merged"][0], d["Merged"][2]], w, label="Merged view", color=fs.GREY)
        b2 = ax.bar(x + w / 2, [d["M+BF"][0], d["M+BF"][2]], w, label="Merged + finding & BI-RADS prototypes", color=fs.BLUE)
        for bars in (b1, b2):
            for b in bars:
                ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.008, f"{b.get_height():.3f}", ha="center", fontsize=9)
        ax.set_xticks(x, ["VinDr-Mammo\n(internal test)", "INbreast\n(external, no fine-tuning)"])
        ax.set_title(bb)
        ax.set_ylim(0.5, 0.86)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Binary macro-F1 (512 px)")
    axes[0].legend(loc="upper right", fontsize=9)
    fig.suptitle("Prototype learning helps most on the external dataset", x=0.01, ha="left", fontsize=12.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "ieee_generalization.png")
    plt.close(fig)


def ablation_ieee():
    rows = IEEE_ABLATION_BIN
    labels = [r[0] for r in rows]
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    y = np.arange(len(rows))[::-1]
    ax.scatter([r[1] for r in rows], y, color=fs.BLUE, s=46, label="VinDr-Mammo", zorder=3)
    ax.scatter([r[2] for r in rows], y, color=fs.ORANGE, s=46, marker="D", label="INbreast (external)", zorder=3)
    for yi, r in zip(y, rows):
        ax.plot([r[1], r[2]], [yi, yi], color=fs.RULE, lw=2, zorder=1)
    ax.set_yticks(y, labels)
    ax.set_xlabel("Binary macro-F1, ConvNeXt-Base, 512 px")
    ax.set_title("Ablation: each component, internal vs external")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(OUT / "ieee_ablation.png")
    plt.close(fig)


def efficiency_ieee():
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.6))
    cfg = ["Two-view\n(dual encoder)", "Shared\ntwo-view", "Merged view\n(proposed)"]
    cols = [fs.GREY, fs.GREY, fs.BLUE]
    for ax, key, title in [(axes[0], 1, "GFLOPs per breast"), (axes[1], 3, "Throughput (breasts / s)")]:
        vals = [IEEE_EFFICIENCY["ConvNeXt-Base"][c][key] for c in ["Two-View", "Shared Two-View", "Merged"]]
        bars = ax.bar(cfg, vals, color=cols, width=0.6)
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.02, f"{b.get_height():g}", ha="center", fontsize=9)
        ax.set_title(title)
        ax.grid(axis="x", visible=False)
    fig.suptitle("ConvNeXt-Base at 512 px: half the compute, ~4x the throughput", x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "ieee_efficiency.png")
    plt.close(fig)


def generalization_fm():
    ids = ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"]
    ds = ["VinDr-Mammo", "INbreast", "LUMINA"]
    fig, ax = plt.subplots(figsize=(10.5, 4.3))
    x = np.arange(len(ids))
    w = 0.26
    colors = [fs.BLUE, fs.ORANGE, fs.GREEN]
    for i, (d, c) in enumerate(zip(ds, colors)):
        vals = [FM_CROSS[e][d][0] for e in ids]
        ax.bar(x + (i - 1) * w, vals, w, label=d + (" (internal)" if i == 0 else " (external)"), color=c)
    ax.set_xticks(x, [f"{e}\n{FM_CROSS[e]['name']}" for e in ids], fontsize=8.5)
    ax.set_ylim(0.6, 0.96)
    ax.set_ylabel("ROC-AUC")
    ax.legend(ncol=3, fontsize=9, loc="upper left")
    ax.grid(axis="x", visible=False)
    ax.set_title("No single configuration wins everywhere: rankings change under dataset shift")
    fig.tight_layout()
    fig.savefig(OUT / "fm_generalization.png")
    plt.close(fig)


def generalization_flow():
    """Study design: where the models were trained and how they were tested."""
    fig, ax = plt.subplots(figsize=(13, 4.6))
    ax.set_xlim(0, 13); ax.set_ylim(0, 4.6); ax.axis("off")

    def box(x, y, w, h, title, lines, ec=fs.INK, fc="white"):
        ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=1.3))
        ax.text(x + 0.18, y + h - 0.3, title, fontsize=11, fontweight="bold", va="top", color=ec)
        for i, t in enumerate(lines):
            ax.text(x + 0.18, y + h - 0.75 - i * 0.36, t, fontsize=9.3, va="top", color=fs.INK)

    def arrow(x0, y0, x1, y1, label="", dy=0.0):
        ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="-|>", color=fs.MUTED, lw=1.3))
        if label:
            ax.text((x0 + x1) / 2, (y0 + y1) / 2 + dy, label, fontsize=8.5, color=fs.MUTED, ha="center",
                    style="italic", bbox=dict(fc="white", ec="none", pad=1.5))

    box(0.1, 1.0, 3.0, 2.7, "Train: VinDr-Mammo", ["Vietnam, multiple hospitals", "3 device vendors", "patient-level split", "train / val / test", "BI-RADS + finding labels"], ec=fs.BLUE, fc="#f3f6fb")
    box(4.7, 2.55, 3.5, 1.85, "Internal test", ["held-out VinDr patients", "stratified by device,", "density and finding type"])
    box(4.7, 0.1, 3.5, 2.15, "External test (frozen model)", ["INbreast: Portugal, Siemens,", "  same BI-RADS labels", "LUMINA: multi-vendor,", "  pathology labels"], ec=fs.ORANGE, fc="#fdf6f1")
    box(9.8, 1.0, 3.1, 2.7, "What is reported", ["macro-F1, AUC, AP,", "QWK, calibration (ECE)", "95% bootstrap CIs", "DeLong / McNemar tests", "failure analysis"])
    arrow(3.15, 2.9, 4.65, 3.45, "same split, all models", dy=0.28)
    arrow(3.15, 1.8, 4.65, 1.2, "no fine-tuning", dy=-0.3)
    arrow(8.25, 3.45, 9.75, 2.9)
    arrow(8.25, 1.2, 9.75, 1.8)
    fig.savefig(OUT / "generalization_study.png")
    plt.close(fig)


if __name__ == "__main__":
    cropping_steps()
    generalization_flow()
    generalization_ieee()
    ablation_ieee()
    efficiency_ieee()
    generalization_fm()
    print("figures written to", OUT)
