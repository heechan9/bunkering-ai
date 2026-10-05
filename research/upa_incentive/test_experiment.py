import unittest
from experiment import fee
class FeeTests(unittest.TestCase):
    def test_cap(self): self.assertEqual(fee(18,10,True,True),(180,120,60))
    def test_short(self): self.assertEqual(fee(4,10,True,True),(40,40,0))
    def test_ineligible(self): self.assertEqual(fee(12,10,False,True),(120,0,120))
    def test_unapproved(self): self.assertEqual(fee(12,10,True,False),(120,0,120))
    def test_invalid(self):
        for x in [-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):fee(x,10,True,True)
if __name__=='__main__':unittest.main()
