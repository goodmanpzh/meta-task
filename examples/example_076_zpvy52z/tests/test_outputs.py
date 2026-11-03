"""
Test suite for XRF spectral unmixing task.
Verifies: component count, mixing proportions, peak fitting, element identification.
"""
import json
import os
import numpy as np
import pandas as pd
import pytest


# ============================================================
# Helper functions
# ============================================================

def load_spectra():
    """Load mixed spectra data."""
    data = pd.read_csv('/app/mixed_spectra.csv')
    energy = data['energy_keV'].values
    spectra = data.drop('energy_keV', axis=1).values.T
    return energy, spectra

def load_xrf_ref():
    """Load XRF reference lines."""
    with open('/app/xrf_reference_lines.json') as f:
        return json.load(f)


# ============================================================
# Test 1: Number of components
# ============================================================

class TestComponentCount:
    def test_n_components_file_exists(self):
        """n_components.txt must exist."""
        assert os.path.exists('/app/n_components.txt'), \
            "Missing /app/n_components.txt"

    def test_n_components_is_integer(self):
        """n_components.txt must contain a valid integer."""
        with open('/app/n_components.txt') as f:
            content = f.read().strip()
        n = int(content)
        assert 2 <= n <= 10, f"n_components={n} is not in reasonable range [2,10]"

    def test_n_components_correct(self):
        """The correct number of source components is 4."""
        with open('/app/n_components.txt') as f:
            n = int(f.read().strip())
        assert n == 4, f"Expected 4 components, got {n}"


# ============================================================
# Test 2: Mixing proportions
# ============================================================

class TestMixingProportions:
    def test_mixing_file_exists(self):
        """mixing_proportions.csv must exist."""
        assert os.path.exists('/app/mixing_proportions.csv'), \
            "Missing /app/mixing_proportions.csv"

    def test_mixing_shape(self):
        """Mixing matrix must be 15 samples x N components."""
        df = pd.read_csv('/app/mixing_proportions.csv', index_col=0)
        assert df.shape[0] == 15, f"Expected 15 rows, got {df.shape[0]}"
        with open('/app/n_components.txt') as f:
            n = int(f.read().strip())
        assert df.shape[1] == n, f"Expected {n} columns, got {df.shape[1]}"

    def test_mixing_non_negative(self):
        """All mixing proportions must be non-negative."""
        df = pd.read_csv('/app/mixing_proportions.csv', index_col=0)
        assert (df.values >= -1e-6).all(), \
            "Mixing proportions contain negative values"

    def test_mixing_rows_sum_to_one(self):
        """Each row must sum to approximately 1.0."""
        df = pd.read_csv('/app/mixing_proportions.csv', index_col=0)
        row_sums = df.values.sum(axis=1)
        np.testing.assert_allclose(row_sums, 1.0, atol=0.02,
            err_msg="Row sums deviate from 1.0")

    def test_mixing_reconstruction_quality(self):
        """
        The mixing proportions should allow good reconstruction of the
        original spectra via least-squares recovery of source spectra.
        """
        energy, spectra = load_spectra()
        df = pd.read_csv('/app/mixing_proportions.csv', index_col=0)
        W = df.values

        # Recover H from X = W @ H using least squares
        H_recovered = np.linalg.lstsq(W, spectra, rcond=None)[0]
        reconstruction = W @ H_recovered

        # Compute normalized reconstruction error
        # Use mean relative error instead of R-squared
        total_energy = np.sum(spectra ** 2)
        residual_energy = np.sum((spectra - reconstruction) ** 2)
        norm_error = residual_energy / total_energy

        assert norm_error < 0.10, \
            f"Normalized reconstruction error = {norm_error:.4f}, expected < 0.10"

    def test_mixing_dominant_components(self):
        """
        Samples 1-4 should each be dominated by a different component.
        The first 4 samples were designed with one dominant source (0.65-0.70).
        """
        df = pd.read_csv('/app/mixing_proportions.csv', index_col=0)
        W = df.values

        dominant_components = []
        for i in range(4):
            dom = np.argmax(W[i])
            dominant_components.append(dom)
            assert W[i, dom] > 0.3, \
                f"Sample {i+1}: dominant proportion {W[i,dom]:.3f} < 0.3"

        # All 4 dominant components should be different
        assert len(set(dominant_components)) == 4, \
            f"First 4 samples should have 4 different dominant components, got {dominant_components}"

    def test_mixing_variability(self):
        """
        The mixing proportions should show meaningful variation across samples.
        Each component should be the dominant one in at least one sample.
        """
        df = pd.read_csv('/app/mixing_proportions.csv', index_col=0)
        W = df.values

        dominant_per_sample = np.argmax(W, axis=1)
        unique_dominant = set(dominant_per_sample)

        with open('/app/n_components.txt') as f:
            n = int(f.read().strip())

        assert len(unique_dominant) == n, \
            f"Expected each of {n} components to dominate at least one sample, " \
            f"but only {len(unique_dominant)} are dominant: {unique_dominant}"


# ============================================================
# Test 3: Peak fitting
# ============================================================

class TestPeakFitting:
    def test_peak_fits_file_exists(self):
        """peak_fits.json must exist."""
        assert os.path.exists('/app/peak_fits.json'), \
            "Missing /app/peak_fits.json"

    def test_peak_fits_structure(self):
        """peak_fits.json must have correct structure."""
        with open('/app/peak_fits.json') as f:
            peaks = json.load(f)

        with open('/app/n_components.txt') as f:
            n = int(f.read().strip())

        assert isinstance(peaks, dict), "peak_fits.json must be a dict"
        assert len(peaks) == n, f"Expected {n} components, got {len(peaks)}"

        for key, peak_list in peaks.items():
            assert isinstance(peak_list, list), f"Component {key} must be a list"
            for p in peak_list:
                assert 'center_keV' in p, f"Missing 'center_keV' in component {key}"
                assert 'amplitude' in p, f"Missing 'amplitude' in component {key}"
                assert 'sigma_keV' in p, f"Missing 'sigma_keV' in component {key}"

    def test_peak_positions_physical(self):
        """All peak positions must be within the energy range."""
        with open('/app/peak_fits.json') as f:
            peaks = json.load(f)

        for key, peak_list in peaks.items():
            for p in peak_list:
                assert 0.5 <= p['center_keV'] <= 15.0, \
                    f"Component {key}: peak at {p['center_keV']} keV outside range"
                assert p['amplitude'] > 0, \
                    f"Component {key}: negative amplitude at {p['center_keV']} keV"
                assert 0.01 <= p['sigma_keV'] <= 0.3, \
                    f"Component {key}: sigma {p['sigma_keV']} keV unrealistic"

    def test_peak_widths_scale_with_energy(self):
        """
        Detector physics: peak sigma should generally increase with energy.
        Check that the mean sigma of peaks above 7 keV is larger than
        the mean sigma of peaks below 7 keV.
        """
        with open('/app/peak_fits.json') as f:
            peaks = json.load(f)

        sigmas_low = []
        sigmas_high = []
        for key, peak_list in peaks.items():
            for p in peak_list:
                if p['center_keV'] < 7.0:
                    sigmas_low.append(p['sigma_keV'])
                else:
                    sigmas_high.append(p['sigma_keV'])

        if len(sigmas_low) > 0 and len(sigmas_high) > 0:
            mean_low = np.mean(sigmas_low)
            mean_high = np.mean(sigmas_high)
            assert mean_high >= mean_low, \
                f"Peak widths should increase with energy: mean_low={mean_low:.4f}, mean_high={mean_high:.4f}"

    def test_sufficient_peaks_per_component(self):
        """Each component should have at least 2 peaks (Ka + Kb at minimum)."""
        with open('/app/peak_fits.json') as f:
            peaks = json.load(f)

        for key, peak_list in peaks.items():
            assert len(peak_list) >= 2, \
                f"Component {key}: only {len(peak_list)} peaks, expected >= 2"

    def test_peaks_near_known_xrf_lines(self):
        """
        At least 70% of fitted peaks should be within 0.1 keV of a known
        XRF emission line.
        """
        with open('/app/peak_fits.json') as f:
            peaks = json.load(f)

        xrf_ref = load_xrf_ref()
        ref_energies = [r['energy_keV'] for r in xrf_ref]

        total_peaks = 0
        matched_peaks = 0
        for key, peak_list in peaks.items():
            for p in peak_list:
                total_peaks += 1
                center = p['center_keV']
                min_dist = min(abs(center - e) for e in ref_energies)
                if min_dist <= 0.10:
                    matched_peaks += 1

        match_ratio = matched_peaks / total_peaks if total_peaks > 0 else 0
        assert match_ratio >= 0.70, \
            f"Only {matched_peaks}/{total_peaks} ({match_ratio:.1%}) peaks near known XRF lines"


# ============================================================
# Test 4: Element identification
# ============================================================

class TestElementIdentification:
    def test_elements_file_exists(self):
        """identified_elements.json must exist."""
        assert os.path.exists('/app/identified_elements.json'), \
            "Missing /app/identified_elements.json"

    def test_elements_structure(self):
        """identified_elements.json must be a dict of sorted string lists."""
        with open('/app/identified_elements.json') as f:
            elements = json.load(f)

        with open('/app/n_components.txt') as f:
            n = int(f.read().strip())

        assert isinstance(elements, dict), "Must be a dict"
        assert len(elements) == n, f"Expected {n} components, got {len(elements)}"

        for key, elem_list in elements.items():
            assert isinstance(elem_list, list), f"Component {key} must be a list"
            assert all(isinstance(e, str) for e in elem_list), \
                f"Component {key} must contain strings"
            assert elem_list == sorted(elem_list), \
                f"Component {key} elements must be sorted"

    def test_all_major_elements_found(self):
        """
        The 4 sources contain these MAJOR elements (highest amplitude peaks):
        Fe, Cu, Ca, and Ni must each be identified in at least one component.
        """
        with open('/app/identified_elements.json') as f:
            elements = json.load(f)

        all_elements = set()
        for key, elem_list in elements.items():
            all_elements.update(elem_list)

        required_major = {'Fe', 'Cu', 'Ca', 'Ni'}
        missing = required_major - all_elements
        assert len(missing) == 0, \
            f"Major elements not found in any component: {missing}"

    def test_element_separation_quality(self):
        """
        The NMF decomposition should separate sources well enough that
        the peak fitting reveals distinct elemental signatures per component.
        Use peak amplitudes to determine which component has the strongest
        signal for each characteristic element, and verify they map to
        different components.
        """
        with open('/app/identified_elements.json') as f:
            elements = json.load(f)
        with open('/app/peak_fits.json') as f:
            peaks = json.load(f)

        xrf_ref = load_xrf_ref()

        # For each major element, find which component has the highest-amplitude
        # peak near its Ka line
        ka_lines = {
            'Fe': 6.404, 'Cu': 8.048, 'Ca': 3.692, 'Ni': 7.472
        }

        best_component = {}
        for elem, ka_energy in ka_lines.items():
            best_amp = 0
            best_comp = None
            for comp_key, peak_list in peaks.items():
                for p in peak_list:
                    if abs(p['center_keV'] - ka_energy) <= 0.10:
                        if p['amplitude'] > best_amp:
                            best_amp = p['amplitude']
                            best_comp = comp_key

            if best_comp is not None:
                best_component[elem] = best_comp

        # At least 3 of the 4 major elements should map to different components
        if len(best_component) >= 3:
            unique_comps = set(best_component.values())
            assert len(unique_comps) >= 3, \
                f"Expected >= 3 different components for major elements, " \
                f"got mapping: {best_component}"

    def test_secondary_elements_present(self):
        """
        Beyond the 4 dominant elements, important secondary elements should
        be identified: Ti (in Fe source), Zn (in Cu source), Cr (in Ni source).
        At least 2 of these 3 should appear somewhere.
        """
        with open('/app/identified_elements.json') as f:
            elements = json.load(f)

        all_elements = set()
        for key, elem_list in elements.items():
            all_elements.update(elem_list)

        secondary = {'Ti', 'Zn', 'Cr'}
        found = secondary & all_elements
        assert len(found) >= 2, \
            f"Expected at least 2 of {secondary} to be identified, found {found}"

    def test_no_phantom_elements(self):
        """
        Elements not present in ANY source should not be identified.
        The sources don't contain Rb or Pb, so these should not appear.
        """
        with open('/app/identified_elements.json') as f:
            elements = json.load(f)

        all_elements = set()
        for key, elem_list in elements.items():
            all_elements.update(elem_list)

        phantom = {'Rb', 'Pb'}
        found_phantom = phantom & all_elements
        assert len(found_phantom) == 0, \
            f"Phantom elements incorrectly identified: {found_phantom}"
