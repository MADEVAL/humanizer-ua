.PHONY: test eval validate all

test:
	python -m unittest skills/humanizer-ua/scripts/test_scan.py -v

eval:
	python eval/run_eval.py

validate:
	python scripts/validate_package.py --full

all: test eval validate
