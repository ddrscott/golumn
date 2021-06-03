VERSION=$(shell grep '__version__' golumn/__init__.py | grep -o '\(\d\+\.\)\+\d\+')

version:
	@echo golumn: ${VERSION}

icon:
	img2py -a -F -i -n AppIcon res/grid-128.ico golumn/images.py

dist: dist/golumn-${VERSION}-py3-none-any.whl

dist/golumn-${VERSION}-py3-none-any.whl:
	python setup.py bdist_wheel

publish: dist
	twine upload dist/golumn-${VERSION}-py3-none-any.whl
