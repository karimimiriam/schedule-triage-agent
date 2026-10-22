"One run of the agent: read open issues, ask the model, let the hands decide, then act."

import argparse
import logging
import os
import time

import httpx
from google.genai.errors import APIError
from pydantic import ValidationError

from triage.classifier import GeminiClassifier
from triage.github import GitHub
from triage.hands import Outcome, Rules, decide

log = logging.getLogger("triage")


def run(dry_run: bool) -> None:
    rules = Rules()
    github = GitHub(os.environ["GITHUB_TOKEN"], os.environ["GITHUB_REPOSITORY"])
    classifier = GeminiClassifier(os.environ["GEMINI_MODEL"], rules)
    pause = 60 / int(os.environ.get("MODEL_REQUESTS_PER_MINUTE", "5"))
    done = 0

    issues = github.open_issues()
    log.info("found %s open issues", len(issues))
    for position, issue in enumerate(issues):
        if issue.labels & rules.labels.keys():
            log.info("#%s already labelled, no model call needed", issue.number)
            continue
        if position:
            time.sleep(pause)  # stay under the model's rate limit instead of hitting it

        # If the model is down or answers badly, change nothing and move on.
        try:
            request = classifier.suggest(issue)
        except (APIError, httpx.HTTPError, ValidationError) as error:
            log.warning("#%s skipped, model unavailable (%s)", issue.number, type(error).__name__)
            continue

        outcome, reason = decide(
            request, issue=issue.number, labels=issue.labels, done=done, rules=rules
        )
        log.info(
            "#%s %r asked %s %s -> %s (%s)",
            issue.number,
            issue.title,
            request.action,
            request.label,
            outcome,
            reason,
        )
        if outcome is Outcome.DONE:
            if not dry_run:
                github.add_label(issue.number, request.label)
            done += 1

    mode = "would label" if dry_run else "labelled"
    log.info("finished: %s %s issues, model %s", mode, done, classifier.version)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Label new GitHub issues.")
    parser.add_argument("--dry-run", action="store_true", help="show decisions, change nothing")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    run(parser.parse_args().dry_run)
