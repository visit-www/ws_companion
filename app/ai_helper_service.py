import json
import hashlib
import logging
import re
from types import SimpleNamespace
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from flask import current_app

import requests

from sqlalchemy import or_

from .ai_clients import call_openai_chat, call_gemini_chat, call_qubrid_deepseek
from .models import SmartHelperCard, SmartHelperSectionEnum, SmartHelperKindEnum
from . import db

logger = logging.getLogger(__name__)

# Heuristics to avoid noisy generations
STOPLIST_TOKENS = {
    # Generic stopwords / boilerplate that should not trigger AI
    "the", "and", "with", "for", "of", "in", "on", "at", "to", "a", "an",
    "is", "are", "be", "being", "been", "from", "by", "about", "into", "per",
    # Reporting boilerplate
    "patient", "exam", "study", "surgery", "history", "note", "report",
    "impression", "recommendation", "comparison", "technique", "findings",
    # Editor/template noise
    "template", "section", "paragraph", "example", "sample", "text",
}

# Allowlist for high-value clinical tokens even if short
ALLOWLIST_TOKENS = {
    # Core imaging terms
    "ct", "cta", "ctpa", "mri", "mr", "mra", "xr", "us", "ultrasound", "pet", "pet/ct",
    # Cardio-pulmonary
    "pe", "dvt", "rv", "lv", "lvef", "rvef", "rv/lv", "strain", "right heart strain",
    # Scores / staging / neuro
    "wells", "d-dimer", "ddimer", "ctsi", "aspects", "nihss", "ich",
    # Onc/staging
    "tnm", "tlics", "ao", "ota",
    # Other high-yield tokens
    "pancreatitis", "stroke",
}

# Terms we consider non-informative for token matching/deduping
TOKEN_STOPWORDS = {
    "cancer", "carcinoma", "tumor", "tumour", "mass", "lesion", "staging",
    "score", "classification", "grading", "grade", "system", "scale",
    "disease", "syndrome", "disorder", "condition",
    # Generic clinical modifiers we don't want to fragment tokens
    "acute", "chronic", "in",
}


def _canonical_terms(text: str) -> List[str]:
    """
    Produce a canonical list of token stems for deduping semantically similar selections.
    - Lowercase, strip punctuation.
    - Remove generic stopwords (e.g., cancer, staging).
    - Apply light stemming: strip common medical suffixes and plural/adj endings.
    - Truncate to a short root to smooth small variants (e.g., pancreas/pancreatitis -> pancre).
    """
    raw_tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    stems = []
    for tok in raw_tokens:
        if tok in TOKEN_STOPWORDS:
            continue
        root = tok
        # Strip common suffixes
        for suf in ("itis", "osis", "omas", "oma", "ing", "tion", "s", "es", "ic", "al", "ary", "atic"):
            if root.endswith(suf) and len(root) > len(suf) + 2:
                root = root[: -len(suf)]
                break
        # Truncate to 6 chars to smooth minor spelling/ending variants
        if len(root) > 6:
            root = root[:6]
        if len(root) >= 2:
            stems.append(root)
    # Deduplicate while preserving deterministic order
    stems = sorted(set(stems))
    return stems


def _normalize_token(text: str) -> str:
    stems = _canonical_terms(text)
    return " ".join(stems)


def _dedupe_hash(section: str, selection_text: str, modality, body_part, module) -> str:
    # Build a stable hash to avoid regenerating for identical contexts.
    payload = "|".join([
        (section or "").lower(),
        _normalize_token(selection_text),
        getattr(modality, "name", "") or "",
        getattr(body_part, "name", "") or "",
        getattr(module, "name", "") or "",
    ])
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()



def _parse_cards(raw: str) -> List[Dict[str, Any]]:
    if isinstance(raw, str):
        trimmed = raw.strip()
        # Strip Markdown fences if the model wrapped JSON in ```json ... ```
        if trimmed.startswith("```"):
            trimmed = re.sub(r"^```(?:json)?\s*|\s*```$", "", trimmed, flags=re.IGNORECASE | re.MULTILINE).strip()
        # Strip <think>...</think> meta sections if present (some models prepend reasoning)
        trimmed = re.sub(r"<think>.*?</think>", "", trimmed, flags=re.DOTALL).strip()
        # Drop any leading non-JSON chatter before the first bracket/brace
        first_brace = min([idx for idx in [trimmed.find("["), trimmed.find("{")] if idx != -1], default=-1)
        if first_brace > 0:
            trimmed = trimmed[first_brace:]
    else:
        trimmed = raw

    try:
        data = json.loads(trimmed)
    except Exception:
        # Attempt salvage: trim trailing junk after the last closing bracket if present
        if isinstance(trimmed, str):
            if "[" in trimmed and "]" in trimmed:
                try:
                    candidate = trimmed[: trimmed.rfind("]") + 1]
                    data = json.loads(candidate)
                except Exception:
                    data = None
            else:
                data = None

            if data is None and "{" in trimmed and "}" in trimmed:
                # Try to capture from first bracket/brace to last brace and close array if needed
                start = trimmed.find("[")
                if start == -1:
                    start = trimmed.find("{")
                end = trimmed.rfind("}")
                if start != -1 and end != -1 and end > start:
                    candidate = trimmed[start:end + 1]
                    if candidate.strip().startswith("{"):
                        candidate = "[" + candidate + "]"
                    candidate = re.sub(r",\s*]", "]", candidate)
                    try:
                        data = json.loads(candidate)
                    except Exception:
                        data = None
            if data is None:
                # Try balancing unmatched braces/brackets by appending closers
                balanced = trimmed
                brace_diff = balanced.count("{") - balanced.count("}")
                if brace_diff > 0:
                    balanced += "}" * brace_diff
                bracket_diff = balanced.count("[") - balanced.count("]")
                if bracket_diff > 0:
                    balanced += "]" * bracket_diff
                try:
                    data = json.loads(balanced)
                except Exception:
                    return []
        else:
            return []

    if isinstance(data, dict) and "cards" in data:
        data = data["cards"]
    elif isinstance(data, dict):
        # Accept a single-card dict by wrapping it
        data = [data]

    if not isinstance(data, list):
        return []
    return data


def _validate_cards(cards: List[Dict[str, Any]], selection_token: str = "") -> List[Dict[str, Any]]:
    cleaned = []
    for card in cards:
        title = (card.get("title") or "").strip()
        summary = (card.get("summary") or "").strip()
        bullets = card.get("bullets") or []
        raw_bullets = list(bullets) if isinstance(bullets, list) else []
        insert_options = card.get("insert_options") or []
        kind = (card.get("kind") or "info").lower()
        tables = card.get("tables") or []

        if not title:
            continue
        title = title[:120]
        summary = summary[:360]

        bullets = [b for b in bullets if isinstance(b, str) and b.strip()][:8]
        uniq = []
        seen = set()
        for b in bullets:
            key = b.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            uniq.append(b)
        bullets = uniq

        cleaned_options = []
        if isinstance(insert_options, list):
            for opt in insert_options[:3]:
                label = (opt.get("label") or "").strip() if isinstance(opt, dict) else ""
                text = (opt.get("text") or "").strip() if isinstance(opt, dict) else ""
                if label and text:
                    cleaned_options.append({"label": label[:80], "text": text[:500]})

        allowed_kinds = {"info", "score", "checklist", "differential", "technique", "measurement", "classification", "other"}
        if kind not in allowed_kinds:
            kind = "info"

        normalized_tables = []
        if isinstance(tables, list):
            for tbl in tables:
                if not isinstance(tbl, dict):
                    continue
                rows = tbl.get("rows") or []
                if not rows:
                    continue
                normalized_tables.append({
                    "title": (tbl.get("title") or "").strip(),
                    "header": tbl.get("header") or tbl.get("headers") or "",
                    "rows": rows if isinstance(rows, list) else [],
                })

        # Require multi-table output only when explicitly score to capture components + interpretation
        if kind == "score" and len(normalized_tables) < 2:
            continue

        # Enforce source allowlist and priority
        def _first_link(b_list: list[str]) -> str | None:
            for b in b_list:
                match = re.search(r"https?://[^\s\"]+", b)
                if not match:
                    continue
                url = match.group(0)
                parsed = urlparse(url)
                host = parsed.netloc.lower()
                path = (parsed.path or "").strip("/")
                has_query = bool(parsed.query)
                # Require host and either a path or querystring to avoid homepage-only 404s
                if host and (path or has_query):
                    return url
            return None

        # Search for sources in the raw bullets before truncation
        source_url = _first_link(raw_bullets) or _first_link(bullets)
        allowed_source = None
        if source_url:
            allowed_source = f'Sources: <a href="{source_url}" target="_blank" rel="noopener">{source_url}</a>'
        if not allowed_source:
            if "tnm" in (selection_token or "").lower():
                source_url = "https://www.canstaging.org/tool?tnm_version=v8"
                allowed_source = 'Sources: <a href="https://www.canstaging.org/tool?tnm_version=v8" target="_blank" rel="noopener">canstaging.org</a>'
            else:
                # Relaxed: allow missing source but mark as pending verification
                allowed_source = "Sources: pending verification"

        # Remove existing source bullets to avoid duplicates
        bullets = [b for b in bullets if "source" not in b.lower()]
        if len(bullets) < 8:
            bullets.append(allowed_source)
        else:
            bullets[-1] = allowed_source

        cleaned.append({
            "title": title,
            "summary": summary,
            "bullets": bullets,
            "insert_options": cleaned_options,
            "kind": kind,
            "tables": normalized_tables,
            "source_url": source_url,
        })
    return cleaned[:1]



def _section_enum(section: str) -> Optional[SmartHelperSectionEnum]:
    key = (section or "").strip().lower()
    mapping = {
        "indication": SmartHelperSectionEnum.INDICATION,
        "comparison": SmartHelperSectionEnum.COMPARISON,
        "technique": SmartHelperSectionEnum.TECHNIQUE,
        "observations": SmartHelperSectionEnum.OBSERVATIONS,
        "conclusion": SmartHelperSectionEnum.CONCLUSION,
        "recommendations": SmartHelperSectionEnum.RECOMMENDATIONS,
        "any": SmartHelperSectionEnum.ANY,
    }
    return mapping.get(key)


def _kind_enum(kind: str) -> Optional[SmartHelperKindEnum]:
    key = (kind or "").strip().lower()
    mapping = {
        "info": SmartHelperKindEnum.INFO,
        "score": SmartHelperKindEnum.SCORE,
        "checklist": SmartHelperKindEnum.CHECKLIST,
        "differential": SmartHelperKindEnum.DIFFERENTIAL,
        "technique": SmartHelperKindEnum.TECHNIQUE,
        "measurement": SmartHelperKindEnum.MEASUREMENT,
        "classification": SmartHelperKindEnum.CLASSIFICATION,
        "other": SmartHelperKindEnum.OTHER,
    }
    return mapping.get(key, SmartHelperKindEnum.INFO)


def _recent_ai_card_exists(token: str, section_enum, modality, body_part, module, dedupe_hash: str, max_age_hours: int = 24) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    q = db.session.query(SmartHelperCard).filter(
        SmartHelperCard.source.in_(["ai", "ai-unverified"]),
        SmartHelperCard.generated_for_token == token,
        SmartHelperCard.generated_hash == dedupe_hash,
        SmartHelperCard.created_at >= cutoff,
    )
    if section_enum:
        q = q.filter(SmartHelperCard.section == section_enum)
    if modality:
        q = q.filter(SmartHelperCard.modality == modality)
    if body_part:
        q = q.filter(SmartHelperCard.body_part == body_part)
    if module:
        q = q.filter(SmartHelperCard.module == module)
    return db.session.query(q.exists()).scalar()


def _any_card_exists(token: str, section_enum, modality, body_part, module) -> bool:
    """
    Check if any card (any source) already exists for this token and context.
    Used to avoid hitting the model when a card is already present.
    """
    def _stem_set(tok: str) -> set[str]:
        return set((tok or "").split())

    target_stems = _stem_set(token)

    q = db.session.query(SmartHelperCard.token).filter(SmartHelperCard.token.isnot(None))
    if section_enum:
        q = q.filter(SmartHelperCard.section == section_enum)
    if modality:
        q = q.filter(SmartHelperCard.modality == modality)
    if body_part:
        q = q.filter(SmartHelperCard.body_part == body_part)
    if module:
        q = q.filter(SmartHelperCard.module == module)

    for (tok_str,) in q.all():
        row_stems = _stem_set(tok_str)
        # Exact match, subset, or superset match counts as existing
        if target_stems == row_stems or target_stems.issubset(row_stems) or row_stems.issubset(target_stems):
            return True
    return False


def _resolve_quota(user, cfg) -> Optional[int]:
    """
    Decide the daily quota for a user.
    - Admins: unlimited (None).
    - If override set: use it.
    - Paid vs free default from config.
    - Always capped by AI_MAX_DAILY_CALLS_PER_USER if set.
    """
    if user is None:
        return cfg.get("AI_FREE_DAILY_LIMIT", 5)

    # Admins have no quota
    if getattr(user, "is_admin", False):
        return None

    override = getattr(user, "ai_daily_quota_override", None)
    if override is not None:
        quota = override
    else:
        quota = cfg.get("AI_PAID_DAILY_LIMIT", 20) if getattr(user, "is_paid", False) else cfg.get("AI_FREE_DAILY_LIMIT", 5)

    max_cap = cfg.get("AI_MAX_DAILY_CALLS_PER_USER", None)
    if max_cap is not None:
        quota = min(quota, max_cap)
    return quota


def _quota_allows(user, cfg) -> bool:
    """Check quota without incrementing."""
    if user is None or getattr(user, "is_admin", False):
        return True

    quota = _resolve_quota(user, cfg)
    if quota is None:
        return True

    now = datetime.now(timezone.utc)
    last_reset = getattr(user, "ai_calls_last_reset", None)
    if last_reset is None or last_reset.date() != now.date():
        return True  # will reset on increment path

    return user.ai_calls_used_today < quota


def _increment_quota(user, cfg) -> None:
    """Increment usage after a successful generation."""
    if user is None or getattr(user, "is_admin", False):
        return

    quota = _resolve_quota(user, cfg)
    if quota is None:
        return

    now = datetime.now(timezone.utc)
    last_reset = getattr(user, "ai_calls_last_reset", None)
    if last_reset is None or last_reset.date() != now.date():
        user.ai_calls_used_today = 0

    user.ai_calls_used_today = (user.ai_calls_used_today or 0) + 1
    user.ai_calls_last_reset = now
    db.session.add(user)
    db.session.commit()


def quota_status(user, cfg) -> dict:
    """
    Return a lightweight snapshot of quota status for display purposes.
    Does not mutate the user record.
    """
    if user is None or getattr(user, "is_admin", False):
        return {"quota": None, "used": 0, "remaining": None, "label": "Unlimited"}

    quota = _resolve_quota(user, cfg)
    now = datetime.now(timezone.utc)
    last_reset = getattr(user, "ai_calls_last_reset", None)
    used = getattr(user, "ai_calls_used_today", 0) or 0

    if last_reset is None or last_reset.date() != now.date():
        used = 0

    if quota is None:
        return {"quota": None, "used": used, "remaining": None, "label": "Unlimited"}

    remaining = max(quota - used, 0)
    return {
        "quota": quota,
        "used": used,
        "remaining": remaining,
        "label": f"{remaining} / {quota} left today",
    }


def generate_ai_cards(context: dict, selection_text: str, section: str, user=None) -> List[SmartHelperCard]:
    cfg = current_app.config
    if not cfg.get("AI_HELPERS_ENABLED"):
        return []

    force_provider = (context.get("force_provider") or "").strip().lower() if isinstance(context, dict) else ""
    force_timeout = None
    try:
        force_timeout = int(context.get("force_timeout")) if context.get("force_timeout") is not None else None
    except Exception:
        force_timeout = None
    replace_fallback = bool(context.get("replace_fallback")) if isinstance(context, dict) else False

    # Use raw text for gating, normalized stems for dedupe
    token_raw = selection_text.strip().lower() if selection_text else ""
    token = _normalize_token(selection_text)
    force_ai = bool(context.get("force_ai"))
    # Basic noise gate: skip empty or trivial selections unless allowlisted or force_ai
    if not token_raw:
        return []
    if not force_ai:
        if len(token_raw) < 3 and token_raw not in ALLOWLIST_TOKENS:
            return []
        if token_raw in STOPLIST_TOKENS and token_raw not in ALLOWLIST_TOKENS:
            return []

    section_enum = _section_enum(section)
    modality = context.get("modality_enum")
    body_part = context.get("body_part_enum")
    module = context.get("module_enum")
    study_type = context.get("study_type") or ""

    dedupe = _dedupe_hash(section, selection_text, modality, body_part, module)
    # Allow regeneration requests (replace_fallback) to bypass dedupe so we can swap in a new provider response.
    if not replace_fallback:
        if _any_card_exists(token, section_enum, modality, body_part, module):
            return []
        if _recent_ai_card_exists(token, section_enum, modality, body_part, module, dedupe):
            return []

    if not _quota_allows(user, cfg):
        logger.info("AI helper quota exceeded for user %s", getattr(user, "id", None))
        return []

    def _make_no_card(reason_text: str) -> list:
        msg = (reason_text or "").strip() or "No smart helper card could be generated for this query."
        return [SimpleNamespace(
            id=None,
            title="No card generated",
            summary=msg,
            kind="info",
            reason=msg,
            section=section_enum or SmartHelperSectionEnum.ANY,
            bullets=[msg],
            insert_options=[],
            tags="",
            token=token,
            modality=modality,
            body_part=body_part,
            module=module,
            display_style="auto",
            source="ai-status",
            source_detail="ai-no-card",
        )]

    def _make_salvage_card_from_parsed(parsed, reason_text: str) -> list:
        """Best-effort card if parsed content exists but failed validation."""
        if not parsed:
            return []
        first = parsed[0] if isinstance(parsed, list) else parsed
        if not isinstance(first, dict):
            return []
        title = (first.get("title") or "Helper card").strip() or "Helper card"
        summary = (first.get("summary") or reason_text or json.dumps(first)[:400]).strip()
        bullets = first.get("bullets") if isinstance(first.get("bullets"), list) else []
        return [SimpleNamespace(
            id=None,
            title=title,
            summary=summary,
            kind=first.get("kind") or "info",
            reason=reason_text or summary,
            section=section_enum or SmartHelperSectionEnum.ANY,
            bullets=bullets,
            insert_options=[],
            tags="",
            token=token,
            modality=modality,
            body_part=body_part,
            module=module,
            display_style="auto",
            source="ai-status",
            source_detail="ai-salvage",
        )]

    requested_provider = (force_provider or cfg.get("AI_PROVIDER") or "openai").lower()
    # Map friendly names to internal handler keys and label keys
    def _map_provider(name: str):
        n = (name or "").lower()
        if n in {"deepseek", "ds", "qubrid"}:
            return "qubrid", "deepseek"
        if n in {"openai", "oai"}:
            return "openai", "openai"
        if n in {"gemini", "g"}:
            return "gemini", "gemini"
        return n, n

    provider, provider_label = _map_provider(requested_provider)
    fallback_used = False
    timeout_val = force_timeout or cfg.get("AI_REQUEST_TIMEOUT", 15)
    modality_name = getattr(modality, "name", "") or "unspecified"
    body_part_name = getattr(body_part, "name", "") or "unspecified"

    def _normalize_token_key(tok: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (tok or "").lower())

    # Alias map to soften formatting differences for known systems
    token_aliases = {
        # LI-RADS family
        "li-rads": "lirads",
        "li rads": "lirads",
        "liver imaging reporting and data system": "lirads",
        "li-rads ct": "lirads",
        "li-rads mri": "lirads",
        "li-rads us": "lirads_us",
        "li rads us": "lirads_us",
        "lirads us": "lirads_us",
        "ultrasound lirads": "lirads_us",
        "li-rads ceus": "lirads_ceus",
        "li rads ceus": "lirads_ceus",
        "lirads ceus": "lirads_ceus",

        # BI-RADS
        "bi-rads": "birads",
        "bi rads": "birads",
        "breast imaging reporting and data system": "birads",
        "bi-rads mri": "birads",
        "bi-rads us": "birads",
        "bi-rads mammography": "birads",

        # TI-RADS (various ecosystems)
        "ti-rads": "tirads",
        "ti rads": "tirads",
        "acr ti-rads": "tirads_acr",
        "acr tirads": "tirads_acr",
        "eu-tirads": "tirads_eu",
        "eu tirads": "tirads_eu",
        "k-tirads": "tirads_k",
        "k tirads": "tirads_k",
        "ata thyroid risk": "ata_thyroid_risk",

        # O-RADS
        "o-rads": "orads",
        "orads": "orads",
        "o-rads us": "orads_us",
        "orads us": "orads_us",
        "o-rads mri": "orads_mri",
        "orads mri": "orads_mri",
        "o-rads mri adnexal": "orads_mri",
        "orads mri adnexal": "orads_mri",

        # PI-RADS
        "pi-rads": "pirads",
        "pi rads": "pirads",
        "prostate imaging reporting and data system": "pirads",
        "pi-qual": "piqual",
        "pi qual": "piqual",

        # Common RADS / reporting systems
        "lung-rads": "lungrads",
        "lung rads": "lungrads",
        "cad-rads": "cadrads",
        "cad rads": "cadrads",
        "co-rads": "corads",
        "co rads": "corads",
        "ni-rads": "nirads",
        "ni rads": "nirads",
        "vi-rads": "virads",
        "vi rads": "virads",
        "my-rads": "myrads",
        "my rads": "myrads",

        # Renal cysts
        "bosniak": "bosniak",
        "bosniak classification": "bosniak",

        # Neuro scores
        "aspects": "aspects",
        "alberta stroke program early ct score": "aspects",
        "marshall": "marshall_ct",
        "marshall ct": "marshall_ct",
        "rotterdam": "rotterdam_ct",
        "rotterdam ct": "rotterdam_ct",
        "fisher": "fisher_sah",
        "modified fisher": "modified_fisher_sah",
        "pc-aspects": "pc_aspects",
        "pc aspects": "pc_aspects",
        "cta collateral score": "cta_collateral_score",
        "tan collateral": "tan_collateral",
        "asitn sir": "asitn_sir",
        "asitn/sir": "asitn_sir",
        "mtici": "mtici",
        "tici": "tici",
        "clot burden score": "clot_burden_score",
        "cbs": "clot_burden_score",
        "cta spot sign": "cta_spot_sign",
        "spot sign score": "cta_spot_sign",
        "abc/2": "abc2_hematoma",
        "abc2": "abc2_hematoma",
        "fazekas": "fazekas",
        "ecass hemorrhagic transformation": "ecass_ht",
        "toas t": "toast",
        "toast": "toast",
        "basilar artery occlusion score": "basilar",

        # Spine trauma
        "tlics": "tlics",
        "slics": "slics",
        "ao spine": "aospine",
        "ao spine thoracolumbar": "aospine_thoracolumbar",
        "ao spine subaxial cervical": "aospine_subaxial_cervical",
        "denis three column": "denis_three_column",
        "denis 3 column": "denis_three_column",

        # Oncology response / staging (agnostic)
        "recist": "recist",
        "recist 1.1": "recist",
        "irecist": "irecist",
        "mrecist": "mrecist",
        "tnm": "tnm",
        "ajcc": "tnm",
        "percist": "percist",
        "choi criteria": "choi",
        "rano": "rano",
        "rano-bm": "rano_bm",
        "rano bm": "rano_bm",
        "rano-lgg": "rano_lgg",
        "rano lgg": "rano_lgg",
        "rano-hgg": "rano_hgg",
        "rano hgg": "rano_hgg",
        "macdonald": "macdonald",
        "who cns grading": "who_cns_grading",
        "figo": "figo",
        "figo staging": "figo",
        "ann arbor": "ann_arbor",
        "durie salmon": "durie_salmon",
        "iss myeloma": "iss_myeloma",

        # IMPORTANT: clinical-only scores (do NOT modality-allowlist)
        "chads2": "clinical_only__chads2",
        "chads2-vasc": "clinical_only__cha2ds2vasc",
        "chasd2vasc": "clinical_only__cha2ds2vasc",
        "cha2ds2-vasc": "clinical_only__cha2ds2vasc",
        "melt": "clinical_only__meld",
        "meld": "clinical_only__meld",
        "child pugh": "clinical_only__childpugh",
        "wells": "clinical_only__wells",
        "geneva": "clinical_only__geneva",
        "pesi": "clinical_only__pesi",
        "spesi": "clinical_only__spesi",

        # RMI: ultrasound-based + CA-125 (treat as US/clinical, not CT/MRI)
        "rmi": "rmi",
        "risk of malignancy index": "rmi",

        # Trauma / bleeding / injury scales
        "gcs": "gcs",
        "glasgow coma scale": "gcs",
        "ais": "ais",
        "abbreviated injury scale": "ais",
        "iss": "iss",
        "injury severity score": "iss",
        "niss": "niss",
        "fast grading": "fast_grading",
        "aast liver": "aast_liver",
        "aast spleen": "aast_spleen",
        "aast kidney": "aast_kidney",
        "aast pancreas": "aast_pancreas",
        "aast bowel": "aast_bowel",
        "young burgess": "young_burgess_pelvis",
        "tile classification": "tile_pelvis",
        "svs thoracic aortic injury": "svs_thoracic_aortic_injury",
        "biffl": "biffl_bcvi",
        "biffl bcvi": "biffl_bcvi",
        "hemothorax volume": "hemothorax_volume_ct",

        # Lymphoma / PET CT
        "cotswolds": "cotswolds",
        "deauville": "deauville",
        "recil": "recil",
        "mtv": "mtv",
        "tlg": "tlg",
        "bone marrow involvement": "bone_marrow_patterns",
        "bulky disease": "bulky_disease",

        # Chest oncology / mediastinum
        "iaslc lung cancer staging": "iaslc_lung_tnm",
        "mediastinal nodal mapping": "mediastinal_nodal_map",
        "pleural effusion malignancy criteria": "pleural_effusion_malignancy",
        "malignant airway obstruction": "malignant_airway_obstruction",

        # Abdomen / GI acute/onc
        "bclc": "bclc",
        "okuda": "okuda",
        "child pugh": "clinical_only__childpugh",
        "metavir": "metavir",
        "ct severity index": "ctsi",
        "modified ctsi": "modified_ctsi",
        "revised atlanta": "revised_atlanta",
        "hinchey": "hinchey",
        "boey score": "boey_score",
        "tokyo guidelines": "tokyo_guidelines",

        # Head & neck
        "laryngeal cartilage invasion": "laryngeal_cartilage",
        "nodal necrosis": "nodal_necrosis",
        "extranodal extension": "extranodal_extension",

        # MSK oncology
        "enneking": "enneking",
        "ajcc bone tumor": "ajcc_bone_tumor",
        "weinstein boriani biagini": "wbb_spine",
        "msts": "msts",
        "bone-rads": "bonerads",

        # Vascular / acute aorta / PE
        "stanford dissection": "stanford_dissection",
        "debakey dissection": "debakey_dissection",
        "debkey dissection": "debakey_dissection",
        "qanadli": "qanadli_pe",
        "qanadli pe": "qanadli_pe",
        "rv/lv ratio": "rv_lv_ratio_ctpa",
        "rv lv ratio": "rv_lv_ratio_ctpa",
    }

    # Deterministic mapping to short-circuit obvious modality-specific systems.
    # Keys are normalized tokens; values are sets of allowed modality keys (lowercase).
    modality_token_allowlist = {
        # Thyroid (US-based)
        "tirads": {"us"},
        "tirads_acr": {"us"},
        "tirads_eu": {"us"},
        "tirads_k": {"us"},
        "ata_thyroid_risk": {"us"},

        # Ovarian/adnexal
        "orads": {"us", "mri"},
        "orads_us": {"us"},
        "orads_mri": {"mri"},

        # Prostate
        "pirads": {"mri"},
        "piqual": {"mri"},

        # Liver
        "lirads": {"ct", "mri"},
        "lirads_us": {"us"},
        "lirads_ceus": {"ceus"},  # treat separately if you support CEUS

        # Breast
        "birads": {"mg", "us", "mri"},

        # Chest
        "lungrads": {"ct"},
        "corads": {"ct"},
        "cadrads": {"ct"},  # CCTA CT

        # Head & neck (often CT/MRI; PETCT optional)
        "nirads": {"ct", "mri", "petct"},

        # Bladder
        "virads": {"mri"},

        # Myeloma
        "myrads": {"mri"},

        # Renal cysts
        "bosniak": {"ct", "mri"},

        # Neuro
        "aspects": {"ct", "mri"},
        "marshall_ct": {"ct"},
        "rotterdam_ct": {"ct"},
        "fisher_sah": {"ct"},
        "modified_fisher_sah": {"ct"},
        "pc_aspects": {"ct", "mri"},
        "cta_collateral_score": {"ct"},
        "tan_collateral": {"ct"},
        "asitn_sir": {"ct"},
        "mtici": {"ct"},
        "tici": {"ct"},
        "clot_burden_score": {"ct"},
        "cta_spot_sign": {"ct"},
        "abc2_hematoma": {"ct"},
        "fazekas": {"mri"},
        "ecass_ht": {"ct", "mri"},
        "toast": {"ct", "mri"},
        "basilar": {"ct"},

        # Spine trauma
        "tlics": {"ct", "mri"},
        "slics": {"ct", "mri"},
        "aospine": {"ct", "mri"},
        "aospine_thoracolumbar": {"ct", "mri"},
        "aospine_subaxial_cervical": {"ct", "mri"},
        "denis_three_column": {"ct", "mri"},
        "young_burgess_pelvis": {"ct"},
        "tile_pelvis": {"ct"},

        "aast_liver": {"ct"},
        "aast_spleen": {"ct"},
        "aast_kidney": {"ct"},
        "aast_pancreas": {"ct"},
        "aast_bowel": {"ct"},

        "svs_thoracic_aortic_injury": {"ct"},
        "biffl_bcvi": {"ct"},

        # RMI is US + lab/clinical; do not allow CT/MRI
        "rmi": {"us"},

        # Neuro trauma/bleed additional
        "ich_score": {"ct"},
        "modified_ich_score": {"ct"},
        "graeb_score": {"ct"},
        "modified_graeb": {"ct"},
        "hunt_hess": {"ct"},
        "wfns_sah": {"ct"},
        "abc2_hematoma": {"ct"},

        # Oncology – agnostic / response
        "percist": {"petct"},
        "choi": {"ct"},
        "rano": {"mri"},
        "rano_bm": {"mri"},
        "rano_lgg": {"mri"},
        "rano_hgg": {"mri"},
        "macdonald": {"mri"},
        "who_cns_grading": {"mri"},
        "figo": {"us", "mri", "ct"},
        "ann_arbor": {"ct", "petct"},
        "durie_salmon": {"ct", "mri"},
        "iss_myeloma": {"ct", "mri"},

        # Lymphoma
        "lugano": {"ct", "petct"},
        "cotswolds": {"ct", "petct"},
        "deauville": {"petct"},
        "recil": {"ct", "mri"},
        "mtv": {"petct"},
        "tlg": {"petct"},
        "bone_marrow_patterns": {"ct", "petct", "mri"},
        "bulky_disease": {"ct", "petct"},

        # Chest / thoracic oncology
        "iaslc_lung_tnm": {"ct"},
        "mediastinal_nodal_map": {"ct"},
        "pleural_effusion_malignancy": {"ct"},
        "malignant_airway_obstruction": {"ct"},

        # Abdomen / GI
        "bclc": {"ct", "mri"},
        "okuda": {"ct", "mri"},
        "ctsi": {"ct"},
        "modified_ctsi": {"ct"},
        "revised_atlanta": {"ct"},
        "hinchey": {"ct"},
        "metavir": {"ct", "mri"},
        "boey_score": {"ct"},
        "tokyo_guidelines": {"ct", "us"},

        # Head & neck
        "laryngeal_cartilage": {"ct", "mri"},
        "nodal_necrosis": {"ct", "mri"},
        "extranodal_extension": {"ct", "mri"},

        # MSK oncology
        "enneking": {"mri", "ct"},
        "ajcc_bone_tumor": {"mri", "ct"},
        "wbb_spine": {"mri"},
        "msts": {"mri", "ct"},
        "bonerads": {"ct", "mri"},

        # Vascular / PE
        "stanford_dissection": {"ct"},
        "debakey_dissection": {"ct"},
        "qanadli_pe": {"ct"},
        "rv_lv_ratio_ctpa": {"ct"},
    }

    # Modality-agnostic systems that should be allowed across modalities
    modality_agnostic_tokens = {
        "tnm",
        "recist",
        "irecist",
        "mrecist",
    }

    # Clinical-only tokens should not trigger radiology helper cards
    clinical_only_tokens = {
        "clinical_only__chads2",
        "clinical_only__cha2ds2vasc",
        "clinical_only__meld",
        "clinical_only__childpugh",
        "clinical_only__wells",
        "clinical_only__geneva",
        "clinical_only__pesi",
        "clinical_only__spesi",
    }
    normalized_token_key = token_aliases.get(token_raw.strip().lower(), _normalize_token_key(token_raw))
    modality_key = (modality_name or "").lower()
    mapping_verdict = None
    mapping_reason = None

    if normalized_token_key in clinical_only_tokens:
        reason_text = f'Not generating helper cards: token "{token_raw}" is a clinical-only score and not a radiology modality system.'
        return _make_no_card(reason_text)

    if normalized_token_key in modality_agnostic_tokens:
        mapping_verdict = "ALLOW"

    if normalized_token_key in modality_token_allowlist and mapping_verdict is None:
        allowed_modalities = modality_token_allowlist[normalized_token_key]
        if modality_key in allowed_modalities:
            mapping_verdict = "ALLOW"
        else:
            mapping_verdict = "REJECT"
            mapping_reason = (
                f'Token "{token_raw}" is modality-specific and not defined for modality {modality_name}. '
                f'Allowed modalities: {", ".join(sorted(allowed_modalities)).upper()}.'
            )

    def _normalize_verdict(text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"(?i)<think[^>]*>", "", cleaned)
        cleaned = re.sub(r"(?i)</think>", "", cleaned)
        cleaned = re.sub(r"(?i)<think.*", "", cleaned)  # handle unterminated blocks
        cleaned = re.sub(r"^```(?:[a-zA-Z0-9_-]+)?\s*|\s*```$", "", cleaned, flags=re.DOTALL)
        cleaned = cleaned.strip()
        # Look for explicit ALLOW/REJECT token
        for tok in re.split(r"\s+", cleaned):
            up = tok.strip().upper()
            if up in {"ALLOW", "REJECT"}:
                return up
        # Fallback: substring search
        if "ALLOW" in cleaned.upper():
            return "ALLOW"
        if "REJECT" in cleaned.upper():
            return "REJECT"
        return "UNSURE"

    validator_prompt = "\n".join([
        "You are a modality–concept validator for a radiology application.",
        "Determine whether the given token represents a concept that is (1) natively defined for the specified Modality AND (2) formally accepted for use with that Modality in standard radiology practice or guidelines.",
        "Rules:",
        "- If the concept is modality-exclusive (e.g., US-only, MRI-only) and the modality does not match → REJECT",
        "- If applying the concept would require adaptation, reinterpretation, or cross-modality reasoning → REJECT",
        "- If the query is nonsensical, non-medical, or unrelated to radiology → REJECT",
        "- Do NOT reject a guideline-based system solely because another modality-specific system exists for the same organ. Multiple CT-based frameworks may coexist. Reject only if modality mismatch exists.",
        "- Do NOT reject an imaging management guideline/framework just because it lacks a formal score or classification; absence of a numeric score does NOT imply modality invalidity.",
        "- Only return ALLOW if the concept is inherently valid for this modality",
        "Return exactly one token: ALLOW or REJECT",
        f"Token: {token_raw}",
        f"Modality: {modality_name}",
        f"Body part: {body_part_name}",
    ])

    def _call_validator(pvd: str):
        if pvd == "gemini":
            return call_gemini_chat(
                prompt=validator_prompt,
                model=cfg.get("GEMINI_MODEL", "gemini-1.5-pro"),
                max_tokens=cfg.get("AI_MAX_TOKENS_VALIDATOR", 8),
                timeout=timeout_val,
                api_key=cfg.get("GEMINI_API_KEY"),
            )
        if pvd == "qubrid":
            return call_qubrid_deepseek(
                prompt=validator_prompt,
                model=cfg.get("QUBRID_MODEL") or "deepseek-ai/deepseek-r1-distill-llama-70b",
                max_tokens=cfg.get("AI_MAX_TOKENS_VALIDATOR", 8),
                timeout=timeout_val,
                api_key=cfg.get("QUBRID_API_KEY"),
            )
        openai_model = cfg.get("AI_MODEL") or "gpt-4o"
        return call_openai_chat(
            prompt=validator_prompt,
            model=openai_model,
            max_tokens=cfg.get("AI_MAX_TOKENS_VALIDATOR", 8),
            timeout=timeout_val,
            api_key=cfg.get("OPENAI_API_KEY"),
        )

    try:
        verdict_raw = (_call_validator(provider) or "").strip()
    except Exception:
        logger.exception("AI modality validator failed; defaulting to REJECT")
        verdict_raw = ""
        if provider != "openai" and cfg.get("OPENAI_API_KEY"):
            try:
                verdict_raw = (_call_validator("openai") or "").strip()
            except Exception:
                logger.exception("AI modality validator OpenAI fallback failed")
                verdict_raw = ""

    verdict = mapping_verdict or _normalize_verdict(verdict_raw)

    if verdict == "REJECT":
        logger.info(
            "AI helper modality validator rejected token",
            extra={
                "token": token_raw,
                "modality": modality_name,
                "body_part": body_part_name,
                "verdict": verdict,
                "verdict_raw": verdict_raw,
            },
        )
        reason_text = mapping_reason or (
            f'Not generating helper cards: token "{token_raw}" is not valid for modality {modality_name} '
            f'(validator verdict: {verdict or "REJECT"}).'
            )
        return _make_no_card(reason_text)
    # UNSURE falls through to generator; generator prompt already enforces modality locks and >95% confidence rule.

    def _provider_card_exists(token_value, section_value, modality_value, body_part_value, module_value, provider_tag):
        if not provider_tag:
            return False
        q_check = db.session.query(SmartHelperCard).filter(
            SmartHelperCard.is_active.is_(True),
            SmartHelperCard.token == token_value,
            SmartHelperCard.source_detail.ilike(f"ai-{provider_tag}%"),
        )
        # Match same section or ANY
        section_filters = [SmartHelperSectionEnum.ANY]
        if section_value is not None:
            section_filters.append(section_value)
        q_check = q_check.filter(SmartHelperCard.section.in_(section_filters))
        # Match modality/body/module with allowance for NULL (generic)
        if modality_value is not None:
            q_check = q_check.filter(or_(SmartHelperCard.modality == modality_value, SmartHelperCard.modality.is_(None)))
        if body_part_value is not None:
            q_check = q_check.filter(or_(SmartHelperCard.body_part == body_part_value, SmartHelperCard.body_part.is_(None)))
        if module_value is not None:
            q_check = q_check.filter(or_(SmartHelperCard.module == module_value, SmartHelperCard.module.is_(None)))
        return db.session.query(q_check.exists()).scalar()

    # Block regenerating with the same provider if it already produced a card for this context
    if _provider_card_exists(token, section_enum, modality, body_part, module, provider_label):
        return _make_no_card(f'Helper cards already exist for provider "{provider_label}" in this context. Try another provider if needed.')

    prompt_parts = [
        "You are an expert radiologist colleague creating ONE comprehensive helper card for experienced radiologists.",
        "Behave like a well-read radiology with subspeciality expertise and ability to bring in relevant, reputable knowledge to enrich the answer.", 
        "HARD CONSTRAINT: The following mapping is authoritative and exhaustive. If the token is not explicitly valid for the modality below, you MUST return []. Modality–exclusive systems: US-only: TI-RADS, ATA Thyroid Risk, O-RADS US; MRI-only: PI-RADS; CT/MRI: LI-RADS; MG/US/MRI: BI-RADS.",
        f"Token: {token_raw}",
        f"Modality: {modality_name}",
        "Modality validation rule: Content must be modality-specific, clinically appropriate, and internally consistent with the provided Modality. If the query violates this requirement or is not logically applicable, return [] and generate no content. Cross-modality generalization is prohibited.",
        "If the classification, score, or system was not originally defined, validated, and published for the specified Modality, return [] immediately. Do not reinterpret or adapt across modalities.",
        "Make the card comprehensive and clinically/radiologically relevant: include applications, implications, and key pitfalls that affect reporting decisions.",
        "When authoritative scores/classifications/TNM/grading exist, present them in tables; use multiple tables if needed. Use bullets/checklists when more natural; do not force tables when inappropriate.",
        "When there a scoring system , classification system or staging system required computation from multiple components, ensure ALL components are included with detailed criteria and thresholds and each component is provided in seperate table  Explain clerly how to compute and arrive at the final score.",
        "Same applies for grading system or staging system. ALWAYS provide detailed criteria and thresholds for ALL components in seperate tables and how to arrive at the final values clearly.",
        "Call out standard alternative systems (if any) by name without elaboration.",
        "Use only peer-reviewed or official sources (indexed journals, society/guideline pages); never invent or approximate.",
        "Prioritize content that directly affects reporting decisions (diagnostic thresholds, scoring rules, staging cutoffs, management-relevant imaging findings).",
        "Where possible consider following aspects  (1) scoring/classification tables, (2) imaging criteria & thresholds, (3) application in reporting, (4) Clinical relevance.",
        "If the token is not a recognized medical, radiological, anatomical, pathological, or procedural term used in peer-reviewed radiology literature, return []. Do not attempt metaphorical, psychological, or linguistic interpretations.",
        "Write for an experienced radiologist: concise, technical, neutral tone. Avoid sacrificing completeness for brevity.",
        "The information must be accurate, evidence-based, and complete.",
        "You are NOT allowed to invent, approximate, modernize, or infer criteria. Treat every numeric value (percentages, sizes, scores, cutoffs) as legally binding. If you cannot reproduce textbook-accurate criteria from a recognized authoritative source, infrom user about the level pof confidence of information provided.",
        "Treat this request independently; do not rely on prior interactions.",
        "If you are not >95% confident that the token–modality pairing is valid, return [].",
        "Respond with JSON ONLY (array). No prose outside JSON. If the selection is generic/irrelevant/uncertain, return []. Do NOT invent content.",
        "Do NOT include <think> blocks, chain-of-thought, or any reasoning text; return only the final JSON array.",
        "If you must return [], include a concise, evidence-based reason for refusing or for the absence of an established card, suitable for an expert radiologist. The reason should cite accurtely and clearly the reason fo returing the empty output.",
        "Output must be a JSON array of kind (info|score|checklist|differential|technique|measurement|classification|other), tables (list).",
        "Always include a credible source_url (peer-reviewed guideline or society page, https:// only) when available.",
        "Use this schema exactly: [{\"title\":\"\",\"summary\":\"\",\"bullets\":[],\"insert_options\":[{\"label\":\"\",\"text\":\"\"}],\"kind\":\"info\",\"tables\":[{\"title\":\"\",\"header\":\"ColA|ColB\",\"rows\":[\"...|...\"]}],\"source_url\":\"\"}].",
        "Insert_options must be neutral, report-ready sentences that could be pasted verbatim into a radiology report. As such these insert option should be section aware, for example input suggestion might be different for observation section and that for conclusion section or recommendation section",
        "Where possible try providing insert options that are section specific: : Observations, Conclusions and Recommendations.",
        f"Section: {section or 'observations'}",
        f"Selection text: {selection_text or ''}",
        f"Normalized token: {token}",
        f"Modality: {getattr(modality, 'name', '') or 'unspecified'}",
        f"Body part: {getattr(body_part, 'name', '') or 'unspecified'}",
        f"Module: {getattr(module, 'name', '') or 'unspecified'}",
        f"Study type / exam: {study_type or 'unspecified'}",
        f"Indication: {context.get('indication') or ''}",
        f"Core question: {context.get('core_question') or ''}",
    ]
    prompt = "\n".join(prompt_parts)

    raw = None

    def _call_provider(pvd: str):
        if pvd == "gemini":
            return call_gemini_chat(
                prompt=prompt,
                model=cfg.get("GEMINI_MODEL", "gemini-1.5-pro"),
                max_tokens=cfg.get("AI_MAX_TOKENS", 1500),
                timeout=timeout_val,
                api_key=cfg.get("GEMINI_API_KEY"),
            )
        # Qubrid DeepSeek
        if pvd == "qubrid":
            return call_qubrid_deepseek(
                prompt=prompt,
                model=cfg.get("QUBRID_MODEL") or "deepseek-ai/deepseek-r1-distill-llama-70b",
                max_tokens=cfg.get("AI_MAX_TOKENS", 1500),
                timeout=timeout_val,
                api_key=cfg.get("QUBRID_API_KEY"),
            )
        # OpenAI
        openai_model = cfg.get("AI_MODEL") or "gpt-4o"
        try:
            return call_openai_chat(
                prompt=prompt,
                model=openai_model,
                max_tokens=cfg.get("AI_MAX_TOKENS", 1500),
                timeout=timeout_val,
                api_key=cfg.get("OPENAI_API_KEY"),
            )
        except Exception as exc:
            # Retry once with gpt-4o if model id is invalid
            if "invalid model" in str(exc).lower() and openai_model != "gpt-4o":
                return call_openai_chat(
                    prompt=prompt,
                    model="gpt-4o",
                    max_tokens=cfg.get("AI_MAX_TOKENS", 1500),
                    timeout=timeout_val,
                    api_key=cfg.get("OPENAI_API_KEY"),
                )
            raise

    used_provider = provider_label
    try:
        raw = _call_provider(provider)
    except requests.exceptions.ReadTimeout:
        logger.warning("AI provider timed out: %s", provider)
        # Retry once
        try:
            raw = _call_provider(provider)
        except requests.exceptions.ReadTimeout:
            logger.warning("AI provider timed out again: %s", provider)
            # Offer fallback to OpenAI
            if provider != "openai" and cfg.get("OPENAI_API_KEY"):
                try:
                    raw = _call_provider("openai")
                    used_provider = "openai"
                    fallback_used = True
                except Exception:
                    logger.exception("OpenAI fallback failed after timeout on %s", provider)
                    return []
            else:
                return []
        except Exception:
            logger.exception("AI helper generation failed after timeout retry")
            return []
    except Exception:
        logger.exception("AI helper generation failed")
        return []

    parsed_cards = _parse_cards(raw)
    cards = _validate_cards(parsed_cards, selection_token=token)
    if not cards:
        def _extract_reason(r):
            if r is None:
                return ""
            text = str(r).strip()
            # If the model included a <think> block, prefer content outside it; fall back to the think text
            think_match = re.search(r"<think>(.*?)</think>", text, flags=re.DOTALL)
            if think_match:
                after_think = (text[: think_match.start()] + text[think_match.end():]).strip()
                text = after_think or think_match.group(1).strip()
            # Strip code fences
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.MULTILINE).strip()
            # Remove a naked leading [] marker so we can parse following JSON/lines cleanly
            text = re.sub(r"^\[\]\s*", "", text).strip()
            # Try structured JSON extraction first
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    if parsed.get("reason"):
                        return str(parsed["reason"]).strip()
                    if parsed.get("summary"):
                        return str(parsed["summary"]).strip()
                if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
                    if parsed[0].get("reason"):
                        return str(parsed[0]["reason"]).strip()
                    if parsed[0].get("summary"):
                        return str(parsed[0]["summary"]).strip()
            except Exception:
                pass
            # Regex fallback: grab the reason field if present
            m = re.search(r'"reason"\s*:\s*"([^"]+)"', text, flags=re.IGNORECASE)
            if m:
                return m.group(1).strip()
            m = re.search(r"\breason\b\s*[:\-]\s*(.+)$", text, flags=re.IGNORECASE)
            if m:
                return m.group(1).strip()
            # Final fallback: collapse whitespace and return full text without truncation
            text = re.sub(r"\s+", " ", text).strip()
            return text

        reason = _extract_reason(raw) or ""
        # Attempt to salvage a valid card if the reason itself contains JSON card content
        if reason:
            salvage_cards_raw = _parse_cards(reason)
            salvage_cards = _validate_cards(salvage_cards_raw, selection_token=token)
            if salvage_cards:
                return salvage_cards
            # If validation still fails but we parsed something, surface a best-effort card
            salvage_fallback = _make_salvage_card_from_parsed(salvage_cards_raw, reason)
            if salvage_fallback:
                return salvage_fallback
        # If parsed_cards had content but failed validation, surface a best-effort card
        if parsed_cards:
            salvage_fallback = _make_salvage_card_from_parsed(parsed_cards, reason)
            if salvage_fallback:
                return salvage_fallback
        warn_payload = {
            "raw_response": raw[:2000] if isinstance(raw, str) else raw,
            "parsed_cards": parsed_cards,
            "token": token,
            "section": section,
            "modality_name": getattr(modality, "name", None),
            "body_part_name": getattr(body_part, "name", None),
            "module_name": getattr(module, "name", None),
            "fallback_used": fallback_used,
            "reason": reason,
            "provider": provider,
        }
        logger.warning("AI helper returned no valid cards", extra=warn_payload)
        try:
            print(f"[AI helper] No valid cards. Context: {warn_payload}")
        except Exception:
            pass

        # Return a non-persisted placeholder card to inform the frontend
        return _make_no_card(reason)

    saved: List[SmartHelperCard] = []
    for card in cards:
        definition_json: dict[str, Any] = {}

        if card.get("tables"):
            tables_out = []
            for tbl in card["tables"]:
                raw_header = tbl.get("header") or tbl.get("headers") or ""
                if isinstance(raw_header, list):
                    headers = [str(h).strip() for h in raw_header]
                elif isinstance(raw_header, str):
                    headers = raw_header.split("|") if raw_header else []
                else:
                    headers = []
                rows_raw = [
                    (row.split("|") if isinstance(row, str) else row) for row in (tbl.get("rows") or [])
                ]
                if headers:
                    normalized_rows = []
                    for cells in rows_raw:
                        cells = cells or []
                        if len(cells) < len(headers):
                            cells = cells + [""] * (len(headers) - len(cells))
                        elif len(cells) > len(headers):
                            cells = cells[: len(headers)]
                        normalized_rows.append(cells)
                else:
                    normalized_rows = rows_raw
                tables_out.append({
                    "title": tbl.get("title"),
                    "headers": headers,
                    "rows": normalized_rows,
                })
            if tables_out:
                definition_json["tables"] = tables_out

        if card.get("bullets"):
            definition_json["bullet_groups"] = [{
                "title": None,
                "style": "bullets",
                "items": card.get("bullets") or [],
            }]

        if fallback_used:
            definition_json["fallback_provider"] = "openai"

        row = SmartHelperCard(
            title=card["title"],
            summary=card["summary"],
            bullets_json=card["bullets"],
            insert_options_json=card["insert_options"],
            kind=_kind_enum(card["kind"]),
            section=section_enum or SmartHelperSectionEnum.ANY,
            token=token,
            modality=modality,
            body_part=body_part,
            module=module,
            priority=5,
            is_active=True,
            source="ai-unverified",
            generated_for_token=token,
            generated_hash=dedupe,
            definition_json=definition_json,
        )
        row.source_detail = f"ai-{used_provider or provider_label or provider}"
        db.session.add(row)
        saved.append(row)

    db.session.commit()

    _increment_quota(user, cfg)
    return saved
