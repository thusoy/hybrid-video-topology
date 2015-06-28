# The main latex-file
TEXFILE = main

# Fix reference file and compile source
default: latex


all: render-data latex


render-data: latencies bitrates captured-latencies captured-bitrates graphviz inkscape-illustrations utilization script-runtimes


latencies:
	find data -type d -name "appear.in*" ! -name "*capture*" ! -name "*final*" | while read datadir; do target_name=$$(basename $$datadir); echo "Calculating latencies from $$target_name"; ./tools/latexify_latency_csv.py $$datadir/$$target_name-latency.csv > $$datadir/latency.tex; done
	export SOURCE=appear.in-capture-vanilla-3p; ./tools/latexify_latency_csv.py -f data/$$SOURCE/$$SOURCE.csv > data/$$SOURCE/latency-timer.tex
	export SOURCE=appear.in-capture-vanilla-3p; ./tools/latexify_captured_data_latency.py -s 1434048948 data/$$SOURCE/$$SOURCE.dat > data/$$SOURCE/latency-getstats.tex
	export SOURCE=appear.in-capture-traveller; ./tools/latexify_latency_csv.py -f data/$$SOURCE/$$SOURCE.csv > data/$$SOURCE/latency-timer.tex
	export SOURCE=appear.in-capture-traveller; ./tools/latexify_captured_data_latency.py -s 1434050117 data/$$SOURCE/$$SOURCE.dat > data/$$SOURCE/latency-getstats.tex
	export SOURCE=appear.in-final-vanilla-3p; ./tools/latexify_latency_csv.py -f data/$$SOURCE/$$SOURCE.csv > data/$$SOURCE/latency-timer.tex
	export SOURCE=appear.in-final-vanilla-3p; ./tools/latexify_captured_data_latency.py --new-format -s 1434048948 data/$$SOURCE/$$SOURCE.dat > data/$$SOURCE/latency-getstats.tex
	export SOURCE=appear.in-final-traveller; ./tools/latexify_latency_csv.py -f data/$$SOURCE/$$SOURCE.csv > data/$$SOURCE/latency-timer.tex
	export SOURCE=appear.in-final-traveller; ./tools/latexify_captured_data_latency.py --new-format -s 1434050117 data/$$SOURCE/$$SOURCE.dat > data/$$SOURCE/latency-getstats.tex

captured-latencies:
	find data -type d -name "*-capture-*" | while read datadir; do target=$$(basename "$$datadir"); ./tools/latexify_captured_data_latency.py data/$$target/$$target.dat > data/$$target/latency-getstats.tex; done
	find data -type d -name "*-final-*" | while read datadir; do target=$$(basename "$$datadir"); ./tools/latexify_captured_data_latency.py --new-format data/$$target/$$target.dat > data/$$target/latency-getstats.tex; done

captured-bitrates:
	find data -type d -name "*-capture-*" | while read datadir; do target=$$(basename "$$datadir"); ./tools/latexify_captured_data_bitrate.py data/$$target/$$target.dat > data/$$target/bitrate-getstats.tex; done
	find data -type d -name "*-final-*" | while read datadir; do target=$$(basename "$$datadir"); ./tools/latexify_captured_data_bitrate.py data/$$target/$$target.dat > data/$$target/bitrate-getstats.tex; done

inkscape-illustrations:
	bash -c 'find figs -type f -name "*.svg" | while read path; do target=$$(basename "$$path"); inkscape -f "$$path" --export-eps figs/$${target%.*}.eps; done'

bitrates:
	find data -type d -name "appear.in*" ! -name "*capture*" ! -name "*final*" | while read datadir; do ./tools/latexify_csv_bitrate_traces.py $$datadir/*-bitrates.csv > $$datadir/bitrate.tex; done
	./tools/latexify_csv_bitrate_traces.py -n 120 data/appear.in-final-traveller/*-bitrates.csv > data/appear.in-final-traveller/bitrate-tcpdump.tex
	./tools/latexify_csv_bitrate_traces.py -n 120 data/appear.in-final-vanilla-3p/*-bitrates.csv > data/appear.in-final-vanilla-3p/bitrate-tcpdump.tex

utilization:
	test -d tmp || mkdir tmp
	for case in traveller standup friends; do ./tools/calculate_link_utilization.py data/appear.in-$$case/bitrate.tex -c $$case > tmp/$$case-utilization-firefox.tex; done
	for case in traveller standup friends; do ./tools/calculate_link_utilization.py data/appear.in-final-$$case/bitrate-getstats.tex -c $$case > tmp/$$case-utilization-chrome.tex; done

graphviz:
	bash -c 'find figs -type f -name "*.dot" | while read path; do target=$$(basename "$$path"); dot -Teps figs/$$target -o "figs/$${target%.*}.eps"; done'

script-runtimes:
	./tools/latexify_script_runtimes.py > tmp/script-runtimes.tex
	./tools/latexify_script_runtimes.py mem > tmp/script-runtimes-mem.tex

latex:
	pdflatex -draftmode --shell-escape $(TEXFILE) && \
	bibtex $(TEXFILE) && \
	makeglossaries $(TEXFILE) && \
	pdflatex -draftmode --shell-escape $(TEXFILE) && \
	pdflatex --shell-escape $(TEXFILE) && \
	cp $(TEXFILE).pdf report.pdf


# Removes TeX-output files
clean:
	rm -f *.aux $(TEXFILE).bbl $(TEXFILE).blg *.log *.out $(TEXFILE).toc $(TEXFILE).lot $(TEXFILE).lof $(TEXFILE).glg $(TEXFILE).glo $(TEXFILE).gls $(TEXFILE).ist $(TEXFILE).acn $(TEXFILE).acr $(TEXFILE).alg $(TEXFILE).xdy $(TEXFILE).loa
	find data -type f -name "*.tex" ! -name "latency-lin.tex" -delete
	find figs -type f -name "*.eps" -delete
