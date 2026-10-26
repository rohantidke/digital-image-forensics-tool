import io
import base64
import numpy as np
import cv2
from PIL import Image, ImageChops, ImageEnhance

def perform_ela(image: Image.Image, quality: int = 95, scale_factor: int = 25) -> dict:
    """
    Perform Error Level Analysis (ELA).
    Identifies areas with different compression levels by resaving the image
    at a known JPEG quality and measuring the difference.

    Parameters:
        image: PIL Image object
        quality: JPEG compression quality (typically 90-95)
        scale_factor: Multiplier to amplify differences for human visual perception

    Returns:
        dict containing base64 images (amplified ELA and thermal heatmap) and statistics.
    """
    # Ensure RGB
    orig_rgb = image.convert("RGB")
    width, height = orig_rgb.size

    # Save to buffer at specified quality
    buffer = io.BytesIO()
    orig_rgb.save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    recompressed = Image.open(buffer)

    # Compute pixel-by-pixel difference
    diff = ImageChops.difference(orig_rgb, recompressed)

    # Calculate statistics from the raw difference
    diff_np = np.array(diff, dtype=np.float32)
    gray_diff = cv2.cvtColor(diff_np.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    
    mean_val = float(np.mean(gray_diff))
    max_val = float(np.max(gray_diff))
    std_val = float(np.std(gray_diff))

    # Determine automatic or manual scale
    extrema = diff.getextrema()
    max_chan_diff = max([ex[1] for ex in extrema])
    if max_chan_diff == 0:
        max_chan_diff = 1

    actual_scale = scale_factor
    if actual_scale <= 0:
        actual_scale = int(255.0 / max_chan_diff)

    # Create amplified ELA visual
    enhancer = ImageEnhance.Brightness(diff)
    ela_amplified = enhancer.enhance(actual_scale)

    # Create Thermal / Colormap heatmap
    norm_diff = cv2.normalize(gray_diff, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    heatmap = cv2.applyColorMap(norm_diff, cv2.COLORMAP_JET)

    # High-error anomaly masking
    # Pixels with error significantly above baseline indicate spliced or altered regions
    threshold_val = mean_val + (2.5 * std_val)
    _, anomaly_mask = cv2.threshold(gray_diff, max(threshold_val, 12), 255, cv2.THRESH_BINARY)
    anomaly_pixels = int(np.count_nonzero(anomaly_mask))
    anomaly_percentage = round((anomaly_pixels / (width * height)) * 100.0, 2)

    # Find bounding boxes of suspicious hot spots
    contours, _ = cv2.findContours(anomaly_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    suspicious_regions = []
    min_area = (width * height) * 0.002 # At least 0.2% of image
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > min_area:
            x, y, w, h = cv2.boundingRect(cnt)
            suspicious_regions.append({
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
                "area_px": int(area)
            })

    # Encode ELA amplified image to base64
    ela_buf = io.BytesIO()
    ela_amplified.save(ela_buf, format="PNG")
    ela_b64 = base64.b64encode(ela_buf.getvalue()).decode("utf-8")

    # Encode Heatmap to base64
    _, heat_buf = cv2.imencode(".png", heatmap)
    heat_b64 = base64.b64encode(heat_buf.tobytes()).decode("utf-8")

    # Assess tampering likelihood from ELA
    # If standard deviation is high and localized clusters exist
    has_tamper_signature = False
    notes = []
    if len(suspicious_regions) > 0 and anomaly_percentage > 0.5:
        has_tamper_signature = True
        notes.append(
            f"Detected {len(suspicious_regions)} localized region(s) with anomalous compression error levels ({anomaly_percentage}% of total area)."
        )
    elif max_val > 40 and std_val > 8:
        notes.append("High overall compression divergence across the canvas.")
    else:
        notes.append("Compression error levels appear uniform across the entire image.")

    return {
        "quality": quality,
        "scale_factor": actual_scale,
        "mean_error": round(mean_val, 2),
        "max_error": round(max_val, 2),
        "std_deviation": round(std_val, 2),
        "anomaly_percentage": anomaly_percentage,
        "suspicious_region_count": len(suspicious_regions),
        "suspicious_regions": suspicious_regions[:10],
        "has_tamper_signature": has_tamper_signature,
        "notes": notes,
        "ela_image_base64": f"data:image/png;base64,{ela_b64}",
        "heatmap_image_base64": f"data:image/png;base64,{heat_b64}"
    }
