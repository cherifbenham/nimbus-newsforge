"""
Weekly Newsletter Template Generator
Uses Gemini to generate a structured HTML newsletter from selected news items
"""

import os
from datetime import datetime
from typing import Dict, List

import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel

# Initialize Vertex AI with correct project
PROJECT_ID = os.getenv("PROJECT_ID", "nimbus-newsforge")
LOCATION = os.getenv("REGION", "europe-west4")
vertexai.init(project=PROJECT_ID, location=LOCATION)


def generate_weekly_template(news_items: List[Dict[str, str]], week_info: str = "") -> str:
    """
    Generate a weekly newsletter HTML template using Gemini

    Args:
        news_items: List of news items with title, abstract, url, gemini_classification, ci_comment
        week_info: Optional week information (e.g., "Week 41 (13-17 Oct 2025)")

    Returns:
        HTML string for the newsletter
    """

    # Prepare the prompt for Gemini
    model_name = os.getenv("MODEL_FLASH", "gemini-2.0-flash-exp")
    model = GenerativeModel(model_name)

    # Get week info
    if not week_info:
        now = datetime.now()
        week_number = now.isocalendar()[1]
        week_info = f"Week {week_number} ({now.strftime('%d %b %Y')})"

    # Build the news items text
    news_text = "\n\n".join([
        f"Title: {item.get('title', '')}\n"
        f"Abstract: {item.get('abstract', '')}\n"
        f"URL: {item.get('url', '')}\n"
        f"Classification: {item.get('gemini_classification', '')}\n"
        f"CI Comment: {item.get('ci_comment', item.get('gemini_comment', ''))}"
        for item in news_items
    ])

    prompt = f"""You are an expert newsletter editor for a competitive intelligence team in the travel industry.

Generate a professional HTML newsletter following this EXACT structure and styling:

1. **Opening paragraph**: "Dear all, You will find below a summary of the **key developments identified in {week_info}** via our Daily News Review. To access the articles, click on >."

2. **Highlights of the week section**: Create a compelling summary paragraph that highlights 3-5 most important stories with inline links. This should be engaging and capture attention.

3. **Categorized sections with specific subsections**: Organize news following this EXACT structure:

   **SECTION: Industry / Regulation**
   - Subsection: General Industry News

   **SECTION: Competitors**
   - Subsection: Sabre
   - Subsection: Travelport
   - Subsection: Google
   - Subsection: Accelya

   **SECTION: M&A and Investments**
   (No subsections - place items directly under main section)

   **SECTION: Travel Providers**
   - Subsection: Airlines
   - Subsection: Intermediaries (Online travel agencies, business travel agencies...)
   - Subsection: Hospitality
   - Subsection: Airports

   **SECTION: Financials**
   (No subsections)

   **SECTION: Research and Reports**
   (No subsections)

   **CRITICAL RULES:**
   - ONLY include sections that have at least one news item
   - ONLY include subsections that have at least one news item
   - DO NOT display empty sections or empty subsections
   - Each section must have the blue top border (div with border-top)
   - Subsections use H2 with indentation and blue color

4. **News item format**: For each news item:
   - **Title format - CRITICAL**: Transform titles to highlight the essence with clarifications
     * **DO NOT copy-paste titles literally** from the source
     * Extract the main essence/key point and make it bold
     * Add clarifying or complementary information after the bold text
     * Example transformation:
       - Source title: "Air France-KLM acquires 2.3% shareholding in WestJet"
       - Transform to: "**Air France-KLM acquires stake in WestJet** expanding their long-standing partnership with Delta Air Lines"
     * The bold part should be concise and impactful (5-10 words)
     * The clarification should add context or key details
   - Add brief summary with &ndash; separator after the title
   - **Source link - CRITICAL INSTRUCTIONS**: Determine the actual news source and use it as the link text
     * **IGNORE aggregator/redirect domains**: If URL is from newsweaver, safelinks, redirects, or similar aggregators, DO NOT use that domain name
     * **Identify the real source**: Use the article title, abstract context, or URL path to determine the actual publication
     * Examples of what to IGNORE: "newsweaver", "digestrelay", "safelinks", "protection.outlook"
     * **Extract from direct URLs**: For direct links, parse the domain
       - https://www.phocuswire.com/article → "Phocuswire"
       - https://skift.com/article → "Skift"
       - https://www.reuters.com/article → "Reuters"
     * **For aggregator URLs**: Look at title/abstract to determine source, or use generic "Source"
       - If title mentions "[Phocuswire]" or article is clearly from a known source, use that
       - Otherwise use "Source" or "Read more" as fallback
     * Capitalize properly: "phocuswire" → "Phocuswire", "reuters" → "Reuters"
     * Create link: <a href="FULL_URL">Source Name</a>
     * IMPORTANT: The link text should be the actual news source name, NOT ">" and NOT aggregator names
   - If there's a CI comment, add it in italicized paragraph with light blue background (#c5d5f9) and indented
   - **CI comment format**: MUST start with "CI comment: " followed by the actual comment text

**CRITICAL STYLING REQUIREMENTS:**
- Use EXACTLY these inline styles (copy them precisely):
  - Regular paragraphs: `style="margin: 0cm 0cm 8pt; font-size: 11pt; font-family: Arial, sans-serif; color: #000835; line-height: 14pt;"`
  - Section dividers: `style="border: none; border-top: solid #3A8BFF 1.0pt; padding: 1.0pt 0cm 0cm 0cm;"`
  - H1 (main sections): `style="margin: 0cm 0cm 6pt; break-after: avoid; border: none; padding: 0cm; font-size: 20pt; font-family: Arial, sans-serif; color: #000835; font-weight: normal;"`
  - H2 (subsections): `style="margin: 28pt 0cm 12pt 42.55pt; line-height: 16pt; break-after: avoid; font-size: 14pt; font-family: Arial, sans-serif; color: #3a8bff; font-weight: normal;"`
  - CI comments: `style="margin: 0cm 0cm 8pt 42.55pt; font-size: 10pt; font-family: Arial, sans-serif; color: #000835; line-height: 14pt; background: #c5d5f9; font-style: italic;"`
  - **IMPORTANT**: CI comments MUST begin with "CI comment: " prefix (e.g., "CI comment: Air France-KLM acquired a 2.3% shareholding in WestJet...")
  - Empty paragraphs for spacing: `<p style="margin: 0cm 0cm 8pt; font-size: 11pt; font-family: Arial, sans-serif; color: #000835; line-height: 14pt;">&nbsp;</p>`

**News items to include:**

{news_text}

**CRITICAL CI COMMENT REQUIREMENTS:**
- **EVERY news item with a CI comment MUST include it in the HTML output** - this is mandatory
- CI comments provide strategic insights and CANNOT be omitted
- Format: Always start with "CI comment: " prefix followed by the actual comment text
- Style: Use the exact CI comment styling shown above (light blue background #c5d5f9, italic, indented)
- If a news item has a CI comment in the data above, you MUST include it in the output HTML
- DO NOT skip or omit CI comments due to length - they are essential content

**Important guidelines:**
- **Title transformation is mandatory**: Extract essence (bold) + add clarifying information
  * Example: "**Emirates launches new route to Barcelona** targeting business travelers with twice-daily flights"
  * Example: "**Google integrates AI into travel search** enabling natural language queries for flight bookings"
  * DO NOT simply copy the source title - transform it to be more informative
- Keep summaries concise and actionable (use &ndash; for dash separator after title)
- **SOURCE LINKS ARE CRITICAL - READ CAREFULLY**: Identify the ACTUAL news source, not aggregator domains
  * **DO NOT USE** these aggregator/redirect domains: newsweaver, digestrelay, safelinks, protection.outlook, redirects
  * **Direct URLs**: Extract from domain (e.g., www.phocuswire.com → Phocuswire)
  * **Aggregator URLs**:
    - Check if title has source in brackets like "[Phocuswire]" - use that
    - Analyze article title/abstract to identify the publication (Skift, Reuters, Bloomberg, etc.)
    - If source unclear, use "Source" as link text
  * Remove "www." prefix and domain extension (.com, .co.uk, etc.)
  * Capitalize properly (phocuswire → Phocuswire, reuters → Reuters)
  * Wrap in anchor tag: <a href="full_url">Actual Source Name</a>
  * Example: https://www.phocuswire.com/article → <a href="https://www.phocuswire.com/article">Phocuswire</a>
- CI comments should provide strategic context or implications
- **CRITICAL**: All CI comments MUST start with the prefix "CI comment: " followed by the actual comment
- Analyze each news item's classification and map it to the correct section AND subsection
- For Competitors: identify which specific company (Sabre, Travelport, Google, Accelya) and use that subsection
- For Travel Providers: identify whether it's Airlines, Intermediaries, Hospitality, or Airports
- If a section or subsection would be empty, DO NOT include it in the output HTML
- Maintain professional tone appropriate for executive audience
- Use proper HTML entities (&ndash; for dash, &rsquo; for apostrophe, &amp; for ampersand)
- Include blank lines between sections using &nbsp; paragraphs
- Make the "Highlights of the week" section compelling with 3-5 key stories linked inline

**OUTPUT REQUIREMENTS:**
- Return ONLY the HTML content
- NO markdown code blocks or explanations
- NO empty sections or subsections
- ONLY sections with actual news items
- Link format must be: <a href="FULL_URL">SourceName</a> (NOT ">")

**EXAMPLE NEWS ITEM OUTPUTS:**
CORRECT - Title with bold essence + clarification, source link, and CI comment:
<p style="margin: 0cm 0cm 8pt; font-size: 11pt; font-family: Arial, sans-serif; color: #000835; line-height: 14pt;"><strong>Delta reports strong Q3 earnings</strong> exceeding analyst expectations &ndash; driven by loyalty program growth and premium travelers demand. <a href="https://www.phocuswire.com/delta-earnings-q3">Phocuswire</a></p>
<p style="margin: 0cm 0cm 8pt 42.55pt; font-size: 10pt; font-family: Arial, sans-serif; color: #000835; line-height: 14pt; background: #c5d5f9; font-style: italic;">CI comment: Air France-KLM acquired a 2.3% shareholding in WestJet from Delta Air Lines, expanding their partnership which began in 2009.</p>

CORRECT - Aggregator URL with title transformation:
<p style="margin: 0cm 0cm 8pt; font-size: 11pt; font-family: Arial, sans-serif; color: #000835; line-height: 14pt;"><strong>Uber and WeRide launch robotaxis in Saudi Arabia</strong> marking first deployment in the Middle East &ndash; available via the Uber platform for passenger rides in Riyadh. <a href="https://digestrelay.newsweaver.com/xyz">Phocuswire</a></p>

WRONG - Using aggregator name:
<p style="margin: 0cm 0cm 8pt; font-size: 11pt; font-family: Arial, sans-serif; color: #000835; line-height: 14pt;"><strong>News article</strong> &ndash; summary text. <a href="https://digestrelay.newsweaver.com/xyz">DigestRelay Newsweaver</a></p>"""

    config = GenerationConfig(
        temperature=0.7,
        max_output_tokens=16000,  # Increased to handle longer newsletters with CI comments
    )

    response = model.generate_content(prompt, generation_config=config)
    html_content = response.text.strip()  # type: ignore

    # Clean up any markdown code blocks if Gemini adds them
    if html_content.startswith("```html"):
        html_content = html_content.split("```html")[1]
    if html_content.startswith("```"):
        html_content = html_content.split("```", 1)[1]
    if html_content.endswith("```"):
        html_content = html_content.rsplit("```", 1)[0]

    return html_content.strip()
