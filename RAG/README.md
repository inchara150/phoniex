# Phoenix standalone: contracts + Agentic RAG node

```
python demo.py                                   # end-to-end demo, no deps
python -m unittest discover -s tests -t . -v     # 16 tests
```

## Integration checklist (when you get access to the main repo)
1. Diff `phoenix_contracts/state.py` against the real `PhoenixState`; rename keys here or there.
2. In `brain.py`: `graph.add_node("rag", make_rag_node(retriever, telemetry=logger))`
   and add the edge trace-scanner -> rag -> generator. Skip-on-`delay` is built in.
3. In the generator node, replace prompt construction with `build_generation_prompt(state)`
   (or just append `state["context_block"]`).
4. Replace `HashingEmbedder` with a real embedder (implement `.dim` and `.embed(text)`),
   and `InMemoryVectorStore` with `QdrantStore(dim=...)` (`pip install qdrant-client`).
   NOTE: `QdrantStore` could not be run in the offline build sandbox; smoke-test it first.
   If you change embedders, re-tune `min_score` (it is embedder-specific).
