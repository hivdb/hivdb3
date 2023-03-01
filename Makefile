DEPS = $(wildcard hivdb3/*.py hivdb3/*/*.py)
WSDIR = payload/worksheets
TBDIR = payload/tables

SRC_INVITRO_SEL = $(wildcard $(WSDIR)/invitro_selection/*.csv)
TGT_INVITRO_SEL = $(addprefix $(TBDIR)/invitro_selection/,$(notdir $(SRC_INVITRO_SEL)))
$(TBDIR)/invitro_selection/%-ivsel.csv: $(WSDIR)/invitro_selection/%-ivsel.csv $(WSDIR)/isolates/baseline_isolates.csv
	@pipenv run python -m hivdb3.entry generate-invitro-selection $< $@ --baseline-csv $(word 2,$^)
$(TGT_INVITRO_SEL): $(DEPS) 
payload: $(TGT_INVITRO_SEL)

TGT_IVSEL_DRUGS = $(addprefix $(TBDIR)/invitro_selection_drugs/,$(patsubst %-ivsel.csv,%-drugs.csv,$(notdir $(SRC_INVITRO_SEL))))
$(TBDIR)/invitro_selection_drugs/%-drugs.csv: $(WSDIR)/invitro_selection/%-ivsel.csv $(WSDIR)/isolates/baseline_isolates.csv
	@pipenv run python -m hivdb3.entry generate-ivsel-drugs $< $@ --baseline-csv $(word 2,$^)
$(TGT_IVSEL_DRUGS): $(DEPS) 
payload: $(TGT_IVSEL_DRUGS)

TGT_IVSEL_ISO = $(WSDIR)/isolates/invitro_selection_isolates.csv
$(TGT_IVSEL_ISO): $(WSDIR)/isolates/baseline_isolates.csv $(DEPS) $(SRC_INVITRO_SEL)
	@pipenv run python -m hivdb3.entry generate-ivsel-isolates \
		$(WSDIR)/invitro_selection $@ \
		--baseline-csv $< \
		--consensus-csv $(WSDIR)/hiv1_consensus.csv
payload: $(TGT_IVSEL_ISO)

SRC_ISOLATES = $(wildcard $(WSDIR)/isolates/*.csv)
TGT_MUTATIONS = $(addprefix $(TBDIR)/mutations.d/,$(notdir $(SRC_ISOLATES)))
$(TBDIR)/mutations.d/%.csv: $(WSDIR)/isolates/%.csv
	@pipenv run python -m hivdb3.entry generate-mutations $< $@
$(TGT_MUTATIONS): $(DEPS)
payload: $(TGT_MUTATIONS)

SRC_ISOLATES = $(wildcard $(WSDIR)/isolates/*.csv)
TGT_ISOLATES = $(addprefix $(TBDIR)/isolates.d/,$(notdir $(SRC_ISOLATES)))
$(TBDIR)/isolates.d/%.csv: $(WSDIR)/isolates/%.csv
	@pipenv run python -m hivdb3.entry generate-isolates $< $@
$(TGT_ISOLATES): $(DEPS)
payload: $(TGT_ISOLATES)

SRC_ISOLATES = $(wildcard $(WSDIR)/isolates/*.csv)
TGT_GENE_ISOLATES = $(addprefix $(TBDIR)/gene_isolates.d/,$(notdir $(SRC_ISOLATES)))
$(TBDIR)/gene_isolates.d/%.csv: $(WSDIR)/isolates/%.csv
	@pipenv run python -m hivdb3.entry generate-gene-isolates $< $@
$(TGT_GENE_ISOLATES): $(DEPS)
payload: $(TGT_GENE_ISOLATES)

TGT_REFAA = $(TBDIR)/ref_amino_acid.csv
$(TGT_REFAA): $(WSDIR)/hiv1_consensus.csv $(DEPS)
	@pipenv run python -m hivdb3.entry generate-ref-amino-acid $< $@
payload: $(TGT_REFAA)

TGT_DRUGS = $(TBDIR)/drugs.csv
$(TGT_DRUGS): $(DEPS) $(SRC_INVITRO_SEL)
	@pipenv run python -m hivdb3.entry generate-drugs \
		$(WSDIR)/invitro_selection $@
payload: $(TGT_DRUGS)

TGT = $(TGT_INVITRO_SEL) $(TGT_IVSEL_DRUGS) $(TGT_IVSEL_ISO) $(TGT_MUTATIONS) $(TGT_ISOLATES) $(TGT_GENE_ISOLATES) $(TGT_REFAA) $(TGT_DRUGS)

build/sqls: scripts/export-sqls.sh schema.dbml $(wildcard constraints_pre-import/*.sql derived_tables/*.sql constraints_post-import/*.sql $(TBDIR)/*.csv $(TBDIR)/*/*.csv $(TBDIR)/*/*/*.csv) $(TGT)
	@docker run \
		--rm -it \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
		hivdb/hivdb3-builder:latest \
		scripts/export-sqls.sh

requirements.txt: Pipfile Pipfile.lock
	@pipenv lock -r > $@

network:
	@docker network create -d bridge hivdb3-network 2>/dev/null || true

builder: requirements.txt
	@docker build . -t hivdb/hivdb3-builder:latest

docker-envfile:
	@test -f docker-envfile || (echo "Config file 'docker-envfile' not found, use 'docker-envfile.example' as a template to create it." && false)

update-builder:
	#@docker pull hivdb/hivdb3-builder:latest > /dev/null

inspect-builder: update-builder network docker-envfile
	@docker run --rm -it \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
		--volume ~/.aws:/root/.aws:ro \
		--network=hivdb3-network \
		--env-file ./docker-envfile \
   		hivdb/hivdb3-builder:latest /bin/bash

release-builder:
	@docker push hivdb/hivdb3-builder:latest

local-release: update-builder network docker-envfile
	@docker run --rm -it \
		--shm-size=1536m \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
		--volume ~/.aws:/root/.aws:ro \
		--network=hivdb3-network \
		--env-file ./docker-envfile \
   		hivdb/hivdb3-builder:latest \
		scripts/export-sqlite.sh local

release: update-builder network docker-envfile
	@docker run --rm -it \
		--shm-size=1536m \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
		--volume ~/.aws:/root/.aws:ro \
		--network=hivdb3-network \
		--env-file ./docker-envfile \
   		hivdb/hivdb3-builder:latest \
		scripts/github-release.sh

pre-release: update-builder network docker-envfile
	@docker run --rm -it \
		--shm-size=1536m \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
		--volume ~/.aws:/root/.aws:ro \
		--network=hivdb3-network \
		--env-file ./docker-envfile \
   		hivdb/hivdb3-builder:latest \
		scripts/github-release.sh --pre-release

sync-to-s3: update-builder docker-envfile
	@docker run --rm -it \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
		--volume ~/.aws:/root/.aws:ro \
		--env-file ./docker-envfile \
   		hivdb/hivdb3-builder:latest \
		scripts/sync-to-s3.sh

devdb: update-builder network build/sqls
	$(eval volumes = $(shell docker inspect -f '{{ range .Mounts }}{{ .Name }}{{ end }}' hivdb3-devdb))
	@docker rm -f hivdb3-devdb 2>/dev/null || true
	@docker volume rm $(volumes) 2>/dev/null || true
	@docker run \
		-d --name=hivdb3-devdb \
		-e POSTGRES_HOST_AUTH_METHOD=trust \
		-p 127.0.0.1:6547:5432 \
		--volume=$(shell pwd)/postgresql.conf:/etc/postgresql/postgresql.conf \
		--volume=$(shell pwd)/build/sqls:/docker-entrypoint-initdb.d \
		--network=hivdb3-network \
		postgres:13.1 \
		-c 'config_file=/etc/postgresql/postgresql.conf'

log-devdb:
	@docker logs -f hivdb3-devdb

psql-devdb:
	@docker exec -it hivdb3-devdb psql -U postgres

psql-devdb-no-docker:
	@psql -U postgres -h localhost -p 6547

payload/suppl-tables/non_genbank_articles.csv: scripts/find-non-genbank-refs.sh
	@scripts/find-non-genbank-refs.sh "$@"

sync-cpr-urls: update-builder docker-envfile
	@docker run --rm -it \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
		--volume ~/.aws:/root/.aws:ro \
		--env-file ./docker-envfile \
   		hivdb/hivdb3-builder:latest \
		scripts/sync-cpr-urls.sh


.PHONY: autofill devdb *-devdb builder *-builder *-sqlite release pre-release debug-* sync-* update-builder new-study import-*
