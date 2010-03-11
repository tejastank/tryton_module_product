#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.model.modelstorage import OPERATORS
from trytond.pyson import Not, Bool, Eval
from decimal import Decimal

STATES = {
    'readonly': Not(Bool(Eval('active'))),
}

class UomCategory(ModelSQL, ModelView):
    'Product uom category'
    _name = 'product.uom.category'
    _description = __doc__
    name = fields.Char('Name', required=True, translate=True)
    uoms = fields.One2Many('product.uom', 'category', 'Unit of Measures')

    def __init__(self):
        super(UomCategory, self).__init__()
        self._order.insert(0, ('name', 'ASC'))

UomCategory()


class Uom(ModelSQL, ModelView):
    'Unit of measure'
    _name = 'product.uom'
    _description = __doc__
    name = fields.Char('Name', size=None, required=True, states=STATES,
            translate=True)
    symbol = fields.Char('Symbol', size=10, required=True, states=STATES,
            translate=True)
    category = fields.Many2One('product.uom.category', 'UOM Category',
            required=True, ondelete='RESTRICT', states=STATES)
    rate = fields.Float('Rate', digits=(12, 12), required=True,
            on_change=['rate'], states=STATES,
            help='The coefficient for the formula:\n' \
                    '1 (base unit) = coef (this unit)')
    factor = fields.Float('Factor', digits=(12, 12), states=STATES,
            on_change=['factor'], required=True,
            help='The coefficient for the formula:\n' \
                    'coef (base unit) = 1 (this unit)')
    rounding = fields.Float('Rounding Precision', digits=(12, 12),
            required=True, states=STATES)
    digits = fields.Integer('Display Digits')
    active = fields.Boolean('Active')

    def __init__(self):
        super(Uom, self).__init__()
        self._sql_constraints += [
            ('non_zero_rate_factor', 'CHECK((rate != 0.0) or (factor != 0.0))',
                'Rate and factor can not be both equal to zero.')
        ]
        self._constraints += [
            ('check_factor_and_rate', 'invalid_factor_and_rate'),
        ]
        self._order.insert(0, ('name', 'ASC'))
        self._error_messages.update({
                'change_uom_rate_title': 'You cannot change Rate, Factor or '
                    'Category on a Unit of Measure. ',
                'change_uom_rate': 'If the UOM is still not used, you can '
                    'delete it ortherwise you can deactivate it ' 
                    'and create a new one.',
                'invalid_factor_and_rate': 'Invalid Factor and Rate values!',
            })

    def check_xml_record(self, cursor, user, ids, values, context=None):
        return True

    def default_rate(self, cursor, user, context=None):
        return 1.0

    def default_factor(self, cursor, user, context=None):
        return 1.0

    def default_active(self, cursor, user, context=None):
        return 1

    def default_rounding(self, cursor, user, context=None):
        return 0.01

    def default_digits(self, cursor, user, context=None):
        return 2

    def default_category(self, cursor, user, context=None):
        category_obj = self.pool.get('product.uom.category')
        product_obj = self.pool.get('product.product')
        if context is None:
            context = {}
        if 'category' in context:
            if isinstance(context['category'], (tuple, list)) \
                    and len(context['category']) > 1 \
                    and context['category'][1] in ('uom.category',
                            'product.default_uom.category'):
                if context['category'][1] == 'uom.category':
                    if not context['category'][0]:
                        return False
                    uom  = self.browse(cursor, user, context['category'][0],
                            context=context)
                    return uom.category.id
                else:
                    if not context['category'][0]:
                        return False
                    product = product_obj.browse(cursor, user,
                            context['category'][0], context=context)
                    return product.default_uom.category.id
        return False

    def on_change_factor(self, cursor, user, ids, value, context=None):
        if value.get('factor', 0.0) == 0.0:
            return {'rate': 0.0}
        return {'rate': round(1.0 / value['factor'], self.rate.digits[1])}

    def on_change_rate(self, cursor, user, ids, value, context=None):
        if value.get('rate', 0.0) == 0.0:
            return {'factor': 0.0}
        return {'factor': round(1.0 / value['rate'], self.factor.digits[1])}

    def search_rec_name(self, cursor, user, name, args, context=None):
        args2 = []
        i = 0
        while i < len(args):
            ids = self.search(cursor, user, ['OR',
                (self._rec_name, args[i][1], args[i][2]),
                ('symbol', args[i][1], args[i][2]),
                ], context=context)
            args2.append(('id', 'in', ids))
            i += 1
        return args2

    @staticmethod
    def round(number, precision=1.0):
        return round(number / precision) * precision

    def check_factor_and_rate(self, cursor, user, ids):
        "Check coherence between factor and rate"
        for uom in self.browse(cursor, user, ids):
            if uom.rate == uom.factor == 0.0:
                continue
            if uom.rate != round(1.0 / uom.factor, self.rate.digits[1]) and \
                    uom.factor != round(1.0 / uom.rate, self.factor.digits[1]):
                return False
        return True

    def write(self, cursor, user, ids, values, context=None):
        if user == 0:
            return super(Uom, self).write(cursor, user, ids, values, context)
        if 'rate' not in values and 'factor' not in values \
                and 'category' not in values:
            return super(Uom, self).write(cursor, user, ids, values, context)

        if isinstance(ids, (int, long)):
            ids = [ids]

        uoms = self.browse(cursor, user, ids, context=context)
        old_uom = dict((uom.id, (uom.factor, uom.rate, uom.category.id)) \
                           for uom in uoms)

        res = super(Uom, self).write(cursor, user, ids, values, context)
        uoms = self.browse(cursor, user, ids, context=context)

        for uom in uoms:
            if uom.factor != old_uom[uom.id][0] \
                    or uom.rate != old_uom[uom.id][1] \
                    or uom.category.id != old_uom[uom.id][2]:

                self.raise_user_error(cursor, 'change_uom_rate_title',
                        error_description='change_uom_rate', context=context)
        return res

    def select_accurate_field(self, uom):
        """
        Select the more accurate field.
        It chooses the field that has the least decimal.

        :param uom: a BrowseRecord of UOM.
        :return: 'factor' or 'rate'.
        """
        lengths = {}
        for field in ('rate', 'factor'):
            format = '%%.%df' % getattr(self, field).digits[1]
            lengths[field] = len((format % getattr(uom,
                field)).split('.')[1].rstrip('0'))
        if lengths['rate'] < lengths['factor']:
            return 'rate'
        elif lengths['factor'] < lengths['rate']:
            return 'factor'
        elif uom.factor >= 1.0:
            return 'factor'
        else:
            return 'rate'

    def compute_qty(self, cursor, user, from_uom, qty, to_uom=None,
            round=True, context=None):
        """
        Convert quantity for given uom's.

        :param cursor: the database cursor
        :param user: the user id
        :param from_uom: a BrowseRecord of product.uom
        :param qty: an int or long or float value
        :param to_uom: a BrowseRecord of product.uom
        :param round: a boolean to round or not the result
        :param context: the context
        :return: the converted quantity
        """
        if not from_uom or not qty or not to_uom:
            return qty
        if from_uom.category.id != to_uom.category.id:
            return qty
        if self.select_accurate_field(from_uom) == 'factor':
            amount = qty * from_uom.factor
        else:
            amount = qty / from_uom.rate
        if to_uom is not None:
            if self.select_accurate_field(to_uom) == 'factor':
                amount = amount / to_uom.factor
            else:
                amount = amount * to_uom.rate
            if round:
                amount = self.round(amount, to_uom.rounding)
        return amount

    def compute_price(self, cursor, user, from_uom, price, to_uom=False,
            context=None):
        """
        Convert price for given uom's.

        :param cursor: the database cursor
        :param user: the user id
        :param from_uom: a BrowseRecord of product.uom
        :param price: a Decimal value
        :param to_uom: a BrowseRecord of product.uom
        :param context: the context
        :return: the converted price
        """
        if not from_uom or not price or not to_uom:
            return price
        if from_uom.category.id != to_uom.category.id:
            return price
        factor_format = '%%.%df' % self.factor.digits[1]
        rate_format = '%%.%df' % self.rate.digits[1]

        if self.select_accurate_field(from_uom) == 'factor':
            new_price = price / Decimal(factor_format % from_uom.factor)
        else:
            new_price = price * Decimal(rate_format % from_uom.rate)

        if self.select_accurate_field(to_uom) == 'factor':
            new_price = new_price * Decimal(factor_format % to_uom.factor)
        else:
            new_price = new_price / Decimal(rate_format % to_uom.rate)

        return new_price

    def search(self, cursor, user, args, offset=0, limit=None, order=None,
            context=None, count=False, query_string=False):
        product_obj = self.pool.get('product.product')
        args = args[:]
        def process_args(args):
            i = 0
            while i < len(args):
                #add test for xmlrpc that doesn't handle tuple
                if (isinstance(args[i], tuple) \
                        or (isinstance(args[i], list) and len(args[i]) > 2 \
                        and args[i][1] in OPERATORS)) \
                        and args[i][0] == 'category' \
                        and isinstance(args[i][2], (list, tuple)) \
                        and len(args[i][2]) == 2 \
                        and args[i][2][1] in ('product.default_uom.category',
                                'uom.category'):
                    if not args[i][2][0]:
                        args[i] = ('id', '!=', '0')
                    else:
                        if args[i][2][1] == 'product.default_uom.category':
                            product = product_obj.browse(cursor, user,
                                    args[i][2][0], context=context)
                            category_id = product.default_uom.category.id
                        else:
                            uom = self.browse(cursor, user, args[i][2][0],
                                    context=context)
                            category_id = uom.category.id
                        args[i] = (args[i][0], args[i][1], category_id)
                elif isinstance(args[i], list):
                    process_args(args[i])
                i += 1
        process_args(args)
        return super(Uom, self).search(cursor, user, args, offset=offset,
                limit=limit, order=order, context=context, count=count,
                query_string=query_string)

Uom()
