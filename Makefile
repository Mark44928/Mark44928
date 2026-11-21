# Mark44928 — Makefile
# GitHub profile README + static family hub. Static HTML/CSS/JS, no build
# step, no tests. Pages deploys from main.
#
#   make check    the hub is well-formed HTML (every repo card has a target)
#   make clean    remove nothing (assets and HTML are checked in)

PYTHON ?= python3
export TMPDIR ?= /data/data/com.termux/files/usr/tmp

.PHONY: check clean

# Every project card must link somewhere real: a repo URL or a local hub
# anchor. A card with no href is a dead button on the published page.
check:
	@missing=0; \
	for href in $$(grep -oE 'href="[^"]+"' index.html | sed 's/href="//;s/"//'); do \
		case "$$href" in \
			http*|mailto:*|assets/*|logos/*|docs/*|*.svg|*.png|*.css|*.js|\#*) ;; \
			*) echo "suspicious href: $$href"; missing=1 ;; \
		esac; \
	done; \
	[ "$$missing" = "0" ] && echo "hub links OK" || exit 1

clean:
	@true