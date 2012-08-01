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
import string
import csv
import sys
import os
import getopt

## local libs
## append local lib path
#LIBRARY_PATH = os.path.join(
    #os.path.dirname(os.path.abspath(sys.argv[0])),
    #os.path.pardir, os.path.pardir, 'lib')
#sys.path.append(LIBRARY_PATH)

from config import Config
from Transport import Transport
import Computer
import lm

def main(dirname):
    config = Config()
    config.parse()
    
    companyName=config.options.get('company',False)
    picklesPath = config.options.get('pickles_path',False)
    reportType=int(config.options.get('report_type',False))
    fiscalyearName=config.options.get('fiscalyear',False)
    periodName=config.options.get('period',False)
    sequenceName=config.options.get('sequence',False)
    onlyValidatedMoves=True
    if str(config.options.get('only_validated_moves',True))=='False':
        onlyValidatedMoves=False
    
    immediateVatCreditAccountCode=config.options.get('immediate_credit_vat_account_code',False)
    immediateVatDebitAccountCode=config.options.get('immediate_debit_vat_account_code',False)
    deferredVatCreditAccountCode=config.options.get('deferred_credit_vat_account_code',False)
    deferredVatDebitAccountCode=config.options.get('deferred_debit_vat_account_code',False)
    treasuryVatAccountCode=config.options.get('treasury_vat_account_code',False)
    
    pdfFileName=False
    try:
        #vat registers
        if reportType==1:
            vatRegister = Computer.getVatRegister(picklesPath, companyName, onlyValidatedMoves, fiscalyearName=fiscalyearName, sequenceName=sequenceName)
            print vatRegister
            transportRIva = Transport(DF=vatRegister,TIP='tab',LM=lm.lm_registri_iva)
            pdfFileName = "RegistroIVA"+string.replace(sequenceName," ","")+companyName+string.replace(fiscalyearName," ","")
        #vat summary
        elif reportType==2:
            vatSummary=Computer.getVatSummary(picklesPath, companyName, onlyValidatedMoves, immediateVatCreditAccountCode, immediateVatDebitAccountCode, deferredVatCreditAccountCode, deferredVatDebitAccountCode, periodName=periodName, sequenceName=sequenceName)
            print vatSummary
            pdfFileName="RiepilogoIVA"+string.replace(sequenceName," ","")+companyName+string.replace(periodName," ","")
        #vat detail
        elif reportType==3:
            vatRegister = Computer.getVatRegister(picklesPath, companyName, onlyValidatedMoves, periodName=periodName, sequenceName=sequenceName)
            print vatRegister
            transportRIva = Transport(DF=vatRegister,TIP='tab',LM=lm.lm_registri_iva)
            vatSummary=Computer.getVatSummary(picklesPath, companyName, onlyValidatedMoves, immediateVatCreditAccountCode, immediateVatDebitAccountCode, deferredVatCreditAccountCode, deferredVatDebitAccountCode, periodName=periodName, sequenceName=sequenceName)
            print vatSummary
            pdfFileName="DettaglioIVA"+string.replace(sequenceName," ","")+companyName+string.replace(periodName," ","")
        #deferred vat detail
        elif reportType==4:            
            payments = Computer.getDeferredVatDetail(picklesPath, companyName, onlyValidatedMoves, deferredVatCreditAccountCode, deferredVatDebitAccountCode, searchPayments=True, paymentsPeriodName=periodName)
            notPayed = Computer.getDeferredVatDetail(picklesPath, companyName, onlyValidatedMoves, deferredVatCreditAccountCode, deferredVatDebitAccountCode, searchPayments=False, paymentsPeriodName=periodName)
            print payments
            print notPayed
            transportPayments = Transport(DF=payments,TIP='tab',LM=lm.lm_pagamenti_iva_differita)
            transportNotPayed = Transport(DF=notPayed,TIP='tab',LM=lm.lm_da_pagare_iva_differita)
            pdfFileName="DettaglioIVAEsigibDifferita"+companyName+string.replace(periodName," ","")
        #deferred vat summary
        elif reportType==5:
            deferredVatSummary = Computer.getDeferredVatSummary(picklesPath, companyName, onlyValidatedMoves, deferredVatCreditAccountCode, deferredVatDebitAccountCode, paymentsPeriodName=periodName)
            print deferredVatSummary
            pdfFileName="RiepilogoIVAEsigibDifferita"+companyName+string.replace(periodName," ","")
        #vat liquidation
        elif reportType==6:
            liquidationSummary = Computer.getVatLiquidationSummary(picklesPath, companyName, onlyValidatedMoves, immediateVatCreditAccountCode, immediateVatDebitAccountCode, deferredVatCreditAccountCode, deferredVatDebitAccountCode, treasuryVatAccountCode, periodName=periodName)
            print liquidationSummary
            pdfFileName="ProspettoLiquidazioneIVA"+companyName+string.replace(periodName," ","")
        #exercise control summary
        elif reportType==7:
            vatSummary = Computer.getVatSummary(picklesPath, companyName, onlyValidatedMoves, immediateVatCreditAccountCode, immediateVatDebitAccountCode, deferredVatCreditAccountCode, deferredVatDebitAccountCode, fiscalyearName=fiscalyearName)
            #print vatSummary
            vatControlSummary = Computer.getVatControlSummary(fiscalyearName, vatSummary, picklesPath, companyName, onlyValidatedMoves, immediateVatCreditAccountCode, immediateVatDebitAccountCode, deferredVatCreditAccountCode, deferredVatDebitAccountCode)
                        
            pdfFileName="ProspettoControlloEsercizio"+companyName+string.replace(fiscalyearName," ","")
            
    except:
        raise

    #create tex files
    #basepath = os.path.join(dirname, os.path.pardir, os.path.pardir)
    #texDirPath=os.path.join(basepath, "templates")
    #Tools.writeTex(headerFileWrapper, os.path.join(texDirPath,"header.tex"))
    #Tools.writeTex(documentFileWrapper, os.path.join(texDirPath,"document.tex"))
    
    ##create pdf file

    #templateTexDirPath=os.path.join(texDirPath,"template.tex")
    #pdfdirPath=os.path.join(basepath,"pdf")
    #pdfFilePath=os.path.join(pdfdirPath,string.replace(pdfFileName,"/","")+".pdf")
   
    #if not os.path.exists(pdfdirPath):
        #os.makedirs(pdfdirPath)
    #if pdfFileName:
        #os.system("texi2pdf -o "+pdfFilePath+" -I "+texDirPath+" -c --quiet "+templateTexDirPath)
    return 0


if __name__ == "__main__":
    abspath=os.path.abspath(sys.argv[0])
    dirname=os.path.dirname(abspath)
    sys.exit(main(dirname))
