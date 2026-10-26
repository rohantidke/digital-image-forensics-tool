import io
import base64
import hashlib
from datetime import datetime
from PIL import Image
import cv2
import numpy as np

from .metadata import extract_metadata
from .ela import perform_ela
from .copy_move import detect_copy_move
from .noise import analyze_noise_inconsistency
from .frequency import analyze_frequency_domain
from .luminance import analyze_luminance_gradients
from .stego_lsb import analyze_stego_lsb
from .carving import carve_file_and_eof
from .scoring import compute_tamper_score
from .report_generator import generate_pdf_report
from .properties import analyze_image_properties, compute_dhash, calculate_similarity_percentage
from .db import save_investigation

class ForensicAnalyzer:
    """
    Central Orchestrator for the VeriPix Digital Image Forensic Suite.
    Executes forensic inspections, computes tampering probability index,
    stores records into persistent SQLite storage, and produces reports.
    """

    def __init__(self, file_bytes: bytes, filename: str = "suspect_image.jpg", investigation_id: str = None):
        self.file_bytes = file_bytes
        self.filename = filename

        # Load image with Pillow
        self.pil_image = Image.open(io.BytesIO(file_bytes))
        
        # Keep an optimized base64 version of the original image for web UI display
        self.original_b64 = self._encode_original_image()

        # Generate unique investigation ID if not provided
        if not investigation_id:
            sha_snip = hashlib.sha256(file_bytes).hexdigest()[:6].upper()
            self.investigation_id = f"INV-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{sha_snip}"
        else:
            self.investigation_id = investigation_id

        # Cached analysis dictionary
        self.results = None

    def _encode_original_image(self) -> str:
        """Encode the original image to base64 for UI rendering."""
        preview_img = self.pil_image.copy()
        # Cap dimensions to max 1600px for web performance if huge
        if max(preview_img.size) > 1600:
            preview_img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        preview_img.convert("RGB").save(buf, format="JPEG", quality=90)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"

    def run_full_analysis(self, ela_quality: int = 95, ela_scale: int = 25, persist: bool = True) -> dict:
        """Run all forensic examination modules and return consolidated results."""
        # 1. Metadata & EXIF
        metadata_res = extract_metadata(self.file_bytes, self.filename)

        # 2. Image Properties, Histograms & Perceptual Hashing
        props_res = analyze_image_properties(self.pil_image, self.file_bytes)

        # 3. Error Level Analysis (ELA)
        ela_res = perform_ela(self.pil_image, quality=ela_quality, scale_factor=ela_scale)

        # 4. Copy-Move Forgery Detection
        copymove_res = detect_copy_move(self.pil_image)

        # 5. Sensor Noise Consistency
        noise_res = analyze_noise_inconsistency(self.pil_image)

        # 6. Frequency Domain (2D FFT)
        freq_res = analyze_frequency_domain(self.pil_image)

        # 7. Luminance Gradient Analysis
        lum_res = analyze_luminance_gradients(self.pil_image)

        # 8. Steganography & Bit-Plane LSB Analysis
        stego_res = analyze_stego_lsb(self.pil_image)

        # 9. File Carving & EOF Payload Inspection
        carving_res = carve_file_and_eof(self.file_bytes, metadata_res.get("format", "JPEG"))

        # 10. Multi-Metric Scoring
        scoring_res = compute_tamper_score(
            metadata_res=metadata_res,
            ela_res=ela_res,
            copymove_res=copymove_res,
            noise_res=noise_res,
            freq_res=freq_res,
            luminance_res=lum_res,
            stego_res=stego_res,
            carving_res=carving_res
        )

        self.results = {
            "investigation_id": self.investigation_id,
            "filename": self.filename,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "original_image_base64": self.original_b64,
            "metadata": metadata_res,
            "properties": props_res,
            "ela": ela_res,
            "copy_move": copymove_res,
            "noise": noise_res,
            "frequency": freq_res,
            "luminance": lum_res,
            "stego": stego_res,
            "carving": carving_res,
            "scoring": scoring_res
        }

        # Persist to SQLite database
        if persist:
            try:
                save_investigation(self.results)
            except Exception as e:
                print(f"[!] Warning: Database persistence encountered an error: {e}")

        return self.results

    def recompute_ela(self, quality: int, scale_factor: int) -> dict:
        """Dynamically recompute only ELA with custom quality/scale settings."""
        return perform_ela(self.pil_image, quality=quality, scale_factor=scale_factor)

    def generate_pdf(self, case_id: str = None, examiner: str = "Digital Forensics Unit") -> bytes:
        """Export official forensic PDF investigation report."""
        if not self.results:
            self.run_full_analysis()
        return generate_pdf_report(self.results, case_id=case_id or self.investigation_id, examiner=examiner)

def compare_two_images(bytes1: bytes, bytes2: bytes, name1: str = "image1", name2: str = "image2") -> dict:
    """
    Compare two images side-by-side:
    - Cryptographic hash comparison (MD5, SHA-256)
    - Perceptual hash similarity (dHash Hamming distance)
    - Pixel-by-pixel difference map
    """
    sha1 = hashlib.sha256(bytes1).hexdigest()
    sha2 = hashlib.sha256(bytes2).hexdigest()
    md5_1 = hashlib.md5(bytes1).hexdigest()
    md5_2 = hashlib.md5(bytes2).hexdigest()
    is_exact_match = (sha1 == sha2)

    img1 = Image.open(io.BytesIO(bytes1)).convert("RGB")
    img2 = Image.open(io.BytesIO(bytes2)).convert("RGB")

    phash1 = compute_dhash(img1)
    phash2 = compute_dhash(img2)
    similarity_pct = calculate_similarity_percentage(phash1, phash2)

    # Compute difference heatmap
    # Resize img2 to match img1 if dimensions differ
    arr1 = np.array(img1)
    arr2 = np.array(img2.resize(img1.size, Image.Resampling.LANCZOS))

    diff = cv2.absdiff(arr1, arr2)
    gray_diff = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)
    norm_diff = cv2.normalize(gray_diff, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    heatmap = cv2.applyColorMap(norm_diff, cv2.COLORMAP_JET)

    # Encode images to base64
    def pil_to_b64(pil_im):
        buf = io.BytesIO()
        pil_im.save(buf, format="JPEG", quality=85)
        return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

    _, heat_buf = cv2.imencode(".jpg", heatmap, [cv2.IMWRITE_JPEG_QUALITY, 85])
    heat_b64 = f"data:image/jpeg;base64,{base64.b64encode(heat_buf.tobytes()).decode('utf-8')}"

    mean_diff = float(np.mean(gray_diff))
    max_diff = float(np.max(gray_diff))

    return {
        "file1": {
            "name": name1,
            "size_bytes": len(bytes1),
            "dimensions": [img1.width, img1.height],
            "sha256": sha1,
            "md5": md5_1,
            "phash": phash1,
            "preview_b64": pil_to_b64(img1)
        },
        "file2": {
            "name": name2,
            "size_bytes": len(bytes2),
            "dimensions": [img2.width, img2.height],
            "sha256": sha2,
            "md5": md5_2,
            "phash": phash2,
            "preview_b64": pil_to_b64(img2)
        },
        "comparison": {
            "is_exact_match": is_exact_match,
            "perceptual_similarity_pct": similarity_pct,
            "mean_pixel_difference": round(mean_diff, 2),
            "max_pixel_difference": round(max_diff, 2),
            "verdict": "Exact Duplicate (Identical File)" if is_exact_match else (
                "Visually Similar / Near-Duplicate" if similarity_pct >= 90.0 else (
                    "Moderately Similar Content" if similarity_pct >= 75.0 else "Distinct / Dissimilar Images"
                )
            ),
            "diff_heatmap_b64": heat_b64
        }
    }
