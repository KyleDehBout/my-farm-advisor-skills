<!-- Copyright 2026 Clayton Young (borealBytes / Superior Byte Works, LLC) -->
<!-- Licensed under the Apache License, Version 2.0. -->

---
name: qtl-analysis
description: >
  Example-first QTL analysis toolkit for GWAS, eQTL mapping, classical QTL, structure,
  prediction, and reporting workflows. Uses open-source tools such as tensorQTL, GEMMA,
  PLINK, and R/qtl2 through runnable examples rather than a single command wrapper.
license: Apache-2.0
metadata:
  author: Clayton Young (borealBytes / Superior Byte Works, LLC)
  skill-author: Clayton Young / Superior Byte Works, LLC (@borealBytes)
  contact: Clayton@SuperiorByteWorks.com
  linkedin: https://linkedin.com/in/claytoneyoung/
  version: "1.0.0"
  skill-version: "1.0.0"
  category: genomics
  tools: [tensorQTL, GEMMA, PLINK, R/qtl2, pyQTL]
---

# QTL Analysis

## Overview

This skill is organized around runnable examples. Pick the workflow area that matches the
analysis you want, move into that example directory, and adapt the code, R, or shell steps to
your own dataset.

Use this skill when:
- performing GWAS on inbred lines or natural populations
- mapping cis/trans eQTLs from RNA-seq or expression matrices
- analyzing experimental crosses with classical QTL methods
- checking kinship, population structure, LD, or haplotypes before association testing
- running genomic prediction or marker-assisted breeding workflows
- packaging QTL outputs into reports, ideograms, and breeding decisions

## Tool Selection Guide

| Analysis Type | Primary Tool | When to Use |
| --- | --- | --- |
| eQTL mapping | tensorQTL | GPU-accelerated cis/trans eQTL mapping |
| LMM-GWAS | GEMMA | Mixed-model GWAS with kinship correction |
| GLM-GWAS | PLINK 2 | Fast association tests on large cohorts |
| Classical QTL | R/qtl2 | Experimental crosses, LOD scans, permutations |
| Visualization | pyQTL + matplotlib | Manhattan, QQ, LocusZoom-style plots |
| Population structure | PLINK / numpy workflows | PCA, clustering, admixture, kinship |
| Genomic prediction | sklearn + breeding examples | GBLUP-style baselines and selection workflows |

The example library covers:
- QTL and GWAS mapping workflows
- QC and preprocessing workflows
- Population structure and relatedness workflows
- Prediction and breeding-support workflows
- Reporting and visualization workflows

## Installation

### Step 1: Run System Check

```bash
python scripts/check_system.py
```

### Step 2: Install Dependencies

```bash
bash scripts/install_deps.sh
```

### Optional GPU/HPC Readiness Check

```bash
python scripts/verify_gpu_hpc.py --json
```

Run this before tensorQTL or other CUDA-backed workflows to confirm that PyTorch can see your
NVIDIA GPU and to capture a quick local readiness report.

## How To Use This Skill

```bash
cd examples/mapping/gwas-lmm
python run_gwas.py
```

Most examples follow the same pattern:
1. Move into a workflow example directory.
2. Run the `run_*.py` script.
3. Inspect the generated `output/` artifacts.
4. Adapt the code to your real genotype, phenotype, expression, or map files.

Example outputs are intentionally untracked in this repository. Re-run the example to reproduce
plots, tables, and intermediate artifacts locally.

## Optional Unified CLI

The primary usage model remains example-first, but the remote baseline helper CLI is included for
users who want one entrypoint for common tasks.

```bash
# GWAS helper
python scripts/qtl_cli.py gwas --geno data.bed --pheno traits.csv --method lmm

# eQTL helper
python scripts/qtl_cli.py eqtl --geno genotypes.vcf.gz --expr expression.bed.gz --mode cis

# Classical QTL helper
python scripts/qtl_cli.py lodscan --cross cross.json --perms 1000 --output lod_results/
```

## Workflow Areas

### `qc/`

Use these when validating inputs, filtering markers, checking samples, or visualizing phenotype
distributions before modeling.

- `examples/qc/vcf-validation/`
- `examples/qc/snp-filtering/`
- `examples/qc/phenotype-plots/`
- `examples/qc/sample-qc/`
- `examples/qc/snp-annotation/`
- `examples/qc/imputation/`

### `mapping/`

Use these when running GWAS, eQTL mapping, classical LOD scans, or more advanced association
variants such as multi-trait, interaction, or threshold-adjusted scans.

- `examples/mapping/gwas-lmm/`
- `examples/mapping/gwas-glm/`
- `examples/mapping/eqtl-cis/`
- `examples/mapping/classical-qtl/`
- `examples/mapping/multi-trait-gwas/`
- `examples/mapping/gxe-gwas/`
- `examples/mapping/covariate-gwas/`
- `examples/mapping/threshold-correction/`
- `examples/mapping/genomic-control/`
- `examples/mapping/rare-variant-tests/`
- `examples/mapping/epistasis-scan/`
- `examples/mapping/cnv-integration/`

### `structure/`

Use these when describing population structure, relatedness, haplotypes, LD, or clustering.

- `examples/structure/population-structure/`
- `examples/structure/admixture/`
- `examples/structure/kmeans-clustering/`
- `examples/structure/ld-decay/`
- `examples/structure/haplotype-analysis/`
- `examples/structure/pedigree-kinship/`
- `examples/structure/genomic-nrm/`
- `examples/structure/genetic-similarity/`
- `examples/structure/deep-clustering/`

### `prediction/`

Use these when ranking lines, estimating breeding values, testing prediction models, or showing
breeding-oriented downstream use of marker results.

- `examples/prediction/genomic-prediction/`
- `examples/prediction/marker-selection/`
- `examples/prediction/blup/`
- `examples/prediction/bayesian-gp/`
- `examples/prediction/elastic-net-cv/`
- `examples/prediction/cross-validation/`
- `examples/prediction/gxe-prediction/`
- `examples/prediction/backcross-selection/`

### `reporting/`

Use these when packaging outputs for interpretation, cataloging, or presentation.

- `examples/reporting/qmapper-ideogram/`
- `examples/reporting/analysis-report/`
- `examples/reporting/real-dataset/`

## Foundational Examples

If you only run a few examples first, start here:
- `examples/mapping/gwas-lmm/`
- `examples/mapping/eqtl-cis/`
- `examples/mapping/classical-qtl/`
- `examples/structure/population-structure/`
- `examples/prediction/genomic-prediction/`

## Quality Checklist

After every QTL analysis:

- [ ] Input QC completed (MAF / call-rate / missingness checks)
- [ ] Population structure reviewed before interpreting GWAS peaks
- [ ] Kinship or relatedness method matched to the study design
- [ ] Multiple-testing correction applied and documented
- [ ] Effect direction or top peaks pass a biological plausibility check
- [ ] Random seed, tool versions, and command paths captured for reproducibility

## Input Formats

**Genotypes**
- VCF/VCF.GZ
- PLINK `.bed/.bim/.fam`
- CSV or TSV genotype matrices

**Phenotypes**
- CSV with sample IDs and one or more traits
- PLINK phenotype files

**Expression**
- BED-like gene expression tables
- CSV or TSV matrices with genes as rows and samples as columns

**Cross Data**
- R/qtl2 JSON inputs
- CSV genotype, phenotype, and map tables for conversion into cross-ready inputs

## Common Pitfalls

1. Use QC examples before modeling examples.
2. Check population structure before interpreting GWAS peaks.
3. Match genotype format to the example you are adapting.
4. Keep genetic maps and physical maps distinct in classical QTL workflows.
5. Use the GPU readiness check before expecting tensorQTL acceleration.

## Support Scripts

- `scripts/check_system.py`: environment and dependency check
- `scripts/install_deps.sh`: one-shot installer
- `scripts/qtl_cli.py`: optional remote-baseline helper CLI
- `scripts/generate_all_visualizations.py`: batch output regeneration helper
- `scripts/generate_sample_qtl_data.py`: synthetic data helper
- `scripts/verify_gpu_hpc.py`: GPU readiness helper for tensorQTL-style workloads

## Model Versions & Tools

| Tool | Language | Best For | License |
| --- | --- | --- | --- |
| tensorQTL | Python/GPU | eQTL mapping | BSD-3 |
| GEMMA | C++ | LMM-GWAS | GPL-3 |
| PLINK 2 | C++ | GWAS, PCA, QC | GPL-3 |
| R/qtl2 | R | Classical QTL | GPL-3 |
| pyQTL | Python | Visualization | BSD-3 |
| ADMIXTURE | C++ | Population structure | BSD-3 |

## Resources

- tensorQTL: https://github.com/broadinstitute/tensorqtl
- GEMMA: https://github.com/genetics-statistics/GEMMA
- PLINK: https://www.cog-genomics.org/plink/2.0/
- R/qtl2: https://kbroman.org/qtl2/
- GWAS Catalog: https://www.ebi.ac.uk/gwas/
