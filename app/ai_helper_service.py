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
                    return f"Sources: <a href=\"{url}\" target=\"_blank\">{url}</a>"
            return None

        # Search for sources in the raw bullets before truncation
        allowed_source = _first_link(raw_bullets) or _first_link(bullets)
        if not allowed_source:
            if "tnm" in (selection_token or "").lower():
                allowed_source = "Sources: <a href=\"https://www.canstaging.org/tool?tnm_version=v8\" target=\"_blank\">canstaging.org</a>"
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
    if _any_card_exists(token, section_enum, modality, body_part, module):
        return []
    if _recent_ai_card_exists(token, section_enum, modality, body_part, module, dedupe):
        return []

    if not _quota_allows(user, cfg):
        logger.info("AI helper quota exceeded for user %s", getattr(user, "id", None))
        return []

    prompt_parts = [
        "You are an expert radiologist colleague creating ONE comprehensive helper card for experienced radiologists.",
        "Behave like a well-read radiology assistant (ChatGPT/Gemini-level) that brings in relevant, reputable knowledge to enrich the answer.",
        "Prioritize content that directly affects reporting decisions (diagnostic thresholds, scoring rules, staging cutoffs, management-relevant imaging findings). De-prioritize general explanations.",
        "Content priority order: (1) scoring/classification tables, (2) imaging criteria & thresholds, (3) application in reporting, (4) brief clinical relevance. If space is limited, drop lower-priority items.",
        "Write for an experienced radiologist: concise, technical, neutral tone. Assume baseline knowledge; avoid teaching language.",
        "The information must be accurate, evidence-based, and complete within the constraints.",
        "You are NOT allowed to invent, approximate, modernize, or infer criteria. Treat every numeric value (percentages, sizes, scores, cutoffs) as legally binding. If you cannot reproduce textbook-accurate criteria from a recognized authoritative source, return [].",
        "Accuracy is more important than completeness. If any component (criteria, thresholds, categories) is incomplete or uncertain, return [].",
        "Every score, cutoff, category, or classification must be traceable to a named authoritative source. If no authoritative source applies, return [].",
        "If you are not certain from a verifiable source, return [] rather than approximating. Do not invent values, thresholds, or categories.",
        "Treat this request independently; do not rely on prior interactions. Use only information you can attribute to credible sources.",
        "Respond with JSON ONLY (array). No prose outside JSON. If the selection is generic/irrelevant/uncertain, return []. Do NOT invent content.",
        "Do NOT include <think> blocks, chain-of-thought, or any reasoning text; return only the final JSON array.",
        "If you must return [], include a concise, evidence-based reason for refusing or for the absence of an established card, suitable for an expert radiologist. The reason should cite modality applicability or lack of authoritative sources.",
        "If the existence, components, or thresholds of a score/classification are uncertain, return [] rather than approximating.",
        "Output must be a JSON array of length 1 with keys: title (<=120), summary (<=360), bullets (<=8), insert_options (<=3 {label,text}), kind (info|score|checklist|differential|technique|measurement|classification|other), tables (list).",
        "Use this schema exactly: [{\"title\":\"\",\"summary\":\"\",\"bullets\":[],\"insert_options\":[{\"label\":\"\",\"text\":\"\"}],\"kind\":\"info\",\"tables\":[{\"title\":\"\",\"header\":\"ColA|ColB\",\"rows\":[\"...|...\"]}]}].",
        "If needed, create multiple tables. Each table must have >=3 rows unless the system truly has fewer.",
        "When a score/classification exists, create separate tables for: (a) criteria/components with points or definitions, and (b) severity/grade interpretation. Do NOT merge these into one table.",
        "For any score/staging/classification, include ALL official components and categories; partial or simplified versions are not acceptable. Add separate tables when multiple components exist.",
        "If a score is a sum of multiple subscores/components, include a separate table for each subscore/component, then a combined total/interpretation table with severity bands. Include how to determine each tier/value (e.g., what findings qualify for each category).",
        "If the requested concept matches a known standardized score or classification, reproduce the official criteria verbatim in structure and thresholds. Do not paraphrase numeric cutoffs. Do not synthesize or modernize scores unless an officially published revision exists.",
        "Cover broadly (not just the literal query): what the concept means/used for; radiologic and clinical significance/utility; relevant scores/classifications/staging; how scoring/classification is done (detailed criteria/points); key imaging patterns; how to apply in clinical scenarios.",
        "Focus on imaging criteria, measurements, thresholds, diagnostic criteria, imaging patterns, classification/staging systems; avoid definitions and PHI.",
        "Tables: include only if a real, established score/classification exists; never invent rows. If none, set tables: []. Do not return empty table rows.",
        "Prefer to present data in tabular manner. Do not hesitate to create more than one table if needed for clarity.",
        "Bullets: concise but complete imaging pearls, measurement thresholds, key differentials if applicable, and 1-2 pitfalls if applicable. Do not duplicate table content. Last bullet must be 'Sources:' followed by 1–2 direct, specific authoritative references with full article-level URLs (peer-reviewed radiology articles or official society/guideline pages). Avoid homepages, root domains, and fabricated or dead links; use the most precise page that actually exists.",
        "Prefer Radiopaedia (article-level), Radiology Assistant, RSNA/AJR/Radiology reviews, NICE/ACR/ESGAR/EASL guidelines. If uncertain, return [].",
        "Insert_options must be neutral, report-ready sentences that could be pasted verbatim into a radiology report. Avoid recommendations, differentials, or management advice.",
        "When Section is 'observations', emphasize imaging findings and criteria. When 'conclusion', emphasize classification, severity, or score interpretation. When 'technique', emphasize protocol-dependent considerations.",
        "If the score or criteria are modality-specific, restrict content strictly to the provided Modality. Do not generalize across modalities.",
        "Do not add meta commentary or offers. Return only the JSON array.",
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

    provider = (force_provider or cfg.get("AI_PROVIDER") or "openai").lower()
    raw = None
    fallback_used = False
    timeout_val = force_timeout or cfg.get("AI_REQUEST_TIMEOUT", 15)

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
            # Preserve reasoning inside <think> if present
            think_match = re.search(r"<think>(.*?)</think>", text, flags=re.DOTALL)
            if think_match:
                text = think_match.group(1).strip()
            # Strip code fences
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.MULTILINE).strip()
            # If model returned a JSON array string, treat as empty
            if text == "[]":
                return ""
            # Heuristic: keep tail sentences, prefer those mentioning refusal/returning []
            sentences = re.split(r"(?<=[.!?])\s+", text)
            sentences = [s.strip() for s in sentences if s.strip()]
            if not sentences:
                return ""
            # Look for refusal indicators near the end
            tail = sentences[-3:] if len(sentences) >= 3 else sentences
            refusal = [s for s in tail if re.search(r"\b(return\s*\[\]|\[\]\s*$|cannot|can't|not applicable|doesn't apply|no authoritative|uncertain|insufficient)\b", s, flags=re.IGNORECASE)]
            if refusal:
                text = " ".join(refusal)
            else:
                text = " ".join(tail)
            text = text.strip()
            if len(text) > 300:
                text = text[:300] + "…"
            return text

        reason = _extract_reason(raw) or ""
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
        placeholder = SimpleNamespace(
            id=None,
            title="No card generated",
            summary=reason,
            kind="info",
            section=section_enum or SmartHelperSectionEnum.ANY,
            bullets=[reason],
            insert_options=[],
            tags="",
            token=token,
            modality=modality,
            body_part=body_part,
            module=module,
            display_style="auto",
            source="ai-status",
            source_detail="ai-no-card",
        )
        return [placeholder]

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
        row.source_detail = "ai-new-fallback-openai" if fallback_used else "ai-new"
        db.session.add(row)
        saved.append(row)

    db.session.commit()

    # If we successfully regenerated with preferred provider, optionally remove prior OpenAI fallback cards for same token/context
    if replace_fallback and provider in {"deepseek", "qubrid"} and not fallback_used:
        q_del = db.session.query(SmartHelperCard).filter(
            SmartHelperCard.source_detail == "ai-new-fallback-openai",
            SmartHelperCard.token == token,
        )
        if section_enum:
            q_del = q_del.filter(SmartHelperCard.section == section_enum)
        if modality:
            q_del = q_del.filter(SmartHelperCard.modality == modality)
        if body_part:
            q_del = q_del.filter(SmartHelperCard.body_part == body_part)
        if module:
            q_del = q_del.filter(SmartHelperCard.module == module)
        q_del.delete(synchronize_session=False)
        db.session.commit()

    _increment_quota(user, cfg)
    return saved
