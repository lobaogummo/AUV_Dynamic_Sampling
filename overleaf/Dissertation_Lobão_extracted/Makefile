#jlopes,  Sun Nov  3 23:24:34 2024

SRC=meec_thesis

latexmk:
	latexmk -pdf -recorder -pvc $(SRC).tex

clean: 
	-rm  -f \
	*.aux *.log *.nav *.log *.toc *.snm *.out *.dvi *.ps \
	*latexmk *.bcf *.fls *.bbl *.blg *.lof *.lot *.tdo *.xml
