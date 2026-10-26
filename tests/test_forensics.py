import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.analyzer import ForensicAnalyzer, compare_two_images
from engine.db import get_dashboard_stats, get_investigations

def test_engine_on_samples():
    samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))
    
    samples = [
        "sample_authentic.jpg",
        "sample_copy_move_forged.jpg",
        "sample_spliced_tampered.jpg",
        "sample_stego_hidden.png",
        "sample_eof_carved.jpg"
    ]

    print("=" * 75)
    print("VERIPIX DIGITAL FORENSIC ENGINE v2.0 - SYSTEM VERIFICATION TEST")
    print("=" * 75)

    loaded_bytes = {}

    for s_name in samples:
        s_path = os.path.join(samples_dir, s_name)
        assert os.path.exists(s_path), f"Sample {s_name} not found"
        
        with open(s_path, "rb") as f:
            data = f.read()
        loaded_bytes[s_name] = data

        analyzer = ForensicAnalyzer(data, s_name)
        results = analyzer.run_full_analysis(persist=True)

        scoring = results["scoring"]
        score_val = scoring["tamper_score"]
        status_label = scoring["status_label"]
        props = results.get("properties", {})

        print(f"\n[+] Analyzing: {s_name}")
        print(f"    - Investigation ID: {results['investigation_id']}")
        print(f"    - Dimensions: {results['metadata']['dimensions']} ({props.get('megapixels')} MP)")
        print(f"    - SHA-256: {results['metadata']['hashes']['sha256'][:16]}...")
        print(f"    - dHash (pHash): {props.get('perceptual_hash')}")
        print(f"    - Tamper Score: {score_val}% | Status: {status_label}")
        print(f"    - Observed Facts: {len(scoring['observed_facts'])} item(s)")
        for fact in scoring["observed_facts"]:
            print(f"       * {fact}")

        # Check histograms and channel views exist
        assert "histograms" in props and "luminance" in props["histograms"], "Histogram computation failed"
        assert "channel_views" in props and "red_channel_b64" in props["channel_views"], "Channel views generation failed"

        # Test PDF Generation
        pdf_bytes = analyzer.generate_pdf(case_id=results['investigation_id'])
        assert len(pdf_bytes) > 1000, f"PDF report generation failed for {s_name}"
        print(f"    - PDF Report: Generated successfully ({len(pdf_bytes)} bytes)")

    # Test Dual Image Comparison
    print("\n" + "-" * 75)
    print("[*] Testing Dual Image Comparison & Perceptual Hashing...")
    cmp_exact = compare_two_images(
        loaded_bytes["sample_authentic.jpg"],
        loaded_bytes["sample_authentic.jpg"],
        "auth1", "auth2"
    )
    assert cmp_exact["comparison"]["is_exact_match"] is True
    assert cmp_exact["comparison"]["perceptual_similarity_pct"] == 100.0
    print("    - Exact duplicate test: PASSED (100% similarity, exact SHA-256 match)")

    cmp_diff = compare_two_images(
        loaded_bytes["sample_authentic.jpg"],
        loaded_bytes["sample_spliced_tampered.jpg"],
        "auth", "spliced"
    )
    assert cmp_diff["comparison"]["is_exact_match"] is False
    print(f"    - Distinct images test: PASSED ({cmp_diff['comparison']['perceptual_similarity_pct']}% visual similarity, non-matching)")

    # Test SQLite Database Persistence
    print("\n" + "-" * 75)
    print("[*] Testing Persistent Database Storage (SQLite)...")
    stats = get_dashboard_stats()
    records = get_investigations()
    print(f"    - Stored Records Count: {stats['total_analyzed']}")
    print(f"    - Potential Anomalies Flagged: {stats['potential_anomalies']}")
    print(f"    - Inconclusive: {stats['inconclusive']}")
    print(f"    - No Anomaly Detected: {stats['no_anomaly_detected']}")
    assert stats["total_analyzed"] >= 5, "Database failed to persist records"

    print("\n" + "=" * 75)
    print("ALL TESTS PASSED SUCCESSFULLY! Forensic v2.0 pipeline verified.")
    print("=" * 75)

if __name__ == "__main__":
    test_engine_on_samples()
