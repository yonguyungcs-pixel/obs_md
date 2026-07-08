"""
ai/post_processor.py — AI 后处理管线

支持 OpenAI / Google Gemini / DeepSeek / Ollama（本地），
通过 config.yaml 中的 ai.provider 一键切换。

所有 AI 功能均可独立开关，处理失败不阻断主流程。
"""

import json
from typing import Any, Optional

from loguru import logger

from ai.prompts import KNOWLEDGE_CARD_PROMPT, SUMMARY_AND_TAGS_PROMPT, SYSTEM_PROMPT


# ------------------------------------------------------------------
# 主处理器
# ------------------------------------------------------------------

class AIPostProcessor:
    """AI 后处理管线。"""

    def __init__(self, ai_config: dict) -> None:
        self._cfg = ai_config
        self._enabled = ai_config.get("enabled", False)
        self._provider = ai_config.get("provider", "ollama").lower()
        self._features = ai_config.get("features", {})
        self._max_chars = ai_config.get("max_input_chars", 8000)
        self._client: Optional[Any] = None

        if self._enabled:
            self._init_client()

    def is_enabled(self) -> bool:
        return self._enabled and self._client is not None

    def process(self, markdown: str, existing_meta: dict) -> dict:
        """
        对已转换的 Markdown 执行 AI 后处理，返回要合并到 Frontmatter 的额外字段。

        Args:
            markdown:      已转换的 Markdown 正文
            existing_meta: 已有的 Frontmatter 字典（避免重复处理）

        Returns:
            额外 Frontmatter 字段（summary、tags、category 等）
        """
        if not self.is_enabled():
            return {}

        content = markdown[: self._max_chars]
        extra: dict = {}

        # ---- 摘要 + Tags + 分类 + 待办 ----
        if any(
            self._features.get(f, False)
            for f in ("summary", "tags", "category", "todos")
        ):
            try:
                result = self._call_llm(
                    SUMMARY_AND_TAGS_PROMPT.format(content=content)
                )
                data = _safe_json(result)
                if self._features.get("summary") and "summary" in data:
                    extra["summary"] = data["summary"]
                if self._features.get("tags") and "tags" in data:
                    extra["tags"] = data["tags"]
                if self._features.get("category") and "category" in data:
                    extra["category"] = data["category"]
                if self._features.get("todos") and "todos" in data:
                    extra["todos"] = data["todos"]
            except Exception as e:
                logger.warning(f"[AI] 摘要/Tags 处理失败（不影响主流程）: {e}")

        # ---- 知识卡片 ----
        if self._features.get("knowledge_cards"):
            try:
                result = self._call_llm(
                    KNOWLEDGE_CARD_PROMPT.format(content=content)
                )
                data = _safe_json(result)
                if "cards" in data:
                    extra["knowledge_cards"] = data["cards"]
            except Exception as e:
                logger.warning(f"[AI] 知识卡片生成失败（不影响主流程）: {e}")

        if extra:
            extra["ai_processed"] = True
            extra["ai_provider"] = self._provider
            logger.info(f"[AI] 后处理完成，生成字段: {list(extra.keys())}")

        return extra

    # ------------------------------------------------------------------
    # LLM 调用（统一入口）
    # ------------------------------------------------------------------

    def _call_llm(self, user_prompt: str) -> str:
        if self._provider == "openai":
            return self._call_openai(user_prompt)
        elif self._provider == "gemini":
            return self._call_gemini(user_prompt)
        elif self._provider == "deepseek":
            return self._call_deepseek(user_prompt)
        elif self._provider == "ollama":
            return self._call_ollama(user_prompt)
        else:
            raise ValueError(f"不支持的 AI 提供商: {self._provider}")

    # ---- OpenAI ----

    def _call_openai(self, user_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._cfg["openai"]["model"],
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content

    # ---- DeepSeek（兼容 OpenAI SDK，只改 base_url + model）----

    def _call_deepseek(self, user_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._cfg["deepseek"]["model"],
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content

    # ---- Gemini ----

    def _call_gemini(self, user_prompt: str) -> str:
        model = self._client.GenerativeModel(
            model_name=self._cfg["gemini"]["model"],
            system_instruction=SYSTEM_PROMPT,
        )
        response = model.generate_content(user_prompt)
        return response.text

    # ---- Ollama（本地） ----

    def _call_ollama(self, user_prompt: str) -> str:
        import ollama
        ollama_cfg = self._cfg.get("ollama", {})
        response = ollama.chat(
            model=ollama_cfg.get("model", "qwen2.5:7b"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response["message"]["content"]

    # ------------------------------------------------------------------
    # 客户端初始化
    # ------------------------------------------------------------------

    def _init_client(self) -> None:
        try:
            if self._provider == "openai":
                self._client = self._init_openai()
            elif self._provider == "deepseek":
                self._client = self._init_deepseek()
            elif self._provider == "gemini":
                self._client = self._init_gemini()
            elif self._provider == "ollama":
                self._client = True   # Ollama 用函数调用，无需持久 client
                logger.info(f"[AI] 使用 Ollama 本地模型")
                return
            logger.info(f"[AI] 已初始化: provider={self._provider}")
        except Exception as e:
            logger.error(f"[AI] 客户端初始化失败，AI 功能将被禁用: {e}")
            self._client = None

    def _init_openai(self):
        import os
        from openai import OpenAI
        cfg = self._cfg.get("openai", {})
        api_key = cfg.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        base_url = cfg.get("base_url") or None
        return OpenAI(api_key=api_key, base_url=base_url)

    def _init_deepseek(self):
        import os
        from openai import OpenAI
        cfg = self._cfg.get("deepseek", {})
        api_key = cfg.get("api_key") or os.environ.get("DEEPSEEK_API_KEY", "")
        base_url = cfg.get("base_url", "https://api.deepseek.com/v1")
        return OpenAI(api_key=api_key, base_url=base_url)

    def _init_gemini(self):
        import os
        import google.generativeai as genai
        cfg = self._cfg.get("gemini", {})
        api_key = cfg.get("api_key") or os.environ.get("GOOGLE_API_KEY", "")
        genai.configure(api_key=api_key)
        return genai


# ------------------------------------------------------------------
# 内部工具
# ------------------------------------------------------------------

def _safe_json(text: str) -> dict:
    """安全解析 JSON，容忍 LLM 输出中的 markdown 代码块包装。"""
    text = text.strip()
    # 去掉可能的 ```json ... ``` 包装
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"[AI] JSON 解析失败，原始输出: {text[:200]}")
        return {}
