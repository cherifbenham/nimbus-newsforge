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
    from vertexai.generative_models import \
        GenerationConfig as _GenConfig  # type: ignore
    from vertexai.generative_models import GenerativeModel as _GenModel
except Exception:  # pragma: no cover - dev convenience
    _GenConfig = None
    _GenModel = None

# Optional embeddings support for similarity scoring
try:  # pragma: no cover - optional dependency
    from vertexai.language_models import \
        TextEmbeddingModel as _EmbModel  # type: ignore
except Exception:  # pragma: no cover - dev convenience
    _EmbModel = None

from utils import LOCATION, MODEL_FLASH, MODEL_PRO, PROJECT_ID

# Initialize Vertex AI with correct project
try:
    import vertexai
    vertexai.init(project=PROJECT_ID, location=LOCATION)
except Exception:
    pass  # Will fall back to heuristic classification

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
        import os as _os

        from google.cloud import firestore  # lazy import
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
You are a senior Competitive Intelligence analyst for Nimbus Travel, a leading travel technology company. Your role is to provide actionable insights for strategic decision-making.

For each news item, you must provide THREE outputs:

1. **"refined_title"**: Transform the title and abstract into a concise, two-part format:
   - PART 1 (in bold using markdown **text**): Extract the core essence or main point from the title AND abstract
   - PART 2 (NOT in bold): Add clarifying or complementary information that provides context
   - The refined title should be concise but informative (not just copy-pasting the original title)
   - Use both the title and abstract to understand the full story

   Examples:
     * Original title: "Air France-KLM buys minority stake in Canada's WestJet"
       Original abstract: "The European airline group will acquire 19.9% of WestJet's parent company for $600M"
       Refined: "**Air France-KLM acquires 19.9% stake in WestJet** for $600M to strengthen North American network"

     * Original title: "Sabre reports Q3 revenue growth"
       Original abstract: "Travel technology company posts 5% increase driven by distribution segment recovery"
       Refined: "**Sabre reports 5% Q3 revenue growth** driven by distribution segment recovery"

     * Original title: "Emirates adds Barcelona route"
       Original abstract: "The Dubai-based carrier will operate daily flights starting March 2025"
       Refined: "**Emirates launches daily Barcelona service** starting March 2025"

2. **"gemini_comment"**: This is the CI comment - a separate analytical insight that:
   - Extracts specific metrics and numbers (percentages, revenue figures, growth rates, market share, etc.)
   - Identifies strategic implications for Nimbus Travel (market opportunities, competitive threats, technology trends)
   - Provides comparative context when available (year-over-year changes, regional differences, competitor positioning)
   - Focuses on business impact rather than describing what happened
   - Is concise (1-3 sentences) but packed with insights

GOOD COMMENT EXAMPLES:
- "All regions are operating above winter 2019 capacity levels, except for South-East Asia. North America and Europe are expected to grow 2.1% and 4.6% respectively."
- "Sabre claims airlines can achieve up to a 3.5% uplift in overall revenue."
- "While Navan has improved its financial performance, it continues to operate at a loss. For the fiscal year ending January 2025, the company posted a net loss of $18M, though this was an improvement from the previous year's $331.5M loss."

BAD COMMENT EXAMPLES (too generic):
- "This is relevant for our company"
- "Interesting development in the travel industry"
- "Will Agentic AI Turn OTAs Into Passive Order Takers?"

3. **"gemini_classification"**: Choose exactly one of: {classes}. Use the wording exactly as listed.

CLASSIFICATION GUIDANCE:
- **General Industry News**: Industry-wide operational metrics and trends (passenger numbers, load factors, booking volumes, traffic statistics, capacity changes, fleet updates, route launches, regulatory changes, government policies, compliance updates, infrastructure developments)
- **Competitors**: Direct competitors' activities, strategies, market positioning, competitive moves
- **M&A & Investments**: Mergers, acquisitions, investments, funding rounds, stakes, partnerships with equity involvement
- **Travel Providers**: Airlines, hotels, OTAs, agencies, rail, bus, car rental, and other travel service providers' business activities
- **Financial Reports / Info**: Revenue, profits, earnings, financial results, quarterly reports, guidance, financial performance
- **Research & Reports**: Market studies, industry surveys, research findings, analyst reports, trend analyses{addendum}

Return a JSON array with objects formatted as:
[
  {{
    "id": "<id from input>",
    "refined_title": "**Bold essence** clarification text",
    "gemini_comment": "<insightful, data-driven comment>",
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


def _project_similarity_to_range(cosine_sim: float, min_output: float = 0.5, max_output: float = 0.99) -> float:
    """
    Project cosine similarity (-1..1) to a custom range (default: 0.5..0.99).

    Args:
        cosine_sim: Raw cosine similarity value (-1 to 1)
        min_output: Minimum output value (default 0.5)
        max_output: Maximum output value (default 0.99)

    Returns:
        Similarity score in the range [min_output, max_output]
    """
    # First normalize cosine similarity from -1..1 to 0..1
    normalized = (cosine_sim + 1.0) / 2.0

    # Then scale to the target range [min_output, max_output]
    output_range = max_output - min_output
    projected = min_output + (normalized * output_range)

    # Clamp to ensure we stay within bounds
    return max(min_output, min(max_output, projected))


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
    # Industry operational metrics keywords - should be General Industry News
    if any(k in text for k in ["passengers", "load factor", "booking", "traffic", "capacity", "fleet", "route launch", "regulation", "regulatory", "compliance", "infrastructure"]):
        return "General Industry News"
    return "General Industry News"


def _fallback_comment(title: str, abstract: str) -> str:
    """Build a concise, non-fluffy comment as a fallback."""
    base = title.strip() or abstract.strip()
    if not base:
        return "Relevant industry development with potential impact on our company."
    return f"Relevance for our company: {base[:180]}"  # keep it short


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
        refined_title = str(entry.get("refined_title", "")).strip()
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
            "refined_title": refined_title,
            "gemini_comment": comment,
            "gemini_classification": classification,
            "similarity": score_val,  # Changed from gemini_score to match frontend schema
        })
    return results


def _add_similarity_scores(
    results: List[Dict[str, str]],
    original_items: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """Add similarity scores to results if SIM_WEIGHT > 0 and custom prompt exists."""
    sim_weight_env = os.getenv("COMPOSE_WEEKLY_SIM_WEIGHT", "").strip()
    try:
        SIM_WEIGHT = max(0.0, min(1.0, float(sim_weight_env))) if sim_weight_env else 0.3  # Default to 0.3
    except Exception:
        SIM_WEIGHT = 0.3

    logging.info("Similarity scoring enabled with SIM_WEIGHT=%.2f", SIM_WEIGHT)

    if SIM_WEIGHT <= 0.0:
        logging.info("Similarity scoring disabled (SIM_WEIGHT=0)")
        return results

    # Load and embed custom prompt
    prompt_text = _load_custom_prompt()
    if not prompt_text:
        logging.warning("No custom prompt found for similarity scoring, using default scoring context")
        # Use a default prompt about Nimbus relevance
        prompt_text = """
        Nimbus Travel is a travel technology company providing solutions for airlines, hotels,
        travel agencies, and corporate travelers. We focus on airline IT systems, hotel property management,
        distribution (GDS), corporate travel management, payments, and travel analytics.
        """

    global _CACHED_PROMPT_TEXT, _CACHED_PROMPT_EMBEDDING  # noqa: PLW0603
    if prompt_text != _CACHED_PROMPT_TEXT:
        logging.info("Embedding reference prompt (%d chars)", len(prompt_text))
        _CACHED_PROMPT_EMBEDDING = _embed_text(prompt_text) or None
        _CACHED_PROMPT_TEXT = prompt_text
        if _CACHED_PROMPT_EMBEDDING:
            logging.info("Reference prompt embedded successfully")
        else:
            logging.warning("Failed to embed reference prompt")

    prompt_vec = _CACHED_PROMPT_EMBEDDING
    if prompt_vec is None:
        logging.warning("No prompt embedding available, skipping similarity scoring")
        return results

    # Create lookup from original items by id
    items_by_id = {str(item.get("id", idx)): item for idx, item in enumerate(original_items)}

    # Add similarity to each result
    computed_count = 0
    for result in results:
        result_id = result.get("id")
        if result_id not in items_by_id:
            continue

        original = items_by_id[result_id]
        title = str(original.get("title", "") or "").strip()
        abstract = str(original.get("abstract", "") or "").strip()
        class_daily = str(original.get("class_daily", "") or "").strip()

        try:
            item_text = f"{title}\n\n{abstract}\n\n{class_daily}"
            item_vec = _embed_text(item_text)
            if item_vec is not None:
                cos = _cosine_similarity(prompt_vec, item_vec)  # -1..1

                # Simple linear scaling from -1..1 to 0..100
                sim_score = int(round(((cos + 1.0) / 2.0) * 100))
                result["similarity"] = sim_score
                computed_count += 1
        except Exception as e:
            logging.debug("Failed to compute similarity for item %s: %s", result_id, e)

    logging.info("Computed similarity scores for %d/%d items", computed_count, len(results))
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
            model_name=MODEL_PRO,
            generation_config=_GenConfig(
                temperature=0.2,
                max_output_tokens=8000,  # Increased for multiple items (12 items * ~500 tokens each)
            ),
        )
        responses = model.generate_content([prompt])
        raw_text = responses.text or ""
        logging.info("Gemini raw response length: %d characters", len(raw_text))
        logging.debug("Gemini raw response: %s", raw_text[:500])  # Log first 500 chars
        gemini_results = _parse_model_output(raw_text)
        logging.info("Parsed %d results from Gemini", len(gemini_results))
        if gemini_results:
            logging.debug("First result: %s", gemini_results[0])
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
