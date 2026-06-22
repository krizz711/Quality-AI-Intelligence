# Contributing

## Branch protection (configure in GitHub repo settings)
- Require status checks to pass before merging:
  - "Unit Tests / unit"
  - "Integration Tests / integration"
- Require branches to be up to date before merging
- Do not allow bypassing the above settings

## Branch naming
- phase-N/description  for roadmap phases
- fix/description       for bug fixes
- stabilize/description for stabilization work

## PR checklist
- [ ] Unit tests pass locally: pytest tests/ --ignore=tests/integration
- [ ] Integration tests pass locally: docker compose exec api pytest tests/integration/ -v
- [ ] BATCH_METRICS log lines visible in docker compose logs api
- [ ] No new print() statements (use logger.info/warning/error)
- [ ] Alembic migration included if db/models.py changed
