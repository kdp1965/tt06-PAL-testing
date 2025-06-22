SRCS = $(wildcard *.txt)
PNGS = $(SRCS:.txt=.png)

ASCEE = $(shell which ascee)

all: $(PNGS)

%.png: %.txt
	$(ASCEE) -f png $<

info:
	@echo $(PNGS)
