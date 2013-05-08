all: main 

clean: 
	rm -f *.aux *.bbl *.log *.pdf *.blg *.out


main: main.tex main.bib 
	pdflatex main.tex
	bibtex main
	pdflatex main.tex
	pdflatex main.tex
