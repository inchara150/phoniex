import re
import os

with open('agent/brain.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add imports
if 'ChatGoogleGenerativeAI' not in code:
    code = code.replace(
        'from langchain_ollama import ChatOllama',
        'from langchain_ollama import ChatOllama\nfrom langchain_google_genai import ChatGoogleGenerativeAI\nfrom dotenv import load_dotenv\nload_dotenv()'
    )

# 2. Add LLM initialization
if 'cloud_llm =' not in code:
    code = re.sub(
        r'# 1\. Models Initialization \(100% Local\)\ngenerator_llm = ChatOllama\(model="qwen2\.5-coder:7b", temperature=0\.1\)\ncritic_llm = ChatOllama\(model="qwen2\.5-coder:7b", temperature=0\.0\)',
        '# 1. Models Initialization\ngenerator_llm = ChatOllama(model="qwen2.5-coder:7b", temperature=0.1)\ncloud_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1) if os.getenv("GEMINI_API_KEY") else generator_llm\ncritic_llm = ChatOllama(model="qwen2.5-coder:7b", temperature=0.0)\ncloud_critic_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.0) if os.getenv("GEMINI_API_KEY") else critic_llm',
        code
    )

# 3. Modify local_developer_node to use the route correctly
code = code.replace(
    'response = generator_llm.invoke([',
    'llm = cloud_llm if state.get("execution_route") == "cloud_heavy" else generator_llm\n        response = llm.invoke(['
)
code = code.replace(
    'print("[dY  GENERATOR (Ollama)] Patch generated successfully.")',
    'agent_name = "Gemini" if state.get("execution_route") == "cloud_heavy" else "Ollama"\n        print(f"[🧠 GENERATOR ({agent_name})] Patch generated successfully.")'
)
code = code.replace(
    'print(f"\\n[dY  GENERATOR (Ollama)] Attempt {iteration}:',
    'agent_name = "Gemini" if state.get("execution_route") == "cloud_heavy" else "Ollama"\n    print(f"\\n[🧠 GENERATOR ({agent_name})] Attempt {iteration}:'
)
code = code.replace(
    'print(f"[dY  GENERATOR] Ollama Error: {e}")',
    'print(f"[🧠 GENERATOR] API Error: {e}")'
)

# 4. Modify critic_node to use the route correctly
code = code.replace(
    'response = critic_llm.invoke([',
    'llm = cloud_critic_llm if state.get("execution_route") == "cloud_heavy" else critic_llm\n        response = llm.invoke(['
)
code = code.replace(
    'print("\\n[dY ? CRITIC (Ollama)] Reviewing the generated patch before sandbox execution...")',
    'agent_name = "Gemini" if state.get("execution_route") == "cloud_heavy" else "Ollama"\n    print(f"\\n[🧐 CRITIC ({agent_name})] Reviewing the generated patch before sandbox execution...")'
)
code = code.replace(
    'print("[dY ? CRITIC (Ollama)] Patch approved! Sending to Sandbox.")',
    'print(f"[🧐 CRITIC ({agent_name})] Patch approved! Sending to Sandbox.")'
)
code = code.replace(
    'print(f"[dY ? CRITIC (Ollama)] Patch rejected. Sending feedback back to Generator.")',
    'print(f"[🧐 CRITIC ({agent_name})] Patch rejected. Sending feedback back to Generator.")'
)

with open('agent/brain.py', 'w', encoding='utf-8') as f:
    f.write(code)
