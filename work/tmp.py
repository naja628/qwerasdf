def bundle(seq, shape = 2, *more, splice_1 = False):
    '''bundle(seq, shape = 2, *more) -> yield tuples made of consecutive elements of seq
        [*bundle(range(4), 2)]        -> [ (0, 1), (2, 3) ]
        [*bundle(range(6), 2, 1)]     -> [ (0, 1), (2,), (3, 4), (5,) ]
        [*bundle( range(6), (2, 1) )] -> [ ((0, 1), (2,)), ((3, 4), (5,)) ]
    "Uneven" elements at the end will be discarded (early StopIteration).
        [*bundle(range(3))] -> [(0, 1)]
    Negative numbers request elements to be discarded instead of bundled.
    If splice_1, 1's will yield elements themselves instead of 1-tuples.
        [*bundle(range(4), 1, -1, splice_1 = True)] -> [0, 2]
    '''
    seq = iter(seq)
    sentinel = object() 
    #
    def extract(shape):
        if type(shape) is int:
            if shape == 1 and splice_1: 
                return next(seq)
            elif shape >= 0:
                tmp = (next(seq) for _ in range(shape))
                return tuple(x in tmp if x is not sentinel)
            else:
                [next(seq) for _ in range(-shape)] # side effects
                return sentinel
        else:
            return tuple((extract(sub) for sub in shape))
    #
    while True:
        try:
            for sub in [shape, *more]:
                tmp = extract(sub)
                if tmp is not sentinel: yield tmp
        except:
            return

[*bundle(range(4), 2)]        
[*bundle(range(6), 2, 1)]     
[*bundle(range(6), 2, 1, splice_1 = True)]     
[*bundle( range(6), (2, 1) )] 
[*bundle(range(4), 1, -2, splice_1 = True)] 
[*bundle(range(3))]
