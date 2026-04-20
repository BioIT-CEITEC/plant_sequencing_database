"""
Assess whether biological annotation fields can be derived from raw FASTQ sequencing data.

This script analyzes each field from the extracted JSON and classifies it into:
1. Directly Available - Information present in raw FASTQ files
2. Inferable - Can be derived through computational bioinformatics analysis
3. Not Obtainable - Requires external metadata, curated databases, or experimental context
"""

import json
from pathlib import Path


def create_field_assessments():
    """Create comprehensive assessment of each field."""
    
    assessments = {
        "source": "ERC000022.xml extracted fields",
        "sequencing_data": {
            "format": "FASTQ (paired-end)",
            "data_types": ["nucleotide_sequences", "quality_scores", "sequence_identifiers"],
            "accession": "SRR3932411"
        },
        "classification_framework": {
            "Directly_Available": "Information explicitly present in raw FASTQ data",
            "Inferable": "Can be derived through bioinformatics analysis (alignment, assembly, annotation)",
            "Not_Obtainable": "Requires external data, ecological context, literature, or experimental metadata"
        },
        "field_assessments": []
    }
    
    # Field group 1: Organism characteristics: ecosystem
    assessments["field_assessments"].append({
        "group_name": "Organism characteristics: ecosystem",
        "fields": [
            {
                "name": "trophic_level",
                "field_type": "TEXT_CHOICE_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Trophic level (autotroph, heterotroph, etc.) is an ecological/metabolic classification that requires taxonomic identification of organisms and their metabolic capabilities. While taxonomic classification can be inferred through 16S rRNA or whole-genome alignment, assigning trophic level requires curated functional databases or literature review of organism characteristics.",
                "requirements": ["Taxonomic classification", "Functional database lookup (KEGG, IMG)", "Literature review"]
            },
            {
                "name": "observed_biotic_relationship",
                "field_type": "TEXT_CHOICE_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Biotic relationships (commensal, mutualism, parasite) describe ecological interactions between organisms in their natural environment. These require ecological field observations and experimental validation, not derivable from sequence alone.",
                "requirements": ["Field observations", "Ecological experiments", "Environmental metadata"]
            },
            {
                "name": "known_pathogenicity",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Pathogenicity can be partially inferred through taxonomic identification. Known pathogenic species can be identified through alignment against reference genomes. However, specific virulence factors and host-pathogen specificity require functional annotation and literature databases.",
                "requirements": ["Taxonomic classification", "Virulence factor databases (VFDB)", "Reference genome alignment"],
                "limitations": "Only identifies presence of known pathogenic taxa; does not determine host specificity or virulence degree"
            },
            {
                "name": "relationship_to_oxygen",
                "field_type": "TEXT_CHOICE_FIELD",
                "classification": "Inferable",
                "reasoning": "Oxygen requirements can be inferred through taxonomic classification and functional gene analysis. Different organisms show preference for aerobic/anaerobic conditions based on their metabolic pathways (detected through genome/metagenome assembly).",
                "requirements": ["Taxonomic classification", "Functional gene annotation", "Metabolic pathway analysis"],
                "limitations": "Only provides probability based on known organism traits; cannot determine actual conditions experienced by organism"
            },
            {
                "name": "propagation",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Propagation mode (sexual/asexual, lytic/lysogenic for phages) can be inferred for known taxa through taxonomic classification and functional genomics analysis.",
                "requirements": ["Taxonomic identification", "Genome assembly", "Functional annotation"],
                "limitations": "Limited to known organisms with characterized genomes"
            }
        ]
    })
    
    # Field group 2: Sample collection methods
    assessments["field_assessments"].append({
        "group_name": "sample collection: methods, storage and transport",
        "fields": [
            {
                "name": "sample_collection_device",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Collection device is experimental metadata that must be documented during sample collection. No sequencing information reveals how the sample was physically collected.",
                "requirements": ["Laboratory documentation", "Sample metadata records"]
            },
            {
                "name": "sample_collection_method",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Collection method is procedural metadata independent of sequence content.",
                "requirements": ["Experimental protocol documentation"]
            },
            {
                "name": "sample_storage_conditions",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Storage conditions (temperature, duration) are post-collection metadata not encoded in sequences.",
                "requirements": ["Laboratory records"]
            }
        ]
    })
    
    # Field group 3: Local environment conditions - soil
    assessments["field_assessments"].append({
        "group_name": "local environment conditions: soil",
        "fields": [
            {
                "name": "soil_taxonomicfao_classification",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Soil classification requires physical and chemical analysis (texture, mineral composition, pH, organic matter) and expert soil science classification. Sequences alone cannot classify soil.",
                "requirements": ["Soil physics laboratory", "Soil chemistry analysis", "FAO classification expertise"]
            },
            {
                "name": "soil_taxonomiclocal_classification",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Local soil classification requires regional soil science expertise and physical soil analysis.",
                "requirements": ["Regional soil database", "Physical soil analysis"]
            },
            {
                "name": "soil_taxonomiclocal_classification_method",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Documentation of classification method is metadata.",
                "requirements": ["Experimental documentation"]
            },
            {
                "name": "soil_type",
                "field_type": "TEXT_CHOICE_FIELD",
                "classification": "Inferable",
                "reasoning": "Soil type can be partially inferred through microbial community composition analysis. Certain soil types have characteristic microbial signatures (e.g., acidic soils have different communities than alkaline soils). Taxonomic profiling can suggest soil characteristics.",
                "requirements": ["Taxonomic profiling", "Functional metagenomics", "Soil microbiome databases"],
                "limitations": "Inference is probabilistic and requires training datasets; not definitive without laboratory analysis"
            },
            {
                "name": "soil_type_method",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Documentation of method used for soil classification.",
                "requirements": ["Experimental protocol documentation"]
            },
            {
                "name": "soil_texture_measurement",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Soil texture (sand, silt, clay ratios) can be partially inferred through microbial community composition. Different soil textures have distinct microbial communities and functional potentials.",
                "requirements": ["Metagenomic profiling", "Microbial ecology databases"],
                "limitations": "Probabilistic inference only; requires calibration against reference soils"
            },
            {
                "name": "soil_texture_method",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Protocol documentation.",
                "requirements": ["Experimental records"]
            }
        ]
    })
    
    # Field group 4: Sample collection - core sample properties
    assessments["field_assessments"].append({
        "group_name": "sample collection: core sample properties",
        "fields": [
            {
                "name": "microbial_biomass",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Microbial biomass can be estimated from sequencing depth and read abundance when normalized by known reference genomes or through absolute quantification markers (e.g., 16S copy number). However, this requires additional quantitative information beyond sequence alone.",
                "requirements": ["Sequencing depth metadata", "Reference database", "Quantitative PCR data (if available)"],
                "limitations": "Estimation is relative without absolute quantification data"
            }
        ]
    })
    
    # Field group 5: Non-sample terms - study/project
    assessments["field_assessments"].append({
        "group_name": "non-sample terms: study or project",
        "fields": [
            {
                "name": "project_name",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Project accession (PRJNA309843, SRP069062) is available in the ENA record and FASTQ file headers.",
                "source": "FASTQ header, ENA metadata"
            }
        ]
    })
    
    # Field group 6: Non-sample terms (genetic)
    assessments["field_assessments"].append({
        "group_name": "non-sample terms",
        "fields": [
            {
                "name": "ploidy",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Ploidy level can be inferred for isolated organisms through genome assembly depth analysis and k-mer distribution. For mixed communities (metagenomics), ploidy is not directly determinable.",
                "requirements": ["Genome assembly", "Depth-of-coverage analysis", "k-mer frequency distribution"],
                "limitations": "Applicable mainly to pure cultures; difficult for mixed communities"
            },
            {
                "name": "number_of_replicons",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Number of replicons can be determined through genome assembly. Different replicon types (chromosomes, plasmids) are identifiable through assembly graphs and structural analysis.",
                "requirements": ["Complete genome assembly", "Graph-based assembly analysis"]
            },
            {
                "name": "extrachromosomal_elements",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Plasmids and other extrachromosomal elements can be identified through assembly and their characteristic sequence signatures (different GC content, repeated elements).",
                "requirements": ["Genome assembly", "Structural analysis"]
            },
            {
                "name": "estimated_size",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Genome size can be estimated from k-mer frequency distribution (for single genomes) or from sequencing depth and total reads.",
                "requirements": ["k-mer analysis", "Coverage information"],
                "note": "For metagenomes, only total DNA size can be estimated, not individual organism genomes"
            },
            {
                "name": "target_gene",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "If targeting specific genes (e.g., 16S rRNA, 18S rRNA marker genes), the target is documented in the sequencing strategy metadata.",
                "source": "ENA metadata, SRA submission details"
            },
            {
                "name": "target_subfragment",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "The specific subfragment (e.g., V4 region of 16S rRNA) is usually specified in the experimental design and ENA metadata.",
                "source": "ENA metadata"
            },
            {
                "name": "multiplex_identifiers",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Barcodes/MIDs are present in FASTQ header lines and demultiplexing files.",
                "source": "FASTQ headers"
            },
            {
                "name": "sequence_quality_check",
                "field_type": "TEXT_CHOICE_FIELD",
                "classification": "Directly Available",
                "reasoning": "Quality information is present in FASTQ files (Phred scores). Quality assessment results may be available in SRA metadata.",
                "source": "FASTQ quality scores, ENA/SRA records"
            },
            {
                "name": "chimera_check_software",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Chimera detection requires analysis with software tools. The presence of chimeric sequences can be determined, but the specific software used depends on analysis workflow.",
                "requirements": ["UCHIME, VSEARCH, or similar tools"],
                "note": "Can be applied to data, but which tool was used originally may not be recorded"
            },
            {
                "name": "relevant_electronic_resources",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "References, DOIs, and URLs are available in ENA/SRA submission records and run metadata.",
                "source": "ENA metadata, publication data"
            },
            {
                "name": "relevant_standard_operating_procedures",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "SOPs may be referenced in the ENA submission or project metadata.",
                "source": "ENA metadata, project documentation"
            }
        ]
    })
    
    # Field group 7: Collection event information
    assessments["field_assessments"].append({
        "group_name": "Collection event information",
        "fields": [
            {
                "name": "collection_date",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Collection date is recorded in ENA metadata and SRA run information.",
                "source": "ENA/SRA metadata"
            },
            {
                "name": "altitude",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Altitude/elevation is often included in ENA submission metadata.",
                "source": "ENA metadata"
            },
            {
                "name": "geographic_location_latitude",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Geographic coordinates are recorded in ENA metadata.",
                "source": "ENA metadata"
            },
            {
                "name": "geographic_location_longitude",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Geographic coordinates are recorded in ENA metadata.",
                "source": "ENA metadata"
            },
            {
                "name": "geographic_location_region_and_locality",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Location information is in ENA metadata.",
                "source": "ENA metadata"
            },
            {
                "name": "broadscale_environmental_context",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Environmental context (biome, ecosystem type) is described in ENA metadata and sample information.",
                "source": "ENA metadata"
            },
            {
                "name": "local_environmental_context",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Local environmental context can be inferred from microbial community composition. Specific taxa indicate local environmental conditions (e.g., presence of particular plant-associated bacteria suggests proximity to plants).",
                "requirements": ["Taxonomic profiling", "Ecological databases"],
                "limitations": "Inference is probabilistic and indirect"
            },
            {
                "name": "environmental_medium",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "The environmental medium (soil, water, host, etc.) is specified in ENA metadata.",
                "source": "ENA metadata, sample_type field"
            },
            {
                "name": "elevation",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Elevation data is in ENA metadata.",
                "source": "ENA metadata"
            }
        ]
    })
    
    # Field group 8: Sample collection
    assessments["field_assessments"].append({
        "group_name": "sample collection",
        "fields": [
            {
                "name": "amount_or_size_of_sample_collected",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Sample size information is typically recorded in ENA metadata.",
                "source": "ENA metadata"
            },
            {
                "name": "sieving",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Sieving size and method are procedural documentation not derivable from sequences.",
                "requirements": ["Experimental protocol documentation"]
            },
            {
                "name": "microbial_biomass_method",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "The method used for biomass determination is procedural documentation.",
                "requirements": ["Experimental protocol documentation"]
            },
            {
                "name": "horizon_method",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Soil horizon identification method is procedural documentation.",
                "requirements": ["Experimental protocol documentation"]
            }
        ]
    })
    
    # Field group 9: Unusual properties
    assessments["field_assessments"].append({
        "group_name": "unusual properties",
        "fields": [
            {
                "name": "extreme_unusual_propertiesheavy_metals",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Presence of heavy metals can be inferred from the presence of heavy metal-resistant organisms (identified through taxonomy) and heavy metal resistance genes.",
                "requirements": ["Taxonomic profiling", "Functional gene annotation", "Heavy metal resistance databases"],
                "limitations": "Only indicates presence of resistance; does not quantify heavy metal concentrations"
            },
            {
                "name": "extreme_unusual_propertiesheavy_metals_method",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Analytical method documentation.",
                "requirements": ["Experimental records"]
            },
            {
                "name": "extreme_unusual_propertiesal_saturation",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Aluminum saturation requires chemical analysis, not derivable from sequences.",
                "requirements": ["Chemical analysis laboratory"]
            },
            {
                "name": "extreme_unusual_propertiesal_saturation_method",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Analytical method documentation.",
                "requirements": ["Experimental records"]
            }
        ]
    })
    
    # Field group 10: Organism characteristics (geographic)
    assessments["field_assessments"].append({
        "group_name": "Organism characteristics (geographic location)",
        "fields": [
            {
                "name": "geographic_location_country_andor_sea",
                "field_type": "TEXT_CHOICE_FIELD",
                "classification": "Directly Available",
                "reasoning": "Country/location is specified in ENA metadata.",
                "source": "ENA metadata"
            }
        ]
    })
    
    # Field group 11: Host disorder
    assessments["field_assessments"].append({
        "group_name": "host disorder",
        "fields": [
            {
                "name": "host_disease_status",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "For human-associated samples, disease status can be partially inferred from presence of pathogenic organisms or disease-associated microbial biomarkers. However, definitive diagnosis requires clinical metadata.",
                "requirements": ["Pathogen detection", "Disease biomarker databases", "Clinical metadata"],
                "limitations": "Can only identify presence of known pathogens; cannot diagnose complex diseases"
            }
        ]
    })
    
    # Field group 12: Host description
    assessments["field_assessments"].append({
        "group_name": "host description",
        "fields": [
            {
                "name": "host_scientific_name",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Host organism information is documented in ENA metadata when applicable.",
                "source": "ENA metadata"
            }
        ]
    })
    
    # Field group 13: Links
    assessments["field_assessments"].append({
        "group_name": "link",
        "fields": [
            {
                "name": "link_to_climate_information",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Climate information links are provided in ENA metadata or associated publications.",
                "source": "ENA metadata, project documentation"
            },
            {
                "name": "link_to_classification_information",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Classification references are in ENA metadata.",
                "source": "ENA metadata"
            },
            {
                "name": "links_to_additional_analysis",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Additional analysis results are often linked in ENA records or supplementary data.",
                "source": "ENA metadata, supplementary databases"
            }
        ]
    })
    
    # Field group 14: Local environment conditions (detailed)
    assessments["field_assessments"].append({
        "group_name": "local environment conditions",
        "fields": [
            {
                "name": "current_land_use",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Land use information is documented in ENA metadata.",
                "source": "ENA metadata"
            },
            {
                "name": "current_vegetation",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Vegetation type can be inferred from plant-associated microbial communities. Presence of plant-specific microbes and fungal communities indicates vegetation type.",
                "requirements": ["Taxonomic profiling", "Plant microbiome databases", "Fungal community analysis"],
                "limitations": "Probabilistic inference; requires training data"
            },
            {
                "name": "current_vegetation_method",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Methodology documentation.",
                "requirements": ["Experimental records"]
            },
            {
                "name": "soil_horizon",
                "field_type": "TEXT_CHOICE_FIELD",
                "classification": "Inferable",
                "reasoning": "Soil horizon can be partially inferred from microbial community depth profiles. Different soil horizons have distinct microbial communities (O, A, E, B, R layers have different communities).",
                "requirements": ["Depth-resolved microbial profiling", "Soil microbiome training data"],
                "limitations": "Requires depth information in samples; only probabilistic"
            },
            {
                "name": "drainage_classification",
                "field_type": "TEXT_CHOICE_FIELD",
                "classification": "Inferable",
                "reasoning": "Drainage class (well-drained, poorly drained) can be inferred from anaerobic/aerobic microbial community composition. Poor drainage shows anaerobic indicators; well-drained shows aerobic indicators.",
                "requirements": ["Functional gene analysis", "Anaerobic/aerobic biomarkers"],
                "limitations": "Inference based on microbial metabolic potential, not direct measurement"
            },
            {
                "name": "temperature",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Temperature at time of sampling is often recorded in ENA metadata or field notes.",
                "source": "ENA metadata"
            },
            {
                "name": "ph",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "pH can be inferred from microbial community composition. Different microbes prefer different pH ranges (acidophiles vs. alkaliphiles, neutrophiles). Community structure indicates probable pH range.",
                "requirements": ["Taxonomic profiling", "pH preference databases"],
                "limitations": "Estimation only; requires calibration against reference samples"
            },
            {
                "name": "ph_method",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Methodology documentation.",
                "requirements": ["Experimental records"]
            },
            {
                "name": "water_content",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Soil water content can be partially inferred from microbial community composition. Wet soils show different microbial signatures than dry soils.",
                "requirements": ["Functional gene profiling", "Moisture-responsive biomarkers"],
                "limitations": "Rough estimation only"
            },
            {
                "name": "slope_gradient",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Slope is a physical geographic parameter not encodable in sequences.",
                "requirements": ["Geographic survey", "Topographic data"]
            },
            {
                "name": "slope_aspect",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Directional aspect is a geographic parameter not encodable in sequences.",
                "requirements": ["Geographic survey"]
            },
            {
                "name": "profile_position",
                "field_type": "TEXT_CHOICE_FIELD",
                "classification": "Inferable",
                "reasoning": "Position in soil profile (summit, shoulder, backslope, toeslope) can be inferred from microbial community composition, which varies with soil age and water movement patterns.",
                "requirements": ["Depth-resolved profiling", "Slope position biomarkers"],
                "limitations": "Requires depth information; probabilistic inference"
            }
        ]
    })
    
    # Field group 15: Concentration measurement
    assessments["field_assessments"].append({
        "group_name": "concentration measurement",
        "fields": [
            {
                "name": "water_content_method",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Analytical method documentation.",
                "requirements": ["Experimental records"]
            },
            {
                "name": "total_organic_carbon_method",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Methodology documentation.",
                "requirements": ["Experimental records"]
            },
            {
                "name": "total_nitrogen_content_method",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Analytical method documentation.",
                "requirements": ["Experimental records"]
            },
            {
                "name": "organic_matter",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Organic matter content can be inferred from microbial biomass and metabolic potential. High organic matter correlates with certain microbial communities specialized in organic matter decomposition.",
                "requirements": ["Microbial profiling", "Decomposer biomarkers", "Metagenomic functional analysis"],
                "limitations": "Rough estimation; requires calibration"
            },
            {
                "name": "organic_nitrogen",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Organic nitrogen can be inferred from presence of nitrogen-cycling organisms (nitrogen fixers, nitrifiers, denitrifiers).",
                "requirements": ["Functional gene analysis", "Nitrogen cycling biomarkers"],
                "limitations": "Presence/absence indication only; not quantitative"
            },
            {
                "name": "total_organic_carbon",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Total organic carbon can be estimated from microbial community composition and functional gene abundance related to carbon cycling.",
                "requirements": ["Metagenomics", "Carbon cycling pathway analysis"],
                "limitations": "Rough estimation; requires reference data"
            },
            {
                "name": "total_nitrogen_content",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Total nitrogen indicated by nitrogen-cycling gene abundance and nitrogen-fixing organism presence.",
                "requirements": ["Functional gene profiling", "nifH abundance"],
                "limitations": "Qualitative indication only"
            },
            {
                "name": "salinity_method",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Analytical method documentation.",
                "requirements": ["Experimental records"]
            }
        ]
    })
    
    # Field group 16: Pointer to physical material
    assessments["field_assessments"].append({
        "group_name": "Pointer to physical material",
        "fields": [
            {
                "name": "source_material_identifiers",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Material sample identifiers are in ENA metadata and run information.",
                "source": "ENA metadata, biosample_id"
            }
        ]
    })
    
    # Field group 17: Local environment history
    assessments["field_assessments"].append({
        "group_name": "local environment history",
        "fields": [
            {
                "name": "historyprevious_land_use",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Historical land use requires documentary evidence, not derivable from current sequencing.",
                "requirements": ["Historical records", "Land use maps", "Literature"]
            },
            {
                "name": "previous_land_use_method",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Methodology documentation.",
                "requirements": ["Historical documentation"]
            },
            {
                "name": "historycrop_rotation",
                "field_type": "TEXT_FIELD",
                "classification": "Not Obtainable",
                "reasoning": "Crop rotation history requires agricultural records.",
                "requirements": ["Farm records", "Agricultural documentation"]
            },
            {
                "name": "historyagrochemical_additions",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Agricultural chemical history can be partially inferred from presence of antibiotic-resistant bacteria, pesticide-degrading genes, or pollutant-adapted organisms.",
                "requirements": ["Antibiotic resistance profiling", "Functional gene analysis", "Chemical resistance databases"],
                "limitations": "Can only detect legacy effects; cannot reconstruct specific compounds or timing"
            },
            {
                "name": "historytillage",
                "field_type": "TEXT_CHOICE_FIELD",
                "classification": "Inferable",
                "reasoning": "Tillage history can be inferred from soil structure indicators reflected in microbial community differences. No-till soils have different microbial communities than tilled soils.",
                "requirements": ["Microbial profiling", "Soil management biomarkers"],
                "limitations": "Probabilistic inference; requires reference communities"
            },
            {
                "name": "historyfire",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Fire history can be inferred from presence of thermophilic organisms and fire-adapted microbial communities.",
                "requirements": ["Thermophile profiling", "Fire-adapted biomarkers"],
                "limitations": "Recent fires only; not for ancient burn history"
            },
            {
                "name": "historyflooding",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Flooding history can be inferred from anaerobic biomarkers and flood-tolerant organism presence.",
                "requirements": ["Anaerobic biomarker analysis"],
                "limitations": "Can only detect recent flooding effects"
            },
            {
                "name": "historyextreme_events",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Some extreme events (drought, contamination) leave microbial signatures detectable through community analysis.",
                "requirements": ["Comparative metagenomics", "Stress-response biomarkers"],
                "limitations": "Limited to events leaving microbial traces; many events undetectable"
            },
            {
                "name": "mean_seasonal_temperature",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Mean seasonal temperature can be inferred from thermophile/psychrophile abundance and seasonally active microbial groups.",
                "requirements": ["Seasonal sampling", "Temperature-adapted organism profiles"],
                "limitations": "Rough estimation; requires temporal data"
            },
            {
                "name": "mean_seasonal_precipitation",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Precipitation patterns can be inferred from moisture-adapted microbial communities and fungal indicators.",
                "requirements": ["Fungal/bacterial moisture indicators"],
                "limitations": "Rough inference; requires training data"
            },
            {
                "name": "mean_annual_precipitation",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Annual precipitation data for the sampling location may be in ENA metadata or available from climate databases linked to geographic coordinates.",
                "source": "ENA metadata, climate database lookup"
            },
            {
                "name": "mean_annual_temperature",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Annual temperature data for location is available in climate databases indexed by geographic coordinates.",
                "source": "Climate database lookup (NOAA, WorldClim)"
            }
        ]
    })
    
    # Field group 18: Host details
    assessments["field_assessments"].append({
        "group_name": "host details",
        "fields": [
            {
                "name": "host_specificity_or_range",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Host specificity can be partially inferred through taxonomic identification of the organism and literature on known host associations. However, determining specificity requires experimental data.",
                "requirements": ["Taxonomic classification", "Host-pathogen databases (ViPR, Pathosystems)"],
                "limitations": "Can only identify known host associations; cannot determine novel specificities"
            }
        ]
    })
    
    # Field group 19: Treatment
    assessments["field_assessments"].append({
        "group_name": "treatment",
        "fields": [
            {
                "name": "perturbation",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Type of perturbation (chemical, physical, biological) can be inferred from presence of perturbation-response biomarkers or stress-adapted organisms. However, specific details require experimental documentation.",
                "requirements": ["Stress response gene analysis", "Biomarker profiles"],
                "limitations": "Can identify presence of stress; cannot reliably determine specific perturbation type or timing"
            }
        ]
    })
    
    # Field group 20: Experimental factor and block
    assessments["field_assessments"].append({
        "group_name": "experimental factor and block",
        "fields": [
            {
                "name": "negative_control_type",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Control sample type information is in ENA metadata.",
                "source": "ENA metadata, sample_type field"
            },
            {
                "name": "positive_control_type",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Positive control information is in ENA metadata.",
                "source": "ENA metadata"
            },
            {
                "name": "experimental_factor",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Experimental design and factors are documented in ENA submission metadata.",
                "source": "ENA metadata, study design"
            }
        ]
    })
    
    # Field group 21: Organism characteristics - genetic
    assessments["field_assessments"].append({
        "group_name": "Organism characteristics: genetic",
        "fields": [
            {
                "name": "encoded_traits",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Encoded traits (antibiotic resistance, virulence factors, metabolic capabilities) can be inferred through functional gene annotation and presence/absence of known trait-encoding genes.",
                "requirements": ["Genome assembly", "Functional annotation databases (KEGG, EggNOG, Virulence Factor DB)"],
                "limitations": "Only identifies known traits; cannot predict novel traits"
            },
            {
                "name": "subspecific_genetic_lineage",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Subspecific lineage (biovar, serovar, strain type) can be determined through multilocus sequence typing (MLST), whole genome SNP analysis, or 16S rRNA DGGE patterns.",
                "requirements": ["MLST analysis", "SNP profiling", "Reference genome comparison"],
                "limitations": "Limited to known lineages with sequence databases"
            },
            {
                "name": "taxonomic_classification",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Taxonomic classification is a primary output of sequence analysis. Taxonomy can be determined through 16S rRNA sequence comparison, whole-genome alignment, or metagenomic profiling.",
                "requirements": ["Reference database comparison (RDP, Silva, Greengenes, NCBI)", "Alignment/phylogenetic tools"],
                "note": "One of the most reliable inferences from sequencing data"
            }
        ]
    })
    
    # Field group 22: Reference
    assessments["field_assessments"].append({
        "group_name": "Reference",
        "fields": [
            {
                "name": "isolation_and_growth_condition",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Growth conditions are often documented in ENA metadata and associated publications.",
                "source": "ENA metadata, publication data"
            },
            {
                "name": "annotation_source",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Annotation source (e.g., JGI, NCBI, IMG) is documented in ENA records or genome annotation metadata.",
                "source": "ENA metadata, annotation database records"
            },
            {
                "name": "reference_for_biomaterial",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Primary reference for the biomaterial is documented in ENA submission records and publications.",
                "source": "ENA metadata, primary publication"
            }
        ]
    })
    
    # Field group 23: Sample processing
    assessments["field_assessments"].append({
        "group_name": "sample processing",
        "fields": [
            {
                "name": "sample_pooling",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Sample pooling information is documented in ENA metadata and library preparation notes.",
                "source": "ENA metadata, library_strategy field"
            },
            {
                "name": "sample_material_processing",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Sample processing procedures are documented in ENA submission and protocol information.",
                "source": "ENA metadata, study documentation"
            },
            {
                "name": "sample_volume_or_weight_for_dna_extraction",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Sample volume/weight for extraction is often in ENA metadata.",
                "source": "ENA metadata"
            },
            {
                "name": "nucleic_acid_extraction",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Extraction protocol is documented in ENA submission and methods.",
                "source": "ENA metadata, protocol documentation"
            },
            {
                "name": "nucleic_acid_amplification",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Amplification protocol (if applicable) is in ENA metadata.",
                "source": "ENA metadata, PCR conditions"
            },
            {
                "name": "library_size",
                "field_type": "TEXT_FIELD",
                "classification": "Inferable",
                "reasoning": "Library size can be estimated from FASTQ file size and read length, or is documented in ENA metadata.",
                "source": "ENA metadata, read count"
            },
            {
                "name": "library_reads_sequenced",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Total number of reads is directly available from FASTQ files and ENA metadata.",
                "source": "FASTQ file, ENA metadata"
            },
            {
                "name": "library_construction_method",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Library construction method is documented in ENA metadata.",
                "source": "ENA metadata, library_construction_protocol"
            },
            {
                "name": "library_vector",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Vector information is in ENA metadata if cloning was used.",
                "source": "ENA metadata"
            },
            {
                "name": "library_screening_strategy",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Screening strategy is documented in ENA metadata.",
                "source": "ENA metadata"
            },
            {
                "name": "pcr_conditions",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "PCR conditions are documented in ENA metadata and methods.",
                "source": "ENA metadata"
            },
            {
                "name": "pcr_primers",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Primer sequences are in ENA metadata and methods section.",
                "source": "ENA metadata, primer sequences"
            },
            {
                "name": "adapters",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Adapter sequences are documented in ENA submission and library prep information.",
                "source": "ENA metadata, sequencing adapter info"
            }
        ]
    })
    
    # Field group 24: Environmental information
    assessments["field_assessments"].append({
        "group_name": "Environmental information",
        "fields": [
            {
                "name": "depth",
                "field_type": "TEXT_FIELD",
                "classification": "Directly Available",
                "reasoning": "Sampling depth is documented in ENA metadata and geographic information.",
                "source": "ENA metadata"
            }
        ]
    })
    
    return assessments


def main():
    """Generate and save assessment report."""
    assessment_data = create_field_assessments()
    
    output_file = Path(__file__).parent / "field_derivability_assessment.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(assessment_data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("Field Derivability Assessment Report")
    print("=" * 80)
    
    total_fields = 0
    directly_available = 0
    inferable = 0
    not_obtainable = 0
    
    for fg in assessment_data["field_assessments"]:
        for field in fg["fields"]:
            total_fields += 1
            classification = field["classification"]
            if classification == "Directly Available":
                directly_available += 1
            elif classification == "Inferable":
                inferable += 1
            else:
                not_obtainable += 1
    
    print(f"\nTotal Fields Analyzed: {total_fields}")
    print(f"\nClassification Summary:")
    print(f"  Directly Available:  {directly_available:3d} ({100*directly_available/total_fields:.1f}%)")
    print(f"  Inferable:           {inferable:3d} ({100*inferable/total_fields:.1f}%)")
    print(f"  Not Obtainable:      {not_obtainable:3d} ({100*not_obtainable/total_fields:.1f}%)")
    
    print(f"\n✓ Detailed assessment saved to: {output_file}")


if __name__ == "__main__":
    main()
