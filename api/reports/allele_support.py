# Allele support report

from werkzeug.exceptions import BadRequest
from api.reports.reports import SYSDATA, run_rscript, send_report
from api.reports.report_utils import make_output_file, chunk_list
from app import app, vdjbase_dbs, genomic_dbs
from db.vdjbase_model import HaplotypesFile, SamplesHaplotype, AllelesSample, Gene, Allele
from db.vdjbase_airr_model import Sample, Patient
from db.genomic_db import Sequence as GenomicSequence, Subject as GenomicSubject, SubjectSequence as GenomicSubjectSequence, Gene as GenomicGene
from receptor_utils.simple_bio_seq import write_csv
import os
from api.vdjbase.vdjbase import VDJBASE_SAMPLE_PATH, apply_rep_filter_params
import xlwt

APPEARANCE_SCRIPT = 'allele_appeareance2.R'
SAMPLE_CHUNKS = 400

def run(format, species, genomic_datasets, genomic_samples, rep_datasets, rep_samples, params):
    if format != 'xls':
        raise BadRequest('Invalid format requested')

    rep_samples_by_dataset = {}
    for rep_sample in rep_samples:
        if rep_sample['dataset'] not in rep_samples_by_dataset:
            rep_samples_by_dataset[rep_sample['dataset']] = []
        rep_samples_by_dataset[rep_sample['dataset']].append(rep_sample['sample_name'])

    imgt_refs = {}
    gene_order = {}

    for dataset in rep_samples_by_dataset.keys():
        session = vdjbase_dbs[species][dataset].session

        refs = session.query(Allele).filter(Allele.novel==0).all()

        for ref in refs:
            if ref.name not in imgt_refs:
                imgt_refs[ref.name] = ref.seq.replace('.', '')

        genes = session.query(Gene).filter(Gene.pseudo_gene==0).all()

        for gene in genes:
            if gene.name not in gene_order:
                gene_order[gene.name] = gene.locus_order

    rep_counts = {}

    for dataset in rep_samples_by_dataset.keys():
        appearances = []

        for sample_chunk in chunk_list(rep_samples_by_dataset[dataset], SAMPLE_CHUNKS):
            sample_list = session.query(Sample.sample_name).filter(Sample.sample_name.in_(sample_chunk)).all()
            sample_list = [s[0] for s in sample_list]

            app_query = session.query(AllelesSample.patient_id, Gene.name, Allele.name, Sample.sample_name, Patient.patient_name)\
                                .filter(Sample.id == AllelesSample.sample_id)\
                                .filter(Allele.id == AllelesSample.allele_id)\
                                .filter(Gene.id == Allele.gene_id)\
                                .filter(Patient.id == AllelesSample.patient_id)\
                                .filter(Sample.sample_name.in_(sample_list))

            appearances.extend(app_query.all())

        for app in appearances:
            pid, gene, allele, sample, patient_name = app
            allele = allele.split('*', 1)[1].upper()
            if gene not in rep_counts:
                rep_counts[gene] = [{}, []]
            if allele not in rep_counts[gene][0]:
                rep_counts[gene][0][allele] = []
            if pid not in rep_counts[gene][0][allele]:
                rep_counts[gene][0][allele].append(patient_name)
            if pid not in rep_counts[gene][1]:
                rep_counts[gene][1].append(patient_name)

        gen_samples_by_dataset = {}
        for gen_sample in genomic_samples:
            if gen_sample['dataset'] not in gen_samples_by_dataset:
                gen_samples_by_dataset[gen_sample['dataset']] = []
            gen_samples_by_dataset[gen_sample['dataset']].append(gen_sample['identifier'])

        for dataset in gen_samples_by_dataset.keys():
            session = genomic_dbs[species][dataset].session

            refs = session.query(GenomicSequence).filter(GenomicSequence.novel == 0).all()

            for ref in refs:
                if ref.name not in imgt_refs:
                    imgt_refs[ref.name] = ref.sequence.replace('.', '')

            genes = session.query(GenomicGene).filter(GenomicGene.pseudo_gene==0).all()

            for gene in genes:
                if gene.name not in gene_order:
                    gene_order[gene.name] = gene.locus_order

        gen_counts = {}

        for dataset in gen_samples_by_dataset.keys():
            appearances = []

            for sample_chunk in chunk_list(gen_samples_by_dataset[dataset], SAMPLE_CHUNKS):
                sample_list = session.query(GenomicSubject.identifier).filter(GenomicSubject.identifier.in_(sample_chunk)).all()
                sample_list = [s[0] for s in sample_list]

                app_query = session.query(GenomicSubject.id, GenomicSequence.gene, GenomicSequence.name, GenomicSubject.identifier) \
                    .filter(GenomicSubject.id == GenomicSubjectSequence.subject_id) \
                    .filter(GenomicSequence.id == GenomicSubjectSequence.sequence_id) \
                    .filter(GenomicSequence.type.in_(['V-REGION', 'D-REGION', 'J-REGION'])) \
                    .filter(GenomicSubject.identifier.in_(sample_list))

                appearances.extend(app_query.all())

            for app in appearances:
                pid, gene, allele, patient_name = app
                allele = allele.split('*', 1)[1].upper()
                if gene not in gen_counts:
                    gen_counts[gene] = [{}, []]
                if allele not in gen_counts[gene][0]:
                    gen_counts[gene][0][allele] = []
                if pid not in gen_counts[gene][0][allele]:
                    gen_counts[gene][0][allele].append(patient_name)
                if pid not in gen_counts[gene][1]:
                    gen_counts[gene][1].append(patient_name)

        imgt_counts = {}

        for ref in imgt_refs.keys():
            ref = ref.upper()
            gene, allele = ref.split('*')
            if gene not in imgt_counts:
                imgt_counts[gene] = [{}, [1]]
            if allele not in imgt_counts[gene][0] and allele != 'DEL':
                imgt_counts[gene][0][allele] = [1]

        headers = ['Allele', 'IMGT', 'AIRR-Seq', 'Genomic']

        genes_in_order = sorted(gene_order.items(), key=lambda x: x[1], reverse=True)
        genes_in_order = [g[0] for g in genes_in_order]

        results = []

        for gene in genes_in_order:
            # Assemble the set of alleles to list for this gene
            ref_alleles = []
            novel_alleles = []

            for counts in [imgt_counts, rep_counts, gen_counts]:
                if gene in counts:
                    for allele in counts[gene][0].keys():
                        if '_' in allele:
                            if allele not in novel_alleles:
                                novel_alleles.append(allele)
                        else:
                            if allele not in ref_alleles:
                                ref_alleles.append(allele)

            ref_alleles.sort()
            novel_alleles.sort()

            ref_alleles.extend(novel_alleles)

            def allele_count(gene, allele, counts):
                if gene not in counts:
                    return 0
                if allele not in counts[gene][0]:
                    return 0
                return len(counts[gene][0][allele])

            for allele in ref_alleles:
                row = {
                    'Allele': f'{gene}*{allele}',
                    'IMGT': allele_count(gene, allele, imgt_counts),
                    'AIRR-Seq': allele_count(gene, allele, rep_counts),
                    'Genomic': allele_count(gene, allele, gen_counts),

                }
                results.append(row)

        output_path = make_output_file('csv')
        write_csv(output_path, results)
        return send_report(output_path, 'csv', f'{species}_allele_usage.csv')


