
###############################
Test Suite for Prechecking Runs
###############################

Using the Tests
---------------

Bay-Delta SCHISM is a complex application and many setup issues recur. The project contains a pre-check suite
for finding some of these repeat errors. Some tests SCHISM input consistency in general, many others 
invoke Bay-Delta domain-specific relationships. 

The suite is contained in the `test_suite` directory of Bay-Delta SCHISM. The testing system is based on pytest, the ubiquitous testing
framework for Python. For those who are unfamiliar, pytest takes care of launching tests, counting successes and failures and tracking
simulation information as *fixtures*. Some of this is lingo. See the `pytest web site <https://docs.pytest.org/>`_ 

To run the tests you will first of all need to make sure your environment has pytest in it. Remember, you are not just adding this to 
your developer environment to test code, but to launch it as a user in everyday modeling. The  
`recommended environment <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/blob/master/schism_env.yml>`_ has pytest in it.

Then you use a command like the following:

.. _code-block: console

  sim_dir$ pytest /path/to/BayDeltaSCHISM/test_suite --sim_dir=.

Note that the `--sim_dir=.` part of the command is actually the default, so you can omit this if you launch the testing framework in the study directory
you are testing. The path `/path/to/BayDeltaSCHISM/test_suite` is a pointer to your Bay-Delta SCHISM installation subdirectory.

To make it simpler, we recommend setting an alias on the command line or in your .bashrc file:

.. _code-block: console

  alias schism_pretest='pytest /path/to/BayDeltaSCHISM/test_suite'


Writing Run Tests
-----------------

Basics of testing
=================

Leaving aside some quibbles over conventions, a test is just a function that has a name that starts 
with `test_` and that contains a python assert statement that contains the items to be tested and a message for failure:

.. _code-block: console

  def test_silly():
      assert 1 == 2, "One is not equal to two"

Bay-Delta SCHISM run tests are housed in the `/test_suite` directory of your Bay-Delta SCHISM installation. 
Any test scripts in this directory will be run when you launch pytest with the `/test_suite` directory.
They are usually launched in the simulation directory or you can name the simulation directory in your pytest command as
in the introductory example.  

Test Fixtures
=============
You will need to know the concepts of a *test fixture*, if only to make use of a small number of super important 
fixtures that are already defined. You can read about test fixtures on the `pytest web site <https://docs.pytest.org/>`_ 

First, there is the `sim_dir` fixture. Please use this rather than writing tests that assume 
the test is run in the simulation directory.  
A trivial example that uses `sim_dir` looks like this:

def test_param_exists(sim_dir):
    assert os.path.exists(os.path.join(sim_dir,"param.nml")), "Simulation directory must contain 'param.nml'"

Where `sim_dir` is applied as an input to he test_param_exists function.
This calls the `sim_dir` fixture function found in conftest.py and then submits the output of that function to the test_param_exists function.
A second indispensible fixture is `params`. This fetches the run parameters in `param.nml` using the `param.py` module. 
You should avoid parse `param.nml` with your own code.

A third proposal allows run-specific variables in a testconfig.yaml file that is in `sim_dir`.

Markers
=======

You can learn about markers on the `pytest web site <https://docs.pytest.org/>`_. You can use them to categorize tests.
Please use the `prerun` marker:

.. _code-block: python

  @pytest.mark.prerun
  def test_something():
    assert 1==2, "Failure message"

The marker will be ran upon calling pytest and any assert statement that fails (ex: 1==2) will trigger the following 'Failure message'. 
That's where you can add helpful information about what the test failure is and how to fix it.

What to test
============

Start with what is broken or what perenially gets out of synch. The Bay-Delta SCHISM testing suite has the feel of being *regression tests*.
Regression tests are basically checking for things that have gone wrong before. Examples:

* Source and sink (channel depletion) time series have different numbers of columns than the number of sources and sinks declared in `source_sink.in`. This is a generic SCHISM issue. This would be housed in `test_source_sink.py <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/blob/master/test_suite/test_source_sink.py>`
* Suisun marsh radial gate, flashboard and boatlock structures are operated in nonsense ways. For instance:
	the radial gates (montezuma_radial) are operated tidally while the flashboards (montezuma_flashboards) are out. This is an example of domain-specific insight. One of the issues of course is that run checks may slow down users in developing strong knowledge of the region. 
* Legacy files such as param.nml or flow_xsects.yaml are used in runs without reviewing them for and out-of-date entries.
* elev2D.th.nc start date matches param.nml start date, see `test_elev2d.py <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/blob/master/test_suite/test_elev2d.py>`



