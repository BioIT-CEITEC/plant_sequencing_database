import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # Load CERIT_API_KEY and CERIT_BASE_URL from .env
client = OpenAI(api_key=os.getenv("CERIT_API_KEY"), base_url=os.getenv("CERIT_BASE_URL"))

def chat_with_cerit(prompt: str) -> str:
    """Sends a single prompt to GLM 5.1 via CERIT and returns the text."""
    try:
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "glm-5.1"),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error connecting to CERIT: {e}"

if __name__ == "__main__":
    user_prompt = "Explain the key features of GLM 5.1 in three bullet points."
    print(f"Response:\n{chat_with_cerit(user_prompt)}")
