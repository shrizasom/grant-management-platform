.PHONY: seed server eval

seed:
	powershell -ExecutionPolicy Bypass -File scripts/seed.ps1

server:
	python -m server.mcp_server

eval:
	python -m evals.run_evals
