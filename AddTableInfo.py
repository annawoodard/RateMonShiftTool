import sys
from colors import *
write = sys.stdout.write

def MoreTableInfo(PSColumnByLS,LiveLumiByLS,DeliveredLumiByLS,StartLS,LastLS):
    StartLS=10
    LastLS=20
    PrescaleColumnString=''
        
    if min(list(PSColumnByLS.values())[StartLS:LastLS]) == max(list(PSColumnByLS.values())[StartLS:LastLS]):
        PrescaleColumnString = str(PSColumnByLS[StartLS])

    else:
        PrescaleColumnString = str(max(PSColumnByLS[StartLS]))+" and "+str(min(PSColumnByLS[LastLS]))


    AvLiveLumi = 1000 * ( max(list(LiveLumiByLS.values()[StartLS:LastLS])) - LiveLumiByLS.values()[StartLS]) / ( ( len(list(LiveLumiByLS.values()[StartLS:LastLS])) - 1 ) * 23.3 )
        
    AvDeliveredLumi = 1000 * ( max(list(DeliveredLumiByLS.values()[StartLS:LastLS])) - DeliveredLumiByLS.values()[StartLS] ) / ( ( len(list(DeliveredLumiByLS.values()[StartLS:LastLS])) - 1 ) * 23.3 )

    AvDeadtime = 100 * (AvDeliveredLumi - AvLiveLumi) / (AvDeliveredLumi + 0.1)
            
    ##nameBufLen=60
##             RateBuffLen=10
##             write('*'*(nameBufLen+3*RateBuffLen+10))
##             write ('\nCalculation using FirstLS = %s to LastLS = %s of run %s \n' % (HeadParser.FirstLS, HeadParser.LastLS, CompareRunNum))

    write("The average delivered lumi of these lumi sections is:       ")
    write(str(round(AvDeliveredLumi,1))+"e30"+"\n")
    write("The average live (recorded) lumi of these lumi sections is: ")
    if AvLiveLumi==0:
        write(bcolors.FAIL)
    elif AvLiveLumi<100:
        write(bcolors.WARNING)
        
    write(str(round(AvLiveLumi,1))+"e30")
    write(bcolors.ENDC+"\n")
    write("The average deadtime of these lumi sections is:              ")
    if AvDeadtime > 5:
        write(bcolors.FAIL)
    elif AvDeadtime > 10:
        write(bcolors.WARNING)
    else:
        write(bcolors.OKBLUE)
        write(str(round(AvDeadtime,1))+"%")
    write(bcolors.ENDC+"\n")

    print "Using prescale column "+str(PrescaleColumnString)
