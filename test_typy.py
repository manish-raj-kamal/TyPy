import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from Typy import format_code


class TypyFormatTests(unittest.TestCase):
    def test_format_code_preserves_exact_text_and_strips_trailing(self):
        raw = "def greet():\n    print('hello')\n  print('bye')\n"
        expected = "def greet():\n    print('hello')\n  print('bye')\n"
        self.assertEqual(format_code(raw), expected)

    def test_format_code_handles_nested_blocks_verbatim(self):
        raw = "def greet():\n  print('hello')\n  if True:\n    print('nested')\n  print('done')\n"
        expected = "def greet():\n  print('hello')\n  if True:\n    print('nested')\n  print('done')\n"
        self.assertEqual(format_code(raw), expected)


if __name__ == "__main__":
    unittest.main()


