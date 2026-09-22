"""Run:  python demo.py   (no network, no extra dependencies)"""
from pathlib import Path

from phoenix_contracts import FakeLLMClient, TelemetryLogger
from phoenix_rag import (HashingEmbedder, VectorRetriever, build_generation_prompt,
                         make_rag_node)

TRACE = '''Traceback (most recent call last):
  File "app/config.py", line 17, in load_config
    return settings["database_url"]
KeyError: 'database_url'
'''

retriever = VectorRetriever(HashingEmbedder())
print("indexed chunks:", retriever.index_directory(Path(__file__).parent / "sample_docs"))

rag = make_rag_node(retriever, telemetry=TelemetryLogger("telemetry.jsonl"))
state = {"error_trace": TRACE, "route": "local_edge", "target_function": "load_config",
         "source_code": 'def load_config(settings):\n    return settings["database_url"]'}
state.update(rag(state))

print("status :", state["rag_status"])
print("queries:", state["rag_queries"])
for c in state["retrieved_context"]:
    print(f"  {c['score']:.2f}  {c['source']} > {c['heading']}")
print("\n--- prompt sent to generator ---\n" + build_generation_prompt(state))
FakeLLMClient()  # swap for the real client at integration time
