import io
import base64
import math
import numpy as np
import cv2
from PIL import Image

def detect_copy_move(
    image: Image.Image,
    min_spatial_distance: int = 40,
    min_cluster_size: int = 6,
    max_features: int = 2500
) -> dict:
    """
    Detect Copy-Move (Cloning) Forgery in digital images.
    Uses ORB/AKAZE keypoint extraction, spatial proximity filtering,
    and displacement vector clustering to pinpoint duplicated regions.

    Parameters:
        image: PIL Image
        min_spatial_distance: Minimum Euclidean distance (px) between matched keypoints
                              to ignore local repetitive textures.
        min_cluster_size: Minimum number of parallel vectors required to confirm a clone.
        max_features: Number of features to extract.
    """
    # Convert PIL to BGR OpenCV format
    rgb_img = np.array(image.convert("RGB"))
    bgr_img = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape

    # 1. Feature Detection (ORB with fallback to AKAZE)
    orb = cv2.ORB_create(
        nfeatures=max_features,
        scaleFactor=1.2,
        nlevels=8,
        edgeThreshold=15,
        fastThreshold=12
    )
    keypoints, descriptors = orb.detectAndCompute(gray, None)

    if descriptors is None or len(keypoints) < 30:
        akaze = cv2.AKAZE_create()
        keypoints, descriptors = akaze.detectAndCompute(gray, None)

    total_keypoints = len(keypoints) if keypoints is not None else 0

    if descriptors is None or total_keypoints < 20:
        # Not enough distinct features found (e.g. solid color or blank image)
        _, buf = cv2.imencode(".png", bgr_img)
        b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
        return {
            "forgery_detected": False,
            "total_keypoints": total_keypoints,
            "matched_pairs_count": 0,
            "clone_clusters_count": 0,
            "clusters": [],
            "annotated_image_base64": f"data:image/png;base64,{b64}",
            "notes": ["Insufficient keypoints detected to evaluate copy-move forgery."]
        }

    # 2. Keypoint Matching using Brute Force Matcher
    # Use Hamming distance for binary descriptors
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    # For each descriptor, query 3 nearest neighbors
    # m[0] is self, m[1] is best distinct match, m[2] is 2nd distinct match
    raw_matches = bf.knnMatch(descriptors, descriptors, k=min(4, len(descriptors)))

    candidate_pairs = []
    seen_pairs = set()

    for m in raw_matches:
        if len(m) < 2:
            continue
        # Self match is at index 0 (distance 0)
        # Check m[1]
        best_match = m[1]
        query_idx = best_match.queryIdx
        train_idx = best_match.trainIdx

        if query_idx == train_idx:
            if len(m) >= 3:
                best_match = m[2]
                query_idx = best_match.queryIdx
                train_idx = best_match.trainIdx
            else:
                continue

        pair_key = (min(query_idx, train_idx), max(query_idx, train_idx))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        pt1 = keypoints[query_idx].pt
        pt2 = keypoints[train_idx].pt

        # Spatial Euclidean distance check
        dx = pt2[0] - pt1[0]
        dy = pt2[1] - pt1[1]
        spatial_dist = math.hypot(dx, dy)

        if spatial_dist >= min_spatial_distance:
            # Check descriptor distance threshold
            if best_match.distance < 55:  # Good feature similarity
                # Canonical vector representation
                if pt1[0] > pt2[0] or (pt1[0] == pt2[0] and pt1[1] > pt2[1]):
                    pt_src, pt_dst = pt2, pt1
                    vec_dx, vec_dy = -dx, -dy
                else:
                    pt_src, pt_dst = pt1, pt2
                    vec_dx, vec_dy = dx, dy

                vec_len = math.hypot(vec_dx, vec_dy)
                angle_deg = (math.degrees(math.atan2(vec_dy, vec_dx)) + 360) % 360

                candidate_pairs.append({
                    "src": pt_src,
                    "dst": pt_dst,
                    "dx": vec_dx,
                    "dy": vec_dy,
                    "length": vec_len,
                    "angle": angle_deg,
                    "distance": best_match.distance
                })

    # 3. Vector Clustering (Displacement Consistency)
    # Cloned regions undergo consistent translational displacement
    clusters = []
    angle_bin_size = 15.0  # degrees
    length_bin_size = 35.0 # pixels

    bins = {}
    for pair in candidate_pairs:
        a_bin = int(pair["angle"] / angle_bin_size)
        l_bin = int(pair["length"] / length_bin_size)
        b_key = (a_bin, l_bin)
        if b_key not in bins:
            bins[b_key] = []
        bins[b_key].append(pair)

    # Filter clusters with >= min_cluster_size
    palette = [
        (0, 0, 255),    # Red
        (0, 255, 0),    # Green
        (255, 0, 0),    # Blue
        (0, 255, 255),  # Yellow
        (255, 0, 255),  # Magenta
        (0, 165, 255),  # Orange
        (255, 255, 0)   # Cyan
    ]

    annotated = bgr_img.copy()
    verified_clusters = []
    color_idx = 0

    for b_key, pairs_in_bin in bins.items():
        if len(pairs_in_bin) >= min_cluster_size:
            color = palette[color_idx % len(palette)]
            color_idx += 1

            src_pts = [p["src"] for p in pairs_in_bin]
            dst_pts = [p["dst"] for p in pairs_in_bin]

            avg_len = sum(p["length"] for p in pairs_in_bin) / len(pairs_in_bin)
            avg_angle = sum(p["angle"] for p in pairs_in_bin) / len(pairs_in_bin)

            # Draw arrows and keypoints on canvas
            for p in pairs_in_bin:
                p1 = (int(p["src"][0]), int(p["src"][1]))
                p2 = (int(p["dst"][0]), int(p["dst"][1]))
                cv2.circle(annotated, p1, 4, color, -1)
                cv2.circle(annotated, p2, 4, color, -1)
                cv2.arrowedLine(annotated, p1, p2, color, 1, tipLength=0.04)

            # Draw bounding boxes around source and target clusters
            src_x = [p[0] for p in src_pts]
            src_y = [p[1] for p in src_pts]
            dst_x = [p[0] for p in dst_pts]
            dst_y = [p[1] for p in dst_pts]

            src_box = [int(min(src_x)), int(min(src_y)), int(max(src_x) - min(src_x)), int(max(src_y) - min(src_y))]
            dst_box = [int(min(dst_x)), int(min(dst_y)), int(max(dst_x) - min(dst_x)), int(max(dst_y) - min(dst_y))]

            cv2.rectangle(
                annotated,
                (src_box[0], src_box[1]),
                (src_box[0] + src_box[2], src_box[1] + src_box[3]),
                color, 2
            )
            cv2.rectangle(
                annotated,
                (dst_box[0], dst_box[1]),
                (dst_box[0] + dst_box[2], dst_box[1] + dst_box[3]),
                color, 2
            )

            verified_clusters.append({
                "cluster_id": len(verified_clusters) + 1,
                "matches_count": len(pairs_in_bin),
                "avg_displacement_px": round(avg_len, 1),
                "angle_degrees": round(avg_angle, 1),
                "source_box": src_box,
                "clone_box": dst_box
            })

    # Encode annotated image to base64
    _, buf = cv2.imencode(".png", annotated)
    annotated_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

    is_forged = len(verified_clusters) > 0
    notes = []
    if is_forged:
        notes.append(
            f"Detected {len(verified_clusters)} distinct copy-move clone cluster(s) with aligned translation vectors."
        )
    else:
        notes.append("No consistent spatial duplication vectors detected across keypoints.")

    return {
        "forgery_detected": is_forged,
        "total_keypoints": total_keypoints,
        "matched_pairs_count": len(candidate_pairs),
        "clone_clusters_count": len(verified_clusters),
        "clusters": verified_clusters,
        "annotated_image_base64": f"data:image/png;base64,{annotated_b64}",
        "notes": notes
    }
