import json
import logging
import os
from typing import Dict, List, Tuple

# Optional dependencies: prefer to import if available, otherwise use fallbacks.
try:
    import json_repair as _json_repair  # type: ignore
except Exception:  # pragma: no cover - dev convenience
    _json_repair = None  # Fallback to standard json

try:
    from vertexai.generative_models import GenerationConfig as _GenConfig, GenerativeModel as _GenModel  # type: ignore
except Exception:  # pragma: no cover - dev convenience
    _GenConfig = None
    _GenModel = None

# Optional embeddings support for similarity scoring
try:  # pragma: no cover - optional dependency
    from vertexai.language_models import TextEmbeddingModel as _EmbModel  # type: ignore
except Exception:  # pragma: no cover - dev convenience
    _EmbModel = None

from utils import MODEL_FLASH


ALLOWED_CLASSES = [
    "General Industry News",
    "Competitors",
    "M&A & Investments",
    "Travel Providers",
    "Financial Reports / Info",
    "Research & Reports",
]

# Optional file to allow admins to tweak scoring/classification guidance
# Cache for prompt embedding to avoid recomputing every request
_CACHED_PROMPT_TEXT: str = ""
_CACHED_PROMPT_EMBEDDING: list[float] | None = None


def _load_custom_prompt() -> str:
    """Load custom prompt from Firestore config/dev.prompt_weekly_compose.

    Returns empty string if nothing is configured.
    """
    try:
        from google.cloud import firestore  # lazy import
        import os as _os
        db = firestore.Client(
            project=_os.getenv('PROJECT_ID') or None,
            database=_os.getenv('FIRESTORE_DATABASE_ID', '(default)')
        )
        doc = db.collection("config").document("dev").get()
        if doc.exists:
            text = doc.to_dict().get("prompt_weekly_compose", "")
            if isinstance(text, str) and text.strip():
                return text.strip()
    except Exception:
        logging.debug("ComposeWeekly: Firestore prompt not available.")
    return ""


def _normalise_classification(raw: str) -> str:
    """Map Gemini output to one of the allowed classes."""
    if not raw:
        return ALLOWED_CLASSES[0]

    cleaned = raw.strip().lower()
    lookup = {c.lower(): c for c in ALLOWED_CLASSES}
    if cleaned in lookup:
        return lookup[cleaned]

    # Attempt partial match (e.g. "financial reports" -> "Financial Reports / Info")
    for allowed in ALLOWED_CLASSES:
        if cleaned in allowed.lower() or allowed.lower() in cleaned:
            return allowed

    logging.warning("Unexpected classification '%s', defaulting to '%s'", raw, ALLOWED_CLASSES[0])
    return ALLOWED_CLASSES[0]


def _build_prompt(items: List[Dict[str, str]]) -> str:
    items_json = json.dumps(items, ensure_ascii=False)
    classes = ", ".join(ALLOWED_CLASSES)
    custom = _load_custom_prompt()
    addendum = f"\n\nAdditional CI instructions (for scoring/classification):\n{custom}\n" if custom else ""
    return f"""
You are assisting the Amadeus Competitive Intelligence team. For each news item provide:
- "gemini_comment": one or two sentences on why this news matters to Amadeus. Avoid marketing fluff.
- "gemini_classification": choose exactly one of: {classes}. Use the wording exactly as listed.{addendum}

Return a JSON array with objects formatted as:
[
  {{
    "id": "<id from input>",
    "gemini_comment": "<comment>",
    "gemini_classification": "<one allowed class>"
  }}
]

Do not wrap the JSON in markdown code fences and do not include additional commentary.

News items to analyze:
{items_json}
""".strip()


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors. Returns -1..1; safe on zeros."""
    try:
        import math
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return dot / (na * nb)
    except Exception:
        return 0.0


def _embed_text(text: str) -> List[float] | None:
    """Return embedding vector for text using Vertex AI if available; else None."""
    if not text or _EmbModel is None:
        return None
    try:
        model = _EmbModel.from_pretrained("text-embedding-005")  # falls back if unavailable
        out = model.get_embeddings([text])
        if not out:
            return None
        emb = out[0].values if hasattr(out[0], "values") else getattr(out[0], "embedding", None)
        # Normalize output to a plain list[float]
        if emb is None:
            return None
        # Some SDK versions expose .values, others .values is nested
        if hasattr(emb, "values"):
            emb = emb.values
        return list(emb)
    except Exception:
        return None


def _fallback_classify(title: str, abstract: str, class_daily: str = "") -> str:
    """Heuristic classification fallback when Gemini is unavailable."""
    text = f"{title} {abstract} {class_daily}".lower()
    if any(k in text for k in ["acquire", "merger", "m&a", "investment", "raises", "funding"]):
        return "M&A & Investments"
    if any(k in text for k in ["revenue", "profits", "earnings", "quarter", "q1", "q2", "q3", "q4", "guidance", "financial"]):
        return "Financial Reports / Info"
    if any(k in text for k in ["report", "study", "survey", "research", "insights"]):
        return "Research & Reports"
    if any(k in text for k in ["airline", "hotel", "ot a", "ota ", "carrier", "airport", "agency", "rail", "bus", "supplier", "provider"]):
        return "Travel Providers"
    if any(k in text for k in ["competitor", "rival", "vs ", "vs.", "battle", "compete", "market share"]):
        return "Competitors"
    # Map class_daily hints
    if class_daily:
        mapped = _normalise_classification(class_daily)
        if mapped:
            return mapped
    return "General Industry News"


def _fallback_comment(title: str, abstract: str) -> str:
    """Build a concise, non-fluffy comment as a fallback."""
    base = title.strip() or abstract.strip()
    if not base:
        return "Relevant industry development with potential impact on Amadeus."
    return f"Relevance for Amadeus: {base[:180]}"  # keep it short


def _parse_model_output(text: str) -> List[Dict[str, str]]:
    text = (text or "").strip().replace("```json", "").replace("```", "").strip()
    if _json_repair is not None:
        parsed = _json_repair.loads(text)
    else:
        parsed = json.loads(text)
    if isinstance(parsed, dict) and "items" in parsed:
        parsed = parsed["items"]
    if not isinstance(parsed, list):
        raise ValueError("Gemini response is not a list")
    results: List[Dict[str, str]] = []
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id", ""))
        comment = str(entry.get("gemini_comment", "")).strip()
        classification = _normalise_classification(str(entry.get("gemini_classification", "")))
        # Score is optional but encouraged; coerce to 1..100 with default 50
        score_val = 0
        try:
            score_val = int(str(entry.get("gemini_score", "")).strip() or 0)
        except Exception:
            score_val = 0
        score_val = max(1, min(100, score_val)) if score_val else 50
        results.append({
            "id": entry_id,
            "gemini_comment": comment,
            "gemini_classification": classification,
            "gemini_score": score_val,
        })
    return results


def _add_similarity_scores(
    results: List[Dict[str, str]],
    original_items: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """Add similarity scores to results if SIM_WEIGHT > 0 and custom prompt exists."""
    sim_weight_env = os.getenv("COMPOSE_WEEKLY_SIM_WEIGHT", "").strip()
    try:
        SIM_WEIGHT = max(0.0, min(1.0, float(sim_weight_env))) if sim_weight_env else 0.0
    except Exception:
        SIM_WEIGHT = 0.0

    if SIM_WEIGHT <= 0.0:
        return results

    # Load and embed custom prompt
    prompt_text = _load_custom_prompt()
    if not prompt_text:
        return results

    global _CACHED_PROMPT_TEXT, _CACHED_PROMPT_EMBEDDING  # noqa: PLW0603
    if prompt_text != _CACHED_PROMPT_TEXT:
        _CACHED_PROMPT_EMBEDDING = _embed_text(prompt_text) or None
        _CACHED_PROMPT_TEXT = prompt_text

    prompt_vec = _CACHED_PROMPT_EMBEDDING
    if prompt_vec is None:
        return results

    # Create lookup from original items by id
    items_by_id = {str(item.get("id", idx)): item for idx, item in enumerate(original_items)}

    # Add similarity to each result
    for result in results:
        result_id = result.get("id")
        if result_id not in items_by_id:
            continue

        original = items_by_id[result_id]
        title = str(original.get("title", "") or "").strip()
        abstract = str(original.get("abstract", "") or "").strip()
        class_daily = str(original.get("class_daily", "") or "").strip()

        try:
            item_vec = _embed_text(f"{title}\n\n{abstract}\n\n{class_daily}")
            if item_vec is not None:
                cos = _cosine_similarity(prompt_vec, item_vec)  # -1..1
                sim_score = int(round(((cos + 1.0) / 2.0) * 100))  # 0..100
                result["similarity"] = sim_score
        except Exception:
            logging.debug("Failed to compute similarity for item %s", result_id)

    return results


def generate_compose_weekly_insights(items: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], str]:
    """Generate Gemini comments and classifications for uploaded news items.

    Falls back to a local heuristic if Vertex AI is unavailable or returns errors,
    so the UI can proceed without failing the workflow.
    """
    if not items:
        return [], "empty"

    logging.info("Generating compose-weekly insights for %d item(s)", len(items))

    # Try the online Gemini path first (unless forced to fallback)
    force_fallback = os.getenv("COMPOSE_WEEKLY_FALLBACK", "").strip().lower() in {"1", "true", "yes"}
    try:
        if force_fallback:
            raise RuntimeError("Forced fallback via COMPOSE_WEEKLY_FALLBACK env var")
        if _GenModel is None or _GenConfig is None:
            raise RuntimeError("Vertex AI SDK unavailable (no vertexai module)")
        prompt = _build_prompt(items)
        model = _GenModel(
            model_name=MODEL_FLASH,
            generation_config=_GenConfig(
                temperature=0.2,
                max_output_tokens=1024,
            ),
        )
        responses = model.generate_content([prompt])
        gemini_results = _parse_model_output(responses.text or "")
        # Add similarity scores to Gemini results if configured
        gemini_results = _add_similarity_scores(gemini_results, items)
        return gemini_results, "gemini"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logging.exception("Gemini generation failed, using local fallback: %s", exc)

    # Fallback: heuristic generation
    results: List[Dict[str, str]] = []
    # Prepare similarity reference from custom prompt, if available
    sim_weight_env = os.getenv("COMPOSE_WEEKLY_SIM_WEIGHT", "").strip()
    try:
        SIM_WEIGHT = max(0.0, min(1.0, float(sim_weight_env))) if sim_weight_env else 0.0
    except Exception:
        SIM_WEIGHT = 0.3
    prompt_vec = None
    if SIM_WEIGHT > 0.0:
        prompt_text = _load_custom_prompt()
        global _CACHED_PROMPT_TEXT, _CACHED_PROMPT_EMBEDDING  # noqa: PLW0603
        if prompt_text and prompt_text != _CACHED_PROMPT_TEXT:
            _CACHED_PROMPT_EMBEDDING = _embed_text(prompt_text) or None
            _CACHED_PROMPT_TEXT = prompt_text
        prompt_vec = _CACHED_PROMPT_EMBEDDING
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        entry_id = str(item.get("id", idx))
        title = str(item.get("title", "") or "").strip()
        abstract = str(item.get("abstract", "") or "").strip()
        class_daily = str(item.get("class_daily", "") or "").strip()

        classification = _fallback_classify(title, abstract, class_daily)
        comment = _fallback_comment(title, abstract)
        # Optional: similarity with setup prompt using embeddings
        sim_score = None
        if SIM_WEIGHT > 0.0:
            try:
                if prompt_vec is not None:
                    item_vec = _embed_text(f"{title}\n\n{abstract}\n\n{class_daily}")
                    if item_vec is not None:
                        cos = _cosine_similarity(prompt_vec, item_vec)  # -1..1
                        sim_score = int(round(((cos + 1.0) / 2.0) * 100))  # 0..100
            except Exception:
                pass
        results.append({
            "id": entry_id,
            "gemini_comment": comment,
            "gemini_classification": classification,
            **({"similarity": sim_score} if sim_score is not None else {}),
        })

    return results, "fallback"
