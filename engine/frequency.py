import io
import base64
import numpy as np
import cv2
from PIL import Image

def analyze_frequency_domain(image: Image.Image) -> dict:
    """
    Perform 2D Fast Fourier Transform (FFT) analysis.
    Examines the frequency magnitude spectrum to detect periodic interpolation
    artifacts, double compression grids, and high-frequency resharpening spikes.

    Parameters:
        image: PIL Image
    """
    rgb_img = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2GRAY).astype(np.float32)
    height, width = gray.shape

    # 1. Compute 2D Fast Fourier Transform
    dft = np.fft.fft2(gray)
    dft_shift = np.fft.fftshift(dft)

    # 2. Magnitude Spectrum (log scale)
    magnitude = np.abs(dft_shift)
    mag_spectrum = 20 * np.log(magnitude + 1.0)

    # Normalize to 0-255
    norm_spectrum = cv2.normalize(mag_spectrum, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    
    # False-color representation for enhanced visual contrast
    colored_spectrum = cv2.applyColorMap(norm_spectrum, cv2.COLORMAP_VIRIDIS)

    # 3. Frequency Energy Distribution Analysis
    cy, cx = height // 2, width // 2
    y_idx, x_idx = np.ogrid[:height, :width]
    dist_from_center = np.sqrt((x_idx - cx)**2 + (y_idx - cy)**2)
    max_radius = np.sqrt(cx**2 + cy**2)

    # Masks for Low, Mid, and High frequencies
    low_mask = dist_from_center < (max_radius * 0.15)
    mid_mask = (dist_from_center >= (max_radius * 0.15)) & (dist_from_center < (max_radius * 0.50))
    high_mask = dist_from_center >= (max_radius * 0.50)

    total_energy = np.sum(magnitude) + 1e-6
    low_energy_pct = round(float(np.sum(magnitude[low_mask]) / total_energy) * 100.0, 2)
    mid_energy_pct = round(float(np.sum(magnitude[mid_mask]) / total_energy) * 100.0, 2)
    high_energy_pct = round(float(np.sum(magnitude[high_mask]) / total_energy) * 100.0, 2)

    # 4. Periodic Grid & Resampling Artifact Detection
    # Look for isolated sharp harmonic peaks in high frequencies using local maxima dilation
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(norm_spectrum, kernel)
    
    # Mask out central DC component
    dc_mask = np.ones((height, width), dtype=bool)
    cv2.circle(dc_mask.astype(np.uint8), (cx, cy), int(max_radius * 0.18), 0, -1)
    
    # Peak must be a strict local maximum and above energy threshold
    peak_points = (norm_spectrum == dilated) & (norm_spectrum > 175) & dc_mask & high_mask
    peak_y, peak_x = np.nonzero(peak_points)
    
    # Count conjugate symmetric peak pairs: (cx + dx, cy + dy) vs (cx - dx, cy - dy)
    symmetric_pairs = 0
    annotated_spectrum = colored_spectrum.copy()
    
    for py, px in zip(peak_y, peak_x):
        # Mirror coordinates
        mx, my = 2 * cx - px, 2 * cy - py
        if 0 <= my < height and 0 <= mx < width:
            # Check if mirror point is also elevated
            if peak_points[my, mx] or norm_spectrum[my, mx] > 165:
                symmetric_pairs += 1
                cv2.circle(annotated_spectrum, (int(px), int(py)), 4, (0, 0, 255), 1)

    # Symmetric pairs counted twice (once per twin)
    unique_symmetric_peaks = symmetric_pairs // 2

    # Base64 encodings
    _, spec_buf = cv2.imencode(".png", annotated_spectrum)
    spec_b64 = base64.b64encode(spec_buf.tobytes()).decode("utf-8")

    # Assess anomalies (Periodic grids and resampling create regular lattices with many twin peaks)
    has_periodic_artifacts = unique_symmetric_peaks >= 18
    notes = []
    if has_periodic_artifacts:
        notes.append(
            f"Detected {unique_symmetric_peaks} symmetric harmonic peaks in high frequencies, indicating periodic grid resampling, double JPEG compression, or artificial deconvolution."
        )
    else:
        notes.append("Continuous radial frequency decay without abnormal harmonic spikes.")

    return {
        "low_frequency_energy_pct": low_energy_pct,
        "mid_frequency_energy_pct": mid_energy_pct,
        "high_frequency_energy_pct": high_energy_pct,
        "periodic_peaks_detected": unique_symmetric_peaks,
        "has_periodic_artifacts": has_periodic_artifacts,
        "spectrum_image_base64": f"data:image/png;base64,{spec_b64}",
        "notes": notes
    }
