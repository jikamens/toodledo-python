build: check-secrets
	poetry build

lint: check-secrets
	poetry run pylint *.py tests toodledo
	poetry run flake8

test: check-secrets test-secrets.sh test-token.json
	. ./test-secrets.sh; poetry run pytest $(PYTEST_ARGS)

# N.B. Before you do this you need to do
# `poetry config pypi.token.pypi <token>`
publish:
	poetry publish

clean: ; -rm -rf dist

test-secrets.sh:
	@echo "Please create test-secrets.sh from test-secrets.sh.template" 1>&2
	@false

test-token.json: test-secrets.sh
	. ./test-secrets.sh; poetry run python generate-credentials.py

check-secrets: check-pre-commit-hook
	@./git-pre-commit

check-pre-commit-hook: git-pre-commit
	@if ! cmp -s git-pre-commit .git/hooks/pre-commit; then \
	    echo "Install git-pre-commit as .git/hooks/pre-commit" 1>&2; \
	    exit 1; \
	fi
