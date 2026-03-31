# Release Checklist v0.1.0

## Branch Prep

- Sync `develop` with remote and ensure working tree is clean.
- Create `release/v0.1.0` from `develop`.
- Freeze non-release feature merges until release is complete.

## Test Gates

- Run local quality gate: `python scripts/check_quality.py`.
- Confirm CI quality workflow passes on the release branch.
- Verify no failing tests in the pytest matrix.

## Changelog and Release Notes

- Update changelog entries for v0.1.0.
- Summarize user-facing changes, fixes, and known limitations.
- Validate version references match tag and release notes.

## Tag and Merge Flow

- Merge `develop` into `release/v0.1.0`.
- Apply final release fixes only on `release/v0.1.0`.
- Tag release on `main` as `v0.1.0` after merge.
- Merge `release/v0.1.0` into `main`.
- Back-merge `main` into `develop` to preserve release commits.
