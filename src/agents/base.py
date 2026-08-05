"""Lớp cơ sở dùng chung cho mọi agent: gọi LLM có fallback an toàn + ghi trace."""

from __future__ import annotations

from src import llm_client, trace_logger


class BaseAgent:
    name: str = "BaseAgent"

    def summarize(self, case_id: str, system: str, user: str, fallback: str) -> str:
        """Gọi LLM cho phần diễn giải ngôn ngữ (KHÔNG dùng cho số liệu/ID).

        Nếu Ollama không khả dụng, dùng câu tóm tắt fallback deterministic để
        pipeline vẫn chạy được và output vẫn đúng schema.
        """
        try:
            text = llm_client.chat(system, user, temperature=0.2)
            trace_logger.log(
                case_id, self.name, "llm_call",
                {"system": system, "user": user, "response": text},
            )
            return text.strip()
        except llm_client.LLMError as exc:
            trace_logger.log(
                case_id, self.name, "llm_unavailable",
                {"error": str(exc), "fallback_used": fallback},
            )
            return fallback

    def log_tool(self, case_id: str, tool_name: str, data: dict) -> None:
        trace_logger.log(case_id, self.name, "tool_call", {"tool": tool_name, **data})

    def log_handoff(self, case_id: str, to_agent: str, data: dict) -> None:
        trace_logger.log(case_id, self.name, "handoff", {"to": to_agent, **data})
