#!/bin/bash

normalize_text() {
    sed -E "s/[^ \.]{40,}/ /g" | sed -E "s/[[:punct:]]{4,}/ /g" | 
    sed -E -e 's/[!"%&$^*@`~(),?=\/\|<:;>\{\}-]/ /g' -e 's/\[/ /g' -e 's/\]/ /g' | 
    sed -E -e 's/(c#)|#/\1/g' -e 's/(c\+\+)|\+/\1/g' | tr -s " "
}

INPUTFILE=$1
FOLDER=$(dirname $INPUTFILE)
FILENAME=$(basename $INPUTFILE)
OUTPUTFILE="$FOLDER"/"$FILENAME"_norm

cat "$INPUTFILE" | normalize_text > "$OUTPUTFILE"