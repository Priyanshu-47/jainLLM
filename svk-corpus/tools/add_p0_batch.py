#!/usr/bin/env python3
"""Add Task 22 P0 batch sources to the manifest configs."""
import csv
import sys
from pathlib import Path

ROOT = Path(r"E:\JainLLM\svk-corpus")
NEW_SOURCES = ROOT / "configs" / "new_sources.csv"
CURATED_FIELDS = ROOT / "configs" / "curated_fields.csv"

# 4 new Internet Archive items for P0 batch
new_source_rows = [
    "SVK-2015,Sri Avasyaka Sutra Part-i (1928),Sri Avasyaka Sutra Part-i,Bhadrabahu,JAIN,UNKNOWN,unknown,CANONICAL,san,Devanagari,DjVuTXT;PDF,not measured,UNMEASURED,https://archive.org/details/in.ernet.dli.2015.406853,https://archive.org/download/in.ernet.dli.2015.406853/,Internet Archive,none declared,DLI item no rights metadata. 1928 publication pre-1930. Avashyaka Sutra covers Samayik Pratikraman Vandana Pratyakhyan practices,WITH_CONDITIONS (R95_CHRONOLOGY_UNRESOLVED),CONDITIONAL,CONDITIONAL,n/a (Sanskrit/Prakrit canonical),none,source text layer; quality to be measured,no,MEDIUM,LOW,UNKNOWN,HIGH,TRAIN,Avashyaka Sutra Part 1 by Bhadrabahu. Covers six obligatory duties (Avashyaka). Pre-1930 publication. Publisher: Surat, Sheth Devchand Lalbhai Jain Pustakbhandar. 621 pages.",
    "SVK-2016,Panch-pratikraman (1928),Panch-pratikraman,Jain Kashinathji,JAIN,UNKNOWN,unknown,PRACTICE,hi,Devanagari,DjVuTXT;PDF,not measured,UNMEASURED,https://archive.org/details/in.ernet.dli.2015.445046,https://archive.org/download/in.ernet.dli.2015.445046/,Internet Archive,none declared,DLI item no rights metadata. 1928 publication pre-1930. Pratikraman practice text in Hindi,WITH_CONDITIONS (R95_CHRONOLOGY_UNRESOLVED),CONDITIONAL,CONDITIONAL,n/a (Hindi practice text),none,source text layer; quality to be measured,no,MEDIUM,LOW,UNKNOWN,HIGH,TRAIN,Panch-pratikraman Hindi practice text. Publisher: Bikaner, Champalal Gani Jain Grantmala. 368 pages. Covers Pratikraman (repentance ritual).",
    "SVK-2017,Pratikraman Sutra Arth Ane Sanvado Sahit (1939),Pratikraman Sutra,unknown,JAIN,UNKNOWN,unknown,PRACTICE,gu,Gujarati,DjVuTXT;PDF,not measured,UNMEASURED,https://archive.org/details/dli.ernet.520259,https://archive.org/download/dli.ernet.520259/,Internet Archive,none declared,DLI item no rights metadata. 1939 publication. Gujarati Pratikraman practice text,WITH_CONDITIONS (R95_CHRONOLOGY_UNRESOLVED),CONDITIONAL,CONDITIONAL,n/a (Gujarati practice text),none,source text layer; quality to be measured,no,MEDIUM,LOW,UNKNOWN,HIGH,TRAIN,Pratikraman Sutra with meaning and dialogue in Gujarati. Source library: Gujrat Vidyapith Library. Covers Pratikraman practice.",
    "SVK-2018,Shrawak Pratikraman Sutra,Shrawak Pratikraman Sutra,Shastri Vijay Muni,JAIN,UNKNOWN,unknown,PRACTICE,hi,Devanagari,DjVuTXT;PDF,not measured,UNMEASURED,https://archive.org/details/in.ernet.dli.2015.341224,https://archive.org/download/in.ernet.dli.2015.341224/,Internet Archive,none declared,DLI item with copyright permitted per dc.rights. Publisher: Aagara Sanmati Gianpith,WITH_CONDITIONS (R95_CHRONOLOGY_UNRESOLVED),CONDITIONAL,CONDITIONAL,n/a (Hindi practice text),none,source text layer; quality to be measured,no,MEDIUM,LOW,UNKNOWN,HIGH,TRAIN,Shrawak Pratikraman Sutra by Shastri Vijay Muni. Publisher: Aagara, Sanmati Gianpith. 168 pages. Subject: Jain Sahitya."
]

new_curated_rows = [
    "SVK-2015,internet_archive,in.ernet.dli.2015.406853,1928,unknown,\"Surat, Sheth Devchand Lalbhai Jain Pustakbhandar\",https://archive.org/details/in.ernet.dli.2015.406853,DLI item no rights metadata. 1928 publication pre-1930. Avashyaka Sutra.,low,false,false,true,true,Avashyaka Sutra Part 1 by Bhadrabahu. Publisher: Surat, Sheth Devchand Lalbhai Jain Pustakbhandar. 621 pages.",
    "SVK-2016,internet_archive,in.ernet.dli.2015.445046,1928,unknown,\"Bikaner, Champalal Gani Jain Grantmala\",https://archive.org/details/in.ernet.dli.2015.445046,DLI item no rights metadata. 1928 publication pre-1930.,low,false,false,true,true,Panch-pratikraman Hindi practice text. Publisher: Bikaner, Champalal Gani Jain Grantmala. 368 pages.",
    "SVK-2017,internet_archive,dli.ernet.520259,1939,unknown,\"Gujrat Vidyapith Library\",https://archive.org/details/dli.ernet.520259,DLI item no rights metadata. 1939 publication.,low,false,false,true,true,Pratikraman Sutra with meaning and dialogue in Gujarati. Source library: Gujrat Vidyapith Library.",
    "SVK-2018,internet_archive,in.ernet.dli.2015.341224,unknown,unknown,\"Aagara, Sanmati Gianpith\",https://archive.org/details/in.ernet.dli.2015.341224,DLI item with copyright permitted per dc.rights.,low,false,false,true,true,Shrawak Pratikraman Sutra by Shastri Vijay Muni. Publisher: Aagara, Sanmati Gianpith. 168 pages."
]

# Append to new_sources.csv
with open(NEW_SOURCES, "a", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    for row in new_source_rows:
        fields = row.split(",", 31)  # split into 32 fields
        writer.writerow(fields)

# Append to curated_fields.csv
with open(CURATED_FIELDS, "a", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    for row in new_curated_rows:
        # Parse carefully since fields may contain commas in quotes
        import io
        reader = csv.reader(io.StringIO(row))
        for r in reader:
            writer.writerow(r)

print(f"Added 4 new sources to {NEW_SOURCES.name}")
print(f"Added 4 curated entries to {CURATED_FIELDS.name}")
print("New source IDs: SVK-2015, SVK-2016, SVK-2017, SVK-2018")
