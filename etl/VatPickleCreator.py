#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#    
#    Copyright (C) 2012 Servabit Srl (<infoaziendali@servabit.it>).
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

__VERSION__ = '0.1'

import os
import sys
import pandas
try:
    import cPickle
except ImportError:
    import Pickle as cPickle

# Servabit libraries
PathPr1="/home/contabilita/star_branch/etl/"
PathPr2="/home/contabilita/star_branch/share/"
sys.path.append(PathPr1) 
sys.path.append(PathPr2)   
sys.path=list(set(sys.path)) 
from stark import StarK
import config
from config import Config
import DBmap2
import create_dict
import stark


def CreateVatDW(companyName):
    config = Config()
    config.parse()
    
    if not companyName:
        companyName=config.options.get('company',False)
    picklesPath = config.options.get('pickles_path',False)
    immediateVatCreditAccountCode=config.options.get('immediate_credit_vat_account_code',False)
    immediateVatDebitAccountCode=config.options.get('immediate_debit_vat_account_code',False)
    deferredVatCreditAccountCode=config.options.get('deferred_credit_vat_account_code',False)
    deferredVatDebitAccountCode=config.options.get('deferred_debit_vat_account_code',False)
    treasuryVatAccountCode=config.options.get('treasury_vat_account_code',False)
    
    '''Questa funzione serve a generare per una Company i diversi file pickle che compongono il
       Datawarehouse per la reportistica iva
    ''' 
    ############################################################################################
    #  importazione dei dati della classe Account Move Line
    #  contenente le informazioni sulle linee di scrittura contabile
    ############################################################################################
    MVLD = {
             'M_NAME' : ('move', ('name', None)),
             'M_REF' : ('move', ('ref', None)), 
             'STA_MOV'  : ('move', ('state', None)),
             'DATE_DOC' : ('move', ('invoice', ('date_document', None))),
             'COD_CON' : ('account', ('code', None)),
             'NAM_IMP'  : ('company', ('name', None)),
             'DATE'  : ('move', ('date', None)),
             'PERIOD'  : ('period', ('name', None)),
             'ESER'  : ('period', ('fiscalyear', ('name', None))),
             'PARTNER'  : ('partner', ('name', None)),
             'JOURNAL'  : ('journal', ('name', None)),
             'TYP_JRN' : ('journal', ('type', None)), 
             'DBT_MVL'  : ('debit', None),
             'CRT_MVL'  : ('credit', None),
             'RECON'  : ('reconcile_id', None),
             'RECON_P'  : ('reconcile_partial_id', None),
             'TAX_COD'  : ('tax_code_id', None), 
             'NAM_SEQ'  : ('journal', ('sequence', ('name', None))), 
             'COD_SEQ'  : ('journal', ('sequence', ('code', None))), 
             }
    moveLinesDict = create_dict.create_dict(DBmap2.AccountMoveLine, MVLD, companyName)
    moveLineDf = pandas.DataFrame(moveLinesDict)
    #moveLineDf['TAX_COD'].ix[moveLineDf['TAX_COD'].isnull()] = "NULL"
    vatDatasDf = moveLineDf.ix[(moveLineDf["COD_SEQ"]=='RIVA') & (moveLineDf["TAX_COD"].notnull())].reset_index()
    #aggiunta colonna TNAME
    companyPathPkl = os.path.join(picklesPath,companyName)
    taxDf = StarK.Loadk(companyPathPkl,"TAX.pickle").DF
    df2 = vatDatasDf[vatDatasDf['TYP_JRN'].isin(['sale', 'purchase'])]
    df3 = pandas.merge(df2,taxDf,left_on='TAX_COD',right_on='TAX_CODE')
    df4 = pandas.merge(df2,taxDf,left_on='TAX_COD',right_on='BASE_CODE')
    df5 = vatDatasDf[vatDatasDf['TYP_JRN'].isin(['sale_refund', 'purchase_refund'])]
    df6 = pandas.merge(df5,taxDf,left_on='TAX_COD',right_on='REF_TAX_CODE')
    df7 = pandas.merge(df5,taxDf,left_on='TAX_COD',right_on='REF_BASE_CODE')
    vatDatasDf = pandas.concat([df3,df4,df6,df7]).reset_index(drop=True)
    del vatDatasDf["TAX_CODE"]
    del vatDatasDf["BASE_CODE"]
    del vatDatasDf["REF_TAX_CODE"]
    del vatDatasDf["REF_BASE_CODE"]
    vatDatasDf = vatDatasDf.rename(columns={'NAM_TAX' : 'TNAME',
                                            'NAM_SEQ' : 'SEQUENCE',
                                            'COD_CON' : 'TACC'
                                            })

    #aggiunta a vatDatasDf delle move.line relative ai pagamenti dell'iva differita
    df0 = vatDatasDf.ix[(vatDatasDf["TACC"]==deferredVatCreditAccountCode) | (vatDatasDf["TACC"]==deferredVatDebitAccountCode)].reset_index()
    reconcileDf = df0[["RECON","RECON_P"]].drop_duplicates().reset_index(drop=True)
    reconcileDf['RECON'].ix[reconcileDf['RECON'].isnull()] = "NULL"
    reconcileDf['RECON_P'].ix[reconcileDf['RECON_P'].isnull()] = "NULL"
    df0 = moveLineDf.ix[moveLineDf["COD_SEQ"]!='RIVA'].reset_index()
    df1 = pandas.merge(df0,reconcileDf,on="RECON").reset_index(drop=True)
    df2 = pandas.merge(df0,reconcileDf,on="RECON_P").reset_index(drop=True)
    df3 = pandas.concat([df1,df2]).reset_index(drop=True)
    del df3["RECON_P.x"]
    del df3["RECON_P.y"]
    del df3["RECON.x"]
    del df3["RECON.y"]
    vatDatasDf = pandas.concat([vatDatasDf,df3]).reset_index(drop=True)
    #aggiunta a vatDatasDf delle move.line relative ai pagamenti dell'iva sul conto treasuryVatAccountCode
    df0 = moveLineDf.ix[moveLineDf["TACC"]==treasuryVatAccountCode].reset_index()
    vatDatasDf = pandas.concat([vatDatasDf,df0]).reset_index(drop=True)
    del vatDatasDf["index"]
    #costruzione delle altre colonne del df finale
    vatDatasDf['M_NUM'] = ''
    for i in range(len(vatDatasDf)):
        row = vatDatasDf[i:i+1]
        moveName = row['M_NAME'][i]
        moveNameSplits = moveName.split("/")
        vatDatasDf['M_NUM'][i:i+1] = moveNameSplits[len(moveNameSplits)-1]
    
    vatDatasDf['CASH'] = False
    for i in range(len(vatDatasDf)):
        row = vatDatasDf[i:i+1]
        debit = row['DBT_MVL'][i]
        credit = row['CRT_MVL'][i]
        accountCode = row['TACC'][i]
        vatDatasDf['CASH'][i:i+1] = (debit>0 and accountCode==deferredVatDebitAccountCode) or (credit>0 and accountCode==deferredVatCreditAccountCode)
                                            
    vatDatasDf['TTAX'] = False
    vatDatasDf['TTAX'].ix[vatDatasDf['TACC'].isin([immediateVatCreditAccountCode,immediateVatDebitAccountCode,deferredVatCreditAccountCode,deferredVatDebitAccountCode])] = True
    
    vatDatasDf['TCRED'] = False
    vatDatasDf['TCRED'].ix[vatDatasDf['TACC'].isin([immediateVatCreditAccountCode,deferredVatCreditAccountCode])] = True
    
    #TODO
    vatDatasDf['TDET'] = True
    vatDatasDf['TDET'].ix[vatDatasDf['TACC'].isin([immediateVatCreditAccountCode,deferredVatCreditAccountCode])] = False
    
    
    print len(vatDatasDf)
    print len(vatDatasDf.ix[vatDatasDf['TTAX']==True])
    print len(vatDatasDf.ix[vatDatasDf['TTAX']==False])

if __name__ == "__main__":
    CreateVatDW("Aderit")
    #CreateVatDW("Vicem")
    #CreateVatDW("Studiabo")