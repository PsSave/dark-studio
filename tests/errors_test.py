import unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from errors import explain
class ErrorsTest(unittest.TestCase):
    def test_wrapped_rate_limit(self):
        outer=RuntimeError('query failed')
        outer.__cause__=RuntimeError('429 Too Many Requests https://secret.example')
        text=explain(outer)
        self.assertIn('limitou temporariamente',text)
        self.assertNotIn('secret',text)
    def test_internal_error_not_blames_instagram(self):
        self.assertIn('erro interno',explain(ValueError('oops')))
    def test_login_distinct_from_rate_limit(self):
        self.assertIn('sessão de login',explain(RuntimeError('401 Unauthorized')))
if __name__=='__main__': unittest.main()
