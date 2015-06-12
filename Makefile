# The main latex-file
TEXFILE = main

# Fix reference file and compile source
default: latex


all: render-data latex


render-data: latencies bitrates


latencies:
	find data -type d -name "appear.in*" ! -name "*capture*" | while read datadir; do target_name=$$(basename $$datadir); echo "Calculating latencies from $$target_name"; ./tools/latexify_latency_csv.py $$datadir/$$target_name-latency.csv > $$datadir/latency.tex; done
	export SOURCE=appear.in-capture-vanilla-3p; ./tools/latexify_latency_csv.py -f data/$$SOURCE/$$SOURCE.csv > data/$$SOURCE/latency-timer.tex
	export SOURCE=appear.in-capture-vanilla-3p; ./tools/latexify_captured_data_latency.py -s 1434048948 data/$$SOURCE/$$SOURCE.dat > data/$$SOURCE/latency-getstats.tex
	export SOURCE=appear.in-capture-asia; ./tools/latexify_latency_csv.py -f data/$$SOURCE/$$SOURCE.csv > data/$$SOURCE/latency-timer.tex
	export SOURCE=appear.in-capture-asia; ./tools/latexify_captured_data_latency.py -s 1434050117 data/$$SOURCE/$$SOURCE.dat > data/$$SOURCE/latency-getstats.tex


bitrates:
	find data -type d -name "appear.in*" ! -name "*capture*" | while read datadir; do ./tools/latexify_csv_bitrate_traces.py $$datadir/*-bitrates.csv > $$datadir/bitrate.tex; done


latex:
	dot -Teps figs/nodesplitting-post.dot -o figs/nodesplitting-post.eps
	dot -Teps figs/nodesplitting-pre.dot -o figs/nodesplitting-pre.eps
	pdflatex --shell-escape $(TEXFILE) && \
	bibtex $(TEXFILE) && \
	makeglossaries $(TEXFILE) && \
	pdflatex --shell-escape $(TEXFILE) && \
	pdflatex --shell-escape $(TEXFILE) && \
	cp $(TEXFILE).pdf report.pdf


# Removes TeX-output files
clean:
	rm -f *.aux $(TEXFILE).bbl $(TEXFILE).blg *.log *.out $(TEXFILE).toc $(TEXFILE).lot $(TEXFILE).lof $(TEXFILE).glg $(TEXFILE).glo $(TEXFILE).gls $(TEXFILE).ist $(TEXFILE).acn $(TEXFILE).acr $(TEXFILE).alg $(TEXFILE).xdy $(TEXFILE).loa
	find data -type f -name "*.tex" -delete
