import scripts.generate_manifest as generate_manifest


def test_iter_files_matches_direct_children_for_recursive_globs(monkeypatch):
    monkeypatch.setattr(generate_manifest, "INCLUDE_GLOBS", ["docs/**/*.md"])
    monkeypatch.setattr(
        generate_manifest,
        "_git_ls_files",
        lambda: [
            "docs/DETERMINISM_CONTRACT.md",
            "docs/nested/file.md",
            "docs/notes.txt",
        ],
    )

    assert generate_manifest._iter_files() == [
        "docs/DETERMINISM_CONTRACT.md",
        "docs/nested/file.md",
    ]


def test_iter_files_uses_tracked_paths_for_case_collisions(monkeypatch):
    monkeypatch.setattr(generate_manifest, "INCLUDE_GLOBS", ["docs/**/*.md"])
    monkeypatch.setattr(
        generate_manifest,
        "_git_ls_files",
        lambda: [
            "MANIFEST.sha256",
            "docs/DETERMINISM_CONTRACT.md",
            "docs/determinism_contract.md",
        ],
    )

    assert generate_manifest._iter_files() == [
        "docs/DETERMINISM_CONTRACT.md",
        "docs/determinism_contract.md",
    ]
