# Python regression CI

`.github/workflows/python-tests.yml` runs the complete pytest collection on every PR
(including drafts), pushes to main, and manual dispatch. No path filter is used, so
changes in research code, shared code, configuration, fixtures, or test dependencies
cannot silently miss this workflow. The existing web evidence workflow is unchanged.

The job uses Python 3.12 and CPU PyTorch. `requirements-ci.txt` pins the direct test
dependencies; transitive versions are recorded with `pip freeze` in the uploaded
artifact. This is not a full dependency lock. Reproduce in a fresh virtual environment:

```bash
python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-ci.txt
python -m pip check
MPLBACKEND=Agg PYTHONHASHSEED=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest -q
```

Tests create their own temporary fixtures/checkpoints. The job does not download
an official checkpoint or private Drive data, train an operational model, rerun the
full official evaluation, merge a PR, or deploy a site. Small training steps inside
existing unit tests remain part of the test suite.

The job has a 20-minute timeout and cancels older runs for the same PR/ref. Pytest
failures propagate through `tee` using `pipefail`. JUnit XML, the pytest log and the
environment listing are uploaded for 14 days, including when tests fail. Installation
failures remain in Actions step logs; there may be no artifact if installation failed.

A green check only establishes that the collected tests passed in that environment.
Counterexample review and private-model functional verification remain separate.
On 2026-10-07, repository ruleset `main-python-ci` (ID `24645588`) was enabled
for the default branch (`main`). It requires `pytest (Python 3.12, CPU)` from
GitHub Actions, with no bypass actors. Requiring the branch to be up to date is
not enabled. No additional review-count, deployment or automatic merge rule was added.
The workflow file and this repository setting are separate; renaming the job requires
updating the required-check setting too. [Follow-up record](../audits/remaining_work_20261007.md).

## Review and integration

Record the exact base/head SHA, reviewed diff, executed commands and unverified scope.
Separate author-reported results, independent reviewer execution and hosted CI.
A reviewer should receive the diff and acceptance criteria in a fresh context and
report reproducible defects without treating the author's passing tests as approval.
After fixes, recheck the new head. Before merging, verify the reviewed SHA, current
main integration and CI; merge only within the user's authorization. Never publish
private checkpoints, raw evaluation data or private storage links in review comments.

This workflow supplies machine checks. Claude/Jules review and Codex independent
validation are separate tasks; automatic AI review is not configured by this workflow.
