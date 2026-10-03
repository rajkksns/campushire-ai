"""End-to-end analysis-flow integration test (Task 12.7).

Exercises the complete happy path through the HTTP API against a real
temp-file SQLite database (Requirements 13.1, 13.2, 13.4):

    create profile -> add skills -> submit resume -> run analysis
                    -> retrieve the persisted analysis

The job description and skills are chosen from the curated vocabulary
(``python``, ``docker``, ``kubernetes``) so extraction produces a meaningful,
deterministic result. The test asserts the pipeline wired the kernel correctly
(matched/weak/missing partition, conserved score, ordered roadmap) and that the
persisted analysis reads back identically by id and appears in the profile's
list — i.e. the stored result is authoritative and needs no recomputation.
"""

from __future__ import annotations


def test_full_analysis_flow_persists_and_reads_back(client):
    """A profile's analysis is computed, persisted, and retrievable verbatim."""
    # -- create profile -------------------------------------------------- #
    created = client.post("/profiles", json={"name": "Asha Verma"})
    assert created.status_code == 201, created.text
    profile_id = created.json()["id"]

    # -- add skills ------------------------------------------------------ #
    # Python at proficiency 4 (>= 3 -> MATCHED). Docker at proficiency 1
    # (< 3 -> WEAK). Kubernetes is intentionally absent -> MISSING.
    add_python = client.post(
        f"/profiles/{profile_id}/skills",
        json={"name": "Python", "skill_type": "technical", "proficiency": 4},
    )
    assert add_python.status_code == 201, add_python.text
    add_docker = client.post(
        f"/profiles/{profile_id}/skills",
        json={"name": "Docker", "skill_type": "technical", "proficiency": 1},
    )
    assert add_docker.status_code == 201, add_docker.text

    # -- submit resume (paste) ------------------------------------------- #
    resume = client.put(
        f"/profiles/{profile_id}/resume",
        json={"content": "Built services with Python and Docker in production."},
    )
    assert resume.status_code == 200, resume.text

    # -- run analysis ---------------------------------------------------- #
    jd = (
        "We are hiring a backend engineer. Required: strong Python and Docker. "
        "Kubernetes is required for our platform team."
    )
    run = client.post(f"/profiles/{profile_id}/analyses", json={"job_description": jd})
    assert run.status_code == 201, run.text
    result = run.json()

    analysis_id = result["id"]
    required_names = {item["name"] for item in result["breakdown"]}
    assert {"python", "docker", "kubernetes"}.issubset(required_names)

    # Partition is total and disjoint across matched/weak/missing.
    matched_names = {m["name"] for m in result["matched"]}
    weak_names = {w["name"] for w in result["weak"]}
    missing_names = {m["name"] for m in result["missing"]}
    assert "python" in matched_names
    assert "docker" in weak_names
    assert "kubernetes" in missing_names
    assert matched_names.isdisjoint(weak_names)
    assert matched_names.isdisjoint(missing_names)
    assert weak_names.isdisjoint(missing_names)

    # Score is a conserved integer in [0, 100]: the breakdown points sum to it.
    score = result["readiness_score"]
    assert 0 <= score <= 100
    assert sum(item["points"] for item in result["breakdown"]) == score
    # Python matched + Docker weak + Kubernetes missing -> partial readiness.
    assert 0 < score < 100

    # Roadmap covers only the gaps (weak + missing), excludes matched, and is
    # ranked 1..N by priority (Requirement 12.7).
    roadmap_names = {r["name"] for r in result["roadmap"]}
    assert roadmap_names == {"docker", "kubernetes"}
    assert "python" not in roadmap_names
    ranks = [r["priority_rank"] for r in result["roadmap"]]
    assert ranks == list(range(1, len(ranks) + 1))

    # -- retrieve the persisted analysis by id (13.2) -------------------- #
    fetched = client.get(f"/analyses/{analysis_id}")
    assert fetched.status_code == 200, fetched.text
    # The stored result reads back identically to the run response (no
    # recomputation; the persisted JSON is authoritative, Requirement 13.1).
    assert fetched.json() == result

    # -- list the profile's analyses (13.4) ------------------------------ #
    listed = client.get(f"/profiles/{profile_id}/analyses")
    assert listed.status_code == 200, listed.text
    analyses = listed.json()
    assert len(analyses) == 1
    assert analyses[0]["id"] == analysis_id
    assert analyses[0] == result
