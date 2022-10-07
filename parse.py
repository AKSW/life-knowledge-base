import csv
import sys
import urllib.parse

urlencode = urllib.parse.quote_plus

from tqdm import tqdm
from dwca.read import DwCAReader
from rdflib import Namespace, URIRef, Graph, Literal, XSD
from rdflib.namespace import RDF, RDFS

if len(sys.argv) < 2:
    print("Please give the input file as an argument")
    exit(1)

# If positiv second arg was given, use it as N_taxons (max number to parse)
if len(sys.argv) > 2 and int(sys.argv[2]) > 0:
    N_taxons = int(sys.argv[2])
else:
    N_taxons = 0

# Declare common name spaces
dwc = Namespace("http://rs.tdwg.org/dwc/terms/")
taxons = Namespace("http://col.htwk-leipzig.de/taxon/")
names = Namespace("http://col.htwk-leipzig.de/name/")
onto = Namespace("http://ontology.col.htwk-leipzig.de/")

csv.field_size_limit(sys.maxsize)  # Needed for iteration of col-data
with DwCAReader(path=sys.argv[1]) as dwca:
    for count, crow in tqdm(enumerate(dwca), total=N_taxons, unit=" Taxons", smoothing=0):
        g = Graph()

        # Create base entity and name with COL ID as URI and label
        entity = taxons[urlencode(crow.id)]
        sname = names[urlencode(crow.id)]
        g.add((entity, RDF.type, dwc.Taxon))
        g.add((entity, RDFS.label, Literal(crow.id)))
        g.add((entity, dwc.scientificName, sname))

        # Parse core rows
        for key, value in crow.data.items():
            if value != '':
                match key:
                    # dwc.taxonID -> dropped
                    case "http://rs.tdwg.org/dwc/terms/taxonID":
                        continue
                    # dwc.parentNameUsageID -> col.parent
                    case "http://rs.tdwg.org/dwc/terms/parentNameUsageID":
                        g.add((entity, onto.parent, taxons[urlencode(value)]))
                    # dwc.datasetID -> inherited with datatype
                    case "http://rs.tdwg.org/dwc/terms/datasetID":
                        g.add((entity, URIRef(key), Literal(value, datatype=XSD.integer)))
                    # dwc.taxonRank -> entity a onto.<Rank>, scientific name inherits
                    case "http://rs.tdwg.org/dwc/terms/taxonRank":
                        g.add((sname, dwc.taxonRank, Literal(value)))  # inherit
                        match value.capitalize():
                            case "Unranked" | "Kingdom" | "Phylum" | "Class" | "Subclass" | \
                                 "Order" | "Suborder" | "Family" | "Genus" | "Species" as rank:
                                g.add((entity, RDF.type, onto[rank]))
                            case _:
                                g.add((entity, RDF.type, onto.Other))
                    # dwc.scientificName -> label for scientific Name object
                    case "http://rs.tdwg.org/dwc/terms/scientificName":
                        g.add((sname, RDFS.label, Literal(value)))
                    # dwc.taxonomicStatus -> TaxonomicStatus of scientific Name object
                    case "http://rs.tdwg.org/dwc/terms/taxonomicStatus":
                        match value:
                            case "accepted":
                                g.add((sname, dwc.taxonomicStatus, onto.accepted))
                            case "synonym":
                                g.add((sname, dwc.taxonomicStatus, onto.synonym))
                            case "ambiguous synonym":
                                g.add((sname, dwc.taxonomicStatus, onto.ambiguous_synonym))
                            case "provisionally accepted":
                                g.add((sname, dwc.taxonomicStatus, onto.provisionally_accepted))
                            case "misapplied":
                                g.add((sname, dwc.taxonomicStatus, onto.misapplied))
                            case "unresolved":
                                g.add((sname, dwc.taxonomicStatus, onto.unresolved))
                            case _:
                                raise Exception(f"Unknown dwc:taxonomicStatus: {value} at taxon {crow.id}.")
                    # dc.references -> inherited as URI
                    case "http://purl.org/dc/terms/references":
                        g.add((entity, URIRef(key), URIRef(value)))
                    # attributes inherited with Taxon as object
                    case "http://rs.tdwg.org/dwc/terms/acceptedNameUsageID" | \
                         "http://rs.tdwg.org/dwc/terms/originalNameUsageID":
                        g.add((entity, URIRef(key), taxons[urlencode(value)]))
                    # fully inherited attributes
                    case "http://rs.tdwg.org/dwc/terms/taxonRemarks" | \
                         "http://catalogueoflife.org/terms/notho":
                        g.add((entity, URIRef(key), Literal(value)))
                    # fully inherited attributes to sname
                    case "http://rs.tdwg.org/dwc/terms/scientificNameID" | \
                         "http://rs.tdwg.org/dwc/terms/scientificNameAuthorship" | \
                         "http://rs.tdwg.org/dwc/terms/genericName" | \
                         "http://rs.tdwg.org/dwc/terms/infragenericEpithet" | \
                         "http://rs.tdwg.org/dwc/terms/specificEpithet" | \
                         "http://rs.tdwg.org/dwc/terms/infraspecificEpithet" | \
                         "http://rs.tdwg.org/dwc/terms/cultivarEpithet" | \
                         "http://rs.tdwg.org/dwc/terms/nameAccordingTo" | \
                         "http://rs.tdwg.org/dwc/terms/namePublishedIn" | \
                         "http://rs.tdwg.org/dwc/terms/nomenclaturalCode" | \
                         "http://rs.tdwg.org/dwc/terms/nomenclaturalStatus":
                        g.add((sname, URIRef(key), Literal(value)))
                    case _:
                        raise Exception(f"Could not parse key {key} with value {value} in core rows.")

        # Parse extension rows
        for extension_line in crow.extensions:
            match extension_line.rowtype:
                # VernacularName extension -> add onto:VernacularName object
                case "http://rs.gbif.org/terms/1.0/VernacularName":
                    vname = extension_line.data["http://rs.tdwg.org/dwc/terms/vernacularName"]
                    lang = extension_line.data["http://purl.org/dc/terms/language"]
                    match lang:
                        case "eng":
                            lang = "en"
                        case "deu":
                            lang = "de"
                    vname_object = names[urlencode(f"{crow.id}_{vname}")]  # ID added for prohibiting collisions
                    g.add((vname_object, RDF.type, onto.VernacularName))
                    g.add((vname_object, RDFS.label, Literal(vname, lang=lang)))
                    g.add((entity, dwc.vernacularName, vname_object))

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
                                   onto.occurs,
                                   Literal(locality)))
                        elif occurrence_status == 'native':
                            g.add((entity,
                                   onto.occursNatively,
                                   Literal(locality)))
                        elif occurrence_status == 'domesticated':
                            g.add((entity,
                                   onto.occursDomesticated,
                                   Literal(locality)))
                        elif occurrence_status == 'alien':
                            g.add((entity,
                                   onto.occursAlien,
                                   Literal(locality)))
                        else:
                            raise Exception(f"Distribution unknown: {occurrence_status}!")

                    if locationID != '':
                        if occurrence_status == 'uncertain' or occurrence_status == '':
                            g.add((entity,
                                   onto.occurs,
                                   Literal(locationID)))
                        elif occurrence_status == 'native':
                            g.add((entity,
                                   onto.occursNatively,
                                   Literal(locationID)))
                        elif occurrence_status == 'domesticated':
                            g.add((entity,
                                   onto.occursDomesticated,
                                   Literal(locationID)))
                        elif occurrence_status == 'alien':
                            g.add((entity,
                                   onto.occursAlien,
                                   Literal(locationID)))
                        else:
                            raise Exception(f"Distribution unknown: {occurrence_status}!")

                case "http://rs.gbif.org/terms/1.0/SpeciesProfile":
                    if extension_line.data["http://rs.gbif.org/terms/1.0/isExtinct"] == 'true':
                        g.add((entity, onto.hasStatus, onto.EX))
                    if extension_line.data["http://rs.gbif.org/terms/1.0/isMarine"] == 'true':
                        g.add((entity, onto.livesIn, onto.Marine))
                    if extension_line.data["http://rs.gbif.org/terms/1.0/isFreshwater"] == 'true':
                        g.add((entity, onto.livesIn, onto.Freshwater))
                    if extension_line.data["http://rs.gbif.org/terms/1.0/isTerrestrial"] == 'true':
                        g.add((entity, onto.livesIn, onto.Terrestrial))

        g.serialize(sys.stdout.buffer, format='nt', encoding='utf-8')

        if N_taxons != 0 and count >= N_taxons:
            break
