"""
combine.py — Merge 4 per-candidate CSVs into one reliable dataset.

Uses fuzzy candidate name matching to align candidates across sources,
then resolves vote counts using multi-source voting.

3-pass matching:
  Pass 1: Strict fuzzy match (threshold 0.75)
  Pass 2: Relaxed match for single-source orphans against same-party clusters (0.55)
  Pass 3: Force-merge same constituency + same party (except independents, DT-only JaPa)

Also detects suspicious patterns and writes them to suspicious_matches.csv.

Input:  pipeline/{tbs,ds,bss,dt}_candidates.csv
Output: pipeline/combined_candidates.csv
        pipeline/suspicious_matches.csv
"""

import csv
import os
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from normalize import PARTY_CANONICAL, normalize_candidate_name

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPE = os.path.dirname(os.path.abspath(__file__))

SOURCES = {
    "tbs": os.path.join(PIPE, "tbs_candidates.csv"),
    "ds":  os.path.join(PIPE, "ds_candidates.csv"),
    "bss": os.path.join(PIPE, "bss_candidates.csv"),
    "dt":  os.path.join(PIPE, "dt_candidates.csv"),
}

OUTPUT = os.path.join(PIPE, "combined_candidates.csv")
SUSPICIOUS = os.path.join(PIPE, "suspicious_matches.csv")
MERGE_LOG = os.path.join(PIPE, "merge_log.csv")

JAPA = "Jatiya Party (JaPa)"

# Global list to collect all merge events
_merge_events = []
JP_MANJU = "Jatiya Party (Manju) (JP\u2013Manju)"


def canon_party(p):
    return PARTY_CANONICAL.get(p, p)


def is_independent(party):
    return "independent" in party.lower()


def load_source(path):
    """Load a source CSV into {seat_name: [(candidate, party, votes)]}."""
    by_seat = defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cand = row["candidate"].strip()
            if cand:
                try:
                    votes = int(row["votes"]) if row["votes"] else 0
                except (ValueError, TypeError):
                    votes = 0
                by_seat[row["seat_name"]].append((cand, row["party"].strip(), votes))
    return by_seat


# --- Name similarity ---

def consonant_skeleton(name):
    """Strip vowels and whitespace for consonant-based comparison."""
    return re.sub(r"[aeiou\s\.\,\-]", "", name.lower())


def name_similarity(a, b):
    """Basic fuzzy similarity between two candidate names."""
    na = normalize_candidate_name(a).lower()
    nb = normalize_candidate_name(b).lower()
    if na == nb:
        return 1.0

    wa, wb = set(na.split()), set(nb.split())
    if wa and wb:
        overlap = len(wa & wb) / max(len(wa), len(wb))
        if overlap >= 0.7:
            return 0.85 + 0.15 * overlap

    return SequenceMatcher(None, na, nb).ratio()


def relaxed_similarity(a, b):
    """
    Aggressive fuzzy matching for same-party candidates.
    Combines: SequenceMatcher, consonant skeleton, word overlap with surname boost.
    """
    na = normalize_candidate_name(a).lower()
    nb = normalize_candidate_name(b).lower()
    if na == nb:
        return 1.0

    scores = []

    # 1) Sequence matcher
    seq = SequenceMatcher(None, na, nb).ratio()
    scores.append(seq)

    # 2) Word overlap (filter common prefixes)
    wa, wb = set(na.split()), set(nb.split())
    if wa and wb:
        meaningful = (wa & wb) - {"md.", "mst.", "a.", "m.", "s.", "k."}
        if len(meaningful) >= 2:
            scores.append(len(meaningful) / min(len(wa), len(wb)))
        elif len(meaningful) == 1:
            word = next(iter(meaningful))
            # Boost if the shared word is the surname (last word)
            is_surname = (word == na.split()[-1] == nb.split()[-1])
            scores.append(0.55 if is_surname else 0.4)

    # 3) Consonant skeleton
    ca, cb = consonant_skeleton(na), consonant_skeleton(nb)
    if ca and cb:
        scores.append(SequenceMatcher(None, ca, cb).ratio())

    # 4) Blend bonus
    if len(scores) >= 2 and seq >= 0.4:
        scores.append((seq + max(scores)) / 2)

    return max(scores) if scores else 0.0


# --- Vote resolution ---

SOURCE_PRIORITY = ["dt", "tbs", "ds", "bss"]


def resolve_votes(votes_dict):
    """
    Pick the best vote count from multiple sources.

    Strategy:
      1. Group values within 2% tolerance into clusters.
      2. If a cluster has 2+ sources agreeing, use its median.
      3. Otherwise fall back to priority order: dt > tbs > ds > bss.
    """
    vals = [(src, v) for src, v in votes_dict.items() if v > 0]
    if not vals:
        return 0
    if len(vals) == 1:
        return vals[0][1]

    # Cluster by 2% tolerance
    clusters = []
    for src, v in sorted(vals, key=lambda x: x[1]):
        placed = False
        for cl in clusters:
            if cl[0][1] > 0 and abs(v - cl[0][1]) / cl[0][1] <= 0.02:
                cl.append((src, v))
                placed = True
                break
        if not placed:
            clusters.append([(src, v)])

    best = max(clusters, key=len)
    if len(best) >= 2:
        sorted_v = sorted(v for _, v in best)
        return sorted_v[len(sorted_v) // 2]  # median

    # No agreement — use highest-priority source
    by_src = dict(vals)
    for p in SOURCE_PRIORITY:
        if p in by_src:
            return by_src[p]
    return vals[0][1]


# --- Candidate matching ---

def match_candidates(seat, sources_data):
    """
    Match candidates across sources for a single seat.
    Pass 1: strict (0.75), Pass 2: relaxed for orphans (0.55),
    Pass 3: force-merge same party (except independents, DT-only JaPa).
    """
    clusters = []

    # Pass 1: strict matching
    for src, candidates in sources_data.items():
        for cand_name, party, votes in candidates:
            c_party = canon_party(party)
            best, best_score = None, 0

            for cl in clusters:
                score = name_similarity(cand_name, cl["name"])
                if canon_party(cl["party"]) == c_party:
                    score += 0.1
                if score > best_score:
                    best_score, best = score, cl

            if best and best_score >= 0.75 and src not in best["sources"]:
                _merge_events.append({
                    "seat": seat, "pass": 1,
                    "merged_name": cand_name, "merged_source": src,
                    "merged_party": canon_party(party),
                    "into_name": best["name"],
                    "into_sources": ",".join(sorted(best["sources"])),
                    "into_party": canon_party(best["party"]),
                    "similarity": f"{best_score:.2f}",
                    "note": "strict match",
                })
                best["sources"].add(src)
                best["votes"][src] = votes
                if len(cand_name) > len(best["name"]):
                    best["name"] = cand_name
            else:
                clusters.append({
                    "name": cand_name, "party": party,
                    "votes": {src: votes}, "sources": {src},
                })

    # Pass 2: relaxed matching for single-source orphans
    # Repeatedly try to merge orphans (1-source clusters) into better-matched clusters.
    # Prioritize merging into multi-source clusters over other orphans.
    # Restarts after each merge since merging changes cluster membership.
    changed = True
    while changed:
        changed = False
        orphans = [c for c in clusters if len(c["sources"]) == 1]
        multi = [c for c in clusters if len(c["sources"]) > 1]

        for orphan in orphans:
            o_party = canon_party(orphan["party"])
            o_src = next(iter(orphan["sources"]))

            # Find best same-party match (multi-source first for stability)
            best, best_score = None, 0
            for target in multi + orphans:
                if target is orphan or o_src in target["sources"]:
                    continue
                if canon_party(target["party"]) != o_party:
                    continue
                score = relaxed_similarity(orphan["name"], target["name"])
                if score > best_score:
                    best_score, best = score, target

            if best and best_score >= 0.55:
                _merge_events.append({
                    "seat": seat, "pass": 2,
                    "merged_name": orphan["name"],
                    "merged_source": ",".join(sorted(orphan["sources"])),
                    "merged_party": canon_party(orphan["party"]),
                    "into_name": best["name"],
                    "into_sources": ",".join(sorted(best["sources"])),
                    "into_party": canon_party(best["party"]),
                    "similarity": f"{best_score:.2f}",
                    "note": "relaxed orphan match",
                })
                _merge_into(best, orphan)
                clusters.remove(orphan)
                changed = True
                break  # restart — cluster list changed

    # Pass 3: force-merge same party (except independents, DT-only JaPa)
    # Assumption: each party runs at most one candidate per seat, so remaining
    # same-party fragments must be the same person. Skip independents (multiple
    # per seat) and DT-only JaPa entries (DT often mislabels parties as JaPa).
    changed = True
    while changed:
        changed = False
        by_party = defaultdict(list)
        for cl in clusters:
            cp = canon_party(cl["party"])
            if is_independent(cp):
                continue
            if cp == JAPA and cl["sources"] == {"dt"}:
                continue  # DT-only JaPa entries are unreliable
            by_party[cp].append(cl)

        for party, pcs in by_party.items():
            if len(pcs) <= 1:
                continue
            # Merge all fragments into the cluster with the most sources
            pcs.sort(key=lambda c: -len(c["sources"]))
            primary = pcs[0]
            merged_any = False
            for other in pcs[1:]:
                if primary["sources"] & other["sources"]:
                    continue  # overlapping sources = genuinely different people
                sim = relaxed_similarity(primary["name"], other["name"])
                note = "same-party force-merge"
                if sim < 0.5:
                    note = f"same-party force-merge (LOW SIMILARITY)"
                    _add_merge_note(primary, other, party, sim)
                _merge_events.append({
                    "seat": seat, "pass": 3,
                    "merged_name": other["name"],
                    "merged_source": ",".join(sorted(other["sources"])),
                    "merged_party": canon_party(other["party"]),
                    "into_name": primary["name"],
                    "into_sources": ",".join(sorted(primary["sources"])),
                    "into_party": canon_party(primary["party"]),
                    "similarity": f"{sim:.2f}",
                    "note": note,
                })
                _merge_into(primary, other, keep_existing_votes=True)
                clusters.remove(other)
                merged_any = True
            if merged_any:
                changed = True
                break  # restart — cluster list changed

    return clusters


def _merge_into(target, source, keep_existing_votes=False):
    """Merge source cluster into target."""
    if "merges" not in target:
        target["merges"] = []
    src_str = next(iter(source["sources"]))
    target["merges"].append(
        f"fuzzy-merged '{source['name']}' ({src_str}) -> '{target['name']}' "
        f"(score={relaxed_similarity(source['name'], target['name']):.2f})"
    )
    target["sources"].update(source["sources"])
    for s, v in source["votes"].items():
        if keep_existing_votes and s in target["votes"] and target["votes"][s] > 0:
            continue
        target["votes"][s] = v
    if len(source["name"]) > len(target["name"]):
        target["name"] = source["name"]


def _add_merge_note(primary, other, party, sim):
    """Add a low-similarity merge warning note."""
    p_srcs = ",".join(sorted(primary["sources"]))
    o_srcs = ",".join(sorted(other["sources"]))
    p_votes = "; ".join(f"{s}={v}" for s, v in sorted(primary["votes"].items()))
    o_votes = "; ".join(f"{s}={v}" for s, v in sorted(other["votes"].items()))
    if "merges" not in primary:
        primary["merges"] = []
    primary["merges"].append(
        f"same-party-merged (LOW SIMILARITY {sim:.2f}): "
        f"[{o_srcs}] '{other['name']}' ({o_votes}) "
        f"-> [{p_srcs}] '{primary['name']}' ({p_votes}), party={party}"
    )


# --- Suspicious match detection ---

def detect_suspicious(all_data):
    """Detect cross-party matches: same name under different parties in same seat."""
    issues = []

    # Build index: normalized_name -> [(src, seat, party, raw_name, votes)]
    index = defaultdict(list)
    for src, src_data in all_data.items():
        for seat, candidates in src_data.items():
            for cand, party, votes in candidates:
                norm = normalize_candidate_name(cand).lower()
                index[norm].append((src, seat, canon_party(party), cand, votes))

    for norm_name, entries in index.items():
        # Group by seat
        by_seat = defaultdict(list)
        for src, seat, party, raw, votes in entries:
            by_seat[seat].append((src, party, raw, votes))

        for seat, seat_entries in by_seat.items():
            parties = set(e[1] for e in seat_entries)
            if len(parties) <= 1:
                continue

            dt_parties = set(e[1] for e in seat_entries if e[0] == "dt")
            non_dt_parties = set(e[1] for e in seat_entries if e[0] != "dt")

            # Determine auto-fix status (in priority order)
            status = _classify_cross_party(seat_entries, parties, dt_parties, non_dt_parties)

            detail = "; ".join(f"{e[0]}: {e[2]} ({e[1]}, {e[3]} votes)" for e in seat_entries)
            issues.append({
                "type": "cross-party-same-seat",
                "seat": seat,
                "normalized_name": norm_name,
                "detail": detail,
                "status": status,
            })

    return issues


def _classify_cross_party(seat_entries, parties, dt_parties, non_dt_parties):
    """Determine auto-fix status for a cross-party entry."""
    # Rule 1: Any single source has this name under multiple parties → different people
    src_parties = defaultdict(set)
    for src, party, *_ in seat_entries:
        src_parties[src].add(party)
    if any(len(p) > 1 for p in src_parties.values()):
        return "auto-fixed: same name confirmed as different candidates (multiple parties in same source)"

    # Rule 2: DT maps to JaPa, others agree on something else
    if dt_parties == {JAPA} and len(non_dt_parties) == 1 and JAPA not in non_dt_parties:
        return f"auto-fixed: dt mapped to JaPa, using {next(iter(non_dt_parties))} from other sources"
    if len(non_dt_parties) == 1 and dt_parties and dt_parties != non_dt_parties and JAPA in dt_parties:
        return f"auto-fixed: dt mapped to JaPa, using {next(iter(non_dt_parties))} from other sources"

    # Rule 3: JaPa vs JP-Manju → prefer JP-Manju
    if parties == {JAPA, JP_MANJU}:
        return "auto-fixed: JaPa vs JP-Manju conflict, using JP-Manju"

    # Rule 4 (last resort): majority of sources agree on one party
    party_counts = Counter(e[1] for e in seat_entries)
    most_common, count = party_counts.most_common(1)[0]
    total = sum(party_counts.values())
    if count > total / 2:
        return f"auto-fixed: majority of sources ({count}/{total}) agree on {most_common}"

    return ""



# --- Main ---

def main():
    all_data = {}
    for src, path in SOURCES.items():
        if os.path.exists(path):
            all_data[src] = load_source(path)
            n = sum(len(v) for v in all_data[src].values())
            print(f"Loaded {src}: {n} candidates across {len(all_data[src])} seats")
        else:
            print(f"WARNING: {path} not found, skipping {src}")

    suspicious = detect_suspicious(all_data)

    all_seats = sorted(set().union(*[d.keys() for d in all_data.values()]))
    print(f"\nTotal unique seats: {len(all_seats)}")

    results = []
    for seat in all_seats:
        sources_for_seat = {src: data[seat] for src, data in all_data.items() if seat in data}
        clusters = match_candidates(seat, sources_for_seat)

        # Collect low-similarity merge warnings
        for cl in clusters:
            for m in cl.get("merges", []):
                if m.startswith("same-party-merged (LOW"):
                    names = re.findall(r"'([^']+)'", m)
                    suspicious.append({
                        "type": "unmatched-same-party",
                        "seat": seat,
                        "normalized_name": " | ".join(names) if names else cl["name"],
                        "detail": m,
                        "status": "auto-fixed: same constituency + same party, force-merged (verify names)",
                    })

        for cl in clusters:
            resolved = resolve_votes(cl["votes"])
            comments = list(cl.get("merges", []))

            # Flag large vote spread
            nonzero = [v for v in cl["votes"].values() if v > 0]
            if len(nonzero) >= 2:
                spread = (max(nonzero) - min(nonzero)) / max(nonzero)
                if spread > 0.20:
                    comments.append(f"vote-mismatch: spread={spread:.0%}")

            results.append({
                "seat_name": seat,
                "candidate": cl["name"],
                "party": canon_party(cl["party"]),
                "votes": resolved,
                "num_sources": len(cl["sources"]),
                "sources": ",".join(sorted(cl["sources"])),
                "vote_details": "; ".join(f"{s}={v}" for s, v in sorted(cl["votes"].items())),
                "comment": "; ".join(comments) if comments else "",
            })

    results.sort(key=lambda r: (r["seat_name"], -r["votes"]))

    fields = ["seat_name", "candidate", "party", "votes", "num_sources", "sources", "vote_details", "comment"]
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(results)

    print(f"\nSaved {len(results)} candidates to {OUTPUT}")
    multi = sum(1 for r in results if r["num_sources"] >= 2)
    print(f"Seats: {len({r['seat_name'] for r in results})}, Candidates with 2+ sources: {multi}/{len(results)}")

    # Write merge log — every merge across all 3 passes
    if _merge_events:
        merge_fields = ["seat", "pass", "merged_name", "merged_source", "merged_party",
                        "into_name", "into_sources", "into_party", "similarity", "note"]
        _merge_events.sort(key=lambda e: (e["seat"], e["pass"]))
        with open(MERGE_LOG, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=merge_fields)
            w.writeheader()
            w.writerows(_merge_events)

        pass_counts = Counter(e["pass"] for e in _merge_events)
        print(f"\nMerge log: {len(_merge_events)} merges written to {MERGE_LOG}")
        for p in sorted(pass_counts):
            print(f"  Pass {p}: {pass_counts[p]}")

    # Write suspicious matches (unfixed first, then fixed)
    if suspicious:
        for s in suspicious:
            s.setdefault("status", "")
        suspicious.sort(key=lambda s: (1 if s["status"] else 0, s["type"], s["seat"]))

        with open(SUSPICIOUS, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["type", "seat", "normalized_name", "detail", "status"])
            w.writeheader()
            w.writerows(suspicious)

        type_counts = Counter(s["type"] for s in suspicious)
        print(f"\nSuspicious matches: {len(suspicious)} issues written to {SUSPICIOUS}")
        for t, c in type_counts.items():
            print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
