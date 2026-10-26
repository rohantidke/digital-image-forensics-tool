import io
import base64
import numpy as np
import cv2
from PIL import Image

def analyze_noise_inconsistency(image: Image.Image, block_size: int = 16) -> dict:
    """
    Analyze image sensor noise consistency.
    Extracts the high-frequency residual noise and evaluates local variance across
    blocks to detect spliced regions with mismatched noise profiles.

    Parameters:
        image: PIL Image
        block_size: Window size (px) for calculating localized variance
    """
    rgb_img = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2GRAY).astype(np.float32)
    height, width = gray.shape

    # 1. Noise Residual Extraction via Median Filter Subtraction
    # Median filter suppresses noise while preserving edges
    median = cv2.medianBlur(gray.astype(np.uint8), 3).astype(np.float32)
    noise_residual = np.abs(gray - median)

    # Normalize noise residual for visualization
    res_norm = cv2.normalize(noise_residual, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

    # 2. Local Variance Computation across Blocks
    num_blocks_y = height // block_size
    num_blocks_x = width // block_size

    if num_blocks_x == 0 or num_blocks_y == 0:
        num_blocks_x = max(1, num_blocks_x)
        num_blocks_y = max(1, num_blocks_y)
        block_size = min(height, width)

    var_grid = np.zeros((num_blocks_y, num_blocks_x), dtype=np.float32)

    for by in range(num_blocks_y):
        for bx in range(num_blocks_x):
            y_start = by * block_size
            x_start = bx * block_size
            block = noise_residual[y_start:y_start + block_size, x_start:x_start + block_size]
            var_grid[by, bx] = float(np.var(block))

    mean_var = float(np.mean(var_grid))
    std_var = float(np.std(var_grid))
    cv_var = float(std_var / (mean_var + 1e-6)) # Coefficient of variation

    # Resize variance grid back to image size for heatmap display
    var_resized = cv2.resize(var_grid, (width, height), interpolation=cv2.INTER_CUBIC)
    var_norm = cv2.normalize(var_resized, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    var_heatmap = cv2.applyColorMap(var_norm, cv2.COLORMAP_INFERNO)

    # Anomaly Detection: Detect blocks with abnormal noise variance
    # Both hyper-noisy (spliced from grainy image) and hypo-noisy (smoothed/inpainted)
    upper_threshold = mean_var + (2.5 * std_var)
    lower_threshold = max(0.0, mean_var - (2.0 * std_var))

    abnormal_high_blocks = int(np.sum(var_grid > upper_threshold))
    abnormal_low_blocks = int(np.sum(var_grid < lower_threshold))
    total_blocks = num_blocks_y * num_blocks_x
    abnormal_percentage = round(((abnormal_high_blocks + abnormal_low_blocks) / total_blocks) * 100.0, 2)

    # Base64 encodings
    _, res_buf = cv2.imencode(".png", res_norm)
    res_b64 = base64.b64encode(res_buf.tobytes()).decode("utf-8")

    _, heat_buf = cv2.imencode(".png", var_heatmap)
    heat_b64 = base64.b64encode(heat_buf.tobytes()).decode("utf-8")

    is_suspicious = cv_var > 0.85 or abnormal_percentage > 4.5
    notes = []
    if is_suspicious:
        notes.append(
            f"High noise variance disparity (CV = {cv_var:.2f}). {abnormal_percentage}% of spatial blocks exhibit anomalous sensor noise levels."
        )
    else:
        notes.append("Sensor noise distribution appears uniform and homogeneous across the canvas.")

    return {
        "mean_noise_variance": round(mean_var, 2),
        "variance_std": round(std_var, 2),
        "coefficient_of_variation": round(cv_var, 3),
        "abnormal_block_percentage": abnormal_percentage,
        "is_noise_inconsistent": is_suspicious,
        "noise_residual_base64": f"data:image/png;base64,{res_b64}",
        "noise_heatmap_base64": f"data:image/png;base64,{heat_b64}",
        "notes": notes
    }
