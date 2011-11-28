#!/usr/bin/env python
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

import sys, os
DIR = os.path.abspath(os.path.normpath(os.path.join(__file__,
    '..', '..', '..', '..', '..', 'trytond')))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))

import unittest
from decimal import Decimal
import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT, test_view,\
    test_depends
from trytond.transaction import Transaction

class ProductTestCase(unittest.TestCase):
    '''
    Test Product module.
    '''

    def setUp(self):
        trytond.tests.test_tryton.install_module('product')
        self.uom = POOL.get('product.uom')
        self.uom_category = POOL.get('product.uom.category')

    def test0005views(self):
        '''
        Test views.
        '''
        test_view('product')

    def test0006depends(self):
        '''
        Test depends.
        '''
        test_depends()

    def test0010uom_non_zero_rate_factor(self):
        '''
        Test uom non_zero_rate_factor constraint.
        '''
        with Transaction().start(DB_NAME, USER,
                context=CONTEXT) as transaction:
            category_id = self.uom_category.create({'name': 'Test'})
            transaction.cursor.commit()

            self.failUnlessRaises(Exception, self.uom.create, {
                'name': 'Test',
                'symbol': 'T',
                'category': category_id,
                'rate': 0,
                'factor': 0,
                })
            transaction.cursor.rollback()

            self.uom.create({
                'name': 'Test',
                'symbol': 'T',
                'category': category_id,
                'rate': 1.0,
                'factor': 1.0,
                })
            transaction.cursor.commit()

            self.failUnlessRaises(Exception, self.uom.write, {
                'rate': 0.0,
                })
            transaction.cursor.rollback()

            self.failUnlessRaises(Exception, self.uom.write, {
                'factor': 0.0,
                })
            transaction.cursor.rollback()

            self.failUnlessRaises(Exception, self.uom.write, {
                'rate': 0.0,
                'factor': 0.0,
                })
            transaction.cursor.rollback()

    def test0020uom_check_factor_and_rate(self):
        '''
        Test uom check_factor_and_rate constraint.
        '''
        with Transaction().start(DB_NAME, USER,
                context=CONTEXT) as transaction:
            category_id = self.uom_category.search([
                ('name', '=', 'Test'),
                ], limit=1)[0]

            self.failUnlessRaises(Exception, self.uom.create, {
                'name': 'Test',
                'symbol': 'T',
                'category': category_id,
                'rate': 2,
                'factor': 2,
                })
            transaction.cursor.rollback()

            uom_id = self.uom.search([
                ('name', '=', 'Test'),
                ], limit=1)[0]

            self.failUnlessRaises(Exception, self.uom.write, uom_id,
                    {
                        'rate': 2.0,
                        })
            transaction.cursor.rollback()

            self.failUnlessRaises(Exception, self.uom.write, uom_id,
                    {
                        'factor': 2.0,
                        })
            transaction.cursor.rollback()

    def test0030uom_select_accurate_field(self):
        '''
        Test uom select_accurate_field function.
        '''
        tests = [
            ('Meter', 'factor'),
            ('Kilometer', 'factor'),
            ('centimeter', 'rate'),
            ('Foot', 'factor'),
        ]
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            for name, result in tests:
                uom_id = self.uom.search([
                    ('name', '=', name),
                    ], limit=1)[0]
                uom = self.uom.browse(uom_id)
                self.assert_(result == self.uom.select_accurate_field(uom))


    def test0040uom_compute_qty(self):
        '''
        Test uom compute_qty function.
        '''
        tests = [
            ('Kilogram', 100, 'Gram', 100000, 100000),
            ('Gram', 1, 'Pound', 0.0022046226218487759, 0.0),
            ('Second', 5, 'Minute', 0.083333333333333343, 0.08),
            ('Second', 25, 'Hour', 0.0069444444444444441, 0.01),
            ('Millimeter', 3, 'Inch', 0.11811023622047245, 0.12),
        ]
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            for from_name, qty, to_name, result, rounded_result in tests:
                from_uom = self.uom.browse(self.uom.search(
                    [
                     ('name', '=', from_name),
                    ], limit=1)[0])
                to_uom = self.uom.browse(self.uom.search(
                    [
                        ('name', '=', to_name),
                    ], limit=1)[0])
                self.assert_(result == self.uom.compute_qty(from_uom,
                    qty, to_uom, False))
                self.assert_(rounded_result == self.uom.compute_qty(
                    from_uom, qty, to_uom, True))

            self.assert_(10 == self.uom.compute_qty(None, 10, to_uom))
            self.assert_(10 == self.uom.compute_qty(None, 10, to_uom, True))
            self.assert_(0 == self.uom.compute_qty(from_uom, 0, to_uom))
            self.assert_(0 == self.uom.compute_qty(from_uom, 0, to_uom, True))
            self.assert_(10 == self.uom.compute_qty(from_uom, 10, None))
            self.assert_(10 == self.uom.compute_qty(from_uom, 10, None, True))

    def test0050uom_compute_price(self):
        '''
        Test uom compute_price function.
        '''
        tests = [
            ('Kilogram', Decimal('100'), 'Gram', Decimal('0.1')),
            ('Gram', Decimal('1'), 'Pound', Decimal('453.59237')),
            ('Second', Decimal('5'), 'Minute', Decimal('300')),
            ('Second', Decimal('25'), 'Hour', Decimal('90000')),
            ('Millimeter', Decimal('3'), 'Inch', Decimal('76.2')),
        ]
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            for from_name, price, to_name, result in tests:
                from_uom = self.uom.browse(self.uom.search(
                    [
                        ('name', '=', from_name),
                    ], limit=1)[0])
                to_uom = self.uom.browse(self.uom.search(
                    [
                        ('name', '=', to_name),
                    ], limit=1)[0])
                self.assert_(result == self.uom.compute_price(from_uom,
                    price, to_uom))

def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        ProductTestCase))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
