import sys, os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from pyrem_torq.treeseq import *

class TestTorqTreeseq(unittest.TestCase):
    def testRemoveStrattrs(self):
        seq = [ 'a', 1, 'b', 2, 'c' ]
        self.assertEquals(seq_remove_strattrs(seq), [ 'a', 'b', 'c' ])
    
        seq = [ 'a', [ 'B', 1, 'b' ], 2, 'c' ]
        self.assertEquals(seq_remove_strattrs(seq), [ 'a', [ 'B', 'b' ], 'c' ])
    
    def testEncloseStrattrs(self):
        seq = [ 'a', 1, 'b', 2, 'c' ]
        self.assertEquals(seq_enclose_strattrs(seq), [ 'a', ( 1, 'b' ), ( 2, 'c' ) ])
    
        seq = [ 'a', [ 'B', 1, 'b' ], 2, 'c' ]
        self.assertEquals(seq_enclose_strattrs(seq), [ 'a', [ 'B', ( 1, 'b' ) ], ( 2, 'c' ) ])
        
    def testEncloseStrattrsToIllegalData(self):
        seq = [ 'a', 1, 'b', 'c' ]
        with self.assertRaises(IndexError):
            seq_enclose_strattrs(seq)
    
        seq = [ 'a', [ 'B', 1, 'b' ], 'c' ]
        with self.assertRaises(IndexError):
            seq_enclose_strattrs(seq)
        
    def testDiscloseStrattrs(self):
        seq = [ 'a', ( 1, 'b' ), ( 2, 'c' ) ]
        self.assertEquals(seq_disclose_strattrs(seq), [ 'a', 1, 'b', 2, 'c' ])

        seq = [ 'a', [ 'B', ( 1, 'b' ) ], ( 2, 'c' ) ]
        self.assertEquals(seq_disclose_strattrs(seq), [ 'a', [ 'B', 1, 'b' ], 2, 'c' ])
        
    def testDiscloseStrattrsToIllegalData(self):
        seq = [ 'a', ( 1, 'b' ), 'c' ]
        with self.assertRaises(TypeError):
            seq_disclose_strattrs(seq)

        seq = [ 'a', [ 'B', ( 1, 'b' ) ], 'c' ]
        with self.assertRaises(TypeError):
            seq_disclose_strattrs(seq)
    
    def testSplitAndMergeStrattrs(self):
        seq = [ 'a', 1, 'b', 2, 'c' ]
        atrSeq, strSeq = seq_split_strattrs(seq)
        self.assertEquals(strSeq, [ 'a', 'b', 'c' ])
        self.assertEquals(atrSeq, [ 'a', 1, 2 ])
        mergedSeq = seq_merge_strattrs(atrSeq, strSeq)
        self.assertEquals(mergedSeq, seq)
        
        seq = [ 'a', [ 'B', 1, 'b' ], 2, 'c' ]
        atrSeq, strSeq = seq_split_strattrs(seq)
        self.assertEquals(strSeq, [ 'a', [ 'B', 'b' ], 'c' ])
        self.assertEquals(atrSeq, [ 'a', [ 'B', 1 ], 2 ])
        mergedSeq = seq_merge_strattrs(atrSeq, strSeq)
        self.assertEquals(mergedSeq, seq)
         
#def TestSuite(TestTorqTreeseq):
#    return unittest.makeSuite(TestTorqTreeseq)

if __name__ == '__main__':
    unittest.main()

