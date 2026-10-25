import asyncio
import json
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import requests

import api
from agents import audio_utils, document_agent, intake_agent, retrieval_agent
from agents.http_clients import create_retry_session


class ProviderFailureTests(unittest.TestCase):
    def test_vercel_chroma_cache_is_copied_to_writable_runtime_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "source")
            os.makedirs(source)
            source_file = os.path.join(source, "chroma.sqlite3")
            with open(source_file, "wb") as file:
                file.write(b"prebuilt index")

            with (
                patch.dict(os.environ, {"VERCEL": "1"}),
                patch.object(retrieval_agent, "CACHE_DIR", source),
            ):
                runtime_cache = retrieval_agent._runtime_cache_dir()

            try:
                self.assertNotEqual(runtime_cache, source)
                with open(os.path.join(runtime_cache, "chroma.sqlite3"), "rb") as file:
                    self.assertEqual(file.read(), b"prebuilt index")
            finally:
                shutil.rmtree(runtime_cache)

    def test_nvidia_chat_transport_uses_supported_client_options(self):
        client = SimpleNamespace(_client=SimpleNamespace())
        with (
            patch.dict(os.environ, {"NVIDIA_API_KEY": "test-key"}),
            patch.object(intake_agent, "ChatNVIDIA", return_value=client) as factory,
        ):
            self.assertIs(intake_agent.get_llm(), client)

        self.assertNotIn("get_session_fn", factory.call_args.kwargs)
        self.assertEqual(factory.call_args.kwargs["timeout"], 90)
        self.assertIs(client._client.get_session_fn, create_retry_session)

    def test_provider_session_retries_transient_connectivity_failures(self):
        retry = create_retry_session().get_adapter("https://").max_retries

        self.assertEqual(retry.total, 3)
        self.assertEqual(retry.connect, 3)
        self.assertEqual(retry.status, 3)

    def test_nvidia_embedding_transport_sets_timeout_on_low_level_client(self):
        client = SimpleNamespace(_client=SimpleNamespace())
        with patch.object(
            retrieval_agent, "NVIDIAEmbeddings", return_value=client
        ) as factory:
            retrieval_agent.LazyNVIDIAEmbeddings()._get_client()

        self.assertNotIn("timeout", factory.call_args.kwargs)
        self.assertNotIn("get_session_fn", factory.call_args.kwargs)
        self.assertEqual(client._client.timeout, 30)
        self.assertIs(client._client.get_session_fn, create_retry_session)

    def test_gnani_connection_error_is_propagated(self):
        with patch.object(
            audio_utils._HTTP_SESSION,
            "post",
            side_effect=requests.ConnectionError("offline"),
        ):
            with self.assertRaises(requests.ConnectionError):
                audio_utils.speech_to_text_bytes(b"audio", "recording.wav", "en-IN")

    def test_tavily_failure_falls_back_without_searching_profile_data(self):
        with (
            patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}),
            patch.dict(retrieval_agent._web_cache, {}, clear=True),
            patch.object(
                retrieval_agent.vector_store,
                "get",
                return_value={"documents": ["Public Support Scheme eligibility rules"]},
            ),
            patch.object(retrieval_agent, "TavilyClient") as tavily,
            patch.object(retrieval_agent.time, "sleep"),
        ):
            tavily.return_value.search.side_effect = requests.ConnectionError("offline")
            result = retrieval_agent.search_official_sources.func(
                ["Public Support Scheme"]
            )

        self.assertIn("temporarily unavailable", result)
        self.assertEqual(tavily.return_value.search.call_count, 2)
        query = tavily.return_value.search.call_args.kwargs["query"]
        self.assertIn("Public Support Scheme", query)
        self.assertNotIn("income", query.lower())
        self.assertNotIn("caste", query.lower())

    def test_checklist_uses_tavily_when_documents_have_no_checklist(self):
        web_payload = {
            "documents": [{"name": "Income certificate", "note": "if applicable"}],
            "start_date": "not found in documents",
            "deadline": "not found in documents",
            "how_to_apply": ["Apply through the official portal."],
            "other_requirements": [],
            "where_to_apply": "Official state portal",
        }
        with (
            patch.object(document_agent, "ensure_indexed"),
            patch.object(document_agent, "get_scheme_text", return_value=""),
            patch.object(
                document_agent,
                "get_web_text",
                return_value=(
                    "Official requirements evidence",
                    "searched",
                    ["https://example.ap.gov.in/scheme"],
                ),
            ) as web_search,
            patch.object(document_agent, "ask_json", return_value=web_payload) as ask_json,
        ):
            result = document_agent.find_requirements(
                "Example Student Scheme",
                {"annual_income": 0, "caste_category": "SC"},
                SimpleNamespace(),
            )

        web_search.assert_called_once_with("Example Student Scheme")
        prompt = ask_json.call_args.args[1]
        self.assertIn("Official requirements evidence", prompt)
        self.assertNotIn('"annual_income": 0', prompt)
        self.assertEqual(result["documents"][0]["name"], "Income certificate")
        self.assertEqual(result["how_to_apply"], ["Apply through the official portal."])
        self.assertEqual(result["sources"], ["https://example.ap.gov.in/scheme"])
        self.assertEqual(result["web_search_status"], "searched")

    def test_web_checklist_search_uses_scheme_only_and_official_sources(self):
        with (
            patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}),
            patch.object(document_agent, "TavilyClient") as tavily,
        ):
            tavily.return_value.search.return_value = {
                "results": [
                    {
                        "title": "Official scheme",
                        "url": "https://department.ap.gov.in/scheme",
                        "content": "Application documents and process",
                    },
                    {
                        "title": "Untrusted copy",
                        "url": "https://example.com/scheme",
                        "content": "Not an official source",
                    },
                ]
            }
            text, status, sources = document_agent.get_web_text("Example Scheme")

        query = tavily.return_value.search.call_args.kwargs["query"]
        self.assertIn("Example Scheme", query)
        self.assertNotIn("income", query.lower())
        self.assertNotIn("caste", query.lower())
        self.assertIn("ap.gov.in", text)
        self.assertNotIn("Untrusted copy", text)
        self.assertEqual(status, "searched")
        self.assertEqual(sources, ["https://department.ap.gov.in/scheme"])

    def test_audio_api_reports_gnani_outage_without_leaking_error(self):
        session = api.ConversationSession(
            session_id="00000000-0000-0000-0000-000000000001",
            locale="en-IN",
        )
        response = api._audio_stream(session, b"recording", "recording.webm")

        async def collect_events():
            return [event async for event in response.body_iterator]

        with patch.object(api, "_transcribe_upload", side_effect=ConnectionError("private detail")):
            events = asyncio.run(collect_events())

        combined = "".join(events)
        self.assertIn("event: error", combined)
        self.assertIn("We could not process that audio", combined)
        self.assertNotIn("private detail", combined)

    def test_matching_failure_keeps_session_retryable(self):
        session = api.ConversationSession(
            session_id="00000000-0000-0000-0000-000000000002",
            stage="intake",
            language="English",
            locale="en-IN",
        )
        intake_result = {
            "details": {"age": 32, "occupation": "farmer"},
            "confirmed": True,
            "optional_details_asked": True,
        }
        selection_result = {
            "reply": "Here are the schemes to review.",
            "details": {
                "ranked_schemes": "Scheme A",
                "selected_schemes": [],
            },
        }

        with (
            patch.object(intake_agent, "resume_turn_session"),
            patch.object(intake_agent, "handle_turn", return_value=intake_result),
            patch(
                "agents.eligibilty_agent.start_turn_session",
                side_effect=[ConnectionError(), selection_result],
            ),
        ):
            with self.assertRaises(ConnectionError):
                api._process_text(session, "yes", lambda _status: None)

            self.assertEqual(session.stage, "matching")
            result = api._process_text(session, "yes", lambda _status: None)

        self.assertEqual(result["stage"], "selection")
        self.assertEqual(session.optional_details_asked, True)

    def test_optional_profile_fields_can_be_skipped_without_blocking(self):
        captured = {}

        def capture_agent(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace()

        with patch.object(intake_agent, "create_agent", side_effect=capture_agent):
            intake_agent.start_turn_session("optional-profile-test", "English")

        tools = {item.name: item for item in captured["tools"]}
        save_result = tools["save_profile_details"].invoke(
            {
                "age": 32,
                "gender": "female",
                "occupation": "farmer",
                "district": "Krishna",
                "annual_income": 120000,
            }
        )
        skip_result = tools["skip_optional_details"].invoke({})
        session_state = intake_agent._turn_sessions["optional-profile-test"]["state"]
        intake_agent.end_turn_session("optional-profile-test")

        self.assertIn("optional details", save_result.lower())
        self.assertIn("skipped", skip_result.lower())
        self.assertTrue(session_state["optional_details_asked"])

    def test_optional_followup_state_is_persisted_with_session(self):
        session = api.ConversationSession(
            session_id="00000000-0000-0000-0000-000000000003",
            optional_details_asked=True,
        )
        restored = api.ConversationSession.from_payload(
            session.session_id,
            session.to_payload(),
            session.lock,
        )

        self.assertTrue(restored.optional_details_asked)

    def test_build_index_replaces_old_documents_and_writes_freshness_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            schemes_dir = os.path.join(directory, "schemes")
            cache_dir = os.path.join(directory, "cache")
            os.makedirs(schemes_dir)
            with open(os.path.join(schemes_dir, "current.pdf"), "wb") as pdf_file:
                pdf_file.write(b"current scheme")

            store = SimpleNamespace(
                get=lambda **_kwargs: {"ids": ["deleted-scheme-chunk"]},
                delete=lambda **kwargs: deleted_ids.extend(kwargs["ids"]),
                add_documents=lambda **kwargs: added_documents.extend(kwargs["documents"]),
            )
            deleted_ids = []
            added_documents = []
            documents = [SimpleNamespace(page_content="current scheme")]
            splitter = SimpleNamespace(split_documents=lambda items: items)

            with (
                patch.object(retrieval_agent, "SCHEMES_DIR", schemes_dir),
                patch.object(retrieval_agent, "CACHE_DIR", cache_dir),
                patch.object(
                    retrieval_agent,
                    "INDEX_MANIFEST",
                    os.path.join(cache_dir, "schemes_manifest.json"),
                ),
                patch(
                    "langchain_community.document_loaders.PyPDFDirectoryLoader",
                    return_value=SimpleNamespace(load=lambda: documents),
                ),
                patch(
                    "langchain_text_splitters.RecursiveCharacterTextSplitter",
                    return_value=splitter,
                ),
                patch.object(retrieval_agent, "vector_store", store),
            ):
                retrieval_agent.build_index()
                retrieval_agent.ensure_indexed()

                with open(
                    os.path.join(cache_dir, "schemes_manifest.json"),
                    encoding="utf-8",
                ) as manifest_file:
                    manifest = json.load(manifest_file)

            self.assertEqual(deleted_ids, ["deleted-scheme-chunk"])
            self.assertEqual(added_documents, documents)
            self.assertIn("current.pdf", manifest["files"])

    def test_ensure_indexed_rejects_changed_scheme_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            schemes_dir = os.path.join(directory, "schemes")
            cache_dir = os.path.join(directory, "cache")
            os.makedirs(schemes_dir)
            os.makedirs(cache_dir)
            with open(os.path.join(schemes_dir, "current.pdf"), "wb") as pdf_file:
                pdf_file.write(b"updated scheme")
            manifest_path = os.path.join(cache_dir, "schemes_manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as manifest_file:
                json.dump({"old.pdf": "old-content-hash"}, manifest_file)

            with (
                patch.object(retrieval_agent, "SCHEMES_DIR", schemes_dir),
                patch.object(retrieval_agent, "INDEX_MANIFEST", manifest_path),
                patch.object(
                    retrieval_agent,
                    "vector_store",
                    SimpleNamespace(get=lambda **_kwargs: {"ids": ["stale"]}),
                ),
                self.assertRaisesRegex(RuntimeError, "scheme PDFs have changed"),
            ):
                retrieval_agent.ensure_indexed()

    def test_retrieve_all_schemes_uses_profile_query_for_every_source(self):
        sources = ["schemes/student.pdf", "schemes/farmer.pdf"]
        calls = []

        def get(**kwargs):
            calls.append(kwargs)
            return {
                "metadatas": [{"source": source} for source in sources],
            }

        def search_by_vector(_vector, k, filter):
            source = filter["source"]
            return [
                SimpleNamespace(
                    page_content=f"{source}-chunk-{index}",
                    metadata={"source": source, "page": index},
                )
                for index in range(k)
            ]

        with (
            patch.object(retrieval_agent, "ensure_indexed"),
            patch.object(
                retrieval_agent,
                "vector_store",
                SimpleNamespace(get=get, similarity_search_by_vector=search_by_vector),
            ),
            patch.object(
                retrieval_agent.embeddings,
                "embed_query",
                return_value=[0.1, 0.2],
            ) as embed_query,
        ):
            result = retrieval_agent.retrieve_all_schemes.func("SC student scholarship eligibility")

        self.assertEqual(result.count("-chunk-"), 6)
        self.assertIn("student.pdf", result)
        self.assertIn("farmer.pdf", result)
        self.assertEqual(embed_query.call_count, 1)
        self.assertIn("SC student scholarship", embed_query.call_args.args[0])

    def test_timeout_error_classifier_finds_nested_read_timeout(self):
        timeout = TimeoutError("provider timeout")
        transport = ConnectionError("connection failed")
        transport.__cause__ = timeout

        self.assertTrue(api._is_timeout_error(transport))
        self.assertFalse(api._is_timeout_error(ConnectionError("offline")))

    def test_stream_uses_safe_retryable_message(self):
        async def collect_events():
            def fail(_report_status):
                raise RuntimeError("private provider details")

            return [
                event
                async for event in api._stream_events(
                    fail,
                    "matching",
                    failure_message=lambda _error: (
                        "Scheme matching is temporarily unavailable. Retry."
                    ),
                )
            ]

        events = asyncio.run(collect_events())
        combined = "".join(events)

        self.assertIn("Scheme matching is temporarily unavailable", combined)
        self.assertNotIn("private provider details", combined)


if __name__ == "__main__":
    unittest.main()
