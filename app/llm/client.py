"""Optional LLM enrichment over an OpenAI-compatible endpoint.

Scores and citations never depend on the LLM.  If no key is configured or the
remote call fails, callers fall back to deterministic templates.
"""

from __future__ import annotations

import json
import logging
import re

from app.config import Settings, get_settings
from app.llm import prompts
from app.schemas import CompensationResult, LegalCitation, RiskFinding

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = None
        if self.settings.llm_enabled:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url,
                timeout=self.settings.llm_timeout,
            )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @property
    def mode(self) -> str:
        return f"online:{self.settings.llm_model}" if self.enabled else "offline"

    def _chat(self, system: str, user: str, json_mode: bool = False) -> str | None:
        if not self._client:
            return None
        kwargs = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        try:
            if json_mode:
                try:
                    response = self._client.chat.completions.create(
                        **kwargs, response_format={"type": "json_object"}
                    )
                except Exception:
                    response = self._client.chat.completions.create(**kwargs)
            else:
                response = self._client.chat.completions.create(**kwargs)
            return (response.choices[0].message.content or "").strip() or None
        except Exception as exc:
            logger.warning("LLM call failed, falling back to rules: %s", exc)
            return None

    def summarize_contract(
        self,
        contract_title: str,
        findings: list[RiskFinding],
        overall_risk: str,
        risk_score: float,
    ) -> str | None:
        finding_text = "\n".join(
            f"- [{item.risk_level.value}] {item.clause_title}：{item.issue}"
            for item in findings[:8]
        ) or "- 未发现明显高风险条款"
        user = prompts.CONTRACT_SUMMARY_USER.format(
            contract_title=contract_title,
            overall_risk=overall_risk,
            risk_score=f"{risk_score:.0f}",
            findings=finding_text,
        )
        return self._chat(prompts.CONTRACT_SUMMARY_SYSTEM, user)

    def compose_answer(
        self,
        question: str,
        intent: str,
        citations: list[LegalCitation],
        calculation: CompensationResult | None,
    ) -> dict | None:
        if not citations:
            return None
        citation_text = "\n".join(
            f"- 《{item.law}》{item.article}（{item.title}）：{item.text}"
            for item in citations[:5]
        )
        calculation_text = (
            f"{calculation.formula}；金额 {calculation.amount:,.0f} 元；"
            + "；".join(calculation.breakdown)
            if calculation and calculation.applies
            else "不适用或无足够事实计算"
        )
        user = prompts.QA_USER.format(
            question=question,
            intent=intent,
            calculation=calculation_text,
            citations=citation_text,
        )
        content = self._chat(prompts.QA_SYSTEM, user, json_mode=True)
        if not content:
            return None
        data = _parse_json(content)
        if not isinstance(data, dict):
            return None
        conclusion = str(data.get("conclusion", "")).strip()
        analysis = str(data.get("analysis", "")).strip()
        if not conclusion:
            return None
        return {"conclusion": conclusion, "analysis": analysis}


def _parse_json(content: str):
    content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"(\[.*\]|\{.*\})", content, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
