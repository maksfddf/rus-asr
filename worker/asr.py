import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import wave
from pathlib import Path

import numpy as np
import onnx_asr
import requests

URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_KEY"]
BUDGET = int(os.environ.get("BUDGET_SEC", "18000"))
CHUNK = 600
OVERLAP = 5
SILENCE = 0.004
MAX_DURATION = 4 * 3600
MAX_BYTES = 50 * 1024 * 1024
KEEP_DAYS = 7

H = {"apikey": KEY, "Authorization": "Bearer " + KEY}


def api(path, method="GET", **kw):
    r = requests.request(method, URL + path, headers={**H, **kw.pop("headers", {})}, timeout=120, **kw)
    if not r.ok:
        raise RuntimeError(f"{method} {path}: {r.status_code} {r.text[:400]}")
    return r


def claim():
    r = api("/rest/v1/rpc/claim_job", "POST", json={})
    rows = r.json()
    return rows[0] if rows else None


def patch(job_id, **kv):
    api(f"/rest/v1/jobs?id=eq.{job_id}", "PATCH", json=kv,
        headers={"Prefer": "return=minimal"})


def run(cmd):
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.decode("utf-8", "replace")[-600:])


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)], capture_output=True)
    return float(out.stdout.decode().strip() or 0)


def to_wav(src, dst):
    run(["ffmpeg", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000",
         "-c:a", "pcm_s16le", str(dst)])


def cut(src, start, length, dst):
    run(["ffmpeg", "-y", "-ss", str(start), "-t", str(length), "-i", str(src),
         "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dst)])


def loud(path):
    with wave.open(str(path), "rb") as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return float(np.sqrt(np.mean((data.astype(np.float32) / 32768.0) ** 2))) if data.size else 0.0


def join_text(parts):
    out = []
    for piece in parts:
        if not out:
            out.extend(piece.split())
            continue
        tail = [w.lower() for w in out[-12:]]
        head = piece.split()
        cut_n = 0
        for n in range(min(12, len(tail), len(head)), 0, -1):
            if tail[-n:] == [w.lower() for w in head[:n]]:
                cut_n = n
                break
        out.extend(head[cut_n:])
    return " ".join(out)


def srt_time(t):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def build_srt(segs):
    out = []
    for i, seg in enumerate(segs, 1):
        a = seg["start"]
        b = a + 6 if i == len(segs) else min(segs[i]["start"], a + 15)
        out.append(f"{i}\n{srt_time(a)} --> {srt_time(max(b, a + 0.5))}\n{seg['text']}\n")
    return "\n".join(out)


def cleanup():
    try:
        keep = {r["storage_path"] for r in api("/rest/v1/jobs?select=storage_path&status=in.(queued,running)").json()}
        objs = api("/storage/v1/object/list/audio", "POST",
                   json={"prefix": "", "limit": 1000, "sortBy": {"column": "created_at", "order": "asc"}}).json()
        now = time.time()
        for o in objs:
            name = o.get("name")
            if not name or name in keep:
                continue
            ts = o.get("created_at") or ""
            try:
                t = time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
            except ValueError:
                continue
            if now - t > KEEP_DAYS * 86400:
                api(f"/storage/v1/object/audio/{name}", "DELETE")
                print("drop", name, flush=True)
    except Exception as e:
        print("cleanup skipped", e, flush=True)


def process(model, job, workdir):
    job_id = job["id"]
    src = workdir / ("src" + Path(job["storage_path"]).suffix)
    r = requests.get(f"{URL}/storage/v1/object/audio/{job['storage_path']}", headers=H, timeout=300)
    if not r.ok:
        raise RuntimeError("download " + r.text[:200])
    src.write_bytes(r.content)
    if len(r.content) > MAX_BYTES:
        raise RuntimeError("file above 50 MB")

    wav = workdir / "full.wav"
    to_wav(src, wav)
    total = duration(wav)
    if total > MAX_DURATION:
        raise RuntimeError("audio above 4 hours")
    patch(job_id, duration_s=total)

    step = CHUNK - OVERLAP
    parts, segs = [], []
    start = 0.0
    while start < total:
        piece = workdir / f"{len(segs):05d}.wav"
        cut(wav, start, min(CHUNK, total - start), piece)
        if loud(piece) >= SILENCE:
            text = model.recognize(str(piece)).strip()
            if text:
                parts.append(text)
                segs.append({"start": round(start, 3), "text": text})
        start += step

    text = join_text(parts)
    patch(job_id, status="done", text=text, srt=build_srt(segs), finished_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    api(f"/storage/v1/object/audio/{job['storage_path']}", "DELETE")


def main():
    model = onnx_asr.load_model("gigaam-v3-e2e-ctc", providers=["CPUExecutionProvider"])
    cleanup()
    started = time.time()
    while time.time() - started < BUDGET:
        job = claim()
        if not job:
            print("queue empty")
            return
        print("job", job["id"], flush=True)
        workdir = Path(tempfile.mkdtemp())
        try:
            process(model, job, workdir)
            print("done", job["id"], flush=True)
        except Exception as e:
            patch(job["id"], status="error", error=str(e)[:800],
                  finished_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            print("error", job["id"], e, flush=True)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
