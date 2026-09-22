import re
import os

with open('agent/brain.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Imports
imports = """
from phoenix_rag import HashingEmbedder, VectorRetriever, make_rag_node
from phoenix_contracts import TelemetryLogger
from pathlib import Path

# 0. RAG Initialization
retriever = VectorRetriever(HashingEmbedder())
sample_docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "RAG", "sample_docs")
if os.path.exists(sample_docs_dir):
    retriever.index_directory(Path(sample_docs_dir))
rag_node_instance = make_rag_node(retriever, telemetry=TelemetryLogger("telemetry.jsonl"))
"""
code = code.replace("from trace_scanner import TraceScanner", "from trace_scanner import TraceScanner\n" + imports)

# 2. State definition
state_injection = """
    original_code: Optional[str]
    error_trace: str
    severity: str
    rag_status: str
    rag_queries: list
    retrieved_context: list
    context_block: str
"""
code = re.sub(r'    original_code: Optional\[str\]\n    error_trace: str\n    severity: str', state_injection, code)

# 3. Add Context Injection to User Prompt in local_developer_node
prompt_injection = """
    if state.get("context_block"):
        user_prompt += f"\\n{state['context_block']}\\n"

    if state.get("critic_feedback"):
"""
code = code.replace('    if state.get("critic_feedback"):', prompt_injection)

# 4. Graph rewiring
code = code.replace('workflow.add_conditional_edges("scheduler_entry_node", route_scheduler)', 
                    'workflow.add_node("rag_node", rag_node_instance)\nworkflow.add_edge("scheduler_entry_node", "rag_node")\nworkflow.add_conditional_edges("rag_node", route_scheduler)')

with open('agent/brain.py', 'w', encoding='utf-8') as f:
    f.write(code)
