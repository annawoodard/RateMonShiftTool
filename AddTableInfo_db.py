import sys
from colors import *
from DatabaseParser import *
from termcolor import colored, cprint
write = sys.stdout.write

NHighExpress=0
NHighStreamA=0

def MoreTableInfo(parser,LumiRange,config,isCol=True):
    print "Monitoring Run %d" % (parser.RunNumber,)
    print "len=",len(LumiRange)
    print "LSRange=", LumiRange
    if len(LumiRange)>0:
        
        [AvInstLumi, AvLiveLumi, AvDeliveredLumi, AvDeadTime,PSCols] = parser.GetAvLumiInfo(LumiRange)
        deadtimebeamactive=parser.GetDeadTimeBeamActive(LumiRange)*100
        ##print "dtba=",deadtimebeamactive
    else:
        print "no lumisections to monitor"
        return
    try:
        LastPSCol = PSCols[-1]
    except:
        LastPSCol = -1
    if isCol:
        
        aRates = parser.GetTriggerRatesByLS("AOutput")
        bRates = parser.GetTriggerRatesByLS("BOutput")
        if len(bRates) == 0:
            realARates = aRates
        else:
            realARates={}
            for k,v in bRates.iteritems():
                realARates[k]=aRates[k]-bRates[k]
                #realARates = aRates - bRates*20;
    else:
        if len(parser.GetTriggerRatesByLS("AOutput"))>0:
            aRates = parser.GetTriggerRatesByLS("AOutput")
        else:
            aRates = parser.GetTriggerRatesByLS("AForPPOutput")
            
    
    expressRates = {}
    if isCol:
        expressRates = parser.GetTriggerRatesByLS("ExpressOutput")
    else:
        if len(parser.GetTriggerRatesByLS("ExpressOutput"))>0:
            expressRates=parser.GetTriggerRatesByLS("ExpressOutput")
        else:
            expressRates = parser.GetTriggerRatesByLS("ExpressForCosmicsOutput")
    ExpRate=0
    PeakRate=0
    AvgExpRate=0
    
    ARate=0
    PeakRateA=0
    AvgRateA=0
    
    realARate=0
    realPeakRateA=0
    realAvgRateA=0
    
    if len(expressRates.values()) > 20:
        AvgExpRate = sum(expressRates.values())/len(expressRates.values())

    for ls in LumiRange:  ## Find the sum and peak express stream rates
        thisR = expressRates.get(ls,0)
        ExpRate+=thisR
        if thisR>PeakRate:
            PeakRate=thisR

        thisRateA=aRates.get(ls,0)
        ARate+=thisRateA
        if thisRateA>PeakRateA:
            PeakRateA=thisRateA

        thisRealRateA = aRates.get(ls,0) - bRates.get(ls,0)
        realARate+=thisRealRateA
        if thisRealRateA > realPeakRateA:
            realReakRateA = thisRealRateA
        #ARate+=aRates.get(ls,0)
    ## Print Stream A Rate --moved see below
    ##print "Current Steam A Rate is: %0.1f Hz" % (ARate/len(LumiRange),)

    Warn = False

    ##########################################
    ## Check if the express stream is too high
    ##########################################
    global NHighExpress
    badExpress = ExpRate/len(LumiRange) > config.MaxExpressRate ## avg express stream rate too high?
    baseText = "\nCurrent Express Stream rate is: %0.1f Hz" % (ExpRate/len(LumiRange),) ## text to display
    if badExpress:
        text = colored(baseText,'red',attrs=['reverse'])  ## bad, make the text white on red
        NHighExpress+=1  ## increment the bad express counter
    else:
        text = baseText 
        NHighExpress=0
        
    write(text)
    if badExpress:
        if len(LumiRange)>1:
            if (ExpRate-PeakRate)/(len(LumiRange)-1) <=config.MaxExpressRate: ## one lumisection causes this
                write("  <<  This appears to be due to a 1 lumisection spike, please monitor\n")
            else:
                if NHighExpress > 1:  # big problem, call HLT DOC
                    write(colored("  <<  WARNING: Current Express rate is too high!",'red',attrs=['reverse']) )
                    Warn = True

                #    if AvgExpRate > config.MaxExpressRate:
                #        write( colored("\n\nWARNING: Average Express Stream Rate is too high (%0.1f Hz)  << CALL HLT DOC" % AvgExpRate,'red',attrs=['reverse']) )
                #        Warn = True
        
            


    #########################################
    ##Check if Stream A is too high
    #########################################
    global NHighStreamA
    badStreamA =realARate/len(LumiRange) > config.MaxStreamARate ##Cosmics Express Rate 300 Hz max
    baseTextA= "\nCurrent Steam A Rate is: %0.1f Hz" % (ARate/len(LumiRange),)
    baseTextRealA= "\nCurrent PROMPT Steam A Rate is: %0.1f Hz" % (realARate/len(LumiRange),)
    if badStreamA:
        textA=colored(baseTextA,'red',attrs=['reverse'])  ## bad, make the text white on red
        textRealA=colored(baseTextRealA,'red',attrs=['reverse'])  ## bad, make the text white on red
        NHighStreamA+=1
    else:
        textA=baseTextA
        textRealA=baseTextRealA
        NHighStreamA=0

    write(textA)
    write(textRealA)
    if badStreamA:
        if len(LumiRange)>1:
            if (realARate-realPeakRateA)/(len(LumiRange)-1) <=config.MaxStreamARate: ## one lumisection causes this
                write("  <<  This appears to be due to a 1 lumisection spike, please monitor\n")
            else:
                if NHighStreamA >1: ##Call HLT doc!
                    write(colored("  <<  WARNING: Current Stream A rate is too high!",'red',attrs=['reverse']) )
                    Warn = True
    write("\n\n")
            
    ######################################
    ##Warning for HLT doc
    ######################################
    if Warn:  ## WARNING
        rows, columns = os.popen('stty size', 'r').read().split()  ## Get the terminal size
        cols = int(columns)
        write( colored("*"*cols+"\n",'red',attrs=['reverse','blink']) )
        line = "*" + " "*int((cols-22)/2)+"CALL HLT DOC (165575)"+" "*int((cols-23)/2)+"*\n"

        write( colored(line,'red',attrs=['reverse','blink']) )
        write( colored("*"*cols+"\n",'red',attrs=['reverse','blink']) )
    
    
    PrescaleColumnString=''
    PSCols = list(set(PSCols))
    for c in PSCols:
        PrescaleColumnString = PrescaleColumnString + str(c) + ","

    if isCol:
        write("The average instantaneous lumi of these lumisections is: ")
        write(str(round(AvInstLumi,1))+"e30\n")
        write("The delivered lumi of these lumi sections is:            ")
        write(str(round(len(LumiRange)*AvDeliveredLumi,1))+"e30"+"\n")
        write("The live (recorded) lumi of these lumi sections is:      ")
        write(str(round(len(LumiRange)*AvLiveLumi,1))+"e30\n\n")
        write("The average deadtime of these lumi sections is:          ")
        if deadtimebeamactive > 5:
            write(bcolors.FAIL)
        elif deadtimebeamactive > 10:
            write(bcolors.WARNING)
        else:
            write(bcolors.OKBLUE)
        write(str(round(deadtimebeamactive,2))+"%")
        write(bcolors.ENDC+"\n")
    write("Used prescale column(s): %s  " % (str(PrescaleColumnString),) )
    if LastPSCol in config.ForbiddenCols and isCol:
        write( colored("<< Using column %d! Please check in the documentation that this is the correct column" % (LastPSCol),'red',attrs=['reverse']) )
    write("\nLumisections: ")
    if not isSequential(LumiRange):
        write(str(LumiRange)+"   Lumisections are not sequential (bad LS skipped)\n")
    else:
        write("%d - %d\n" % (min(LumiRange),max(LumiRange),))
    ##print "\nLast Lumisection of the run is:        "+str(parser.GetLastLS())
    write(  "\nLast Lumisection good where DAQ is active is:  "+str(parser.GetLastLS(isCol)) )
    ##write(  "Last Lumisection where DAQ is active is:  "+str(parser.GetLastLS(True)) )
    write("\n\n\n")

    ## if isCol:
##         L1RatePredictions = config.GetExpectedL1Rates(AvInstLumi)
##         if len(L1RatePredictions):
##             print "Expected Level 1 Rates:"
##         for key,val in L1RatePredictions.iteritems():
##             write("Prescale Column "+str(key)+":  "+str(round(val/1000,1))+" kHz")
##             if key == LastPSCol:
##                 write(' << taking data in this column')
##             write('\n')
        
    

def isSequential(t):
    try:
        if len(t)<2:
            return True
    except:
        return True        
    for i,e in enumerate(t[1:]):
        if not abs(e-t[i])==1:
            return False
    return True
