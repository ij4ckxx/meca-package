# Vendored DTD: jats-archiving-1.2

Per ADR-025 and Risk Register RISK-023: real DTD files, version-pinned,
required for structural validation of generated XML.

**Populated** — DTD-compliance milestone. This is the full ANSI/NISO
JATS (Z39.96) Journal Archiving and Interchange DTD Suite v1.2
(2019-02-08), MathML 2.0 variant, exactly as referenced by the
`DOCTYPE` in the NISO MECA project's own reference `article.xml`
(https://github.com/niso-standards/meca/blob/main/examples/article.xml):

```
<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Archiving and
Interchange DTD v1.2 20190208//EN"
"https://jats.nlm.nih.gov/archiving/1.2/JATS-archivearticle1.dtd">
```

Source: `JATS-Archiving-1-2-MathML2-DTD.zip`, downloaded from
https://public.nlm.nih.gov/projects/jats/archiving/1.2/ (the official
NLM/NISO distribution point). Public-domain US government work; freely
redistributable.

`JATS-archivearticle1.dtd` is the entry point `article.xml` validation
loads (see `meca_engine.validation.xml_validator`); every other file
in this directory is a module/entity/character-set file it includes by
relative `SYSTEM` reference. Do not remove or rename any file here —
the suite resolves them all relative to this directory.
