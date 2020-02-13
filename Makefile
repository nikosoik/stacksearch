VENV=${HOME}/.stacksearch
PYTHON=python3
LANG_MODEL=en_core_web_sm

virtual-env:
	$(PYTHON) -m venv $(VENV)

base-deps:
	. $(VENV)/bin/activate && \
	pip install -r requirements.txt

spacy-lang-model:
	$(PYTHON) -m spacy download $(LANG_MODEL)

setup: virtual-env base-deps spacy-lang-model

clean:
	rm -rf $(VENV)
