"""
combine_new.py — Merge 4 per-candidate CSVs into one reliable dataset.

For each constituency:
  1. Load all entries (candidate, party, votes, source) from 4 source files
  2. Rule 1: Similar name + same party → merge (never merge two from same source)
  3. Rule 2: Same name + different party + same votes → merge (cross-party typo fix)
  4. Rule 3: (reserved)
  5. Resolve votes, flag unmerged suspicious pairs, write results

Input:  pipeline/{tbs,ds,bss,dt}_candidates.csv
Output: pipeline/combined_candidates.csv, merge_log.csv, suspicious_matches.csv
"""

import csv, os, re, sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from normalize import PARTY_CANONICAL, normalize_candidate_name

PIPE = os.path.dirname(os.path.abspath(__file__))

SOURCE_FILES = {
    "tbs": os.path.join(PIPE, "tbs_candidates.csv"),
    "ds":  os.path.join(PIPE, "ds_candidates.csv"),
    "bss": os.path.join(PIPE, "bss_candidates.csv"),
    "dt":  os.path.join(PIPE, "dt_candidates.csv"),
}

SOURCE_PRIORITY = ["dt", "tbs", "ds", "bss"]
JAPA = "Jatiya Party (JaPa)"
JP_MANJU = "Jatiya Party (Manju) (JP\u2013Manju)"


# ── Helpers ──────────────────────────────────────────────────────────────────

def canon(p):
    return PARTY_CANONICAL.get(p, p)


def parse_votes(raw):
    try:
        return int(raw) if raw else 0
    except (ValueError, TypeError):
        return 0


def norm_name(name):
    return normalize_candidate_name(name).lower()


def _expand_initials(name):
    """Normalize initials: 'G. K.' and 'Gk' and 'GK' all → 'g. k.'"""
    # Expand runs of uppercase like 'Gk' → 'G. K.'
    name = re.sub(r'\b([A-Z])([a-z]?)(?=[A-Z])', r'\1. ', name)
    # Normalize 'G.K.' → 'G. K.'
    name = re.sub(r'\.(?=[A-Za-z])', '. ', name)
    return name.lower()


def consonant_skeleton(name):
    return re.sub(r"[aeiou\s\.\,\-]", "", name.lower())


# ── Name similarity ──────────────────────────────────────────────────────────

def name_similarity(a, b):
    """Combined fuzzy similarity score between two candidate names."""
    na, nb = norm_name(a), norm_name(b)
    if na == nb:
        return 1.0

    scores = []

    # Sequence matcher on normalized names
    seq = SequenceMatcher(None, na, nb).ratio()
    scores.append(seq)

    # Also compare with expanded initials (G.K. vs Gk)
    ea, eb = _expand_initials(na), _expand_initials(nb)
    if ea != na or eb != nb:
        seq_exp = SequenceMatcher(None, ea, eb).ratio()
        scores.append(seq_exp)

    # Word overlap
    FILLER = {"md.", "mst.", "a.", "m.", "s.", "k."}
    wa, wb = set(na.split()), set(nb.split())
    if wa and wb:
        meaningful = (wa & wb) - FILLER
        if len(meaningful) >= 2:
            scores.append(len(meaningful) / min(len(wa), len(wb)))
        elif len(meaningful) == 1:
            word = next(iter(meaningful))
            is_surname = (word == na.split()[-1] == nb.split()[-1])
            scores.append(0.55 if is_surname else 0.4)

    # Subset check: if all meaningful words of the shorter name appear in the
    # longer name, it's likely a truncated version (e.g. "Ali" ⊂ "Saheb Ali")
    # Score reflects how much of the longer name is covered.
    ma, mb = wa - FILLER, wb - FILLER
    if ma and mb and ma != mb:
        shorter, longer = (ma, mb) if len(ma) <= len(mb) else (mb, ma)
        if shorter <= longer:
            # Full containment: scale between 0.60 (1/many) and 0.85 (all-but-one)
            coverage = len(shorter) / len(longer)
            scores.append(0.60 + 0.25 * coverage)

    # Consonant skeleton
    ca, cb = consonant_skeleton(na), consonant_skeleton(nb)
    if ca and cb:
        scores.append(SequenceMatcher(None, ca, cb).ratio())

    # Blend bonus
    if len(scores) >= 2 and max(scores) >= 0.4:
        scores.append((seq + max(scores)) / 2)

    return max(scores)


def votes_match(v1, v2):
    """True if two vote counts are similar (within 5% tolerance)."""
    if v1 == 0 or v2 == 0:
        return False
    if v1 == v2:
        return True
    return abs(v1 - v2) / max(v1, v2) <= 0.05


# ── Load ─────────────────────────────────────────────────────────────────────

def load_entries_by_seat():
    """Load all sources into {seat: [{candidate, party, votes, source}, ...]}."""
    by_seat = defaultdict(list)

    for src, path in SOURCE_FILES.items():
        if not os.path.exists(path):
            print(f"WARNING: {path} not found, skipping {src}")
            continue
        n = 0
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cand = row["candidate"].strip()
                if not cand:
                    continue
                by_seat[row["seat_name"]].append({
                    "candidate": cand,
                    "party": row["party"].strip(),
                    "votes": parse_votes(row["votes"]),
                    "source": src,
                })
                n += 1
        seats = sum(1 for entries in by_seat.values() if any(e["source"] == src for e in entries))
        print(f"Loaded {src}: {n} candidates across {seats} seats")

    return by_seat


# ── Cluster operations ───────────────────────────────────────────────────────

def new_cluster(name, party, votes, source):
    return {"name": name, "party": party, "votes": {source: votes}, "sources": {source}}


def merge_into(target, source_cl):
    """Merge source_cl into target. Mutates target."""
    target["sources"].update(source_cl["sources"])
    for s, v in source_cl["votes"].items():
        if s not in target["votes"] or target["votes"][s] == 0:
            target["votes"][s] = v
    if len(source_cl["name"]) > len(target["name"]):
        target["name"] = source_cl["name"]


def log_merge(log, seat, rule, merged, target, sim, note):
    log.append({
        "seat": seat, "rule": rule,
        "merged_name": merged["name"],
        "merged_source": ",".join(sorted(merged["sources"])),
        "merged_party": canon(merged["party"]),
        "merged_votes": "; ".join(f"{s}={v}" for s, v in sorted(merged["votes"].items())),
        "into_name": target["name"],
        "into_sources": ",".join(sorted(target["sources"])),
        "into_party": canon(target["party"]),
        "into_votes": "; ".join(f"{s}={v}" for s, v in sorted(target["votes"].items())),
        "similarity": f"{sim:.2f}",
        "note": note,
    })


def sources_overlap(a, b):
    """True if two clusters share any source — never merge these."""
    return bool(a["sources"] & b["sources"])


# ── Rule 1: Similar name + same party → merge ───────────────────────────────

RULE1_THRESHOLD = 0.65
# Lower threshold when party AND votes both match — strong evidence of same person
RULE1_BOOSTED_THRESHOLD = 0.40

def _have_matching_votes(a, b):
    """True if any vote values match exactly across different sources (both > 0)."""
    for sa, va in a["votes"].items():
        for sb, vb in b["votes"].items():
            if sa != sb and va > 0 and va == vb:
                return True
    return False


def rule1_name_party(seat, clusters, merge_log):
    """Merge clusters with similar names and matching party. Never same source.
    Uses a lower name threshold if votes also match exactly."""
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(clusters):
            for j, b in enumerate(clusters):
                if j <= i:
                    continue
                if sources_overlap(a, b):
                    continue
                if canon(a["party"]) != canon(b["party"]):
                    continue

                sim = name_similarity(a["name"], b["name"])
                threshold = RULE1_THRESHOLD
                # Same party + same votes = strong evidence → lower name bar
                if _have_matching_votes(a, b):
                    threshold = RULE1_BOOSTED_THRESHOLD

                if sim >= threshold:
                    if len(a["sources"]) >= len(b["sources"]):
                        target, merged = a, b
                    else:
                        target, merged = b, a

                    boosted = " [vote-boosted]" if threshold < RULE1_THRESHOLD else ""
                    log_merge(merge_log, seat, 1, merged, target, sim,
                              f"name+party match (sim={sim:.2f}){boosted}")
                    merge_into(target, merged)
                    clusters.remove(merged)
                    changed = True
                    break
            if changed:
                break


# ── Rule 2: Same name + different party + same votes → merge ────────────────

RULE2_NAME_THRESHOLD = 0.80

def rule2_name_votes(seat, clusters, merge_log):
    """
    Merge clusters where name is very similar, votes match,
    but party differs (cross-source party labeling error).
    Never same source.
    """
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(clusters):
            for j, b in enumerate(clusters):
                if j <= i:
                    continue
                if sources_overlap(a, b):
                    continue

                sim = name_similarity(a["name"], b["name"])
                if sim < RULE2_NAME_THRESHOLD:
                    continue

                # Check if any vote values are exactly the same across sources
                has_matching_votes = False
                for sa, va in a["votes"].items():
                    for sb, vb in b["votes"].items():
                        if sa != sb and va > 0 and va == vb:
                            has_matching_votes = True
                            break
                    if has_matching_votes:
                        break

                if not has_matching_votes:
                    continue

                # Merge — keep the party from the cluster with more sources
                if len(a["sources"]) >= len(b["sources"]):
                    target, merged = a, b
                else:
                    target, merged = b, a

                log_merge(merge_log, seat, 2, merged, target, sim,
                          f"name+votes match, party differs: "
                          f"{canon(merged['party'])} → {canon(target['party'])}")
                merge_into(target, merged)
                clusters.remove(merged)
                changed = True
                break
            if changed:
                break


# ── Rule 3: Fix JaPa party labels ────────────────────────────────────────────

def rule3_fix_japa(seat, clusters, merge_log):
    """
    Two fixes:
    1. If DT is the only source saying JaPa, override with the party from other sources.
    2. If a cluster has JaPa vs JP-Manju conflict, use JP-Manju.
    """
    for cl in clusters:
        party = canon(cl["party"])

        # Fix 2: JaPa vs JP-Manju → use JP-Manju
        if party == JAPA:
            # Check if any merge log entry for this seat+candidate involved JP-Manju
            for m in merge_log:
                if m["seat"] != seat:
                    continue
                if m["into_name"] == cl["name"] or m["merged_name"] == cl["name"]:
                    if JP_MANJU in (m["merged_party"], m["into_party"]):
                        old_party = cl["party"]
                        cl["party"] = JP_MANJU
                        log_merge(merge_log, seat, 3,
                                  cl, cl, 1.0,
                                  f"JaPa → JP-Manju override (was {canon(old_party)})")
                        break

    # Fix 1 (separate pass): If a cluster is DT-only JaPa, and another cluster
    # has the same candidate from non-DT sources under a different party, merge them.
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(clusters):
            if canon(a["party"]) != JAPA:
                continue
            if a["sources"] != {"dt"}:
                continue  # only fix DT-only JaPa clusters

            for j, b in enumerate(clusters):
                if j == i or sources_overlap(a, b):
                    continue
                sim = name_similarity(a["name"], b["name"])
                if sim < RULE1_THRESHOLD:
                    continue

                # DT says JaPa, other source says something else → merge into other
                log_merge(merge_log, seat, 3, a, b, sim,
                          f"DT-only JaPa merged: {JAPA} → {canon(b['party'])}")
                merge_into(b, a)
                clusters.remove(a)
                changed = True
                break
            if changed:
                break


# ── Vote resolution ──────────────────────────────────────────────────────────

def load_total_votes_cast():
    """Load total_votes_cast per seat from DS, DT, TBS wide CSVs."""
    from collections import defaultdict
    base = os.path.dirname(PIPE)
    sources = {
        "ds": os.path.join(base, "result_from_source", "result_from_dailystar.csv"),
        "dt": os.path.join(base, "result_from_source", "result_from_dhakatribune.csv"),
        "tbs": os.path.join(base, "result_from_source", "tbsnews_party_by_seat.csv"),
    }
    from normalize import normalize_seat_name
    by_seat = defaultdict(dict)
    for label, path in sources.items():
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                seat = normalize_seat_name(row.get("seat_name", ""))
                tv = row.get("total_votes", "")
                if seat and tv and tv != "-":
                    try:
                        by_seat[seat][label] = int(float(tv))
                    except (ValueError, TypeError):
                        pass

    result = {}
    for seat, vals in by_seat.items():
        pos = {s: v for s, v in vals.items() if v > 0}
        if not pos:
            continue
        if len(pos) == 1:
            result[seat] = next(iter(pos.values()))
            continue
        # Cluster within 5%, pick largest group's max
        clusters = []
        for s, v in sorted(pos.items(), key=lambda x: x[1]):
            placed = False
            for cl in clusters:
                if cl[0][1] > 0 and abs(v - cl[0][1]) / cl[0][1] <= 0.05:
                    cl.append((s, v))
                    placed = True
                    break
            if not placed:
                clusters.append([(s, v)])
        best = max(clusters, key=lambda cl: (len(cl), max(v for _, v in cl)))
        result[seat] = max(v for _, v in best)
    return result


def resolve_votes(votes_by_source, ceiling=None):
    """Pick the best vote: group within 5%, prefer cluster under ceiling if available."""
    vals = {s: v for s, v in votes_by_source.items() if v > 0}
    if not vals:
        return 0
    if len(vals) == 1:
        _, v = next(iter(vals.items()))
        # If only 1 source has votes and 2+ *detailed* sources report 0,
        # treat as suspect inflation. BSS only reports winner+runner-up so
        # its 0 doesn't count as counter-evidence.
        detailed_zeros = [s for s, val in votes_by_source.items()
                          if val == 0 and s != "bss"]
        if len(detailed_zeros) >= 2:
            return 0
        return v

    # Cluster values within 5% tolerance
    clusters = []
    for s, v in sorted(vals.items(), key=lambda x: x[1]):
        placed = False
        for cl in clusters:
            ref = cl[0][1]
            if ref > 0 and abs(v - ref) / ref <= 0.05:
                cl.append((s, v))
                placed = True
                break
        if not placed:
            clusters.append([(s, v)])

    # If we have a ceiling (total_votes_cast), prefer clusters that fit under it
    if ceiling and len(clusters) > 1:
        under = [cl for cl in clusters if max(v for _, v in cl) <= ceiling]
        if under:
            # Among valid clusters, pick most-agreed, then largest value
            best = max(under, key=lambda cl: (len(cl), max(v for _, v in cl)))
            return max(v for _, v in best)

    # Fallback: pick the cluster with most sources
    best = max(clusters, key=lambda cl: (len(cl), max(v for _, v in cl)))
    return max(v for _, v in best)


# ── Suspicious: unmerged pairs that look like they might be the same ────────

SUSPICIOUS_NAME_THRESHOLD = 0.40

def find_suspicious(seat, clusters):
    """
    Find pairs of clusters in the same seat that didn't merge but look similar.
    Criteria (any one is enough):
      - Similar name (>= 0.50)
      - Same party
      - Matching votes
    """
    issues = []
    for i, a in enumerate(clusters):
        for j, b in enumerate(clusters):
            if j <= i:
                continue
            # If any source lists both candidates, they're confirmed different people
            if a["sources"] & b["sources"]:
                continue

            sim = name_similarity(a["name"], b["name"])
            same_party = canon(a["party"]) == canon(b["party"])
            matching_votes = any(
                votes_match(va, vb)
                for va in a["votes"].values() if va > 0
                for vb in b["votes"].values() if vb > 0
            )

            reasons = []
            if sim >= SUSPICIOUS_NAME_THRESHOLD:
                reasons.append(f"similar name (sim={sim:.2f})")
            if same_party:
                reasons.append(f"same party ({canon(a['party'])})")
            if matching_votes:
                reasons.append("matching votes")

            if not reasons:
                continue

            # Skip obvious non-matches: different party + low similarity + no vote match
            if not same_party and sim < SUSPICIOUS_NAME_THRESHOLD and not matching_votes:
                continue

            a_detail = (f"{a['name']} [{','.join(sorted(a['sources']))}] "
                        f"({canon(a['party'])}, "
                        f"{'; '.join(f'{s}={v}' for s,v in sorted(a['votes'].items()))})")
            b_detail = (f"{b['name']} [{','.join(sorted(b['sources']))}] "
                        f"({canon(b['party'])}, "
                        f"{'; '.join(f'{s}={v}' for s,v in sorted(b['votes'].items()))})")

            issues.append({
                "type": "unmerged-suspicious",
                "seat": seat,
                "name_a": a["name"],
                "name_b": b["name"],
                "similarity": f"{sim:.2f}",
                "reason": "; ".join(reasons),
                "detail_a": a_detail,
                "detail_b": b_detail,
                "merged_by": "",
            })

    return issues


# ── Write outputs ────────────────────────────────────────────────────────────

def write_combined(results, path):
    results.sort(key=lambda r: (r["seat_name"], -r["votes"]))
    fields = ["seat_name", "candidate", "party", "votes",
              "num_sources", "sources", "vote_details", "comment"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(results)
    multi = sum(1 for r in results if r["num_sources"] >= 2)
    print(f"\nSaved {len(results)} candidates to {path}")
    print(f"Seats: {len({r['seat_name'] for r in results})}, 2+ sources: {multi}/{len(results)}")


def write_merge_log(merge_log, path):
    if not merge_log:
        return
    fields = ["seat", "rule", "merged_name", "merged_source", "merged_party", "merged_votes",
              "into_name", "into_sources", "into_party", "into_votes", "similarity", "note"]
    merge_log.sort(key=lambda e: (e["seat"], e["rule"]))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(merge_log)
    counts = Counter(e["rule"] for e in merge_log)
    print(f"\nMerge log: {len(merge_log)} merges to {path}")
    for r in sorted(counts):
        print(f"  Rule {r}: {counts[r]}")


def write_suspicious(suspicious, path):
    if not suspicious:
        print("\nNo suspicious unmerged pairs found.")
        return
    suspicious.sort(key=lambda s: (-float(s["similarity"]), s["seat"]))
    fields = ["type", "seat", "name_a", "name_b", "similarity", "reason", "detail_a", "detail_b", "merged_by"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(suspicious)
    print(f"\nSuspicious: {len(suspicious)} unmerged pairs to {path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    entries_by_seat = load_entries_by_seat()
    print(f"\nTotal seats: {len(entries_by_seat)}")

    total_votes_cast = load_total_votes_cast()
    merge_log = []
    results = []
    suspicious = []

    for seat in sorted(entries_by_seat):
        entries = entries_by_seat[seat]

        # Build initial clusters — one per entry
        clusters = []
        for e in entries:
            clusters.append(new_cluster(e["candidate"], e["party"], e["votes"], e["source"]))

        # Apply rules (order matters)
        rule1_name_party(seat, clusters, merge_log)
        rule2_name_votes(seat, clusters, merge_log)
        rule3_fix_japa(seat, clusters, merge_log)

        # Add Rule 3 merges to suspicious (they were merged but worth reviewing)
        for m in merge_log:
            if m["seat"] != seat or m["rule"] != 3:
                continue
            suspicious.append({
                "type": "merged-rule3",
                "seat": seat,
                "name_a": m["merged_name"],
                "name_b": m["into_name"],
                "similarity": m["similarity"],
                "reason": m["note"],
                "detail_a": f"{m['merged_name']} [{m['merged_source']}] ({m['merged_party']})",
                "detail_b": f"{m['into_name']} [{m['into_sources']}] ({m['into_party']})",
                "merged_by": f"rule 3: {m['note']}",
            })

        # Find suspicious unmerged pairs
        suspicious.extend(find_suspicious(seat, clusters))

        # Build result rows — resolve votes with ceiling, then fix sum overflows
        ceiling = total_votes_cast.get(seat)
        seat_results = []
        for cl in clusters:
            votes = resolve_votes(cl["votes"], ceiling=ceiling)
            nonzero = [v for v in cl["votes"].values() if v > 0]
            comment = ""
            if len(nonzero) >= 2:
                spread = (max(nonzero) - min(nonzero)) / max(nonzero)
                if spread > 0.20:
                    comment = f"vote-mismatch: spread={spread:.0%}"
            seat_results.append((cl, votes, comment))

        # If sum of resolved votes exceeds total_votes_cast, re-resolve
        # candidates with vote mismatches: pick the value closest to but not
        # exceeding ceiling, or use median of values under ceiling
        if ceiling:
            total_resolved = sum(v for _, v, _ in seat_results)
            if total_resolved > ceiling:
                new_results = []
                for cl, votes, comment in seat_results:
                    nonzero = sorted([v for v in cl["votes"].values() if v > 0])
                    if len(nonzero) >= 2:
                        spread = (nonzero[-1] - nonzero[0]) / nonzero[-1]
                        if spread > 0.10:
                            # Sum overflows — use most-agreed value, or minimum
                            # if no agreement (conservative: avoids inflated outliers)
                            under = [v for v in nonzero if v <= ceiling]
                            vals_to_pick = under if under else nonzero
                            # Cluster within 5%, pick largest group
                            pick_clusters = []
                            for v in sorted(vals_to_pick):
                                placed = False
                                for pc in pick_clusters:
                                    if pc[0] > 0 and abs(v - pc[0]) / pc[0] <= 0.05:
                                        pc.append(v)
                                        placed = True
                                        break
                                if not placed:
                                    pick_clusters.append([v])
                            best_cl = max(pick_clusters, key=len)
                            if len(best_cl) >= 2:
                                votes = best_cl[len(best_cl) // 2]
                            else:
                                # No agreement — take minimum (conservative)
                                votes = min(vals_to_pick)
                            if not comment:
                                comment = f"vote-mismatch: spread={spread:.0%}"
                    new_results.append((cl, votes, comment))
                seat_results = new_results

        for cl, votes, comment in seat_results:
            results.append({
                "seat_name": seat,
                "candidate": cl["name"],
                "party": canon(cl["party"]),
                "votes": votes,
                "num_sources": len(cl["sources"]),
                "sources": ",".join(sorted(cl["sources"])),
                "vote_details": "; ".join(f"{s}={v}" for s, v in sorted(cl["votes"].items())),
                "comment": comment,
            })

    write_combined(results, os.path.join(PIPE, "combined_candidates.csv"))
    write_merge_log(merge_log, os.path.join(PIPE, "merge_log.csv"))
    write_suspicious(suspicious, os.path.join(PIPE, "suspicious_matches.csv"))


if __name__ == "__main__":
    main()
