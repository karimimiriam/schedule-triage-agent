# schedule-triage-agent

A scheduled AI agent that labels new GitHub issues as `bug`, `question` or `idea`.
The model can only suggest. A small, strict checker decides what actually happens.

## How it works

A Kubernetes CronJob starts the agent every weekday at 06:00 (Africa/Nairobi). Each run:

1. Reads open issues from GitHub.
2. Skips issues that already have one of the three labels, without calling the model.
3. Asks the model which label fits. This is the only step that uses AI.
4. Checks the request against hard rules (`triage/hands.py`).
5. Adds the label only if every rule passes.
6. Logs every decision and the model version that answered.

## Safety

- **Rules live in code, not in the prompt.** Only `add_label` is allowed, only on the issue being processed, only with an allowed label, at most 5 per run. Anything else is refused.
- **Fails closed.** If the model is slow, down, rate limited or answers in the wrong shape, the issue is skipped and nothing changes. The next scheduled run tries again.
- **Least privilege.** The GitHub token can reach this repository only, with issue access and no access to code. The pod gets no Kubernetes API token.
- **Hardened container.** Pinned base images by digest, locked dependencies, non-root user, read-only filesystem, no Linux capabilities, no privilege escalation, `restricted` Pod Security in its namespace.
- **Secrets stay out of Git and the image.** Keys live in a local `.env` (ignored) and a Kubernetes Secret.

## Run it locally

```bash
cp .env.example .env        # then fill in your own keys
uv sync
uv run pytest
uv run --env-file .env python -m triage --dry-run
```

`--dry-run` shows every decision without changing anything on GitHub.

## Deploy to a local cluster (kind)

```bash
kind create cluster --config deploy/kind-config.yaml
docker build -t schedule-triage-agent:0.1.2 .
kind load docker-image schedule-triage-agent:0.1.2 --name codesafi
kubectl apply -f deploy/namespace.yaml
kubectl create secret generic triage-keys --namespace triage \
  --from-env-file=<(grep -E '^(GITHUB_TOKEN|GEMINI_API_KEY)=' .env)
kubectl apply -f deploy/cronjob.yaml
```

Run it now instead of waiting for the schedule:

```bash
kubectl create job --from=cronjob/schedule-triage-agent manual-run --namespace triage
kubectl logs --follow job/manual-run --namespace triage
```

## Configuration

| Variable | Purpose |
|---|---|
| `GITHUB_TOKEN` | Fine-grained token: this repository only, Issues read/write |
| `GEMINI_API_KEY` | Key for the model |
| `GITHUB_REPOSITORY` | `owner/name` of the repository to triage |
| `GEMINI_MODEL` | Model name, pinned to a fixed version |
| `MODEL_REQUESTS_PER_MINUTE` | Paces model calls to stay under the rate limit (default 5) |

## Known limits

- The checker guarantees an action is safe, not that the label is right.
- The free model tier is rate limited per minute and per day, and is often slow. Skipped issues are retried on the next run.
- GitHub's issues API occasionally returned an empty list during testing. The agent logs the count each run and simply does nothing when it finds no issues.
- Kubernetes Secrets are encoded, not encrypted. Use encryption at rest or a vault in production.
- Next steps: a GitHub App instead of a personal token, a NetworkPolicy, image scanning, and a test for the full run.
