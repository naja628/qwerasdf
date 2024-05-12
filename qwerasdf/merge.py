# problem this all merge thing doesn't handle the case when 2 weaves overlap
# too hard to detect
def merge_into(dest, src, weaves):
    dest = [ sh for sh in dest if sh not in src ]
    to_append, touched = [], []
    for sh in src:
        for target in dest:
            if (f := sh.merger(target)):
                # find weaves on `sh`
                # transform them using f to put them on target
                # don't include `sh` in shapes to be added
                # do twice because attach-point may be at index 0 or 1
                for which in (0, 1):
                    attached = [we for we in weaves if we.hangpoints[which].s == sh]
                    for we in attached:
                        hg = we.hangpoints[which]
                        #
                        we.incrs = we.incrs[not which], f(hg.i + we.incrs[which]) - f(hg.i)
                        if not which: we.incrs = we.incrs[1], we.incrs[0]
                        #
                        hg.s, hg.i = target, f(hg.i)
                #
                touched.append(target)
                break
        else:
            to_append.append(sh)
    #
    dest += to_append
    return dest, to_append + touched
    ##

def merge_weaves(weaves):
    def decomp(we):
        incrs, nwires = we.incrs, we.nwires
        [(i1, s1), (i2, s2)] = [ (hg.i, hg.s) for hg in we.hangpoints]
        return incrs, nwires, i1, s1, i2, s2
    #
    uniques, seen = [], set()
    for we in reversed(weaves):
        tup = decomp(we)
        if tup in seen: continue
        else: 
            seen.add(tup)
            uniques.append(we)
    uniques.reverse()
    return uniques

