import io
import base64
import math
import numpy as np
import cv2
from PIL import Image

def analyze_luminance_gradients(image: Image.Image) -> dict:
    """
    Analyze luminance gradients and surface lighting consistency.
    Estimates dominant lighting orientation across quadrants to detect
    incompatible lighting conditions in spliced composites.

    Parameters:
        image: PIL Image
    """
    rgb_img = np.array(image.convert("RGB"))
    lab = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2LAB)
    L_channel = lab[:, :, 0].astype(np.float32)
    height, width = L_channel.shape

    # 1. Compute Sobel gradients
    gx = cv2.Sobel(L_channel, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(L_channel, cv2.CV_32F, 0, 1, ksize=3)

    magnitude = np.sqrt(gx**2 + gy**2)
    angle_rad = np.arctan2(gy, gx) # -pi to pi
    angle_deg = (np.degrees(angle_rad) + 360.0) % 360.0

    # Normalize magnitude for visualization
    mag_norm = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    colored_gradient = cv2.applyColorMap(mag_norm, cv2.COLORMAP_HOT)

    # 2. Quadrant-Based Dominant Lighting Direction
    # Divide into 4 quadrants: Top-Left, Top-Right, Bottom-Left, Bottom-Right
    mid_y, mid_x = height // 2, width // 2
    quadrants = {
        "Top-Left": (slice(0, mid_y), slice(0, mid_x)),
        "Top-Right": (slice(0, mid_y), slice(mid_x, width)),
        "Bottom-Left": (slice(mid_y, height), slice(0, mid_x)),
        "Bottom-Right": (slice(mid_y, height), slice(mid_x, width))
    }

    quadrant_directions = {}
    valid_angles = []

    for name, (sy, sx) in quadrants.items():
        q_gx = gx[sy, sx]
        q_gy = gy[sy, sx]
        q_mag = magnitude[sy, sx]

        # Weight angles by gradient magnitude (sharp illumination edges)
        strong_edges = q_mag > np.percentile(q_mag, 85)
        if np.any(strong_edges):
            avg_gx = np.mean(q_gx[strong_edges])
            avg_gy = np.mean(q_gy[strong_edges])
            dom_angle = (math.degrees(math.atan2(avg_gy, avg_gx)) + 360.0) % 360.0
            quadrant_directions[name] = round(dom_angle, 1)
            valid_angles.append(dom_angle)
        else:
            quadrant_directions[name] = 0.0

    # Measure maximum angular difference across quadrants
    max_divergence = 0.0
    for i in range(len(valid_angles)):
        for j in range(i + 1, len(valid_angles)):
            diff = abs(valid_angles[i] - valid_angles[j])
            diff = min(diff, 360.0 - diff)
            if diff > max_divergence:
                max_divergence = diff

    # 3. Overlay Direction Arrows on Gradient Map
    annotated = colored_gradient.copy()
    centers = {
        "Top-Left": (mid_x // 2, mid_y // 2),
        "Top-Right": (mid_x + mid_x // 2, mid_y // 2),
        "Bottom-Left": (mid_x // 2, mid_y + mid_y // 2),
        "Bottom-Right": (mid_x + mid_x // 2, mid_y + mid_y // 2)
    }

    for name, pt in centers.items():
        ang = quadrant_directions.get(name, 0.0)
        rad = math.radians(ang)
        arrow_len = 35
        end_pt = (
            int(pt[0] + arrow_len * math.cos(rad)),
            int(pt[1] + arrow_len * math.sin(rad))
        )
        cv2.arrowedLine(annotated, pt, end_pt, (255, 255, 255), 2, tipLength=0.3)
        cv2.putText(
            annotated, f"{int(ang)}°",
            (pt[0] - 15, pt[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA
        )

    # Measure lateral (Left vs Right) illumination conflict:
    # Conflicting lateral illumination (e.g. Left lit from left, Right lit from right)
    # is a strong indicator of splicing disparate source photos.
    diff_top = abs(quadrant_directions.get("Top-Left", 0) - quadrant_directions.get("Top-Right", 0))
    diff_top = min(diff_top, 360.0 - diff_top)

    diff_bottom = abs(quadrant_directions.get("Bottom-Left", 0) - quadrant_directions.get("Bottom-Right", 0))
    diff_bottom = min(diff_bottom, 360.0 - diff_bottom)

    max_lateral_divergence = max(diff_top, diff_bottom)

    # Base64 encoding
    _, buf = cv2.imencode(".png", annotated)
    grad_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

    # Inconsistent if lateral lighting sources clearly oppose each other (> 125 deg)
    is_inconsistent = max_lateral_divergence > 125.0
    notes = []
    if is_inconsistent:
        notes.append(
            f"Significant lateral illumination vector conflict (delta: {max_lateral_divergence:.1f}°). Scene elements exhibit contradictory directional lighting."
        )
    else:
        notes.append("Directional lighting and luminance gradients are consistent across scene quadrants.")

    return {
        "quadrant_directions": quadrant_directions,
        "max_angular_divergence_deg": round(max_divergence, 1),
        "max_lateral_divergence_deg": round(max_lateral_divergence, 1),
        "is_lighting_inconsistent": is_inconsistent,
        "gradient_image_base64": f"data:image/png;base64,{grad_b64}",
        "notes": notes
    }
