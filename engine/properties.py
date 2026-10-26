import io
import base64
import numpy as np
import cv2
from PIL import Image

def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
    """
    Compute difference perceptual hash (dHash).
    Resizes image to (hash_size + 1, hash_size), converts to grayscale,
    and compares adjacent pixels. Robust to scaling and minor compression.
    """
    try:
        gray = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = np.array(gray)
        # Compute difference between adjacent horizontal pixels
        diff = pixels[:, 1:] > pixels[:, :-1]
        # Convert boolean array to 64-bit hex string
        decimal_val = 0
        hex_str = []
        for index, value in enumerate(diff.flatten()):
            if value:
                decimal_val += 2 ** (index % 8)
            if (index % 8) == 7:
                hex_str.append(hex(decimal_val)[2:].rjust(2, "0"))
                decimal_val = 0
        return "".join(hex_str)
    except Exception:
        return "0000000000000000"

def hamming_distance(hash1_hex: str, hash2_hex: str) -> int:
    """Calculate the Hamming distance between two hex hashes."""
    try:
        val1 = int(hash1_hex, 16)
        val2 = int(hash2_hex, 16)
        xor_val = val1 ^ val2
        return bin(xor_val).count("1")
    except Exception:
        return 64

def calculate_similarity_percentage(hash1_hex: str, hash2_hex: str, total_bits: int = 64) -> float:
    """Calculate perceptual similarity percentage based on Hamming distance."""
    dist = hamming_distance(hash1_hex, hash2_hex)
    similarity = max(0.0, 100.0 - (dist / total_bits) * 100.0)
    return round(similarity, 2)

def extract_color_histograms(image: Image.Image) -> dict:
    """
    Compute 256-bin histograms for Red, Green, Blue, and Luminance channels.
    Normalized to 0 - 100% for clean charting.
    """
    rgb_arr = np.array(image.convert("RGB"))
    r_chan = rgb_arr[:, :, 0]
    g_chan = rgb_arr[:, :, 1]
    b_chan = rgb_arr[:, :, 2]
    
    # Luminance channel via standard Rec.601 formula
    lum = (0.299 * r_chan + 0.587 * g_chan + 0.114 * b_chan).astype(np.uint8)

    r_hist, _ = np.histogram(r_chan, bins=256, range=(0, 256))
    g_hist, _ = np.histogram(g_chan, bins=256, range=(0, 256))
    b_hist, _ = np.histogram(b_chan, bins=256, range=(0, 256))
    l_hist, _ = np.histogram(lum, bins=256, range=(0, 256))

    # Downsample to 64 bins for fast responsive rendering on frontend
    def downsample_hist(hist, target_bins=64):
        factor = len(hist) // target_bins
        downsampled = [int(np.sum(hist[i*factor:(i+1)*factor])) for i in range(target_bins)]
        max_val = max(downsampled) if max(downsampled) > 0 else 1
        return [round((v / max_val) * 100.0, 1) for v in downsampled]

    return {
        "red": downsample_hist(r_hist),
        "green": downsample_hist(g_hist),
        "blue": downsample_hist(b_hist),
        "luminance": downsample_hist(l_hist)
    }

def generate_channel_views(image: Image.Image) -> dict:
    """
    Generate isolated single-channel representations (Red, Green, Blue, and Grayscale)
    for detailed visual inspection.
    """
    rgb_arr = np.array(image.convert("RGB"))
    height, width, _ = rgb_arr.shape

    # Red only
    r_isolated = np.zeros_like(rgb_arr)
    r_isolated[:, :, 0] = rgb_arr[:, :, 0]

    # Green only
    g_isolated = np.zeros_like(rgb_arr)
    g_isolated[:, :, 1] = rgb_arr[:, :, 1]

    # Blue only
    b_isolated = np.zeros_like(rgb_arr)
    b_isolated[:, :, 2] = rgb_arr[:, :, 2]

    # Grayscale
    gray = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2GRAY)

    def encode_np(arr, is_gray=False):
        if is_gray:
            _, buf = cv2.imencode(".jpg", arr, [cv2.IMWRITE_JPEG_QUALITY, 85])
        else:
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            _, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return f"data:image/jpeg;base64,{base64.b64encode(buf.tobytes()).decode('utf-8')}"

    return {
        "red_channel_b64": encode_np(r_isolated),
        "green_channel_b64": encode_np(g_isolated),
        "blue_channel_b64": encode_np(b_isolated),
        "grayscale_b64": encode_np(gray, is_gray=True)
    }

def analyze_image_properties(image: Image.Image, file_bytes: bytes) -> dict:
    """Comprehensive image properties analysis."""
    width, height = image.size
    aspect_ratio = round(width / max(1, height), 2)
    megapixels = round((width * height) / 1_000_000.0, 2)
    phash_str = compute_dhash(image)
    histograms = extract_color_histograms(image)
    channel_views = generate_channel_views(image)

    return {
        "dimensions": [width, height],
        "aspect_ratio": f"{aspect_ratio}:1 ({width}:{height})",
        "megapixels": megapixels,
        "color_mode": image.mode,
        "perceptual_hash": phash_str,
        "histograms": histograms,
        "channel_views": channel_views,
        "raw_size_bytes": len(file_bytes)
    }
