import re
import binascii

MAGIC_SIGNATURES = [
    (b"\x50\x4B\x03\x04", "ZIP Archive (.zip / .docx / .jar)"),
    (b"\x50\x4B\x05\x06", "Empty ZIP Archive"),
    (b"\x52\x61\x72\x21\x1A\x07", "RAR Archive (.rar)"),
    (b"\x37\x7A\xBC\xAF\x27\x1C", "7-Zip Archive (.7z)"),
    (b"%PDF-", "Adobe PDF Document (.pdf)"),
    (b"MZ", "Windows Executable / DLL (.exe / .dll)"),
    (b"\xFF\xD8\xFF", "Embedded JPEG Image"),
    (b"\x89PNG\r\n\x1a\n", "Embedded PNG Image"),
    (b"GIF89a", "Embedded GIF Image (89a)"),
    (b"GIF87a", "Embedded GIF Image (87a)"),
    (b"\x1F\x8B\x08", "GZIP Compressed File (.gz)")
]

SUSPICIOUS_KEYWORD_PATTERNS = [
    r"https?://[^\s\"'<>]+",
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    r"(?i)powershell|cmd\.exe|bash|eval\(|base64|system\(|chmod|passwd",
    r"(?i)password|secret|confidential|admin|flag\{[^}]+\}",
    r"<\?php|<script"
]

def format_hex_dump(data: bytes, max_bytes: int = 128) -> str:
    """Format bytes into standard forensic hex dump (offset, hex, ascii)."""
    lines = []
    chunk = data[:max_bytes]
    for i in range(0, len(chunk), 16):
        line_bytes = chunk[i:i+16]
        hex_str = " ".join(f"{b:02X}" for b in line_bytes)
        ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in line_bytes)
        lines.append(f"{i:04X}  {hex_str:<48}  |{ascii_str}|")
    return "\n".join(lines)

def carve_file_and_eof(file_bytes: bytes, file_format: str = "JPEG") -> dict:
    """
    Inspect raw file stream for End-of-File (EOF) anomalies,
    appended hidden payloads, embedded file signatures, and forensic strings.

    Parameters:
        file_bytes: Raw binary bytes of image file
        file_format: Format string (JPEG, PNG, etc.)
    """
    total_size = len(file_bytes)
    eof_offset = -1
    trailing_size = 0
    trailing_data = b""
    detected_payload_type = None

    # Detect EOF marker
    fmt_upper = (file_format or "").upper()

    if fmt_upper in ["JPEG", "JPG", "MPO"]:
        # JPEG ends at 0xFF 0xD9
        last_eoi = file_bytes.rfind(b"\xFF\xD9")
        if last_eoi != -1:
            eof_offset = last_eoi + 2
            if eof_offset < total_size:
                trailing_size = total_size - eof_offset
                trailing_data = file_bytes[eof_offset:]

    elif fmt_upper == "PNG":
        # PNG ends at IEND chunk (49 45 4E 44) + 4 bytes CRC
        iend_pos = file_bytes.rfind(b"IEND")
        if iend_pos != -1:
            eof_offset = iend_pos + 8
            if eof_offset < total_size:
                trailing_size = total_size - eof_offset
                trailing_data = file_bytes[eof_offset:]

    elif fmt_upper == "GIF":
        # GIF ends at 0x3B
        last_trailer = file_bytes.rfind(b"\x3B")
        if last_trailer != -1:
            eof_offset = last_trailer + 1
            if eof_offset < total_size:
                trailing_size = total_size - eof_offset
                trailing_data = file_bytes[eof_offset:]

    # Check for embedded file signatures in trailing data
    if trailing_size > 0:
        for magic, desc in MAGIC_SIGNATURES:
            if trailing_data.startswith(magic) or magic in trailing_data[:64]:
                detected_payload_type = desc
                break

    # Extract printable ASCII strings (min length 4)
    # Search whole file or trailing data
    target_for_strings = trailing_data if trailing_size > 0 else file_bytes
    found_strings = []
    
    # Extract strings
    pattern = re.compile(b"[ -~]{4,}")
    raw_matches = pattern.findall(target_for_strings)

    keyword_hits = []
    for m in raw_matches:
        try:
            s = m.decode("ascii", errors="ignore").strip()
            if len(s) >= 4:
                # Check suspicious patterns
                for kw_pat in SUSPICIOUS_KEYWORD_PATTERNS:
                    if re.search(kw_pat, s):
                        keyword_hits.append(s)
                        break
                if len(found_strings) < 40:
                    found_strings.append(s)
        except Exception:
            pass

    has_eof_anomaly = trailing_size > 32 # Ignore small trailing padding (<= 32 bytes)
    notes = []
    if has_eof_anomaly:
        desc = detected_payload_type or "Unidentified binary data"
        notes.append(
            f"Detected {trailing_size} trailing bytes appended beyond official EOF marker. Identified payload: {desc}."
        )
    else:
        notes.append("No abnormal data appended beyond the official format terminator.")

    return {
        "total_file_size": total_size,
        "eof_marker_offset": eof_offset,
        "trailing_payload_bytes": trailing_size,
        "has_eof_payload": has_eof_anomaly,
        "detected_payload_type": detected_payload_type,
        "suspicious_keywords_found": keyword_hits[:15],
        "extracted_strings_sample": found_strings[:25],
        "trailing_hex_dump": format_hex_dump(trailing_data, 128) if trailing_size > 0 else "",
        "notes": notes
    }
