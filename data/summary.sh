#!/bin/bash
# Run from data dir: ./summary.sh

print_table() {
    local dir="$1"
    local label="$2"
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf " %s  (%s)\n" "$label" "$(date '+%Y-%m-%d %H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf "%-12s  %6s  %8s  %8s  %8s  %5s\n" \
           "METHOD" "TSLOTS" "DET" "ERR" "LAMBDA" "RUNS"
    echo "──────────────────────────────────────────────────────────────────────────"
    
    for f in "$dir"/*.json; do
        [ -e "$f" ] || continue
        basename "$f" .json
    done | awk -F'[_-]' '
    {
        method = ""
        tslots = ""; det = ""; err = ""; lam = "-"
        i = 1
        while (i <= NF && $i !~ /^p[0-9]+$/) {
            method = (method == "" ? $i : method "_" $i)
            i++
        }
        if ($i ~ /^p[0-9]+$/) { tslots = substr($i, 2); i++ }
        if ($i ~ /^det/) { det = substr($i, 4); i++ }
        if ($i ~ /^err/) { err = substr($i, 4); i++ }
        if ($i ~ /^lam/) { lam = substr($i, 4); i++ }
        print method "\t" tslots "\t" det "\t" err "\t" lam
    }' | sort | uniq -c | awk '{
        printf "%-12s  %6s  %8s  %8s  %8s  %5d\n", $2, $3, $4, $5, $6, $1
    }'
    
    echo "──────────────────────────────────────────────────────────────────────────"
    total=$(find "$dir" -maxdepth 1 -name "*.json" 2>/dev/null | wc -l)
    printf " Total: %d files\n" "$total"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

print_table "dummyyes" "DUMMY YES"
print_table "dummyless" "DUMMY LESS"
