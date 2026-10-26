def compute_tamper_score(
    metadata_res: dict,
    ela_res: dict,
    copymove_res: dict,
    noise_res: dict,
    freq_res: dict,
    luminance_res: dict,
    stego_res: dict,
    carving_res: dict
) -> dict:
    """
    Compute a consolidated Multi-Metric Forensic Anomaly Index (0 - 100%).
    Synthesizes empirical findings from metadata, compression artifacts, cloning,
    sensor noise, frequency harmonics, illumination, steganography, and file structure.
    Adheres strictly to objective, neutral digital forensics reporting standards.
    """
    total_score = 0
    breakdown = []
    observed_facts = []
    algorithmic_interpretations = []

    # 1. Metadata Analysis
    meta_score = 0
    if metadata_res.get("software_detected"):
        meta_score += 25
        sw = metadata_res["software_detected"]
        breakdown.append(f"Image editing/processing software tag detected: '{sw}' (+25 pts)")
        observed_facts.append(f"EXIF metadata records editing tool: '{sw}'.")
        algorithmic_interpretations.append("Indicates prior post-processing or re-saving in an external editor; does not by itself prove malicious forgery.")
    elif metadata_res.get("tampering_indicators"):
        meta_score += 10
        breakdown.append("Metadata timestamp discrepancies detected (+10 pts)")
        observed_facts.append("Discrepancy detected between capture date and modification timestamp in EXIF headers.")
    total_score += min(25, meta_score)

    # 2. Error Level Analysis (ELA)
    ela_score = 0
    if ela_res.get("has_tamper_signature"):
        count = ela_res.get("suspicious_region_count", 0)
        pct = ela_res.get("anomaly_percentage", 0.0)
        ela_score = min(25, int(15 + count * 3))
        breakdown.append(f"ELA localized compression divergence ({count} clusters, {pct}% area) (+{ela_score} pts)")
        observed_facts.append(f"Compression error variance reveals {count} localized area(s) ({pct}% of image) with divergent error levels.")
        algorithmic_interpretations.append("Divergent error levels suggest composite splicing, though high-contrast edges or resaving can also induce localized error.")
    elif ela_res.get("std_deviation", 0) > 9.0:
        ela_score = 8
        breakdown.append("Moderate compression irregularity across canvas (+8 pts)")
    total_score += min(25, ela_score)

    # 3. Copy-Move Cloning Detection
    cm_score = 0
    if copymove_res.get("forgery_detected"):
        clusters = copymove_res.get("clone_clusters_count", 0)
        cm_score = min(30, 20 + clusters * 5)
        breakdown.append(f"Copy-Move duplication candidate: {clusters} cluster(s) (+{cm_score} pts)")
        observed_facts.append(f"ORB/AKAZE spatial vector clustering identified {clusters} duplicated region pair(s) with aligned translation vectors.")
        algorithmic_interpretations.append("Repetitive textures or natural patterns may produce false matches; manual visual review of connecting vectors is recommended.")
    total_score += min(30, cm_score)

    # 4. Sensor Noise Consistency
    noise_score = 0
    if noise_res.get("is_noise_inconsistent"):
        cv_val = noise_res.get("coefficient_of_variation", 0.0)
        pct = noise_res.get("abnormal_block_percentage", 0.0)
        noise_score = min(20, int(12 + cv_val * 6))
        breakdown.append(f"Sensor noise variance disparity (CV = {cv_val:.2f}, {pct}% abnormal blocks) (+{noise_score} pts)")
        observed_facts.append(f"High-pass noise residual variance is heterogeneous across spatial blocks ({pct}% abnormal noise variance).")
        algorithmic_interpretations.append("Mismatched noise distribution can signify objects sourced from differing sensors or local filtering.")
    total_score += min(20, noise_score)

    # 5. Frequency Domain (2D FFT)
    freq_score = 0
    if freq_res.get("has_periodic_artifacts"):
        peaks = freq_res.get("periodic_peaks_detected", 0)
        freq_score = min(15, int(8 + (peaks // 5)))
        breakdown.append(f"Periodic frequency harmonic spikes detected ({peaks} peaks) (+{freq_score} pts)")
        observed_facts.append(f"2D Fourier magnitude spectrum exhibits {peaks} prominent symmetric harmonic peaks in high frequencies.")
        algorithmic_interpretations.append("Harmonic lattice lines correlate with periodic resampling, double JPEG compression, or generative grid patterns.")
    total_score += min(15, freq_score)

    # 6. File Carving & EOF Payload
    carve_score = 0
    if carving_res.get("has_eof_payload"):
        bytes_len = carving_res.get("trailing_payload_bytes", 0)
        ptype = carving_res.get("detected_payload_type") or "unidentified binary data"
        carve_score = 30 if carving_res.get("detected_payload_type") else 20
        breakdown.append(f"Appended trailing data past format EOF ({bytes_len} bytes: {ptype}) (+{carve_score} pts)")
        observed_facts.append(f"Detected {bytes_len} bytes of data appended past the standard format End-of-File marker (Signature: {ptype}).")
        algorithmic_interpretations.append("Trailing data outside container markers is atypical for standard cameras and frequently indicates steganography or payload embedding.")
    total_score += min(30, carve_score)

    # 7. Steganography / LSB
    stego_score = 0
    if stego_res.get("is_stego_detected"):
        prob = stego_res.get("chi_square_tests", {}).get("max_stego_probability", 0.0)
        stego_score = 25
        breakdown.append(f"Steganographic LSB distribution anomaly (PoV confidence: {prob}%) (+25 pts)")
        observed_facts.append(f"Westfeld-Pfitzmann Chi-Square test confirms equalized LSB Pairs of Values (PoV confidence: {prob}%).")
        algorithmic_interpretations.append("Statistical equalization of adjacent byte values indicates potential LSB substitution steganography.")
    elif stego_res.get("max_lsb_entropy", 0) > 0.992:
        stego_score = 10
        breakdown.append("Elevated LSB plane entropy (+10 pts)")
    total_score += min(25, stego_score)

    # 8. Luminance Gradient
    lum_score = 0
    if luminance_res.get("is_lighting_inconsistent"):
        lum_score = 12
        breakdown.append("Lateral lighting direction discrepancy (+12 pts)")
        observed_facts.append("Surface luminance gradient orientation diverges between horizontal scene quadrants.")
        algorithmic_interpretations.append("Contradictory directional lighting can indicate composite assembly from sources under different illumination.")
    total_score += min(15, lum_score)

    # Final score normalization (0 to 100)
    final_score = min(100, max(0, total_score))

    # Neutral forensic classification
    if final_score >= 50:
        status = "POTENTIAL_ANOMALY"
        status_label = "Potential Anomaly Detected"
        status_color = "#ef4444" # Red
        risk_level = "Elevated"
        summary = "Multiple algorithmic checks identified statistical, structural, or metadata anomalies. Further manual investigation is recommended."
    elif final_score >= 20:
        status = "INCONCLUSIVE"
        status_label = "Inconclusive / Mild Artifacts"
        status_color = "#f59e0b" # Amber
        risk_level = "Moderate"
        summary = "Isolated anomalies detected. Findings may result from legitimate re-compression, social media processing, or subtle enhancement."
    else:
        status = "NO_ANOMALY"
        status_label = "No Anomaly Detected by Selected Checks"
        status_color = "#10b981" # Green
        risk_level = "Baseline"
        summary = "All evaluated parameters (EXIF, compression error, sensor noise, frequency spectrum, and file structure) align within expected baseline bounds."

    if not observed_facts:
        observed_facts.append("No statistical or structural deviations detected across the eight forensic modules.")

    disclaimer = (
        "Forensic Disclaimer: This automated examination evaluates algorithmic heuristics, compression artifacts, "
        "and statistical properties. In accordance with ISO/IEC 27037 digital evidence principles, algorithmic findings "
        "are indicators and should not be treated as absolute legal proof without contextual investigation."
    )

    return {
        "tamper_score": final_score,
        "status": status,
        "status_label": status_label,
        "status_color": status_color,
        "risk_level": risk_level,
        "summary": summary,
        "disclaimer": disclaimer,
        "score_breakdown": breakdown,
        "observed_facts": observed_facts,
        "algorithmic_interpretations": algorithmic_interpretations,
        # Backward compatibility for report & UI
        "verdict": status_label,
        "verdict_color": status_color,
        "recommendation": summary,
        "evidence_summary": observed_facts
    }
