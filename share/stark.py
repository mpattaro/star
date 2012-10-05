# -*- coding: utf-8 -*-
##############################################################################
#    
#    Copyright (C) 2012 Servabit Srl (<infoaziendali@servabit.it>).
#    Author: Luigi Cirillo (<luigi.cirillo@servabit.it>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################
__version__ = '0.9'
__author__ = ['Luigi Cirillo (<luigi.cirillo@servabit.it>)',
              'Marco Pattaro (<marco.pattaro@servabit.it>)']
__all__ = ['Stark']

import sys
import os 
import pandas
import numpy
import copy 
import string

BASEPATH = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        os.path.pardir))
sys.path.append(BASEPATH)
sys.path = list(set(sys.path))
from share import GenericPickler

TI_VALS = (
    'elab'
)

TIP_VALS = ['D', 'N', 'S', 'R']

OPERATORS = {
    '+' : '__add__',
    '-' : '__sub__',
    '*' : '__mul__',
    '/' : '__div__',
    '//': '__floordiv__',
    '**': '__pow__',
    '%' : '__mod__',
}

class Stark(GenericPickler):
    ''' This is the artifact that outputs mainly from etl procedures. It is a
    collection of meta-information around datas inside a pandas DataFrame.

    Stark has the following attributes:
        DF: a pandas DataFrame
        LD: the path where the object will be saved as pickle
        TI: type (just 'elab' for now)
        VD: a a dictionary of various info for the user; keys are DF columns
        names, each key contain a dictionary with the following keys.
            TIP: data use, one of (D|N|S|R), that stands for:
                Dimension: can be used in aggregation (like groupby)
                Numeric: a numeric data type
                String: a string data type
                Calculated: (Ricavato in Italian)
            DES: a short description
            MIS: unit of measure
            ELA: elaboration that ptocuced the data (if TIP == 'R')

    '''

    def __init__(self, DF, LD=None, TI='elab', VD=None):
        self._DF = DF
        self.LD = LD
        if TI not in TI_VALS:
            raise ValueError("TI must be one of %s" % TI_VALS)
        self.TI = TI
        if VD is None:
            VD = {}
        if not set(VD.keys()).issubset(set(DF.columns.tolist())):
            raise ValueError("VD.keys() must be a subset of DF.columns")
        self._VD = VD
        self._update_vd()

    def _update_vd(self):
        ''' Call this method every time VD is changed to update Stark data
        ''' 
        self._dim = list()
        self._cal = list()
        self._num = list()
        for key, val in self._VD.iteritems():
            if val['TIP'] == 'D':
                self._dim.append(key)
            elif val['TIP'] == 'R':
                self._cal.append(key)
            elif val['TIP'] == 'N':
                self._num.append(key)
            elif val['TIP'] == 'S':
                self._str.append(key)
                
    @property
    def VD(self):
        return self._VD

    @VD.setter
    def VD(self, vd):
        ''' VD setter:
        Just check VD/DF consistency before proceding.
        ''' 
        if vd is None:
            vd = {}
        if not set(vd.keys()).issubset(set(self.DF.columns.tolist())):
            raise ValueError("vd.keys() must be a subset of DF.columns")
        self._VD = vd
        self._update_vd()

    @property
    def DF(self):
        return self._DF

    @DF.setter
    def DF(self, df):
        ''' DF settre:
        Just check VD/DF consistency before proceding.
        '''
        if not set(self._VD.keys()).issubset(set(df.columns.tolist())):
            raise ValueError("VD.keys() must be a subset of DF.columns")
        self._DF = df

    def update_vd(self, key, entry):
        ''' Update VD dictionary with a new entry.
        
        @ param key: new key in the dictionary
        @ param entry: value to assign
        @ raise ValueError: if DF/VD consistency would broke

        '''
        # Check key consistency
        if key not in self._DF.columns.tolist():
            raise ValueError("VD.keys() must be a subset of DF.columns")
        # TODO: check entry consistency
        self._VD[key] = entry
        self._update_vd()

    def update_df(self, col, series=None, var_type='N', expr=None, des=None, mis=None):
        ''' Utility method to safely add/update a DataFrame column.
        
        Add or modify a column of the DataFrame trying to preserve DF/VD
        consistency. This method has two main beheviours:
            1 - When passing an already calculated series or list to assign to
                a column, it consequently modify the VD.
            2 - When passing an expression, the new column is automatically
                calculated and assinged; finally the VD is updated.

        @ param col: Column's name
        @ param series: Series or list or any other type accepted as DataFrame
            column.
        @ param var_type: One of VD TIP values, if it's 'R' an expr must not be
            None
        @ param expr: The expression to calculate the column's value, it can
            either be a string or a tuple.
        @ param des: Descriprion
        @ param mis: Unit of measure.
        @ raise ValueError: when parameters are inconsistent

        '''
        if var_type not in TIP_VALS:
            raise ValueError("var_type mut be one of [%s]" % '|'.join(TIP_VALS))
        if expr is None and var_type == 'R':
            raise ValueError("You must specify an expression for var_type = 'R'")
        elif series is None and var_type != 'R':
            raise ValueError("You must pass a series or list for var_type != 'R'")        
        if var_type == 'R':
            try:
                self._DF[col] = Stark.eval(expr, df=self._DF)
            except AttributeError:
                self._DF[col] = Stark.eval_polish(expr, df=self._DF)
        else:
            self._DF[col] = series
        self.update_vd(col, {
                'TIP' : var_type,
                'DES' : des,
                'MIS' : mis,
                'ELA' : expr})

    def save(self, file_=None):
        if file_ is None:
            file_ = self.LD
        if not os.path.exists(os.path.dirname(file_)):
            os.makedirs(os.path.dirname(file_))
        super(Stark, self).save(file_)

    @staticmethod
    def eval(func, df):
        ''' Evaluate a function with DataFrame columns'es placeholders.
        
        Without placeholders this function is just a common python eval; when
        func contains column's names preceded by '$', this will be substituted
        with actual column's reference bevore passing the whole string to
        eval().

        @ param func: a string rappresenting a valid python statement; the
            string can containt DataFrame columns'es placeholders in the form
           of '$colname'
        @ param df: DataFrame to apply function to.
        @ return: eval(func) return value

        Example:
            "$B / $C * 100"
        
        '''
        if not isinstance(func, str) or isinstance(func, unicode):
            raise AttributeError(
                'func must be a string, %s received instead.' % type(func).__name__)
        templ = string.Template(func)
        ph_dict = {}
        ph_list = [ph[1] for ph in string.Template.pattern.findall(func)]
        for ph in ph_list:
            ph_dict[ph] = str().join(["df['", ph, "']"])
        return eval(templ.substitute(ph_dict))

    @staticmethod
    def eval_polish(func, df):
        ''' Parse and execute a statement in polish notation.

        Statemenst must be expressed in a Lisp-like manner, but uing python
        tuples. If any dataframe's column is part of the statement, the
        column's name can be expressed as a string in the statement.
        
        @ param func: function in polish notation
        @ param df: DataFrame containing columns to which func refears to
        @ return: function result

        Example:
            ('mul', ('div', 'B', 'C'), 100) # where 'B' and 'C' are in
                                            # df.columns
        Is the same as:
            df['B'] / df['C'] * 100

        '''
        # Some input checks
        if not isinstance(func, tuple):
            raise AttributeError(
                'func must be a tuple, %s teceived instead.' % type(func).__name__)
        if len(func) < 2:
            raise AttributeError(
                'func must have at last two elements (an operator and a term), received %s' % len(func))
        if df is None:
            df = pandas.DataFrame()
        op = func[0]
        if op in OPERATORS.keys():
            op = OPERATORS[op]
        else:
            op = '__%s__' % func[0]
        terms = list()
        # Evaluate
        for idx in range(1, len(func)):
            if hasattr(func[idx], '__iter__'): # recursive step
                terms.append(Stark.eval_polish(func[idx], df))
            elif func[idx] in df.columns: # df col
                terms.append(df[func[idx]])
            else: # literal
                terms.append(func[idx])
        try:
            return terms[0].__getattribute__(op)(terms[1])
        except (IndexError, TypeError):
            return terms[0].__getattribute__(op)()
            
    def aggregate(self, func='sum', dim=None, var=None):
        ''' Apply an aggregation function to the DataFrame. If the DataFrame
        contains datas that are calculated as a transformation of other columns
        from the same DataFrame, this will be re-calculated in the output one.

        The user can specify which dimension should be used in the grouping
        operation and which columns must appear int the output DataFrame.

        @ param func: function used to aggregate, can be either a string or a
            function name.
        @ param dim: name, or list of names, of DataFrame's columns that act as
            dimensions (can be used as indexes, from pandas point of view).
        @ param var: name, or list of names, of DataFrame's columns that we
            want to be part of the resulting DataFrame. If calculated columns
            are in this list, also those from which they are evaluated must be
            present.
        @ return: a new Stark instance with aggregated data

        '''
        if dim is None:
            dim = self._dim
        if var is None:
            var = self._num + self._cal
        # var and dim may be single column's name
        if isinstance(var, str) or isinstance(var, unicode):
            var = [var]
        if isinstance(dim, str) or isinstance(dim, unicode):
            dim = [dim]
        outkeys = dim + var
        group = self._DF.groupby(dim)
        # Create aggregate df
        # Trying to avoid dispatching ambiguity
        try:
            df = group.aggregate(func)[var].reset_index()
        except AttributeError:
            df = group.aggregate(eval(func))[var].reset_index()
        # re-evaluate calculated values
        for key in self._cal:
            if (key in outkeys) and (self._VD[key]['TIP'] == 'R'):
                try:
                    df[key] = Stark.eval(self._VD[key]['ELA'], df)
                except AttributeError:
                    df[key] = Stark.eval_polish(self._VD[key]['ELA'], df)
        # prepare new VD
        vd = dict()
        for key in outkeys:
            vd[key] = copy.deepcopy(self._VD[key])
        # pack up everithing and return
        return Stark(df, VD=vd)

    def agg(self, func='sum', dim=None, var=None):
        ''' Alias to Stark.aggregate()
        ''' 
        return self.aggregate(func=func, dim=dim, var=var)

        
if __name__ == '__main__' :
    ''' Test
    ''' 
    cols = ['B', 'C']
    countries = numpy.array([
        ('namerica', 'US'),
        ('europe', 'UK'),
        ('europe', 'GR'),
        ('europe', 'IT'),
        ('asia', 'JP'),
        ('samerica', 'BR'),
        ])
    nelems = 100
    key = map(tuple, countries[numpy.random.randint(0, len(countries), nelems)])
    index = pandas.MultiIndex.from_tuples(key, names=['region', 'country'])
    df = pandas.DataFrame(
        numpy.random.randn(nelems, len(cols)), columns=cols,
        index=index).sortlevel().reset_index()

    vd = {
        'region' : {'TIP': 'D',
               'DES': 'This is a dimension',
               'MIS': None,
               'ELA': None,},
        'country' : {'TIP': 'D',
               'DES': 'Another one',
               'MIS': None,
               'ELA': None,},
        'B' : {'TIP': 'N',
               'DES': 'Lo! a numeric!',
               'MIS': 'Bagigi',
               'ELA': None,},
        'C' : {'TIP': 'N',
               'DES': 'You are getting boring now!',
               'MIS': 'Noci',
               'ELA': None,},
        'D' : {'TIP': 'R',
               'DES': 'P != NP',
               'MIS': 'Cocce di bagigio',
               'ELA' : "$B / $C * 100"},
        'E' : {'TIP': 'R',
               'DES': 'P != NP',
               'MIS': 'Cocce di bagigio',
               'ELA': ('*', ('/', 'B', 'C'), 100)}
        }

    df['D'] = Stark.eval(vd['D']['ELA'], df)
    df['E'] = Stark.eval_polish(vd['E']['ELA'], df)
    s = Stark(df, VD=vd)
    s1 = s.aggregate(numpy.mean)
