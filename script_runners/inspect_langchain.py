import langchain
import langchain.agents
import sys

print(f"LangChain Version: {langchain.__version__}")
print(f"LangChain Agents File: {langchain.agents.__file__}")

print("\nAttributes in langchain.agents:")
for attr in dir(langchain.agents):
    if "agent" in attr.lower():
        print(f" - {attr}")

try:
    from langchain.agents import create_tool_calling_agent
    print("\ncreate_tool_calling_agent successfully imported!")
except ImportError:
    print("\ncreate_tool_calling_agent NOT found in langchain.agents")

try:
    from langchain.agents import create_openai_tools_agent
    print("create_openai_tools_agent found instead")
except ImportError:
    pass
