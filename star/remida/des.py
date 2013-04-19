# -*- coding: utf-8 -*-

###############################################################################
#
#    Copyright (C) 2012 Servabit Srl (<infoaziendali@servabit.it>).
#    Author: Luigi Curzi <tremst@gmail.com>
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
###############################################################################

import os
import sys
import logging
import traceback as trb
import des_engines as de
import des_objects as do
import utils as ut
import decimal as dc

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), 
                                        os.path.pardir))

sys.path.append(BASEPATH)
sys.path = list(set(sys.path))


def convert_data(data):
    if isinstance(data, str):
        return unicode(data, "utf8")
    elif isinstance(data, dict):
        return dict(convert_data((k, v)) for k, v in data.iteritems())
    elif isinstance(data, (list, tuple)):
        return type(data)([convert_data(e) for e in data])
    else:
        try:
            data = dc.Decimal(str(data))
        except TypeError:
            pass
        return data
                           

def convert_df(df):
    try:
        return convert_data(dict((k, v.values()[0]) 
                                 for k, v in df.to_dict().iteritems()))
    except TypeError:
        return df


class Des(object):
    '''
    classe per l'oggetto testo automatico
    '''
    def __init__(self, data):
        logging.basicConfig(level=logging.INFO)
        try:
            engine_name = data.engine.lower()
        except:
            # FIXME: raise a warning
            logging.debug(u"{0}".format(trb.format_exc()))
            engine_name = "xml"
        
        main_string = unicode(data.main, "utf8")
        try:
            portfolio_string = unicode(data.portfolio, "utf8")
        except:
            # FIXME: raise a warning
            logging.debug(u"{0}".format(trb.format_exc()))
            portfolio_string = ""
        
        try:
            self.df = convert_df(data.df.rename(columns=data.lm))
        except:
            # FIXME: raise a warning
            logging.debug(u"{0}".format(trb.format_exc()))
            self.df = None    
        
        engine_class = getattr(de, "{0}_engine".format(engine_name))
        self.engine = engine_class(main_string, portfolio_string, self.df)
        self.tree = self.engine.get_tree()
        do.propagate_local_parameters(self.tree, self.df, [])
        
    def out(self):
        raise NotImplementedError
    

class TexDes(Des):
    def __init__(self, data):
        Des.__init__(self, data)
        
    def out(self):
        res = self.tree.substitute()
        res = ut.escape(res, ut.TEX_ESCAPE)
        res = " ".join(res.split())
        res = res.replace(" .", ".")
        res = res.replace(" ,", ",")
        res = res.replace(" ;", ";")
        res = res.replace(" :", ":")
        res = unicode("{{{0}}}", "utf8").format(res)
        return res
    

class HTMLDes(Des):
    def __init__(self, data):
        Des.__init__(self, data)           
    
    def out(self):
        res = []
        for paragraph in self.paragraphs:
            paragraph_id = paragraph["id"]
            paragraph_text = self.elab_text(paragraph["value"])
            res.append(unicode("<div id='{0}' class='paragraph'>", 
                               "utf8").format(paragraph_id))
            res.append(paragraph_text)
            res.append(unicode("</div>", "utf8"))
        return unicode("", "utf8").join(res)
