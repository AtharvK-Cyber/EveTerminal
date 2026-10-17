.PHONY: all test install uninstall deb clean

all: test

test:
	python3 -m unittest discover tests

install:
	sudo bash ./install.sh

uninstall:
	sudo bash ./uninstall.sh

deb:
	bash ./package_deb.sh

clean:
	rm -rf build/ dist/ *.egg-info build_deb/ *.deb
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
