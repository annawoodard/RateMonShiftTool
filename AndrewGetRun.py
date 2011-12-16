#!/usr/bin/env python

import sys
from AndrewWBMParser import AndrewWBMParser

WBMPageTemplate = "http://cmswbm/cmsdb/servlet/RunSummary?RUN=%s&DB=cms_omds_lb"

def GetRun(RunNum, fileName, Save, StartLS=999999, EndLS=111111):
    print "Getting info for run "+str(RunNum)+" from LS "+str(StartLS)+" to "+str(EndLS)
    print "This can take several minutes ..."
    
    RunSumPage = WBMPageTemplate % str(RunNum)
    
    
    Parser = AndrewWBMParser()
    Parser._Parse(RunSumPage)
    [HLTLink,LumiLink,L1Link,PrescaleLink,TriggerLink] = Parser.ParseRunPage()
    
    Parser._Parse(LumiLink)
    [LumiInfo,StartLS,EndLS] = Parser.ParseLumiPage(StartLS,EndLS)
        
    Parser._Parse(TriggerLink)
    TriggerInfo =  Parser.ParseTriggerModePage()

    HLTLink = HLTLink.replace("HLTSummary?","HLTSummary?fromLS="+str(StartLS)+"&toLS="+str(EndLS)+"&")
    Parser._Parse(HLTLink)
    TriggerRates = Parser.ParseHLTSummaryPage(StartLS,EndLS)
    
 
    Parser._Parse(L1Link)
    L1Rates = Parser.ParseL1Page()

    PrescaleValues = Parser.AssemblePrescaleValues()

    TotalPSInfo = Parser.ComputeTotalPrescales(StartLS,EndLS)

    CorrectedPSInfo = Parser.CorrectForPrescaleChange(StartLS,EndLS)

##     L1_LS_Link = L1Link.replace("L1Summary?","L1Summary?fromLS="+str(Parser.FirstLS)+"&toLS="+str(EndLS)+"&")
##     Parser._Parse(L1_LS_Link)
##     Parser.Parse_LS_L1Page()
    
    if Save:
        Parser.Save(fileName)
    print "Done!"

    return Parser
