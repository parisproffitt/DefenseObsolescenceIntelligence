"""Foundry locations. Names match the README tables (CLAUDE.md working rules)."""

PROJECT = "/CONTINUUM-edbe5f/Continuum"
RAW = f"{PROJECT}/raw"            # as delivered: messy exports + uploaded notice lists
CLEAN = f"{PROJECT}/clean"        # cleaned, typed, keyed; backs the Ontology
ANALYSIS = f"{PROJECT}/analysis"  # computed: impact cases, flags, COAs, forecast evaluation
ONTOLOGY = f"{PROJECT}/ontology"  # datasets written only by Actions (procurement, reviews)
AIP = f"{PROJECT}/aip"            # AIP extraction runs and their scores (step 4)
