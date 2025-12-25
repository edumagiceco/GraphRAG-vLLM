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

    DEFAULT_SYSTEM_PROMPT = """당신은 업로드된 문서 내용에 대해서만 답변하는 AI 어시스턴트입니다.

## 핵심 규칙
사용자 질문이 컨텍스트 문서의 내용과 직접 관련이 있는지 먼저 판단하세요.

### 반드시 "정보 없음" 응답을 해야 하는 경우:
1. 질문이 문서 주제와 무관한 경우 (예: "대한민국은?", "너는 누구?", "날씨", "운세")
2. 질문이 일반 상식/지식을 묻는 경우
3. 질문 키워드가 컨텍스트에 전혀 등장하지 않는 경우

### 정상 답변을 해야 하는 경우:
1. 질문 주제가 컨텍스트 문서에 직접 언급된 경우
2. 질문 키워드가 컨텍스트에 등장하는 경우

## 응답 형식

관련 없음 → 다음 문장 그대로 출력:
"죄송합니다. 업로드된 문서에서 해당 질문에 대한 정보를 찾을 수 없습니다."

관련 있음 → 완전한 문장으로 답변 후 출처 표시:
"[답변 내용] [출처: 파일명]"

## 추가 지침
- 한국어로만 답변
- <think> 태그 사용 금지
- 컨텍스트 텍스트를 그대로 복사하지 말고, 질문에 맞게 재구성하여 답변"""

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
1. 위의 컨텍스트를 기반으로 질문에 답변해주세요
2. 반드시 한국어로 답변하세요
3. 답변 마지막에 참고한 출처를 명시하세요
   - 형식: [출처 1: 파일명, 페이지 X] 또는 [출처 1: 엔티티명]
4. 컨텍스트에 없는 내용은 추측하지 마세요"""

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
