#!/usr/bin/env python
import sys
from AndrewWBMParser import AndrewWBMParser

import sys
import os
#import selectionParser
import itertools
import getopt
from operator import itemgetter
import time
from selectionParser import selectionParser

#WBMPageTemplate = "http://cmswbm/cmsdb/servlet/RunSummary?RUN=%s&DB=cms_omds_lb"
WBMPageTemplate = "http://cmswbm/cmsdb/servlet/RunSummary?RUN=%s"

def main():

    NumberOfParsingTries = 3
    LumiSegmentLength = 10
    first_run = 178421
    DebugPrint = False

    run_file = str(sys.argv[1])
    RunNumber = []
    StartingLS = {}
    EndingLS = {}
    #PrescaleColumnIndex = {}
    L1Prescale = {}
    HLTPrescale = {}
    MissingLS = {}

    selected_runs = []
    input_file = open(run_file)
    file_content = input_file.read()
    if "Cert" in str(run_file):
        inputRange = selectionParser(file_content)
        selected_runs.extend(inputRange.runs())
        selected_runs.sort()
        for run in selected_runs:
            if run < first_run:
                continue
            RunNumber.append(run)
            StartingLS[run] = []
            EndingLS[run] = []
            lslist = inputRange.runsandls()[run]
            last_lumisection = max(lslist)
            for iteratedLS in lslist:
                if not iteratedLS == last_lumisection+1:
                    StartingLS[run].append(iteratedLS)
                last_lumisection = iteratedLS

            last_lumisection = min(lslist)-1
            for iteratedLS in lslist:
                if not iteratedLS == last_lumisection+1:
                    EndingLS[run].append(last_lumisection)
                last_lumisection = iteratedLS
            EndingLS[run].append(max(lslist))

            if DebugPrint:
                for print_iterator in range(0,len(StartingLS[run])):
                    print str(run)+", "+str(StartingLS[run][print_iterator])+", "+str(EndingLS[run][print_iterator])
                
        input_file.close()

    else:
        last_run = 0
        for line in file_content.splitlines():
            if line.strip():
                [run, min_ls, max_ls] = [int(item) for item in line.split(',')]
                if run < first_run:
                    continue
                if not run == last_run:
                    RunNumber.append(run)
                    StartingLS[run] = []
                    EndingLS[run] = []
                StartingLS[run].append(min_ls)
                EndingLS[run].append(max_ls)

    last_runnumber = 0
    run_iterator = 0
    while run_iterator < len(RunNumber):
        RunNum = RunNumber[run_iterator]
        lumi_range = len(StartingLS[RunNum])
        if not RunNum == last_runnumber:
            lumi_iterator = 0
        StartingLSIndex = StartingLS[RunNum][lumi_iterator]
        
        TryParsing = 0
        RunSumPage = WBMPageTemplate % RunNum
        Parser = AndrewWBMParser()
        while TryParsing < NumberOfParsingTries and lumi_iterator == 0: ##Begin parsing information about the whole run
            #try: 
            if TryParsing < NumberOfParsingTries: #Comment out "try" if you want parsing error output for debugging
                if DebugPrint:
                    print str(RunNum)+" from "+str(StartingLS[RunNum][0])+" to "+str(EndingLS[RunNum][lumi_range-1])
                    print "TryParsing = "+str(TryParsing)+", lumi_iterator = "+str(lumi_iterator)

                Parser._Parse(RunSumPage)
                [HLTLink,LumiLink,L1Link,PrescaleLink,TriggerLink] = Parser.ParseRunPage()

                Parser._Parse(LumiLink)
                [LumiSection,PSColumnByLS,InstLumiByLS,DeliveredLumiByLS,LiveLumiByLS,AvInstLumi,AvDeliveredLumi,AvLiveLumi] = Parser.ParseLumiPage(RunNum)

                ##The following code would get the prescale column information from the PrescaleChanges page
                #Parser._Parse(PrescaleLink)
                #PrescaleColumn = Parser.ParsePSColumnPage()
                #PrescaleColumnIndex[RunNum] = {}
                #for rowintable in range(0, len(PrescaleColumn)): #"range" excludes the last element
                    #if PrescaleColumn[rowintable][0] < EndingLS[RunNum][lumi_range-1]:
                        #for n in range (PrescaleColumn[rowintable][0], EndingLS[RunNum][lumi_range-1]+1): #"range" excludes the last element
                            #PrescaleColumnIndex[RunNum][n] = PrescaleColumn[rowintable][1]

                Parser._Parse(TriggerLink)
                [L1TriggerMode, HLTTriggerMode, HLTSeed] = Parser.ParseTriggerModePage()
                L1Prescale[RunNum] = {}
                HLTPrescale[RunNum] = {}
                MissingLS[RunNum] = []
                for key in L1TriggerMode:
                    L1Prescale[RunNum][key] = {}
                    for n in range(StartingLS[RunNum][0]-1, EndingLS[RunNum][lumi_range-1]+1): #"range()" excludes the last element
                        try:
                            L1Prescale[RunNum][key][n] = L1TriggerMode[key][PSColumnByLS[n]]
                        except:
                           MissingLS[RunNum].append(int(n))
                           if DebugPrint and not n < 2:
                               print "LS "+str(n)+" of key "+str(key)+" is missing from the LumiSections page"
                for key in HLTTriggerMode:
                    HLTPrescale[RunNum][key] = {}
                    for n in range(StartingLS[RunNum][0]-1, EndingLS[RunNum][lumi_range-1]+1): #"range" excludes the last element
                        try:
                            HLTPrescale[RunNum][key][n] = HLTTriggerMode[key][PSColumnByLS[n]]
                        except:
                            if DebugPrint and not n < 2:
                                print "LS "+str(n)+" of key "+str(key)+" is missing from the LumiSections page"

                TryParsing = NumberOfParsingTries + 1
                

            #except:
                #time.sleep(10)
                #print "Sleeping"
                #TryParsing+=1
                #if TryParsing == 10:
                    #print "Could not parse run "+str(RunNum)
        ##End parsing information about the whole run

        ##Begin parsing information about particular LS ranges
        while StartingLSIndex < EndingLS[RunNum][lumi_iterator] + 1 - LumiSegmentLength:
            StartLS = StartingLSIndex
            EndLS = StartLS + LumiSegmentLength - 1
            StartingLSIndex+=LumiSegmentLength
            TryParsing = 0

            #if DebugPrint:
            print "Trying to parse run "+str(RunNum)+" from LS "+str(StartLS)+" to "+str(EndLS)+"\n"
            while TryParsing < NumberOfParsingTries:
                try:
                    HLTLink = HLTLink.replace("HLTSummary?","HLTSummary?fromLS="+str(StartLS)+"&toLS="+str(EndLS)+"&")
                    Parser._Parse(HLTLink)
                    TriggerRates = Parser.ParseHLTSummaryPage()
                    HLTLink = HLTLink.replace("HLTSummary?fromLS="+str(StartLS)+"&toLS="+str(EndLS)+"&","HLTSummary?")

                    AvDeliveredLumi = 1000*(DeliveredLumiByLS[EndLS] - DeliveredLumiByLS[StartLS])/( 23.3*(EndLS-StartLS))
                    AvLiveLumi = 1000*(LiveLumiByLS[EndLS] - LiveLumiByLS[StartLS])/( 23.3*(EndLS-StartLS))
    
                    for key in TriggerRates:
                        HLT_zero = False ##Don't look at LS ranges where the L1 or HLT prescale is 0
                        L1_zero = False
                        #if not "Mu" in key:
                        #if not "HLT_Photon225_NoHE_v" in key:
                            #continue
                        if DebugPrint:
                            print key
                        AvHLTPrescale = 0.0
                        for LSIterator in range(StartLS,EndLS+1): #"range" excludes the last element
                            if HLTPrescale[RunNum][key][LSIterator] > 0:
                                AvHLTPrescale+=1.0/HLTPrescale[RunNum][key][LSIterator]
                            else:
                                AvHLTPrescale+=1 ##To prevent a divide by 0 error later
                                HLT_zero = True

                        #if HLT_zero == True:
                            #if DebugPrint:
                                #print str(key)+ " has an HLT prescale of 0 between LS "+str(StartLS)+" and "+str(EndLS)

                        AvHLTPrescale = (EndLS + 1 - StartLS)/AvHLTPrescale
                        RealHLTPrescale = TriggerRates[key][1]
                        RawRate = TriggerRates[key][0]

                        try:
                            n1 = 0.0
                            InitialColumnIndex = PSColumnByLS[StartLS]
                            
                            AvL1Prescale = 0.0
                            for LSIterator in range(StartLS,EndLS+1): #"range" excludes the last element
                                if L1Prescale[RunNum][HLTSeed[key]][LSIterator] > 0:
                                    AvL1Prescale+=1.0/L1Prescale[RunNum][HLTSeed[key]][LSIterator]
                                else:
                                    L1_zero = True
                                if PSColumnByLS[LSIterator] == InitialColumnIndex:
                                    n1+=1

                            #if L1_zero == True:
                                #if DebugPrint:
                                    #print str(key)+ " has an L1 prescale of 0 between LS "+str(StartLS)+" and "+str(EndLS)
                            if L1_zero == True or HLT_zero == True:
                                continue

                            AvL1Prescale = (EndLS + 1 - StartLS)/AvL1Prescale
                            
                            n2 = float(EndLS + 1 - StartLS - n1)
                            L1 = float(L1Prescale[RunNum][HLTSeed[key]][StartLS])
                            L2 = float(L1Prescale[RunNum][HLTSeed[key]][EndLS])
                            H1 = float(HLTPrescale[RunNum][key][StartLS])
                            H2 = float(HLTPrescale[RunNum][key][EndLS])

                            IdealHLTPrescale = ((n1/L1)+(n2/L2))/((n1/(L1*H1))+(n2/(L2*H2)))
                            IHP = IdealHLTPrescale
                            RHP = RealHLTPrescale
                            #if DebugPrint:
                                #print str(n1)+"  "+str(n2)+"  "+str(L1)+"  "+str(L2)+"  "+str(H1)+"  "+str(H2)+"  "+str(IHP)+"  "+str(RHP)
                            if IHP < 1 or RHP < 1:
                                if DebugPrint:
                                    print "IHP = "+str(IHP)+" and RHP = "+str(RHP)+" - why is it less than 1?"

                            if (IHP/RHP > 1.02 or IHP/RHP < 0.98) and RHP > 0.99 and RawRate > 0.2:
                                if H1 == H2 and L1 == L2 and not EndLS == EndingLS[RunNum][lumi_range-1]:
                                    H2 = float(HLTPrescale[RunNum][key][EndLS+1])
                                    L2 = float(L1Prescale[RunNum][HLTSeed[key]][EndLS+1])
                                if H1 == H2 and L1 == L2 and not StartLS == 3:
                                    H1 = float(HLTPrescale[RunNum][key][StartLS-1])
                                    L1 = float(L1Prescale[RunNum][HLTSeed[key]][StartLS-1])
                                if DebugPrint:
                                    print "Change of prescale from "+str(L1)+" to "+str(L2)+" or "+str(H1)+" to "+str(H2)+" in LS range "+str(StartLS)+" to "+str(EndLS)
                                    print "n1 = "+str(n1)+", n2 = "+str(n2)+", L1 = "+str(L1)+", L2 = "+str(L2)+", H1 = "+str(H1)+", H2 = "+str(H2)+", IHP = "+str(IHP)+", NHP = "+str(RHP)
                                if H1 == H2:
                                    xLS = 0
                                else:
                                    xLS = ((-(RHP/IHP)*(L2*n1+L1*n2)*(H2*L2*n1+H1*L1*n2))+((H2*L2*n1+H1*L1*n2)*(L2*n1+L1*n2)))/(((RHP/IHP)*(L2*n1+L1*n2)*(H1*L1-H2*L2))+((H2*L2*n1+H1*L1*n2)*(L2-L1)))
                            else:
                                xLS = 0
                            if xLS > 1:
                                xLS = 1
                            if xLS < -1:
                                xLS = -1
                            #if not xLS == 0:
                                #print "xLS = "+str(xLS)

                            FullPrescale = (n1 + n2)/(((n1 - xLS)/(H1*L1))+(n2+xLS)/(H2*L2))

                            IdealPrescale = 0.0
                            for LSIterator in range(StartLS,EndLS+1): #"range" excludes the last element
                                IdealPrescale+=1.0/(L1Prescale[RunNum][HLTSeed[key]][LSIterator]*HLTPrescale[RunNum][key][LSIterator])
                            IdealPrescale = (EndLS + 1 - StartLS)/IdealPrescale

                        except:
                            #print str(key)+" does not have a unitary L1 seed"
                            #if not " OR" in str(HLTSeed[key]):
                                #print str(key)+" is allegedly seeded by "+str(HLTSeed[key])
                            #print L1Prescale[RunNum][HLTSeed[key]]
                            FullPrescale = RealHLTPrescale
                            IdealPrescale = AvHLTPrescale

                        if L1_zero == True or HLT_zero == True:
                            continue
                        if RawRate > 0.2 and AvLiveLumi > 500:
                            #OldRate = RawRate * RealHLTPrescale * AvL1Prescale
                            IdealRate = RawRate * IdealPrescale
                            Rate = RawRate * FullPrescale
                            print str(key)+", "+str(AvDeliveredLumi)+", "+str(AvLiveLumi)+", "+str(FullPrescale)+", "+str(RawRate)+", "+str(IdealRate)+", "+str(Rate)
                            #print str(AvL1Prescale)+", "+str(AvHLTPrescale)+", "+str(RealHLTPrescale)+", "+str(IdealPrescale)+", "+str(FullPrescale)+", "+str(RawRate)+", "+str(OldRate)+", "+str(IdealRate)+", "+str(Rate)
                    
                    TryParsing = NumberOfParsingTries + 1
                except:
                    time.sleep(20)
                    TryParsing+=1
                    if TryParsing == NumberOfParsingTries:
                        print "Could not parse LS "+str(StartLS)+" to "+str(EndLS)+" of run "+str(RunNum)

        last_runnumber = RunNum
        lumi_iterator +=1
        if lumi_iterator == lumi_range:
            run_iterator += 1
           
        

if __name__=='__main__':
    main()
