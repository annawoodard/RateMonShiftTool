#!/usr/bin/env python

import pickle
import getopt
import sys
import os

def usage():
    print sys.argv[0]+" [options]"
    print "This script makes a pkl file from TMD rate predictions\nto be used in the RatePredictor script for new menu deployment"
    print "--TriggerList=<path>"
    print "--NColBunch=<# colliding bunches>"

def main():
    print "making TMD pkl fit files"
    
############# fIT FILE NAME ###########
    
    fit_file="fits_TMD_ncolbunch%s.pkl"

#######################################

    ncolbunch=28
    ntotbunch=1331
    bunfrac=float(ncolbunch)/float(ntotbunch)

#######################################
    try:
        opt, args = getopt.getopt(sys.argv[1:],"",["NColBunch=","TriggerList="])
            
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)

    trig_list=[]
    fit_list={}
    for o,a in opt:
        if o == "--NColBunch":
            ncolbunch=int(a)
            ntotbunch=1331
            bunfrac=float(ncolbunch)/float(ntotbunch)
        elif o == "--TriggerList":
            try:
                f = open(a)
                for line in f:
                    if line.startswith('#'):
                        continue

                    if len(line)<3 or line=='\n':
                        continue
                    line = ((line.rstrip('\n')).rstrip(' '))
                    if line.find(':')==-1: 
                        list.append( line )
                    
                    else:
                        split = line.split(':')
                        ##trig_list.append([split[0],split[1],split[2],split[3]])
                        trig_list.append(split[0])
                        fit_list[split[0]]=[float(split[1])*bunfrac,float(split[2])*bunfrac,float(split[3])*bunfrac]
                        

                    
                    ## if entry.find(':')!=-1:
##                         entry = entry[:entry.find(':')]   ## We can point this to the existing monitor list, just remove everything after ':'!
##                         if entry.find('#')!=-1:
##                             entry = entry[:entry.find('#')]   ## We can point this to the existing monitor list, just remove everything after ':'!                    
##                     trig_list.append( entry.rstrip('\n'))
            except:
                print "\nInvalid Trigger List\n"
                sys.exit(0)
        else:
            print "\nInvalid Option %s\n" % (str(o),)
            usage()
            sys.exit(2)

    

    OutputFit={}
    for keys in fit_list.iterkeys():
        
        ##change format to that produced in rate predictor
        fit_list_fortrig=fit_list[keys]
        fit_list_fortrig.insert(0,"poly")#fit name
        fit_list_fortrig.append(0.0)#cubic term
        fit_list_fortrig.append(10.0)#chisq/ndf
        fit_list_fortrig.append(0.0)#meanrawrate
        fit_list_fortrig.append(0.0)#0.err
        fit_list_fortrig.append(0.0)#1.err
        fit_list_fortrig.append(0.0)#2.err
        fit_list_fortrig.append(0.0)#3.err
        
        OutputFit[keys]=fit_list_fortrig
        ##print "trig=",keys, "fit pars=",fit_list_fortrig

    fit_file = fit_file % (ncolbunch)
    
    if os.path.exists(fit_file):
            os.remove(fit_file)
    FitOutputFile = open(fit_file, 'wb')
    pickle.dump(OutputFit, FitOutputFile, 2)
    FitOutputFile.close()
    print "Output fit file is "+str(fit_file)

    

if __name__=='__main__':
    main()
