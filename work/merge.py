# problem this all merge thing doesn't handle the case when 2 weaves overlap
# to hard to detect
def merge_into(dest, src, weaves):
    to_append, touched = [], []
    for sh in src:
        for target in dest:
            if (f := target.merger(sh)):
                # find weaves on `sh`
                # transform them using f to put them on target
                # don't include `sh` in shapes to be added
                # do twice because attach-point may be at index 0 or 1
                we0 = [we for we in weaves if we.hangpoints[0].s == sh]
                for we in we0:
                    hg = we.hangpoints[0]
                    hg.s, hg.i, we.incrs[0] = target, f(hg.i), f(hg.i + we.incrs[0])
                #
                we1 = [we for we in weaves if we.hangpoints[1].s == sh]
                for we in we1:
                    hg = we.hangpoints[1]
                    hg.s, hg.i, we.incrs[1] = target, f(hg.i), f(hg.i + we.incrs[1])
                touched.append(target)
                break
        else:
            to_append.append(sh)
    #
    dest += to_append
    return dest, to_append + touched
    ##
