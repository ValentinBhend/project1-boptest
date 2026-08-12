# -*- coding: utf-8 -*-
"""
This module implements unit tests testcase.py.

"""

import os
import unittest
import numpy as np
import pandas as pd
import testcase
import utilities

testing_root_dir = os.path.join(utilities.get_root_path(), 'testing')

reference_result_directory = 'testcase'

class Advance(unittest.TestCase, utilities.partialChecks):
    '''Unit tests for the testcase.TestCase.advance API.

    '''

    def test_check_input_for_zero(self):
        '''Test that an overwrite value of 0 given in float is used.

        '''

        self.testcase.set_step(60)
        # Advance first wih fan speed of 0.5, then with fan speed of 0.0.
        u = {'fcu_oveFan_u': 0.5,
             'fcu_oveFan_activate':1}
        status, message, payload = self.testcase.advance(u)
        u = {'fcu_oveFan_u': 0.0,
             'fcu_oveFan_activate':1}
        status, message, payload = self.testcase.advance(u)
        # Get results
        status, message, payload = self.testcase.get_results(['fcu_reaPFan_y', 'fcu_oveFan_u'],
                                                             0,
                                                             payload['time'])
        # Test results
        df = pd.DataFrame(payload).set_index('time')
        ref_filepath = os.path.join(testing_root_dir, 'references', reference_result_directory, 'check_input_for_zero.csv')
        self.compare_ref_timeseries_df(df, ref_filepath)

    def setUp(self):
        '''Set up for unit tests.  Uses bestest_air.

        '''

        os.chdir(os.path.join(testing_root_dir))
        os.chdir('..')
        from testcase import TestCase
        self.testcase = TestCase(fmupath='testcases/bestest_air/models/wrapped.fmu')

class WarmupInterval(unittest.TestCase, utilities.partialChecks):
    '''Unit tests for the warmup simulation grid option of initialize.

    '''

    def test_default_is_thirty(self):
        '''Test that the warmup grid is 30 s unless asked otherwise, which is
        the behaviour of earlier BOPTEST versions.

        '''

        self.testcase.initialize(24*3600, 3600)
        times = np.array(self.testcase.y_store['time'])
        warmup = times[times <= 24*3600]
        np.testing.assert_array_equal(np.unique(np.diff(warmup)), [30])

    def test_rejects_invalid(self):
        '''Test that a grid that is not a positive number is refused with a 400
        rather than producing a division by zero deep in the simulation.

        '''

        for value in [0, -30, 'abc']:
            status, message, payload = \
                self.testcase.initialize(24*3600, 3600, warmup_interval=value)
            self.assertEqual(status, 400)
            self.assertEqual(payload, None)
            self.assertTrue('warmup_interval' in message)

    def test_only_the_warmup_grid_changes(self):
        '''Test that the option coarsens the warmup period only, and leaves
        the test period on the mandated 30 s grid that the KPIs integrate
        over.

        '''

        start_time, warmup_period, step, nsteps = 24*3600, 3600, 900, 4
        for warmup_interval in [30, 900]:
            self.testcase.initialize(start_time, warmup_period,
                                     warmup_interval=warmup_interval)
            self.testcase.set_step(step)
            for _ in range(nsteps):
                self.testcase.advance(u={})

            times = np.array(self.testcase.y_store['time'])
            warmup_times = times[times <= start_time]
            test_times = times[times >= start_time]

            np.testing.assert_array_equal(
                np.unique(np.diff(warmup_times)), [warmup_interval],
                'The warmup period should be recorded on the requested grid.')
            np.testing.assert_array_equal(
                np.unique(np.diff(test_times)), [30],
                'The test period must stay on the 30 s grid whatever the '
                'warmup grid is.')
            self.assertEqual(test_times[0], start_time)
            self.assertEqual(test_times[-1], start_time + nsteps*step)

    def test_kpi_integration_still_starts_at_the_start_time(self):
        '''Test that the KPI calculator excludes the warmup samples whatever
        grid they were recorded on.  It selects them by time rather than by
        counting samples, so a coarser warmup grid must not shift the point
        the integration begins at.

        '''

        start_time, warmup_period = 24*3600, 3600
        for warmup_interval in [30, 900]:
            self.testcase.initialize(start_time, warmup_period,
                                     warmup_interval=warmup_interval)
            self.testcase.cal.initialize()
            i = self.testcase.cal.i_last_tdis
            self.assertTrue(self.testcase.y_store['time'][i] >= start_time)
            self.assertTrue(self.testcase.y_store['time'][i-1] < start_time)

    def setUp(self):
        '''Set up for unit tests.  Uses bestest_air.

        '''

        os.chdir(os.path.join(testing_root_dir))
        os.chdir('..')
        from testcase import TestCase
        self.testcase = TestCase(fmupath='testcases/bestest_air/models/wrapped.fmu')


if __name__ == '__main__':
    utilities.run_tests(os.path.basename(__file__))
