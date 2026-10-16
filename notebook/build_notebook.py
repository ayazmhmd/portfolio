"""Build the research-summary notebook (Jupyter / Kaggle compatible)."""
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).parent
nb = nbf.v4.new_notebook()
C = []


def md(s):
    C.append(nbf.v4.new_markdown_cell(s.strip()))


def code(s):
    C.append(nbf.v4.new_code_cell(s.strip()))


md("""
# Research summary: multi-view mammography and clinical risk models
**Ayaz Mehmood** · MS Data Science (NUST) · [ayazmehmood550@gmail.com](mailto:ayazmehmood550@gmail.com)

This notebook summarises the experiments behind my three most recent manuscripts:

| # | Paper | Status | What it asks |
|---|---|---|---|
| 1 | *Intelligent Breast Cropping and Multi-View Fusion with Finding-BI-RADS Prototype Learning for Mammogram Classification* | IEEE Access, under review | Can one encoder read both views of a breast, and do clinically defined prototypes improve generalisation? |
| 2 | *Adaptive Foundation Model Learning for Breast-Level Classification from Dual-View Mammography* (MammoRLE-MIL) | ready for submission | How should a frozen DINOv2 model be adapted and pooled for dual-view mammography, and does it transfer? |
| 3 | *Machine Learning-Enabled Pre-Screening for Five-Year Risk of Common Cancers* | Cancer Epidemiology, submitted | Can routine primary-care data stratify cancer risk better than age alone? |

What runs here:
1. A re-implementation of the **boundary-aware breast cropping** used in paper 1, applied step by step to two sample mammograms.
2. The **result tables** of papers 1 and 2 (transcribed from the manuscripts), with charts of the main findings: internal vs external performance, ablations, efficiency.

The models themselves were trained on VinDr-Mammo, which is under a credentialed-access licence, so the training data and checkpoints are not included here.
""")

code("""
import numpy as np, pandas as pd, matplotlib as mpl, matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
import cv2

INK, MUTED, RULE = "#1e1e1e", "#6b6b6b", "#d9d6cf"
BLUE, ORANGE, GREEN, GREY = "#1a4d8f", "#c0612b", "#3a7d44", "#9a9a9a"
mpl.rcParams.update({"figure.dpi": 110, "font.family": "DejaVu Serif", "font.size": 10.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": RULE,
    "axes.grid": True, "grid.color": "#eeece6", "axes.titleweight": "bold", "axes.titlelocation": "left",
    "legend.frameon": False, "xtick.color": MUTED, "ytick.color": MUTED})
pd.set_option("display.precision", 3)
""")

md("""
## 1 · Paper 1: cropping, merged views and Finding-BI-RADS prototypes

**Pipeline.** Each mammogram is cropped to the breast; the MLO view is flipped so that the chest walls of both views meet in the middle; the two crops are concatenated into one composite and passed through **a single encoder** (EfficientNet-B3 or ConvNeXt-Base). During training, two prototype memories (one for radiological *finding types*, one for *BI-RADS categories*) pull embeddings towards clinically meaningful anchors. The prototypes are used only during training, so they add nothing at inference.

Tasks: binary normal (BI-RADS 1) vs abnormal (BI-RADS 2–5), and five-class BI-RADS grading with an ordinal (CORAL-style) head. Trained on **VinDr-Mammo**, tested externally on **INbreast** without fine-tuning.

### 1.1 Boundary-aware cropping, re-implemented
The steps follow the paper: Gaussian smoothing → Otsu threshold → 5×5 morphological closing/opening → largest connected component → a **row-wise tissue-extent profile**. Starting from the widest row, the profile is followed up and down while the breast keeps tapering. Where it stops tapering (pectoral muscle, skin folds, artefacts), the crop boundary is placed, with a margin. The crop uses no lesion annotations.
""")

code((HERE / "mammo_crop.py").read_text().split('"""', 2)[2].strip())

code("""
DATA = next((p for p in [Path("data"), Path("/kaggle/input/mammo-samples")] if (p / "sample_view_a.png").exists()), None)
if DATA is None:
    print("Sample images not found: put sample_view_a.png / sample_view_b.png in ./data")
else:
    fig, axes = plt.subplots(2, 5, figsize=(15, 6.6), gridspec_kw={"width_ratios": [1, 1, 1, 1.15, 0.8]})
    for row, (name, label) in enumerate([("sample_view_a.png", "Right CC"), ("sample_view_b.png", "Left CC")]):
        img = cv2.imread(str(DATA / name), 0)
        r = crop_breast(img)
        x0, y0, x1, y1 = r.box
        ax = axes[row]
        ax[0].imshow(img, cmap="gray"); ax[0].set_title(f"1  Input ({label})")
        ax[0].add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec=ORANGE, lw=1.6))
        ax[1].imshow(r.otsu, cmap="gray"); ax[1].set_title("2  Smoothing + Otsu")
        ax[2].imshow(r.mask, cmap="gray"); ax[2].set_title("3  Largest component")
        ax[3].plot(r.profile, np.arange(len(r.profile)), color=BLUE); ax[3].invert_yaxis()
        ax[3].axhline(r.ref_row, color=ORANGE, ls="--"); ax[3].axhspan(y0, y1, color=BLUE, alpha=.07)
        ax[3].set_title("4  Row-wise extent"); ax[3].set_xlabel("tissue extent (px)")
        ax[4].imshow(r.image, cmap="gray"); ax[4].set_title("5  Cropped ROI")
        for a in (ax[0], ax[1], ax[2], ax[4]):
            a.axis("off")
        print(f"{label}: laterality={r.laterality}, box={r.box}, kept {100*r.image.size/img.size:.0f}% of pixels")
    plt.tight_layout(); plt.show()
""")

md("""
In the paper, every annotated lesion box in VinDr-Mammo was mapped through this crop to check that no diagnostic tissue is lost:
""")

code("""
crop_check = pd.DataFrame({"lesion boxes": [2254], "fully inside crop": [2239], "partly cut": [9], "outside crop": [6]})
crop_check["% fully kept"] = 100 * crop_check["fully inside crop"] / crop_check["lesion boxes"]
crop_check
""")

md("### 1.2 Results")
code((HERE / "results_data.py").read_text().split('"""', 2)[2].strip())

code("""
rows = []
for bb, d in IEEE_BINARY_TWOVIEW.items():
    rows.append((bb, "Two-view (dual encoder)", "512", *d["512"]))
for bb, d in IEEE_BINARY_MERGED.items():
    rows.append((bb, "Merged view", "512", *d["Merged"]))
    rows.append((bb, "Merged view", "1024", *d["Merged 1024px"]))
    rows.append((bb, "Merged + prototypes (M+BF)", "512", *d["M+BF"]))
binary = pd.DataFrame(rows, columns=["Backbone", "Configuration", "Res.", "VinDr F1", "VinDr AUC", "INbreast F1", "INbreast AUC"])
binary.style.format(precision=3).set_caption("Binary normal vs abnormal (macro-F1, AUC)")
""")

code("""
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
for ax, bb in zip(axes, IEEE_BINARY_MERGED):
    d = IEEE_BINARY_MERGED[bb]; x = np.arange(2); w = .36
    for off, key, col, lab in [(-w/2, "Merged", GREY, "Merged view"), (w/2, "M+BF", BLUE, "+ finding & BI-RADS prototypes")]:
        bars = ax.bar(x + off, [d[key][0], d[key][2]], w, color=col, label=lab)
        ax.bar_label(bars, fmt="%.3f", fontsize=9)
    ax.set_xticks(x, ["VinDr-Mammo (internal)", "INbreast (external)"]); ax.set_title(bb); ax.set_ylim(.5, .86); ax.grid(axis="x", visible=False)
axes[0].set_ylabel("Binary macro-F1"); axes[0].legend(fontsize=9)
plt.suptitle("Prototype learning: small internal gain, large external gain", x=.01, ha="left", fontweight="bold"); plt.tight_layout(); plt.show()
""")

code("""
rows = []
for bb in IEEE_FIVECLASS_MERGED:
    for cfg in ("Merged", "M+BF"):
        f = IEEE_FIVECLASS_MERGED[bb][cfg]; o = IEEE_ORDINAL[bb][cfg]
        rows.append((bb, cfg, f[0], f[1], o[0], o[1], f[2], f[3], o[2], o[3]))
five = pd.DataFrame(rows, columns=["Backbone", "Config", "VinDr F1", "VinDr AUC", "VinDr QWK", "VinDr MAE",
                                   "INbreast F1", "INbreast AUC", "INbreast QWK", "INbreast MAE"])
five.style.format(precision=3).set_caption("Five-class BI-RADS grading (512 px)")
""")

code("""
abl = pd.DataFrame(IEEE_ABLATION_BIN, columns=["Variant (ConvNeXt-Base, binary)", "VinDr F1", "INbreast F1"])
abl["gap (internal - external)"] = abl["VinDr F1"] - abl["INbreast F1"]
abl.style.format(precision=3).background_gradient(subset=["INbreast F1"], cmap="Blues")
""")

code("""
eff = pd.DataFrame([(bb, cfg, *v) for bb, d in IEEE_EFFICIENCY.items() for cfg, v in d.items()],
                   columns=["Backbone", "Configuration", "Params (M)", "GFLOPs", "Latency (ms)", "Throughput (breasts/s)"])
eff
""")

md("""
**Take-aways from paper 1**
- One encoder on a merged CC+MLO composite matches a parameter-matched shared two-view encoder, with **half the FLOPs and about 4× the throughput**.
- Cropping helps (removing it lowers F1 for both backbones), and 99.3% of lesion boxes stay fully inside the crop.
- Finding + BI-RADS prototypes give a modest internal gain but a **large external gain** (INbreast binary F1 +0.095 for EfficientNet-B3). The gain is significant on McNemar's test (p < 0.01) for all four model–dataset pairs, and larger than the seed-to-seed spread (SD 0.006).
- Where it still fails: BI-RADS 3 and 4 recall (0.16–0.40), dense breasts, and the Planmed device. These are reported per subgroup with 95% CIs in the paper.
""")

md("""
## 2 · Paper 2: MammoRLE-MIL, adapting DINOv2 to dual-view mammography

A frozen **DINOv2 ViT-B/14** encodes each view at 518×518 (1,369 patch tokens). Two components are added and ablated:
- **MoLRE (mixture of low-rank experts):** K LoRA experts on the query and value projections, mixed per image by a small router. The backbone stays frozen, and the zero-initialised experts start out as the original model.
- **Multi-head gated-attention MIL:** several attention heads pool the patch tokens of each view; their outputs are weighted and fused. CC and MLO embeddings are concatenated for one breast-level prediction.

Eight configurations (E1–E8) were trained on VinDr-Mammo and tested on INbreast (same BI-RADS label definition) and LUMINA (multi-vendor, pathology labels), without any fine-tuning on the external sets.
""")

code("""
ids = list(FM_CROSS)
fm = pd.DataFrame([(e, FM_CROSS[e]["name"], *[v for ds in ("VinDr-Mammo", "INbreast", "LUMINA") for v in FM_CROSS[e][ds]]) for e in ids],
                  columns=["ID", "Configuration", "VinDr AUC", "VinDr AP", "INbreast AUC", "INbreast AP", "LUMINA AUC", "LUMINA AP"])
fm.style.format(precision=3).highlight_max(subset=fm.columns[2:], color="#dbe6f4")
""")

code("""
fig, ax = plt.subplots(figsize=(11, 4.2)); x = np.arange(len(ids)); w = .26
for i, (ds, col) in enumerate(zip(["VinDr-Mammo", "INbreast", "LUMINA"], [BLUE, ORANGE, GREEN])):
    ax.bar(x + (i - 1) * w, [FM_CROSS[e][ds][0] for e in ids], w, color=col, label=ds)
ax.set_xticks(x, [f"{e}\\n{FM_CROSS[e]['name']}" for e in ids], fontsize=8.5); ax.set_ylim(.6, .96)
ax.set_ylabel("ROC-AUC"); ax.legend(ncol=3); ax.grid(axis="x", visible=False)
ax.set_title("Rankings change across datasets"); plt.tight_layout(); plt.show()

rank = fm.set_index("ID")[["VinDr AUC", "INbreast AUC", "LUMINA AUC"]].rank(ascending=False).astype(int)
print("Rank of each configuration per dataset (1 = best):"); rank.T
""")

md("""
**Take-aways from paper 2**
- The biggest single step is replacing global mean pooling with attention MIL (+0.072 AUC, +0.143 AP on VinDr). All MIL and MoLRE variants beat the frozen baseline (DeLong p < 0.001).
- MoLRE adds a further gain at fixed pooling (E2 → E4: +0.033 AUC, p = 0.014). The best internal AUC is **0.878**, and the best INbreast AP is **0.814**.
- More experts or more heads is **not** monotonically better, and the best configuration differs between VinDr, INbreast and LUMINA. LUMINA changes both the domain and the label (pathology rather than BI-RADS), so this is reported as a trade-off rather than one winning model.
""")

md("""
## 3 · Paper 3: five-year cancer risk from routine data (brief)
Developed at Klarity with UK Biobank data. Machine-learning models predict five-year incidence of six common cancers from demographic and clinical variables, as a pre-screening step before invitation. Compared with age-based invitation, the high-risk group is enriched about three-fold. The details stay with the manuscript while it is under review.

## 4 · What I'm working on now
- **Cross-device harmonisation** of mammograms before classification. This follows from the device-level drops found in papers 1 and 2.
- **Device unlearning**, to measure how much vendor-specific information the learned representations retain.
- **H&E → IHC virtual staining** with flow matching. An earlier attempt at lesion synthesis with LoRA-adapted latent-diffusion inpainting did not help downstream performance, which is what motivated the switch.
""")

nb["cells"] = C
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, HERE / "mammography_research_summary.ipynb")
print("written")
