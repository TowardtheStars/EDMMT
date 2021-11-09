SHELL := powershell.exe

.PHONY: all test clear_db

all:

test:
	python test.py

clear_db:
	rm -r "db"
	