""" Unit tests for the problem interface."""

import unittest
import os
import json

import errno
from shutil import rmtree
from tempfile import mkdtemp

from openmdao.core.problem import Problem
from openmdao.test_suite.components.sellar import SellarStateConnection
from openmdao.visualization.n2_viewer.n2_viewer import _get_viewer_data, n2
from openmdao.recorders.sqlite_recorder import SqliteRecorder
from openmdao.utils.shell_proc import check_call


# set DEBUG to True if you want to view the generated HTML file(s)
DEBUG = False


class TestViewModelData(unittest.TestCase):

    def setUp(self):
        if not DEBUG:
            self.dir = mkdtemp()
        else:
            self.dir = os.getcwd()

        self.sqlite_db_filename = os.path.join(self.dir, "sellarstate_model.sqlite")
        self.sqlite_db_filename2 = os.path.join(self.dir, "sellarstate_model_view.sqlite")
        self.sqlite_html_filename = os.path.join(self.dir, "sqlite_n2.html")
        self.problem_html_filename = os.path.join(self.dir, "problem_n2.html")

        self.expected_tree = json.loads('{"name": "root", "type": "root", "class": "SellarStateConnection", "component_type": null, "subsystem_type": "group", "is_parallel": false, "linear_solver": "LN: SCIPY", "nonlinear_solver": "NL: Newton", "children": [{"name": "px", "type": "subsystem", "class": "IndepVarComp", "subsystem_type": "component", "is_parallel": false, "component_type": "indep", "linear_solver": "", "nonlinear_solver": "", "children": [{"name": "x", "type": "unknown", "implicit": false, "dtype": "ndarray"}]}, {"name": "pz", "type": "subsystem", "class": "IndepVarComp", "subsystem_type": "component", "is_parallel": false, "component_type": "indep", "linear_solver": "", "nonlinear_solver": "", "children": [{"name": "z", "type": "unknown", "implicit": false, "dtype": "ndarray"}]}, {"name": "sub", "type": "subsystem", "class": "Group", "component_type": null, "subsystem_type": "group", "is_parallel": false, "linear_solver": "LN: SCIPY", "nonlinear_solver": "NL: RUNONCE", "children": [{"name": "state_eq_group", "type": "subsystem", "class": "Group", "component_type": null, "subsystem_type": "group", "is_parallel": false, "linear_solver": "LN: SCIPY", "nonlinear_solver": "NL: RUNONCE", "children": [{"name": "state_eq", "type": "subsystem", "class": "StateConnection", "subsystem_type": "component", "is_parallel": false, "component_type": "implicit", "linear_solver": "", "nonlinear_solver": "", "children": [{"name": "y2_actual", "type": "param", "dtype": "ndarray"}, {"name": "y2_command", "type": "unknown", "implicit": true, "dtype": "ndarray"}]}]}, {"name": "d1", "type": "subsystem", "class": "SellarDis1withDerivatives", "subsystem_type": "component", "is_parallel": false, "component_type": "explicit", "linear_solver": "", "nonlinear_solver": "", "children": [{"name": "z", "type": "param", "dtype": "ndarray"}, {"name": "x", "type": "param", "dtype": "ndarray"}, {"name": "y2", "type": "param", "dtype": "ndarray"}, {"name": "y1", "type": "unknown", "implicit": false, "dtype": "ndarray"}]}, {"name": "d2", "type": "subsystem", "class": "SellarDis2withDerivatives", "subsystem_type": "component", "is_parallel": false, "component_type": "explicit", "linear_solver": "", "nonlinear_solver": "", "children": [{"name": "z", "type": "param", "dtype": "ndarray"}, {"name": "y1", "type": "param", "dtype": "ndarray"}, {"name": "y2", "type": "unknown", "implicit": false, "dtype": "ndarray"}]}]}, {"name": "obj_cmp", "type": "subsystem", "class": "ExecComp", "subsystem_type": "component", "is_parallel": false, "component_type": "exec", "linear_solver": "", "nonlinear_solver": "", "children": [{"name": "x", "type": "param", "dtype": "ndarray"}, {"name": "y1", "type": "param", "dtype": "ndarray"}, {"name": "y2", "type": "param", "dtype": "ndarray"}, {"name": "z", "type": "param", "dtype": "ndarray"}, {"name": "obj", "type": "unknown", "implicit": false, "dtype": "ndarray"}]}, {"name": "con_cmp1", "type": "subsystem", "class": "ExecComp", "subsystem_type": "component", "is_parallel": false, "component_type": "exec", "linear_solver": "", "nonlinear_solver": "", "children": [{"name": "y1", "type": "param", "dtype": "ndarray"}, {"name": "con1", "type": "unknown", "implicit": false, "dtype": "ndarray"}]}, {"name": "con_cmp2", "type": "subsystem", "class": "ExecComp", "subsystem_type": "component", "is_parallel": false, "component_type": "exec", "linear_solver": "", "nonlinear_solver": "", "children": [{"name": "y2", "type": "param", "dtype": "ndarray"}, {"name": "con2", "type": "unknown", "implicit": false, "dtype": "ndarray"}]}]}')
        self.expected_pathnames = json.loads('["sub.d1", "sub.d2", "sub.state_eq_group.state_eq"]')
        self.expected_conns = json.loads("""
            [
                {"src": "sub.d1.y1", "tgt": "con_cmp1.y1"},
                {"src": "sub.d2.y2", "tgt": "con_cmp2.y2"},
                {"src": "px.x", "tgt": "obj_cmp.x"},
                {"src": "sub.d1.y1", "tgt": "obj_cmp.y1"},
                {"src": "sub.d2.y2", "tgt": "obj_cmp.y2"},
                {"src": "pz.z", "tgt": "obj_cmp.z"},
                {"src": "px.x", "tgt": "sub.d1.x"},
                {"src": "sub.state_eq_group.state_eq.y2_command", "tgt": "sub.d1.y2"},
                {"src": "pz.z", "tgt": "sub.d1.z"},
                {"src": "sub.d1.y1", "tgt": "sub.d2.y1"},
                {"src": "pz.z", "tgt": "sub.d2.z"},
                {"src": "sub.d2.y2", "tgt": "sub.state_eq_group.state_eq.y2_actual", "cycle_arrows": ["sub.d1 sub.d2", "sub.state_eq_group.state_eq sub.d1"]}
            ]
        """)
        self.expected_abs2prom = json.loads("""
            {
                "input": {
                    "sub.state_eq_group.state_eq.y2_actual": "state_eq.y2_actual",
                    "sub.d1.z": "z",
                    "sub.d1.x": "x",
                    "sub.d1.y2": "d1.y2",
                    "sub.d2.z": "z",
                    "sub.d2.y1": "y1",
                    "obj_cmp.x": "x",
                    "obj_cmp.y1": "y1",
                    "obj_cmp.y2": "obj_cmp.y2",
                    "obj_cmp.z": "z",
                    "con_cmp1.y1": "y1",
                    "con_cmp2.y2": "con_cmp2.y2"
                },
                "output": {
                    "px.x": "x",
                    "pz.z": "z",
                    "sub.state_eq_group.state_eq.y2_command": "state_eq.y2_command",
                    "sub.d1.y1": "y1",
                    "sub.d2.y2": "d2.y2",
                    "obj_cmp.obj": "obj",
                    "con_cmp1.con1": "con1",
                    "con_cmp2.con2": "con2"
                }
            }
        """)

    def tearDown(self):
        if not DEBUG:
            try:
                rmtree(self.dir)
            except OSError as e:
                # If directory already deleted, keep going
                if e.errno not in (errno.ENOENT, errno.EACCES, errno.EPERM):
                    raise e

    def test_model_viewer_has_correct_data_from_problem(self):
        """
        Verify that the correct model structure data exists when stored as compared
        to the expected structure, using the SellarStateConnection model.
        """
        p = Problem(model=SellarStateConnection())
        p.setup()

        model_viewer_data = _get_viewer_data(p)

        # check expected model tree
        self.assertDictEqual(model_viewer_data['tree'], self.expected_tree)

        # check expected system pathnames
        pathnames = model_viewer_data['sys_pathnames_list']
        self.assertListEqual(sorted(pathnames), self.expected_pathnames)

        # check expected connections, after mapping cycle_arrows indices back to pathnames
        connections = sorted(model_viewer_data['connections_list'], key=lambda x: (x['tgt'], x['src']))
        for conn in connections:
            if 'cycle_arrows' in conn and conn['cycle_arrows']:
                cycle_arrows = []
                for src, tgt in conn['cycle_arrows']:
                    cycle_arrows.append(' '.join([pathnames[src], pathnames[tgt]]))
                conn['cycle_arrows'] = sorted(cycle_arrows)
        self.assertEqual(len(connections), len(self.expected_conns))
        for c, ex in zip(connections, self.expected_conns):
            self.assertEqual(c['src'], ex['src'])
            self.assertEqual(c['tgt'], ex['tgt'])
            self.assertEqual(c.get('cycle_arrows', []), ex.get('cycle_arrows', []))

        # check expected abs2prom map
        self.assertDictEqual(model_viewer_data['abs2prom'], self.expected_abs2prom)

    def test_model_viewer_has_correct_data_from_sqlite(self):
        """
        Verify that the correct data exists when a model structure is recorded
        and then pulled out of a sqlite db file and compared to the expected
        structure.  Uses the SellarStateConnection model.
        """
        p = Problem(model=SellarStateConnection())

        r = SqliteRecorder(self.sqlite_db_filename)
        p.driver.add_recorder(r)

        p.setup()
        p.final_setup()
        r.shutdown()

        model_viewer_data = _get_viewer_data(self.sqlite_db_filename)
        print(model_viewer_data['tree'])

        # check expected model tree
        self.assertDictEqual(model_viewer_data['tree'], self.expected_tree)

        # check expected system pathnames
        pathnames = model_viewer_data['sys_pathnames_list']
        self.assertListEqual(sorted(pathnames), self.expected_pathnames)

        # check expected connections, after mapping cycle_arrows indices back to pathnames
        connections = sorted(model_viewer_data['connections_list'], key=lambda x: (x['tgt'], x['src']))
        for conn in connections:
            if 'cycle_arrows' in conn:
                cycle_arrows = []
                for src, tgt in conn['cycle_arrows']:
                    cycle_arrows.append(' '.join([pathnames[src], pathnames[tgt]]))
                conn['cycle_arrows'] = sorted(cycle_arrows)
        self.assertEqual(len(connections), len(self.expected_conns))
        for c, ex in zip(connections, self.expected_conns):
            self.assertEqual(c['src'], ex['src'])
            self.assertEqual(c['tgt'], ex['tgt'])
            self.assertEqual(c.get('cycle_arrows', []), ex.get('cycle_arrows', []))

        # check expected abs2prom map
        self.assertDictEqual(model_viewer_data['abs2prom'], self.expected_abs2prom)

    def test_n2_from_problem(self):
        """
        Test that an n2 html file is generated from a Problem.
        """
        p = Problem()
        p.model = SellarStateConnection()
        p.setup()
        n2(p, outfile=self.problem_html_filename, show_browser=DEBUG)

        # Check that the html file has been created and has something in it.
        self.assertTrue(os.path.isfile(self.problem_html_filename),
                        (self.problem_html_filename + " is not a valid file."))
        self.assertGreater(os.path.getsize(self.problem_html_filename), 100)

    def test_n2_from_sqlite(self):
        """
        Test that an n2 html file is generated from a sqlite file.
        """
        p = Problem()
        p.model = SellarStateConnection()
        r = SqliteRecorder(self.sqlite_db_filename2)
        p.driver.add_recorder(r)
        p.setup()
        p.final_setup()
        r.shutdown()
        n2(self.sqlite_db_filename2, outfile=self.sqlite_html_filename, show_browser=DEBUG)

        # Check that the html file has been created and has something in it.
        self.assertTrue(os.path.isfile(self.sqlite_html_filename),
                        (self.problem_html_filename + " is not a valid file."))
        self.assertGreater(os.path.getsize(self.sqlite_html_filename), 100)

        # Check that there are no errors when running from the command line with a recording.
        check_call('openmdao n2 --no_browser %s' % self.sqlite_db_filename2)

    def test_n2_command(self):
        """
        Check that there are no errors when running from the command line with a script.
        """
        from openmdao.test_suite.scripts import sellar
        filename = os.path.abspath(sellar.__file__).replace('.pyc', '.py')  # PY2
        check_call('openmdao n2 --no_browser %s' % filename)

    def test_n2_set_title(self):
        """
        Test that an n2 html file is generated from a Problem.
        """
        p = Problem()
        p.model = SellarStateConnection()
        p.setup()
        n2(p, outfile=self.problem_html_filename, show_browser=DEBUG,
                   title="Sellar State Connection")

        # Check that the html file has been created and has something in it.
        self.assertTrue(os.path.isfile(self.problem_html_filename),
                        (self.problem_html_filename + " is not a valid file."))
        self.assertTrue( 'OpenMDAO Model Hierarchy and N2 diagram: Sellar State Connection' \
                         in open(self.problem_html_filename).read() )


if __name__ == "__main__":
    unittest.main()
