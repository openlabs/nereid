.PHONY: clean-pyc test upload-docs docs

all: clean-pyc test

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

upload-docs:
	$(MAKE) -C docs html dirhtml epub
	cd docs/_build/; mv html nereid-docs; zip -r nereid-docs.zip nereid-docs; mv nereid-docs html
	scp -r docs/_build/dirhtml/* openlabs.co.in:/var/www/nereid.openlabs.co.in/docs/
	scp docs/_build/nereid-docs.zip openlabs.co.in:/var/www/nereid.openlabs.co.in/docs/nereid-docs.zip
	scp docs/_build/epub/Nereid.epub openlabs.co.in:/var/www/nereid.openlabs.co.in/docs/nereid-docs.epub

docs:
	$(MAKE) -C docs html
