BEGIN {
    lc = 0; wc = 0
}
{ 
    lc = lc + 1 
    wc = wc + NF
}
END {
    print lc, wc
}
