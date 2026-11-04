"""Capability adapters + OpenRouter adapter, Phase 0.
Every AI call MUST go through OpenRouterAdapter.call() so it is metered in the
credit ledger and logged to CRM. Direct provider calls elsewhere are a bug.
Providers are swappable by replacing one adapter class, not by editing pipeline code.

Credit table (spec, amounts set from actual provider pricing — these are
PLACEHOLDER tiers for the proof, not prices): vision=low, video=medium, avatar=high,
music/voicebox=0 (free to run per spec: editing, rendering, Voicebox voice are free).
Admin bypasses blocking, but metering/logging still happen.
"""
import json, urllib.request

class OpenRouterAdapter:
    def __init__(self, cfg, crm_log):
        self.cfg, self.crm_log = cfg, crm_log
    def call(self, capability, model, payload, estimated_credits=0, user_id=None, job_id=None):
        """Dry-run when no API key is set: records the call, spends 0, returns no
        generated media. With a key set, this is the ONLY place that hits OpenRouter.
        Real model pricing must replace estimated_credits before public launch."""
        from .crm import log_event
        if not self.cfg.openrouter_api_key:
            log_event(self.crm_log, "ai_call_dry_run", user_id=user_id, capability=capability,
                      model=model, job_id=str(job_id) if job_id else None, credits=0)
            return {"dry_run": True, "capability": capability, "model": model, "credits": 0}
        # Minimal live path (no key is present in the VM proof, so this is untested live).
        req = urllib.request.Request(self.cfg.openrouter_base + "/chat/completions",
            data=json.dumps({"model": model, "messages": [{"role": "user", "content": json.dumps(payload)}]}).encode(),
            headers={"Authorization": f"Bearer {self.cfg.openrouter_api_key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            out = json.loads(r.read().decode())
        log_event(self.crm_log, "ai_call", user_id=user_id, capability=capability,
                  model=model, job_id=str(job_id) if job_id else None, credits=estimated_credits)
        return {"dry_run": False, "result": out, "credits": estimated_credits}

class VisionAdapter:
    """Tags shots, scores sharpness/lighting/motion, transcribes via Voicebox STT in prod.
    Proof implementation: deterministic tags from payload (no model call) so the
    pipeline shape can be tested without spend. Replace with OpenRouter vision call."""
    def __init__(self, router): self.router = router
    def analyze(self, asset, user_id=None, job_id=None):
        return {"shot_tags": {"type": asset.get("type_hint", "unknown")}, "sharpness": None, "note": "proof adapter: replace with vision model call via OpenRouterAdapter"}

class VideoAdapter:
    """FFmpeg rendering is free per spec. Generative video goes via OpenRouterAdapter
    and is BLOCKED for tattoo detail by the template layer (see Phase 1) — this
    adapter must never be called with a tattoo template + generative=True."""
    def __init__(self, router): self.router = router
    def photo_motion(self, src, out, motion="slow_push"):
        import subprocess
        # Ken Burns-style zoompan, 9:16 proof render. Real recipe timing is Phase 1.
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", src, "-vf",
               "scale=1080:1920,zoompan=z='min(zoom+0.0015,1.3)':d=125:s=1080x1920",
               "-t", "5", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return out
    def photo_motion_multi(self, sources, out, durations):
        """Step 6: one 9:16 video from 3-6 photos, one zoompan segment per photo.
        Each segment is rendered to a temp clip at 30fps, then concatenated
        with the concat demuxer (same codec, same size, so no re-encode loss
        beyond the first pass). Returns out. No generative model is called:
        this is photo-motion from real photos only."""
        import os, subprocess, tempfile
        if not (3 <= len(sources) <= 6):
            raise ValueError(f"photo_motion_multi needs 3-6 sources, got {len(sources)}")
        if len(durations) != len(sources):
            raise ValueError("durations must match sources")
        with tempfile.TemporaryDirectory() as tmp:
            clips = []
            for idx, (src, dur) in enumerate(zip(sources, durations)):
                clip = os.path.join(tmp, f"seg{idx}.mp4")
                frames = max(1, int(round(float(dur) * 30)))
                cmd = ["ffmpeg", "-y", "-loop", "1", "-i", src, "-vf",
                       f"scale=1080:1920,zoompan=z='min(zoom+0.0015,1.3)':d={frames}:s=1080x1920:fps=30",
                       "-t", str(float(dur)), "-c:v", "libx264", "-pix_fmt", "yuv420p", clip]
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                clips.append(clip)
            lst = os.path.join(tmp, "list.txt")
            with open(lst, "w") as f:
                for c in clips:
                    f.write(f"file '{c}'\n")
            cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                   "-c", "copy", "-movflags", "+faststart", out]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        return out

class AvatarAdapter:
    def __init__(self, router): self.router = router
    def generate(self, *a, **k):
        raise RuntimeError("Avatar generation is Phase 5+, not Phase 0/1. Consent flow must be built first; do not call this in Phase 0/1.")

class MusicAdapter:
    """Royalty-free / Voicebox music only. No copyrighted tracks bundled. Composer
    (Suno/Udio-style) is a later phase and needs a provider with commercial-use API terms."""
    def __init__(self, router): self.router = router
    def pick(self, mood):
        return {"mood": mood, "source": "starter royalty-free library (to be approved by Matt)", "credits": 0}
