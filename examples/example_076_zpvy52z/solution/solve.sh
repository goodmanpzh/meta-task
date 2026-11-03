#!/bin/bash
set -e

cat > /app/solve_xrf.py << 'PYEOF'
import numpy as np
import pandas as pd
import json
from sklearn.decomposition import NMF
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
from scipy.ndimage import minimum_filter1d, uniform_filter1d

# Load data
data = pd.read_csv('/app/mixed_spectra.csv')
energy = data['energy_keV'].values
spectra = data.drop('energy_keV', axis=1).values.T  # (15 x 1024)

print(f"Loaded {spectra.shape[0]} spectra, {spectra.shape[1]} channels")

# Load XRF reference lines
with open('/app/xrf_reference_lines.json') as f:
    xrf_ref = json.load(f)

# ============================================================
# Step 1: Determine number of components via reconstruction error
# ============================================================
print("\n=== Step 1: Component count determination ===")
errors = {}
for n in range(2, 9):
    nmf = NMF(n_components=n, init='nndsvda', max_iter=2000, random_state=42, tol=1e-4)
    W = nmf.fit_transform(spectra)
    H = nmf.components_
    recon = W @ H
    mse = np.mean((spectra - recon) ** 2)
    errors[n] = mse
    print(f"  n={n}: MSE = {mse:.2f}")

# Find elbow: look at the ratio of consecutive errors
ns = sorted(errors.keys())
errs = [errors[n] for n in ns]

# Compute relative improvements
rel_improvements = []
for i in range(1, len(errs)):
    if errs[i-1] > 0:
        rel_improvements.append((errs[i-1] - errs[i]) / errs[i-1])
    else:
        rel_improvements.append(0)

# Find elbow using second derivative approach
second_diffs = []
for i in range(1, len(rel_improvements)):
    second_diffs.append(rel_improvements[i-1] - rel_improvements[i])

# The elbow corresponds to the largest second difference
best_idx = np.argmax(second_diffs)
n_components = ns[best_idx + 1]

print(f"\nSelected n_components = {n_components}")

with open('/app/n_components.txt', 'w') as f:
    f.write(str(n_components))

# ============================================================
# Step 2: Final NMF decomposition with proper normalization
# ============================================================
print(f"\n=== Step 2: NMF decomposition with {n_components} components ===")

# Run NMF multiple times to find best solution
best_error = float('inf')
best_W = None
best_H = None

for seed in [0, 42, 123, 456, 789, 1000, 2000]:
    nmf = NMF(n_components=n_components, init='nndsvda', max_iter=5000,
              random_state=seed, tol=1e-6)
    W = nmf.fit_transform(spectra)
    H = nmf.components_
    recon = W @ H
    err = np.mean((spectra - recon) ** 2)
    if err < best_error:
        best_error = err
        best_W = W.copy()
        best_H = H.copy()

W = best_W
H = best_H

print(f"Best reconstruction MSE: {best_error:.2f}")

# Proper normalization: normalize each source spectrum (rows of H) to sum to 1,
# then adjust W accordingly so that X = W @ H is preserved.
# After: each column of H_norm sums to 1, and W_adjusted has the scaling.
# Then normalize rows of W_adjusted to sum to 1 for proportions.
H_col_norms = H.sum(axis=1, keepdims=True)  # (n_components, 1)
H_normalized = H / H_col_norms              # source spectra normalized
W_scaled = W * H_col_norms.T                # absorb scaling into W

# Now normalize each row of W_scaled to sum to 1
row_sums = W_scaled.sum(axis=1, keepdims=True)
W_proportions = W_scaled / row_sums

print("\nMixing proportions (first 5 samples):")
for i in range(5):
    props = [f"{v:.4f}" for v in W_proportions[i]]
    print(f"  Sample {i+1}: {props}")

# Save mixing proportions
columns = [f'component_{i+1}' for i in range(n_components)]
index = [f'sample_{i+1:02d}' for i in range(15)]
mixing_df = pd.DataFrame(W_proportions, columns=columns, index=index)
mixing_df.index.name = 'sample'
mixing_df.to_csv('/app/mixing_proportions.csv')
print("Mixing proportions saved.")

# ============================================================
# Step 3: Peak fitting on each recovered source spectrum
# ============================================================
print(f"\n=== Step 3: Peak fitting ===")

def multi_gaussian(x, *params):
    """Sum of Gaussians: params = [c1, a1, s1, c2, a2, s2, ...]"""
    y = np.zeros_like(x)
    n_peaks = len(params) // 3
    for i in range(n_peaks):
        center = params[3*i]
        amplitude = params[3*i + 1]
        sigma = params[3*i + 2]
        y += amplitude * np.exp(-0.5 * ((x - center) / sigma) ** 2)
    return y

def fit_spectrum_peaks(energy, spectrum, min_rel_amplitude=0.05):
    """Find and fit Gaussian peaks in a spectrum."""
    # Subtract a smooth baseline (rolling minimum then smooth)
    baseline = minimum_filter1d(spectrum, size=80)
    baseline = uniform_filter1d(baseline, size=80)
    spectrum_sub = np.maximum(spectrum - baseline, 0)

    max_val = spectrum_sub.max()
    if max_val == 0:
        return []

    channel_width = energy[1] - energy[0]
    min_distance = max(int(0.10 / channel_width), 3)

    peaks, properties = find_peaks(spectrum_sub,
                                    height=max_val * 0.02,
                                    distance=min_distance,
                                    prominence=max_val * 0.015)

    if len(peaks) == 0:
        return []

    # Initial parameter estimates
    p0 = []
    bounds_low = []
    bounds_high = []
    for pk in peaks:
        center = energy[pk]
        amplitude = spectrum_sub[pk]
        # Expected sigma from detector physics
        expected_sigma = 0.055 * np.sqrt(max(center, 1.0) / 5.9)
        p0.extend([center, amplitude, expected_sigma])
        bounds_low.extend([center - 0.12, 0, 0.015])
        bounds_high.extend([center + 0.12, amplitude * 5, 0.15])

    try:
        popt, _ = curve_fit(multi_gaussian, energy, spectrum_sub,
                           p0=p0, bounds=(bounds_low, bounds_high),
                           maxfev=30000)
    except (RuntimeError, ValueError):
        popt = np.array(p0)

    # Extract and filter peaks
    results = []
    n_peaks = len(popt) // 3
    max_amplitude = max(popt[3*i + 1] for i in range(n_peaks))

    for i in range(n_peaks):
        center = popt[3*i]
        amplitude = popt[3*i + 1]
        sigma = popt[3*i + 2]

        if amplitude >= min_rel_amplitude * max_amplitude:
            results.append({
                'center_keV': round(float(center), 4),
                'amplitude': round(float(amplitude), 4),
                'sigma_keV': round(float(sigma), 4)
            })

    return sorted(results, key=lambda x: x['center_keV'])

peak_fits = {}
for i in range(n_components):
    # Use the original (un-normalized) H for peak fitting since it has the
    # actual spectral shape
    source_spectrum = H[i]
    peaks = fit_spectrum_peaks(energy, source_spectrum)
    peak_fits[str(i)] = peaks
    print(f"\nComponent {i}: {len(peaks)} peaks found")
    for p in peaks:
        print(f"  {p['center_keV']:.3f} keV (amp={p['amplitude']:.2f}, sigma={p['sigma_keV']:.4f})")

with open('/app/peak_fits.json', 'w') as f:
    json.dump(peak_fits, f, indent=2)

# ============================================================
# Step 4: Element identification
# ============================================================
print(f"\n=== Step 4: Element identification ===")

def identify_elements(peaks, xrf_ref, tolerance=0.08):
    """Match peak centers to XRF reference lines."""
    elements = set()
    for peak in peaks:
        center = peak['center_keV']
        for ref_line in xrf_ref:
            if abs(center - ref_line['energy_keV']) <= tolerance:
                elements.add(ref_line['element'])
    return sorted(list(elements))

identified = {}
for i in range(n_components):
    peaks = peak_fits[str(i)]
    elements = identify_elements(peaks, xrf_ref)
    identified[str(i)] = elements
    print(f"Component {i} elements: {elements}")

with open('/app/identified_elements.json', 'w') as f:
    json.dump(identified, f, indent=2)

print("\n=== Analysis complete ===")
PYEOF

python /app/solve_xrf.py
