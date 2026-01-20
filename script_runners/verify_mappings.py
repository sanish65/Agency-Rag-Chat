from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os

load_dotenv()

# We want to see what SQL it generates for "office visits"
prompt = ChatPromptTemplate.from_messages([
    ("system", 
     "You are a helpful data assistant connected to a BigQuery database.\n"
     "RULES:\n"
     "1. DATASET: Always search answers from the `hackathon_data` dataset.\n"
     "2. TABLE MAPPINGS: Use these specific tables when the user refers to these terms:\n"
     "   - `office_visit_table`: office visits, branch visits, query from branches, client queries\n"
     "   - `application_table`: applications, application, applicants\n"
     "3. JOINS: If required, perform cross-table information gathering by joining tables based on their IDs.\n"
     "4. If asked for data, describe the SQL you would run. Always use the dataset `hackathon_data`."
    ),
    ("human", "{input}"),
])

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
chain = prompt | llm

test_queries = [
    "Show me all office visits",
    "How many applicants are there?"
]

for q in test_queries:
    print(f"\nQuery: {q}")
    response = chain.invoke({"input": q})
    print("Response:", response.content)
