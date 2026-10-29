"""
DualMova — Validation Report Generator for Rejected Segments
============================================================
Generates:
1. rejected_validation_report.html — Interactive dashboard with direct links
   to knihi.com using W3C Text Fragments (#:~:text=...) and a copyable Ctrl+F query.
2. rejected_validation.tsv — Full tabular export for spreadsheet auditing.
"""

import json
import html
import urllib.parse
from pathlib import Path
from collections import Counter

PROCESSED_DIR = Path(__file__).parent / "processed"
REJ_PATH = PROCESSED_DIR / "rejected.jsonl"
HTML_OUT = PROCESSED_DIR / "rejected_validation_report.html"
TSV_OUT = PROCESSED_DIR / "rejected_validation.tsv"


def clean_words_for_url(text: str) -> tuple[str, str, str]:
    """
    Returns:
    - ctrl_f_query: First 4 clean words for manual Ctrl+F search
    - text_start: First 3-4 words for W3C Text Fragment
    - text_end: Last 3 words for W3C Text Fragment
    """
    # Strip punctuation for safe URL and search fragment matching
    words = [w.strip("«»\"'(),.:;!?[]-—") for w in text.split()]
    words = [w for w in words if w]
    
    if not words:
        return "", "", ""
    
    start_phrase = " ".join(words[:min(4, len(words))])
    ctrl_f = start_phrase
    end_phrase = " ".join(words[max(0, len(words)-3):]) if len(words) > 4 else ""
    return ctrl_f, start_phrase, end_phrase


def build_fragment_url(base_url: str, start: str, end: str) -> str:
    """Generates a URL according to the W3C Text Fragments standard (#:~:text=start,end)."""
    if not base_url:
        return ""
    if not start:
        return base_url
    
    # URL encode fragments
    q_start = urllib.parse.quote(start)
    if end and end != start:
        q_end = urllib.parse.quote(end)
        return f"{base_url}#:~:text={q_start},{q_end}"
    return f"{base_url}#:~:text={q_start}"


def main():
    print(f"Reading rejected entries from {REJ_PATH}...")
    
    stats_reason = Counter()
    records = []
    
    with open(REJ_PATH, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            row = json.loads(line)
            reason = row.get("reject_reason") or row.get("metrics", {}).get("reason", "UNKNOWN")
            stats_reason[reason] += 1
            
            text_raw = row.get("text_raw", "")
            base_url = row.get("source_url", "")
            ctrl_f, start_w, end_w = clean_words_for_url(text_raw)
            frag_url = build_fragment_url(base_url, start_w, end_w)
            
            features = row.get("metrics", {}).get("features", {})
            feat_str = ""
            if features:
                tar_f = features.get("taras", [])
                nar_f = features.get("nark", [])
                parts = []
                if tar_f:
                    parts.append("TARAS: " + ", ".join(tar_f[:4]))
                if nar_f:
                    parts.append("NARK: " + ", ".join(nar_f[:4]))
                feat_str = " | ".join(parts)
            
            records.append({
                "id": idx,
                "author": row.get("author", "Unknown"),
                "title": row.get("title", "Untitled"),
                "genre": row.get("genre", "prose"),
                "reason": reason,
                "url": base_url,
                "frag_url": frag_url,
                "ctrl_f": ctrl_f,
                "snippet": text_raw[:220].replace("\n", " "),
                "features": feat_str,
            })
            
            if idx % 10000 == 0:
                print(f"Processed {idx} records...")

    total_count = len(records)
    print(f"Total rejected records: {total_count}")
    print(f"Breakdown by reason: {dict(stats_reason)}")
    
    # -- 1. Export to TSV ----------------------------------------------------
    print(f"Writing TSV to {TSV_OUT}...")
    with open(TSV_OUT, "w", encoding="utf-8") as f_tsv:
        f_tsv.write("ID\tAuthor\tTitle\tGenre\tReject_Reason\tCtrl_F_Query\tDirect_URL_Highlighted\tFeatures\tSnippet\n")
        for r in records:
            f_tsv.write(
                f"{r['id']}\t{r['author']}\t{r['title']}\t{r['genre']}\t{r['reason']}\t"
                f"{r['ctrl_f']}\t{r['frag_url']}\t{r['features']}\t{r['snippet']}\n"
            )
            
    # -- 2. Export to HTML Dashboard -----------------------------------------
    print(f"Generating HTML validation dashboard at {HTML_OUT}...")
    
    # Store compact JSON payload for high-performance in-browser client rendering
    json_data = json.dumps(records, ensure_ascii=False)
    
    html_content = f"""<!DOCTYPE html>
<html lang="be">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DualMova — Валідацыя адбракаваных сегментаў knihi.com</title>
<style>
  :root {{
    --bg: #0f172a;
    --card: #1e293b;
    --border: #334155;
    --text: #f8fafc;
    --muted: #94a3b8;
    --primary: #38bdf8;
    --accent: #818cf8;
    --danger: #f43f5e;
    --warning: #fbbf24;
    --success: #34d399;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 24px;
    line-height: 1.5;
  }}
  .header {{
    margin-bottom: 24px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border);
  }}
  h1 {{ font-size: 24px; color: var(--primary); margin-bottom: 8px; }}
  p.subtitle {{ color: var(--muted); font-size: 14px; margin-bottom: 16px; }}
  
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 20px;
  }}
  .stat-card {{
    background: var(--card);
    border: 1px solid var(--border);
    padding: 12px 16px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
  }}
  .stat-card:hover, .stat-card.active {{
    border-color: var(--primary);
    background: #253349;
  }}
  .stat-val {{ font-size: 20px; font-weight: bold; color: var(--text); }}
  .stat-label {{ font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }}
  
  .controls {{
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
    align-items: center;
  }}
  .search-input {{
    flex: 1;
    min-width: 250px;
    background: var(--card);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 14px;
  }}
  .search-input:focus {{ outline: none; border-color: var(--primary); }}
  
  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
  }}
  .badge-ambiguous {{ background: #581c87; color: #d8b4fe; }}
  .badge-russian {{ background: #881337; color: #fda4af; }}
  .badge-ocr {{ background: #713f12; color: #fde047; }}
  .badge-chimera {{ background: #7c2d12; color: #fdba74; }}
  .badge-neutral {{ background: #1e3a5f; color: #93c5fd; }}
  .badge-trasianka {{ background: #3f1e5f; color: #f472b6; }}
  
  .item-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 12px;
    transition: border 0.15s;
  }}
  .item-card:hover {{ border-color: #475569; }}
  .card-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
    gap: 12px;
  }}
  .card-title {{ font-size: 15px; font-weight: 600; color: #e2e8f0; }}
  .card-author {{ font-size: 13px; color: var(--muted); }}
  .snippet {{
    font-size: 13px;
    color: #cbd5e1;
    background: #151e2e;
    padding: 10px 12px;
    border-radius: 6px;
    border-left: 3px solid var(--primary);
    margin-bottom: 10px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    white-space: pre-wrap;
    word-break: break-word;
  }}
  .card-actions {{
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    font-size: 13px;
  }}
  .btn-link {{
    background: #0284c7;
    color: white;
    text-decoration: none;
    padding: 6px 12px;
    border-radius: 5px;
    font-weight: 500;
    transition: background 0.15s;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }}
  .btn-link:hover {{ background: #0369a1; }}
  .btn-copy {{
    background: #334155;
    color: var(--text);
    border: 1px solid #475569;
    padding: 6px 12px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 13px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s;
  }}
  .btn-copy:hover {{ background: #475569; }}
  .btn-copy.copied {{ background: var(--success); color: black; }}
  .features-info {{ font-size: 12px; color: #fb7185; margin-left: auto; }}

  .pagination {{
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 12px;
    margin-top: 24px;
    padding: 16px;
  }}
  .page-btn {{
    background: var(--card);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
  }}
  .page-btn:disabled {{ opacity: 0.4; cursor: not-allowed; }}
  .page-info {{ font-size: 14px; color: var(--muted); }}
</style>
</head>
<body>

<div class="header">
  <h1>🔎 DualMova — Валідацыя 52,806 адбракаваных сегментаў knihi.com</h1>
  <p class="subtitle">
    Прамыя спасылкі вядуць непасрэдна на старонку кнігі на <strong>knihi.com</strong> з выкарыстаннем W3C Text Fragments:
    браўзер адкрывае твор, аўтаматычна скроліць да патрэбнага абзаца і <strong>падсвятляе яго жоўтым колерам</strong>.
    Таксама даступная кнопка хуткага капіявання запыту для ручнога пошуку праз <strong>Ctrl+F</strong>.
  </p>

  <div class="stats-grid">
    <div class="stat-card active" onclick="setFilter('ALL')">
      <div class="stat-val">{total_count:,}</div>
      <div class="stat-label">УСЯГО АДХІЛЕНА</div>
    </div>
    <div class="stat-card" onclick="setFilter('REJECT_LOW_CONFIDENCE_AMBIGUOUS')">
      <div class="stat-val">{stats_reason.get('REJECT_LOW_CONFIDENCE_AMBIGUOUS', 0):,}</div>
      <div class="stat-label">AMBIGUOUS (ПАМЫЛКА МЯККАСЦІ)</div>
    </div>
    <div class="stat-card" onclick="setFilter('REJECT_RUSSIAN_CHARS')">
      <div class="stat-val">{stats_reason.get('REJECT_RUSSIAN_CHARS', 0):,}</div>
      <div class="stat-label">РУСКАЯ ГРАФІКА</div>
    </div>
    <div class="stat-card" onclick="setFilter('REJECT_ORTHOGRAPHIC_CHIMERA')">
      <div class="stat-val">{stats_reason.get('REJECT_ORTHOGRAPHIC_CHIMERA', 0):,}</div>
      <div class="stat-label">АРФАГРАФІЧНЫЯ ХІМЕРЫ</div>
    </div>
    <div class="stat-card" onclick="setFilter('REJECT_OCR_HOMOGLYPH')">
      <div class="stat-val">{stats_reason.get('REJECT_OCR_HOMOGLYPH', 0):,}</div>
      <div class="stat-label">OCR ГОМАГЛІФЫ</div>
    </div>
    <div class="stat-card" onclick="setFilter('REJECT_NEUTRAL_NO_CONTEXT')">
      <div class="stat-val">{stats_reason.get('REJECT_NEUTRAL_NO_CONTEXT', 0):,}</div>
      <div class="stat-label">НЕЙТРАЛЬНЫЯ БЕЗ КАНТЭКСТУ</div>
    </div>
    <div class="stat-card" onclick="setFilter('REJECT_TRASIANKA_BELAZAR')">
      <div class="stat-val">{stats_reason.get('REJECT_TRASIANKA_BELAZAR', 0):,}</div>
      <div class="stat-label">ТРАСЯНКА / БЕЛАЗАР</div>
    </div>
  </div>

  <div class="controls">
    <input type="text" id="searchInput" class="search-input" placeholder="🔍 Пошук па назве, аўтару або тэксце абзаца..." oninput="handleSearch()">
    <div id="filterCount" style="color: var(--muted); font-size: 14px;"></div>
  </div>
</div>

<div id="recordsContainer"></div>

<div class="pagination">
  <button id="prevBtn" class="page-btn" onclick="prevPage()">← Папярэдняя</button>
  <span id="pageInfo" class="page-info">Старонка 1 з 1</span>
  <button id="nextBtn" class="page-btn" onclick="nextPage()">Наступная →</button>
</div>

<script>
  const ALL_RECORDS = {json_data};
  let currentFilter = 'ALL';
  let searchQuery = '';
  let currentPage = 1;
  const PAGE_SIZE = 100;
  let filteredRecords = ALL_RECORDS;

  function getBadgeClass(reason) {{
    if (reason === 'REJECT_LOW_CONFIDENCE_AMBIGUOUS') return 'badge-ambiguous';
    if (reason === 'REJECT_RUSSIAN_CHARS') return 'badge-russian';
    if (reason === 'REJECT_OCR_HOMOGLYPH') return 'badge-ocr';
    if (reason === 'REJECT_ORTHOGRAPHIC_CHIMERA') return 'badge-chimera';
    if (reason === 'REJECT_NEUTRAL_NO_CONTEXT') return 'badge-neutral';
    if (reason === 'REJECT_TRASIANKA_BELAZAR') return 'badge-trasianka';
    return 'badge-ambiguous';
  }}

  function updateFiltered() {{
    filteredRecords = ALL_RECORDS.filter(r => {{
      const matchFilter = (currentFilter === 'ALL' || r.reason === currentFilter);
      if (!matchFilter) return false;
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      return r.title.toLowerCase().includes(q) ||
             r.author.toLowerCase().includes(q) ||
             r.snippet.toLowerCase().includes(q);
    }});
    currentPage = 1;
    render();
  }}

  function setFilter(filter) {{
    currentFilter = filter;
    document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('active'));
    event.currentTarget.classList.add('active');
    updateFiltered();
  }}

  function handleSearch() {{
    searchQuery = document.getElementById('searchInput').value.trim();
    updateFiltered();
  }}

  function prevPage() {{
    if (currentPage > 1) {{
      currentPage--;
      render();
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}
  }}

  function nextPage() {{
    const totalPages = Math.ceil(filteredRecords.length / PAGE_SIZE);
    if (currentPage < totalPages) {{
      currentPage++;
      render();
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}
  }}

  function copyQuery(btn, query) {{
    navigator.clipboard.writeText(query).then(() => {{
      const origText = btn.innerHTML;
      btn.innerHTML = '✓ Скапіявана для Ctrl+F!';
      btn.classList.add('copied');
      setTimeout(() => {{
        btn.innerHTML = origText;
        btn.classList.remove('copied');
      }}, 2000);
    }});
  }}

  function render() {{
    const container = document.getElementById('recordsContainer');
    const totalPages = Math.max(1, Math.ceil(filteredRecords.length / PAGE_SIZE));
    
    document.getElementById('filterCount').innerText = `Знойдзена: ${{filteredRecords.length.toLocaleString()}} запісаў`;
    document.getElementById('pageInfo').innerText = `Старонка ${{currentPage}} з ${{totalPages}}`;
    document.getElementById('prevBtn').disabled = (currentPage === 1);
    document.getElementById('nextBtn').disabled = (currentPage >= totalPages);

    const startIdx = (currentPage - 1) * PAGE_SIZE;
    const pageItems = filteredRecords.slice(startIdx, startIdx + PAGE_SIZE);

    if (pageItems.length === 0) {{
      container.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--muted);">Нічога не знойдзена па вашым запыце.</div>';
      return;
    }}

    let html = '';
    for (const r of pageItems) {{
      const badgeCls = getBadgeClass(r.reason);
      const safeTitle = r.title.replace(/"/g, '&quot;');
      const safeAuthor = r.author.replace(/"/g, '&quot;');
      const safeQuery = r.ctrl_f.replace(/"/g, '&quot;');

      html += `
      <div class="item-card">
        <div class="card-header">
          <div>
            <div class="card-title">${{safeTitle}}</div>
            <div class="card-author">${{safeAuthor}} (${{r.genre}})</div>
          </div>
          <span class="badge ${{badgeCls}}">${{r.reason}}</span>
        </div>
        <div class="snippet">${{r.snippet}}</div>
        <div class="card-actions">
          <a class="btn-link" href="${{r.frag_url}}" target="_blank" rel="noopener noreferrer">
            🔗 Адкрыць на knihi.com з падсветкай
          </a>
          <button class="btn-copy" onclick="copyQuery(this, '${{safeQuery}}')">
            📋 Ctrl+F: "${{safeQuery}}"
          </button>
          ${{r.features ? `<span class="features-info">🚨 ${{r.features}}</span>` : ''}}
        </div>
      </div>
      `;
    }}
    container.innerHTML = html;
  }}

  // Initial render
  updateFiltered();
</script>

</body>
</html>
"""
    with open(HTML_OUT, "w", encoding="utf-8") as f_html:
        f_html.write(html_content)

    print(f"Validation reports generated:\n  HTML: {HTML_OUT}\n  TSV:  {TSV_OUT}")


if __name__ == "__main__":
    main()
