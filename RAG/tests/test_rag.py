import json
import tempfile
import unittest
from pathlib import Path

from phoenix_contracts import (Chunk, Embedder, FakeLLMClient, FakeRetriever,
                               Retriever, TelemetryLogger, read_events)
from phoenix_rag import (HashingEmbedder, VectorRetriever, build_generation_prompt,
                         build_queries, chunk_markdown, make_rag_node, parse_trace)

DOCS = Path(__file__).resolve().parent.parent / "sample_docs"
TRACE = '''Traceback (most recent call last):
  File "app/billing.py", line 42, in compute_ratio
    return total / count
ZeroDivisionError: division by zero
'''


def make_retriever():
    r = VectorRetriever(HashingEmbedder())
    r.index_directory(DOCS)
    return r


class TestChunking(unittest.TestCase):
    def test_headings_and_code_fence_kept_whole(self):
        md = "# A\n\n## B\ntext one\n\n```python\nx = 1\n\ny = 2\n```\n\n## C\ntext two"
        chunks = chunk_markdown(md, "f.md", max_chars=50)
        fenced = [c for c in chunks if "```" in c.text]
        self.assertEqual(len(fenced), 1)
        self.assertIn("y = 2", fenced[0].text)
        self.assertEqual({c.heading for c in chunks}, {"B", "C"})

    def test_deterministic_ids_and_progress(self):
        md = "## H\n" + "\n\n".join(f"para {i} " + "x" * 200 for i in range(10))
        a, b = chunk_markdown(md, "f.md", max_chars=300), chunk_markdown(md, "f.md", max_chars=300)
        self.assertEqual([c.id for c in a], [c.id for c in b])
        self.assertGreater(len(a), 3)


class TestEmbedder(unittest.TestCase):
    def test_deterministic_and_normalised(self):
        e = HashingEmbedder()
        v1, v2 = e.embed("KeyError in load_config"), e.embed("KeyError in load_config")
        self.assertEqual(v1, v2)
        self.assertAlmostEqual(sum(x * x for x in v1), 1.0, places=6)

    def test_protocol_conformance(self):
        self.assertIsInstance(HashingEmbedder(), Embedder)
        self.assertIsInstance(make_retriever(), Retriever)
        self.assertIsInstance(FakeRetriever(), Retriever)


class TestQuery(unittest.TestCase):
    def test_parse_trace(self):
        info = parse_trace(TRACE)
        self.assertEqual(info["exc_type"], "ZeroDivisionError")
        self.assertEqual(info["frames"][-1][1], "compute_ratio")

    def test_build_queries(self):
        qs = build_queries({"error_trace": TRACE})
        self.assertTrue(any("ZeroDivisionError" in q for q in qs))
        self.assertLessEqual(len(qs), 3)
        self.assertEqual(build_queries({}), [])


class TestRetrieval(unittest.TestCase):
    def test_top_hit_is_relevant_doc(self):
        top = make_retriever().retrieve("ZeroDivisionError division by zero denominator", k=1)[0]
        self.assertEqual(top.heading, "ZeroDivisionError")

    def test_metadata_filter(self):
        res = make_retriever().retrieve("session commit", k=5, filters={"source": "database.md"})
        self.assertTrue(res and all(c.source == "database.md" for c in res))


class TestRagNode(unittest.TestCase):
    def test_ok_path_injects_guideline(self):
        node = make_rag_node(make_retriever())
        out = node({"error_trace": TRACE, "route": "local_edge", "target_function": "compute_ratio"})
        self.assertEqual(out["rag_status"], "ok")
        self.assertIn("ZeroDivisionError", out["context_block"])
        self.assertTrue(out["retrieved_context"])
        # node returns only the keys it owns
        self.assertLessEqual(set(out), {"rag_status", "rag_queries", "retrieved_context", "context_block"})

    def test_skips(self):
        node = make_rag_node(make_retriever())
        self.assertTrue(node({"error_trace": TRACE, "route": "delay"})["rag_status"].startswith("skipped:route"))
        self.assertEqual(node({"route": "local_edge"})["rag_status"], "skipped:no_query")

    def test_relevance_gate(self):
        node = make_rag_node(make_retriever(), min_score=0.99)
        out = node({"error_trace": TRACE})
        self.assertEqual(out["rag_status"], "no_relevant_docs")
        self.assertEqual(out["context_block"], "")

    def test_budget_and_k(self):
        chunks = [Chunk(id=str(i), text="x" * 500, source="s", score=0.9) for i in range(6)]
        node = make_rag_node(FakeRetriever(chunks), k=5, max_context_chars=1200)
        out = node({"error_trace": TRACE})
        self.assertEqual(len(out["retrieved_context"]), 2)

    def test_telemetry_event_written(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "t.jsonl"
            make_rag_node(make_retriever(), telemetry=TelemetryLogger(log))({"error_trace": TRACE, "route": "local_edge"})
            ev = list(read_events(log))
            self.assertEqual(len(ev), 1)
            self.assertEqual(ev[0]["node"], "rag")
            self.assertEqual(ev[0]["route"], "local_edge")
            self.assertGreater(ev[0]["latency_ms"], 0)
            json.dumps(ev[0])


class TestPrompt(unittest.TestCase):
    def test_context_reaches_llm_prompt(self):
        state = {"error_trace": TRACE, "route": "local_edge", "source_code": "def compute_ratio(t, c):\n    return t / c"}
        state.update(make_rag_node(make_retriever())(state))
        llm = FakeLLMClient("def compute_ratio(t, c): ...")
        llm.complete(build_generation_prompt(state))
        self.assertIn("Project guidelines", llm.prompts[0])
        self.assertIn("ZeroDivisionError", llm.prompts[0])

    def test_no_context_no_section(self):
        self.assertNotIn("Project guidelines", build_generation_prompt({"error_trace": TRACE}))



class TestRelativeFloor(unittest.TestCase):
    def test_weak_neighbours_dropped(self):
        chunks = [Chunk(id="a", text="strong", source="s", score=0.8),
                  Chunk(id="b", text="weak", source="s", score=0.2)]
        out = make_rag_node(FakeRetriever(chunks))({"error_trace": TRACE})
        self.assertEqual([c["id"] for c in out["retrieved_context"]], ["a"])


if __name__ == "__main__":
    unittest.main()
