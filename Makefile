.PHONY: conda-setup conda-run

conda-setup:
	conda env update -f environment.yml --prune

conda-run:
	conda activate stm32-thermal && python main.py
