import google.generativeai as genai
import os
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True)
    args = parser.parse_args()
    
    genai.configure(api_key=args.key)
    
    print("Listando modelos disponíveis...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name} ({m.display_name})")

if __name__ == "__main__":
    main()
