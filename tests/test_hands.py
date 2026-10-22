"One test for every rule the hands enforce."

from triage.hands import Outcome, Request, Rules, decide

RULES = Rules()
NO_LABELS: frozenset[str] = frozenset()


def outcome(request: Request, labels: frozenset[str] = NO_LABELS, done: int = 0) -> Outcome:
    return decide(request, issue=request.issue, labels=labels, done=done, rules=RULES)[0]


def test_allowed_label_is_done():
    assert outcome(Request(issue=2, action="add_label", label="bug")) == Outcome.DONE


def test_tricked_brain_cannot_delete_branches():
    assert outcome(Request(issue=5, action="delete_branch")) == Outcome.REFUSED


def test_tricked_brain_cannot_close_issues():
    assert outcome(Request(issue=5, action="close_issue")) == Outcome.REFUSED


def test_label_outside_the_list_is_refused():
    request = Request(issue=4, action="add_label", label="enhancement")
    assert outcome(request) == Outcome.REFUSED


def test_request_for_another_issue_is_refused():
    request = Request(issue=2, action="add_label", label="bug")
    result = decide(request, issue=5, labels=NO_LABELS, done=0, rules=RULES)
    assert result[0] == Outcome.REFUSED


def test_already_labelled_issue_is_left_alone():
    request = Request(issue=2, action="add_label", label="bug")
    assert outcome(request, labels=frozenset({"bug"})) == Outcome.ALREADY_DONE


def test_limit_per_run_is_enforced():
    request = Request(issue=3, action="add_label", label="question")
    assert outcome(request, done=5) == Outcome.SKIPPED
