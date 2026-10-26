import hashlib
import io
import base64
from datetime import datetime
from PIL import Image, ExifTags

SUSPICIOUS_SOFTWARE_KEYWORDS = [
    "photoshop", "gimp", "canva", "lightroom", "paint.net", "photopea",
    "snapseed", "picsart", "pixlr", "affinity", "camera raw", "coreldraw",
    "procreate", "facetune", "afterlight", "vsco"
]

def calculate_hashes(file_bytes: bytes) -> dict:
    """Calculate cryptographic hashes for chain-of-custody verification."""
    return {
        "md5": hashlib.md5(file_bytes).hexdigest(),
        "sha1": hashlib.sha1(file_bytes).hexdigest(),
        "sha256": hashlib.sha256(file_bytes).hexdigest()
    }

def _convert_gps_to_degrees(value):
    """Helper to convert GPS rational coordinates to decimal degrees."""
    try:
        if isinstance(value, (tuple, list)) and len(value) == 3:
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
        return float(value)
    except Exception:
        return None

def extract_metadata(file_bytes: bytes, filename: str) -> dict:
    """
    Extract comprehensive metadata, EXIF tags, GPS coordinates,
    and flag potential metadata inconsistencies.
    """
    hashes = calculate_hashes(file_bytes)
    result = {
        "filename": filename,
        "file_size_bytes": len(file_bytes),
        "file_size_formatted": f"{len(file_bytes) / 1024:.2f} KB",
        "hashes": hashes,
        "format": "Unknown",
        "dimensions": [0, 0],
        "megapixels": 0.0,
        "color_mode": "Unknown",
        "has_exif": False,
        "exif": {},
        "gps": None,
        "software_detected": None,
        "thumbnail_base64": None,
        "warnings": [],
        "tampering_indicators": []
    }

    try:
        img = Image.open(io.BytesIO(file_bytes))
        result["format"] = img.format or "Unknown"
        result["dimensions"] = [img.width, img.height]
        result["megapixels"] = round((img.width * img.height) / 1_000_000.0, 2)
        result["color_mode"] = img.mode

        # Try to extract EXIF
        exif_raw = img.getexif()
        if exif_raw:
            result["has_exif"] = True
            exif_dict = {}

            # Parse primary tags
            for tag_id, val in exif_raw.items():
                tag_name = ExifTags.TAGS.get(tag_id, f"Tag_{tag_id}")
                
                # Check for GPS info (0x8825)
                if tag_name == "GPSInfo" or tag_id == 0x8825:
                    gps_data = {}
                    try:
                        gps_ifd = exif_raw.get_ifd(0x8825)
                        for gps_id, gps_val in gps_ifd.items():
                            gps_name = ExifTags.GPSTAGS.get(gps_id, f"GPS_{gps_id}")
                            gps_data[gps_name] = str(gps_val)

                        # Extract latitude / longitude if present
                        lat = gps_ifd.get(2) # GPSLatitude
                        lat_ref = gps_ifd.get(1) # GPSLatitudeRef
                        lon = gps_ifd.get(4) # GPSLongitude
                        lon_ref = gps_ifd.get(3) # GPSLongitudeRef

                        if lat and lon:
                            lat_deg = _convert_gps_to_degrees(lat)
                            lon_deg = _convert_gps_to_degrees(lon)
                            if lat_deg is not None and lon_deg is not None:
                                if str(lat_ref).upper() == 'S':
                                    lat_deg = -lat_deg
                                if str(lon_ref).upper() == 'W':
                                    lon_deg = -lon_deg

                                result["gps"] = {
                                    "latitude": round(lat_deg, 6),
                                    "longitude": round(lon_deg, 6),
                                    "map_url": f"https://www.google.com/maps?q={lat_deg},{lon_deg}",
                                    "raw": gps_data
                                }
                    except Exception:
                        pass
                else:
                    # Format value safely
                    if isinstance(val, bytes):
                        try:
                            val = val.decode('utf-8', errors='ignore').strip()
                        except Exception:
                            val = f"<binary {len(val)} bytes>"
                    exif_dict[tag_name] = str(val)

            # Check for embedded IFDs (ExifIFD: 0x8769)
            try:
                exif_ifd = exif_raw.get_ifd(0x8769)
                for tag_id, val in exif_ifd.items():
                    tag_name = ExifTags.TAGS.get(tag_id, f"Exif_{tag_id}")
                    if isinstance(val, bytes):
                        try:
                            val = val.decode('utf-8', errors='ignore').strip()
                        except Exception:
                            val = f"<binary {len(val)} bytes>"
                    if tag_name not in exif_dict:
                        exif_dict[tag_name] = str(val)
            except Exception:
                pass

            result["exif"] = exif_dict

            # Inspect Software & Processing tags
            software_tags = [
                exif_dict.get("Software", ""),
                exif_dict.get("ProcessingSoftware", ""),
                exif_dict.get("HostComputer", "")
            ]
            detected_sw = []
            for s in software_tags:
                if s:
                    s_lower = s.lower()
                    for kw in SUSPICIOUS_SOFTWARE_KEYWORDS:
                        if kw in s_lower:
                            detected_sw.append(s)
                            result["tampering_indicators"].append(
                                f"Image metadata reveals post-processing tool: '{s}'."
                            )
                            break
            if detected_sw:
                result["software_detected"] = ", ".join(set(detected_sw))

            # Timestamp consistency checks
            orig_date = exif_dict.get("DateTimeOriginal")
            digitized_date = exif_dict.get("DateTimeDigitized")
            modify_date = exif_dict.get("DateTime")

            if orig_date and modify_date and orig_date != modify_date:
                result["tampering_indicators"].append(
                    f"EXIF capture date ({orig_date}) differs from modification date ({modify_date})."
                )

        else:
            if result["format"] in ["JPEG", "MPO"]:
                result["warnings"].append(
                    "Standard camera EXIF headers are completely absent (often stripped by web apps or image editors)."
                )

        # Try to extract embedded thumbnail
        try:
            if hasattr(img, "_getexif"):
                raw_exif = img._getexif()
                if raw_exif:
                    # Check thumbnail offset/data
                    if 0x0201 in raw_exif and 0x0202 in raw_exif:
                        # Thumbnail exists
                        pass
        except Exception:
            pass

    except Exception as e:
        result["warnings"].append(f"Metadata parsing encountered an issue: {str(e)}")

    return result
