# VeriPix: Digital Image Forensic Tool - Presentation & Viva Defense Guide

Use this guide to prepare your slides, live software demonstration, and viva voce defense.

---

## Part 1: Slide-by-Slide Presentation Structure (10-12 Minutes)

### Slide 1: Title & Team Information
- **Title**: Design and Development of a Tool for Digital Forensics of Images
- **Tool Name**: VeriPix - Advanced Image Forensics & Tampering Detection Toolkit
- **Presenter(s)**: [Your Name / Team Members]
- **Supervisor / Department**: [Department of Computer Science & Engineering / Cybersecurity]

### Slide 2: Problem Statement & Motivation
- Proliferation of sophisticated photo-editing software (Photoshop, GIMP) and AI inpainting makes digital forgery trivial.
- Splicing, cloning, and metadata manipulation threaten court evidence, insurance verifications, journalism, and cybersecurity.
- Traditional tools are either fragmented command-line utilities or expensive proprietary suites.
- **Objective**: Develop an integrated, open-architecture, passive digital image forensic suite with automated scoring and official report generation.

### Slide 3: Passive vs. Active Forensics
- **Active Forensics**: Requires digital watermarks or digital signatures embedded at capture time. Ineffective if no prior watermark exists.
- **Passive (Blind) Forensics**: No prior knowledge required. Inspects intrinsic mathematical and physical footprints left during image acquisition, lossy compression, and manipulation.

### Slide 4: System Architecture & Workflow
- Input suspect image $\to$ Cryptographic Hash Generation (MD5, SHA-1, SHA-256).
- Parallel 8-Module Analysis Pipeline.
- Multi-Factor Tampering Probability Aggregation ($0 - 100\%$).
- Dual Output: Modern Web Workbench + Court-Admissible PDF Report.

### Slide 5: Metadata & Integrity Verification
- Cryptographic chain-of-custody verification.
- Deep EXIF & IFD parsing: Camera make, model, lens, exposure, timestamps.
- Reverse-lookup GPS Geolocation (latitude/longitude with Google Maps link).
- Software fingerprinting: Flags editing suites (Photoshop, Canva, GIMP, Snapseed).

### Slide 6: Error Level Analysis (ELA)
- Principle: JPEG lossy compression asymptotes error levels across repeated saves.
- Spliced patches possess different compression histories and quantize with noticeably higher error.
- Dynamic quality recompression (70–98%) + scale enhancement ($25\times$) + Thermal Jet heatmap.

### Slide 7: Copy-Move (Cloning) Forgery Detection
- Principle: Duplicating an object inside the same image bypasses ELA because noise and compression match.
- Solution: Keypoint feature extraction (ORB/AKAZE) + $k$-NN matching with Lowe's ratio test.
- Spatial Euclidean distance filter ($\ge 40\text{ px}$) suppresses natural texture matches.
- Translational displacement vector clustering identifies true cloned clusters.

### Slide 8: Sensor Noise Residual & 2D FFT Harmonics
- **Noise Analysis**: Photo-Response Non-Uniformity (PRNU) residual extraction via median filter subtraction; detects spliced objects from different sensors via spatial block variance.
- **2D Fourier Transform (FFT)**: Logarithmic magnitude spectrum reveals periodic resampling lattices, double JPEG compression grids, and AI lattice spikes.

### Slide 9: Steganography & File Carving
- **Stego LSB**: Bit-plane decomposition (Bits 0–7 for R, G, B channels); Shannon entropy calculation; Westfeld-Pfitzmann Chi-Square ($\chi^2$) test for Pairs of Values (PoVs) equalization.
- **File Carving**: JPEG EOI (`0xFFD9`) / PNG `IEND` boundary scanning; carves appended hidden payloads (ZIP archives, PDFs, executables) and printable strings.

### Slide 10: Multi-Metric Tampering Index
- Multi-factor weighted scoring model ($0 - 100\%$).
- Three-tier classification:
  - $0 - 24\%$: `AUTHENTIC / LOW RISK` (Green)
  - $25 - 54\%$: `SUSPICIOUS / INCONCLUSIVE` (Orange)
  - $55 - 100\%$: `LIKELY TAMPERED` (Red)
- Automated evidence rationale and investigator recommendations.

### Slide 11: Live Demonstration & Results
- Showcase 5 test specimens:
  1. Authentic photograph (low score, verified EXIF).
  2. Copy-move forged image (cloned balloon with vector arrows).
  3. Photoshop spliced composite (high ELA error + software flag).
  4. LSB Steganography payload (high entropy + 100% Chi-square confidence).
  5. Appended ZIP payload (carved file with extracted text strings).
- Demonstration of the interactive split-screen comparison slider.
- Demonstration of the one-click PDF forensic case report download.

### Slide 12: Conclusion & Future Scope
- Summary of contributions.
- Future work: Deepfake detection using Vision Transformers, C2PA Content Credentials support, and GPU acceleration.

---

## Part 2: Top 15 Viva Questions & Model Answers

### Q1: What is Error Level Analysis (ELA) and how does it detect tampering?
**Answer**: ELA works on the principle that JPEG images lose a predictable amount of data each time they are compressed. When an image is resaved, the error rate across uniform areas decreases asymptotically. If an external object is spliced into the image, its compression history will differ from the background canvas. By resaving the image at a known quality level (e.g., 95%) and computing the amplified absolute difference, the spliced region shines brightly with significantly higher error levels compared to the rest of the canvas.

### Q2: Why doesn't ELA detect copy-move cloning?
**Answer**: Because in copy-move forgery, both the source object and the destination canvas belong to the exact same image. They have identical compression history, color quantization, and sensor noise. Therefore, recompressing the image produces identical error levels across both regions. To catch copy-move forgeries, we must use keypoint feature matching (ORB/AKAZE) and spatial displacement vector clustering instead.

### Q3: Why do you enforce a minimum spatial distance between keypoints in Copy-Move detection?
**Answer**: In natural images, adjacent pixels in smooth textures (like grass, walls, or fabrics) share very similar local descriptors. Without a spatial distance threshold, nearest-neighbor matching would match millions of neighboring pixels that are just 1 or 2 pixels apart, generating massive false positives. Enforcing a Euclidean distance constraint (e.g., $\ge 40\text{ px}$) ensures we only evaluate distinct, spatially separated regions of the image.

### Q4: How does the Westfeld-Pfitzmann Chi-Square test detect LSB steganography?
**Answer**: In natural images, natural gradients create natural frequency disparities between adjacent even and odd byte values $(2k, 2k+1)$ (known as Pairs of Values or PoVs). When secret data is embedded using LSB replacement, bits are flipped randomly, causing the frequencies of $2k$ and $2k+1$ to equalize toward their arithmetic mean. The Chi-Square test measures this artificial equalization: when the disparity ratio approaches zero, the Chi-Square statistic becomes abnormally small, indicating statistical certainty of LSB steganography.

### Q5: What is PRNU and how is it used in forensic noise analysis?
**Answer**: PRNU stands for *Photo-Response Non-Uniformity*. It is an intrinsic physical fingerprint caused by minute silicon manufacturing variations in camera sensors. Every sensor leaves a unique high-frequency noise pattern. When an object is spliced from another camera or generated via software, its local noise variance differs from the host camera's PRNU. By subtracting a median filter, we isolate the noise residual and calculate block-wise variance across the canvas to detect foreign patches.

### Q6: What do harmonic spikes in the 2D Fast Fourier Transform (FFT) indicate?
**Answer**: Natural unmanipulated images have continuous, smooth radial frequency decay with energy concentrated at low frequencies. Periodic operations—such as bilinear or bicubic image resizing, periodic cloning, double JPEG compression grids ($8 \times 8$ blocking artifacts), or GAN generative deconvolution—introduce sharp spatial periodicities. In the frequency domain, these periodicities manifest as symmetrical harmonic starbursts or isolated peak spikes in the high-frequency quadrants.

### Q7: What is the purpose of cryptographic hashes (MD5, SHA-256) in digital forensics?
**Answer**: In accordance with ISO/IEC 27037 standards, cryptographic hashes establish the *Chain of Custody* and prove evidence integrity. Even a single bit change in the file alters the SHA-256 hash completely (the avalanche effect). Calculating hashes at the moment of evidence ingestion guarantees to a court of law that the analyzed file has not been altered during examination.

### Q8: What is "File Carving" and how does VeriPix detect hidden data appended to images?
**Answer**: Image formats have official binary terminal markers. For example, a JPEG file must terminate at the End-of-Image (EOI) marker `0xFF 0xD9`, and a PNG terminates after the `IEND` chunk. If the total file size on disk is larger than the offset of this terminator, extra data has been appended past EOF. VeriPix scans the trailing byte stream for magic headers (such as `\x50\x4B\x03\x04` for ZIP or `%PDF-` for PDFs) and extracts printable ASCII strings to expose covert payloads.

### Q9: Can an image have its EXIF stripped and still be authentic?
**Answer**: Yes. Many social media platforms (WhatsApp, Twitter/X, Instagram) automatically strip EXIF metadata to protect user privacy and compress images for transmission. That is why VeriPix treats missing EXIF as a mild warning rather than conclusive evidence of malicious tampering. The multi-factor scoring engine relies on physical image signals (ELA, noise, cloning, FFT) rather than metadata alone.

### Q10: How does VeriPix prevent false positives in lighting/luminance analysis?
**Answer**: In natural outdoor photos, there is a natural vertical illumination disparity (the sky is bright and lit from above, while the ground is dark). VeriPix calculates *lateral* divergence (Left vs. Right quadrants) rather than simple vertical divergence. If an object on the left is lit from the left while the background on the right is lit from the right, this contradictory lateral illumination confirms composite splicing.

### Q11: What is the computational complexity of the ORB copy-move algorithm?
**Answer**: Feature detection with ORB is $O(N)$ where $N$ is the number of pixels. Descriptor matching using brute-force matching on $K$ extracted keypoints is $O(K^2 \cdot \text{descriptor\_length})$. Because ORB uses binary descriptors (256 bits), Hamming distance is computed using fast bitwise XOR and popcount instructions in hardware, running in just a fraction of a second on standard CPUs.

### Q12: Why did you choose FastAPI over Flask or Django?
**Answer**: FastAPI provides superior asynchronous I/O performance, automatic OpenAPI documentation, clean dependency injection, and automatic thread pool delegation for CPU-bound tasks (`def` routes run automatically on separate worker threads without blocking the event loop). It is lightweight, modern, and easily containerizable.

### Q13: How does the Tampering Probability Index combine diverse metrics?
**Answer**: The engine computes weighted raw points based on the severity and confidence of each test:
- Metadata manipulation tool tag: up to 25 pts
- ELA localized high-error clusters: up to 25 pts
- Copy-move clone clusters: up to 30 pts
- PRNU noise heterogeneity: up to 20 pts
- 2D FFT harmonic peaks: up to 15 pts
- Appended trailing payload (carving): up to 30 pts
- Steganography LSB $\chi^2$ confidence: up to 20 pts
- Illumination conflict: up to 15 pts
The sum is normalized to a $0 - 100\%$ scale, with three clearly defined risk bands and itemized rationale bullets explaining each score.

### Q14: How does VeriPix ensure court-admissibility of its forensic reports?
**Answer**: The report generator conforms to ISO/IEC 27037 standards by recording:
1. Unique Case Reference ID and Investigator Name.
2. Evidence identification: exact byte size and cryptographic hashes (MD5, SHA-1, SHA-256).
3. Full audit table with quantitative, reproducible statistical metrics.
4. High-resolution visual evidence plates (Original, ELA, Clone vectors, Noise, FFT).
5. Formal examiner attestation and cryptographic verification token.

### Q15: What are the main limitations and how can they be addressed in future work?
**Answer**: 
1. Highly compressed images (e.g. repeated WhatsApp resaves) lose high-frequency noise details, making sensor PRNU extraction harder.
2. Generative AI deepfakes that alter semantic structure rather than splicing patches require deep learning classifiers.
3. Future enhancements will incorporate Vision Transformer (ViT) deepfake classifiers and support C2PA Content Authenticity metadata standards.
