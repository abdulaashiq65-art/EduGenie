from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client()

print("Models available for generateContent:")
print("--------------------------------------")

for model in client.models.list():
    if "generateContent" in model.supported_actions:
        print(model.name)