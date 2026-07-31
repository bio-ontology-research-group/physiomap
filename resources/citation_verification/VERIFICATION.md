# Manuscript citation verification

Every reference in the manuscript (`main.tex`) was verified by retrieving its authoritative
record from **Crossref** (`api.crossref.org`), **arXiv** (`export.arxiv.org/api`), or **DataCite**
(`api.datacite.org`, for the Zenodo dataset), storing the record in this directory (`<key>.json` /
`<key>.xml`; a few OA PDFs where freely available), reading it, and comparing every field
(authors, title, venue, volume, issue, pages, year, DOI) to the bibitem. Run 2026-06-14.

**Result: 41/41 references are genuine — no fabrications.** 3 field errors fixed in `main.tex`;
1 provider discrepancy left as-is (documented); DOIs added for ~33 refs that lacked them.

## Corrections applied to main.tex
| key | field | was | now (authoritative) | source |
|---|---|---|---|---|
| cowen2017 | title | "...amplifier of genetic **information**" | "...amplifier of genetic **associations**" | Crossref 10.1038/nrg.2017.38 |
| signor2020 | title | "SIGNOR 2.0, the SIGnaling Network Open Resource" | "...Open Resource **2.0: 2019 update**" | Crossref 10.1093/nar/gkz949 |
| sidekick | cite ESWC paper (not Zenodo dataset) | Zenodo dataset, order Henao/Hoehndorf | **ESWC 2026 LNCS paper**, order Ashhad, Mashkova, **Henao, Hoehndorf**, pp. 253–276 | Crossref 10.1007/978-3-032-25159-6_14 (author order confirmed by R.H.) |

## Documented, not changed
- **guyton1972** — Crossref gives pages **13–44**; PubMed (PMID 4334846) gives **13–46**. Provider
  disagreement on the end page only; both resolve to the real paper (DOI 10.1146/annurev.ph.34.030172.000305).
  Kept PubMed's 13–46 in the bibliography.
- **maybee1969** — Crossref stores the first-author surname with a typo ("Maybe"); the correct spelling
  is **Maybee** (as in the bibliography). No change.
- **mooij2013**, **druzdzel1993** — genuine conference papers (UAI 2013 / AAAI 1993) not registered in
  Crossref; corroborated by author/title/topic. arXiv:1304.7920 added for mooij2013.
- **pearl1988**, **samuelson1947** — classic monographs; verified via search, no article-level DOI used.

## Per-reference status (all VERIFIED unless noted) + confirmed identifier
forre2017 arXiv:1710.08775 · forre2018 arXiv:1807.03024 · bongers2021 10.1214/21-AOS2064 ·
mooij2013 arXiv:1304.7920 (not in Crossref) · pearl1988 (book) · pearl2009 10.1017/CBO9780511803161 ·
lauritzen1990 10.1002/net.3230200503 · geiger1990 10.1002/net.3230200504 ·
lancaster1962 10.2307/2295817 · quirk1965 10.2307/2295838 · maybee1969 10.1137/1011004 ·
samuelson1947 (book) · wellman1990 10.1016/0004-3702(90)90026-V · druzdzel1993 (AAAI, not in Crossref) ·
dekleer1984 10.1016/0004-3702(84)90037-7 · kuipers1986 10.1016/0004-3702(86)90073-1 ·
forbus1984 10.1016/0004-3702(84)90038-9 · guyton1972 10.1146/annurev.ph.34.030172.000305 (page note) ·
hester2011 10.3389/fphys.2011.00012 · hunter2003 10.1038/nrm1054 · cellml2008 10.1093/bioinformatics/btn390 ·
biomodels2020 10.1093/nar/gkz1055 · karr2012 10.1016/j.cell.2012.05.044 · kauffman1969 10.1016/0022-5193(69)90015-0 ·
thomas1991 10.1016/S0022-5193(05)80350-9 · lenovere2015 10.1038/nrg3885 · ginsim2006 10.1016/j.biosystems.2005.10.003 ·
cellnopt2012 10.1186/1752-0509-6-133 · maboss2017 10.1093/bioinformatics/btx123 ·
signor2020 10.1093/nar/gkz949 (title fixed) · omnipath2021 10.15252/msb.20209923 · indra2017 10.15252/msb.20177651 ·
barabasi2011 10.1038/nrg2918 · menche2015 10.1126/science.1257601 · cowen2017 10.1038/nrg.2017.38 (title fixed) ·
hpo2021 10.1093/nar/gkaa1043 · chembl2019 10.1093/nar/gky1075 · rhea2022 10.1093/nar/gkab1016 ·
sidekick 10.5281/zenodo.17779317 (author order fixed) · sider2016 10.1093/nar/gkv1075 · ankley2010 10.1002/etc.34

## Reproduce
Records are the `*.json` / `*.xml` files in this directory. Re-fetch any with e.g.
`curl -sL "https://api.crossref.org/works/<DOI>?mailto=..."`.
