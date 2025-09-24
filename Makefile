.PHONY: release help

help:
	@echo "Available targets:"
	@echo "  make release <version>   Create and push a git tag (e.g. make release 0.4.7)"

release:
	@if [ -z "$(word 2,$(MAKECMDGOALS))" ]; then \
		echo "Usage: make release <version>"; \
		exit 1; \
	fi
	@version=$(word 2,$(MAKECMDGOALS)); \
	echo "Tagging version $$version..."; \
	git tag -a v$$version -m "Release $$version"; \
	git push origin v$$version

# Allow "make release 0.4.7" without erroring on unknown target "0.4.7"
%:
	@:
