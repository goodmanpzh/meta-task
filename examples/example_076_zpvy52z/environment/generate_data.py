#!/usr/bin/env python3
"""
Generate synthetic XRF spectroscopy data for spectral unmixing task.

Creates 4 mineral source spectra with known elemental compositions,
mixes them into 15 composite samples with known proportions,
and adds realistic noise.
"""
import numpy as np
import json
import os

np.random.seed(42)

# Energy axis: 0.5 to 15.0 keV, 1024 channels (~14 eV/channel, typical for SDD)
n_channels = 1024
energy = np.linspace(0.5, 15.0, n_channels)
channel_width = energy[1] - energy[0]  # ~0.01416 keV/channel

# XRF emission line energies (keV) - standard Kα and Kβ lines
# Reference: NIST X-ray transition energies
xrf_lines = {
    'Ca_Ka': 3.692, 'Ca_Kb': 4.013,
    'Ti_Ka': 4.511, 'Ti_Kb': 4.932,
    'Cr_Ka': 5.415, 'Cr_Kb': 5.947,
    'Mn_Ka': 5.899, 'Mn_Kb': 6.490,
    'Fe_Ka': 6.404, 'Fe_Kb': 7.058,
    'Co_Ka': 6.930, 'Co_Kb': 7.649,
    'Ni_Ka': 7.472, 'Ni_Kb': 8.265,
    'Cu_Ka': 8.048, 'Cu_Kb': 8.905,
    'Zn_Ka': 8.639, 'Zn_Kb': 9.572,
    'Sr_Ka': 14.165, 'Sr_Kb': 15.836,
    'Rb_Ka': 13.396, 'Rb_Kb': 14.961,
    'Pb_La': 10.551, 'Pb_Lb': 12.614,
    'Ba_La': 4.466, 'Ba_Lb': 4.828,
}

def gaussian(x, center, amplitude, sigma):
    return amplitude * np.exp(-0.5 * ((x - center) / sigma) ** 2)

def detector_sigma(E_keV):
    """Realistic detector resolution: sigma scales with sqrt(E) for SDD."""
    # Typical SDD: FWHM ~ 130 eV at 5.9 keV (Mn Ka)
    # FWHM = 2.355 * sigma, so sigma ~ 55 eV at 5.9 keV
    # sigma(E) = sigma_0 * sqrt(E / E_ref)
    sigma_ref = 0.055  # keV at E_ref
    E_ref = 5.9  # keV
    return sigma_ref * np.sqrt(E_keV / E_ref)

def make_source_spectrum(element_peaks, base_intensity=50):
    """Create a source spectrum from a list of (line_name, amplitude) tuples."""
    spectrum = np.zeros_like(energy)
    # Add a smooth Bremsstrahlung background (exponential decay)
    spectrum += base_intensity * np.exp(-0.15 * energy)
    for line_name, amplitude in element_peaks:
        center = xrf_lines[line_name]
        sigma = detector_sigma(center)
        spectrum += gaussian(energy, center, amplitude, sigma)
    return spectrum

# Define 4 mineral source spectra
# Source 1: Iron-rich mineral (magnetite-like) with some Ti
source1_peaks = [
    ('Fe_Ka', 8000), ('Fe_Kb', 1600),  # Fe dominant
    ('Ti_Ka', 2000), ('Ti_Kb', 400),    # Ti significant
    ('Mn_Ka', 500), ('Mn_Kb', 100),     # trace Mn
    ('Ca_Ka', 300), ('Ca_Kb', 60),      # trace Ca
]

# Source 2: Copper-Zinc sulfide mineral (chalcopyrite-sphalerite)
source2_peaks = [
    ('Cu_Ka', 7000), ('Cu_Kb', 1400),   # Cu dominant
    ('Zn_Ka', 5000), ('Zn_Kb', 1000),   # Zn significant
    ('Fe_Ka', 1500), ('Fe_Kb', 300),     # some Fe
]

# Source 3: Calcium-rich mineral (calcite/apatite) with Ba and Sr
source3_peaks = [
    ('Ca_Ka', 9000), ('Ca_Kb', 1800),   # Ca dominant
    ('Ba_La', 2500), ('Ba_Lb', 500),     # Ba (L-lines overlap with Ti!)
    ('Sr_Ka', 1200), ('Sr_Kb', 240),     # Sr trace
]

# Source 4: Nickel-Chromium alloy with Co (stainless steel-like)
source4_peaks = [
    ('Ni_Ka', 6000), ('Ni_Kb', 1200),   # Ni dominant
    ('Cr_Ka', 4000), ('Cr_Kb', 800),    # Cr significant
    ('Co_Ka', 1500), ('Co_Kb', 300),     # Co (between Fe_Kb and Ni_Ka - tricky!)
    ('Fe_Ka', 2000), ('Fe_Kb', 400),     # Fe present
]

sources = [
    make_source_spectrum(source1_peaks, base_intensity=40),
    make_source_spectrum(source2_peaks, base_intensity=35),
    make_source_spectrum(source3_peaks, base_intensity=45),
    make_source_spectrum(source4_peaks, base_intensity=30),
]

# Source matrix S: (4 x 1024)
S = np.array(sources)

# Normalize each source to unit max for clean mixing
for i in range(4):
    S[i] = S[i] / S[i].max()

# Mixing proportions matrix A: (15 x 4)
# Design so some components are at low abundance (5-10%) in some samples
# No sample is a pure endmember (that would make NMF too easy)
A = np.array([
    [0.65, 0.15, 0.10, 0.10],  # Sample 1: mostly source 1
    [0.10, 0.60, 0.20, 0.10],  # Sample 2: mostly source 2
    [0.12, 0.08, 0.70, 0.10],  # Sample 3: mostly source 3
    [0.08, 0.12, 0.10, 0.70],  # Sample 4: mostly source 4
    [0.40, 0.35, 0.15, 0.10],  # Sample 5: mix of 1 and 2
    [0.30, 0.10, 0.45, 0.15],  # Sample 6: mix of 1 and 3
    [0.25, 0.15, 0.10, 0.50],  # Sample 7: mix of 1 and 4
    [0.10, 0.40, 0.35, 0.15],  # Sample 8: mix of 2 and 3
    [0.15, 0.45, 0.10, 0.30],  # Sample 9: mix of 2 and 4
    [0.10, 0.10, 0.40, 0.40],  # Sample 10: mix of 3 and 4
    [0.30, 0.30, 0.20, 0.20],  # Sample 11: roughly equal
    [0.25, 0.25, 0.25, 0.25],  # Sample 12: equal mix
    [0.50, 0.20, 0.20, 0.10],  # Sample 13: source 1 heavy
    [0.05, 0.55, 0.05, 0.35],  # Sample 14: sources 2 and 4
    [0.20, 0.05, 0.55, 0.20],  # Sample 15: source 3 heavy
])

# Generate mixed spectra: X = A @ S, then add noise
X_clean = A @ S

# Scale to realistic count levels (thousands of counts at peaks)
scale_factor = 10000
X_clean = X_clean * scale_factor

# Add Poisson noise (counting statistics) + small Gaussian readout noise
X_noisy = np.zeros_like(X_clean)
for i in range(15):
    # Poisson noise (dominant)
    counts = np.maximum(X_clean[i], 0.1)  # avoid zero for Poisson
    X_noisy[i] = np.random.poisson(counts.astype(int)).astype(float)
    # Small Gaussian readout noise
    X_noisy[i] += np.random.normal(0, 5, n_channels)
    # Ensure non-negative (physical constraint)
    X_noisy[i] = np.maximum(X_noisy[i], 0)

# Save the mixed spectra
header_parts = ['energy_keV'] + [f'sample_{i+1:02d}' for i in range(15)]
output = np.column_stack([energy, X_noisy.T])
np.savetxt('/app/mixed_spectra.csv', output, delimiter=',',
           header=','.join(header_parts), comments='')

# Save the XRF reference line database
ref_data = []
for name, e in sorted(xrf_lines.items(), key=lambda x: x[1]):
    element = name.split('_')[0]
    line_type = name.split('_')[1]
    ref_data.append({'element': element, 'line': line_type, 'energy_keV': e})

with open('/app/xrf_reference_lines.json', 'w') as f:
    json.dump(ref_data, f, indent=2)

# Save ground truth for test verification (will be deleted after generation)
ground_truth = {
    'n_components': 4,
    'mixing_proportions': A.tolist(),
    'source_spectra': S.tolist(),
    'source_elements': {
        '0': ['Fe', 'Ti', 'Mn', 'Ca'],  # Source 1
        '1': ['Cu', 'Zn', 'Fe'],         # Source 2
        '2': ['Ca', 'Ba', 'Sr'],          # Source 3
        '3': ['Ni', 'Cr', 'Co', 'Fe'],    # Source 4
    },
    'energy_axis': energy.tolist(),
    'scale_factor': scale_factor,
}

with open('/app/.ground_truth.json', 'w') as f:
    json.dump(ground_truth, f)

print("Data generation complete.")
print(f"  Mixed spectra: /app/mixed_spectra.csv ({X_noisy.shape[0]} samples x {n_channels} channels)")
print(f"  XRF reference: /app/xrf_reference_lines.json ({len(xrf_lines)} lines)")
print(f"  Energy range: {energy[0]:.3f} - {energy[-1]:.3f} keV")
