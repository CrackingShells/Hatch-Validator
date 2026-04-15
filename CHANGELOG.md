## <small>0.9.1 (2026-04-15)</small>

* Merge pull request #21 from CrackingShells/dev ([fdff30e](https://github.com/CrackingShells/Hatch-Validator/commit/fdff30e)), closes [#21](https://github.com/CrackingShells/Hatch-Validator/issues/21)
* chore(release): 0.9.1-dev.1 ([fbd38c6](https://github.com/CrackingShells/Hatch-Validator/commit/fbd38c6))
* fix(validator): decouple validate_package from hatch_metadata.json ([fdfb0f9](https://github.com/CrackingShells/Hatch-Validator/commit/fdfb0f9))

## <small>0.9.1-dev.1 (2026-04-15)</small>

* fix(validator): decouple validate_package from hatch_metadata.json ([fdfb0f9](https://github.com/CrackingShells/Hatch-Validator/commit/fdfb0f9))

## 0.9.0 (2026-04-15)

* Merge pull request #20 from HartreeY/feat/schema-v2.0.0-extension ([9c1b618](https://github.com/CrackingShells/Hatch-Validator/commit/9c1b618)), closes [#20](https://github.com/CrackingShells/Hatch-Validator/issues/20)
* fix(test): use get_field("author") matching accessor convention ([c4f6f81](https://github.com/CrackingShells/Hatch-Validator/commit/c4f6f81))
* test(schema-v200): drop tautological tests, keep 3 behavioral ([88767e8](https://github.com/CrackingShells/Hatch-Validator/commit/88767e8))
* refactor(schema-v200): delegate non-docker deps to v1.2.2 ([8255279](https://github.com/CrackingShells/Hatch-Validator/commit/8255279))
* refactor(schema-v200): delegate tools and entry-point to chain ([1509b51](https://github.com/CrackingShells/Hatch-Validator/commit/1509b51))
* refactor(schema-v200): drop citations and provenance strategies ([f5f4fb1](https://github.com/CrackingShells/Hatch-Validator/commit/f5f4fb1))
* refactor(schema-v200): own docker dep validation exclusively ([113c578](https://github.com/CrackingShells/Hatch-Validator/commit/113c578))
* refactor(schema-v200): remove citations and provenance dead code ([5b5d728](https://github.com/CrackingShells/Hatch-Validator/commit/5b5d728))
* refactor(schema-v200): remove over-owned strategies from validator ([150a1ad](https://github.com/CrackingShells/Hatch-Validator/commit/150a1ad))
* feat(schema): add v2.0.0 schema with citations and provenance ([52a0d78](https://github.com/CrackingShells/Hatch-Validator/commit/52a0d78))

## 0.8.0 (2025-12-04)

* Merge pull request #16 from CrackingShells/dev ([c5c57ce](https://github.com/CrackingShells/Hatch-Validator/commit/c5c57ce)), closes [#16](https://github.com/CrackingShells/Hatch-Validator/issues/16)
* Merge pull request #17 from CrackingShells/feature/v1-2-2-conda-support ([d9f9c3d](https://github.com/CrackingShells/Hatch-Validator/commit/d9f9c3d)), closes [#17](https://github.com/CrackingShells/Hatch-Validator/issues/17)
* Merge pull request #18 from CrackingShells/dev ([91e9c76](https://github.com/CrackingShells/Hatch-Validator/commit/91e9c76)), closes [#18](https://github.com/CrackingShells/Hatch-Validator/issues/18)
* chore: add submodule `cracking-shells-playbook` ([3e7df1e](https://github.com/CrackingShells/Hatch-Validator/commit/3e7df1e))
* chore: npm-audit-fix ([8752d47](https://github.com/CrackingShells/Hatch-Validator/commit/8752d47))
* chore(release): 0.8.0-dev.1 [skip ci] ([a631656](https://github.com/CrackingShells/Hatch-Validator/commit/a631656))
* chore(release): 0.8.0-dev.2 ([ca4f5aa](https://github.com/CrackingShells/Hatch-Validator/commit/ca4f5aa))
* fix(accessor): correct v1.2.1 entry point return type ([f90d251](https://github.com/CrackingShells/Hatch-Validator/commit/f90d251))
* fix(ci): wrong location of npm package in `.releaserc.sjon` ([0a1d5bd](https://github.com/CrackingShells/Hatch-Validator/commit/0a1d5bd))
* ci: add automated PyPI publishing ([82b7316](https://github.com/CrackingShells/Hatch-Validator/commit/82b7316))
* ci: migrate to semantic-release ([f05f0cc](https://github.com/CrackingShells/Hatch-Validator/commit/f05f0cc))
* test(v1.2.2): add comprehensive test coverage for conda support ([6cfddf1](https://github.com/CrackingShells/Hatch-Validator/commit/6cfddf1))
* feat(core): add base accessor method for conda channel support ([e69711b](https://github.com/CrackingShells/Hatch-Validator/commit/e69711b))
* feat(factory): register v1.2.2 accessor and validator ([bf73160](https://github.com/CrackingShells/Hatch-Validator/commit/bf73160))
* feat(schema): implement v1.2.2 package schema with conda support ([4e2be30](https://github.com/CrackingShells/Hatch-Validator/commit/4e2be30))
* feat(service): add conda channel retrieval to PackageService ([d129b65](https://github.com/CrackingShells/Hatch-Validator/commit/d129b65))
* docs: diagrams ([7d0f98a](https://github.com/CrackingShells/Hatch-Validator/commit/7d0f98a))
* docs: first pass on whole package docs ([02b37f3](https://github.com/CrackingShells/Hatch-Validator/commit/02b37f3))

## 0.8.0-dev.2 (2025-12-04)

* fix(ci): wrong location of npm package in `.releaserc.sjon` ([0a1d5bd](https://github.com/CrackingShells/Hatch-Validator/commit/0a1d5bd))
* chore: npm-audit-fix ([8752d47](https://github.com/CrackingShells/Hatch-Validator/commit/8752d47))
* ci: add automated PyPI publishing ([82b7316](https://github.com/CrackingShells/Hatch-Validator/commit/82b7316))

## [0.8.0-dev.1](https://github.com/CrackingShells/Hatch-Validator/compare/v0.7.1...v0.8.0-dev.1) (2025-11-04)


### Features

* **core:** add base accessor method for conda channel support ([e69711b](https://github.com/CrackingShells/Hatch-Validator/commit/e69711b718acc08cb8803e336ed8877903d303f5))
* **factory:** register v1.2.2 accessor and validator ([bf73160](https://github.com/CrackingShells/Hatch-Validator/commit/bf73160371a76db8289500783b45c4eb0d9c75b1))
* **schema:** implement v1.2.2 package schema with conda support ([4e2be30](https://github.com/CrackingShells/Hatch-Validator/commit/4e2be30ae20ea4fe81758b45338137292d07f8e0))
* **service:** add conda channel retrieval to PackageService ([d129b65](https://github.com/CrackingShells/Hatch-Validator/commit/d129b6545c1508ea55b539df2fa1e6c6aff02381))


### Bug Fixes

* **accessor:** correct v1.2.1 entry point return type ([f90d251](https://github.com/CrackingShells/Hatch-Validator/commit/f90d25154735d40fca64e87f0ec3060e99519bcf))


### Documentation

* diagrams ([7d0f98a](https://github.com/CrackingShells/Hatch-Validator/commit/7d0f98a088c237f7cfd9d3eef5e4e16237ca1d97))
* first pass on whole package docs ([02b37f3](https://github.com/CrackingShells/Hatch-Validator/commit/02b37f357826cd476a947c117f16a1c42499f6e9))
