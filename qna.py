from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client()

MODEL_NAME = "gemini-3.5-flash-lite"


def ask_gemini(question: str, history=None) -> str:

    if history is None:
        history = []

    conversation = ""

    for message in history:

        role = message.role
        content = message.content

        if role == "user":
            conversation += f"Student: {content}\n"

        elif role == "assistant":
            conversation += f"EduGenie: {content}\n"

    conversation += f"Student: {question}\n"

    prompt = f"""
You are EduGenie, an educational AI assistant.

Your job is to help students understand topics clearly.

Rules:
- Explain in simple language.
- Be accurate.
- Use examples when useful.
- Use bullet points or headings when helpful.
- Remember the previous conversation.
- Understand follow-up questions such as "why?", "how?", "what about it?", etc.
- Do not make up facts.

Conversation so far:

{conversation}

Now answer the student's latest question.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text