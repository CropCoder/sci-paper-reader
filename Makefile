.PHONY: test check build

test:
	python3 -m unittest discover -s tests -v

check:
	python3 -m compileall -q scripts tests
	node --check templates/en2cn.js
	node --check templates/fig.js
	node --check templates/method.js
	node --check templates/site-nav.js

build:
	@echo "Usage: make build PDF=paper.pdf OUT=paper_解读"
	@test -n "$(PDF)" || (echo "PDF is required" && exit 1)
	@test -n "$(OUT)" || (echo "OUT is required" && exit 1)
	python3 scripts/extract_pdf.py "$(PDF)" -o "$(OUT)"
