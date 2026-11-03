#!/usr/bin/env python3
"""
Previous analysis attempt - XRF spectral unmixing
Last modified: 2026-03-28

Notes:
- Tried PCA first but negative loadings don't make physical sense for spectra
- Switched to NMF but getting weird results with n_components=3
- The residuals look structured, probably need more components?
- Peak fitting on the raw mixed spectra was a mess - too many overlapping peaks
- Need to unmix FIRST, then do peak fitting on the recovered source spectra

TODO: figure out the right number of components
TODO: once unmixed, fit peaks and identify elements using the reference database
"""
import numpy as np
import pandas as pd
from sklearn.decomposition import NMF, PCA

# Load data
data = pd.read_csv('/app/mixed_spectra.csv')
energy = data['energy_keV'].values
spectra = data.drop('energy_keV', axis=1).values.T  # (15 samples x 1024 channels)

print(f"Loaded {spectra.shape[0]} spectra, {spectra.shape[1]} channels")
print(f"Energy range: {energy[0]:.3f} - {energy[-1]:.3f} keV")

# PCA for initial exploration (not great for spectra but useful for seeing variance)
pca = PCA(n_components=6)
pca.fit(spectra)
print("\nPCA explained variance ratios:")
for i, v in enumerate(pca.explained_variance_ratio_):
    print(f"  PC{i+1}: {v:.4f} ({100*v:.1f}%)")
cumvar = np.cumsum(pca.explained_variance_ratio_)
print(f"\nCumulative variance: {[f'{v:.4f}' for v in cumvar]}")

# First NMF attempt with 3 components (probably wrong)
nmf3 = NMF(n_components=3, init='nndsvd', max_iter=500, random_state=42)
W3 = nmf3.fit_transform(spectra)
H3 = nmf3.components_
recon3 = W3 @ H3
resid3 = np.mean((spectra - recon3)**2)
print(f"\nNMF with 3 components: reconstruction error = {resid3:.2f}")
print("  -> Residuals look structured, probably missing a component")

# TODO: try more components, find the right number
# TODO: unmix, then peak-fit each source spectrum
# TODO: match peaks to XRF reference lines
