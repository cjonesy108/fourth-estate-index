"""
Social media independence analyzer — Pillar 3 dimension.

Scores `social_media_independence`: do public social posts reveal advocacy
for political positions or causes that may conflict with independent reporting?

Covers three angles in a single pass:
  - Political advocacy: partisan amplification, campaign support, activist framing
  - Amplification patterns: own-outlet bias vs. broader information ecosystem
  - Accountability engagement: constructive vs. defensive responses to criticism

Minimum corpus: 10 posts (per rubric). Returns None if below threshold.
"""

import json
import logging
from typing import Optional

from backend.analysis.base_analyzer import BaseAnalyzer, AnalysisResult, Citation

logger = logging.getLogger(__name__)

MIN_CORPUS = 10


class SocialAnalyzer(BaseAnalyzer):
    analysis_type = "social_media_independence"
    prompt_version = "1.0"
    max_tokens = 4096

    def run(self, corpus: list[dict]) -> Optional[AnalysisResult]:
        if len(corpus) < MIN_CORPUS:
            logger.info(
                f"Social corpus too small ({len(corpus)} posts, min {MIN_CORPUS}) — skipping"
            )
            return None
        return super().run(corpus)

    def build_prompt(self, corpus: list[dict]) -> str:
        posts_text = ""
        for i, p in enumerate(corpus):
            reply_flag = " [REPLY]" if p.get("is_reply") else ""
            quote_flag = " [QUOTE TWEET]" if p.get("is_quote") else ""
            date = p.get("posted_at", "")[:10] if p.get("posted_at") else ""
            posts_text += f"[{i}] {date}{reply_flag}{quote_flag}\n{p['content']}\n\n"

        return f"""You are analyzing the public social media posts of a journalist to assess whether their online conduct aligns with the SPJ Code of Ethics principle of acting independently.

You are scoring the dimension: SOCIAL MEDIA INDEPENDENCE
Definition: Do public social posts reveal advocacy for political positions or causes that may conflict with independent reporting?

CORPUS ({len(corpus)} posts):
{posts_text}

SCORING FRAMEWORK:

Assess three angles:

1. POLITICAL ADVOCACY — Does the journalist use their platform to:
   - Express partisan political support (candidates, parties, policy campaigns)
   - Amplify political actors or advocacy organizations in ways that reveal clear ideological alignment
   - Frame news events in consistently partisan language
   Note: Sharing reporting, expressing concern about press freedom, or quoting sources is NOT advocacy.

2. AMPLIFICATION PATTERNS — What does the journalist amplify?
   - Predominantly their own outlet's content (neutral)
   - A diverse range of sources including opposing viewpoints (positive)
   - Predominantly one ideological perspective (negative)
   - Political campaigns, activist organizations (negative)

3. ACCOUNTABILITY ENGAGEMENT — When challenged or corrected:
   - Do they engage constructively and acknowledge errors? (positive)
   - Do they respond defensively or dismissively? (negative)
   - Do they ignore substantive criticism? (neutral to negative)

SCORING SCALE:
1.0 — Professional and balanced. No discernible political advocacy. Engages constructively with criticism.
0.8 — Mostly professional. Minor opinionated posts that don't materially compromise independence.
0.6 — Some patterns of ideological amplification or partisan framing that raise mild concerns.
0.4 — Consistent patterns of advocacy, partisan amplification, or defensive accountability behavior.
0.2 — Significant political advocacy that clearly conflicts with independent reporting.
0.0 — Posts reveal strong partisan alignment that fundamentally compromises perceived independence.

IMPORTANT DISTINCTIONS:
- Journalists covering human rights, environment, or politics will naturally tweet about those subjects — this is NOT advocacy.
- Quoting a politician or linking to coverage is not endorsement.
- Opinion journalists have different standards — note if the journalist appears to write opinion pieces.
- Focus on PATTERNS, not isolated posts. One partisan retweet does not define a score.

Return a JSON object exactly like this:
{{
  "social_media_independence": <float 0.0-1.0>,
  "flagged_count": <int>,
  "pattern_summary": "<1-2 sentences describing the overall pattern>",
  "advocacy_signal": "<none|mild|moderate|strong>",
  "amplification_pattern": "<balanced|own-outlet|ideological|mixed>",
  "accountability_pattern": "<constructive|defensive|absent>",
  "citations": [
    {{
      "post_index": <int>,
      "cited_text": "<exact text from the post>",
      "flag_type": "<advocacy|amplification|accountability>",
      "flag_value": <float 0.0-1.0 severity>
    }}
  ]
}}

Only include posts in citations that are materially relevant to the score. Do not flag routine journalism.
Return only the JSON object, no other text."""

    def parse_output(self, raw: str) -> tuple[dict, list[Citation]]:
        data = json.loads(raw)

        score = data.get("social_media_independence")
        if score is None:
            raise ValueError("Missing social_media_independence score")

        dimensions = {
            "social_media_independence": round(float(score), 2),
            "flagged_count": data.get("flagged_count", 0),
            "pattern_summary": data.get("pattern_summary", ""),
            "advocacy_signal": data.get("advocacy_signal", ""),
            "amplification_pattern": data.get("amplification_pattern", ""),
            "accountability_pattern": data.get("accountability_pattern", ""),
        }

        citations = []
        for c in data.get("citations", []):
            idx = c.get("post_index")
            citations.append(Citation(
                cited_text=c.get("cited_text", ""),
                dimension="social_media_independence",
                flag_type=c.get("flag_type"),
                flag_value=c.get("flag_value"),
                article_index=idx,
            ))

        return dimensions, citations
