DEPS = $(wildcard hivdb3/*.py) $(wildcard hivdb3/*/*.py)
SRC_INVITRO_SEL = $(wildcard payload/worksheets/invitro_selection/*.csv)
TGT_INVITRO_SEL = $(addprefix payload/tables/invitro_selection/,$(notdir $(SRC_INVITRO_SEL)))

payload/tables/invitro_selection/%-ivsel.csv: payload/worksheets/invitro_selection/%-ivsel.csv
	@pipenv run python -m hivdb3.entry generate-invitro-selection $< $@

$(TGT_INVITRO_SEL): $(DEPS) 

payload: $(TGT_INVITRO_SEL)

builder:
	@docker build . -t hivdb/hivdb3-builder:latest

docker-envfile:
	@test -f docker-envfile || (echo "Config file 'docker-envfile' not found, use 'docker-envfile.example' as a template to create it." && false)

update-builder:
	@docker pull hivdb/hivdb3-builder:latest > /dev/null

inspect-builder: docker-envfile
	@docker run --rm -it \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
		--volume ~/.aws:/root/.aws:ro \
		--env-file ./docker-envfile \
   		hivdb/hivdb3-builder:latest /bin/bash

release-builder:
	@docker push hivdb/hivdb3-builder:latest

autofill: update-builder
	@docker run --rm -it \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
   		hivdb/hivdb3-builder:latest \
		pipenv run python -m drdb.entry autofill-payload payload/

local-release: update-builder docker-envfile
	@docker run --rm -it \
		--shm-size=1536m \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
		--volume ~/.aws:/root/.aws:ro \
		--env-file ./docker-envfile \
   		hivdb/hivdb3-builder:latest \
		scripts/export-sqlite.sh local

release: update-builder docker-envfile
	@docker run --rm -it \
		--shm-size=1536m \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
		--volume ~/.aws:/root/.aws:ro \
		--env-file ./docker-envfile \
   		hivdb/hivdb3-builder:latest \
		scripts/github-release.sh

pre-release: update-builder docker-envfile
	@docker run --rm -it \
		--shm-size=1536m \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
		--volume ~/.aws:/root/.aws:ro \
		--env-file ./docker-envfile \
   		hivdb/hivdb3-builder:latest \
		scripts/github-release.sh --pre-release

reflist ?= ""
import-from-hivdb: update-builder docker-envfile
	@docker run --rm -it \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
		--env-file ./docker-envfile \
   		hivdb/hivdb3-builder:latest \
		scripts/import-from-hivdb.sh ${reflist}

sync-from-cpr: update-builder
	@docker run --rm -it \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
   		hivdb/hivdb3-builder:latest \
		scripts/sync-from-cpr.sh

sync-surv-mutations: update-builder
	@docker run --rm -it \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
   		hivdb/hivdb3-builder:latest \
		scripts/sync-surv-mutations.sh

sync-to-s3: update-builder docker-envfile
	@docker run --rm -it \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
		--volume ~/.aws:/root/.aws:ro \
		--env-file ./docker-envfile \
   		hivdb/hivdb3-builder:latest \
		scripts/sync-to-s3.sh

devdb: update-builder
	@docker run \
		--rm -it \
		--volume=$(shell pwd):/hivdb3/ \
		--volume=$(shell dirname $$(pwd))/hivdb3-payload:/hivdb3-payload \
		hivdb/hivdb3-builder:latest \
		scripts/export-sqls.sh
	$(eval volumes = $(shell docker inspect -f '{{ range .Mounts }}{{ .Name }}{{ end }}' hivdb3-devdb))
	@mkdir -p local/sqls
	@docker rm -f hivdb3-devdb 2>/dev/null || true
	@docker volume rm $(volumes) 2>/dev/null || true
	@docker run \
		-d --name=hivdb3-devdb \
		-e POSTGRES_HOST_AUTH_METHOD=trust \
		-p 127.0.0.1:6547:5432 \
		--volume=$(shell pwd)/postgresql.conf:/etc/postgresql/postgresql.conf \
		--volume=$(shell pwd)/local/sqls:/docker-entrypoint-initdb.d \
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
