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
Branch protection / required checks are repository settings and are not changed by
this workflow. Enable a required check only after its first successful hosted run;
the job name is `pytest (Python 3.12, CPU)`.
