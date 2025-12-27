import gradio as gr
import ast
from data_manager import PlantRAG

_RAG = None

def _get_rag() -> PlantRAG:
    global _RAG
    if _RAG is None:
        _RAG = PlantRAG()
    return _RAG


def _fmt_paper_lines(chunks, limit: int = 3) -> str:
    chunks = (chunks or [])[:limit]
    if not chunks:
        return "_No sources available._"

    lines = []
    for i, c in enumerate(chunks, start=1):
        title = (c.get("title") or "Untitled").strip()
        url = (c.get("url") or "").strip()
        meta = c.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = ast.literal_eval(meta)
            except Exception:
                meta = {}
        authors = (meta.get("authors") or "").strip()
        journal = (meta.get("journal") or "").strip()
        year = (meta.get("year") or "").strip()
        doi = (meta.get("doi") or "").strip()

        # --- choose best link: url if exists, else DOI link ---
        link_url = url
        if not link_url and doi:
            link_url = f"https://doi.org/{doi}"

        # Title line (clickable if we have either url or doi)
        if link_url:
            lines.append(f"**{i}. [{title}]({link_url})**")
        else:
            lines.append(f"**{i}. {title}**")

        # (optional) clean authors a bit
        if authors:
            authors = authors.split("E-mail")[0].split("Accepted")[0].strip()
            lines.append(f"- 👤 Authors: {authors}")

        # Metadata lines (only if exist) - remove "Unknown journal"
        if journal:
            if year:
                lines.append(f"- 📰 {journal} ({year})")
            else:
                lines.append(f"- 📰 {journal}")
        elif year:
            lines.append(f"- 🗓️ Year: {year}")

        # DOI as a clickable link (not just code)
        if doi:
            lines.append(f"- 🔗 DOI: [{doi}](https://doi.org/{doi})")

        lines.append("")

    return "\n".join(lines).strip()



def run_query(question: str, top_k: int = 3, progress=gr.Progress(track_tqdm=True)) -> str:
    q = (question or "").strip()
    if not q:
        return "⚠️ Please enter a question."

    # Create a callback wrapper for Gradio progress
    def gradio_callback(pct, desc=""):
        progress(pct, desc=desc)
    
    out = _get_rag().query(q, top_k=int(top_k), progress_callback=gradio_callback)

    answer = (out.get("response") or "").strip()
    chunks = out.get("chunks") or []
    papers_found = int(out.get("papers_found") or len(chunks))

    md = []
    md.append("### Research-based Answer")
    md.append("")
    md.append(answer if answer else "_No answer returned._")
    md.append("")
    md.append("---")
    md.append(f"**Found {papers_found} relevant papers:**")
    md.append("")
    md.append(_fmt_paper_lines(chunks, limit=min(int(top_k), 5)))

    return "\n".join(md)


def search_screen():
    gr.Markdown("## Search Articles")
    gr.Markdown("Ask a question. We'll search the knowledge base and return the most relevant papers.")

    question = gr.Textbox(
        label="Ask your ecological question",
        placeholder="e.g., how do I know how much water my plant needs?",
        lines=2,
    )

    with gr.Row():
        top_k = gr.Slider(1, 5, value=3, step=1, label="Number of papers to search")
        submit = gr.Button("Submit", variant="primary")
        clear = gr.Button("Clear")

    output = gr.Markdown(value="")

    submit.click(run_query, inputs=[question, top_k], outputs=[output])
    question.submit(run_query, inputs=[question, top_k], outputs=[output])
    clear.click(lambda: ("", 3, ""), outputs=[question, top_k, output])

    return output
