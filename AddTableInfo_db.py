import sys
from colors import *
from DatabaseParser import *
write = sys.stdout.write

def MoreTableInfo(parser,LumiRange,config):
    [AvInstLumi, AvLiveLumi, AvDeliveredLumi, AvDeadTime,PSCols] = parser.GetAvLumiInfo(LumiRange)
    LastPSCol = PSCols[-1]

    if AvDeadTime==0:  ## For some reason the dead time in the DB is occasionally broken
        try:
            AvDeadTime = AvLiveLumi/AvDeliveredLumi * 100
        except:
            AvDeadTime = 100
    PrescaleColumnString=''
    PSCols = list(set(PSCols))
    for c in PSCols:
        PrescaleColumnString = PrescaleColumnString + str(c) + ","

    write("The average instantaneous lumi of these lumisections is: ")
    write(str(round(AvInstLumi,1))+"e30\n")
    write("The delivered lumi of these lumi sections is:            ")
    write(str(round(len(LumiRange)*AvDeliveredLumi,1))+"e30"+"\n")
    write("The live (recorded) lumi of these lumi sections is:      ")
    write(str(round(len(LumiRange)*AvLiveLumi,1))+"e30\n\n")
    write("The average deadtime of these lumi sections is:          ")
    if AvDeadTime > 5:
        write(bcolors.FAIL)
    elif AvDeadTime > 10:
        write(bcolors.WARNING)
    else:
        write(bcolors.OKBLUE)
    write(str(round(AvDeadTime,1))+"%")
    write(bcolors.ENDC+"\n")

    print "Used prescale column(s): "+str(PrescaleColumnString)    
    write("Lumisections: ")
    if not isSequential(LumiRange):
        write(str(LumiRange)+"   Lumisections are not sequential (bad LS skipped)\n")
    else:
        write("%d - %d\n" % (min(LumiRange),max(LumiRange),))
    print "\nLast Lumisection of the run is:        "+str(parser.GetLastLS())
    write(  "Last Lumisection good for physics is:  "+str(parser.GetLastLS(True)) )
    if parser.GetLastLS(True)!=max(LumiRange):
        write(bcolors.WARNING)
        write("  << This exceeds the last lumisection parsed")
    write(bcolors.ENDC+"\n\n\n")

    L1RatePredictions = config.GetExpectedL1Rates(AvInstLumi)
    if len(L1RatePredictions):
        print "Expected Level 1 Rates:"
    for key,val in L1RatePredictions.iteritems():
        write("Prescale Column "+str(key)+":  "+str(round(val/1000,1))+" kHz")
        if key == LastPSCol:
            write(' << We Are here!')
        write('\n')
        
    

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