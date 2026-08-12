from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

from northstar_rag import RAGService, Settings
from northstar_rag.ollama_client import OllamaClient, OllamaError
from northstar_rag.sql_tool import execute_read_only


st.set_page_config(page_title="Northstar Local RAG", page_icon="🔎", layout="wide")
st.title("Northstar local knowledge assistant")
st.caption("Local Ollama model • hybrid retrieval • evidence citations • fictional demo data")

settings = Settings.from_env()


@st.cache_resource
def get_service(current_settings: Settings) -> RAGService:
    return RAGService(current_settings)


service = get_service(settings)

with st.sidebar:
    st.header("Prototype status")
    ollama = OllamaClient(settings.ollama_base_url)
    if ollama.is_running():
        st.success("Ollama is running")
        try:
            installed = ollama.installed_models()
            st.caption(f"Chat: {settings.chat_model}\n\nEmbedding: {settings.embed_model}")
            if not any(name.startswith(settings.chat_model) for name in installed):
                st.warning(f"Pull chat model: ollama pull {settings.chat_model}")
            if not any(name.startswith(settings.embed_model) for name in installed):
                st.warning(f"Pull embedding model: ollama pull {settings.embed_model}")
        except OllamaError as exc:
            st.warning(str(exc))
    else:
        st.error("Ollama is not running")
        st.code("ollama serve", language="bash")

    if service.store.exists():
        try:
            manifest = service.manifest
            st.info(f"Index: {manifest.chunk_count} chunks from {manifest.source_count} files")
        except Exception as exc:
            st.warning(str(exc))
    else:
        st.warning("Index has not been built")

    if st.button("Build / rebuild index", type="primary", use_container_width=True):
        try:
            with st.spinner("Processing OCR/video, reading files, and creating local embeddings…"):
                manifest = service.build_index()
            st.success(f"Built {manifest.chunk_count} chunks from {manifest.source_count} files.")
            if manifest.errors:
                st.warning("Some files were skipped:\n" + "\n".join(manifest.errors))
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    with st.expander("Read-only SQLite explorer"):
        database = settings.data_dir / "02_Attachments" / "support_operations.db"
        sql = st.text_area("SELECT query", "SELECT status, COUNT(*) AS total FROM service_requests GROUP BY status ORDER BY total DESC")
        if st.button("Run safe query", use_container_width=True):
            try:
                result = execute_read_only(database, sql)
                st.dataframe([dict(zip(result.columns, row)) for row in result.rows], use_container_width=True)
                if result.truncated:
                    st.caption("Result was limited to 200 rows.")
            except Exception as exc:
                st.error(str(exc))

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Evidence used"):
                for source in message["sources"]:
                    st.markdown(source)

question = st.chat_input("Ask a question about the Northstar demo data")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        if not service.store.exists():
            response = "Build the index from the sidebar first."
            st.warning(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            history = [
                {"role": item["role"], "content": item["content"]}
                for item in st.session_state.messages[:-1]
                if item["role"] in {"user", "assistant"}
            ]
            try:
                with st.spinner("Checking the sources…"):
                    answer = service.answer(question, history)
                st.markdown(answer.text)
                source_lines = []
                for number, result in enumerate(answer.results, 1):
                    source = result.chunk
                    label = f"**[S{number}] {html.escape(source.title)}** — `{html.escape(source.source_path)}`; {html.escape(source.locator)}"
                    if source.source_url:
                        label += f" — [open source]({source.source_url})"
                    label += f"  \nRelevance: {result.score:.3f}"
                    source_lines.append(label)
                if source_lines:
                    with st.expander("Evidence used", expanded=False):
                        for line in source_lines:
                            st.markdown(line)
                st.session_state.messages.append({"role": "assistant", "content": answer.text, "sources": source_lines})
            except Exception as exc:
                st.error(str(exc))
