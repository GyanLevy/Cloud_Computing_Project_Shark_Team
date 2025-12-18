import html
import re
import gradio as gr

from data_manager import rag_search

_URL_RE = re.compile(r"(https?://[^\s<>()]+|www\.[^\s<>()]+)", re.IGNORECASE)

def _pick_url(url_field: str, title: str, snippet: str) -> str:
    u = (url_field or "").strip()
    if u:
        return u

    blob = f"{title}\n{snippet}"
    m = _URL_RE.search(blob)
    if not m:
        return ""

    found = m.group(0).strip().rstrip(".,;)")
    if found.lower().startswith("www."):
        found = "https://" + found
    return found

def _clean_snippet(text: str, max_len: int = 260) -> str:
    t = (text or "").strip()
    t = re.sub(r"^\s*open\s+", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > max_len:
        t = t[:max_len].rstrip() + "..."
    return t


def search_screen():
    gr.Markdown("## Search Articles")
    gr.Markdown("Type a question or keywords. We’ll show the most relevant articles from the knowledge base.")

    query_in = gr.Textbox(
        label="Search",
        placeholder="e.g., yellow leaves, overwatering, soil moisture...",
    )

    with gr.Row():
        search_btn = gr.Button("Search", variant="primary")
        clear_btn = gr.Button("Clear")

    results_html = gr.HTML("")

    def _render_results(query: str):
        q = (query or "").strip()
        if not q:
            return '<div class="card" style="color:#0f172a;"><b>Tip:</b> Enter a query to search the knowledge base.</div>'

        results = rag_search(q, top_k=5)
        if not results:
            return '<div class="card" style="color:#0f172a;">No results. Try different keywords.</div>'

        cards = []
        for r in results:
            raw_title = str(r.get("title") or "Untitled")
            raw_snip = str(r.get("snippet") or "")

            title = html.escape(raw_title)
            snippet = html.escape(_clean_snippet(raw_snip))
            url = _pick_url(r.get("url"), raw_title, raw_snip)

            if url:
                title_block = (
                    f'<div class="resTitle">'
                    f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{title}</a>'
                    f'</div>'
                )
                link_block = (
                    f'<div class="resLink">'
                    f'<a href="{html.escape(url)}" target="_blank" rel="noopener">Open article</a>'
                    f'</div>'
                )
            else:
                title_block = f'<div class="resTitle"> {title}</div>'
                link_block = ""

            cards.append(
                f"""
                <div class="card resCard">
                  {title_block}
                  <div class="resSnippet">{snippet}</div>
                  {link_block}
                </div>
                """
            )

        return '<div class="resWrap">' + "\n".join(cards) + "</div>"

    def _clear():
        return "", ""

    search_btn.click(fn=_render_results, inputs=[query_in], outputs=[results_html])
    clear_btn.click(fn=_clear, inputs=[], outputs=[query_in, results_html])
