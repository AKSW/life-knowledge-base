# Life Knowledge Base

This collection of an ontology and scripts aims to export the data from the 
[Catalogue of life](https://catalogueoflife.org) (COL) into an n-triple format and enrich the information with additional context and thus 
bring value to the project.


### Usage

For setup install the nesseccary python packages through 

```shell
python3 -m pip install -r requirements.txt
```

To download and export the data simply run

```shell
./download_and_parse.sh
```

You'll find the data in `data/parsed.nt`

You can do a test run where only the first _n_ taxons from the COL are parsed with 
```shell
./download_and_parse.sh n
```


### [Ontology](ontology.ttl)
The CoL already uses the semantic web ontology [Darwin Core](https://dwc.tdwg.org) (dwc). Unfortunately the format is very limited in its expressiveness.
This is why we created an extending ontology that aims to infer stronger semantics to the specific data of the CoL while remaining largely interoperabel with other dwc knowledge bases.

### [Parser](col_parser)
The purpose of the parser is to download the most recent version of the CoL (as a zip archive) and use our extending ontology to transfer the information to an .nt-file. 

