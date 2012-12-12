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
import os
import logging
import pandas

# Servabit libraries
from generic_pickler import GenericPickler
# import stark

__all__ = ['Bag']

STYPES = (
    'tab',
    'ltab',
    'bodytab',
    'graph',
)


class Bag(GenericPickler):
    ''' This class associates raw data with printing meta-information.

    Bag has the following attributes:
        df: A pandas DataFrame which contains the data.
        cod: The path where the object will be saved as pickle.
        stype: Tipology, one of ('tab' | 'graph'), tells the reporting engine
            wether it should produce a table or a graph from datas.
        LM: Dictionary of meta-information; its keys must be a subset of
            df.columns. For each key there should be a list giving specific
            info to the engine. Depending on the value of stype, LM's lists
            assumes different meanings.
            stype == 'graph', list indexes means:
                0: Role of the column in the graphic, 
                   'lax' = use Series as lable for the x axes
                   'bar' = render Series as a bar plot
                   'plot' = render Serias as a plot
                1: Where the axis must be drown ('dx' for right, or 'sx' for
                   left)
                2: Variable legend
            stype == 'tab', list indexes means:
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
    
    def __init__(self, df, lm=None, cod=None, stype='tab',
                 title=None, footnote=None, 
                 size='square', fontsize=10.0,
                 legend=False, **kwargs):
        # super(Bag, self).__init__(df, lm=lm, cod=cod, stype=stype)
        self._df = df
        self.cod = cod
        self._lm = lm
        self.stype = stype
        self.title = title
        self.footnote = footnote
        self.size = size
        self.fontsize = fontsize
        self.legend = legend
        for key, val in kwargs:
            setattr(self, key, val)

    ##############
    # Properties #
    ##############

    @property
    def lm(self):
        ''' Return a shallow copy of lm ''' 
        # TODO: this isn't neither a shallow nor a deep copy, copy of the lm
        # shold be deep while it encounters nested dictionaries, but it should
        # behaves as shallow when it reaches DataFrames, so.. implement a
        # smart_copy() :)
        return copy.deepcopy(self._lm.copy)

    @lm.setter
    def lm(self, new_lm):
        ''' lm setter:
        Just check lm/df consistency before proceding.
        '''
        if not isinstance(new_lm, dict):
            raise ValueError("lm must be a dictionry '%s' received instead" %\
                             type(new_lm))
        self._lm = new_lm
        self._update()

    @property
    def df(self):
        ''' Return a copy of df selecting just those columns that have some
        metadata in lm
        '''
        return self._df[self.columns]

    @df.setter
    def df(self, df):
        ''' DF settre:
        Just check VD/DF consistency before proceding.
        '''
        if not isinstance(df, pandas.DataFrame):
            raise TypeError(
                "df must be a pandas.DataFrame object, %s received instead",
                type(df))
        self._df = df
        # df changed, re-evaluate calculated data
        self._update()

    @property
    def columns(self):
        return pandas.Index(self._lm.keys())

    @property
    def ix(self):
        return self._df.ix

    ###########
    # Publics #
    ###########
        
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
        # TODO: Why this complexity? Isn't it just:
        #     1) Build a df from modlist with modlist[n][0] as index
        #     2) join DF with modlistdf on index
        #     3) DF[_FR_].fillna('@n')
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
        modlist = [(int(x[0]), x[1]) for x in modlist]
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
