# Cotton Blend Optimisation -- task runner
# Windows users without `make`: run `make.bat <target>` or the raw python commands below.

PY ?= python
APPROVER ?=

.PHONY: help setup setup-optional data train eval promote optimise app monitor feedback test ci clean

help:
	@echo "targets:"
	@echo "  setup      - pip install -r requirements.txt (core)"
	@echo "  setup-optional - sentence-transformers retriever + MLflow tracking"
	@echo "  data       - generate synthetic bales + historical laydowns (data/*.parquet)"
	@echo "  train      - train ML quality model -> registered as a CANDIDATE"
	@echo "  eval       - golden-set harness + policy thresholds + regression suite"
	@echo "  promote    - APPROVER=\"name\": gate + approve the candidate, move current pointer, freeze baseline"
	@echo "  optimise   - run LP + GA optimisers on a demo scenario (approved model)"
	@echo "  app        - launch Streamlit HITL review UI (approved model)"
	@echo "  monitor    - drift (PSI) + rolling-MAE + retrain-trigger check"
	@echo "  feedback   - fold 20 simulated master corrections into training, show delta"
	@echo "  test       - pytest"
	@echo "  ci         - what CI runs: data, train, eval (regression gate), test"

setup:
	$(PY) -m pip install -r requirements.txt

setup-optional:
	$(PY) -m pip install -r requirements-optional.txt

data:
	$(PY) -m data.generate

train:
	$(PY) -m models.train

eval:
	$(PY) -m eval.run_golden
	$(PY) -m eval.regression_suite

promote:
	@test -n "$(APPROVER)" || (echo 'usage: make promote APPROVER="<name>"' && exit 2)
	$(PY) -m models.promote --approver "$(APPROVER)"

optimise:
	$(PY) -m optimiser.run_demo

app:
	$(PY) -m streamlit run app/streamlit_app.py

monitor:
	$(PY) -m eval.monitor

feedback:
	$(PY) -m eval.feedback_retrain

test:
	$(PY) -m pytest -q

ci: data train eval test

clean:
	$(PY) -c "import shutil,glob,os; [shutil.rmtree(p,ignore_errors=True) for p in ['artifacts','mlruns','__pycache__']]; [os.remove(f) for f in glob.glob('data/*.parquet')]"
