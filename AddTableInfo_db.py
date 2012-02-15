import sys
from colors import *
from DatabaseParser import *
write = sys.stdout.write

def MoreTableInfo(parser,LumiRange):
    [AvInstLumi, AvLiveLumi, AvDeliveredLumi, AvDeadTime,PSCols] = parser.GetAvLumiInfo(LumiRange)

    if AvDeadTime==0:  ## For some reason the dead time in the DB is occasionally broken
        try:
            AvDeadTime = AvLiveLumi/AvDeliveredLumi * 100
        except:
            AvDeadTime = 100
    PrescaleColumnString=''
    for c in PSCols:
        PrescaleColumnString = PrescaleColumnString + str(c) + ","

    write("The average instantaneous lumi of these lumisections is: ")
    write(str(round(AvInstLumi,1))+"e30\n")
    write("The delivered lumi of these lumi sections is:            ")
    write(str(round(1000*AvDeliveredLumi,1))+"e30"+"\n")
    write("The live (recorded) lumi of these lumi sections is:      ")
    write(str(round(1000*AvLiveLumi,1))+"e30\n\n")
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
    print "Lumisections: "+str(LumiRange)
