"""Boundary-aware breast ROI cropping and merged-view composition.

Re-implementation, for illustration, of the preprocessing described in
Mehmood et al., "Intelligent Breast Cropping and Multi-View Fusion with
Finding-BI-RADS Prototype Learning for Mammogram Classification" (under review).

Steps
1. Gaussian smoothing + Otsu threshold  -> foreground mask
2. Morphological closing/opening (5x5)  -> clean contour
3. Largest connected component          -> breast mask
4. Horizontal crop to the mask, with padding on the chest-wall side
5. Row-wise tissue-extent profile: start at the widest row, walk up/down while
   the extent keeps decreasing; stop where it stops decreasing (pectoral muscle,
   skin folds, artefacts); add an adaptive margin.
"""
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class CropResult:
    image: np.ndarray        # cropped image
    mask: np.ndarray         # breast mask (full size)
    otsu: np.ndarray         # raw Otsu mask (full size)
    profile: np.ndarray      # row-wise tissue extent (pixels)
    ref_row: int             # widest row
    box: tuple               # (x0, y0, x1, y1) in original coordinates
    laterality: str          # 'L' (chest wall on the left) or 'R'


def breast_mask(img, blur=5, kernel=5):
    g = cv2.GaussianBlur(img, (blur, blur), 0)
    _, otsu = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel, kernel))
    m = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, k)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return otsu > 0, m > 0
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return otsu > 0, lab == largest


def _walk(profile, start, step, tol):
    """Follow the profile from `start` while the extent keeps decreasing."""
    i = start
    while 0 <= i + step < len(profile):
        nxt = profile[i + step]
        if nxt == 0:                       # left the breast
            return i
        if nxt > profile[i] + tol:         # extent widens again -> other structure
            return i
        i += step
    return i


def crop_breast(img, view="CC", margin_frac=0.03, tol_frac=0.004):
    """Return a CropResult for a single grayscale mammogram (uint8)."""
    h, w = img.shape
    otsu, mask = breast_mask(img)
    cols = np.where(mask.any(0))[0]
    x0, x1 = int(cols.min()), int(cols.max())
    # chest wall is on the side where the mask touches the image border
    laterality = "L" if mask[:, : w // 10].sum() > mask[:, -w // 10:].sum() else "R"

    profile = mask.sum(1).astype(int)
    ref = int(np.argmax(profile))
    tol = max(1, int(tol_frac * w))
    top = _walk(profile, ref, -1, tol)
    bot = _walk(profile, ref, +1, tol)

    # adaptive margin (paper: 50-100 px at full resolution); relaxed for MLO
    m = int(margin_frac * h * (1.6 if view.upper() == "MLO" else 1.0))
    pad = int(0.02 * w)
    y0, y1 = max(0, top - m), min(h, bot + m)
    if laterality == "L":
        x0, x1 = max(0, x0 - pad), min(w, x1 + m)
    else:
        x0, x1 = max(0, x0 - m), min(w, x1 + pad)
    crop = img[y0:y1, x0:x1]
    return CropResult(crop, mask, otsu, profile, ref, (x0, y0, x1, y1), laterality)


def merge_views(cc, mlo, cc_lat, mlo_lat, size=512):
    """Flip so both chest walls meet in the centre, pad to equal height, concat, resize."""
    # CC on the left with chest wall on its right; MLO on the right with chest wall on its left
    if cc_lat == "L":
        cc = cv2.flip(cc, 1)
    if mlo_lat == "R":
        mlo = cv2.flip(mlo, 1)
    hmax = max(cc.shape[0], mlo.shape[0])

    def pad(x):
        d = hmax - x.shape[0]
        return cv2.copyMakeBorder(x, d // 2, d - d // 2, 0, 0, cv2.BORDER_CONSTANT, value=0)

    comp = np.hstack([pad(cc), pad(mlo)])
    return cv2.resize(comp, (size, size), interpolation=cv2.INTER_CUBIC), comp
