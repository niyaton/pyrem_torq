#coding: utf-8

from itertools import chain as _chain


def inner_expr_iter(expr):
    visitedExprIDSet = set()

    def iei_i(e):
        ide = id(e)
        if ide in visitedExprIDSet: return  # prevent infinite recursion

        visitedExprIDSet.add(ide)
        if hasattr(e, "extract_exprs"):
            for item in e.extract_exprs():
                if item is not None:
                    yield item
                    for v in iei_i(item): yield v  # need PEP380
    return iei_i(expr)


class _AnyItem:
    def __contains__(self, item): return True
    def __eq__(self, right): return right.__class__ is _AnyItem
    def __hash__(self): return hash("_AnyItem")
    def add(self, item): pass
    def update(self, item): return self
    def __repr__(self): return "_AnyItem()"
    def __or__(self, right): return self
    def __ror__(self, right): return self
ANY_ITEM = _AnyItem()


class MatchCandidateForLookAhead:
    __slots__ = []

    @staticmethod
    def __normalize_items(items):
        assert items is not None
        assert items is ANY_ITEM or ANY_ITEM not in items
        return ANY_ITEM if items is ANY_ITEM else frozenset(items)

    def __init__(self, nodes=(), literals=(), emptyseq=False):
        """ MatchCandidateForLookAhead(nodes=(), literals=(), emptyseq=False).
            nodes are the labels that an expression may match to.
            when nodes=ANY_ITEM, it means that an expression may match any labeled nodes.
            literals are the strings that an expression may match to.
            when literals=ANY_ITEM, it means that an expression may match any strings.
            emptyseq specifies an expression may match to an empty seq or not.
        """

        self.__nodes = MatchCandidateForLookAhead.__normalize_items(nodes)
        self.__literals = MatchCandidateForLookAhead.__normalize_items(literals)
        self.__emptyseq = not not emptyseq

    def modified(self, nodes=None, literals=None, emptyseq=None):
        return MatchCandidateForLookAhead(nodes=nodes if nodes is not None else self.__nodes,
            literals=literals if literals is not None else self.__literals,
            emptyseq=emptyseq if emptyseq is not None else self.__emptyseq)

    def _getnodes(self): return self.__nodes
    def _getliterals(self): return self.__literals
    def _getemptyseq(self): return self.__emptyseq

    nodes = property(_getnodes)
    literals = property(_getliterals)
    emptyseq = property(_getemptyseq)

    def __eq__(self, right):
        return right.__class__ == MatchCandidateForLookAhead and \
            self.__nodes == right.__nodes and self.__literals == right.__literals and self.__emptyseq == right.__emptyseq

    def __repr__(self):
        return "MatchCandiateForLookAhead(nodes=%s,literals=%s,emptyseq=%s)" % \
            ((repr(tuple(sorted(self.__nodes))) if self.__nodes.__class__ is not _AnyItem else "ANY_ITEM"),
            (repr(tuple(sorted(self.__literals)))  if self.__literals.__class__ is not _AnyItem else "ANY_ITEM"),
            repr(self.__emptyseq))

    def __hash__(self):
        return hash("MatchCandiateForLookAhead") + sum(map(hash, _chain(self.__nodes, self.__literals, self.__emptyseq)))


class LeftRecursionUndecided(ValueError): pass


class TorqExpression(object):
    ''' A base class of torq expression classes. (Abstract class.) '''

    __slots__ = []

    def __add__(self, other): return Seq(self, other)

    def __or__(self, other): return Or(self, other)

    def __rmul__(self, left):
        if isinstance(left, list):
            if len(left) == 1:
                if not isinstance(left[0], int): raise InvalidRepetitionCount("Invalid type for 1st value of repetition specifier")
                lower, upper = left[0], None
            else:
                if len(left) != 2: raise InvalidRepetitionCount("Invalid type for repetition specifier")
                if not isinstance(left[0], int): raise InvalidRepetitionCount("Invalid type for 1st value of repetition specifier")
                if not (left[1] is None or isinstance(left[1], int)):
                    raise InvalidRepetitionCount("Invalid type for 2nd value of repetition specifier")
                lower, upper = left
        elif isinstance(left, int):
            lower = upper = left
        else:
            raise InvalidRepetitionCount("Invalid type for repeat specifier")
        assert upper is None or lower <= upper
        return Repeat(self, lower, upper)

    def match(self, inpSeq, inpPos):
        ''' Do matching of the expression and input sequence.
            If a substring inpSeq[inpPos:x] is matched by the expression (self),
            returns a tuple of (length of matching substring, list of output nodes).
            Otherwise, returns a tuple (0, []).
        '''
        
        assert inpPos >= 1
        len_inpSeq = len(inpSeq)
        assert inpSeq.__class__ is list and len_inpSeq >= 1
        if inpPos == len_inpSeq:
            r = self._match_eon(inpSeq, inpPos, None)
        else:
            lookAhead = inpSeq[inpPos]
            if lookAhead.__class__ is list:
                r = self._match_node(inpSeq, inpPos, lookAhead)
            else:
                #assert lookAhead.__class__ is int #debug
                r = self._match_lit(inpSeq, inpPos, (lookAhead, inpSeq[inpPos + 1]))
        if r is None: return 0, []
        p, o = r
        if o.__class__ is not list: o = list(o)
        return p, o

    def parse(self, inpSeq):
        ''' Do matching of the expression and input sequence.
            If the entire inpSeq is matched by the expression (self),
            returns list of output nodes. Otherwise, returns None.
        '''

        p, o = self.match(inpSeq, 1)
        if 1 + p != len(inpSeq): return None
        newSeq = [inpSeq[0]]; newSeq.extend(o)
        return newSeq

    def _match_node(self, inpSeq, inpPos, lookAhead): pass  # return None
    _match_lit = _match_eon = _match_node

    def getMatchCandidateForLookAhead(self):
        ''' Returns the possible first items that self matches.
            If such items are unknown, returns None.
            e.g. Literal('a').getMatchCandidateForLookAhead() 
            -> MatchCandidateForLookAhead(nodes=(), literals=('a',), emptyseq=False).
        '''
        return None 
    
    def updateMatchCandidateForLookAhead(self): pass
        
    @staticmethod
    def __call_extract_exprs_if_having(self):
        return list(self.extract_exprs()) if hasattr(self, "extract_exprs") else []
    
    def _eq_i(self, right, alreadyComparedExprs):
        if self.__class__ is not right.__class__: return False
        ex = TorqExpression.__call_extract_exprs_if_having
        return all(es._eq_i(er, alreadyComparedExprs) for es, er in zip(ex(self), ex(right)))
    
    def __eq__(self, right): return self._eq_i(right, set())
    
    def __repr__(self): 
        return "%s(%s)" % (self.__class__.__name__, 
                ",".join(map(repr, TorqExpression.__call_extract_exprs_if_having(self))))
        
    def __hash__(self):
        return hash(self.__class__.__name__) + sum(hash(e) for e in TorqExpression.__call_extract_exprs_if_having(self))
    
    def _isLeftRecursive_i(self, target, visitedExprIdSet): return False
    
    def isLeftRecursive(self): return self._isLeftRecursive_i(self, set())


class TorqExpressionWithExpr(TorqExpression):
    ''' (Abstract class.) intended to be used internally. '''

    __slots__ = ['_expr', '_expr_match_node', '_expr_match_lit', '_expr_match_eon']

    def getexpr(self): return self._expr
    expr = property(getexpr)
    
    def _set_expr(self, expr):
        assert isinstance(expr, TorqExpression)
        self._expr = expr
        self._calc_mc4la()

    def extract_exprs(self): return [self._expr]


class TorqExpressionSingleton(TorqExpression):
    ''' (Abstract class.) intended to be used internally. '''
    __slots__ = []

    def _eq_i(self, right, alreadyComparedExprs):
        return right.__class__ == self.__class__


def _target_expr_flatener(exprs, targetExprClz):
    r = []
    for e in exprs:
        if e.__class__ is targetExprClz:
            r.extend(_target_expr_flatener(e.exprs, targetExprClz))
        else:
            r.append(e)
    return r


class Or(TorqExpression):
    ''' Or expression matches a sequence, iff the sequence is matched by one of the internal expressions. '''

    __slots__ = ['__exprs', '__ntbl_get', '__unknown_nlst', '__ltbl_get', '__unknown_llst', '__elst', '__mc4la']

    def __init__(self, *exprs):
        self._set_exprs(_target_expr_flatener(exprs, Or))
    
    def getexprs(self): return self.__exprs
    exprs = property(getexprs)
    
    def _set_exprs(self, exprs):
        self.__exprs = exprs
        for expr in self.__exprs: assert isinstance(expr, TorqExpression)
        self._calc_mc4la()
    
    def updateMatchCandidateForLookAhead(self):
        for expr in self.__exprs:
            expr.updateMatchCandidateForLookAhead()
        self._calc_mc4la()
    
    def _calc_mc4la(self):
        ntbl, self.__unknown_nlst, ltbl, self.__unknown_llst, self.__elst, including_unknown_req = Or._make_tables(self.__exprs)
        if including_unknown_req:
            self.__mc4la = None
        else:
            self.__mc4la = MatchCandidateForLookAhead(
                    nodes=ANY_ITEM if self.__unknown_nlst else ntbl.keys(),
                    literals=ANY_ITEM if self.__unknown_llst else ltbl.keys(),
                    emptyseq=not not self.__elst) 
        self.__ntbl_get = ntbl.get
        self.__ltbl_get = ltbl.get
    
    @staticmethod
    def _make_tables(exprs):
        def append_to_all_values(tbl, item):
            for L in tbl.itervalues(): L.append(item)
        includingUnknownReq = any(e is None for e in exprs)
        exprAndReqs = [(expr, expr.getMatchCandidateForLookAhead()) for expr in exprs]

        ns, ls = [], []
        for r in filter(None, (r for _, r in exprAndReqs)):
            if r.nodes is not ANY_ITEM: ns.extend(r.nodes)
            if r.literals is not ANY_ITEM: ls.extend(r.literals)

        ntbl = dict((lbl, []) for lbl in ns)
        unknown_nlst = []
        ltbl = dict((s, []) for s in ls)
        unknown_llst = []
        elst = []
        for expr, r in exprAndReqs:
            if r is not None:
                if r.nodes is not ANY_ITEM:
                    for lbl in r.nodes: ntbl[lbl].append(expr)
                else:
                    append_to_all_values(ntbl, expr)
                    unknown_nlst.append(expr)
                if r.literals is not ANY_ITEM:
                    for s in r.literals: ltbl[s].append(expr)
                else:
                    append_to_all_values(ltbl, expr)
                    unknown_llst.append(expr)
                if r.emptyseq: elst.append(expr)
            else:
                for L in _chain(ntbl.itervalues(), ltbl.itervalues(), [unknown_nlst, unknown_llst, elst]):
                    L.append(expr)
        return ntbl, unknown_nlst, ltbl, unknown_llst, elst, includingUnknownReq
    
    def extract_exprs(self): return list(self.__exprs)
        
    def _match_node(self, inpSeq, inpPos, lookAheadNode):
        for expr in self.__ntbl_get(lookAheadNode[0], self.__unknown_nlst):
            r = expr._match_node(inpSeq, inpPos, lookAheadNode)
            if r is not None:
                return r
        #else: return None
        
    def _match_lit(self, inpSeq, inpPos, lookAheadString):
        #assert len(lookAheadString) == 2
        for expr in self.__ltbl_get(lookAheadString[1], self.__unknown_llst):
            r = expr._match_lit(inpSeq, inpPos, lookAheadString)
            if r is not None:
                return r
        #else: return None
    
    def _match_eon(self, inpSeq, inpPos, lookAheadDummy):
        for expr in self.__elst:
            r = expr._match_eon(inpSeq, inpPos, lookAheadDummy)
            if r is not None:
                return r
        #else: return None

    def getMatchCandidateForLookAhead(self): 
        return self.__mc4la
     
    def _isLeftRecursive_i(self, target, visitedExprIdSet):
        id_self = id(self)
        if id_self in visitedExprIdSet:
            return False
        visitedExprIdSet.add(id_self)
        for expr in self.__exprs:
            if expr is target or expr._isLeftRecursive_i(target, visitedExprIdSet):
                return True


class Seq(TorqExpression):
    ''' Seq expression matches a sequence, iff the sequence is a 
        concatenation of the sequences, s1, s2, ...
        Here sequence s1 is matched by the 1st internal expression, 
        s2 by 2nd, and so on.
    '''

    __slots__ = ['__exprs', '__expr0', '__mc4la', ]

    def __init__(self, *exprs):
        self._set_exprs(_target_expr_flatener(exprs, Seq))
        
    def getexprs(self): return self.__exprs
    exprs = property(getexprs)
    
    def _set_exprs(self, exprs):
        self.__exprs = tuple(exprs)
        for expr in self.__exprs: assert isinstance(expr, TorqExpression)
        self.__expr0 = self.__exprs[0] if self.__exprs else Epsilon()
        self._calc_mc4la()
        
    def extract_exprs(self): return list(self.__exprs)
        
    def _calc_mc4la(self):
        ns, ls = set(), set()
        acceptEmpty = True
        for r in (expr.getMatchCandidateForLookAhead() for expr in self.__exprs):
            if r is None: 
                self.__mc4la = None
                return
            ns = ns | r.nodes
            ls = ls | r.literals
            if not r.emptyseq:
                acceptEmpty = False
                break  # for r
        self.__mc4la = MatchCandidateForLookAhead(
                nodes=ns, literals=ls, emptyseq=acceptEmpty)
    
    def updateMatchCandidateForLookAhead(self):
        for expr in self.__exprs:
            expr.updateMatchCandidateForLookAhead()
            mc4la = expr.getMatchCandidateForLookAhead()
            if mc4la is None or not mc4la.emptyseq:
                break  # for expr
        self._calc_mc4la()
    
    def __match_tail(self, inpSeq, inpPos, r):
        if r is None: return None
        p, o = r
        len_inpSeq = len(inpSeq)
        curInpPos = inpPos + p
        outSeq = o if o.__class__ is list else list(o); o_xt = outSeq.extend
        for expr in self.__exprs[1:]:
            if curInpPos == len_inpSeq:
                r = expr._match_eon(inpSeq, curInpPos, None)
            else:
                lookAhead = inpSeq[curInpPos]
                if lookAhead.__class__ is list:
                    r = expr._match_node(inpSeq, curInpPos, lookAhead)
                else:
                    #assert lookAhead.__class__ is int #debug
                    r = expr._match_lit(inpSeq, curInpPos, (lookAhead, inpSeq[curInpPos + 1]))
            if r is None: return None
            curInpPos += r[0]; o_xt(r[1])
        return curInpPos - inpPos, outSeq
    
    def _match_node(self, inpSeq, inpPos, lookAheadNode):
        return self.__match_tail(inpSeq, inpPos, self.__expr0._match_node(inpSeq, inpPos, lookAheadNode))

    def _match_lit(self, inpSeq, inpPos, lookAheadString):
        return self.__match_tail(inpSeq, inpPos, self.__expr0._match_lit(inpSeq, inpPos, lookAheadString))

    def _match_eon(self, inpSeq, inpPos, lookAheadDummy):
        outSeq = []
        for expr in self.__exprs:
            r = expr._match_eon(inpSeq, inpPos, lookAheadDummy)
            if r is None: return None
            #assert r[0] == 0
            outSeq.extend(r[1])
        return 0, outSeq

    def getMatchCandidateForLookAhead(self): 
        return self.__mc4la
        
    def __leftExprs_i(self, visitedExprIdSet): 
        id_self = id(self)
        if id_self in visitedExprIdSet:
            return ()
        visitedExprIdSet.add(id_self)
        for expr in self.__exprs:
            visitedExprIdSet.update(expr.__leftExprs_i(visitedExprIdSet))
            
    def _isLeftRecursive_i(self, target, visitedExprIdSet):
        id_self = id(self)
        if id_self in visitedExprIdSet:
            return False
        visitedExprIdSet.add(id_self)
        for expr in self.exprs:
            mc4a = expr.getMatchCandidateForLookAhead()
            if mc4a is None:
                raise LeftRecursionUndecided(repr(expr))
            if expr is target or expr._isLeftRecursive_i(target, visitedExprIdSet):
                return True
            if not mc4a.emptyseq:
                return False


class InvalidRepetitionCount(ValueError): pass

_zeroLengthReturnValue = 0, ()


class Repeat(TorqExpressionWithExpr):
    ''' Repeat expression matches a sequence, iff a N-time repetition of the internal expression matches the sequence.
        Here, N is a integer, lowerLimit <= N <= upperLimit.
        If lowerLimist is None, it will be regarded as 0.
        If upperLimit is None, it will be regarded as the infinite number.
    '''

    __slots__ = ['__lowerLimit', '__upperLimit', '__mc4la']

    def __init__(self, expr, lowerLimit, upperLimit):
        assert lowerLimit >= 0
        assert upperLimit is None or upperLimit >= lowerLimit
        self.__lowerLimit, self.__upperLimit = lowerLimit, upperLimit
        self._set_expr(expr)
    
    def _calc_mc4la(self):
        mc4la = self._expr.getMatchCandidateForLookAhead()
        self.__mc4la = None if mc4la is None else \
                mc4la.modified(emptyseq=self.__lowerLimit == 0 or mc4la.emptyseq)
    
    def updateMatchCandidateForLookAhead(self):
        self.expr.updateMatchCandidateForLookAhead()
        self._calc_mc4la()
        
    def _match_node(self, inpSeq, inpPos, lookAhead):
        len_inpSeq = len(inpSeq)
        assert inpPos < len_inpSeq
        curInpPos = inpPos
        outSeq = []; o_xt = outSeq.extend
        
        ul = self.__upperLimit if self.__upperLimit is not None else (len_inpSeq - inpPos)
        # inpPos will increase 1 or more by a repetition so we can't repeat the following loop over (len_inpSeq - inpPos) times.
        
        count = 0 - self.__lowerLimit
        ul -= self.__lowerLimit
        while count < ul and curInpPos < len_inpSeq:
            lookAhead = inpSeq[curInpPos]
            if lookAhead.__class__ is list:
                r = self._expr._match_node(inpSeq, curInpPos, lookAhead)
            else:
                #assert lookAhead.__class__ is int #debug
                r = self._expr._match_lit(inpSeq, curInpPos, (lookAhead, inpSeq[curInpPos + 1]))
            if r is None:
                if count < 0: return None
                break  # for count
            p, o = r
            if p == 0 and count >= 0: break  # in order to avoid infinite loop
            curInpPos += p; o_xt(o)
            count += 1
        if curInpPos == len_inpSeq and count < 0:
            r = self._expr._match_eon(inpSeq, inpPos, None)
            if r is None: return None
            p, o = r
            #assert p == 0
            if o.__class__ is not list: o = list(o)
            o_xt(o * -count)
        return curInpPos - inpPos, outSeq
    
    _match_lit = _match_node
    
    def _match_eon(self, inpSeq, inpPos, lookAheadDummy):
        r = self._expr._match_eon(inpSeq, inpPos, lookAheadDummy)
        if r is None:
            return _zeroLengthReturnValue if self.__lowerLimit == 0 else None
        p, o = r
        #assert p == 0
        if self.__lowerLimit != 0:
            if o.__class__ is not list: o = list(o)
            return 0, o * self.__lowerLimit
        return _zeroLengthReturnValue
    
    def _eq_i(self, right, alreadyComparedExprs):
        return right.__class__ is Repeat and \
                self.__lowerLimit == right.__lowerLimit and self.__upperLimit == right.__upperLimit and \
                self._expr._eq_i(right._expr, alreadyComparedExprs)

    def __repr__(self):
        return "Repeat(%s,%s,%s)" % (repr(self.expr), repr(self.__lowerLimit), repr(self.__upperLimit))

    def __hash__(self): return hash("Repeat") + hash(self.expr) + hash(self.__lowerLimit) + hash(self.__upperLimit)

    def getMatchCandidateForLookAhead(self): 
        return self.__mc4la
    
    @staticmethod
    def ZeroOrOne(expr): return _RepeatZeroOrOne(expr)

    @staticmethod
    def ZeroOrMore(expr): return Repeat(expr, 0, None)

    @staticmethod
    def OneOrMore(expr): return Repeat(expr, 1, None)
        
    def _isLeftRecursive_i(self, target, visitedExprIdSet):
        id_self = id(self)
        if id_self in visitedExprIdSet:
            return False
        visitedExprIdSet.add(id_self)
        return self.expr is target or self.expr._isLeftRecursive_i(target, visitedExprIdSet)


class _RepeatZeroOrOne(Repeat):
    __slots__ = []

    def __init__(self, expr):
        Repeat.__init__(self, expr, 0, 1)
        
    def _match_node(self, inpSeq, inpPos, lookAheadNode):
        return self._expr._match_node(inpSeq, inpPos, lookAheadNode) or _zeroLengthReturnValue
    
    def _match_lit(self, inpSeq, inpPos, lookAheadString):
        return self._expr._match_lit(inpSeq, inpPos, lookAheadString) or _zeroLengthReturnValue
   
    def _match_eon(self, inpSeq, inpPos, lookAheadDummy):
        return self._expr._match_eon(inpSeq, inpPos, lookAheadDummy) or _zeroLengthReturnValue

_searchingMc4la = MatchCandidateForLookAhead(nodes=ANY_ITEM, literals=ANY_ITEM, emptyseq=True)


def _toPred(laSet):
    if laSet is ANY_ITEM: return lambda la: True
    elif len(laSet) == 0: return lambda la: False
    else: return laSet.__contains__


class Search(TorqExpressionWithExpr):
    ''' Search(expr) is identical to Repeat(Or(expr, Any()), 0, None). '''

    __slots__ = ['__nodeLAPred', '__literalLAPred']

    def __init__(self, expr):
        self._set_expr(expr)
    
    def _calc_mc4la(self):
        exprMc4la = self.expr.getMatchCandidateForLookAhead()
        if exprMc4la is None:
            self.__nodeLAPred = \
                    self.__literalLAPred = lambda la: True
        else:
            self.__nodeLAPred = _toPred(exprMc4la.nodes)
            self.__literalLAPred = _toPred(exprMc4la.literals)
    
    def updateMatchCandidateForLookAhead(self):
        self.expr.updateMatchCandidateForLookAhead()
        self._calc_mc4la()
        
    def _match_node(self, inpSeq, inpPos, lookAhead):
        len_inpSeq = len(inpSeq)
        curInpPos = inpPos
        outSeq = []; o_xt = outSeq.extend; o_ap = outSeq.append
        while curInpPos < len_inpSeq:
            lookAhead = inpSeq[curInpPos]
            r = None
            if lookAhead.__class__ is list:
                if self.__nodeLAPred(lookAhead[0]):
                    r = self._expr._match_node(inpSeq, curInpPos, lookAhead)
                    if r is not None:
                        p, o = r
                        curInpPos += p; o_xt(o)
                if r is None or p == 0:
                    o_ap(lookAhead)
                    curInpPos += 1
            else:
                #assert lookAhead.__class__ is int #debug
                lookAheadLiteral = (lookAhead, inpSeq[curInpPos + 1])
                if self.__literalLAPred(lookAheadLiteral[1]):
                    r = self._expr._match_lit(inpSeq, curInpPos, lookAheadLiteral)
                    if r is not None:
                        p, o = r
                        curInpPos += p; o_xt(o)
                if r is None or p == 0:
                    o_xt(lookAheadLiteral)
                    curInpPos += 2
        if curInpPos == len_inpSeq:
            r = self._expr._match_eon(inpSeq, curInpPos, None)
            if r is not None:
                p, o = r
                #assert p == 0
                o_xt(o)
        return curInpPos - inpPos, outSeq
    
    _match_lit = _match_node
        
    def _match_eon(self, inpSeq, inpPos, lookAhead):
        return self._expr._match_eon(inpSeq, inpPos, lookAhead)
    
    def getMatchCandidateForLookAhead(self): 
        return _searchingMc4la
 
    def _isLeftRecursive_i(self, target, visitedExprIdSet):
        id_self = id(self)
        if id_self in visitedExprIdSet:
            return False
        visitedExprIdSet.add(id_self)
        return self.expr is target or self.expr._isLeftRecursive_i(target, visitedExprIdSet)


class InterpretError(StandardError):
    def __init__(self, message):
        StandardError.__init__(self, message)
        self.message = message
        self.stack = []

    def __repr__(self):
        return "InterpretError(%s,%s)" % (repr(self.message), repr(self.stack))


class InterpretErrorByErrorExpr(InterpretError):
    def __repr__(self):
        return "InterpretErrorByErrorExpr(%s,%s)" % (repr(self.message), repr(self.stack))

_anyMc4la = MatchCandidateForLookAhead(nodes=ANY_ITEM, literals=ANY_ITEM, emptyseq=False)


class ErrorExpr(TorqExpression):
    def __init__(self, message):
        self.message = message
    
    def _match_node(self, inpSeq, inpPos, lookAhead):
        e = InterpretErrorByErrorExpr(self.message)
        e.stack.insert(0, inpPos)
        raise e
        
    _match_lit = _match_eon = _match_node
    
    def __repr__(self): return "ErrorExpr(%s)" % repr(self.message)
    def __hash__(self): return hash("ErrorExpr") + hash(self.message)

    def _eq_i(self, right, alreadyComparedExprs):
        return right.__class__ is ErrorExpr and self.message == right.message

    def getMatchCandidateForLookAhead(self): return _anyMc4la
    
_emptyMc4la = MatchCandidateForLookAhead(emptyseq=True)


class Epsilon(TorqExpressionSingleton):
    ''' Epsilon expression matches any zero-length sequence. '''
    __slots__ = []

    def _match_node(self, inpSeq, inpPos, lookAhead): return _zeroLengthReturnValue
    _match_lit = _match_eon = _match_node
    def getMatchCandidateForLookAhead(self): return _emptyMc4la


class Any(TorqExpressionSingleton):
    ''' Any expression matches any length-1 sequence. '''
    __slots__ = []

    def _match_node(self, inpSeq, inpPos, lookAhead): return 1, [inpSeq[inpPos]]

    def _match_lit(self, inpSeq, inpPos, lookAheadString): return 2, lookAheadString
    def getMatchCandidateForLookAhead(self): return _anyMc4la


class Never(TorqExpressionSingleton):
    ''' Never expression does not match any sequence. '''
    __slots__ = []

    def _match_node(self, inpSeq, inpPos, lookAhead): return None
    _match_lit = _match_eon = _match_node
    
