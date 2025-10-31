"""
Constants for the Historical OCR application.

This module contains all the constants used throughout the application,
making it easier to maintain and update values in one place.
"""

# API limits
MAX_FILE_SIZE_MB = 200
MAX_PAGES = 20

# Caching
CACHE_TTL_SECONDS = 24 * 3600  # 24 hours
MAX_CACHE_ENTRIES = 20

# Image processing
MAX_IMAGE_DIMENSION = 2500
IMAGE_QUALITY = 100

# Document types
DOCUMENT_TYPES = [
    "Auto-detect (standard processing)",
    "Newspaper or Magazine",
    "Letter or Correspondence",
    "Book or Publication",
    "Form or Legal Document",
    "Recipe",
    "Handwritten Document",
    "Map or Illustration",
    "Table or Spreadsheet",
    "Other (specify in instructions)",
    "Nepali BE License",
    "Citizenship_Front",
    "Citizenship_Back",
    "Voter_ID",
    "LICENSE",
    "Passport_Front",
    "Passport_Back"
]

# Document layouts
DOCUMENT_LAYOUTS = [
    "Standard layout",
    "Multiple columns",
    "Table/grid format",
    "Mixed layout with images"
]

# PDF settings
DEFAULT_PDF_DPI = 100
DEFAULT_MAX_PAGES = 3

# Content themes for subject tag extraction
CONTENT_THEMES = {
    # Historical Periods
    "Prehistoric": ["paleolithic", "neolithic", "stone age", "bronze age", "iron age", "prehistoric", "ancient",
                    "archaeology", "artifact", "primitive"],
    "Ancient World": ["mesopotamia", "egypt", "greek", "roman", "persia", "babylonian", "assyrian", "pharaoh",
                      "hieroglyphics", "cuneiform", "classical", "antiquity", "hellenistic", "republic", "empire"],
    "Medieval": ["middle ages", "medieval", "feudal", "crusades", "byzantine", "carolingian", "holy roman empire",
                 "dark ages", "castle", "knights", "chivalry", "monastery", "plague", "viking", "norse"],
    "Renaissance": ["renaissance", "humanism", "reformation", "counter-reformation", "medici", "tudor", "elizabethan",
                    "shakespeare", "machiavelli", "gutenberg", "printing press"],
    "Early Modern": ["early modern", "enlightenment", "age of reason", "scientific revolution", "colonial",
                     "colonization", "imperialism", "revolution", "baroque", "bourbon", "habsburg", "stuart"],
    "18th Century": ["18th century", "1700s", "revolution", "american revolution", "french revolution", "enlightenment",
                     "rococo", "neoclassical", "voltaire", "rousseau", "industrial"],
    "19th Century": ["19th century", "1800s", "victorian", "romantic", "napoleonic", "civil war",
                     "industrial revolution", "manifest destiny", "colonial", "imperialism", "belle epoque",
                     "fin de siecle"],
    "20th Century": ["20th century", "1900s", "world war", "great depression", "cold war", "interwar", "postwar",
                     "modernism", "atomic", "post-colonial", "totalitarian", "fascism", "soviet", "civil rights"],
    "Contemporary": ["contemporary", "modern", "postmodern", "digital age", "globalization", "information age",
                     "post-industrial", "post-colonial", "post-soviet", "post-war", "21st century"],

    # Geographic Contexts
    "European History": ["europe", "western europe", "eastern europe", "central europe", "mediterranean", "nordic",
                         "iberian", "british", "habsburg", "bourbon", "prussia", "holy roman empire"],
    "Asian History": ["asia", "east asia", "south asia", "central asia", "southeast asia", "china", "japan", "india",
                      "persia", "ottoman", "mongolian", "dynasty", "shogunate", "mughal", "silk road"],
    "African History": ["africa", "north africa", "west africa", "east africa", "sub-saharan", "sahel", "swahili",
                        "maghreb", "nubian", "ethiopian", "zulu", "colonial africa", "apartheid"],
    "American History": ["america", "colonial america", "revolutionary", "antebellum", "civil war", "reconstruction",
                         "frontier", "westward expansion", "manifest destiny", "native american", "indigenous"],
    "Latin American": ["latin america", "mesoamerica", "caribbean", "aztec", "mayan", "inca", "colonial", "viceroyalty",
                       "independence", "revolution", "hispanic", "creole", "mestizo", "indigenous"],
    "Oceanic History": ["oceania", "pacific", "australian", "aboriginal", "indigenous", "polynesian", "melanesian",
                        "micronesian", "maori", "maritime", "exploration", "settlement", "colonial"],

    # Historical Methodologies & Approaches
    "Archival Research": ["archive", "manuscript", "primary source", "provenance", "document", "preservation",
                          "cataloging", "repository", "collection", "papers", "fonds", "records", "registry"],
    "Oral History": ["oral history", "testimony", "interview", "narrative", "memory", "ethnography", "storytelling",
                     "tradition", "folklore", "witness", "account", "recording", "indigenous knowledge"],
    "Historical Archaeology": ["archaeology", "excavation", "artifact", "material culture", "stratigraphy",
                               "conservation", "field work", "site", "ruins", "preservation", "heritage",
                               "restoration"],
    "Digital History": ["digital", "database", "digitization", "computational", "network analysis", "gis", "mapping",
                        "visualization", "data mining", "text analysis", "digital humanities", "encoding"],
    "Historiography": ["historiography", "revisionism", "interpretation", "narrative", "discourse", "bias",
                       "perspective", "theory", "methodology", "framework", "historical thinking", "meta-history"],

    # Historical Document Types
    "Administrative Records": ["record", "registry", "account", "ledger", "census", "tax roll", "inventory", "charter",
                               "deed", "grant", "patent", "minutes", "docket", "survey", "assessment", "register"],
    "Diplomatic Documents": ["treaty", "agreement", "proclamation", "declaration", "diplomatic", "embassy", "consul",
                             "dispatch", "communique", "protocol", "convention", "alliance", "international"],
    "Personal Papers": ["diary", "journal", "memoir", "autobiography", "correspondence", "letter", "personal",
                        "private", "papers", "notes", "scrapbook", "commonplace book", "sketchbook"],
    "Media History": ["newspaper", "gazette", "periodical", "pamphlet", "broadside", "print culture", "press",
                      "editorial", "journalism", "reporter", "editor", "circulation", "readership", "subscriber"],
    "Visual Materials": ["photograph", "illustration", "print", "map", "atlas", "cartography", "engraving", "woodcut",
                         "lithograph", "panorama", "portrait", "landscape", "sketch", "drawing", "plate"],
    "Legal Documents": ["legal", "law", "statute", "code", "constitution", "legislation", "decree", "ordinance",
                        "bylaw", "regulation", "case", "trial", "testimony", "deposition", "verdict", "judgment"],

    # Historical Themes & Movements
    "Economic History": ["economic", "commerce", "trade", "market", "merchant", "finance", "banking", "currency",
                         "coin", "inflation", "recession", "depression", "exchange", "capital", "labor", "guild"],
    "Social History": ["social", "society", "class", "status", "hierarchy", "everyday life", "community",
                       "neighborhood", "urban", "rural", "poverty", "wealth", "leisure", "entertainment", "customs"],
    "Political History": ["political", "politics", "government", "state", "monarchy", "republic", "democracy",
                          "aristocracy", "parliament", "congress", "election", "regime", "policy", "reform",
                          "revolution"],
    "Intellectual History": ["intellectual", "idea", "philosophy", "theory", "concept", "movement", "thought",
                             "discourse", "debate", "enlightenment", "rationalism", "empiricism", "ideology"],
    "Cultural History": ["cultural", "culture", "custom", "tradition", "ritual", "ceremony", "festival", "celebration",
                         "holiday", "folklore", "music", "art", "literature", "fashion", "consumption"],
    "Religious History": ["religious", "religion", "church", "theology", "belief", "faith", "worship", "ritual",
                          "sacred", "clergy", "monastery", "temple", "mosque", "synagogue", "pilgrimage", "sect"],
    "Military History": ["military", "war", "conflict", "battle", "campaign", "siege", "army", "navy", "soldier",
                         "officer", "regiment", "battalion", "artillery", "cavalry", "infantry", "strategy", "tactics"],
    "Science History": ["scientific", "science", "experiment", "discovery", "theory", "hypothesis", "observation",
                        "laboratory", "academy", "research", "natural philosophy", "medicine", "technology"],
    "Environmental History": ["environmental", "ecology", "climate", "weather", "landscape", "agriculture", "farming",
                              "forestry", "conservation", "pollution", "resource", "sustainability", "natural"],

    # Specialized Historical Topics
    "Migration History": ["migration", "immigration", "emigration", "diaspora", "exile", "refugee", "settlement",
                          "colonization", "population movement", "forced migration", "displacement", "resettlement"],
    "Maritime History": ["maritime", "naval", "shipping", "navigation", "sailor", "piracy", "privateering", "admiralty",
                         "port", "harbor", "shipyard", "vessel", "sail", "trade route", "exploration"],
    "Gender History": ["gender", "women", "feminist", "sexuality", "masculinity", "femininity", "patriarchy",
                       "suffrage", "domestic", "family", "marriage", "emancipation", "rights", "equality"],
    "Labor History": ["labor", "worker", "union", "strike", "apprentice", "guild", "factory", "workshop", "wage",
                      "hours", "working conditions", "industrialization", "mechanization", "automation"],
    "Urban History": ["urban", "city", "town", "metropolitan", "municipal", "civic", "suburb", "neighborhood",
                      "planning", "infrastructure", "utilities", "housing", "development", "gentrification"],
    "Rural History": ["rural", "countryside", "village", "agricultural", "farming", "peasant", "yeoman", "tenant",
                      "sharecropper", "enclosure", "common land", "manor", "estate", "plantation"],
    "Colonial History": ["colonial", "colony", "settlement", "frontier", "borderland", "territory", "dominion",
                         "province", "governance", "administration", "native", "indigenous", "contact zone"],
    "Indigenous History": ["indigenous", "native", "aboriginal", "first nations", "tribal", "reservation",
                           "sovereignty", "land rights", "treaty rights", "cultural preservation", "oral tradition"],

    # General Historical Terms
    "Historical": ["history", "historical", "historiography", "heritage", "legacy", "tradition", "memory",
                   "commemoration", "preservation", "conservation", "restoration", "interpretation", "significance"],
    "Chronology": ["chronology", "timeline", "periodization", "era", "epoch", "age", "century", "decade", "millennium",
                   "year", "date", "dating", "chronological", "contemporary", "synchronic", "diachronic"],
    "Heritage": ["heritage", "preservation", "conservation", "landmark", "monument", "historic site", "museum",
                 "archive", "collection", "artifact", "relic", "antiquity", "cultural heritage", "patrimony"]
}

# Period tags based on year ranges
# These ranges are used to assign historical period tags to documents based on their year.
PERIOD_TAGS = {
    (0, 499): "Ancient Era (to 500 CE)",
    (500, 999): "Early Medieval (500–1000)",
    (1000, 1299): "High Medieval (1000–1300)",
    (1300, 1499): "Late Medieval (1300–1500)",
    (1500, 1599): "Renaissance (1500–1600)",
    (1600, 1699): "Early Modern (1600–1700)",
    (1700, 1775): "Enlightenment (1700–1775)",
    (1776, 1799): "Age of Revolutions (1776–1800)",
    (1800, 1849): "Early 19th Century (1800–1850)",
    (1850, 1899): "Late 19th Century (1850–1900)",
    (1900, 1918): "Early 20th Century & WWI (1900–1918)",
    (1919, 1938): "Interwar Period (1919–1938)",
    (1939, 1945): "World War II (1939–1945)",
    (1946, 1968): "Postwar & Mid-20th Century (1946–1968)",
    (1969, 1989): "Late 20th Century (1969–1989)",
    (1990, 2000): "Turn of the 21st Century (1990–2000)",
    (2001, 2099): "Contemporary (21st Century)"
}

# Default fallback tags for documents when no specific tags are detected.
DEFAULT_TAGS = [
    "Document",
    "Historical",
    "Text",
    "Primary Source",
    "Archival Material",
    "Record",
    "Manuscript",
    "Printed Material",
    "Correspondence",
    "Publication"
]

# Generic tags that can be used for broad categorization or as supplemental tags.
GENERIC_TAGS = [
    "Archive",
    "Content",
    "Record",
    "Source",
    "Material",
    "Page",
    "Scan",
    "Image",
    "Transcription",
    "Uncategorized",
    "General",
    "Miscellaneous"
]
