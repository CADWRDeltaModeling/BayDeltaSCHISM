# -*- coding: utf-8 -*-
"""
Test all unit tests
"""

import test_schism_yaml
import test_schism_polygon
import test_schism_mesh
import test_triquadmesh
import xmlrunner
import unittest

if __name__ == "__main__":
    suites = []
    suites.append(unittest.TestLoader().loadTestsFromTestCase(test_schism_yaml.TestSchismYaml))
    suites.append(unittest.TestLoader().loadTestsFromTestCase(test_schism_polygon.TestSchismPolygon))
    suites.append(unittest.TestLoader().loadTestsFromTestCase(test_schism_mesh.TestSchismMesh))
    suites.append(unittest.TestLoader().loadTestsFromTestCase(test_triquadmesh.TestTriQuadMesh))

    for suite in suites:
        # Original unittest runner
        # unittest.TextTestRunner(verbosity=2).run(suite)
        # XML runner for CI
        xmlrunner.XMLTestRunner(output='test-reports').run(suite)
