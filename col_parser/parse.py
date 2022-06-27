import csv
import sys

from tqdm import tqdm
from dwca.read import DwCAReader
from rdflib import Namespace, URIRef, Graph, Literal
from rdflib.namespace import RDF, RDFS

if len(sys.argv) < 2:
    print("Please give input file as an argument")
    exit(1)

# If positiv second arg was given, use it as N_taxons (max number to parse)s
if len(sys.argv) > 2 and int(sys.argv[2]) > 0:
    N_taxons = int(sys.argv[2])
else:
    N_taxons = 0

dwc = Namespace("http://rs.tdwg.org/dwc/terms/")
htwk_col = Namespace("http://col.htwk-leipzig.de/")
htwk_col_ontology = Namespace("http://ontology.col.htwk-leipzig.de/")

csv.field_size_limit(sys.maxsize)  # Needed for iteration of col-data
with DwCAReader(path=sys.argv[1]) as dwca:
    for count, crow in tqdm(enumerate(dwca), total=N_taxons, unit=" Taxons", smoothing=0):
        g = Graph()

        core_data = crow.data
        entity = URIRef(htwk_col[crow.id])
        g.add((entity, RDF.type, dwc.Taxon))
        g.add((entity, RDFS.label, Literal(crow.id)))

        # Core rows
        for key, value in core_data.items():
            if key == dwc.taxonID.__str__() or value == '':
                continue
            elif key == 'http://rs.tdwg.org/dwc/terms/taxonRank':
                if value.capitalize() in ("Unranked", "Kingdom", "Phylum", "Class", "Subclass",
                                          "Order", "Suborder", "Family", "Genus", "Species",):
                    rank = URIRef(htwk_col_ontology[value.capitalize()])
                    g.add((entity, RDF.type, rank))
                    g.add((entity, dwc.taxonRank, rank))
                else:
                    g.add((entity, RDF.type, htwk_col_ontology.Other))
                    g.add((entity, dwc.taxonRank, htwk_col_ontology.Other))
                    g.add((entity, dwc.taxonRank, Literal(value)))
            elif key == 'http://rs.tdwg.org/dwc/terms/parentNameUsageID':
                g.add((entity, htwk_col_ontology.parent, URIRef(htwk_col[value])))
            elif key == 'http://rs.tdwg.org/dwc/terms/acceptedNameUsageID':
                g.add((entity, dwc.acceptedNameUsage, URIRef(htwk_col[value])))
            elif key == 'http://rs.tdwg.org/dwc/terms/originalNameUsageID':
                g.add((entity, dwc.originalNameUsage, URIRef(htwk_col[value])))
            elif key == 'http://rs.tdwg.org/dwc/terms/scientificNameID':
                g.add((entity, dwc.scientificName, URIRef(htwk_col[value])))
            elif key == 'http://purl.org/dc/terms/references':
                g.add((entity, URIRef('http://purl.org/dc/terms/references'), URIRef(value)))
            else:
                g.add((entity, URIRef(key), Literal(value)))

        # Extension rows
        for extension_line in crow.extensions:
            if extension_line.rowtype == "http://rs.gbif.org/terms/1.0/VernacularName":
                g.add((entity, dwc.vernacularName,
                       Literal(extension_line.data[dwc.vernacularName.__str__()],
                               lang=extension_line.data["http://purl.org/dc/terms/language"])
                       ))

            elif extension_line.rowtype == "http://rs.gbif.org/terms/1.0/Distribution":
                # The dwc-extension Distribution can't be parsed to normal triples due to it's structure. To
                # retain all information from the archive meta statements would be needed. I decided against using
                # this technique and instead introduced two new properties, occurs and occursID, with their
                # respective subproperties to capture the information from dwc.locality/dwc.locationID and the
                # dwc.occurrenceStatus.

                data = extension_line.data
                occurrence_status = data['http://rs.tdwg.org/dwc/terms/occurrenceStatus']
                locality = data['http://rs.tdwg.org/dwc/terms/locality']
                locationID = data['http://rs.tdwg.org/dwc/terms/locationID']

                if locality != '':
                    occurrence_status = data['http://rs.tdwg.org/dwc/terms/occurrenceStatus']
                    if occurrence_status == 'uncertain' or occurrence_status == '':
                        g.add((entity,
                               htwk_col_ontology.occurs,
                               Literal(locality)))
                    elif occurrence_status == 'native':
                        g.add((entity,
                               htwk_col_ontology.occursNatively,
                               Literal(locality)))
                    elif occurrence_status == 'domesticated':
                        g.add((entity,
                               htwk_col_ontology.occursDomesticated,
                               Literal(locality)))
                    elif occurrence_status == 'alien':
                        g.add((entity,
                               htwk_col_ontology.occursAlien,
                               Literal(locality)))
                    else:
                        print(f"Distribution unknown: {occurrence_status}!")

                if locationID != '':
                    if occurrence_status == 'uncertain' or occurrence_status == '':
                        g.add((entity,
                               htwk_col_ontology.occursID,
                               Literal(locationID)))
                    elif occurrence_status == 'native':
                        g.add((entity,
                               htwk_col_ontology.occursIDNatively,
                               Literal(locationID)))
                    elif occurrence_status == 'domesticated':
                        g.add((entity,
                               htwk_col_ontology.occursIDDomesticated,
                               Literal(locationID)))
                    elif occurrence_status == 'alien':
                        g.add((entity,
                               htwk_col_ontology.occursIDAlien,
                               Literal(locationID)))
                    else:
                        print(f"Distribution unknown: {occurrence_status}!")

            elif extension_line.rowtype == "http://rs.gbif.org/terms/1.0/SpeciesProfile":
                for key, value in extension_line.data.items():
                    if key != dwc.taxonID.__str__() and value != '':
                        g.add((entity, URIRef(key), Literal(value)))

        g.serialize(sys.stdout.buffer, format='nt', encoding='utf-8')

        if N_taxons != 0 and count >= N_taxons:
            break
