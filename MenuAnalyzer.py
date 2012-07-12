#!/usr/bin/env python

import os
import sys
from DatabaseParser import ConnectDB
import re
import cx_Oracle

try:  ## set is builtin in python 2.6.4 and sets is deprecated
    set
except NameError:
    from sets import Set

class MenuAnalyzer:
    def __init__(self,name):
        ##default ranges
        self.maxModuleNameLength = 300
        self.maxModulesPerPath   = 50
        self.maxPaths = 500
        self.maxEndPaths = 30

        ##required streams
        self.requiredStreamsAndPDs = { 'Calibration' : ['TestEnablesEcalHcalDT'],'EcalCalibration' : ['EcalLaser'],
                                  'TrackerCalibration' : ['TestEnablesTracker']}
        self.ExpressStreamName = 'Express'
        self.expressPDs      = { 'ExpressPhysics' : 'Collisions',
                                 'ExpressCosmics' : 'Cosmics' }

        self.expressType = ''

        self.menuName = name
        self.endPathList = set()
        self.perPathModuleList={}
        self.perModuleTypeList={}
        self.perStreamPDList={}
        self.perPDPathList={}
        self.Results={}
        self.ModuleList=[]
        self.AnalysisList=[]
        

        ## statically define the analysis map: new analyses must be registered here
        self.AnalysisMap = {
            'moduleLength' : self.checkModuleLength,
            'numberOfPaths' : self.checkNumPaths,
            'numberOfEndPaths' : self.checkNumEndPaths,
            'reqStreamsAndPDs' : self.reqStreamsAndPDs,
            'checkExpress' : self.checkExpress,
            'checkNameFormats' :self.checkNameFormats
            }

        self.T0REGEXP = { ## These are the regexps that T0 uses to access things
            # Regexp for save file name paths. We don't process anything else.
            'RXSAFEPATH' : re.compile("^[-A-Za-z0-9_]+$"),
            # Regexp for valid dataset names.
            'RXDATASET' : re.compile("^[-A-Za-z0-9_]+$"),
            # Regexp for valid RelVal dataset names.
            'RXRELVALMC' : re.compile("^/RelVal[^/]+/(CMSSW(?:_[0-9]+)+(?:_pre[0-9]+)?)[-_].*$"),
            'RXRELVALDATA' : re.compile("^/[^/]+/(CMSSW(?:_[0-9]+)+(?:_pre[0-9]+)?)[-_].*$"),
            # Regexp for online DQM files.
            'RXONLINE' : re.compile("^(?:.*/)?DQM_V(\d+)(_[A-Za-z0-9]+)?_R(\d+)\.root$"),
            # Regexp for offline DQM files.
            'RXOFFLINE' : re.compile("^(?:.*/)?DQM_V(\d+)_R(\d+)((?:__[-A-Za-z0-9_]+){3})\.root$"),
            # Regexp for acquisition era part of the processed dataset name.
            'RXERA' : re.compile("^([A-Za-z]+\d+|CMSSW(?:_[0-9]+)+(?:_pre[0-9]+)?)")
            }

    def AddAnalysis(self,name): 
        self.AnalysisList.append(name)

    def AddAllAnalyses(self):
        for name in self.AnalysisMap.iterkeys():
            self.AddAnalysis(name)

    def Analyze(self):
        cursor = ConnectDB('hlt')
        self.GetModules(cursor)
        self.GetStreamsPathsPDs(cursor)
        for analysis in self.AnalysisList: 
            if not self.AnalysisMap.has_key(analysis):
                print "ERROR: Analysis %s not defined" % (analysis,)
                continue
            self.AnalysisMap[analysis]()
            
        

    def checkModuleLength(self):
        self.Results['moduleLength'] = []
        for modName,type in self.perModuleTypeList.iteritems():
            if len(modName) > self.maxModuleNameLength: self.Results['moduleLength'].append(modName)
        
    def checkNumPaths(self):
        if len(self.perPathModuleList) > self.maxPaths:
            self.Results['numberOfPaths'] = len(self.perPathModuleList) 
        else:
            self.Results['numberOfPaths'] = 0
    def checkNumEndPaths(self):
        if len(self.endPathList) > self.maxEndPaths:
            self.Results['numberOfEndPaths'] = len(self.endPathList)
        else:
            self.Results['numberOfEndPaths'] = 0
    def reqStreamsAndPDs(self):
        self.Results['reqStreamsAndPDs'] = []
        for stream,PDList in self.requiredStreamsAndPDs.iteritems():
            if not self.perStreamPDList.has_key(stream): self.Results['reqStreamsAndPDs'].append(stream)
            for PD in PDList:
                if not PD in self.requiredStreamsAndPDs[stream]: self.Results['reqStreamsAndPDs'].append(stream+'::'+PD)
    
    def checkExpress(self):
        self.Results['checkExpress'] = []
        if not self.perStreamPDList.has_key(self.ExpressStreamName):
            self.Results['checkExpress'].append(self.ExpressStreamName)
            return

        if len(self.perStreamPDList[self.ExpressStreamName]) >1:
            self.Results['checkExpress'].append("MULTIPLE_PDS")
        if len(self.perStreamPDList[self.ExpressStreamName]) <1:
            self.Results['checkExpress'].append("NO_PDS")

        for PD in self.perStreamPDList[self.ExpressStreamName]:
            if not self.expressPDs.has_key(PD):
                self.Results['checkExpress'].append(self.ExpressStreamName+"::"+PD)
            else:
                self.expressType = self.expressPDs[PD]
                
        

    def checkNameFormats(self):
        self.Results['checkNameFormats']=[]
        for PD in self.perPDPathList.iterkeys():
            if not self.T0REGEXP['RXDATASET'].match(PD):
                self.Results['checkNameFormats'].append(PD)
        for path in self.perPathModuleList.iterkeys():
            if not self.T0REGEXP['RXSAFEPATH'].match(path):
                self.Results['checkNameFormats'].append(path)
        
    def GetModules(self,cursor):
        sqlquery ="""  
        SELECT I.NAME,E.NAME,D.NAME,I.ISENDPATH
        FROM
        CMS_HLT.PARAMETERS B,
        CMS_HLT.SUPERIDPARAMETERASSOC C,
        CMS_HLT.MODULETEMPLATES D,
        CMS_HLT.MODULES E,
        CMS_HLT.PATHMODULEASSOC F,
        CMS_HLT.CONFIGURATIONPATHASSOC G,
        CMS_HLT.CONFIGURATIONS H,
        CMS_HLT.PATHS I
        WHERE
        B.PARAMID = C.PARAMID AND
        C.SUPERID = F.MODULEID AND
        E.TEMPLATEID = D.SUPERID AND
        F.MODULEID = E.SUPERID AND
        F.PATHID=G.PATHID AND
        I.PATHID=G.PATHID AND
        G.CONFIGID=H.CONFIGID AND
        H.CONFIGDESCRIPTOR='%s' 
        """ % (self.menuName,)
        
        cursor.execute(sqlquery)
        for PathName,ModuleName,ModuleType,endPath in cursor.fetchall():
            if not self.perPathModuleList.has_key(PathName): self.perPathModuleList[PathName] = []
            self.perPathModuleList[PathName].append(ModuleName)
            self.perModuleTypeList[ModuleName] = ModuleType
            if endPath: self.endPathList.add(PathName)


    def GetStreamsPathsPDs(self,cursor):
        sqlquery= """
        SELECT A.STREAMLABEL,E.NAME,F.DATASETLABEL
        FROM
        CMS_HLT.STREAMS A,
        CMS_HLT.CONFIGURATIONS B,
        CMS_HLT.CONFIGURATIONPATHASSOC C,
        CMS_HLT.PATHSTREAMDATASETASSOC D,
        CMS_HLT.PATHS E,
        CMS_HLT.PRIMARYDATASETS F
        WHERE
        B.CONFIGDESCRIPTOR='%s' AND
        C.CONFIGID=B.CONFIGID AND
        D.PATHID=C.PATHID AND
        A.STREAMID=D.STREAMID AND
        E.PATHID = C.PATHID AND
        F.DATASETID = D.DATASETID
        """ % (self.menuName,)
        
        cursor.execute(sqlquery)
        for StreamName,PathName,PDName in cursor.fetchall():
            if not self.perStreamPDList.has_key(StreamName): self.perStreamPDList[StreamName] = []
            if not PDName in self.perStreamPDList[StreamName]: self.perStreamPDList[StreamName].append(PDName)
            if not self.perPDPathList.has_key(PDName): self.perPDPathList[PDName] = []
            self.perPDPathList[PDName].append(PathName)

