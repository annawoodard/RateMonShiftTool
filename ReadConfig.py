#!/usr/bin/env python
import os
import cPickle as pickle
import math

class RateMonConfig:
    
    def __init__(self,path='./'):
        self.CFGfile=path+"/defaults.cfg"
        self.BasePath=path
        self.ReferenceRun=""
        self.DefAllowRateDiff=0.0
        self.DefAllowIgnoreThresh=0.0
        self.ExcludeList=[]
        self.MonitorList=[]
        self.MonitorIntercept=[]
        self.MonitorSlope=[]
        self.MonitorQuad=[]
        self.L1Predictions=[]
        self.MonitorOnly=0
        self.MonTargetLumi=0
        self.FindL1Zeros=0
        self.LSWindow=-1
        self.CompareReference=0
        self.ShifterMode=0
        self.MaxExpressRate=999

    def ReadList(self,filename):
        filename=self.BasePath+'/'+filename
        list = []
        if not os.path.exists(filename):
            return list
        f = open(filename)
        for line in f:
            if line.startswith('#'):
                continue
            if len(line)<3 or line=='\n':
                continue
            line = ((line.rstrip('\n')).rstrip(' '))
            if line.find(':')==-1: # exclude list, no rate estimates
                list.append( line )
            else:
                split = line.split(':')
                list.append([split[0],split[1],split[2],split[3]])
        f.close()
        return list

    def ReadCFG(self):
        f=open(self.CFGfile)
        for line in f:
            if line.startswith('#'):
                continue
            if len(line)<1:
                continue
            
            strippedLine = line.split('#')[0]
            strippedLine = strippedLine.rstrip('\n').rstrip(' ')
            if strippedLine=='':
                continue
            tok = strippedLine.split('=')
            par = tok[0].rstrip(' ').lstrip(' ')
            if len(tok)>=2:
                arg=tok[1].rstrip('\n').rstrip(' ').lstrip(' ')
            else:
                arg=''
                
            if par=="ReferenceRun":
                self.ReferenceRun=arg
            elif par=="DefaultAllowedRateDiff":
                self.DefAllowRateDiff=float(arg)
            elif par=="DefaultIgnoreThreshold":
                self.DefAllowIgnoreThresh=float(arg)
            elif par=="ExcludeTriggerList":
                self.ExcludeList=self.ReadList(arg)
            elif par=="TriggerToMonitorList":
                tmp=self.ReadList(arg)
                for line in tmp:
                    self.MonitorList.append(line[0])
                    self.MonitorIntercept.append(float(line[1]))
                    self.MonitorSlope.append(float(line[2]))
                    self.MonitorQuad.append(float(line[3]))
            elif par=="L1CrossSection":
                self.L1Predictions = self.ReadList(arg)
            elif par == "MonitorOnlyListed":
                self.MonitorOnly=int(arg)
            elif par=="MonitorTargetLumi":
                self.MonTargetLumi=float(arg)
            elif par=="FindL1Zeros":
                self.FindL1Zeros=int(arg)
            elif par=="LSSlidingWindow":
                self.LSWindow=int(arg)
            elif par=="CompareReference":
                self.CompareReference=int(arg)
            elif par=="ShifterMode":
                self.ShifterMode=arg
            elif par=="MaxExpressRate":
                self.MaxExpressRate=float(arg)
            elif par=="MaxStreamARate":
                self.MaxStreamARate=float(arg)
            else:
                print "Invalid Option : "+strippedLine
        f.close()
                
    def AnalyzeTrigger(self,TrigName): ## Have to pass this a version number stripped Trigger
        if TrigName in self.ExcludeList:
            return False
        if self.MonitorOnly and not TrigName in self.MonitorList:
            return False
        return True

##     def GetExpectedRate(self,TrigName,lumi):
##         for trig,intercept,slope,quad in zip(self.MonitorList,self.MonitorIntercept,self.MonitorSlope,self.MonitorQuad):
##             if trig==TrigName:
##                 #print "mon list",self.MonitorList
##                 if lumi:
##                     return intercept + lumi*slope/1000 + lumi*lumi*quad/1000000
##                 else:
##                     return intercept + 3000*slope/1000 + 3000*3000*quad/1000000
##         return -1

    def GetExpectedRate(self,TrigName,Input,Rates,live,delivered):
        RefRun = False

        try:
            Chi2 = Input[TrigName][5]
            if Input[TrigName][0] == "poly":
                return [(live/delivered)*(Input[TrigName][1]+Input[TrigName][2]*delivered+Input[TrigName][3]*delivered*delivered+Input[TrigName][4]*delivered*delivered*delivered), Chi2]
            else:
                return [(live/delivered)*(Input[TrigName][1]+Input[TrigName][2]*math.exp(Input[TrigName][3]*delivered)), Chi2]
        except:
            RefRun = True

        if RefRun:

            num_compare = 0
            pred_rate = 0
            for iterator in range(len(Rates[TrigName]["rate"])):
                delivered_lumi = Rates[TrigName]["delivered_lumi"][iterator]
                if delivered_lumi > delivered - 100 and delivered_lumi < delivered + 100:
                    live_lumi = Rates[TrigName]["live_lumi"][iterator]
                    rate = Rates[TrigName]["rate"][iterator]
                    pred_rate += (live/delivered)*rate*(delivered_lumi/live_lumi)
                    num_compare += 1

            pred_rate = pred_rate/num_compare
            Chi2 = pred_rate/math.sqrt(num_compare)
            return [pred_rate, Chi2]

        return -1
                    
        
    def GetExpectedL1Rates(self,lumi):
        if not lumi:
            return {}
        expectedRates = {}
        for col,inter,slope,quad in self.L1Predictions:
            try:
                expectedRates[int(col)] = lumi*(float(inter)+float(slope)*lumi+float(quad)*lumi*lumi)
            except:
                return {}
        return expectedRates
       
    
