# The main latex-file
TEXFILE = main

# Fix reference file and compile source
default: full

latencies:
	find data -type d -name "appear.in*" | while read datadir; do target_name=$$(basename $$datadir); echo "Calculating latencies from $$target_name"; ./tools/latexify_latency_csv.py $$datadir/$$target_name-latency.csv > $$datadir/latency.tex; done

bitrates:
	find data -type d -name "appear.in*" | while read datadir; do ./tools/latexify_csv_bitrate_traces.py $$datadir/*-bitrates.csv > $$datadir/bitrate.tex; done

render-data: latencies bitrates

full:
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
