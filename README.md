# VeriPix v2.0: Professional Digital Image Forensics & Evidence Auditing Suite

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-5.0+-red.svg)](https://opencv.org/)
[![Database: SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**VeriPix v2.0** is an enterprise-grade digital image forensic examination system designed for cyber investigation laboratories, law enforcement evidence auditing, and academic research. Built with a modular Python processing engine, a persistent SQLite evidence store, and a modern cybersecurity-inspired Web Workbench, VeriPix automates passive forensic analysis, verifies image integrity, detects manipulation anomalies, and produces court-admissible PDF & JSON evidence reports.

---

## 🌟 Key Capabilities & Enhancements in v2.0

### 1. Unified Forensic Operations Dashboard
- **Live Statistics**: Real-time aggregation of total images analyzed, potential anomalies flagged, inconclusive cases, and unmanipulated baselines computed dynamically from persistent SQLite records.
- **Recent Activity Log**: Case history indexed with cryptographic hashes, analysis verdicts, risk percentages, and timestamps.

### 2. Multi-Factor Forensic Processing Pipeline
| Module | Technique / Method | What It Detects |
|---|---|---|
| **Cryptographic Integrity** | MD5, SHA-1, SHA-256 | Chain-of-custody immutability and bit-level file integrity (ISO/IEC 27037). |
| **Perceptual Hashing (dHash)** | 64-bit gradient difference hash | Visual similarity, near-duplicates, resizing, and lossy compression variants. |
| **EXIF & Geolocation Metadata** | EXIF, IFD tags, reverse GPS mapping | Camera hardware, capture timestamps, GPS coordinates, and post-processing software flags (*Adobe Photoshop, Canva, GIMP*). |
| **Error Level Analysis (ELA)** | Differential re-quantization at configurable JPEG quality & scale | Spliced foreign elements with divergent compression histories. |
| **Copy-Move (Clone) Detection** | ORB/AKAZE keypoints + spatial distance filter ($\ge 40\text{ px}$) + displacement vector clustering | Duplicated/cloned regions inside the same image with directional vector arrow plots. |
| **Sensor Noise Residual (PRNU)** | Median filter high-pass residual $+ 16\times 16$ block variance modeling | PRNU sensor noise disparities resulting from composite splicing or AI inpainting. |
| **Frequency Domain (2D FFT)** | 2D Fourier magnitude spectrum + harmonic peak symmetry | Periodic resampling lattices, double JPEG compression blocking grids, and generative artifacts. |
| **Luminance Consistency** | Sobel gradients ($G_x, G_y$) & lateral quadrant lighting vectors | Conflicting lighting sources between spliced foreground objects and background. |
| **Steganography & Bit Planes** | 8-bit plane decomposition (R, G, B), Shannon entropy, Westfeld-Pfitzmann $\chi^2$ PoV test | Hidden payloads or encrypted text embedded in Least Significant Bits (LSB). |
| **File Carving & Structure** | Container boundary verification (JPEG EOI `0xFFD9`, PNG `IEND`) + magic byte matching | Trailing hidden payloads (ZIP, RAR, PDF, EXE) and printable strings appended after EOF. |
| **Color Histograms & Channels** | 256-bin histograms (RGB & Luminance) + Isolated channel visualizer | Color distribution shifts, channel-specific anomalies, and grayscale conversion. |

### 3. Dual Specimen Hash & Image Comparator
- Compares two suspect images side-by-side.
- Evaluates exact cryptographic matches (SHA-256 match vs. mismatch).
- Calculates perceptual hash similarity percentage (dHash Hamming distance).
- Generates a thermal pixel difference heatmap.

### 4. Interactive Evidence Workspace
- Drag-and-drop ingestion with magic-byte format validation (JPEG, PNG, WebP, TIFF, BMP) and 25MB file size limit.
- Original evidence preservation (analysis performed on safe working copy).
- Interactive image canvas with **Zoom In (+)**, **Zoom Out (-)**, and **Fit to Screen (Reset)** controls.
- Color channel switcher (**RGB Composite**, **Red**, **Green**, **Blue**, **Grayscale**).
- Draggable **Before/After Split-Screen Slider** comparing evidence against ELA, clone vectors, noise heatmaps, and 2D FFT spectra.

### 5. Persistent Case Archive & Audit Log
- Built-in SQLite database stores every investigation permanently.
- Search by Case ID, filename, or SHA-256 hash.
- Filter by analysis status (`Potential Anomaly`, `Inconclusive`, `No Anomaly`).
- 1-click **JSON Audit Log** download and official **PDF Examination Report** export.

### 6. Neutral Forensic Reporting Standards
- Formally complies with digital evidence guidelines: avoids single-heuristic definitive claims.
- Classifications:
  - `No Anomaly Detected by Selected Checks` (Baseline)
  - `Inconclusive / Mild Artifacts` (Moderate)
  - `Potential Anomaly Detected` (Elevated Risk)
- Clear distinction between **Observed Empirical Facts** and **Algorithmic Interpretations**.
- Formal ISO/IEC 27037 methodological disclaimer.

---

## 🏗️ Project Architecture

```
digital-image-forensics-tool/
├── engine/                       # Core forensic processing engine
│   ├── __init__.py
│   ├── metadata.py               # Hashes, EXIF tags, GPS, software inspection
│   ├── properties.py             # dHash, color histograms, channel separation
│   ├── ela.py                    # Error Level Analysis with dynamic quality/scale
│   ├── copy_move.py              # Keypoint & displacement vector clone detector
│   ├── noise.py                  # High-pass sensor noise residual & block variance
│   ├── frequency.py              # 2D Fast Fourier Transform magnitude spectrum
│   ├── luminance.py              # Sobel luminance gradient & lighting vectors
│   ├── stego_lsb.py              # Bit-planes (0-7), Shannon entropy, Chi-square
│   ├── carving.py                # EOF marker parsing, trailing payload & strings
│   ├── scoring.py                # Multi-metric Tampering Probability Index
│   ├── db.py                     # SQLite persistent investigation database
│   ├── report_generator.py       # Court-admissible ReportLab PDF generator
│   └── analyzer.py               # Central orchestrator & dual comparator
├── evidence_store/               # Secure evidence storage for ingested working copies
├── templates/
│   └── index.html                # Professional cyber-forensics dashboard UI
├── static/
│   ├── css/style.css             # Dark charcoal & blue forensic stylesheet
│   └── js/app.js                 # Frontend application controller & router
├── samples/                      # Forensic test specimens (ground truth)
│   ├── sample_authentic.jpg      # Clean capture with Canon EOS EXIF & GPS
│   ├── sample_copy_move_forged.jpg # Cloned balloon duplicated in sky
│   ├── sample_spliced_tampered.jpg # Spliced composite patch + Photoshop tag
│   ├── sample_stego_hidden.png   # Covert data embedded into pixel LSBs
│   └── sample_eof_carved.jpg     # Secret ZIP archive appended past JPEG EOI
├── tests/
│   └── test_forensics.py         # Automated verification test suite
├── app.py                        # FastAPI web application server
├── cli.py                        # Headless Command-Line Interface
├── run.bat                       # 1-click Windows runner
├── requirements.txt              # Project dependencies
├── PROJECT_REPORT.md             # Formal academic project documentation
└── PRESENTATION_GUIDE.md         # Viva defense and presentation guide
```

---

## 🚀 Quick Start Guide

### 1. Launch the Application
Navigate to the directory and run:

```powershell
python app.py
```
*(Or simply double-click [`run.bat`](file:///c:/Complaint-Registration-Mangement-System/digital-image-forensics-tool/run.bat))*

The server will automatically detect an open port (e.g. `http://127.0.0.1:8000` or `8001`) and pop open your default browser.

### 2. Run the Automated Test Suite
To verify all algorithmic modules, database persistence, perceptual hashing, and PDF generation:

```powershell
python tests/test_forensics.py
```

### 3. Headless Command-Line Interface (CLI)
```powershell
# Analyze suspect image and export visual plates + PDF report
python cli.py --image samples/sample_spliced_tampered.jpg --report --outdir ./results
```

---

## ⚖️ Standards & References
- **ISO/IEC 27037:2012**: *Guidelines for identification, collection, acquisition, and preservation of digital evidence.*
- **NIST SP 800-86**: *Guide to Integrating Forensic Techniques into Incident Response.*
- **Krawetz, N. (2007)**: *A Picture's Worth: Digital Image Analysis and Error Level Analysis.*
- **Westfeld & Pfitzmann (1999)**: *Attacks on Steganographic Systems: Breaking LSB Steganography.*

---

## 📜 License
Released under the MIT License. Developed for digital forensics education, research, and authenticity verification.
