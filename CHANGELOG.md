# Changelog

## [Unreleased]
- Docker Hub publishing + tags (`latest`, versioned releases)
- Screenshots workflow commits to PR branches (`[skip ci]`)
- Docker Quick Start + Compose examples in README
- CI fixes: Codecov upload, flake8 config, smoke tests
- Improved README badges (CI, Codecov, Screenshots, Docker)

## 0.4.5 — 2025-09-21
### Added
- Wrapper script (`examples/encryptbin-upload.sh`) documented in README
- Explicit documentation of `/api/paste_encrypted` API
- Security model section re-added to README
- Cleanup process (`encryptbin-cleanup` sidecar) explained in README
- Changelog reference added to README

### Changed
- Condensed code row line spacing in `styles.css` for better readability
- Updated curl examples in README to use correct `/api/paste` endpoint
- Improved examples folder references (GitHub Actions, Ansible, systemd)

### Fixed
- GUI “Failed to create paste” issue (storage API alignment)
- Blank paste view caused by missing edit key handling

## 0.4.4 — 2025-09-21
- GitHub-style Write/Preview tabs with auto-detect + override in Preview
- Accurate hover + row numbers; diff tint on +/-
- Examples, docs, CI, pre-commit included

## 0.4.0 — 2025-09-15
- Initial stable EncryptBin release
- Client-side AES encryption, paste creation + retrieval
- Syntax highlighting with language detection
- Burn-after-read, expiration (1 day, 30 days, never)
- Dark/light theme with auto-detect

## 0.3.x — 2025-09-01
- Basic pasting, syntax highlighting
- Local + optional S3 storage backends
- Docker Compose for testing
- Early examples and docs
