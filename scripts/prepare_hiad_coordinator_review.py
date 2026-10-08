"""Prepare an auditable, advisory leakage pre-screen for HIAD vignettes.

This tool never approves a vignette. It highlights exact phrase overlap and
sentences that may disclose a completed response so a non-rating coordinator can
review all frozen cases consistently before model-response collection.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re


REFERENCE_FIELDS = (
    "reference_emergency_action",
    "reference_lesson_learnt",
    "reference_corrective_measures",
)
ACTION_PATTERN = re.compile(
    r"\b(?:shut(?:down|\s+down)|stopp?ed|isolat(?:ed|ion)|evacuat(?:ed|ion)|"
    r"taken\s+out\s+of\s+(?:service|operation)|replac(?:ed|ement)|repair(?:ed)?|"
    r"install(?:ed|ation)|investigat(?:ed|ion)|inspect(?:ed|ion)|called|"
    r"followed\s+up|remained\s+operational|safety\s+(?:equipment|system)\s+"
    r"(?:operated|performed)|corrective\s+action|returned\s+to\s+service)\b",
    flags=re.IGNORECASE,
)
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?", flags=re.IGNORECASE)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean(value: object) -> str:
    return re.sub(
        r"\s+", " ", str(value or "").replace("_x000D_", " ").replace("\\n", " ")
    ).strip()


def _tokens(value: object) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(_clean(value))]


def _sentences(value: object) -> list[str]:
    text = _clean(value)
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+|\s*\n+\s*", text) if item.strip()]


def _maximal_overlap_phrases(
    input_text: str, reference_text: str, min_tokens: int = 4, max_phrases: int = 8
) -> list[str]:
    """Return deterministic maximal exact token spans shared by both texts."""
    source = _tokens(input_text)
    reference = _tokens(reference_text)
    if len(source) < min_tokens or len(reference) < min_tokens:
        return []
    reference_windows: dict[tuple[str, ...], list[int]] = {}
    for start in range(len(reference) - min_tokens + 1):
        key = tuple(reference[start : start + min_tokens])
        reference_windows.setdefault(key, []).append(start)
    candidates: set[tuple[str, ...]] = set()
    for source_start in range(len(source) - min_tokens + 1):
        key = tuple(source[source_start : source_start + min_tokens])
        for reference_start in reference_windows.get(key, []):
            length = min_tokens
            while (
                source_start + length < len(source)
                and reference_start + length < len(reference)
                and source[source_start + length] == reference[reference_start + length]
            ):
                length += 1
            candidates.add(tuple(source[source_start : source_start + length]))
    ordered = sorted(candidates, key=lambda item: (-len(item), " ".join(item)))
    maximal: list[tuple[str, ...]] = []
    for candidate in ordered:
        phrase = " ".join(candidate)
        if any(phrase in " ".join(existing) for existing in maximal):
            continue
        maximal.append(candidate)
        if len(maximal) >= max_phrases:
            break
    return [" ".join(item) for item in maximal]


def _screen(case: dict, min_overlap_tokens: int) -> dict[str, object]:
    context = case.get("input_context") or {}
    input_text = " ".join(
        _clean(context.get(field)) for field in ("title", "description")
    )
    reference_text = " ".join(_clean(case.get(field)) for field in REFERENCE_FIELDS)
    overlaps = _maximal_overlap_phrases(
        input_text, reference_text, min_tokens=min_overlap_tokens
    )
    sentence_review = []
    retained_sentences = []
    action_sentences = []
    for position, sentence in enumerate(_sentences(context.get("description")), start=1):
        sentence_overlaps = _maximal_overlap_phrases(
            sentence, reference_text, min_tokens=min_overlap_tokens
        )
        possible_completed_action = bool(ACTION_PATTERN.search(sentence))
        if possible_completed_action:
            action_sentences.append(sentence)
        else:
            retained_sentences.append(sentence)
        reasons = []
        if possible_completed_action:
            reasons.append("possible completed response/action")
        if sentence_overlaps:
            longest_sentence_overlap = max(
                len(_tokens(phrase)) for phrase in sentence_overlaps
            )
            reasons.append(
                f"exact overlap with coordinator-only reference "
                f"({longest_sentence_overlap} tokens)"
            )
        sentence_review.append(
            {
                "position": position,
                "sentence": sentence,
                "machine_suggestion": (
                    "REVIEW_REMOVE" if possible_completed_action else "RETAIN_WITH_REVIEW"
                ),
                "reasons": reasons,
                "exact_overlap_phrases": sentence_overlaps,
            }
        )
    longest = max((len(_tokens(phrase)) for phrase in overlaps), default=0)
    if longest >= 8 or len(action_sentences) >= 2:
        tier = "HIGH"
    elif overlaps or action_sentences:
        tier = "MEDIUM"
    else:
        tier = "LOW"
    return {
        "event_id": str(case["event_id"]),
        "stratum": str(case.get("stratum") or ""),
        "quality": str(case.get("quality") or ""),
        "advisory_tier": tier,
        "longest_exact_overlap_tokens": longest,
        "exact_overlap_phrases": overlaps,
        "possible_completed_action_sentences": action_sentences,
        # This is deliberately a separate, non-authoritative draft. It removes
        # only sentences matched as completed actions and never mutates the source.
        "machine_suggested_description": " ".join(retained_sentences),
        "machine_removed_sentence_count": len(action_sentences),
        "machine_sentence_review": sentence_review,
        "coordinator_leakage_decision": "",
        "rewrite_required_yes_no": "",
        "coordinator_notes": "",
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "event_id", "stratum", "quality", "advisory_tier",
        "longest_exact_overlap_tokens", "exact_overlap_phrases",
        "possible_completed_action_sentences", "machine_suggested_description",
        "machine_removed_sentence_count", "machine_sentence_review_json",
        "coordinator_leakage_decision",
        "rewrite_required_yes_no", "coordinator_notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            exported = dict(row)
            exported["exact_overlap_phrases"] = " || ".join(row["exact_overlap_phrases"])
            exported["possible_completed_action_sentences"] = " || ".join(
                row["possible_completed_action_sentences"]
            )
            exported["machine_sentence_review_json"] = json.dumps(
                row["machine_sentence_review"], ensure_ascii=False
            )
            exported.pop("machine_sentence_review", None)
            writer.writerow(exported)


def _write_html(path: Path, casebook: dict, rows: list[dict[str, object]]) -> None:
    cases = {str(case["event_id"]): case for case in casebook["cases"]}
    sections = []
    for row in rows:
        case = cases[row["event_id"]]
        context = case["input_context"]
        references = "".join(
            f"<h4>{html.escape(field.replace('_', ' ').title())}</h4>"
            f"<p>{html.escape(_clean(case.get(field)) or '[empty]')}</p>"
            for field in REFERENCE_FIELDS
        )
        overlap_items = "".join(
            f"<li>{html.escape(item)}</li>" for item in row["exact_overlap_phrases"]
        ) or "<li>None detected</li>"
        action_items = "".join(
            f"<li>{html.escape(item)}</li>"
            for item in row["possible_completed_action_sentences"]
        ) or "<li>None detected</li>"
        sentence_items = "".join(
            "<li><strong>#{position} · {suggestion}</strong> — {sentence}"
            "<br><small>{reasons}</small></li>".format(
                position=item["position"],
                suggestion=html.escape(item["machine_suggestion"]),
                sentence=html.escape(item["sentence"]),
                reasons=html.escape("; ".join(item["reasons"]) or "no automated flag"),
            )
            for item in row["machine_sentence_review"]
        )
        suggested_description = str(row["machine_suggested_description"])
        suggestion_disabled = "" if suggested_description else " disabled"
        sections.append(f"""
<section class="case {row['advisory_tier'].lower()}" data-event="{html.escape(row['event_id'])}">
  <h2>Event {html.escape(row['event_id'])} · {html.escape(row['advisory_tier'])} advisory flag
    <span class="case-status">Unresolved</span></h2>
  <div class="grid"><article><h3>Model-visible vignette</h3>
  <label>Title<textarea class="review-title">{html.escape(_clean(context.get('title')))}</textarea></label>
  <label>Description<textarea class="review-description tall">{html.escape(_clean(context.get('description')))}</textarea></label></article>
  <article><h3>Coordinator-only reference</h3>{references}</article></div>
  <h3>Exact overlap candidates</h3><ul>{overlap_items}</ul>
  <h3>Possible completed-action sentences</h3><ul>{action_items}</ul>
  <details class="sentence-review"><summary>Sentence-by-sentence machine review</summary>
    <ol>{sentence_items}</ol></details>
  <div class="machine-draft"><h3>Machine-suggested description · human review required</h3>
    <p>This draft only removes sentences flagged as completed responses. Exact-overlap-only
    sentences remain and every sentence still requires coordinator review.</p>
    <textarea class="machine-suggestion tall" readonly>{html.escape(suggested_description)}</textarea>
    <button class="apply-suggestion" type="button"{suggestion_disabled}>Copy suggestion to editable description</button>
  </div>
  <div class="decision"><label>Decision
    <select class="review-decision"><option value="">Unresolved</option>
      <option value="KEEP">Keep after full review</option>
      <option value="REWRITE">Rewritten to remove hindsight action leakage</option>
    </select></label>
    <label>Coordinator notes<textarea class="review-notes"></textarea></label>
    <label><input type="checkbox" class="review-confirm"> I inspected this complete case,
    retained only contemporaneously observable facts, removed response/lesson leakage,
    and added no facts.</label></div>
</section>""")
    safe_casebook_json = json.dumps(casebook, ensure_ascii=False).replace("<", "\\u003c")
    application_script = r"""
const sourceCasebook = JSON.parse(document.getElementById('casebook-data').textContent);
const reviewSections = [...document.querySelectorAll('section.case')];
const storageKey = `hiad-coordinator-review:${sourceCasebook.source || 'unknown'}:${reviewSections.map(section => section.dataset.event).join(',')}`;

function caseState(section) {
  return {
    eventId: section.dataset.event,
    title: section.querySelector('.review-title').value,
    description: section.querySelector('.review-description').value,
    decision: section.querySelector('.review-decision').value,
    notes: section.querySelector('.review-notes').value,
    confirmed: section.querySelector('.review-confirm').checked
  };
}

function caseComplete(section) {
  const state = caseState(section);
  return Boolean(state.title.trim() && state.description.trim() && state.decision && state.confirmed);
}

function updateProgress() {
  const completed = reviewSections.filter(caseComplete).length;
  document.getElementById('review-progress').textContent = `${completed} / ${reviewSections.length} complete`;
  for (const section of reviewSections) {
    const done = caseComplete(section);
    section.classList.toggle('complete', done);
    section.querySelector('.case-status').textContent = done ? 'Complete' : 'Unresolved';
  }
}

function saveDraft(showNotice = false) {
  const draft = {
    coordinatorCode: document.getElementById('coordinator-code').value,
    qualified: document.getElementById('coordinator-qualified').checked,
    cases: reviewSections.map(caseState),
    savedAt: new Date().toISOString()
  };
  localStorage.setItem(storageKey, JSON.stringify(draft));
  const status = document.getElementById('draft-status');
  status.textContent = `Draft saved locally · ${new Date(draft.savedAt).toLocaleString()}`;
  if (showNotice) status.classList.add('notice-flash');
  window.setTimeout(() => status.classList.remove('notice-flash'), 1000);
}

function restoreDraft() {
  let draft;
  try {
    draft = JSON.parse(localStorage.getItem(storageKey) || 'null');
  } catch (_) {
    draft = null;
  }
  if (!draft || !Array.isArray(draft.cases)) return;
  const byId = new Map(draft.cases.map(item => [String(item.eventId), item]));
  document.getElementById('coordinator-code').value = draft.coordinatorCode || '';
  document.getElementById('coordinator-qualified').checked = draft.qualified === true;
  for (const section of reviewSections) {
    const saved = byId.get(section.dataset.event);
    if (!saved) continue;
    section.querySelector('.review-title').value = saved.title || '';
    section.querySelector('.review-description').value = saved.description || '';
    section.querySelector('.review-decision').value = saved.decision || '';
    section.querySelector('.review-notes').value = saved.notes || '';
    section.querySelector('.review-confirm').checked = saved.confirmed === true;
  }
  document.getElementById('draft-status').textContent = draft.savedAt
    ? `Local draft restored · ${new Date(draft.savedAt).toLocaleString()}`
    : 'Local draft restored';
}

function nextUnresolved() {
  const currentTop = window.scrollY + 10;
  const unresolved = reviewSections.filter(section => !caseComplete(section));
  if (!unresolved.length) {
    alert('All cases are complete. Validate and export the approved JSON.');
    return;
  }
  const next = unresolved.find(section => section.offsetTop > currentTop) || unresolved[0];
  next.scrollIntoView({behavior: 'smooth', block: 'center'});
  next.querySelector('.review-decision').focus();
}

for (const button of document.querySelectorAll('.apply-suggestion')) {
  button.addEventListener('click', () => {
    const section = button.closest('section.case');
    const suggestion = section.querySelector('.machine-suggestion').value.trim();
    if (!suggestion) return;
    section.querySelector('.review-description').value = suggestion;
    section.querySelector('.review-decision').value = 'REWRITE';
    section.querySelector('.review-confirm').checked = false;
    section.querySelector('.review-description').focus();
    saveDraft();
    updateProgress();
  });
}
function downloadApprovedCasebook() {
  const coordinatorCode = document.getElementById('coordinator-code').value.trim();
  const qualified = document.getElementById('coordinator-qualified').checked;
  if (!coordinatorCode || !qualified) {
    alert('Enter a coded coordinator ID and confirm the qualification/independence declaration.');
    return;
  }
  const approved = JSON.parse(JSON.stringify(sourceCasebook));
  const caseById = new Map(approved.cases.map(item => [String(item.event_id), item]));
  for (const section of document.querySelectorAll('section.case')) {
    const eventId = section.dataset.event;
    const decision = section.querySelector('.review-decision').value;
    const confirmed = section.querySelector('.review-confirm').checked;
    const title = section.querySelector('.review-title').value.trim();
    const description = section.querySelector('.review-description').value.trim();
    const notes = section.querySelector('.review-notes').value.trim();
    const item = caseById.get(eventId);
    if (!item || !decision || !confirmed || !title || !description) {
      alert(`Event ${eventId} is unresolved, unconfirmed, or empty. Every frozen case must be retained and reviewed.`);
      section.scrollIntoView({behavior: 'smooth', block: 'center'});
      return;
    }
    const unchanged = title === String(item.input_context.title).trim()
      && description === String(item.input_context.description).replace(/_x000D_/g, ' ').replace(/\\n/g, ' ').replace(/\s+/g, ' ').trim();
    if ((decision === 'KEEP' && !unchanged) || (decision === 'REWRITE' && unchanged)) {
      alert(`Event ${eventId}: choose KEEP only for unchanged text and REWRITE only after editing.`);
      section.scrollIntoView({behavior: 'smooth', block: 'center'});
      return;
    }
    item.input_context.title = title;
    item.input_context.description = description;
    item.narrative_action_leakage_review = 'PASS';
    item.expert_vignette_approved = 'YES';
    item.coordinator_review = {
      coordinator_code: coordinatorCode,
      decision,
      notes,
      reviewed_at_utc: new Date().toISOString(),
      confirmation: 'response/lesson leakage removed without adding facts'
    };
  }
  approved.coordinator_review_metadata = {
    coordinator_code: coordinatorCode,
    completed_at_utc: new Date().toISOString(),
    all_frozen_cases_retained: approved.cases.length === document.querySelectorAll('section.case').length,
    generated_by: 'prepare_hiad_coordinator_review.py interactive review'
  };
  const blob = new Blob([JSON.stringify(approved, null, 2) + '\n'], {type: 'application/json'});
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'approved_holdout_casebook.json';
  link.click();
  URL.revokeObjectURL(link.href);
  localStorage.removeItem(storageKey);
  document.getElementById('draft-status').textContent = 'Approved JSON exported · local draft cleared';
}
document.getElementById('export-approved').addEventListener('click', downloadApprovedCasebook);
document.getElementById('save-draft').addEventListener('click', () => saveDraft(true));
document.getElementById('next-unresolved').addEventListener('click', nextUnresolved);
document.getElementById('clear-draft').addEventListener('click', () => {
  if (!confirm('Clear the locally saved draft and reload the original casebook?')) return;
  localStorage.removeItem(storageKey);
  window.location.reload();
});
for (const control of document.querySelectorAll('textarea, select, input')) {
  control.addEventListener('input', () => { saveDraft(); updateProgress(); });
  control.addEventListener('change', () => { saveDraft(); updateProgress(); });
}
restoreDraft();
updateProgress();
"""
    path.write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>HIAD coordinator leakage review</title><style>
body{{font:15px/1.5 Arial,sans-serif;max-width:1200px;margin:2rem auto;color:#18324a}}
.notice{{background:#fff4d6;border-left:5px solid #b36b00;padding:1rem}}
.toolbar{{position:sticky;top:0;background:#eaf2f7;border:1px solid #b8cad7;padding:1rem;z-index:5}}
.case{{border:1px solid #ccd9e3;border-left:6px solid #6b7c8f;padding:1rem;margin:1rem 0;break-inside:avoid}}
.case.complete{{border-color:#138a72;background:#fbfffd}}.case-status{{float:right;font-size:.85rem;color:#526579}}
.case.high{{border-left-color:#b42318}}.case.medium{{border-left-color:#b36b00}}
.case.low{{border-left-color:#138a72}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}
article{{background:#f5f8fa;padding:.8rem}}.decision{{background:#eef4f8;padding:.8rem}}
.machine-draft{{background:#fff8e7;border-left:4px solid #b36b00;padding:.8rem;margin:1rem 0}}
.machine-draft p,small{{color:#526579}}.sentence-review{{margin:.8rem 0}}
label{{display:block;margin:.5rem 0}}textarea,select,input[type=text]{{box-sizing:border-box;width:100%;padding:.55rem}}
textarea{{min-height:3.5rem}}textarea.tall{{min-height:10rem}}input[type=checkbox]{{width:auto}}
button{{background:#075985;color:white;border:0;border-radius:4px;padding:.65rem 1rem;font-weight:bold;cursor:pointer}}
.secondary{{background:#526579}}.progress{{font-weight:bold;margin:.4rem 0}}#draft-status{{font-size:.85rem;color:#526579}}
.notice-flash{{color:#075985!important;font-weight:bold}}
@media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><h1>HIAD vignette leakage review</h1>
<p class="notice"><strong>Advisory pre-screen only.</strong> Automated flags cannot approve,
rewrite or exclude a case. A qualified non-rating coordinator must inspect every case,
remove hindsight response information without adding facts, and record the final decision.</p>
<div class="toolbar"><label>Coded coordinator ID<input id="coordinator-code" type="text"></label>
<label><input id="coordinator-qualified" type="checkbox"> I am a qualified, non-rating
coordinator and will review every case independently of the response raters.</label>
<div class="progress">Review progress: <span id="review-progress">0 / {len(rows)} complete</span></div>
<div id="draft-status">Drafts stay only in this browser.</div>
<button id="next-unresolved" type="button">Next unresolved case</button>
<button id="save-draft" type="button" class="secondary">Save local draft</button>
<button id="clear-draft" type="button" class="secondary">Clear local draft</button>
<button id="export-approved" type="button">Validate all cases and export approved JSON</button></div>
{''.join(sections)}
<script id="casebook-data" type="application/json">{safe_casebook_json}</script>
<script>{application_script}</script></body></html>""", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--casebook", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-overlap-tokens", type=int, default=4)
    args = parser.parse_args()
    if args.min_overlap_tokens < 3:
        raise SystemExit("--min-overlap-tokens must be at least 3")
    casebook = json.loads(args.casebook.read_text(encoding="utf-8"))
    cases = casebook.get("cases")
    if not isinstance(cases, list) or not cases:
        raise SystemExit("Casebook must contain a non-empty cases list")
    event_ids = [str(case.get("event_id", "")) for case in cases]
    if "" in event_ids or len(event_ids) != len(set(event_ids)):
        raise SystemExit("Casebook event IDs must be non-empty and unique")
    rows = [_screen(case, args.min_overlap_tokens) for case in cases]
    args.output.mkdir(parents=True, exist_ok=True)
    _write_csv(args.output / "coordinator_review.csv", rows)
    _write_html(args.output / "coordinator_review.html", casebook, rows)
    tier_counts = {
        tier: sum(row["advisory_tier"] == tier for row in rows)
        for tier in ("HIGH", "MEDIUM", "LOW")
    }
    suggested_rewrite_counts = {
        "cases_with_removed_action_sentences": sum(
            int(row["machine_removed_sentence_count"]) > 0 for row in rows
        ),
        "sentences_suggested_for_removal": sum(
            int(row["machine_removed_sentence_count"]) for row in rows
        ),
        "cases_without_machine_draft": sum(
            not str(row["machine_suggested_description"]).strip() for row in rows
        ),
    }
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "casebook": args.casebook.name,
        "casebook_sha256": _sha256(args.casebook),
        "case_count": len(rows),
        "advisory_only": True,
        "human_review_required_for_every_case": True,
        "min_overlap_tokens": args.min_overlap_tokens,
        "tier_counts": tier_counts,
        "machine_rewrite_suggestion": {
            "advisory_only": True,
            "source_casebook_modified": False,
            **suggested_rewrite_counts,
        },
        "output_sha256": {
            "coordinator_review.csv": _sha256(args.output / "coordinator_review.csv"),
            "coordinator_review.html": _sha256(args.output / "coordinator_review.html"),
        },
    }
    (args.output / "prescreen_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
