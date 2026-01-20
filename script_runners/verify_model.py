from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()
try:
    llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0)
    print("Invoking model...")
    response = llm.invoke("Hello")
    print("Success! Response:", response.content)
except Exception as e:
    print("Error:", e)
