all:
	pdflatex main
	makeindex main.idx -s StyleInd.ist
	biber main
	pdflatex main
	pdflatex main

clean:
	rm -f *.aux *.bbl *.bcf *.blg *.idx *.ind *.ilg *.log *.ptc *.toc *.run.xml *.pdf
