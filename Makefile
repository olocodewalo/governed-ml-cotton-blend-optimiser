# Cotton Blend Optimisation -- task runner
# Windows users without `make`: run `make.bat <target>` or the raw python commands below.

PY ?= python

.PHONY: help setup data train optimise app eval eval-baseline feedback clean

help:
	@echo "targets:"
	@echo "  setup      - pip install -r requirements.txt"
	@echo "  data       - generate synthetic bales + historical laydowns (data/*.parquet)"
	@echo "  train      - train ML quality model, write registry + SHAP chart"
	@echo "  optimise   - run LP + GA optimisers on a demo scenario, print blends"
	@echo "  app        - launch Streamlit HITL review UI"
	@echo "  eval       - run golden-set harness + regression suite"
	@echo "  eval-baseline - (re)freeze eval/baseline.json from current metrics"
	@echo "  feedback   - fold 20 simulated master corrections into training, show delta"

setup:
	$(PY) -m pip install -r requirements.txt

data:
	$(PY) -m data.generate

train:
	$(PY) -m models.train

optimise:
	$(PY) -m optimiser.run_demo

app:
	$(PY) -m streamlit run app/streamlit_app.py

eval:
	$(PY) -m eval.run_golden
	$(PY) -m eval.regression_suite

eval-baseline:
	$(PY) -m eval.run_golden --freeze-baseline

feedback:
	$(PY) -m eval.feedback_retrain

clean:
	$(PY) -c "import shutil,glob,os; [shutil.rmtree(p,ignore_errors=True) for p in ['artifacts','mlruns','__pycache__']]; [os.remove(f) for f in glob.glob('data/*.parquet')]"
