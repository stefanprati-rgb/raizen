import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print(f"Key encontrada: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Responda apenas 'OK'.")
    print(f"Teste Gemini: {response.text}")
except Exception as e:
    print(f"Erro: {e}")
