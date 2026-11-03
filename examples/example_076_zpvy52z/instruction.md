hey, picking up from where we left off with the XRF spectral unmixing — so I ran that PCA and the 3-component NMF like you suggested but the residuals still have clear structure, which means we're probably missing at least one source mineral. the script is at `/app/previous_analysis.py` if you want to look at what I tried.

the mixed spectra are in `/app/mixed_spectra.csv` (15 samples, 1024 energy channels from 0.5–15 keV) and I've got the XRF reference line database at `/app/xrf_reference_lines.json` with standard Ka and Kb energies.

what I need you to finish:

1. **figure out the correct number of source components** — try NMF with different numbers of components (say 2 through 8) and use the reconstruction error curve to find the elbow. save the number to `/app/n_components.txt` (just the integer).

2. **run the final NMF decomposition** with the correct number of components. normalize the mixing matrix so each row sums to 1 (i.e., mixing proportions per sample). save the mixing proportions to `/app/mixing_proportions.csv` — should have columns `sample_01` through `sample_15` as rows and `component_1` through `component_N` as columns.

3. **fit Gaussian peaks to each recovered source spectrum** — for each component, find peaks in the NMF-recovered spectrum and fit Gaussians to get center energy, amplitude, and sigma. only keep peaks with amplitude above 5% of the max peak in that component. save results to `/app/peak_fits.json` as a dict keyed by component index (as string), where each value is a list of `{"center_keV": ..., "amplitude": ..., "sigma_keV": ...}` objects.

4. **identify elements** — match fitted peak centers to the XRF reference lines (within 0.08 keV tolerance). for each component, report which elements were detected. save to `/app/identified_elements.json` as a dict keyed by component index (as string), where each value is a sorted list of unique element names.

remember the detector resolution scales with sqrt(energy) so the peak widths should increase for higher energy lines. use that as a sanity check on your fits.

the main trap from last time was that Ba L-alpha (4.466 keV) overlaps with Ti K-alpha (4.511 keV) — they're only ~45 eV apart so the peak fitter might merge them or misassign them. same deal with Mn Ka (5.899 keV) and Cr Kb (5.947 keV). make sure the fitting handles closely-spaced peaks properly.
