from HTMLParser import HTMLParser
from urllib2 import urlopen
import cPickle as pickle
import os, sys
import time
import re

### need to overwrite some functions in the HTMLParser library
locatestarttagend = re.compile(r"""
        <[a-zA-Z][-.a-zA-Z0-9:_]*          # tag name
        (?:\s+                             # whitespace before attribute name
        (?:[a-zA-Z_][-.:a-zA-Z0-9_]*     # attribute name
        (?:\s*=\s*                     # value indicator
        (?:'[^']*'                   # LITA-enclosed value
        |\"[^\"]*\"                # LIT-enclosed value
        |this.src='[^']*'          # hack
        |[^'\">\s]+                # bare value
        )
        )?
        )
        )*
        \s*                                # trailing whitespace
        """, re.VERBOSE)

tagfind = re.compile('[a-zA-Z][-.a-zA-Z0-9:_]*')
attrfind = re.compile(
    r'\s*([a-zA-Z_][-.:a-zA-Z_0-9]*)(\s*=\s*'
    r'(\'[^\']*\'|"[^"]*"|[-a-zA-Z0-9./,:;+*%?!&$\(\)_#=~@]*))?')

class AndrewWBMParser(HTMLParser):
    
    def __init__(self):
        HTMLParser.__init__(self)
        self.InRow=0
        self.InEntry=0
        self.table =  []
        self.tmpRow = []
        self.hyperlinks = []

        ##-- Defined in ParsePage1 --##
        self.RunNumber = 0

        ##-- Defined in ParseRunPage --##
        self.RatePage = ''
        self.LumiPage = ''
        self.L1Page=''
        self.PrescaleChangesPage=''
        self.TriggerModePage=''
        self.Date=''
        self.HLT_Key=''

        ##-- Defined in ParseHLTSummaryPage --##
        self.TriggerRates = {}

        ##-- Defined in ParseLumiPage --##
        self.LSByLS = []
        self.InstLumiByLS = {}
        self.DeliveredLumiByLS = {}
        self.LiveLumiByLS = {}
        self.PSColumnByLS = {}
        self.AvInstLumi = 0
        self.AvDeliveredLumi = 0
        self.AvLiveLumi = 0
        self.LumiInfo = []  ##Returns

        ##-- Defined in ParseL1Page (not currently used) --##
        self.L1Rates={}  ##Returns

        ##-- Defined in ParsePSColumnPage (not currently used) --##
        self.PSColumnChanges=[]  ##Returns

        ##-- Defined in ParseTriggerModePage --##
        self.L1TriggerMode={}
        self.HLTTriggerMode={}
        self.HLTSeed={}
        self.TriggerInfo = []  ##Returns

        ##-- Defined in AssemblePrescaleValues --##
        self.L1Prescale={}
        self.HLTPrescale={}
        self.MissingPrescale=[]
        self.PrescaleValues=[]  ##Returns

        ##-- Defined in ComputeTotalPrescales --##
        self.TotalPSInfo = []  ##Returns

        ##-- Defined in CorrectForPrescaleChange --##
        self.CorrectedPSInfo = []  ##Returns

        ##-- In the current Parser.py philosophy, only RunNumber is set globally
        ##    - LS range is set from the outside for each individual function
        #self.FirstLS = -1
        #self.LastLS = -1


    def parse_starttag(self, i):   ## Overwrite function from HTMLParser
        self.__starttag_text = None
        endpos = self.check_for_whole_start_tag(i)
        if endpos < 0:
            return endpos
        rawdata = self.rawdata
        self.__starttag_text = rawdata[i:endpos]

        # Now parse the data between i+1 and j into a tag and attrs
        attrs = []
        match = tagfind.match(rawdata, i+1)
        assert match, 'unexpected call to parse_starttag()'
        k = match.end()
        self.lasttag = tag = rawdata[i+1:k].lower()

        if tag == 'img':
            return endpos

        while k < endpos:
            m = attrfind.match(rawdata, k)
            if not m:
                break
            attrname, rest, attrvalue = m.group(1, 2, 3)
            if not rest:
                attrvalue = None
            elif attrvalue[:1] == '\'' == attrvalue[-1:] or \
                 attrvalue[:1] == '"' == attrvalue[-1:]:
                attrvalue = attrvalue[1:-1]
                attrvalue = self.unescape(attrvalue)
            attrs.append((attrname.lower(), attrvalue))
            k = m.end()

        end = rawdata[k:endpos].strip()
        if end not in (">", "/>"):
            lineno, offset = self.getpos()
            if "\n" in self.__starttag_text:
                lineno = lineno + self.__starttag_text.count("\n")
                offset = len(self.__starttag_text) \
                         - self.__starttag_text.rfind("\n")
            else:
                offset = offset + len(self.__starttag_text)
            self.error("junk characters in start tag: %r"
                       % (rawdata[k:endpos][:20],))
        if end.endswith('/>'):
            # XHTML-style empty tag: <span attr="value" />
            self.handle_startendtag(tag, attrs)
        else:
            self.handle_starttag(tag, attrs)
            if tag in self.CDATA_CONTENT_ELEMENTS:
                self.set_cdata_mode()
        return endpos

    def check_for_whole_start_tag(self, i):
        rawdata = self.rawdata
        m = locatestarttagend.match(rawdata, i)
        if m:
            j = m.end()
            next = rawdata[j:j+1]
            #print next
            #if next == "'":
            #    j = rawdata.find(".jpg'",j)
            #    j = rawdata.find(".jpg'",j+1)
            #    next = rawdata[j:j+1]
            if next == ">":
                return j + 1
            if next == "/":
                if rawdata.startswith("/>", j):
                    return j + 2
                if rawdata.startswith("/", j):
                    # buffer boundary
                    return -1
                # else bogus input
            self.updatepos(i, j + 1)
            self.error("malformed empty start tag")
            if next == "":
                # end of input
                return -1
            if next in ("abcdefghijklmnopqrstuvwxyz=/"
                        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
                # end of input in or before attribute value, or we have the
                # '/' from a '/>' ending
                return -1
            self.updatepos(i, j)
            self.error("malformed start tag")
        raise AssertionError("we should not get here!")

    def _Parse(self,url):
        #try:
        #print self
        #print url
        self.table = []
        self.hyperlinks = []
        req = urlopen(url)
        self.feed(req.read())
        
        #except:
        #print "Error Getting page: "+url
        #print "Please retry.  If problem persists, contact developer"

    def handle_starttag(self,tag,attrs):
        if tag == 'a' and attrs:
            self.hyperlinks.append(attrs[0][1])
                
        if tag == 'tr':
            self.InRow=1
        if tag == 'td':
            self.InEntry=1

    def handle_endtag(self,tag):
        if tag =='tr':
            if self.InRow==1:
                self.InRow=0
                self.table.append(self.tmpRow)
                self.tmpRow=[]
        if tag == 'td':
            self.InEntry=0

    def handle_startendtag(self,tag, attrs):
        pass

    def handle_data(self,data):
        if self.InEntry:
            self.tmpRow.append(data)

    def ParsePage1(self):   ## Parse the Run list page to figure out what the most recent run was
        # Find the first non-empty row on page one
        MostRecent = self.table[0]
        for line in self.table:
            if line == []:
                continue # skip empty rows, not exactly sure why they show up
            MostRecent = line
            break # find first non-empty line
        TriggerMode = MostRecent[3]
        self.RunNumber = MostRecent[0]    ## Set the run number

        isCollisions = not (TriggerMode.find('l1_hlt_collisions') == -1)  ## Is the most recent run a collisions run?
        if not isCollisions:
            return ''
        for link in self.hyperlinks:
            if not link.find('RUN='+self.RunNumber)==-1:
                self.RunPage = link   ## Get the link to the run summary page and return
                return link
        
    def ParseRunPage(self):
        for entry in self.hyperlinks:

            entry = entry.replace('../../','http://cmswbm/')
            if not entry.find('HLTSummary') == -1:
                self.RatePage = entry
            if not entry.find('L1Summary') == -1:
                self.L1Page = entry
            if not entry.find('LumiSections') == -1:
                self.LumiPage = "http://cmswbm/cmsdb/servlet/"+entry
            if not entry.find('PrescaleChanges') == -1:
                self.PrescaleChangesPage = "http://cmswbm/cmsdb/servlet/"+entry
            if not entry.find('TriggerMode') == -1:
                self.TriggerModePage = entry
            #print self.table
            self.HLT_Key = self.table[8][0]
            #print self.HLT_Key
            self.Date = self.table[1][4]
            #print self.Date
            
        return [self.RatePage,self.LumiPage,self.L1Page,self.PrescaleChangesPage,self.TriggerModePage]


    def ParseHLTSummaryPage(self,StartLS,EndLS):

        for line in self.table:
            if not len(line)>6:  # All relevant lines in the table will be at least this long
                continue
            if line[1].startswith('HLT_'):
                TriggerName = line[1][:line[1].find('_v')+2] # Format is HLT_... (####), this gets rid of the (####)
                TriggerRate = float(line[6].replace(',','')) # Need to remove the ","s, since float() can't parse them
                L1Pass = int(line[3])
                PSPass = int(line[4])
                Seed = line[9]
                if int(line[4])>0: #line[3] is L1Pass, line[4] is PSPass
                    PS = float(line[3])/float(line[4])
                else:
                    if int(line[3])>0:
                        PS = line[3]
                    else:
                        PS = 1
                self.TriggerRates[TriggerName] = [TriggerRate,L1Pass,PSPass,PS,Seed,StartLS,EndLS]

        return self.TriggerRates

	
    def ParseLumiPage(self,StartLS,EndLS):

        for line in self.table:
            if len(line)<2 or len(line)>13:
                continue
            if float(line[8]) < 10 or float(line[9]) < 1: ##Beam 1 or Beam 2 absent
                continue

            self.LSByLS.append(int(line[0])) #LumiSection number is in position 0
            self.PSColumnByLS[int(line[0])] = int(line[2]) #Prescale column is in position 2            
            self.InstLumiByLS[int(line[0])] = round(float(line[4]),2) #Instantaneous luminosity (delivered?) is in position 4
            self.LiveLumiByLS[int(line[0])] = round(float(line[6]),2)  # Live lumi is in position 6
            self.DeliveredLumiByLS[int(line[0])] = round(float(line[5]),2) #Delivered lumi is in position 5

        if StartLS < 0:
            EndLS = max(self.LSByLS) - 3
            StartLS = EndLS + StartLS
        if StartLS < 2: #The parser does not parse the first LS
            StartLS = 2
        if StartLS == 999999:
            StartLS = min(self.LSByLS)
        if EndLS == 111111:
            EndLS = max(self.LSByLS)
        if EndLS <= StartLS:
            print "In ParseLumiPage, EndLS <= StartLS"

        print "In ParseLumiPage, StartLS = "+str(StartLS)+" and EndLS = "+str(EndLS)

        self.AvLiveLumi = 1000*(self.LiveLumiByLS[EndLS] - self.LiveLumiByLS[StartLS])/(23.3*(EndLS-StartLS))
        self.AvDeliveredLumi = 1000*(self.DeliveredLumiByLS[EndLS] - self.DeliveredLumiByLS[StartLS])/(23.3*(EndLS-StartLS))
        value_iterator = 0
        for value in self.LSByLS:
            if value >= StartLS and value <= EndLS:
                self.AvInstLumi+=self.InstLumiByLS[value]
                value_iterator+=1
        self.AvInstLumi = self.AvInstLumi / value_iterator

        self.LumiInfo = [self.LSByLS, self.PSColumnByLS, self.InstLumiByLS, self.DeliveredLumiByLS, self.LiveLumiByLS, self.AvInstLumi, self.AvDeliveredLumi, self.AvLiveLumi]

        return [self.LumiInfo,StartLS,EndLS]
    

    def ParseL1Page(self): ##Not used for anything - get this information with ParseTriggerModePage
        for line in self.table:
            if len(line) < 10:
                continue
            if line[1].startswith('L1_'):
                try:
                    self.L1Rates[line[1]] = float(line[len(line)-4])
                except:
                    correctedNumber = line[len(line)-4].replace(",","")
                    self.L1Rates[line[1]] = float(correctedNumber)
                    
        return self.L1Rates

    def ParsePSColumnPage(self):
        for line in self.table:
            if len(line) < 5 or line[0].startswith('Run'):
                continue
            self.PSColumnChanges.append([int(line[1]),int(line[2])]) #line[1] is the first LS of a new PS column, line[2] is the column index
        return self.PSColumnChanges

    def ParseTriggerModePage(self):
        for line in self.table:
            if len(line) < 6 or line[0].startswith('n'):
                continue
            if len(line) > 11:
                print line
            if line[1].startswith('L1_'):
                self.L1TriggerMode[line[1]] = []
                for n in range(2, len(line)): #"range" does not include the last element (i.e. there is no n = len(line))
                    self.L1TriggerMode[line[1]].append(int(line[n]))
                    
            if line[1].startswith('HLT_'):
                HLTStringName = line[1]
                for s in HLTStringName.split("_v"): #Eliminates version number from the string name
                    if s.isdigit():
                        numbertoreplace = s
                HLTStringName = HLTStringName.replace('_v'+str(numbertoreplace),'_v')
                
                self.HLTTriggerMode[HLTStringName] = []

                for n in range(3, len(line)-1): #The parser counts the number in parentheses after the trigger name as its own column
                    self.HLTTriggerMode[HLTStringName].append(int(line[n]))
                        
                if line[len(line)-1].startswith('L1_'):
                    self.HLTSeed[HLTStringName] = line[len(line)-1]
                else:
                    if not " OR" in line[len(line)-1]:
                        self.HLTTriggerMode[HLTStringName].append(int(line[n]))
                        self.HLTSeed[HLTStringName] = "NULL"
                    else:
                        self.HLTSeed[HLTStringName] = str(line[len(line)-1])

        self.TriggerInfo = [self.L1TriggerMode,self.HLTTriggerMode,self.HLTSeed]
        return self.TriggerInfo

    def AssemblePrescaleValues(self): ##Depends on output from ParseLumiPage and ParseTriggerModePage
        MissingName = "Nemo"
        for key in self.L1TriggerMode:
            self.L1Prescale[key] = {}
            for n in range(min(self.LSByLS),max(self.LSByLS)+1): #"range()" excludes the last element
                try:
                    self.L1Prescale[key][n] = self.L1TriggerMode[key][self.PSColumnByLS[n]]
                except:
                    if not key == MissingName:
                        self.MissingPrescale.append(key)
                        MissingName = key
                    if not n < 2:
                        print "LS "+str(n)+" of key "+str(key)+" is missing from the LumiSections page"

        for key in self.HLTTriggerMode:
            self.HLTPrescale[key] = {}
            for n in range(min(self.LSByLS),max(self.LSByLS)+1): #"range" excludes the last element
                try:
                    self.HLTPrescale[key][n] = self.HLTTriggerMode[key][self.PSColumnByLS[n]]
                except:
                    if not key == MissingName:
                        self.MissingPrescale.append(key)
                        MissingName = key
                    if not n < 2:
                        print "LS "+str(n)+" of key "+str(key)+" is missing from the LumiSections page"

        self.PrescaleValues = [self.L1Prescale,self.HLTPrescale,self.MissingPrescale]
        return self.PrescaleValues

    def ComputeTotalPrescales(self,StartLS,EndLS):
        IdealHLTPrescale = {}
        IdealPrescale = {}
        L1_zero = {}
        HLT_zero = {}
        n1 = {}
        n2 = {}
        L1 = {}
        L2 = {}
        H1 = {}
        H2 = {}
        InitialColumnIndex = self.PSColumnByLS[int(StartLS)]

        for key in self.HLTTriggerMode:
            try:
                DoesThisPathHaveAValidL1SeedWithPrescale = self.L1Prescale[self.HLTSeed[key]][StartLS]
            except:
                L1_zero[key] = True
                HLT_zero[key] = False
                continue

            IdealHLTPrescale[key] = 0.0
            IdealPrescale[key] = 0.0
            n1[key] = 0
            L1_zero[key] = False
            HLT_zero[key] = False

            for LSIterator in range(StartLS,EndLS+1): #"range" excludes the last element
                if self.L1Prescale[self.HLTSeed[key]][LSIterator] > 0 and self.HLTPrescale[key][LSIterator] > 0:
                    IdealPrescale[key]+=1.0/(self.L1Prescale[self.HLTSeed[key]][LSIterator]*self.HLTPrescale[key][LSIterator])
                else:
                    IdealPrescale[key]+=1.0 ##To prevent a divide by 0 error later
                    if self.L1Prescale[self.HLTSeed[key]][LSIterator] < 0.1:
                        L1_zero[key] = True
                    if self.HLTPrescale[key][LSIterator] < 0.1:
                        HLT_zero[key] = True
                if self.PSColumnByLS[LSIterator] == InitialColumnIndex:
                    n1[key]+=1

            if L1_zero[key] == True or HLT_zero[key] == True:
                continue

            IdealPrescale[key] = (EndLS + 1 - StartLS)/IdealPrescale[key]

            n2[key] = float(EndLS + 1 - StartLS - n1[key])
            L1[key] = float(self.L1Prescale[self.HLTSeed[key]][StartLS])
            L2[key] = float(self.L1Prescale[self.HLTSeed[key]][EndLS])
            H1[key] = float(self.HLTPrescale[key][StartLS])
            H2[key] = float(self.HLTPrescale[key][EndLS])

            IdealHLTPrescale[key] = ((n1[key]/L1[key])+(n2[key]/L2[key]))/((n1[key]/(L1[key]*H1[key]))+(n2[key]/(L2[key]*H2[key])))

        self.TotalPSInfo = [L1_zero,HLT_zero,IdealPrescale,IdealHLTPrescale,n1,n2,L1,L2,H1,H2]

        return self.TotalPSInfo

        
    def CorrectForPrescaleChange(self,StartLS,EndLS):
        [L1_zero,HLT_zero,IdealPrescale,IdealHLTPrescale,n1,n2,L1,L2,H1,H2] = self.TotalPSInfo
        xLS = {}
        RealPrescale = {}

        for key in self.HLTTriggerMode:
            if L1_zero[key] == True or HLT_zero[key] == True:
                continue
            [TriggerRate,L1Pass,PSPass,PS,Seed,StartLS,EndLS] = self.TriggerRates[key]
            if PS > 0.95 * IdealHLTPrescale[key] and PS < 1.05 * IdealHLTPrescale[key]:
                RealPrescale[key] = IdealPrescale[key]
                continue
                
            if H1[key] == H2[key] and L1[key] == L2[key] and not EndLS > max(self.LSByLS) - 1: ##Look for prescale change into the next LS
                H2[key] = float(self.HLTPrescale[key][EndLS+1])
                L2[key] = float(self.L1Prescale[self.HLTSeed[key]][EndLS+1])
            if H1[key] == H2[key] and L1[key] == L2[key] and not StartLS < 3:
                H1[key] = float(self.HLTPrescale[key][StartLS-1])
                L1[key] = float(self.L1Prescale[self.HLTSeed[key]][StartLS-1])
            if H1[key] == H2[key]:
                xLS[key] = 0
            else:
                xLS[key] = ((-(PS/IdealHLTPrescale[key])*(L2[key]*n1[key]+L1[key]*n2[key])*(H2[key]*L2[key]*n1[key]+H1[key]*L1[key]*n2[key]))+((H2[key]*L2[key]*n1[key]+H1[key]*L1[key]*n2[key])*(L2[key]*n1[key]+L1[key]*n2[key])))/(((PS/IdealHLTPrescale[key])*(L2[key]*n1[key]+L1[key]*n2[key])*(H1[key]*L1[key]-H2[key]*L2[key]))+((H2[key]*L2[key]*n1[key]+H1[key]*L1[key]*n2[key])*(L2[key]-L1[key])))

            if xLS[key] > 1:
                xLS[key] = 1
            if xLS[key] < -1:
                xLS[key] = -1
            RealPrescale[key] = (n1[key] + n2[key])/(((n1[key] - xLS[key])/(H1[key]*L1[key]))+(n2[key]+xLS[key])/(H2[key]*L2[key]))

        self.CorrectedPSInfo = [RealPrescale,xLS,L1,L2,H1,H2]

        return self.CorrectedPSInfo
        
    def Save(self, fileName):
        dir = os.path.dirname(fileName)    
        if not os.path.exists(dir):
            os.makedirs(dir)
        pickle.dump( self, open( fileName, 'w' ) )

    def Load(self, fileName):
        self = pickle.load( open( fileName ) )
