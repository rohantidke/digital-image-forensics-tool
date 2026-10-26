import os
import sqlite3
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "forensics.db")

def get_db_connection():
    """Create a connection to the SQLite forensics database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables for persistent investigation tracking."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS investigations (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_size_formatted TEXT,
                file_size_bytes INTEGER,
                dimensions TEXT,
                format TEXT,
                sha256 TEXT NOT NULL,
                md5 TEXT NOT NULL,
                phash TEXT,
                status TEXT NOT NULL,
                status_label TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                findings_json TEXT NOT NULL,
                thumbnail_b64 TEXT
            )
        """)
        conn.commit()

def save_investigation(results: dict) -> str:
    """Save an analyzed investigation into persistent storage."""
    init_db()
    meta = results.get("metadata", {})
    scoring = results.get("scoring", {})
    props = results.get("properties", {})

    inv_id = results.get("investigation_id")
    if not inv_id:
        now_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        inv_id = f"INV-{now_str}-{meta.get('hashes', {}).get('sha256', '')[:6].upper()}"
        results["investigation_id"] = inv_id

    dim_str = f"{meta.get('dimensions', [0,0])[0]}x{meta.get('dimensions', [0,0])[1]}"
    
    # Store clean JSON representation (strip heavy channel view base64 strings from JSON cache to save space)
    clean_copy = dict(results)
    if "original_image_base64" in clean_copy:
        # Keep original image preview in findings
        pass

    with get_db_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO investigations (
                id, filename, file_size_formatted, file_size_bytes, dimensions,
                format, sha256, md5, phash, status, status_label,
                risk_score, created_at, findings_json, thumbnail_b64
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inv_id,
            meta.get("filename", "suspect.jpg"),
            meta.get("file_size_formatted", "0 KB"),
            meta.get("file_size_bytes", 0),
            dim_str,
            meta.get("format", "Unknown"),
            meta.get("hashes", {}).get("sha256", "N/A"),
            meta.get("hashes", {}).get("md5", "N/A"),
            props.get("perceptual_hash", ""),
            scoring.get("status", "INCONCLUSIVE"),
            scoring.get("status_label", "Inconclusive"),
            scoring.get("tamper_score", 0),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            json.dumps(clean_copy),
            results.get("thumbnail_base64") or clean_copy.get("original_image_base64")
        ))
        conn.commit()

    return inv_id

def get_investigations(limit: int = 50, search: str = "", status_filter: str = "") -> list:
    """Query past investigations with optional search and filter."""
    init_db()
    query = "SELECT id, filename, file_size_formatted, dimensions, format, sha256, phash, status, status_label, risk_score, created_at, thumbnail_b64 FROM investigations WHERE 1=1"
    params = []

    if search:
        query += " AND (filename LIKE ? OR sha256 LIKE ? OR id LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

def get_investigation_by_id(inv_id: str) -> dict:
    """Retrieve full investigation data by ID."""
    init_db()
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM investigations WHERE id = ?", (inv_id,)).fetchone()
        if not row:
            return None
        res = dict(row)
        res["findings"] = json.loads(res["findings_json"])
        return res

def delete_investigation(inv_id: str) -> bool:
    """Delete an investigation record."""
    init_db()
    with get_db_connection() as conn:
        cur = conn.execute("DELETE FROM investigations WHERE id = ?", (inv_id,))
        conn.commit()
        return cur.rowcount > 0

def get_dashboard_stats() -> dict:
    """Compute aggregate dashboard metrics from actual stored database records."""
    init_db()
    with get_db_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM investigations").fetchone()[0]
        flagged = conn.execute("SELECT COUNT(*) FROM investigations WHERE status = 'POTENTIAL_ANOMALY'").fetchone()[0]
        inconclusive = conn.execute("SELECT COUNT(*) FROM investigations WHERE status = 'INCONCLUSIVE'").fetchone()[0]
        no_anomaly = conn.execute("SELECT COUNT(*) FROM investigations WHERE status = 'NO_ANOMALY'").fetchone()[0]

        recent_rows = conn.execute("""
            SELECT id, filename, file_size_formatted, dimensions, format, sha256, status, status_label, risk_score, created_at 
            FROM investigations ORDER BY created_at DESC LIMIT 5
        """).fetchall()

        return {
            "total_analyzed": total,
            "potential_anomalies": flagged,
            "inconclusive": inconclusive,
            "no_anomaly_detected": no_anomaly,
            "recent_investigations": [dict(r) for r in recent_rows]
        }
