# problem this all merge thing doesn't handle the case when 2 weaves overlap
# too hard to detect
def merge_into(dest, src, weaves):
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
                        hg.s, hg.i = target, f(hg.i)
                        we.incrs = we.incrs[not which], f(hg.i + we.incrs[1]) - f(hg.i)
                        if which: we.incrs = we.incrs[0], we.incrs[1]
                #
                touched.append(target)
                break
        else:
            to_append.append(sh)
    #
    dest += to_append
    return dest, to_append + touched
    ##
