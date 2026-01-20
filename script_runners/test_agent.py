from langchain_ollama import ChatOllama
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from agent_tools import list_tables, execute_sql, create_visualization
import json

# Setup
llm = ChatOllama(model="llama3.2", temperature=0)
tools = [list_tables, execute_sql, create_visualization]
llm_with_tools = llm.bind_tools(tools)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful data assistant."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, return_intermediate_steps=True)

def test_query(q):
    print(f"Testing query: {q}")
    try:
        result = agent_executor.invoke({"input": q})
        print(f"Output: {result['output']}")
        print(f"Steps: {len(result['intermediate_steps'])}")
        for i, (action, output) in enumerate(result['intermediate_steps']):
            print(f" Step {i}: Tool={action.tool}, Input={action.tool_input}")
            # print(f" Output: {output[:100]}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Test 1: Simple Question (should use execute_sql)
    test_query("How many tables are there?")
    
    # Test 2: Visualization (should use create_visualization)
    test_query("Create a bar chart of top 5 tables by some metric (mock request)")
