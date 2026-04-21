# SKILL: Metadata Extraction from Scientific Manuscripts

## Metadata

```yaml
skill_id:     manuscript-metadata-extraction
version:      1.0.0
domain:       scientific-publishing / plant-genomics / soil-microbiome / environmental-sampling
task:         field-level text extraction from unstructured scientific narrative
input:        any scientific manuscript (PDF, plain text, or structured document)
output:       structured field-value pairs mapped to the ERC000022 checklist schema
schema_ref:   ERC000022 (EMBL-EBI environmental sample metadata standard)
generalizes:  true — logic applies regardless of manuscript structure, author style, or domain variant
```

---

## Purpose

This skill enables an LLM to read a scientific manuscript and extract structured metadata
values that correspond to fields in the ERC000022 environmental sample checklist. Authors
rarely use field names explicitly. Values are distributed across sections, embedded in
narrative prose, and expressed through domain-specific conventions that vary by author,
journal, and sub-discipline.

The skill defines:
- The full extraction schema with hierarchical field groupings
- Strategies for recognising implicit field values in unstructured text
- Rules for handling encoding ambiguity, unit normalisation, and absent fields
- Generalisation principles so the logic applies across any manuscript format

---

## Core Extraction Principles

### 1. Never require explicit field names

Authors do not write "soil_type: Kastanozem" or "pH: 7.6". Values are embedded in
sentences like "soils were classified as..." or "acidity measurements indicated slightly
alkaline conditions". The extractor must map narrative language to schema fields without
relying on the presence of field-name strings.

### 2. Distribute attention across the full document

A single field's value may be established in one section and elaborated, qualified, or
contradicted in another. Extraction must integrate evidence from all sections before
committing to a value. Do not treat section boundaries as hard scopes.

### 3. Tolerate heterogeneous expression

The same value can be expressed in any of these forms and all are valid extractions:

| Expression type | Example |
|---|---|
| Direct measurement | "pH 7.6" |
| Qualitative descriptor | "slightly alkaline" |
| Comparative reference | "more alkaline than the adjacent control plots" |
| Implied by method | "KCl-extractable aluminum below detection" implies low Al saturation |
| Negation | "no evidence of waterlogging" implies well-drained |
| Range | "7.4 to 7.9" |
| Threshold | "below 5% exchangeable aluminum" |
| Phenological proxy | "grain-filling stage" implies approximate calendar period |

All of these are valid extracted values. Record what the text actually states, not a
normalised canonical form, unless normalisation is explicitly requested.

### 4. Assign confidence and evidence

For every extracted value, identify:
- **Evidence span**: the verbatim sentence(s) from which the value was inferred
- **Confidence**: high (directly stated), medium (inferred from context), low (implied or ambiguous)
- **Section**: where in the document the evidence appeared

### 5. Represent absent fields explicitly

If a field has no recoverable evidence in the document, record it as `null` with a brief
rationale. Absence is informative. Do not guess or hallucinate values for missing fields.

### 6. Distinguish reported values from inferred values

- **Reported**: the author states a value, measurement, or classification directly.
- **Inferred**: the value is reconstructed from related context (e.g., inferring trophic
  level from described metabolic activity rather than from the word "photoautotroph").

Tag inferred values clearly so downstream users can apply appropriate scepticism.

---

## Extraction Schema

The schema below defines all extractable fields, grouped by category. For each field,
the schema specifies the field type, the vocabulary of expected values where applicable,
and guidance on how values typically appear in manuscript prose.

Fields marked `TEXT_CHOICE_FIELD` have a controlled vocabulary. Fields marked
`TEXT_FIELD` accept any string. In both cases, extract whatever the manuscript states —
do not force the text into the controlled vocabulary unless the match is clear.

---

### Group 1: Environment — Geography and Climate

**Group rule:** Any number of fields may be present or absent.

| Field | Type | Controlled values | Extraction guidance |
|---|---|---|---|
| `geographic_location_country_andor_sea` | TEXT_CHOICE_FIELD | Country names, ocean names, "not collected", "not provided" | Country or water body named in site description, affiliation, or data availability section |
| `geographic_location_region_and_locality` | TEXT_FIELD | — | Named region, county, province, watershed, or farm locality |
| `geographic_location_latitude` | TEXT_FIELD | — | Decimal degrees or DMS; may appear as coordinate pair in parentheses |
| `geographic_location_longitude` | TEXT_FIELD | — | Decimal degrees or DMS; accompanies latitude |
| `elevation` | TEXT_FIELD | — | Metres or feet above sea level; may be given as a range across a gradient |
| `altitude` | TEXT_FIELD | — | Synonymous with elevation in many manuscripts; treat as equivalent unless separately stated |
| `broadscale_environmental_context` | TEXT_FIELD | — | Biome descriptor: "semiarid", "temperate", "tropical rainforest", "boreal", etc. May be implied by climate statistics |
| `local_environmental_context` | TEXT_FIELD | — | Finer-scale habitat: "agroecosystem", "riparian zone", "forest edge", "managed grassland" |
| `environmental_medium` | TEXT_FIELD | — | The physical matrix sampled: "soil", "rhizosphere", "sediment", "water", "plant tissue" |
| `mean_annual_temperature` | TEXT_FIELD | — | Annual mean; may be stated as range across sites or elevation bands |
| `mean_annual_precipitation` | TEXT_FIELD | — | Annual total precipitation; often expressed as an upper bound or typical range |
| `mean_seasonal_temperature` | TEXT_FIELD | — | Season-specific temperatures; look for summer/winter extremes in climate description |
| `mean_seasonal_precipitation` | TEXT_FIELD | — | Season-specific precipitation totals |
| `link_to_climate_information` | TEXT_FIELD | — | URL or database citation for climate data (e.g., meteorological service, WorldClim) |

---

### Group 2: Environment — Soil

**Group rule:** Any number of fields may be present or absent.

| Field | Type | Controlled values | Extraction guidance |
|---|---|---|---|
| `soil_type` | TEXT_CHOICE_FIELD | Acrisol, Albeluvisol, Alisol, Andosol, Anthrosol, Arenosol, Calcisol, Cambisol, Chernozem, Cryosol, Durisol, Ferralsol, Fluvisol, Gleysol, Gypsisol, Histosol, Kastanozem, Leptosol, Lixisol, Luvisol, Nitisol, Phaeozem, Planosol, Plinthosol, Podzol, Regosol, Solonchak, Solonetz, Stagnosol, Technosol, Umbrisol, Vertisol | FAO/WRB soil classification name; may appear with or without "classified as" language |
| `soil_taxonomicfao_classification` | TEXT_FIELD | — | Full FAO classification string including edition reference (e.g., "WRB 2015") |
| `soil_taxonomiclocal_classification` | TEXT_FIELD | — | National or regional system name (e.g., USDA Soil Taxonomy order) |
| `soil_taxonomiclocal_classification_method` | TEXT_FIELD | — | How local classification was determined |
| `soil_type_method` | TEXT_FIELD | — | Method used to determine FAO soil type: field survey, laboratory confirmation, published map |
| `soil_texture_measurement` | TEXT_FIELD | — | Texture class (clay loam, sandy loam) or particle-size fractions (% sand, silt, clay) |
| `soil_texture_method` | TEXT_FIELD | — | Analytical method: hydrometer, pipette, laser diffraction |
| `soil_horizon` | TEXT_CHOICE_FIELD | A horizon, B horizon, E horizon, O horizon, Permafrost, R layer | Named in profile description or sampling depth context |
| `drainage_classification` | TEXT_CHOICE_FIELD | excessively drained, moderately well, poorly, somewhat poorly, very poorly, well | Stated or inferred from waterlogging history, redoximorphic features, or topographic position |
| `profile_position` | TEXT_CHOICE_FIELD | backslope, footslope, shoulder, summit, toeslope | Topographic position in the landscape; may be stated as "slope position" |
| `slope_gradient` | TEXT_FIELD | — | Percentage or degrees; may be a range across plots |
| `slope_aspect` | TEXT_FIELD | — | Cardinal or intercardinal direction (e.g., north-facing, NNE) |
| `ph` | TEXT_FIELD | — | Numeric value or qualitative class (acidic, neutral, alkaline); look in soil characterisation and results |
| `ph_method` | TEXT_FIELD | — | Suspension ratio (1:1, 1:2.5, 1:5), solvent (water, CaCl2, KCl), electrode type |
| `water_content` | TEXT_FIELD | — | Gravimetric or volumetric percentage; may vary by site or depth |
| `water_content_method` | TEXT_FIELD | — | Gravimetric (oven-drying), TDR, neutron probe |
| `temperature` | TEXT_FIELD | — | In-situ soil temperature at time of sampling; distinct from air or climate temperature |
| `total_organic_carbon` | TEXT_FIELD | — | Concentration with units (g kg-1, %); may be called "SOC" or "organic carbon" |
| `total_organic_carbon_method` | TEXT_FIELD | — | Dry combustion, Walkley-Black, loss-on-ignition |
| `total_nitrogen_content` | TEXT_FIELD | — | Concentration with units; may be called "total N" or "Kjeldahl N" |
| `total_nitrogen_content_method` | TEXT_FIELD | — | Dry combustion (CHNS), Kjeldahl |
| `organic_matter` | TEXT_FIELD | — | Percentage or g kg-1; may be reported as SOM or estimated via C:N ratio |
| `organic_nitrogen` | TEXT_FIELD | — | Organic N fraction; distinct from total N or mineral N |
| `extreme_unusual_properties/heavy_metals` | TEXT_FIELD | — | Concentration of any heavy metal (Pb, Cd, As, Zn, Cu, Cr, Ni, Hg); look in unusual properties or contamination context |
| `extreme_unusual_properties/heavy_metals_method` | TEXT_FIELD | — | ICP-MS, AAS, XRF |
| `extreme_unusual_properties/al_saturation` | TEXT_FIELD | — | Percentage exchangeable aluminum; phytotoxic above ~60% in acidic soils |
| `extreme_unusual_properties/al_saturation_method` | TEXT_FIELD | — | KCl extraction + AAS or titration |

---

### Group 3: Local Environment — Current Conditions

**Group rule:** Any number of fields may be present or absent.

| Field | Type | Controlled values | Extraction guidance |
|---|---|---|---|
| `current_land_use` | TEXT_FIELD | — | What the land is used for at time of sampling: arable, pasture, forest, urban, conservation |
| `current_vegetation` | TEXT_FIELD | — | Plant species or community present: wheat, mixed grassland, deciduous woodland |
| `current_vegetation_method` | TEXT_FIELD | — | How vegetation was characterised: field survey, remote sensing, published vegetation map |
| `link_to_classification_information` | TEXT_FIELD | — | URL or citation for land use or vegetation classification system |

---

### Group 4: Local Environment — History

**Group rule:** Any number of fields may be present or absent.

| Field | Type | Controlled values | Extraction guidance |
|---|---|---|---|
| `history/previous_land_use` | TEXT_FIELD | — | Prior land use before current: former pasture, deforested, previously flooded |
| `previous_land_use_method` | TEXT_FIELD | — | How prior land use was determined: archives, remote sensing, farmer interview |
| `history/crop_rotation` | TEXT_FIELD | — | Rotation sequence and cycle length; look in agronomic context |
| `history/agrochemical_additions` | TEXT_FIELD | — | Fertiliser types, herbicides, pesticides, and application history |
| `history/tillage` | TEXT_CHOICE_FIELD | chisel, cutting disc, disc plough, drill, mouldboard, ridge till, strip tillage, tined, zonal tillage | Tillage implement or system named in management history |
| `history/fire` | TEXT_FIELD | — | Whether fire has occurred; frequency, date, or type if stated |
| `history/flooding` | TEXT_FIELD | — | Flood history: frequency, duration, dates if stated |
| `history/extreme_events` | TEXT_FIELD | — | Drought, storm, disease outbreak, or other disturbance events |

---

### Group 5: Sample Collection

**Group rule:** Any number of fields may be present or absent.

| Field | Type | Controlled values | Extraction guidance |
|---|---|---|---|
| `collection_date` | TEXT_FIELD | — | Date, season, or phenological stage; ISO 8601 if given, otherwise as stated |
| `sample_collection_device` | TEXT_FIELD | — | Physical tool used: soil corer, auger, syringe, grab sampler; include dimensions if stated |
| `sample_collection_method` | TEXT_FIELD | — | Procedure: composite coring, grab sampling, bulk collection; depth and angle if stated |
| `amount_or_size_of_sample_collected` | TEXT_FIELD | — | Mass or volume of each sample; pooling scheme if multiple cores combined |
| `sample_storage_conditions` | TEXT_FIELD | — | Temperature, container, preservative, and duration from collection to processing |
| `sample_pooling` | TEXT_FIELD | — | Whether samples were pooled; number of individuals or replicates per pool |
| `sieving` | TEXT_FIELD | — | Mesh size and purpose (root removal, aggregate fractionation) |
| `depth` | TEXT_FIELD | — | Sampling depth in cm or m; single value or range |
| `microbial_biomass` | TEXT_FIELD | — | Numeric value with units (µg C g-1, nmol ATP g-1) |
| `microbial_biomass_method` | TEXT_FIELD | — | Chloroform fumigation-extraction, substrate-induced respiration, phospholipid fatty acids |
| `horizon_method` | TEXT_FIELD | — | How soil horizon was identified for targeted sampling |

---

### Group 6: Sample Processing

**Group rule:** Any number of fields may be present or absent.

| Field | Type | Controlled values | Extraction guidance |
|---|---|---|---|
| `sample_material_processing` | TEXT_FIELD | — | Physical processing steps after collection: homogenisation, freeze-drying, grinding |
| `sample_volume_or_weight_for_dna_extraction` | TEXT_FIELD | — | Mass or volume of material used as input to DNA extraction |
| `nucleic_acid_extraction` | TEXT_FIELD | — | Kit name, version, and any protocol modifications (bead-beating speed, additional lysis steps) |
| `nucleic_acid_amplification` | TEXT_FIELD | — | PCR reaction composition: polymerase, buffer, primer concentrations, template input |
| `pcr_primers` | TEXT_FIELD | — | Primer names and sequences; target region implied |
| `pcr_conditions` | TEXT_FIELD | — | Full thermocycle: initial denaturation, cycle count, annealing temperature, extension |
| `library_construction_method` | TEXT_FIELD | — | Kit or protocol: Nextera XT, TruSeq, ligation-based, tagmentation |
| `library_size` | TEXT_FIELD | — | Mean insert size in bp; may be given as range or post-trimming value |
| `library_reads_sequenced` | TEXT_FIELD | — | Read count per sample; may be mean, range, or total across run |
| `library_vector` | TEXT_FIELD | — | Cloning vector if applicable (rare in amplicon studies) |
| `library_screening_strategy` | TEXT_FIELD | — | Selection or enrichment method applied before sequencing |
| `adapters` | TEXT_FIELD | — | Adapter sequences or architecture (e.g., Nextera, TruSeq, custom) |
| `multiplex_identifiers` | TEXT_FIELD | — | Barcode scheme: index length, dual vs. single indexing |

---

### Group 7: Sequencing and Bioinformatics

**Group rule:** Any number of fields may be present or absent.

| Field | Type | Controlled values | Extraction guidance |
|---|---|---|---|
| `target_gene` | TEXT_FIELD | — | Gene or locus targeted: 16S rRNA, ITS, 18S rRNA, nifH, amoA |
| `target_subfragment` | TEXT_FIELD | — | Hypervariable region or sub-region: V3-V4, V4, ITS1, ITS2 |
| `sequence_quality_check` | TEXT_CHOICE_FIELD | manual, none, software | How quality filtering was performed |
| `chimera_check_software` | TEXT_FIELD | — | Software and mode: VSEARCH de novo, UCHIME reference-based, DADA2 |
| `relevant_electronic_resources` | TEXT_FIELD | — | Repository accessions, code repositories, supplementary data URLs |
| `relevant_standard_operating_procedures` | TEXT_FIELD | — | Named SOPs or protocol publications cited |
| `annotation_source` | TEXT_FIELD | — | Reference database and version: SILVA 138.1, UNITE, KEGG, UniRef90 |
| `links_to_additional_analysis` | TEXT_FIELD | — | URLs to downstream analysis tools, pipelines, or published companion analyses |

---

### Group 8: Organism / Host Characteristics

**Group rule:** Any number of fields may be present or absent.

| Field | Type | Controlled values | Extraction guidance |
|---|---|---|---|
| `host_scientific_name` | TEXT_FIELD | — | Binomial name with authority if given; look in title, abstract, and methods |
| `taxonomic_classification` | TEXT_FIELD | — | Full taxonomic lineage or named rank assignments for the focal organism |
| `ploidy` | TEXT_FIELD | — | Ploidy level stated or implied by chromosome formula (2n = 6x = 42 implies hexaploid) |
| `number_of_replicons` | TEXT_FIELD | — | Chromosome count; may be inferred from cytogenetic formula |
| `extrachromosomal_elements` | TEXT_FIELD | — | Plasmids, chloroplast or mitochondrial genomes if separately noted |
| `estimated_size` | TEXT_FIELD | — | Genome size in Mb or Gb; may appear in bioinformatics decontamination context |
| `encoded_traits` | TEXT_FIELD | — | Phenotypic traits relevant to study: drought tolerance, disease resistance |
| `subspecific_genetic_lineage` | TEXT_FIELD | — | Genome formula (AABBDD), subspecies, ecotype, or cultivar lineage |
| `propagation` | TEXT_FIELD | — | How the organism reproduces or was propagated for the study |
| `isolation_and_growth_condition` | TEXT_FIELD | — | Growth medium, temperature, and conditions if organism was cultured |
| `reference_for_biomaterial` | TEXT_FIELD | — | Publication or repository where biomaterial is described or deposited |

---

### Group 9: Organism Ecology

**Group rule:** Any number of fields may be present or absent.

| Field | Type | Controlled values | Extraction guidance |
|---|---|---|---|
| `trophic_level` | TEXT_CHOICE_FIELD | autotroph, carboxydotroph, chemoautotroph, chemoheterotroph, chemolithoautotroph, chemolithotroph, chemoorganoheterotroph, chemoorganotroph, chemosynthetic, chemotroph, copiotroph, diazotroph, facultative autotroph, heterotroph, lithoautotroph, lithoheterotroph, lithotroph, methanotroph, methylotroph, mixotroph, obligate chemoautolithotroph, oligotroph, organoheterotroph, organotroph, photoautotroph, photoheterotroph, photolithoautotroph, photolithotroph, photosynthetic, phototroph | Named directly or inferred from metabolic description; multiple values possible |
| `observed_biotic_relationship` | TEXT_CHOICE_FIELD | commensal, free living, mutualism, parasite, symbiont | Stated or inferred from host-microbe interaction description |
| `known_pathogenicity` | TEXT_FIELD | — | Whether the organism is pathogenic; host range if stated |
| `relationship_to_oxygen` | TEXT_CHOICE_FIELD | aerobe, anaerobe, facultative, microaerophilic, microanaerobe, obligate aerobe, obligate anaerobe | Stated directly or inferred from drainage, redox, or community composition context |
| `host_specificity_or_range` | TEXT_FIELD | — | Host range described for a microbial taxon |
| `host_disease_status` | TEXT_FIELD | — | Whether host plant or animal was healthy, diseased, or symptomatic |

---

### Group 10: Experimental Design

**Group rule:** Any number of fields may be present or absent.

| Field | Type | Controlled values | Extraction guidance |
|---|---|---|---|
| `experimental_factor` | TEXT_FIELD | — | Primary experimental variable: elevation gradient, treatment type, genotype, land use |
| `perturbation` | TEXT_FIELD | — | Controlled perturbation applied: drought stress, N addition, tillage, inoculation |
| `negative_control_type` | TEXT_FIELD | — | Type of negative control: extraction blank, sterile buffer, no-template PCR |
| `positive_control_type` | TEXT_FIELD | — | Type of positive control: mock community, reference standard, known strain |

---

## Extraction Strategies

### Strategy 1: Section-to-field prior mapping

Different manuscript sections are probabilistically associated with different field groups.
Use these priors to direct attention, but do not restrict extraction to these zones.

| Section | High-probability fields |
|---|---|
| Title, Abstract | host_scientific_name, broadscale_environmental_context, target_gene, geographic_location_country |
| Introduction | previous_land_use, broadscale_environmental_context, mean_annual_precipitation, experimental_factor |
| Study site / Site description | All geography, elevation, soil_type, drainage, slope, vegetation, climate |
| Materials and Methods | All sample collection, sample processing, pcr_primers, library construction, nucleic_acid_extraction |
| Results | ph, water_content, total_organic_carbon, total_nitrogen, microbial_biomass, library_reads_sequenced |
| Discussion | trophic_level, relationship_to_oxygen, observed_biotic_relationship (inferred contextually) |
| Supplementary | pcr_conditions, adapters, multiplex_identifiers, positive_control_type, negative_control_type |

### Strategy 2: Trigger phrase recognition

Certain phrases reliably introduce field values. Recognise these triggers regardless
of their syntactic position:

| Trigger phrase pattern | Associated field(s) |
|---|---|
| "classified as [soil name]" / "soils are [soil name]" | soil_type |
| "approximately [N]°N, [E]°E" / "coordinates [N, E]" | geographic_location_latitude, geographic_location_longitude |
| "[N] m above [sea level / mean sea level]" | elevation |
| "pH [value]" / "acidity... [descriptor]" / "[ratio] suspension" | ph, ph_method |
| "collected during [stage/season]" / "sampled in [month]" | collection_date |
| "using [device] ([dimensions])" | sample_collection_device |
| "stored at [temperature]" / "flash-frozen in [medium]" | sample_storage_conditions |
| "extracted using [kit]" | nucleic_acid_extraction |
| "amplified using primers [name] / [sequence]" | pcr_primers, target_gene |
| "sequenced on [platform]" / "paired-end [N] bp" | library_construction_method |
| "mean [N] reads per sample" / "average of [N] reads" | library_reads_sequenced |
| "[N] g kg-1" / "[N] % organic carbon" | total_organic_carbon |
| "hexaploid" / "2n = [N]x = [N]" | ploidy, number_of_replicons |
| "negative control" / "extraction blank" | negative_control_type |
| "mock community" / "positive control" | positive_control_type |
| "mutualistic" / "symbiotic" / "parasitic" / "commensal" | observed_biotic_relationship |
| "obligate aerobe" / "facultative" / "microaerophilic" / "anaerobe" | relationship_to_oxygen |
| "diazotroph" / "nitrogen-fixing" / "autotroph" / "heterotroph" | trophic_level |

### Strategy 3: Unit-anchored value extraction

Many quantitative fields are identifiable by their units. When a unit is detected,
walk backwards and forwards in the sentence to recover the associated numeric value
and the measurement type.

| Unit pattern | Likely fields |
|---|---|
| `°C` | temperature, mean_annual_temperature, mean_seasonal_temperature, pcr_conditions |
| `mm` (in climate context) | mean_annual_precipitation, mean_seasonal_precipitation |
| `m` or `m a.s.l.` | elevation, altitude |
| `cm` or `m` (in sampling context) | depth, sample_collection_device dimensions |
| `g kg-1` or `%` (in soil context) | total_organic_carbon, total_nitrogen_content, organic_matter, water_content |
| `µg C g-1` or `nmol g-1` | microbial_biomass |
| `bp` | library_size, pcr_conditions |
| `Gb` or `Mb` | estimated_size |
| `reads per sample` or `sequences per sample` | library_reads_sequenced |

### Strategy 4: Controlled vocabulary matching

For TEXT_CHOICE_FIELD fields, apply fuzzy matching against the controlled vocabulary
before accepting a free-text extraction. Match rules:

- Exact match: accept directly.
- Case-insensitive match: normalise to the schema value.
- Synonym match: apply domain knowledge (e.g., "well-drained" → `well`; "poorly drained" → `poorly`).
- Partial match with high confidence: flag as medium confidence and record both the
  matched term and the original text.
- No match: record the verbatim text as a free-text extraction; do not force a controlled
  value.

For `soil_type`, the full WRB vocabulary is provided in the schema above. Common
alternative expressions to map:

| Manuscript expression | Controlled value |
|---|---|
| "chernozemic" / "chernozem-like" | Chernozem |
| "podzolised" / "spodosol" | Podzol |
| "ferrallitic" / "latosol" | Ferralsol |
| "gleyed" / "hydromorphic" | Gleysol |
| "alluvial" | Fluvisol |
| "peat" / "moor" | Histosol |
| "volcanic" / "andic" | Andosol |

### Strategy 5: Inferred values from ecological context

Some fields are rarely stated directly but can be reliably inferred from surrounding context.
Apply these inference rules with medium confidence.

| Contextual signal | Inferred field and value |
|---|---|
| Dominant taxa are known obligate aerobes and soil is described as well-oxygenated | `relationship_to_oxygen = aerobe` |
| Community described as enriched under waterlogged / anoxic conditions | `relationship_to_oxygen = anaerobe` |
| Taxa described as enriched in root zone vs bulk soil | `observed_biotic_relationship = mutualism` or `symbiont` |
| Carbon fixation, photosynthesis, or light-driven growth described | `trophic_level = photoautotroph` |
| Nitrogen fixation / nifH gene described | `trophic_level = diazotroph` |
| "Moderately well drained" / "moderate drainage" in site description | `drainage_classification = moderately well` |
| Redoximorphic features, mottling, or gleying described | `drainage_classification = poorly` or `somewhat poorly` |
| Oven-drying at 105°C described for water determination | `water_content_method = gravimetric` |
| "IUSS WRB" or "FAO World Reference Base" cited | `soil_taxonomicfao_classification` — note the edition |
| Chickpea-wheat or legume-cereal rotation described | `history/crop_rotation` — record the sequence |

### Strategy 6: Multi-sentence value assembly

Some field values are not contained in a single sentence. Assemble values across
multiple sentences when:

- A measurement is introduced in one sentence and its method is stated in the next.
- A classification is named in one section and its justification appears later.
- Numeric values are distributed across a results table description and a methods protocol.

In these cases, record the assembled value and cite all contributing evidence spans.

### Strategy 7: Negative evidence extraction

Record explicit negations as field values. These are valid data points.

| Negative statement | Extraction |
|---|---|
| "no fungicide seed treatments were applied" | `history/agrochemical_additions = no fungicide applied` |
| "plots were not inoculated with microbial consortia" | `perturbation = none (no inoculation)` |
| "no fire or extreme flood events had affected the plots" | `history/fire = none recorded`; `history/flooding = none in study period` |
| "aluminum toxicity was not a confounding factor" | `extreme_unusual_properties/al_saturation = below phytotoxic threshold` |

---

## Encoding and Text Quality Handling

Scientific PDFs extracted to plain text frequently contain rendering artefacts. Apply
the following normalisation rules before or during extraction.

### Superscript and subscript recovery

PDF text extraction often strips formatting, causing superscripts and subscripts to
appear inline. Recognise these patterns:

| Raw extracted text | Intended value | Field implication |
|---|---|---|
| `g kg-1` or `g kg 1` | g kg⁻¹ | Concentration unit; negative exponent |
| `m s-1` | m s⁻¹ | Velocity unit |
| `CO2` or `CO 2` | CO₂ | Gas identifier |
| `H2O` | H₂O | Water |
| `K2SO4` | K₂SO₄ | Salt in extraction buffer |
| `18.4 g kg<super>-1</super>` | 18.4 g kg⁻¹ | ReportLab markup; strip tags and interpret exponent |
| `2n = 6x = 42` | 2n = 6x = 42 | Chromosome formula; ploidy = hexaploid, n = 42 |
| `5'` followed by sequence | 5′-[sequence]-3′ | Primer orientation |

### Latin-1 / encoding substitution patterns

When documents were generated with Latin-1 constrained fonts (e.g., ReportLab built-in
Helvetica), non-Latin-1 characters may have been substituted. Recognise these patterns:

| Substituted form | Original intended character | Context |
|---|---|---|
| `--` | — (em-dash) or – (en-dash) | Separating value ranges or clauses |
| `-` between city names | – (en-dash) | Geographic range or corridor name |
| `i` in place names | ı (Turkish dotless i) | Place names: Cankiri = Çankırı |
| `>=` | ≥ | Threshold comparisons in methods |
| `5'` | 5′ | Primer notation |
| Black square glyph in PDF | Unsupported Unicode character | Treat preceding word boundary as end of parseable span; attempt value recovery from context |

When a black square or garbled character appears mid-sentence, attempt value recovery
by:
1. Extracting numeric tokens immediately before and after the garbled position.
2. Identifying the measurement context from the surrounding clause.
3. Assigning a low-confidence extraction with a note that the source character was unrenderable.

### Unit normalisation

Extract values as stated in the text. When normalising for comparison or output:
- Preserve the original unit string alongside the numeric value.
- Do not silently convert between unit systems unless explicitly instructed.
- Record ambiguous units (e.g., "%" which could be w/w, w/v, or v/v) with the
  ambiguity flagged.

---

## Output Format

The recommended output structure for extracted metadata is a JSON object keyed by
field name, with each value represented as an object containing the extracted value,
the source evidence, and the confidence level.

```json
{
  "field_name": {
    "value": "extracted string or null",
    "evidence": "verbatim sentence(s) from which value was extracted",
    "confidence": "high | medium | low",
    "section": "section name where evidence appeared",
    "inference_type": "reported | inferred"
  }
}
```

For fields with multiple values (e.g., trophic_level where several guilds are named),
use an array:

```json
{
  "trophic_level": [
    {
      "value": "diazotroph",
      "evidence": "Diazotrophic lineages constituted 9-17% of the functional community...",
      "confidence": "high",
      "section": "Results",
      "inference_type": "reported"
    },
    {
      "value": "photoautotroph",
      "evidence": "...dominated by aerobic photoautotrophic primary colonists...",
      "confidence": "high",
      "section": "Conclusion",
      "inference_type": "reported"
    }
  ]
}
```

For absent fields:

```json
{
  "history/fire": {
    "value": null,
    "evidence": null,
    "confidence": null,
    "section": null,
    "inference_type": null,
    "absence_note": "No mention of fire history in any section."
  }
}
```

---

## Generalisation Guidelines

These rules ensure the extraction logic does not overfit to any single manuscript's
structure or vocabulary.

**Do not assume section names are standard.** Many manuscripts use non-standard section
titles. "Experimental Setup", "Field Campaign", "Sequencing Protocol", and "Genomic Methods"
can all contain sample collection metadata. Scan all sections.

**Do not assume numeric values have units in the same sentence.** Units are sometimes
established at the start of a paragraph and omitted from subsequent values in the same
context ("pH was measured... values ranged from 7.4 to 7.9" — the unit is implicit from
the first sentence).

**Do not require exact method names.** "Soil DNA was extracted using a commercial bead-beating
kit" is sufficient to populate `nucleic_acid_extraction` even without the kit name.
Record what is present; do not penalise for incomplete reporting.

**Recognise that one sentence may populate multiple fields.** "Soils were collected using
a 5 cm diameter corer at 20 cm depth during the grain-filling period in late June and
stored on dry ice" populates `sample_collection_device`, `depth`, `collection_date`, and
`sample_storage_conditions` simultaneously.

**Geographic inference is permissible at low confidence.** If a latitude/longitude is
absent but a named region and country are present, the country field can be populated
at high confidence and a rough coordinate range can be noted at low confidence based on
the named locality.

**Treat supplementary materials as part of the document.** Supplementary notes, tables,
and data availability statements frequently contain the most precise values for sequencing
parameters, primer sequences, and control descriptions. Weight these sections equally
with the main text.
