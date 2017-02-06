"""Contains test groups for cycles with easily verified values/derivatives.

The Group contains the following components:
    - 'first'
    - (num_comp - 2 copies of) 'middle_i'
    - 'last'

Components other than the 'last' component take an input vector and rotate that vector by a
specified angle in the plane spanned by [1, 0, ..., 0, 1] and [0, 1, ..., 1, 0]. 'first' takes a
parameter 'psi' that corresponds to the initial rotation. The middle components use the rotation
angle specified by 'theta'. All components (including 'first' and 'last') have an output 'theta_out'
that is used to pass the 'theta' angle to the next component. The goal of this group is to determine
a value for 'theta' such that
    psi + (num_comp-1)*theta = 0 (mod 2*pi),
i.e., an angle 'theta' such that rotations by the non-first components would return the vector to
its original location. The 'last' component computes a new value for 'theta_out' that has 1/2 the
error as the input 'theta'. 'last.theta_out' is connected to 'first.theta' to form a cycle and the
reduction of error by 1/2 ensures Gauss-Seidel type methods will converge.

To provide support for multiple variables/variable sizes, the vector is constructed from the inputs
by taking the inputs in order (e.g. x_0, x_1, ...), flattening the array, and concatenating those
arrays into one vector. The outputs y_i are constructed in the reverse manner.

Note: 'theta' is unique only up to equivalence mod (2*pi)/(num_comp - 1). Test authors should not
depend on particular values of 'theta' (or 'x_i'/'y_i' values) without taking this in to account.
"""

from __future__ import print_function, division
from six.moves import range
import numpy as np

from openmdao.api import IndepVarComp
from openmdao.test_suite.groups.parametric_group import ParametericTestGroup
from openmdao.test_suite.components.cycle_comps import PSI, ExplicitCycleComp, ExplicitFirstComp,\
    ExplicitLastComp


class CycleGroup(ParametericTestGroup):
    """Group with a cycle. Derivatives and values are known."""

    def __init__(self, **kwargs):
        super(CycleGroup, self).__init__(**kwargs)

        self.default_params.update({
            'component_class': ['explicit'],
            'connection_type': ['implicit', 'explicit'],
            'partial_type': ['array', 'sparse', 'aij'],
            'num_comp': [3, 2],
            'num_var': [3, 1],
            'var_shape': [(2, 3), (3,)],
        })

    def _initialize_metadata(self):
        self.metadata.declare('num_comp', type_=int, value=2,
                              desc='Total number of components')
        self.metadata.declare('num_var', type_=int, value=1,
                              desc='Number of variables per component')
        self.metadata.declare('var_shape', value=(3,),
                              desc='Shape of each variable')
        self.metadata.declare('connection_type', type_=str, value='explicit',
                              values=['explicit', 'implicit'],
                              desc='How to connect variables.')
        self.metadata.declare('component_class', type_=str, value='explicit',
                              values=['explicit'],
                              desc='Component class to instantiate')
        self.metadata.declare('jacobian_type', value='matvec',
                              values=['matvec', 'dense', 'sparse-coo',
                                      'sparse-csr'],
                              desc='method of assembling derivatives')
        self.metadata.declare('partial_type', value='array',
                              values=['array', 'sparse', 'aij'],
                              desc='type of partial derivatives')

    def initialize(self):
        self._initialize_metadata()

        num_comp = self.metadata['num_comp']
        if num_comp < 2:
            raise ValueError('Number of components must be at least 2.')

        self.num_var = num_var = self.metadata['num_var']
        self.var_shape = var_shape = self.metadata['var_shape']

        self.size = num_var * np.prod(var_shape)
        if self.size < 3:
            raise ValueError('Product of num_var and var_shape must be at least 3.')

        connection_type = self.metadata['connection_type']

        comp_class = self.metadata['component_class']

        if comp_class == 'explicit':
            first_class = ExplicitFirstComp
            middle_class = ExplicitCycleComp
            last_class = ExplicitLastComp
        else:
            raise ValueError('Should not happen or else metadata dict is broken.')

        self._generate_components(connection_type, first_class, middle_class, last_class, num_comp)

        theta_name = 'last.theta_out' if connection_type == 'explicit' else 'theta_0'

        self.total_of = ['last.x_norm2', theta_name]
        self.total_wrt = ['psi_comp.psi']
        self.expected_totals = {
            ('last.x_norm2', 'psi_comp.psi'): 0.,
            (theta_name, 'psi_comp.psi'): -1. / (num_comp - 1),
        }

        expected_theta = (2*np.pi - PSI) / (num_comp - 1)
        self.expected_values = {
            theta_name: expected_theta,
            'last.x_norm2': 0.5*self.size,
        }

    def _generate_components(self, conn_type, first_class, middle_class, last_class, num_comp):
        first_name = 'first'
        last_name = 'last'
        var_shape = self.metadata['var_shape']
        num_var = self.metadata['num_var']
        comp_args = {
            'var_shape': var_shape,
            'num_var': num_var,
            'jacobian_type': self.metadata['jacobian_type'],
            'partial_type': self.metadata['partial_type']
        }

        self.add_subsystem('psi_comp', IndepVarComp('psi', PSI))
        indep_var_comp = self.add_subsystem('x0_comp', IndepVarComp())
        for i in range(num_var):
            indep_var_comp.add_output('x_{0}'.format(i), np.ones(var_shape))

        self._add_cycle_comp(conn_type, first_class, first_name, 0, comp_args)
        prev_name = first_name
        idx = 0

        connection_variables = [('y_{0}'.format(i), 'x_{0}'.format(i)) for i in range(num_var)]
        connection_variables.append(('theta_out', 'theta'))

        # Middle Subsystems
        for idx in range(1, num_comp - 1):
            current_name = 'middle_{0}'.format(idx)
            self._add_cycle_comp(conn_type, middle_class, current_name, idx, comp_args)

            if conn_type == 'explicit':
                self._explicit_connections(prev_name, current_name, connection_variables)

            prev_name = current_name

        # Final Subsystem
        if conn_type == 'explicit':
            self.add_subsystem(last_name, last_class(**comp_args))

            self._explicit_connections(prev_name, last_name, connection_variables)
            self._explicit_connections(last_name, first_name, [('theta_out', 'theta')])

        elif conn_type == 'implicit':
            renames_inputs = {'x_{0}'.format(i): 'x_{0}_{1}'.format(idx + 1, i) for i in range(self.num_var)}
            renames_inputs['theta'] = 'theta_{0}'.format(idx + 1)
            renames_outputs = {
                'theta_out': 'theta_0'
            }
            self.add_subsystem(last_name, last_class(**comp_args),
                               renames_inputs=renames_inputs,
                               renames_outputs=renames_outputs)

        self.connect('psi_comp.psi', first_name + '.psi')
        self.connect('psi_comp.psi', last_name + '.psi')
        if conn_type == 'explicit':
            var_name = first_name + '.x_{0}'
        else:
            var_name = 'x_0_{0}'
        for i in range(num_var):
            self.connect('x0_comp.x_{0}'.format(i), var_name.format(i))

    def _explicit_connections(self, prev_name, current_name, vars):
        for out_var, in_var in vars:
            self.connect(
                '{0}.{1}'.format(prev_name, out_var),
                '{0}.{1}'.format(current_name, in_var)
            )

    def _add_cycle_comp(self, connection_type, comp_class, comp_name, index, comp_args):
        if connection_type == 'explicit':
            self.add_subsystem(comp_name, comp_class(**comp_args))
        elif connection_type == 'implicit':

            renames_inputs = {'x_{0}'.format(i): 'x_{0}_{1}'.format(index, i) for i in range(self.num_var)}
            renames_inputs['theta'] = 'theta_{0}'.format(index)

            renames_outputs = {'y_{0}'.format(i): 'x_{0}_{1}'.format(index + 1, i) for i in range(self.num_var)}
            renames_outputs['theta_out'] = 'theta_{0}'.format(index + 1)

            self.add_subsystem(comp_name, comp_class(**comp_args),
                               renames_inputs=renames_inputs,
                               renames_outputs=renames_outputs)