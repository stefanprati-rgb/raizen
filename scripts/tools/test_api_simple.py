import google.generativeai as genai
import os
import argparse
import time

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True)
    parser.add_argument("--model", default="gemini-2.0-flash")
    args = parser.parse_args()
    
    genai.configure(api_key=args.key)
    model = genai.GenerativeModel(args.model)
    
    print(f"Testando modelo {args.model} com prompt simples...")
    try:
        response = model.generate_content("Responda apenas 'OK' se estiver funcionando.")
        print(f"Resposta: {response.text}")
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
