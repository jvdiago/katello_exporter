IMAGENAME?=jvela/katello_exporter
TAG?=latest

debug: image
	docker run --rm -p 9118:9118 -e KATELLO_USER=admin -e KATELLO_PASSWORD=changeme -e KATELLO_SERVER=https://katello:4433 -e DEBUG=1 -e VIRTUAL_PORT=9118 -e INSECURE=True $(IMAGENAME):$(TAG)

image:
	docker build -t $(IMAGENAME):$(TAG) .

push: image
	docker push $(IMAGENAME):$(TAG)


.PHONY: image push debug
