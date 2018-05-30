#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
import prepare_schism
import unittest
import os, sys, argparse

class TestPrepareSchism(unittest.TestCase):
    def setUp(self):
        dir_cur = os.path.dirname(__file__)
        dir_test = os.path.join(dir_cur, "testdata/prepare_schism")
        os.chdir(dir_test)

    def tearDown(self):
        os.chdir(os.path.dirname(__file__))

    def test_prepare_schism(self):
        os.chdir('simple_triquad')
        args = argparse.Namespace()
        setattr(args, 'main_inputfile', 'main_good.yaml')
        prepare_schism.prepare_schism(args)


if __name__ == '__main__':
    unittest.main()
