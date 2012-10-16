# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2012 Servabit Srl (<infoaziendali@servabit.it>).
#    Author: Luigi Bidoia (<luigi.bidoia@servabit.it>)
#            Viviana Nero (<viviana.nero@studiabo.it>)    
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as
#    published by the Free Software Foundation, either version 2 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import sys
import os
import logging

# Servabit libraries
from share import GenericPickler

__all__ = ['Bag']

TYPE_VALS = (
    'tab',
    'graph'
)

class Bag(GenericPickler):
    ''' This class associates raw data with printing meta-information.

    Bag has the following attributes:
        df: A pandas DataFrame which contains the data.
        path: The path where the object will be saved as pickle.
        type: Tipology, one of ('tab' | 'graph'), tells the reporting engine
            wether it should produce a table or a graph from datas.
        meta: Dictionary of meta-information; its keys must be a subset of
            df.columns. For each key there should be a list giving specific
            info to the engine. Depending on the value of type, LM's lists
            assumes different meanings.
            type == 'graph', list indexes means:
                0: Role of the column in the graphic, 
                   'lax' = use Series as lable for the x axes
                   'bar' = render Series as a bar plot
                   'plot' = render Serias as a plot
                1: Where the axis must be drown ('dx' for right, or 'sx' for
                   left)
                2: Variable legend
            type == 'tab', list indexes means:
                0: Column relative order
                1: Column layout, uses LaTeX tabularx sintax:
                   [|][<dimensione>]l|c|r[|] 
                2: Column label
                Any other element constitures another level in the table
                header. Different adiacent columns with the same label are
                considered multicolumn. If you want to leave a blanc column,
                just use a label that starts with '@v'.

            example:
            lm = {
               'DAT_MVL': [0, '|c|', '|@v0|', '|Data|'],
               'COD_CON': [4, 'l|', '|@v0|', ' Codice Conto|'],
               'NAM_CON': [5, '2l|', ' @v2|', ' Conto|'],
               'NAM_PAR': [2, '2l|', '|@v0|', ' Partner|'],
               'DBT_MVL': [6, '0.5r|', ' @v2|', ' Dare|'],
               'CRT_MVL': [7, '0.5r|', ' @v2|', ' Avere|'],
               }

    '''   
    
    def __init__(self, df, path=None, bag_type='tab', meta=None, 
                 title=None, footnote=None, 
                 size='square', fontsize=10.0,
                 legend=False, **kwargs):
        self.df = df
        self.path = path
        if bag_type not in TYPE_VALS:
            raise ValueError("bag_type must be one of %s" % TYPE_VALS)
        self.type = bag_type        
        if meta is None:
            meta = {}
        if not set(meta.keys()).issubset(set(df.columns.tolist())):
            raise ValueError("path.keys() must be a subset of df.columns")
        self._meta = meta
        self.title = title
        self.footnote = footnote
        self.size = size
        self.fontsize = fontsize
        self.legend = legend
        for key, val in kwargs:
            setattr(self, key, val)

    def save(self, file_=None):
        if file_ is None:
            file_ = self.path
        if not os.path.exists(os.path.dirname(file_)):
            os.makedirs(os.path.dirname(file_))
        super(Bag, self).save(file_)
        
    def set_format(self, modlist):
        ''' Insert line style modifiers in the DF.
        
        @ param modlist: a list of tuples (row number, modifier). row numbers
            are all referred to the original DF.

        Example: [(0, "@b"), (3, "@g")] will insert a blank row as the
        beginning and will make the forth row bold.

        If a row number is greater than the length of the DataFrame and the
        modifier is "@b" or "@i" a new row is added at the end; otherwhise no
        action is taken.

        If DF has '_OR_' column, its values will be reordered.

        '''
        def cmp_to_key(cmp_or):
            'Convert a cmp= function into a key= function'
            class K(object):
                def __init__(self, obj, *args):
                    self.obj = obj
                def __lt__(self, other):
                    return cmp_or(self.obj, other.obj) < 0
                def __gt__(self, other):
                    return cmp_or(self.obj, other.obj) > 0
                def __eq__(self, other):
                    return cmp_or(self.obj, other.obj) == 0
                def __le__(self, other):
                    return cmp_or(self.obj, other.obj) <= 0
                def __ge__(self, other):
                    return cmp_or(self.obj, other.obj) >= 0
                def __ne__(self, other):
                    return cmp_or(self.obj, other.obj) != 0
            return K
        
        def cmp_modifiers(x, y):
            if x[0] != y[0]:
                return x[0] - y[0]
            else:
                a = x[1]
                b = y[1]
                if a in ("@b", "@i") and not b in ("@b", "@i"):
                    return -1
                elif not a in ("@b", "@i") and b in ("@b", "@i"):
                    return +1
                elif (not a in ("@b", "@i") and not b in ("@b", "@i")) or \
                        (a in ("@b", "@i") and b in ("@b", "@i")):
                    logging.warning(
                        "'_OR_' column, check modifiers for row {0}\
                         e row {1}".format(x[0], y[0]))
                    return 0                    
        delta = 0
        blank_line = pandas.DataFrame([[""]*len(self.df.columns)],
                                      columns=self.df.columns)
        new_modlist = list()
        # ordiniamo la lista di modifiers per il numero di linea
        modlist = map(lambda x: (int(x[0]), x[1]), modlist) # FIXME: what's the use of this?
        modlist.sort(key=cmp_to_key(cmp_modifiers))
        # se è presente la colonna _OR_ considero l'ordine definito in essa
        if "_OR_" in self.df.columns:
            self.df["_OR_"] = self.df["_OR_"].map(int)
            self.df = self.df.sort(["_OR_"])
            self.df = self.df.reset_index(True)
        for line, modifier in modlist:
            line += delta
            if line > len(self.df):
                line = len(self.df)         
            if modifier in ("@b", "@i"):       
                self.df = pandas.concat([self.df[:line], 
                                         blank_line, 
                                         self.df[line:]])
                self.df = self.df.reset_index(True)
                delta += 1
            new_modlist.append((line, modifier))
        # setto il valore di default per la colonna _FR_ se non esiste
        if "_FR_" not in self.df.columns:
            self.df["_FR_"] = "@n"
        # aggiungo i modificatori
        for line, modifier in new_modlist:
            if line >= len(self.df):
                continue
            self.df["_FR_"][line] = modifier
        # aggiorno la colonna _OR_
        if "_OR_" in self.df.columns:
            self.df["_OR_"] = range(len(self.df))

    @property
    def meta(self):
        return self._meta

    @meta.setter
    def meta(self, lm):
        if lm is None:
            lm = {}
        if not set(lm.keys()).issubset(set(self.df.columns.tolist())):
            raise ValueError("meta.keys() must be a subset of df.columns")
        self._meta = lm
