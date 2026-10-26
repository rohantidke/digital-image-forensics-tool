import os
import sys
import argparse
import json
import base64

from engine.analyzer import ForensicAnalyzer

def decode_and_save_b64(b64_str: str, filepath: str):
    """Save data:image base64 string to an image file."""
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    raw_data = base64.b64decode(b64_str)
    with open(filepath, "wb") as f:
        f.write(raw_data)

def run_cli():
    parser = argparse.ArgumentParser(
        description="VeriPix: Automated Digital Image Forensic & Tampering Detection CLI"
    )
    parser.add_argument("--image", "-i", required=True, help="Path to target suspect image file")
    parser.add_argument("--outdir", "-o", default="./forensic_output", help="Directory to save forensic plates & report")
    parser.add_argument("--report", "-r", action="store_true", help="Generate official PDF forensic report")
    parser.add_argument("--case-id", default=None, help="Case reference identifier")
    parser.add_argument("--examiner", default="Forensic Field Examiner", help="Examiner name")
    parser.add_argument("--ela-quality", type=int, default=95, help="ELA JPEG quality (70-98)")
    parser.add_argument("--ela-scale", type=int, default=25, help="ELA difference amplification multiplier")

    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"[-] Error: Image path '{args.image}' does not exist.")
        sys.exit(1)

    os.makedirs(args.outdir, exist_ok=True)
    filename = os.path.basename(args.image)

    print("=" * 75)
    print(f"VERIPIX DIGITAL FORENSIC EXAMINATION ENGINE - CLI")
    print(f"Target Evidence: {filename}")
    print("=" * 75)

    with open(args.image, "rb") as f:
        file_bytes = f.read()

    print("[*] Processing image through 8 forensic analysis modules...")
    analyzer = ForensicAnalyzer(file_bytes, filename)
    results = analyzer.run_full_analysis(ela_quality=args.ela_quality, ela_scale=args.ela_scale)

    meta = results["metadata"]
    scoring = results["scoring"]
    ela = results["ela"]
    cm = results["copy_move"]
    noise = results["noise"]
    freq = results["frequency"]
    stego = results["stego"]
    carve = results["carving"]

    print("\n[1] EVIDENCE RECORD & HASHES:")
    print(f"    - Dimensions: {meta['dimensions'][0]}x{meta['dimensions'][1]} px ({meta['megapixels']} MP)")
    print(f"    - File Size : {meta['file_size_formatted']} ({meta['file_size_bytes']} bytes)")
    print(f"    - MD5       : {meta['hashes']['md5']}")
    print(f"    - SHA-256   : {meta['hashes']['sha256']}")

    print("\n[2] FORENSIC VERDICT & TAMPER SCORE:")
    print(f"    - Tamper Probability : {scoring['tamper_score']}%")
    print(f"    - Forensic Verdict   : {scoring['verdict']} ({scoring['risk_level']} Risk)")
    print(f"    - Recommendation     : {scoring['recommendation']}")

    print("\n[3] KEY EVIDENCE FINDINGS:")
    for finding in scoring["evidence_summary"]:
        print(f"    • {finding}")

    # Save visual forensic plates
    print(f"\n[*] Exporting forensic visual plates to '{args.outdir}'...")
    plates = {
        "plate_ela_amplified.png": ela.get("ela_image_base64"),
        "plate_ela_thermal_heatmap.png": ela.get("heatmap_image_base64"),
        "plate_copymove_annotated.png": cm.get("annotated_image_base64"),
        "plate_noise_residual.png": noise.get("noise_residual_base64"),
        "plate_noise_variance_heatmap.png": noise.get("noise_heatmap_base64"),
        "plate_frequency_spectrum_2d.png": freq.get("spectrum_image_base64"),
        "plate_luminance_gradient.png": results["luminance"].get("gradient_image_base64")
    }

    for fname, b64_data in plates.items():
        if b64_data:
            decode_and_save_b64(b64_data, os.path.join(args.outdir, fname))

    # Save JSON summary (without heavy base64 strings)
    json_summary = {
        "filename": filename,
        "metadata": meta,
        "scoring": scoring,
        "ela_metrics": {k: v for k, v in ela.items() if not k.endswith("_base64")},
        "copymove_metrics": {k: v for k, v in cm.items() if not k.endswith("_base64")},
        "noise_metrics": {k: v for k, v in noise.items() if not k.endswith("_base64")},
        "frequency_metrics": {k: v for k, v in freq.items() if not k.endswith("_base64")},
        "luminance_metrics": {k: v for k, v in results["luminance"].items() if not k.endswith("_base64")},
        "stego_metrics": {k: v for k, v in stego.items() if k != "bit_planes_preview"},
        "carving_metrics": carve
    }

    json_path = os.path.join(args.outdir, f"forensic_report_{filename}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_summary, f, indent=4)
    print(f" [+] JSON Report saved: {json_path}")

    # Generate PDF if requested
    if args.report:
        pdf_path = os.path.join(args.outdir, f"Forensic_Report_{filename}.pdf")
        pdf_bytes = analyzer.generate_pdf(case_id=args.case_id, examiner=args.examiner)
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        print(f" [+] Official PDF Forensic Report generated: {pdf_path}")

    print("\n" + "=" * 75)
    print("[*] Forensic examination complete.")
    print("=" * 75)

if __name__ == "__main__":
    run_cli()
