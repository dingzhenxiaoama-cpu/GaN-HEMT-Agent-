import json
import os
from typing import Any

from dotenv import load_dotenv


class LLMClient:
    """Small OpenAI-compatible client for supported domestic model APIs."""

    def __init__(self, api_key: str, base_url: str, model: str):
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError(
                "缺少 openai 依赖，请执行: python -m pip install openai"
            ) from error

        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    @classmethod
    def from_env(cls) -> "LLMClient | None":
        load_dotenv()
        enabled = os.getenv("LLM_ENABLED", "false").lower() in {
            "1",
            "true",
            "yes",
        }
        api_key = os.getenv("LLM_API_KEY")
        if not enabled:
            return None
        if not api_key:
            raise RuntimeError(
                "LLM_ENABLED=true，但 LLM_API_KEY 为空。"
                "请在项目根目录 .env 中填写模型服务密钥后重试。"
            )

        return cls(
            api_key=api_key,
            base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            model=os.getenv("LLM_MODEL", "deepseek-v4-flash"),
        )

    def advise(self, analysis_result: dict[str, dict]) -> dict[str, Any]:
        prompt = (
            "你是 GaN HEMT 紧凑模型建模助手。"
            "请根据下面的测量数据摘要，给出下一步建模建议。"
            "只能依据提供的数据，不要伪造拟合结果。"
            "请返回 JSON，字段包括 next_step、reason、parameters_to_check。\n\n"
            f"测量数据摘要：{json.dumps(analysis_result, ensure_ascii=False)}"
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "你负责解释器件数据并提出可审计的建模步骤。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        content = response.choices[0].message.content or ""

        try:
            advice = json.loads(content)
        except json.JSONDecodeError:
            advice = {
                "next_step": "人工检查模型建议",
                "reason": content,
                "parameters_to_check": [],
            }

        usage = getattr(response, "usage", None)
        usage_summary = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }
        return {"advice": advice, "usage": usage_summary}
