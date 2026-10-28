import unittest
from dedup import canonical
class CanonicalTests(unittest.TestCase):
 def test_tracking(self):
  self.assertEqual(canonical('https://www.linkedin.com/in/Jane-DOE/?trk=abc'),'https://www.linkedin.com/in/jane-doe')
 def test_mobile(self):
  self.assertEqual(canonical('https://m.linkedin.com/in/Jane-DOE'),'https://www.linkedin.com/in/jane-doe')
 def test_reject_other(self):
  self.assertEqual(canonical('https://example.com/in/jane-doe'),'')
if __name__=='__main__':unittest.main()
