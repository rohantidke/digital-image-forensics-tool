// VeriPix Professional Digital Forensic Suite - Interactive Application Controller

let currentAnalysis = null;
let currentZoom = 1.0;
let currentBitPlaneData = { chan: "R", bit: "0" };
let compareFiles = { fileA: null, fileB: null };

document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initUploadWorkspace();
    initSplitSlider();
    initComparator();
    initHistory();
    initPresets();
    loadDashboardStats();
});

// ----------------- View Navigation -----------------
function initNavigation() {
    const navItems = document.querySelectorAll(".sidebar-nav .nav-item");
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const targetView = item.getAttribute("data-view");
            switchView(targetView);
        });
    });

    const toggleBtn = document.getElementById("btnToggleSidebar");
    if (toggleBtn) {
        toggleBtn.addEventListener("click", () => {
            document.getElementById("sidebar").classList.toggle("collapsed");
        });
    }

    const btnNew = document.getElementById("btnTopNewInvestigation");
    if (btnNew) {
        btnNew.addEventListener("click", () => {
            switchView("view-workspace");
        });
    }
}

function switchView(viewId) {
    document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => {
        if (item.getAttribute("data-view") === viewId) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });

    document.querySelectorAll(".view-panel").forEach(panel => {
        panel.classList.remove("active");
    });

    const targetPanel = document.getElementById(viewId);
    if (targetPanel) {
        targetPanel.classList.add("active");
    }

    // Update breadcrumb
    const breadcrumb = document.getElementById("breadcrumbCurrent");
    const titles = {
        "view-dashboard": "Forensic Operations Dashboard",
        "view-workspace": "Investigation & Evidence Laboratory",
        "view-comparator": "Dual Specimen Hash & Image Comparator",
        "view-history": "Investigation Case Archive & Audit Log"
    };
    if (breadcrumb && titles[viewId]) {
        breadcrumb.textContent = titles[viewId];
    }

    // Refresh data if switching to dashboard or history
    if (viewId === "view-dashboard") {
        loadDashboardStats();
    } else if (viewId === "view-history") {
        loadHistory();
    }
}

// ----------------- Dashboard Controller -----------------
async function loadDashboardStats() {
    try {
        const resp = await fetch("/api/stats");
        if (!resp.ok) return;
        const stats = await resp.json();

        document.getElementById("statTotalAnalyzed").textContent = stats.total_analyzed;
        document.getElementById("statPotentialAnomalies").textContent = stats.potential_anomalies;
        document.getElementById("statInconclusive").textContent = stats.inconclusive;
        document.getElementById("statNoAnomaly").textContent = stats.no_anomaly_detected;
        document.getElementById("topbarTotalCases").textContent = stats.total_analyzed;

        renderRecentTable(stats.recent_investigations || []);
    } catch (e) {
        console.error("Dashboard stats error:", e);
    }
}

function renderRecentTable(records) {
    const tbody = document.getElementById("dashboardRecentTbody");
    if (!tbody) return;

    if (records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted" style="padding: 2rem;">No investigations recorded yet. Click 'Start New Examination' to analyze an image.</td></tr>`;
        return;
    }

    tbody.innerHTML = "";
    records.forEach(r => {
        const tr = document.createElement("tr");

        let badgeClass = "badge-no-anomaly";
        if (r.status === "POTENTIAL_ANOMALY") badgeClass = "badge-potential";
        else if (r.status === "INCONCLUSIVE") badgeClass = "badge-inconclusive";

        tr.innerHTML = `
            <td><b>${escapeHtml(r.id)}</b></td>
            <td>${escapeHtml(r.filename)}</td>
            <td>${escapeHtml(r.dimensions || "-")} (${escapeHtml(r.format || "-")})</td>
            <td><code title="${escapeHtml(r.sha256)}">${escapeHtml(r.sha256.substring(0, 14))}...</code></td>
            <td><span class="status-pill-table ${badgeClass}">${escapeHtml(r.status_label)}</span></td>
            <td><b>${r.risk_score}%</b></td>
            <td>${escapeHtml(r.created_at)}</td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="openCaseDetails('${escapeHtml(r.id)}')">
                    <i class="fa-solid fa-folder-open"></i> Open
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// ----------------- Investigation Workspace -----------------
function initUploadWorkspace() {
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");

    dropZone.addEventListener("click", () => fileInput.click());

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleFileUpload(fileInput.files[0]);
        }
    });

    // Zoom Controls
    document.getElementById("btnZoomIn").addEventListener("click", () => {
        currentZoom = Math.min(3.0, currentZoom + 0.2);
        applyZoom();
    });

    document.getElementById("btnZoomOut").addEventListener("click", () => {
        currentZoom = Math.max(0.5, currentZoom - 0.2);
        applyZoom();
    });

    document.getElementById("btnZoomReset").addEventListener("click", () => {
        currentZoom = 1.0;
        applyZoom();
    });

    // Color Channel Switcher
    document.querySelectorAll(".btn-chan").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".btn-chan").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            applyChannelFilter(btn.getAttribute("data-filter"));
        });
    });

    // Execute Analysis
    document.getElementById("btnExecuteAnalysis").addEventListener("click", () => {
        if (currentAnalysis) {
            document.getElementById("resultsDashboard").scrollIntoView({ behavior: "smooth" });
        }
    });

    // ELA Recompute
    const sliderQ = document.getElementById("sliderQuality");
    const sliderS = document.getElementById("sliderScale");
    sliderQ.addEventListener("input", () => {
        document.getElementById("lblQuality").textContent = `${sliderQ.value}%`;
    });
    sliderS.addEventListener("input", () => {
        document.getElementById("lblScale").textContent = `${sliderS.value}x`;
    });

    document.getElementById("btnRecomputeEla").addEventListener("click", () => {
        recomputeEla(parseInt(sliderQ.value), parseInt(sliderS.value));
    });

    // Stego Bit Plane buttons
    document.querySelectorAll("[data-chan]").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll("[data-chan]").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentBitPlaneData.chan = btn.getAttribute("data-chan");
            updateBitPlaneView();
        });
    });

    document.querySelectorAll("[data-bit]").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll("[data-bit]").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentBitPlaneData.bit = btn.getAttribute("data-bit");
            updateBitPlaneView();
        });
    });

    // EXIF Search
    const exifSearch = document.getElementById("exifSearch");
    if (exifSearch) {
        exifSearch.addEventListener("input", (e) => {
            const filter = e.target.value.toLowerCase();
            const rows = document.querySelectorAll("#exifTableBody tr");
            rows.forEach(r => {
                r.style.display = r.textContent.toLowerCase().includes(filter) ? "" : "none";
            });
        });
    }

    // Modal PDF & JSON export
    initExportModals();
}

function applyZoom() {
    const img = document.getElementById("workspaceImagePreview");
    if (img) {
        img.style.transform = `scale(${currentZoom})`;
    }
}

function applyChannelFilter(filterType) {
    if (!currentAnalysis || !currentAnalysis.properties) return;
    const views = currentAnalysis.properties.channel_views || {};
    const img = document.getElementById("workspaceImagePreview");

    switch (filterType) {
        case "red":
            if (views.red_channel_b64) img.src = views.red_channel_b64;
            break;
        case "green":
            if (views.green_channel_b64) img.src = views.green_channel_b64;
            break;
        case "blue":
            if (views.blue_channel_b64) img.src = views.blue_channel_b64;
            break;
        case "gray":
            if (views.grayscale_b64) img.src = views.grayscale_b64;
            break;
        default:
            img.src = currentAnalysis.original_image_base64;
            break;
    }
}

async function handleFileUpload(file) {
    showLoading("Validating & Ingesting Digital Evidence", "Checking file signatures, computing SHA-256, and executing forensic modules...");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("ela_quality", 95);
    formData.append("ela_scale", 25);

    try {
        const resp = await fetch("/api/analyze", {
            method: "POST",
            body: formData
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || "Upload analysis failed");
        }

        const data = await resp.json();
        renderAnalysisResults(data);
        loadDashboardStats(); // Refresh DB stats
    } catch (err) {
        alert("Forensic Ingestion Error: " + err.message);
    } finally {
        hideLoading();
    }
}

function renderAnalysisResults(data) {
    currentAnalysis = data;
    document.getElementById("workspaceActiveArea").style.display = "block";
    document.getElementById("resultsDashboard").style.display = "block";

    const meta = data.metadata;
    const props = data.properties || {};
    const score = data.scoring;
    const ela = data.ela;
    const cm = data.copy_move;
    const noise = data.noise;
    const freq = data.frequency;
    const lum = data.luminance;
    const stego = data.stego;
    const carve = data.carving;

    // Viewport preview & title
    document.getElementById("viewerFilenameTitle").textContent = `${data.filename} (${meta.dimensions[0]}x${meta.dimensions[1]})`;
    document.getElementById("workspaceImagePreview").src = data.original_image_base64;
    currentZoom = 1.0;
    applyZoom();

    // Reset color channel buttons to RGB
    document.querySelectorAll(".btn-chan").forEach(b => b.classList.remove("active"));
    const rgbBtn = document.querySelector(".btn-chan[data-filter='rgb']");
    if (rgbBtn) rgbBtn.classList.add("active");

    // Properties panel
    document.getElementById("propFilename").textContent = data.filename;
    document.getElementById("propDimensions").textContent = `${meta.dimensions[0]} x ${meta.dimensions[1]} px`;
    document.getElementById("propAspect").textContent = props.aspect_ratio || "-";
    document.getElementById("propMegapixels").textContent = `${props.megapixels || meta.megapixels} MP`;
    document.getElementById("propSize").textContent = meta.file_size_formatted;
    document.getElementById("propColorMode").textContent = meta.color_mode;
    document.getElementById("propSha256").textContent = meta.hashes.sha256;
    document.getElementById("propDhash").textContent = props.perceptual_hash || "-";

    // Render Histograms
    renderHistograms(props.histograms || {});

    // Verdict Banner
    const invId = data.investigation_id || "INV-NEW";
    document.getElementById("caseRefBadge").textContent = `CASE ID: ${invId}`;
    document.getElementById("verdictTitle").textContent = score.status_label || score.verdict;

    const pill = document.getElementById("verdictPill");
    pill.textContent = score.status_label;
    pill.style.backgroundColor = `${score.status_color}22`;
    pill.style.color = score.status_color;
    pill.style.border = `1px solid ${score.status_color}`;

    document.getElementById("verdictSummaryText").textContent = score.summary || score.recommendation;

    // Radial Gauge
    const scoreVal = score.tamper_score;
    const gauge = document.getElementById("radialGauge");
    gauge.style.background = `conic-gradient(${score.status_color} ${scoreVal}%, #1a253a ${scoreVal}%)`;
    document.getElementById("gaugeValue").textContent = `${scoreVal}%`;

    // Observed Facts
    const factsList = document.getElementById("observedFactsList");
    factsList.innerHTML = "";
    (score.observed_facts || score.evidence_summary || []).forEach(f => {
        const li = document.createElement("li");
        li.textContent = f;
        factsList.appendChild(li);
    });

    // Split Slider
    document.getElementById("splitOriginalImg").src = data.original_image_base64;
    updateSplitOverlayImage();

    // Tab 1: ELA
    document.getElementById("elaImg").src = ela.ela_image_base64;
    document.getElementById("elaHeatImg").src = ela.heatmap_image_base64;
    document.getElementById("elaMean").textContent = ela.mean_error;
    document.getElementById("elaMax").textContent = ela.max_error;
    document.getElementById("elaStd").textContent = ela.std_deviation;
    document.getElementById("elaArea").textContent = `${ela.anomaly_percentage}% (${ela.suspicious_region_count} hot spots)`;

    // Tab 2: Copy-Move
    document.getElementById("cmImg").src = cm.annotated_image_base64;
    document.getElementById("cmStatus").textContent = cm.forgery_detected ? "Cloning Confirmed" : "Clean";
    document.getElementById("cmStatus").style.color = cm.forgery_detected ? "var(--accent-red)" : "var(--accent-green)";
    document.getElementById("cmKeypoints").textContent = cm.total_keypoints;
    document.getElementById("cmPairs").textContent = cm.matched_pairs_count;
    document.getElementById("cmClusters").textContent = cm.clone_clusters_count;
    document.getElementById("cmCallout").textContent = cm.notes.join(" ");

    // Tab 3: Noise
    document.getElementById("noiseResImg").src = noise.noise_residual_base64;
    document.getElementById("noiseHeatImg").src = noise.noise_heatmap_base64;
    document.getElementById("noiseMean").textContent = noise.mean_noise_variance;
    document.getElementById("noiseStd").textContent = noise.variance_std;
    document.getElementById("noiseCv").textContent = noise.coefficient_of_variation;
    document.getElementById("noiseBlocks").textContent = `${noise.abnormal_block_percentage}%`;
    document.getElementById("noiseCallout").textContent = noise.notes.join(" ");

    // Tab 4: 2D FFT
    document.getElementById("fftImg").src = freq.spectrum_image_base64;
    document.getElementById("fftLow").textContent = `${freq.low_frequency_energy_pct}%`;
    document.getElementById("fftMid").textContent = `${freq.mid_frequency_energy_pct}%`;
    document.getElementById("fftHigh").textContent = `${freq.high_frequency_energy_pct}%`;
    document.getElementById("fftPeaks").textContent = freq.periodic_peaks_detected;
    document.getElementById("fftCallout").textContent = freq.notes.join(" ");

    // Tab 5: Luminance
    document.getElementById("lumImg").src = lum.gradient_image_base64;
    document.getElementById("lumTL").textContent = `${lum.quadrant_directions["Top-Left"]}°`;
    document.getElementById("lumTR").textContent = `${lum.quadrant_directions["Top-Right"]}°`;
    document.getElementById("lumBL").textContent = `${lum.quadrant_directions["Bottom-Left"]}°`;
    document.getElementById("lumBR").textContent = `${lum.quadrant_directions["Bottom-Right"]}°`;
    document.getElementById("lumDiv").textContent = `${lum.max_lateral_divergence_deg || lum.max_angular_divergence_deg}°`;
    document.getElementById("lumCallout").textContent = lum.notes.join(" ");

    // Tab 6: Stego
    document.getElementById("stegoEntropy").textContent = stego.avg_lsb_entropy;
    document.getElementById("stegoProb").textContent = `${stego.chi_square_tests.max_stego_probability || stego.chi_square_tests.average_stego_probability}%`;
    document.getElementById("stegoDisparity").textContent = stego.chi_square_tests.blue ? stego.chi_square_tests.blue.disparity_ratio : "N/A";
    document.getElementById("stegoCallout").textContent = stego.notes.join(" ");
    updateBitPlaneView();

    // Tab 7: EXIF
    const exifTbody = document.getElementById("exifTableBody");
    exifTbody.innerHTML = "";
    const exifTags = meta.exif || {};
    const tagKeys = Object.keys(exifTags);

    if (tagKeys.length === 0) {
        exifTbody.innerHTML = `<tr><td colspan="2" style="color:var(--text-muted);">No camera EXIF metadata found in container headers.</td></tr>`;
    } else {
        tagKeys.sort().forEach(t => {
            const tr = document.createElement("tr");
            tr.innerHTML = `<td style="font-weight:600; color:var(--accent-cyan);">${escapeHtml(t)}</td><td>${escapeHtml(String(exifTags[t]))}</td>`;
            exifTbody.appendChild(tr);
        });
    }

    const gpsAlert = document.getElementById("gpsAlertBox");
    if (meta.gps) {
        gpsAlert.style.display = "flex";
        document.getElementById("gpsCoordsText").textContent = `${meta.gps.latitude}, ${meta.gps.longitude}`;
        document.getElementById("btnGpsMap").href = meta.gps.map_url;
    } else {
        gpsAlert.style.display = "none";
    }

    // Tab 8: Carving
    document.getElementById("carveEof").textContent = carve.eof_marker_offset > 0 ? `0x${carve.eof_marker_offset.toString(16).toUpperCase()} (${carve.eof_marker_offset} B)` : "N/A";
    document.getElementById("carveTrailing").textContent = `${carve.trailing_payload_bytes} bytes`;
    document.getElementById("carvePayload").textContent = carve.detected_payload_type || "None";
    document.getElementById("hexViewer").textContent = carve.trailing_hex_dump || "No trailing bytes appended beyond format terminator.";

    const stringsChips = document.getElementById("stringsChips");
    stringsChips.innerHTML = "";
    (carve.extracted_strings_sample || []).forEach(s => {
        const span = document.createElement("span");
        span.className = "string-chip";
        span.textContent = s;
        stringsChips.appendChild(span);
    });

    // Scroll smoothly to results
    document.getElementById("resultsDashboard").scrollIntoView({ behavior: "smooth" });
}

function renderHistograms(histData) {
    const lumBox = document.getElementById("histLum");
    const rgbBox = document.getElementById("histRgb");
    if (!lumBox || !rgbBox) return;

    lumBox.innerHTML = "";
    rgbBox.innerHTML = "";

    const lumValues = histData.luminance || [];
    lumValues.forEach(val => {
        const bar = document.createElement("div");
        bar.className = "hist-bar";
        bar.style.height = `${val}%`;
        bar.style.backgroundColor = "#e2e8f0";
        lumBox.appendChild(bar);
    });

    const rValues = histData.red || [];
    const gValues = histData.green || [];
    const bValues = histData.blue || [];

    for (let i = 0; i < rValues.length; i++) {
        const avg = ((rValues[i] || 0) + (gValues[i] || 0) + (bValues[i] || 0)) / 3;
        const bar = document.createElement("div");
        bar.className = "hist-bar";
        bar.style.height = `${avg}%`;
        bar.style.backgroundColor = "#38bdf8";
        rgbBox.appendChild(bar);
    }
}

// ----------------- Split Slider Controller -----------------
function initSplitSlider() {
    const container = document.getElementById("sliderContainer");
    const overlay = document.getElementById("splitOverlay");
    const handle = document.getElementById("sliderHandle");
    let isDragging = false;

    const setPosition = (clientX) => {
        const rect = container.getBoundingClientRect();
        let x = clientX - rect.left;
        if (x < 0) x = 0;
        if (x > rect.width) x = rect.width;
        const pct = (x / rect.width) * 100;
        overlay.style.width = `${pct}%`;
        handle.style.left = `${pct}%`;
    };

    container.addEventListener("mousedown", (e) => {
        isDragging = true;
        setPosition(e.clientX);
    });

    window.addEventListener("mousemove", (e) => {
        if (!isDragging) return;
        setPosition(e.clientX);
    });

    window.addEventListener("mouseup", () => {
        isDragging = false;
    });

    container.addEventListener("touchstart", (e) => {
        isDragging = true;
        if (e.touches.length > 0) setPosition(e.touches[0].clientX);
    });

    window.addEventListener("touchmove", (e) => {
        if (!isDragging || e.touches.length === 0) return;
        setPosition(e.touches[0].clientX);
    });

    window.addEventListener("touchend", () => {
        isDragging = false;
    });

    document.getElementById("overlaySelector").addEventListener("change", updateSplitOverlayImage);

    // Tab bar listener
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            btn.classList.add("active");
            document.getElementById(btn.getAttribute("data-tab")).classList.add("active");
        });
    });
}

function updateSplitOverlayImage() {
    if (!currentAnalysis) return;
    const sel = document.getElementById("overlaySelector").value;
    const overlayImg = document.getElementById("splitForensicImg");
    const tagText = document.getElementById("overlayTagText");

    let src = "";
    let label = "";

    switch (sel) {
        case "ela_heat":
            src = currentAnalysis.ela.heatmap_image_base64;
            label = "ELA THERMAL HEATMAP";
            break;
        case "copymove":
            src = currentAnalysis.copy_move.annotated_image_base64;
            label = "COPY-MOVE CLONES";
            break;
        case "noise_heat":
            src = currentAnalysis.noise.noise_heatmap_base64;
            label = "NOISE VARIANCE";
            break;
        case "noise_res":
            src = currentAnalysis.noise.noise_residual_base64;
            label = "NOISE RESIDUAL";
            break;
        case "luminance":
            src = currentAnalysis.luminance.gradient_image_base64;
            label = "LUMINANCE GRADIENT";
            break;
        case "fft":
            src = currentAnalysis.frequency.spectrum_image_base64;
            label = "2D FFT SPECTRUM";
            break;
    }

    overlayImg.src = src;
    tagText.textContent = label;
}

function updateBitPlaneView() {
    if (!currentAnalysis || !currentAnalysis.stego) return;
    const key = `${currentBitPlaneData.chan}_bit${currentBitPlaneData.bit}`;
    const planes = currentAnalysis.stego.bit_planes_preview || {};
    const imgEl = document.getElementById("bitPlaneImg");
    const titleEl = document.getElementById("planeTitle");

    const chanName = currentBitPlaneData.chan === "R" ? "Red" : (currentBitPlaneData.chan === "G" ? "Green" : "Blue");
    const bitDesc = currentBitPlaneData.bit === "0" ? "Bit 0 (Least Significant Bit - LSB)" : "Bit 7 (Most Significant Bit - MSB)";

    titleEl.textContent = `${chanName} Channel - ${bitDesc}`;
    if (planes[key]) {
        imgEl.src = planes[key];
    }
}

async function recomputeEla(quality, scaleFactor) {
    showLoading("Recomputing Error Level Analysis", `Applying ${quality}% JPEG quality & ${scaleFactor}x difference scaling...`);
    const formData = new FormData();
    formData.append("quality", quality);
    formData.append("scale_factor", scaleFactor);

    try {
        const resp = await fetch("/api/recompute-ela", {
            method: "POST",
            body: formData
        });
        if (!resp.ok) throw new Error("Recomputation failed");
        const newEla = await resp.json();

        currentAnalysis.ela = newEla;
        document.getElementById("elaImg").src = newEla.ela_image_base64;
        document.getElementById("elaHeatImg").src = newEla.heatmap_image_base64;
        document.getElementById("elaMean").textContent = newEla.mean_error;
        document.getElementById("elaMax").textContent = newEla.max_error;
        document.getElementById("elaStd").textContent = newEla.std_deviation;
        document.getElementById("elaArea").textContent = `${newEla.anomaly_percentage}% (${newEla.suspicious_region_count} hot spots)`;

        if (document.getElementById("overlaySelector").value === "ela_heat") {
            updateSplitOverlayImage();
        }
    } catch (err) {
        alert("Recomputation error: " + err.message);
    } finally {
        hideLoading();
    }
}

// ----------------- Comparator Controller -----------------
function initComparator() {
    const dropA = document.getElementById("dropA");
    const dropB = document.getElementById("dropB");
    const fileA = document.getElementById("fileA");
    const fileB = document.getElementById("fileB");

    dropA.addEventListener("click", () => fileA.click());
    dropB.addEventListener("click", () => fileB.click());

    fileA.addEventListener("change", () => {
        if (fileA.files.length > 0) handleCompareFile(fileA.files[0], "A");
    });

    fileB.addEventListener("change", () => {
        if (fileB.files.length > 0) handleCompareFile(fileB.files[0], "B");
    });

    document.getElementById("btnRunComparison").addEventListener("click", executeComparison);
}

function handleCompareFile(file, side) {
    compareFiles[side === "A" ? "fileA" : "fileB"] = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById(`drop${side}`).style.display = "none";
        const wrap = document.getElementById(`previewWrap${side}`);
        wrap.style.display = "block";
        document.getElementById(`preview${side}`).src = e.target.result;
        document.getElementById(`name${side}`).textContent = file.name;
    };
    reader.readAsDataURL(file);
}

async function executeComparison() {
    if (!compareFiles.fileA || !compareFiles.fileB) {
        alert("Please load both Specimen A and Specimen B before running comparison.");
        return;
    }

    showLoading("Executing Forensic Comparison", "Calculating cryptographic hashes, dHash distance, and pixel difference matrix...");
    const formData = new FormData();
    formData.append("file1", compareFiles.fileA);
    formData.append("file2", compareFiles.fileB);

    try {
        const resp = await fetch("/api/compare", {
            method: "POST",
            body: formData
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || "Comparison failed");
        }

        const data = await resp.json();
        const cmp = data.comparison;

        document.getElementById("compareResultsArea").style.display = "block";
        document.getElementById("cmpExactVerdict").textContent = cmp.is_exact_match ? "IDENTICAL MATCH" : "NON-MATCHING";
        document.getElementById("cmpExactVerdict").style.color = cmp.is_exact_match ? "var(--accent-green)" : "var(--accent-red)";
        document.getElementById("cmpExactSub").textContent = cmp.is_exact_match ? "Cryptographic bit-for-bit duplicate" : "Cryptographically distinct files";

        document.getElementById("cmpSimilarityPct").textContent = `${cmp.perceptual_similarity_pct}%`;
        document.getElementById("cmpMeanDiff").textContent = `${cmp.mean_pixel_difference} px`;
        document.getElementById("cmpDiffHeatmap").src = cmp.diff_heatmap_b64;

        document.getElementById("compareResultsArea").scrollIntoView({ behavior: "smooth" });
    } catch (err) {
        alert("Comparison Error: " + err.message);
    } finally {
        hideLoading();
    }
}

// ----------------- Case Archive & History Controller -----------------
function initHistory() {
    const searchInput = document.getElementById("historySearch");
    const statusSelect = document.getElementById("historyStatusFilter");
    const refreshBtn = document.getElementById("btnRefreshHistory");

    if (searchInput) searchInput.addEventListener("input", debounce(loadHistory, 300));
    if (statusSelect) statusSelect.addEventListener("change", loadHistory);
    if (refreshBtn) refreshBtn.addEventListener("click", loadHistory);
}

async function loadHistory() {
    const search = document.getElementById("historySearch").value;
    const status = document.getElementById("historyStatusFilter").value;

    try {
        const url = `/api/investigations?search=${encodeURIComponent(search)}&status=${encodeURIComponent(status)}`;
        const resp = await fetch(url);
        if (!resp.ok) return;

        const data = await resp.json();
        const tbody = document.getElementById("historyTbody");
        tbody.innerHTML = "";

        const records = data.investigations || [];
        if (records.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted" style="padding: 2rem;">No historical investigations matching search criteria.</td></tr>`;
            return;
        }

        records.forEach(r => {
            const tr = document.createElement("tr");

            let badgeClass = "badge-no-anomaly";
            if (r.status === "POTENTIAL_ANOMALY") badgeClass = "badge-potential";
            else if (r.status === "INCONCLUSIVE") badgeClass = "badge-inconclusive";

            tr.innerHTML = `
                <td><b>${escapeHtml(r.id)}</b></td>
                <td>${escapeHtml(r.filename)}</td>
                <td>${escapeHtml(r.dimensions || "-")}</td>
                <td><code title="${escapeHtml(r.sha256)}">${escapeHtml(r.sha256.substring(0, 16))}...</code></td>
                <td><span class="status-pill-table ${badgeClass}">${escapeHtml(r.status_label)}</span></td>
                <td><b>${r.risk_score}%</b></td>
                <td>${escapeHtml(r.created_at)}</td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="openCaseDetails('${escapeHtml(r.id)}')">
                        <i class="fa-solid fa-folder-open"></i> Open
                    </button>
                    <a href="/api/investigations/${escapeHtml(r.id)}/json" class="btn btn-secondary btn-sm" download title="Download JSON">
                        <i class="fa-solid fa-file-code"></i>
                    </a>
                    <button class="btn btn-secondary btn-sm" onclick="deleteCase('${escapeHtml(r.id)}')" style="color:var(--accent-red);" title="Delete Record">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Load history error:", e);
    }
}

async function openCaseDetails(invId) {
    showLoading("Retrieving Case File", `Loading investigation ${invId}...`);
    try {
        const resp = await fetch(`/api/investigations/${invId}`);
        if (!resp.ok) throw new Error("Could not retrieve case details");
        const record = await resp.json();
        
        // Switch to investigation lab and render
        switchView("view-workspace");
        renderAnalysisResults(record.findings);
    } catch (err) {
        alert("Error: " + err.message);
    } finally {
        hideLoading();
    }
}

async function deleteCase(invId) {
    if (!confirm(`Are you sure you want to permanently delete investigation ${invId}?`)) return;

    try {
        const resp = await fetch(`/api/investigations/${invId}`, { method: "DELETE" });
        if (!resp.ok) throw new Error("Deletion failed");
        loadHistory();
        loadDashboardStats();
    } catch (err) {
        alert("Error deleting case: " + err.message);
    }
}

// ----------------- Preset Specimen Buttons -----------------
function initPresets() {
    document.querySelectorAll(".preset-item").forEach(btn => {
        btn.addEventListener("click", () => {
            const sampleId = btn.getAttribute("data-sample");
            loadSample(sampleId);
        });
    });
}

async function loadSample(sampleId) {
    showLoading("Ingesting Preset Evidence Specimen", `Processing specimen ${sampleId} through the forensic pipeline...`);
    try {
        const resp = await fetch(`/api/sample/${sampleId}`);
        if (!resp.ok) throw new Error("Failed to analyze sample");
        const data = await resp.json();

        switchView("view-workspace");
        renderAnalysisResults(data);
        loadDashboardStats();
    } catch (err) {
        alert("Sample Error: " + err.message);
    } finally {
        hideLoading();
    }
}

// ----------------- Export Modals (PDF & JSON) -----------------
function initExportModals() {
    const btnPdf = document.getElementById("btnExportPdf");
    const modal = document.getElementById("pdfModal");
    const btnClose = document.getElementById("btnCloseModal");
    const btnCancel = document.getElementById("btnCancelModal");
    const btnConfirm = document.getElementById("btnConfirmPdf");
    const btnJson = document.getElementById("btnDownloadJson");

    if (btnPdf) {
        btnPdf.addEventListener("click", () => {
            if (!currentAnalysis) return;
            const invId = currentAnalysis.investigation_id || "CASE-2026-9041A";
            document.getElementById("modalCaseId").value = invId;
            modal.classList.add("active");
        });
    }

    const closeModal = () => modal.classList.remove("active");
    if (btnClose) btnClose.addEventListener("click", closeModal);
    if (btnCancel) btnCancel.addEventListener("click", closeModal);

    if (btnConfirm) {
        btnConfirm.addEventListener("click", () => {
            const caseId = document.getElementById("modalCaseId").value;
            const examiner = document.getElementById("modalExaminer").value;
            downloadPdf(caseId, examiner);
            closeModal();
        });
    }

    if (btnJson) {
        btnJson.addEventListener("click", () => {
            if (!currentAnalysis) return;
            const invId = currentAnalysis.investigation_id;
            if (invId) {
                window.location.href = `/api/investigations/${invId}/json`;
            } else {
                // Direct download
                const blob = new Blob([JSON.stringify(currentAnalysis, null, 4)], { type: "application/json" });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `Forensic_Audit_${currentAnalysis.filename}.json`;
                a.click();
            }
        });
    }
}

async function downloadPdf(caseId, examiner) {
    showLoading("Generating Digital Forensic Examination Report", "Rendering cryptographic hashes, executive findings, and visual evidence plates...");
    const formData = new FormData();
    formData.append("case_id", caseId);
    formData.append("examiner", examiner);

    try {
        const resp = await fetch("/api/generate-report", {
            method: "POST",
            body: formData
        });
        if (!resp.ok) throw new Error("PDF report generation failed");

        const blob = await resp.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `Forensic_Report_${caseId || "evidence"}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (err) {
        alert("Report Error: " + err.message);
    } finally {
        hideLoading();
    }
}

// ----------------- Utility Helpers -----------------
function showLoading(title, subtitle) {
    const overlay = document.getElementById("loadingOverlay");
    document.getElementById("loadingTitle").textContent = title || "Processing Forensic Pipeline...";
    document.getElementById("loadingStatusText").textContent = subtitle || "Executing mathematical and statistical checks...";
    overlay.classList.add("active");
}

function hideLoading() {
    document.getElementById("loadingOverlay").classList.remove("active");
}

function copyText(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const txt = el.textContent.trim();
    navigator.clipboard.writeText(txt).then(() => {
        alert("Copied to clipboard: " + txt);
    });
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
