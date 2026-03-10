"""
combine.py — Merge 4 per-candidate CSVs into one reliable dataset.

Uses fuzzy candidate name matching to align candidates across sources,
then resolves vote counts using multi-source voting.

Also detects:
  - Cross-party matches: same name matched to different parties in same seat
  - Unmatched same-party: same party+seat candidates that didn't merge across sources

Input:  pipeline/{tbs,ds,bss,dt}_candidates.csv
Output: pipeline/combined_candidates.csv
        pipeline/suspicious_matches.csv
"""

import csv
import os
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from normalize import (
    PARTY_CANONICAL,
    normalize_candidate_name,
    normalize_party,
    normalize_seat_name,
)

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


def canon_party(p):
    return PARTY_CANONICAL.get(p, p)


def load_source(path):
    """Load a source CSV into {seat_name: [(candidate, party, votes)]}."""
    by_seat = defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            seat = row["seat_name"]
            cand = row["candidate"].strip()
            party = row["party"].strip()
            try:
                votes = int(row["votes"]) if row["votes"] else 0
            except (ValueError, TypeError):
                votes = 0
            if cand:
                by_seat[seat].append((cand, party, votes))
    return by_seat


def name_similarity(a, b):
    """Fuzzy similarity between two candidate names."""
    na = normalize_candidate_name(a).lower()
    nb = normalize_candidate_name(b).lower()

    if na == nb:
        return 1.0

    wa = set(na.split())
    wb = set(nb.split())
    if wa and wb:
        overlap = len(wa & wb) / max(len(wa), len(wb))
        if overlap >= 0.7:
            return 0.85 + 0.15 * overlap

    return SequenceMatcher(None, na, nb).ratio()


def match_candidates(seat, sources_data):
    """
    Match candidates across sources for a single seat.
    Two-pass approach:
      1) Strict matching (threshold 0.75)
      2) Relaxed matching for single-source orphans against same-party clusters
         they didn't match in pass 1. Uses lower threshold (0.55) and extra
         heuristics like consonant skeleton, word overlap, etc.
    """
    clusters = []  # [{name, party, votes: {src: v}, sources: set}]

    # --- Pass 1: strict matching ---
    for src, candidates in sources_data.items():
        for cand_name, party, votes in candidates:
            c_party = canon_party(party)

            best_match = None
            best_score = 0
            for cluster in clusters:
                score = name_similarity(cand_name, cluster["name"])
                party_match = canon_party(cluster["party"]) == c_party
                if party_match:
                    score += 0.1
                if score > best_score:
                    best_score = score
                    best_match = cluster

            threshold = 0.75
            if best_match and best_score >= threshold and src not in best_match["sources"]:
                best_match["sources"].add(src)
                best_match["votes"][src] = votes
                if len(cand_name) > len(best_match["name"]):
                    best_match["name"] = cand_name
            else:
                clusters.append({
                    "name": cand_name,
                    "party": party,
                    "votes": {src: votes},
                    "sources": {src},
                })

    # --- Pass 2: relaxed matching for single-source orphans ---
    changed = True
    while changed:
        changed = False
        orphans = [c for c in clusters if len(c["sources"]) == 1]
        multi = [c for c in clusters if len(c["sources"]) > 1]

        for orphan in orphans:
            o_party = canon_party(orphan["party"])
            o_src = next(iter(orphan["sources"]))

            best_match = None
            best_score = 0

            for cluster in multi:
                if o_src in cluster["sources"]:
                    continue
                if canon_party(cluster["party"]) != o_party:
                    continue

                score = relaxed_similarity(orphan["name"], cluster["name"])
                if score > best_score:
                    best_score = score
                    best_match = cluster

            for other in orphans:
                if other is orphan:
                    continue
                if next(iter(other["sources"])) == o_src:
                    continue
                if canon_party(other["party"]) != o_party:
                    continue

                score = relaxed_similarity(orphan["name"], other["name"])
                if score > best_score:
                    best_score = score
                    best_match = other

            if best_match and best_score >= 0.55:
                merge_note = f"fuzzy-merged '{orphan['name']}' ({o_src}) -> '{best_match['name']}' (score={best_score:.2f})"
                if "merges" not in best_match:
                    best_match["merges"] = []
                best_match["merges"].append(merge_note)
                best_match["sources"].update(orphan["sources"])
                for s, v in orphan["votes"].items():
                    best_match["votes"][s] = v
                if len(orphan["name"]) > len(best_match["name"]):
                    best_match["name"] = orphan["name"]
                clusters.remove(orphan)
                changed = True
                break

    # --- Pass 3: force-merge same party (except independents) ---
    # If multiple clusters share the same party in this seat, they must be the same
    # candidate (each party fields exactly one candidate per seat).
    # Skip if party is JaPa and only comes from DT (DT misattributes many candidates to JaPa).
    JAPA = "Jatiya Party (JaPa)"
    changed = True
    while changed:
        changed = False
        by_party = defaultdict(list)
        for cl in clusters:
            cp = canon_party(cl["party"])
            if "independent" not in cp.lower():
                # Skip DT-only JaPa clusters — DT's JaPa mapping is unreliable
                if cp == JAPA and cl["sources"] == {"dt"}:
                    continue
                by_party[cp].append(cl)

        for party, party_clusters in by_party.items():
            if len(party_clusters) <= 1:
                continue
            # Merge all into the first (largest-source) cluster
            party_clusters.sort(key=lambda c: -len(c["sources"]))
            primary = party_clusters[0]
            for other in party_clusters[1:]:
                sim = relaxed_similarity(primary["name"], other["name"])
                p_srcs = ",".join(sorted(primary["sources"]))
                o_srcs = ",".join(sorted(other["sources"]))
                p_votes = "; ".join(f"{s}={v}" for s, v in sorted(primary["votes"].items()))
                o_votes = "; ".join(f"{s}={v}" for s, v in sorted(other["votes"].items()))

                # Only flag as suspicious if names are very different
                if sim < 0.5:
                    merge_note = (
                        f"same-party-merged (LOW SIMILARITY {sim:.2f}): "
                        f"[{o_srcs}] '{other['name']}' ({o_votes}) "
                        f"-> [{p_srcs}] '{primary['name']}' ({p_votes}), party={party}"
                    )
                    if "merges" not in primary:
                        primary["merges"] = []
                    primary["merges"].append(merge_note)

                # Always merge — same constituency + same party = same candidate
                primary["sources"].update(other["sources"])
                for s, v in other["votes"].items():
                    if s not in primary["votes"] or primary["votes"][s] == 0:
                        primary["votes"][s] = v
                if len(other["name"]) > len(primary["name"]):
                    primary["name"] = other["name"]
                clusters.remove(other)
            changed = True
            break

    return clusters


def consonant_skeleton(name):
    """Strip vowels and whitespace to get consonant skeleton for comparison."""
    return re.sub(r"[aeiou\s\.\,\-]", "", name.lower())


def relaxed_similarity(a, b):
    """
    More aggressive fuzzy matching for same-party candidates.
    Combines multiple signals: SequenceMatcher, word overlap,
    first-name match, consonant skeleton similarity.
    """
    na = normalize_candidate_name(a).lower()
    nb = normalize_candidate_name(b).lower()

    if na == nb:
        return 1.0

    scores = []

    seq_score = SequenceMatcher(None, na, nb).ratio()
    scores.append(seq_score)

    wa = set(na.split())
    wb = set(nb.split())
    shared = wa & wb
    if wa and wb:
        COMMON_WORDS = {"md.", "mst.", "a.", "m.", "s.", "k."}
        meaningful_shared = shared - COMMON_WORDS
        if len(meaningful_shared) >= 2:
            overlap = len(meaningful_shared) / min(len(wa), len(wb))
            scores.append(overlap)
        elif len(meaningful_shared) == 1:
            la = na.split()[-1] if na.split() else ""
            lb = nb.split()[-1] if nb.split() else ""
            word = next(iter(meaningful_shared))
            if word == la == lb:
                scores.append(0.55)
            else:
                scores.append(0.4)

    ca = consonant_skeleton(na)
    cb = consonant_skeleton(nb)
    if ca and cb:
        skel_score = SequenceMatcher(None, ca, cb).ratio()
        scores.append(skel_score)

    if len(scores) >= 2 and seq_score >= 0.4:
        scores.append((seq_score + max(scores)) / 2)

    return max(scores) if scores else 0.0


def resolve_votes(votes_dict):
    """
    Resolve vote count from multiple sources.
    Uses cluster/majority logic with 2% tolerance.
    """
    vals = [(src, v) for src, v in votes_dict.items() if v > 0]
    if not vals:
        return 0

    if len(vals) == 1:
        return vals[0][1]

    sorted_vals = sorted(vals, key=lambda x: x[1])
    clusters = []
    for src, v in sorted_vals:
        placed = False
        for cl in clusters:
            ref = cl[0][1]
            if ref > 0 and abs(v - ref) / ref <= 0.02:
                cl.append((src, v))
                placed = True
                break
        if not placed:
            clusters.append([(src, v)])

    best_cluster = max(clusters, key=len)
    if len(best_cluster) >= 2:
        cluster_vals = sorted([v for _, v in best_cluster])
        mid = len(cluster_vals) // 2
        return cluster_vals[mid]

    priority = ["dt", "tbs", "ds", "bss"]
    for p in priority:
        for src, v in vals:
            if src == p:
                return v
    return vals[0][1]


def detect_suspicious(all_data):
    """
    Detect suspicious patterns across all sources:
    1) Cross-party: same candidate name appears under different parties in same seat
    2) Unmatched same-party: same party in same seat has candidates in different sources
       that didn't get merged (possible missed fuzzy match)
    3) Cross-constituency: same candidate name appears in different seats (rare but possible error)
    """
    issues = []

    # Build a global index: normalized_name -> [(src, seat, party, raw_name, votes)]
    global_index = defaultdict(list)
    for src, src_data in all_data.items():
        for seat, candidates in src_data.items():
            for cand, party, votes in candidates:
                norm = normalize_candidate_name(cand).lower()
                global_index[norm].append((src, seat, canon_party(party), cand, votes))

    # 1) Cross-party in same seat
    JAPA = "Jatiya Party (JaPa)"
    JP_MANJU = "Jatiya Party (Manju) (JP–Manju)"
    for norm_name, entries in global_index.items():
        by_seat = defaultdict(list)
        for src, seat, party, raw, votes in entries:
            by_seat[seat].append((src, party, raw, votes))

        for seat, seat_entries in by_seat.items():
            parties = set(e[1] for e in seat_entries)
            if len(parties) <= 1:
                continue

            # If dt is the only source mapping to JaPa and others agree on
            # a different party, it's a known DT error — auto-resolve
            dt_entries = [e for e in seat_entries if e[0] == "dt"]
            non_dt_entries = [e for e in seat_entries if e[0] != "dt"]
            non_dt_parties = set(e[1] for e in non_dt_entries)
            dt_parties = set(e[1] for e in dt_entries)

            status = ""

            # Check if any single source has this name under multiple parties
            # in this seat — if so, they're genuinely different candidates
            src_parties = defaultdict(set)
            for src, party, raw, votes in seat_entries:
                src_parties[src].add(party)
            any_src_has_both = any(len(p) > 1 for p in src_parties.values())

            if any_src_has_both:
                status = "auto-fixed: same name confirmed as different candidates (multiple parties in same source)"
            elif dt_parties == {JAPA} and len(non_dt_parties) == 1 and JAPA not in non_dt_parties:
                # DT mistakenly mapped to JaPa, others agree — auto-fixed
                status = f"auto-fixed: dt mapped to JaPa, using {next(iter(non_dt_parties))} from other sources"
            elif len(non_dt_parties) == 1 and dt_parties and dt_parties != non_dt_parties and JAPA in dt_parties:
                status = f"auto-fixed: dt mapped to JaPa, using {next(iter(non_dt_parties))} from other sources"
            elif parties == {JAPA, JP_MANJU}:
                # JaPa vs JP-Manju conflict — always prefer JP-Manju
                status = "auto-fixed: JaPa vs JP-Manju conflict, using JP-Manju"

            # Last resort: if majority of sources agree on one party, go with that
            if not status:
                from collections import Counter
                party_counts = Counter(e[1] for e in seat_entries)
                most_common_party, most_common_count = party_counts.most_common(1)[0]
                total = sum(party_counts.values())
                if most_common_count > total / 2:
                    status = f"auto-fixed: majority of sources ({most_common_count}/{total}) agree on {most_common_party}"

            detail = "; ".join(f"{e[0]}: {e[2]} ({e[1]}, {e[3]} votes)" for e in seat_entries)
            issues.append({
                "type": "cross-party-same-seat",
                "seat": seat,
                "normalized_name": norm_name,
                "detail": detail,
                "status": status,
            })

    # 2) Same seat + same party but different sources have candidates that look similar
    #    but weren't merged (check combined output for this after matching)
    # This is handled in main() after matching

    return issues


def detect_unmatched_same_party(seat, clusters, sources_data):
    """
    After matching, find cases where the same party has candidates from
    different sources that ended up in separate clusters (possible missed merge).
    """
    issues = []

    # Group clusters by canonical party
    by_party = defaultdict(list)
    for cl in clusters:
        cp = canon_party(cl["party"])
        by_party[cp].append(cl)

    for party, party_clusters in by_party.items():
        if len(party_clusters) <= 1:
            continue
        # Multiple clusters for same party — check if any are from different sources
        for i, c1 in enumerate(party_clusters):
            for c2 in party_clusters[i+1:]:
                # If they share no sources, they might be the same candidate
                if not c1["sources"] & c2["sources"]:
                    sim = relaxed_similarity(c1["name"], c2["name"])
                    issues.append({
                        "type": "unmatched-same-party",
                        "seat": seat,
                        "normalized_name": f"{c1['name']} vs {c2['name']}",
                        "detail": (
                            f"party={party}, similarity={sim:.2f}, "
                            f"[{','.join(sorted(c1['sources']))}] {c1['name']} vs "
                            f"[{','.join(sorted(c2['sources']))}] {c2['name']}"
                        ),
                    })

    return issues


def main():
    # Load all sources
    all_data = {}
    for src, path in SOURCES.items():
        if os.path.exists(path):
            all_data[src] = load_source(path)
            print(f"Loaded {src}: {sum(len(v) for v in all_data[src].values())} candidates across {len(all_data[src])} seats")
        else:
            print(f"WARNING: {path} not found, skipping {src}")

    # Detect cross-source suspicious patterns
    suspicious = detect_suspicious(all_data)

    # Get all seat names
    all_seats = sorted(set().union(*[d.keys() for d in all_data.values()]))
    print(f"\nTotal unique seats: {len(all_seats)}")

    # Match and resolve
    results = []
    for seat in all_seats:
        sources_for_seat = {}
        for src, src_data in all_data.items():
            if seat in src_data:
                sources_for_seat[src] = src_data[seat]

        clusters = match_candidates(seat, sources_for_seat)

        # Detect low-similarity same-party merges from pass 3
        for cl in clusters:
            if "merges" not in cl:
                continue
            for m in cl["merges"]:
                if m.startswith("same-party-merged (LOW"):
                    # Extract both names from the merge note
                    import re as _re
                    names_match = _re.findall(r"'([^']+)'", m)
                    all_names = " | ".join(names_match) if names_match else cl["name"]
                    suspicious.append({
                        "type": "unmatched-same-party",
                        "seat": seat,
                        "normalized_name": all_names,
                        "detail": m,
                        "status": "auto-fixed: same constituency + same party, force-merged (verify names)",
                    })

        for cl in clusters:
            resolved = resolve_votes(cl["votes"])
            n_sources = len(cl["sources"])
            sources_str = ",".join(sorted(cl["sources"]))

            comments = []

            if "merges" in cl:
                for m in cl["merges"]:
                    comments.append(m)

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
                "num_sources": n_sources,
                "sources": sources_str,
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
    seats = len({r["seat_name"] for r in results})
    multi = sum(1 for r in results if r["num_sources"] >= 2)
    print(f"Seats: {seats}, Candidates with 2+ sources: {multi}/{len(results)}")

    # Write suspicious matches report
    if suspicious:
        # Ensure all entries have a status field
        for s in suspicious:
            if "status" not in s:
                s["status"] = ""
        # Sort: unfixed first, fixed at the bottom
        suspicious.sort(key=lambda s: (1 if s["status"] else 0, s["type"], s["seat"]))

        susp_fields = ["type", "seat", "normalized_name", "detail", "status"]
        with open(SUSPICIOUS, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=susp_fields)
            w.writeheader()
            w.writerows(suspicious)
        print(f"\nSuspicious matches: {len(suspicious)} issues written to {SUSPICIOUS}")
        # Summary by type
        from collections import Counter
        type_counts = Counter(s["type"] for s in suspicious)
        for t, c in type_counts.items():
            print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
