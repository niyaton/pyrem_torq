#coding: utf-8

import re

from base_expression import TorqExpression, TorqExpressionSingleton, MatchCandidateForLookAhead, ANY_ITEM


class Literal(TorqExpression):
    ''' Literal expression matches a sequence of characters, 
        which is the same to the internal string. 
    '''

    __slots__ = ['__string', '__mc4la']

    def __init__(self, s):
        self.__string = s
        self.__mc4la = MatchCandidateForLookAhead(literals=(self.__string, ))

    def _match_lit(self, inpSeq, inpPos, lookAheadString):
        #assert len(lookAheadString) == 2
        if self.__string == lookAheadString[1]:
            return 2, lookAheadString
        #return None
    
    def __repr__(self): return "Literal(%s)" % repr(self.__string)
    def __hash__(self): return hash("Literal") + hash(self.__string)
    
    def extract_strings(self):
        return [self.__string]

    def getMatchCandidateForLookAhead(self): return self.__mc4la

    def _eq_i(self, right, alreadyComparedExprs):
        return right.__class__ is Literal and self.__string == right.__string

_anyLiteralMc4la = MatchCandidateForLookAhead(literals=ANY_ITEM)


class AnyLiteral(TorqExpressionSingleton):
    ''' AnyLiteral expression matches a length-1 sequence of character. '''

    __slots__ = []

    def _match_lit(self, inpSeq, inpPos, lookAheadString):
        #assert len(lookAheadString) == 2
        return 2, lookAheadString
    
    def __repr__(self): return "AnyLiteral()"
    def __hash__(self): return hash("AnyLiteral")
    
    def getMatchCandidateForLookAhead(self): return _anyLiteralMc4la


class RexCompilationUnable(ValueError):
    pass


class Rex(TorqExpression):
    ''' Rex expression matches a sequence of characters with the internal regular expression. '''

    __slots__ = ['__expression_match', '__expressionstr', '__ignoreCase']

    def __init__(self, exprStr, ignoreCase=False):
        try:
            flags = re.DOTALL
            if ignoreCase: flags |= re.IGNORECASE
            pat = re.compile(exprStr, flags)
        except Exception:
            raise RexCompilationUnable("invalid regex string: %s" % repr(exprStr))
        self.__expression_match = pat.match
        self.__expressionstr = exprStr
        self.__ignoreCase = ignoreCase
        
    def _match_lit(self, inpSeq, inpPos, lookAheadString):
        #assert len(lookAheadString) == 2
        if self.__expression_match(lookAheadString[1]):
            return 2, lookAheadString
        #return None

    def __repr__(self): return "Rex(%s,ignoreCase=%s)" % (repr(self.__expressionstr), repr(self.__ignoreCase))

    def __hash__(self): return hash("Rex") + hash(self.__expressionstr)
    
    def getMatchCandidateForLookAhead(self): return _anyLiteralMc4la
            
    def _eq_i(self, right, alreadyComparedExprs):
        return right.__class__ is Rex and \
                self.__expressionstr == right.__expressionstr and self.__ignoreCase == right.__ignoreCase
