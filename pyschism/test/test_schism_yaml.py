#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
""" Unittest of customized YAML for SCHISM with including and substitution
"""
from __future__ import absolute_import
from schism_yaml import load, YamlAction, ArgumentParserYaml
import yaml
import argparse
import sys
import unittest
import copy
import os


class TestSchismYaml(unittest.TestCase):
    """ Unit tests of SCHSIM YAML
    """
    dir_testdata = os.path.join(os.path.dirname(__file__),
                                'testdata/schism_yaml')

    def setUp(self):
        self.argv_ori = copy.deepcopy(sys.argv)
        sys.argv = sys.argv[:1]

    def tearDown(self):
        sys.argv = self.argv_ori

    def test_unsubstituted_env(self):
        """ Should raise an exception with unsubstituted environment variables
        """
        fname = os.path.join(self.dir_testdata, 'env_wo_sub.yaml')
        with open(fname, 'r') as fin:
            self.assertRaises(yaml.composer.ComposerError,
                              load, fin)

    def test_multiple_level_in_env(self):
        """ Should raise an exception with multiple level variables in env
        """
        fname = os.path.join(self.dir_testdata, 'env_w_multiplelevel.yaml')
        with open(fname, 'r') as fin:
            self.assertRaises(ValueError, load, fin)

    def test_multiple_substitution_in_one_item(self):
        """ Test multiple substitution in one item
        """
        fname = os.path.join(self.dir_testdata,
                             'substitute_multiple_times_in_one_item.yaml')
        with open(fname, 'r') as f:
            data = load(f)
            self.assertEqual(data['mesh']['work_dir'], 'dir1/file1')

    def test_substitute_wo_including(self):
        """ Test a simple substitution without include
        """
        fname = os.path.join(self.dir_testdata, 'substitute_wo_including.yaml')
        with open(fname, 'r') as f:
            data = load(f)
            self.assertEqual(data['mesh']['work_dir'], 'dir1')

    def test_substitute_multiple_including(self):
        """ Test substitution in multiple including
        """
        fname = os.path.join(self.dir_testdata,
                             'substitute_w_including.yaml')
        with open(fname, 'r') as f:
            data = load(f)
            self.assertEqual(data['mesh']['work_dir'], 'dir1')
        fname = os.path.join(self.dir_testdata,
                             'substitute_w_including_typo.yaml')
        with open(fname, 'r') as f:
            self.assertRaises(ValueError, load, f)

    def test_argparse_action(self):
        """ Test YAML for argparse
        """
        fname = os.path.join(self.dir_testdata, 'argparse.yaml')
        # YAML test
        sys.argv = copy.deepcopy(self.argv_ori)
        sys.argv.extend(("--yaml", "%s" % fname))
        parser = argparse.ArgumentParser(fromfile_prefix_chars="@")
        parser.add_argument("--input1")
        parser.add_argument("--input2")
        parser.add_argument("--input_multi", nargs='+')
        parser.add_argument("--start")
        parser.add_argument("--yaml", action=YamlAction)
        args, _ = parser.parse_known_args()
        self.assertEqual(args.input1, "1")
        self.assertEqual(args.start, "2009/08/23")
        self.assertEqual(args.input_multi, ['1', '2'])
        # Overwriting test 1
        sys.argv = copy.deepcopy(self.argv_ori)
        sys.argv.extend(("--yaml", "%s" % fname))
        sys.argv.extend(("--input1", "2"))
        args, _ = parser.parse_known_args()
        self.assertEqual(args.input1, "2")
        # Overwriting test 2
        sys.argv = copy.deepcopy(self.argv_ori)
        sys.argv.extend(("--input1", "2"))
        sys.argv.extend(("--yaml", "%s" % fname))
        args, _ = parser.parse_known_args()
        self.assertEqual(args.input1, "1")
        # Whitespace in key test
        fname = os.path.join(self.dir_testdata, 'argparse_whitespace.yaml')
        sys.argv = copy.deepcopy(self.argv_ori)
        sys.argv.extend(("--yaml", "%s" % fname))
        self.assertRaises(ValueError, parser.parse_args)
        # Multiple level
        fname = os.path.join(self.dir_testdata, 'argparse_multiple_level.yaml')
        sys.argv = copy.deepcopy(self.argv_ori)
        sys.argv.extend(("--yaml", "%s" % fname))
        self.assertRaises(ValueError, parser.parse_args)

    def test_multiple_argparse_action(self):
        """ Test multiple YAML for argparse
        """
        fname1 = os.path.join(self.dir_testdata, 'argparse.yaml')
        fname2 = os.path.join(self.dir_testdata, 'argparse2.yaml')
        # YAML test
        sys.argv = copy.deepcopy(self.argv_ori)
        sys.argv.extend(("--yaml", fname1, "--yaml", fname2))
        parser = argparse.ArgumentParser()
        parser.add_argument("--input1")
        parser.add_argument("--input2")
        parser.add_argument("--start")
        parser.add_argument("--yaml", action=YamlAction)
        args, _ = parser.parse_known_args()
        self.assertEqual(args.input1, "4")
        self.assertEqual(args.input2, "2")
        self.assertEqual(args.start, "2009/08/23")

    def test_argparse_yaml(self):
        """ Test ArgumentParserYaml
        """
        fname = os.path.join(self.dir_testdata, 'argparse.yaml')
        parser = ArgumentParserYaml(fromfile_prefix_chars="@")
        # YAML test
        sys.argv = copy.deepcopy(self.argv_ori)
        sys.argv.append(("@%s" % fname))
        parser.add_argument("--input1")
        parser.add_argument("--input2")
        parser.add_argument("--input_multi", nargs='+')
        parser.add_argument("--start")
        # args = parser.parse_args()  # Left these for reference
        args, _ = parser.parse_known_args()  # Use this to ignore some arguments
        self.assertEqual(args.input1, "1")
        self.assertEqual(args.start, "2009/08/23")
        self.assertEqual(args.input_multi, ['1', '2'])
        # Overwriting test 1, YAML first
        sys.argv = copy.deepcopy(self.argv_ori)
        sys.argv.append(("@%s" % fname))
        sys.argv.extend(("--input1", "2"))
        args, _ = parser.parse_known_args()
        self.assertEqual(args.input1, "2")
        # Overwriting test 2, YAML at the end
        sys.argv = copy.deepcopy(self.argv_ori)
        sys.argv.extend(("--input1", "2"))
        sys.argv.append(("@%s" % fname))
        args, _ = parser.parse_known_args()
        self.assertEqual(args.input1, "1")
        # Whitespace in key test
        fname = os.path.join(self.dir_testdata, 'argparse_whitespace.yaml')
        sys.argv = copy.deepcopy(self.argv_ori)
        sys.argv.append(("@%s" % fname))
        self.assertRaises(ValueError, parser.parse_args)
        # Multiple level
        fname = os.path.join(self.dir_testdata, 'argparse_multiple_level.yaml')
        sys.argv = copy.deepcopy(self.argv_ori)
        sys.argv.append(("@%s" % fname))
        self.assertRaises(ValueError, parser.parse_args)

    def test_multiple_argparse_yaml(self):
        """ Test multiple YAML for argparse
        """
        fname1 = os.path.join(self.dir_testdata, 'argparse.yaml')
        fname2 = os.path.join(self.dir_testdata, 'argparse2.yaml')
        # YAML test
        sys.argv = copy.deepcopy(self.argv_ori)
        sys.argv.extend(("@%s" % fname1, "@%s" % fname2))
        parser = ArgumentParserYaml(fromfile_prefix_chars='@')
        parser.add_argument("--input1")
        parser.add_argument("--input2")
        parser.add_argument("--start")
        args, _ = parser.parse_known_args()
        self.assertEqual(args.input1, "4")  # Overwrite with the latter value
        self.assertEqual(args.input2, "2")
        self.assertEqual(args.start, "2009/08/23")


if __name__ == "__main__":
    unittest.main()
