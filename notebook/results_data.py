"""Results transcribed from the manuscripts' tables."""

# --- Paper 1: Cropping + merged view + Finding-BI-RADS prototypes (IEEE Access, under review)
# (VinDr F1, VinDr AUC, INbreast F1, INbreast AUC), binary task, 512 px
IEEE_BINARY_MERGED = {
    "EfficientNet-B3": {"Merged": (0.7671, 0.8158, 0.6577, 0.8705), "M+BF": (0.7812, 0.8268, 0.7531, 0.9087),
                        "Merged 1024px": (0.7980, 0.8664, 0.6623, 0.9117)},
    "ConvNeXt-Base": {"Merged": (0.7889, 0.8569, 0.7107, 0.9100), "M+BF": (0.8009, 0.8615, 0.7584, 0.9170),
                      "Merged 1024px": (0.8104, 0.8853, 0.7197, 0.9291)},
}
IEEE_BINARY_TWOVIEW = {
    "EfficientNet-B3": {"256": (0.6845, 0.7349, 0.6038, 0.8408), "512": (0.7807, 0.8304, 0.6569, 0.9155)},
    "ConvNeXt-Base": {"256": (0.7615, 0.8092, 0.6005, 0.8711), "512": (0.8045, 0.8786, 0.6958, 0.9019)},
}
IEEE_FIVECLASS_MERGED = {
    "EfficientNet-B3": {"Merged": (0.4663, 0.7855, 0.4117, 0.7860), "M+BF": (0.5379, 0.8079, 0.5182, 0.8063)},
    "ConvNeXt-Base": {"Merged": (0.5165, 0.8026, 0.5157, 0.8278), "M+BF": (0.5493, 0.8062, 0.5403, 0.8325)},
}
# (QWK VinDr, MAE VinDr, QWK INbreast, MAE INbreast)
IEEE_ORDINAL = {
    "EfficientNet-B3": {"Merged": (0.601, 0.301, 0.682, 0.587), "M+BF": (0.637, 0.276, 0.694, 0.572)},
    "ConvNeXt-Base": {"Merged": (0.643, 0.275, 0.738, 0.552), "M+BF": (0.665, 0.271, 0.784, 0.497)},
}
# Ablation, ConvNeXt-Base binary macro-F1 (VinDr, INbreast)
IEEE_ABLATION_BIN = [
    ("Single view (CC only)", 0.7706, 0.6507),
    ("Merged, no cropping", 0.7760, 0.6520),
    ("Dual encoder", 0.8045, 0.6958),
    ("Dual encoder, shared weights", 0.7979, 0.7279),
    ("Merged view", 0.7889, 0.7107),
    ("+ finding prototypes", 0.8010, 0.7449),
    ("+ BI-RADS prototypes", 0.7922, 0.6956),
    ("+ both (M+BF, proposed)", 0.8009, 0.7584),
    ("M+BF, MLO masked at test", 0.7355, 0.6430),
]
# Params (M), GFLOPs, latency ms, throughput breasts/s
IEEE_EFFICIENCY = {
    "EfficientNet-B3": {"Two-View": (22.2, 20.1, 26.2, 117.8), "Shared Two-View": (11.5, 20.1, 12.9, 119.6), "Merged": (11.1, 10.0, 12.3, 520.8)},
    "ConvNeXt-Base": {"Two-View": (175.7, 320.9, 24.4, 44.9), "Shared Two-View": (88.1, 320.9, 29.7, 45.4), "Merged": (87.8, 160.4, 9.5, 193.8)},
}
IEEE_CROP_CHECK = {"boxes": 2254, "fully_kept": 2239, "partial": 9, "outside": 6}

# --- Paper 2: MammoRLE-MIL (DINOv2 + routed low-rank experts + multi-head MIL)
# id -> name, dataset -> (AUC, AP)
FM_CROSS = {
    "E1": {"name": "global mean", "VinDr-Mammo": (0.773, 0.427), "INbreast": (0.726, 0.548), "LUMINA": (0.647, 0.645)},
    "E2": {"name": "ABMIL", "VinDr-Mammo": (0.845, 0.571), "INbreast": (0.855, 0.785), "LUMINA": (0.729, 0.751)},
    "E3": {"name": "MH-MIL-2", "VinDr-Mammo": (0.855, 0.580), "INbreast": (0.876, 0.814), "LUMINA": (0.710, 0.736)},
    "E4": {"name": "MoLRE-3+ABMIL", "VinDr-Mammo": (0.878, 0.606), "INbreast": (0.868, 0.803), "LUMINA": (0.709, 0.737)},
    "E5": {"name": "MoLRE-3+MH-2", "VinDr-Mammo": (0.860, 0.582), "INbreast": (0.844, 0.764), "LUMINA": (0.752, 0.769)},
    "E6": {"name": "MoLRE-2+MH-2", "VinDr-Mammo": (0.866, 0.590), "INbreast": (0.865, 0.784), "LUMINA": (0.722, 0.751)},
    "E7": {"name": "MoLRE-4+MH-2", "VinDr-Mammo": (0.846, 0.571), "INbreast": (0.859, 0.796), "LUMINA": (0.748, 0.768)},
    "E8": {"name": "MoLRE-3+MH-3", "VinDr-Mammo": (0.870, 0.608), "INbreast": (0.873, 0.814), "LUMINA": (0.715, 0.743)},
}
