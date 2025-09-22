# Contributing to EncryptBin

Thanks for your interest in contributing! 🎉
EncryptBin is a lightweight, secure, self-hosted pastebin — and contributions are welcome.

---

## 🛠 Development Setup

### 1. Clone the repo
```bash
git clone https://github.com/pmalinen/EncryptBin.git
cd EncryptBin
```

### 2. Install dependencies
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### 3. Run locally
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

or with Docker Compose:

```bash
docker compose up --build
```

---

## 🧪 Testing

Run the test suite:

```bash
pytest --cov=. --cov-report=term-missing
```

We enforce a minimum coverage threshold in CI (currently 70%).
All new code should include tests.

---

## 🧹 Pre-commit hooks

This repo uses [pre-commit](https://pre-commit.com/) for linting & formatting.

Install hooks:

```bash
pre-commit install
```

Run on all files:

```bash
pre-commit run --all-files
```

---

## 📸 Screenshots

UI screenshots are auto-generated in GitHub Actions (`screenshots.yml`).
They are committed back to pull request branches with `[skip ci]` to avoid retriggering CI.

---

## 🔐 Security

- Client-side encryption is the default.
- The plaintext API is **disabled by default**.
- If enabled, always use tokens in `API_TOKENS` for automation.

---

## ✅ Pull Requests

- Work in feature branches (never commit directly to `main`).
- Ensure tests & pre-commit checks pass before opening a PR.
- Each PR should focus on a single change or feature.
- Sensitive areas (`app.py`, `storage.py`, workflows) require Code Owner review.

---

## 🙌 Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
Be kind, respectful, and inclusive.

---

## 📝 License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
