.PHONY: all check test eval validate

test:
	python -m unittest skills/humanizer-ua/scripts/test_scan.py skills/humanizer-ua/scripts/test_rules.py -v

eval:
	python eval/run_eval.py

validate:
	python scripts/validate_package.py

check:
	python scripts/validate_package.py --full

all: check
