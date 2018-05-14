#!/bin/bash

remove_stacktrace() {
    sed -E "s/ at ([a-zA-Z_$][a-zA-Z0-9_$]*\.)+[a-zA-Z_$][a-zA-Z0-9_$]*\((([a-zA-Z_$][a-zA-Z0-9_$]{1,30}\.java:[0-9]{1,4})|([a-zA-Z]{1,30} [a-zA-Z]{1,30}))\)/ /g" |
    tr -s " "
}

remove_long_strings() {
    sed -E "s/([01]{4,20}\.){3,30}[01]{4,20}/ /g" | # remove concatenated binary strings
    sed -E "s/([a-zA-Z0-9_$]{2,50}\.){5,}[a-zA-Z0-9_$]{2,50}/ /g" | # remove long package names
    tr -s " "
}

INPUTFILE=$1
FOLDER=$(dirname $INPUTFILE)
FILENAME=$(basename $INPUTFILE)
OUTPUTFILE="$FOLDER"/"$FILENAME"_nst

cat "$INPUTFILE" | remove_stacktrace | remove_long_strings > "$OUTPUTFILE"