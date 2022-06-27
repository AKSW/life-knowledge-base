# Life Knowledge Base

This collection of an ontology and scripts aims to import the data from the 
[Catalogue of life](https://catalogueoflife.org) (CoL) into a queryable 
[virtuoso triple store](https://virtuoso.openlinksw.com), enrich the information with additional context and thus 
bring value to the project.


### Usage

To import the data to a self-hosted instance simply run
```shell
bash update_virtuoso.sh
```

For starting the triple store without updating the data just use `docker-compose up -d`.


### Structure of the Project

The Structure consists of 3 parts:
- ontology
- parser
- update script

#### [Ontology](ontology.ttl)
The CoL already uses the semantic web ontology [Darwin Core](https://dwc.tdwg.org) (dwc), which is why we decided 
against creating an ontology from scratch. Unfortunately the Catalogue uses the format not with its full expressiveness.
This is why we created an extension ontology that aims to infer stronger semantics to the specific data
of the CoL while still maintaining complete interoperability with other dwc knowledge bases.

#### [Parser](col_parser)
The purpose of the parser is to download the most recent version of the CoL (as a zip archive) and use our 
extension ontology to transfer the information to an .nt-file. It uses Python to parse the 
catalogue and can use the [Dockerfile](col_parser/Dockerfile) for encapsulation and CD.

#### [Update Script](update_virtuoso.sh)
The updater first starts the parser to create a current version of the CoL in a rdf format. 
Then it runs an version of virtuoso without port mappings to 
[bulk-import](http://vos.openlinksw.com/owiki/wiki/VOS/VirtBulkRDFLoader) the data to the triple store. 
The script takes about an hour to complete on a standard desktop machine. 
You can limit the number of Taxons to import using
```shell
bash update_virtuoso.sh [limit]
```
