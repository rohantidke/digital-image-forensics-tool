import io
import base64
import math
import numpy as np
import cv2
from scipy.stats import chi2
from PIL import Image

def get_bit_plane(channel_array: np.ndarray, bit_index: int) -> np.ndarray:
    """Extract a specific bit plane (0 to 7) from an 8-bit channel array."""
    # (channel >> bit_index) & 1, scaled to 0 or 255
    plane = ((channel_array >> bit_index) & 1) * 255
    return plane.astype(np.uint8)

def calculate_shannon_entropy(bit_plane_binary: np.ndarray) -> float:
    """Calculate Shannon entropy for a binary bit plane (0s and 1s)."""
    total_pixels = bit_plane_binary.size
    count_ones = np.count_nonzero(bit_plane_binary)
    count_zeros = total_pixels - count_ones

    if count_ones == 0 or count_zeros == 0:
        return 0.0

    p0 = count_zeros / total_pixels
    p1 = count_ones / total_pixels

    entropy = - (p0 * math.log2(p0) + p1 * math.log2(p1))
    return float(entropy)

def chi_square_stego_test(channel_array: np.ndarray) -> dict:
    """
    Perform Chi-Square test and Pair of Values (PoV) symmetry analysis for LSB steganography.
    In unmanipulated images, natural gradients cause noticeable count disparities between 2k and 2k+1.
    In LSB replacement stego, the counts of 2k and 2k+1 equalize dramatically.
    """
    flat = channel_array.flatten()
    counts = np.bincount(flat, minlength=256)

    chi_sq = 0.0
    dof = 0
    total_pair_disparity = 0
    total_valid_pairs = 0

    for k in range(128):
        val_even = int(counts[2 * k])
        val_odd = int(counts[2 * k + 1])
        pair_sum = val_even + val_odd

        if pair_sum > 10:
            expected = pair_sum / 2.0
            diff = abs(val_even - val_odd)
            total_pair_disparity += diff
            total_valid_pairs += pair_sum
            chi_sq += ((val_even - expected)**2 + (val_odd - expected)**2) / expected
            dof += 1

    # Equalization ratio: In stego, disparity ratio approaches 0 (< 0.04)
    disparity_ratio = (total_pair_disparity / max(1, total_valid_pairs))

    # Stego probability estimate
    if dof > 0:
        # Standard Chi-square p-value
        p_val = float(1.0 - chi2.cdf(chi_sq, dof))
        
        # When disparity ratio is extremely low (< 0.035), counts are artificially equalized
        if disparity_ratio < 0.035:
            stego_probability = round(min(100.0, 85.0 + (0.035 - disparity_ratio) * 1000), 2)
        elif p_val > 0.70:
            stego_probability = round(p_val * 100.0, 2)
        else:
            stego_probability = round(max(0.0, (0.12 - disparity_ratio) / 0.12 * 50.0), 2)
    else:
        stego_probability = 0.0
        chi_sq = 0.0

    return {
        "chi_square_stat": round(float(chi_sq), 2),
        "degrees_of_freedom": dof,
        "disparity_ratio": round(float(disparity_ratio), 4),
        "stego_probability_pct": stego_probability
    }

def analyze_stego_lsb(image: Image.Image) -> dict:
    """
    Comprehensive Steganography and Bit-Plane analysis.
    Extracts LSB planes for R, G, B channels, computes bit entropy,
    and conducts Chi-Square PoV testing.

    Parameters:
        image: PIL Image
    """
    rgb_img = np.array(image.convert("RGB"))
    r_chan = rgb_img[:, :, 0]
    g_chan = rgb_img[:, :, 1]
    b_chan = rgb_img[:, :, 2]

    # Extract Bit 0 (LSB) and Bit 7 (MSB) for each channel
    planes = {}
    entropies = {}
    plane_b64 = {}

    channels = {"R": r_chan, "G": g_chan, "B": b_chan}

    for name, chan in channels.items():
        # LSB (bit 0)
        lsb_plane = get_bit_plane(chan, 0)
        lsb_entropy = calculate_shannon_entropy(lsb_plane > 0)
        entropies[f"{name}_LSB_bit0"] = round(lsb_entropy, 4)

        # MSB (bit 7)
        msb_plane = get_bit_plane(chan, 7)
        msb_entropy = calculate_shannon_entropy(msb_plane > 0)
        entropies[f"{name}_MSB_bit7"] = round(msb_entropy, 4)

        # Base64 for LSB & MSB
        _, buf_lsb = cv2.imencode(".png", lsb_plane)
        plane_b64[f"{name}_bit0"] = f"data:image/png;base64,{base64.b64encode(buf_lsb.tobytes()).decode('utf-8')}"

        _, buf_msb = cv2.imencode(".png", msb_plane)
        plane_b64[f"{name}_bit7"] = f"data:image/png;base64,{base64.b64encode(buf_msb.tobytes()).decode('utf-8')}"

    # Perform Chi-Square tests
    chi_r = chi_square_stego_test(r_chan)
    chi_g = chi_square_stego_test(g_chan)
    chi_b = chi_square_stego_test(b_chan)

    max_stego_prob = max(chi_r["stego_probability_pct"], chi_g["stego_probability_pct"], chi_b["stego_probability_pct"])
    avg_stego_prob = round((chi_r["stego_probability_pct"] + chi_g["stego_probability_pct"] + chi_b["stego_probability_pct"]) / 3.0, 2)
    avg_lsb_entropy = round(sum(entropies[f"{c}_LSB_bit0"] for c in ["R", "G", "B"]) / 3.0, 4)
    max_lsb_entropy = max(entropies["R_LSB_bit0"], entropies["G_LSB_bit0"], entropies["B_LSB_bit0"])

    # If any individual channel has high LSB entropy + high stego confidence, flag steganography
    is_stego_detected = max_lsb_entropy > 0.990 and (max_stego_prob > 80.0 or avg_stego_prob > 60.0)
    notes = []
    if is_stego_detected:
        notes.append(
            f"Strong indication of LSB Steganography payload detected (Max LSB Entropy: {max_lsb_entropy:.4f}, Peak Channel Stego Confidence: {max_stego_prob}%)."
        )
    elif max_lsb_entropy > 0.985:
        notes.append("Elevated LSB entropy observed in one or more channels; may contain randomized sensor noise or mild covert data.")
    else:
        notes.append("LSB plane entropy and PoV distributions are consistent with natural unmanipulated imagery.")

    return {
        "avg_lsb_entropy": avg_lsb_entropy,
        "max_lsb_entropy": max_lsb_entropy,
        "entropies": entropies,
        "chi_square_tests": {
            "red": chi_r,
            "green": chi_g,
            "blue": chi_b,
            "average_stego_probability": avg_stego_prob,
            "max_stego_probability": max_stego_prob
        },
        "is_stego_detected": is_stego_detected,
        "bit_planes_preview": plane_b64,
        "notes": notes
    }
