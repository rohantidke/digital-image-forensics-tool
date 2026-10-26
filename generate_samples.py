import io
import os
import zipfile
import numpy as np
import cv2
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")
os.makedirs(SAMPLES_DIR, exist_ok=True)

def create_base_scenic_image(width=640, height=480):
    """Generate a realistic synthetic landscape with sky, mountains, and grass."""
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Sky gradient (blue to light cyan)
    for y in range(int(height * 0.55)):
        ratio = y / (height * 0.55)
        b = int(220 - 40 * ratio)
        g = int(180 + 30 * ratio)
        r = int(120 + 80 * ratio)
        img[y, :] = [b, g, r]

    # Mountains
    mountain_pts = [
        (0, int(height * 0.55)),
        (int(width * 0.2), int(height * 0.35)),
        (int(width * 0.4), int(height * 0.48)),
        (int(width * 0.65), int(height * 0.28)),
        (int(width * 0.85), int(height * 0.45)),
        (width, int(height * 0.55)),
        (width, height),
        (0, height)
    ]
    cv2.fillPoly(img, [np.array(mountain_pts, dtype=np.int32)], (90, 80, 110))

    # Forest / Grass field
    field_pts = [
        (0, int(height * 0.52)),
        (width, int(height * 0.52)),
        (width, height),
        (0, height)
    ]
    cv2.fillPoly(img, [np.array(field_pts, dtype=np.int32)], (45, 120, 60))

    # Add realistic sensor grain / noise
    noise = np.random.normal(0, 4.0, (height, width, 3)).astype(np.float32)
    img_noisy = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return img_noisy

def generate_samples():
    print("[*] Generating digital forensic test samples...")

    # 1. SAMPLE AUTHENTIC
    # Natural image with authentic EXIF data
    base_img = create_base_scenic_image()
    # Add a sun
    cv2.circle(base_img, (120, 100), 30, (180, 240, 255), -1)

    pil_auth = Image.fromarray(cv2.cvtColor(base_img, cv2.COLOR_BGR2RGB))
    
    # Create EXIF dictionary
    exif = pil_auth.getexif()
    exif[0x010F] = "Canon" # Make
    exif[0x0110] = "Canon EOS 5D Mark IV" # Model
    exif[0x0132] = "2026:05:14 11:24:32" # DateTime
    exif[0x0131] = "Digital Photo Professional 4.0" # Clean RAW processor
    
    # Save authentic image
    auth_path = os.path.join(SAMPLES_DIR, "sample_authentic.jpg")
    pil_auth.save(auth_path, "JPEG", quality=92, exif=exif)
    print(f" [+] Created: {auth_path}")

    # 2. SAMPLE COPY-MOVE FORGERY
    # An image with a distinct object duplicated using copy-paste
    cm_img = create_base_scenic_image()
    # Draw a distinct hot air balloon
    def draw_balloon(canvas, cx, cy, scale=1.0):
        r = int(24 * scale)
        # Balloon body
        cv2.circle(canvas, (cx, cy), r, (0, 0, 220), -1)
        cv2.circle(canvas, (cx, cy), int(r * 0.65), (255, 255, 0), -1)
        cv2.circle(canvas, (cx, cy), int(r * 0.3), (0, 255, 255), -1)
        # Basket
        cv2.rectangle(canvas, (cx - 6, cy + r + 8), (cx + 6, cy + r + 18), (20, 60, 120), -1)
        # Ropes
        cv2.line(canvas, (cx - 8, cy + r - 2), (cx - 4, cy + r + 8), (50, 50, 50), 1)
        cv2.line(canvas, (cx + 8, cy + r - 2), (cx + 4, cy + r + 8), (50, 50, 50), 1)

    # Source balloon
    draw_balloon(cm_img, 180, 140, scale=1.0)
    # Target cloned balloon (exact duplicate)
    draw_balloon(cm_img, 460, 160, scale=1.0)

    cm_path = os.path.join(SAMPLES_DIR, "sample_copy_move_forged.jpg")
    cv2.imwrite(cm_path, cm_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f" [+] Created: {cm_path}")

    # 3. SAMPLE SPLICED / TAMPERED WITH PHOTOSHOP METADATA
    # Spliced foreign patch with high noise and photoshop tag
    spliced_img = create_base_scenic_image()
    # Splice an anomalous foreign patch (e.g. mysterious UFO/drone with distinct noise & compression)
    patch = np.zeros((70, 110, 3), dtype=np.uint8)
    cv2.ellipse(patch, (55, 35), (45, 18), 0, 0, 360, (240, 230, 220), -1)
    cv2.circle(patch, (55, 28), 12, (200, 50, 50), -1)
    # Heavy unnatural noise in the spliced patch
    patch_noise = np.random.normal(0, 25.0, patch.shape).astype(np.float32)
    patch = np.clip(patch.astype(np.float32) + patch_noise, 0, 255).astype(np.uint8)

    # Paste into scene
    spliced_img[90:160, 320:430] = patch

    pil_spliced = Image.fromarray(cv2.cvtColor(spliced_img, cv2.COLOR_BGR2RGB))
    exif_spliced = pil_spliced.getexif()
    exif_spliced[0x0131] = "Adobe Photoshop 2024 (Windows)"
    exif_spliced[0x010F] = "Nikon"
    exif_spliced[0x0110] = "NIKON D850"

    spliced_path = os.path.join(SAMPLES_DIR, "sample_spliced_tampered.jpg")
    pil_spliced.save(spliced_path, "JPEG", quality=85, exif=exif_spliced)
    print(f" [+] Created: {spliced_path}")

    # 4. SAMPLE STEGANOGRAPHY (LSB PAYLOAD)
    stego_img = create_base_scenic_image(400, 300)
    # Simulate high-density encrypted steganography payload (e.g. OpenStego / Steghide)
    # In full LSB replacement steganography, the least significant bit is completely randomized
    np.random.seed(1337)
    flat_b = stego_img[:, :, 0].flatten()
    mask = np.uint8(0xFE)
    random_payload = np.random.randint(0, 2, size=len(flat_b), dtype=np.uint8)
    flat_b = (flat_b & mask) | random_payload
    stego_img[:, :, 0] = flat_b.reshape(stego_img[:, :, 0].shape)
    
    stego_path = os.path.join(SAMPLES_DIR, "sample_stego_hidden.png")
    cv2.imwrite(stego_path, stego_img)
    print(f" [+] Created: {stego_path}")

    # 5. SAMPLE EOF CARVED (HIDDEN ZIP IN JPEG)
    eof_base = create_base_scenic_image()
    raw_jpg_buf = cv2.imencode(".jpg", eof_base, [cv2.IMWRITE_JPEG_QUALITY, 90])[1].tobytes()

    # Create an in-memory ZIP archive
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("hidden_confidential_manifest.txt", "CASE FILE #8812: SUSPECT CLASSIFIED ASSETS AND RECOVERY INSTRUCTIONS.")
        zf.writestr("contact_intel.txt", "investigator@cyberforensics.org | ID: 772-AGENT")
    zip_bytes = zip_buf.getvalue()

    # Append ZIP bytes beyond 0xFF 0xD9
    eof_compound_bytes = raw_jpg_buf + zip_bytes
    eof_path = os.path.join(SAMPLES_DIR, "sample_eof_carved.jpg")
    with open(eof_path, "wb") as f:
        f.write(eof_compound_bytes)
    print(f" [+] Created: {eof_path}")

    print("[*] All sample images successfully generated.")

if __name__ == "__main__":
    generate_samples()
