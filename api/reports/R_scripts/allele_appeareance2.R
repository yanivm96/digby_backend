# Allele appeareance graph - relevantive code

#packages:
library('plyr')
library(optparse)
library('purrr')
library('readxl')
library(stringr)
library("vdjbasevis")
library(reshape2)

pdf(NULL)  # stop spurious Rplots.pdf being produced


option_list = list(
  make_option(c("-i", "--input_file"), type="character", default=NULL,
              help="excel file name", metavar="character"),
  make_option(c("-o", "--output_file"), type="character", default=NULL,
              help="graph.pdf file name", metavar="character"))

opt_parser = OptionParser(option_list=option_list);
opt = parse_args(opt_parser);

if (is.null(opt$input_file)){
  stop("input file must be supplied", call.=FALSE)
}

if (is.null(opt$output_file)){
  stop("output reference file must be supplied", call.=FALSE)
}

######### loading data to data frame (use melt function) #############

# merge
path<-opt$input_file
p_file<-opt$output_file

data_merge<- path %>%
  excel_sheets() %>%
  set_names() %>%
  map(read_excel, path = path)

# reshape list to dataframe
data_merge$id <- rownames(data_merge)
plots_names <- names(data_merge)
alleleAPP(data_merge, file = p_file)
