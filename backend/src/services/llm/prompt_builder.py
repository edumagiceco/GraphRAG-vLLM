"""
Prompt builder for LLM interactions.
Constructs prompts with persona, context, and conversation history.
"""
from typing import Optional


class PromptBuilder:
    """
    Builder for constructing LLM prompts with:
    - Persona/system prompts
    - Retrieved context
    - Conversation history
    - Source citation instructions
    """

    DEFAULT_SYSTEM_PROMPT = """당신은 업로드된 문서 내용을 기반으로 정확하고 상세하게 답변하는 AI 어시스턴트입니다.

## 핵심 규칙
1. 컨텍스트에 있는 정보를 종합하여 일관성 있는 하나의 답변을 작성하세요.
2. 여러 출처의 정보가 있다면 내용을 통합하여 자연스럽게 설명하세요.
3. 파편화된 문장이나 출처별로 나뉜 답변을 하지 마세요.

## 응답 형식

### 관련 정보가 있는 경우:
- 질문에 대해 **완전한 문단 형태**로 상세히 답변하세요
- 컨텍스트의 핵심 내용을 요약하고 설명하세요
- 답변 마지막에 출처를 한 번만 표시하세요
- 형식: "[상세한 답변 내용]\n\n[출처: 파일명]"

### 관련 정보가 없는 경우:
"죄송합니다. 업로드된 문서에서 해당 질문에 대한 정보를 찾을 수 없습니다."

## 금지 사항
- 출처를 답변 중간에 반복해서 표시하지 마세요
- 각 출처별로 별도 문장을 나열하지 마세요
- 컨텍스트 텍스트를 그대로 복사하지 마세요
- <think> 태그 사용 금지

## 좋은 답변 예시
"문서관리규정은 회사 내부 문서의 작성, 보관, 배포 및 폐기에 관한 기준을 정하고 있습니다. 모든 문서는 문서주관부서에서 관리하며, 문서관리책임자가 문서의 취급 및 관리를 담당합니다. 문서는 대내문서와 대외문서로 구분되며, 각 문서는 고유번호를 부여받아 체계적으로 관리됩니다.

[출처: document_management_regulations.pdf]"
"""

    DEFAULT_GREETING = "안녕하세요! 무엇을 도와드릴까요?"

    def __init__(
        self,
        persona_name: Optional[str] = None,
        persona_description: Optional[str] = None,
        custom_system_prompt: Optional[str] = None,
        greeting: Optional[str] = None,
    ):
        """
        Initialize prompt builder.

        Args:
            persona_name: Chatbot persona name
            persona_description: Persona description
            custom_system_prompt: Custom system prompt (overrides default)
            greeting: Custom greeting message
        """
        self.persona_name = persona_name
        self.persona_description = persona_description
        self.custom_system_prompt = custom_system_prompt
        self.greeting = greeting or self.DEFAULT_GREETING

    def build_system_prompt(self) -> str:
        """
        Build the system prompt with persona.

        Returns:
            Complete system prompt
        """
        if self.custom_system_prompt:
            base_prompt = self.custom_system_prompt
        else:
            base_prompt = self.DEFAULT_SYSTEM_PROMPT

        if self.persona_name or self.persona_description:
            persona_section = "\n\n## 페르소나"
            if self.persona_name:
                persona_section += f"\n이름: {self.persona_name}"
            if self.persona_description:
                persona_section += f"\n설명: {self.persona_description}"
            return base_prompt + persona_section

        return base_prompt

    def build_context_prompt(
        self,
        context: str,
        citations: Optional[list[dict]] = None,
    ) -> str:
        """
        Build the context section of the prompt.

        Args:
            context: Retrieved context text
            citations: Source citations

        Returns:
            Formatted context section
        """
        if not context:
            return "이 질문에 대한 관련 컨텍스트를 찾을 수 없습니다."

        context_prompt = f"""## 검색된 컨텍스트

{context}

"""
        if citations:
            context_prompt += "## 참고 가능한 출처\n"
            for i, citation in enumerate(citations, 1):
                source_info = []
                if citation.get("filename"):
                    source_info.append(f"파일: {citation['filename']}")
                if citation.get("page"):
                    source_info.append(f"페이지 {citation['page']}")
                if citation.get("entity"):
                    entity_type = citation.get("entity_type", "개념")
                    source_info.append(f"엔티티: {citation['entity']} ({entity_type})")
                if citation.get("chunk_text"):
                    # 청크 텍스트 미리보기 추가 (100자 제한)
                    preview = citation["chunk_text"][:100] + "..." if len(citation.get("chunk_text", "")) > 100 else citation.get("chunk_text", "")
                    source_info.append(f"내용: {preview}")

                if source_info:
                    context_prompt += f"[출처 {i}] {' | '.join(source_info)}\n"

        return context_prompt

    def build_conversation_context(
        self,
        chat_history: Optional[list[dict]] = None,
        max_messages: int = 10,
    ) -> list[dict]:
        """
        Build conversation history for the prompt.

        Args:
            chat_history: List of previous messages
            max_messages: Maximum messages to include

        Returns:
            Formatted chat history
        """
        if not chat_history:
            return []

        # Limit to recent messages
        recent_history = chat_history[-max_messages:]

        return [
            {
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            }
            for msg in recent_history
        ]

    def build_full_prompt(
        self,
        user_message: str,
        context: str,
        citations: Optional[list[dict]] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> tuple[str, list[dict]]:
        """
        Build the complete prompt for LLM.

        Args:
            user_message: Current user message
            context: Retrieved context
            citations: Source citations
            chat_history: Conversation history

        Returns:
            Tuple of (system_prompt, messages)
        """
        system_prompt = self.build_system_prompt()
        context_section = self.build_context_prompt(context, citations)
        history = self.build_conversation_context(chat_history)

        # Combine context with user message
        full_user_message = f"""{context_section}

## 사용자 질문
{user_message}

## 답변 지침
1. 위의 컨텍스트 정보를 종합하여 하나의 완성된 답변을 작성하세요
2. 반드시 한국어로 답변하세요
3. 여러 출처의 정보를 통합하여 자연스럽게 설명하세요
4. 답변 마지막에 주요 출처를 한 번만 명시하세요 (형식: [출처: 파일명])
5. 컨텍스트에 없는 내용은 추측하지 마세요
6. 출처별로 분리된 답변이 아닌, 통합된 하나의 답변을 제공하세요"""

        # Build message list
        messages = history + [{"role": "user", "content": full_user_message}]

        return system_prompt, messages

    @classmethod
    def from_persona_config(cls, persona: dict) -> "PromptBuilder":
        """
        Create builder from persona configuration dict.

        Args:
            persona: Persona config dict

        Returns:
            PromptBuilder instance
        """
        return cls(
            persona_name=persona.get("name"),
            persona_description=persona.get("description"),
            custom_system_prompt=persona.get("system_prompt"),
            greeting=persona.get("greeting"),
        )


def build_chat_prompt(
    user_message: str,
    context: str,
    persona: Optional[dict] = None,
    citations: Optional[list[dict]] = None,
    chat_history: Optional[list[dict]] = None,
) -> tuple[str, list[dict]]:
    """
    Convenience function to build a chat prompt.

    Args:
        user_message: User's question
        context: Retrieved context
        persona: Optional persona config
        citations: Optional source citations
        chat_history: Optional conversation history

    Returns:
        Tuple of (system_prompt, messages)
    """
    if persona:
        builder = PromptBuilder.from_persona_config(persona)
    else:
        builder = PromptBuilder()

    return builder.build_full_prompt(
        user_message=user_message,
        context=context,
        citations=citations,
        chat_history=chat_history,
    )
