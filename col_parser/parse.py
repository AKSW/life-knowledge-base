import csv
import sys

from tqdm import tqdm
from dwca.read import DwCAReader
from rdflib import Namespace, URIRef, Graph, Literal, XSD
from rdflib.namespace import RDF, RDFS

if len(sys.argv) < 2:
    print("Please give the input file as an argument")
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

        # Create base entity with COL ID as URI and label
        entity = URIRef(htwk_col[crow.id])
        g.add((entity, RDF.type, dwc.Taxon))
        g.add((entity, RDFS.label, Literal(crow.id)))

        # Parse core rows
        for key, value in crow.data.items():
            if value != '':
                match key:
                    # dwc.taxonID -> dropped
                    case "http://rs.tdwg.org/dwc/terms/taxonID":
                        continue
                    # dwc.parentNameUsageID -> col.parent
                    case "http://rs.tdwg.org/dwc/terms/parentNameUsageID":
                        g.add((entity, htwk_col_ontology.parent, URIRef(htwk_col[value])))
                    # dwc.datasetID -> inherited with datatype
                    case "http://rs.tdwg.org/dwc/terms/datasetID":
                        g.add((entity, URIRef(key), Literal(value, datatype=XSD.integer)))
                    case "http://rs.tdwg.org/dwc/terms/scientificNameID":
                        # TODO
                        pass
                    # dwc.taxonRank -> entity a onto.<Rank>, inherited
                    case "http://rs.tdwg.org/dwc/terms/taxonRank":
                        g.add((entity, dwc.taxonRank, Literal(value)))  # inherit
                        match value.capitalize():
                            case "Unranked" | "Kingdom" | "Phylum" | "Class" | "Subclass" | \
                                 "Order" | "Suborder" | "Family" | "Genus" | "Species" as rank:
                                g.add((entity, RDF.type, htwk_col_ontology[rank]))
                            case _:
                                g.add((entity, RDF.type, htwk_col_ontology.Other))
                    case "http://rs.tdwg.org/dwc/terms/scientificName":
                        # TODO
                        pass
                    case "http://rs.tdwg.org/dwc/terms/scientificNameAuthorship":
                        # TODO
                        pass
                    case "http://rs.tdwg.org/dwc/terms/genericName":
                        # TODO
                        pass
                    case "http://rs.tdwg.org/dwc/terms/infragenericEpithet":
                        # TODO
                        pass
                    case "http://rs.tdwg.org/dwc/terms/specificEpithet":
                        # TODO
                        pass
                    case "http://rs.tdwg.org/dwc/terms/infraspecificEpithet":
                        # TODO
                        pass
                    case "http://rs.tdwg.org/dwc/terms/cultivarEpithet":
                        # TODO
                        pass
                    case "http://rs.tdwg.org/dwc/terms/nameAccordingTo":
                        # TODO
                        pass
                    case "http://rs.tdwg.org/dwc/terms/namePublishedIn":
                        # TODO
                        pass
                    case "http://rs.tdwg.org/dwc/terms/nomenclaturalCode":
                        # TODO
                        pass
                    case "http://rs.tdwg.org/dwc/terms/nomenclaturalStatus":
                        # TODO
                        pass
                    # dc.references -> inherited as URI
                    case "http://purl.org/dc/terms/references":
                        g.add((entity, URIRef('http://purl.org/dc/terms/references'), URIRef(value)))
                    # attributes inherited with Taxon as object
                    case "http://rs.tdwg.org/dwc/terms/acceptedNameUsageID" | \
                         "http://rs.tdwg.org/dwc/terms/originalNameUsageID":
                        g.add((entity, URIRef(key), htwk_col[value]))
                    # full inherited attributes
                    case "http://rs.tdwg.org/dwc/terms/taxonomicStatus" | \
                         "http://rs.tdwg.org/dwc/terms/taxonRemarks" | \
                         "http://catalogueoflife.org/terms/notho":
                        g.add((entity, URIRef(key), Literal(value)))
                    case _:
                        raise Exception(f"Could not parse key {key} with value {value} in core rows.")

        # Parse extension rows
        for extension_line in crow.extensions:
            match extension_line.rowtype:
                case "http://rs.gbif.org/terms/1.0/VernacularName":
                    g.add((entity, dwc.vernacularName,
                           Literal(extension_line.data["http://rs.tdwg.org/dwc/terms/vernacularName"],
                                   lang=extension_line.data["http://purl.org/dc/terms/language"])
                           ))

                case "http://rs.gbif.org/terms/1.0/Distribution":
                    # The dwc-extension 'Distribution' can't be parsed to normal triples due to its structure. To
                    # retain all information from the archive meta statements would be needed. I decided against using
                    # this technique and instead introduced two new properties, occurs and occursID, with their
                    # respective sub-properties to capture the information from dwc.locality/dwc.locationID and the
                    # dwc.occurrenceStatus.
                    occurrence_status = extension_line.data['http://rs.tdwg.org/dwc/terms/occurrenceStatus']
                    locality = extension_line.data['http://rs.tdwg.org/dwc/terms/locality']
                    locationID = extension_line.data['http://rs.tdwg.org/dwc/terms/locationID']

                    if locality != '':
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
                            raise Exception(f"Distribution unknown: {occurrence_status}!")

                    if locationID != '':
                        if occurrence_status == 'uncertain' or occurrence_status == '':
                            g.add((entity,
                                   htwk_col_ontology.occurs,
                                   Literal(locationID)))
                        elif occurrence_status == 'native':
                            g.add((entity,
                                   htwk_col_ontology.occursNatively,
                                   Literal(locationID)))
                        elif occurrence_status == 'domesticated':
                            g.add((entity,
                                   htwk_col_ontology.occursDomesticated,
                                   Literal(locationID)))
                        elif occurrence_status == 'alien':
                            g.add((entity,
                                   htwk_col_ontology.occursAlien,
                                   Literal(locationID)))
                        else:
                            raise Exception(f"Distribution unknown: {occurrence_status}!")

                case "http://rs.gbif.org/terms/1.0/SpeciesProfile":
                    for key, value in extension_line.data.items():
                        if key != "http://rs.tdwg.org/dwc/terms/taxonID" and value != '':
                            g.add((entity, URIRef(key), Literal(value)))

        g.serialize(sys.stdout.buffer, format='nt', encoding='utf-8')

        if N_taxons != 0 and count >= N_taxons:
            break
