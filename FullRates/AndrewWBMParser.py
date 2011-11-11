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
        self.TriggerRates = {}
        self.LSByLS = []
        self.InstLumiByLS = {}
        self.DeliveredLumiByLS = {}
        self.LiveLumiByLS = {}
        self.PSColumnByLS = {}
        self.AvInstLumi = 0
        self.AvDeliveredLumi = 0
        self.AvLiveLumi = 0
        self.L1Rates={}
        self.PSColumnChanges=[]
        self.L1TriggerMode={}
        self.HLTTriggerMode={}
        self.HLTSeed={}
        self.RatePage = ''
        self.LumiPage = ''
        self.L1Page=''
        self.PrescaleChangesPage=''
        self.TriggerModePage=''
        self.Date=''
        self.HLT_Key=''

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

    def ParseHLTSummaryPage(self):

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
                self.TriggerRates[TriggerName] = [TriggerRate,L1Pass,PSPass,PS,Seed]

        return self.TriggerRates

	
    def ParseLumiPage(self, run,StartLS=-1, EndLS=-1):
        for line in self.table:
            if len(line)<2 or len(line)>13:
                continue

            self.LSByLS.append(int(line[0])) #LumiSection number is in position 0
            self.PSColumnByLS[int(line[0])] = int(line[2]) #Prescale column is in position 2            
            self.InstLumiByLS[int(line[0])] = round(float(line[4]),2) #Instantaneous luminosity (delivered?) is in position 4
            self.LiveLumiByLS[int(line[0])] = round(float(line[6]),2)  # Live lumi is in position 6
            self.DeliveredLumiByLS[int(line[0])] = round(float(line[5]),2) #Delivered lumi is in position 5

        if StartLS == -1: #If not input for StartLS or EndLS, go from beginning to end of run
            StartLS = 1
        if EndLS == -1:
            EndLS = max(self.LSByLS)
        if StartLS < 2: #The parser does not parse the first LS
            StartLS = 2

        self.AvLiveLumi = 1000*(self.LiveLumiByLS[EndLS] - self.LiveLumiByLS[StartLS])/(23.3*(EndLS-StartLS))
        self.AvDeliveredLumi = 1000*(self.DeliveredLumiByLS[EndLS] - self.DeliveredLumiByLS[StartLS])/(23.3*(EndLS-StartLS))
        value_iterator = 0
        for value in self.LSByLS:
            if value >= StartLS and value <= EndLS:
                self.AvInstLumi+=self.InstLumiByLS[value]
                value_iterator+=1
        self.AvInstLumi = self.AvInstLumi / value_iterator

        return [self.LSByLS, self.PSColumnByLS, self.InstLumiByLS, self.DeliveredLumiByLS, self.LiveLumiByLS, self.AvInstLumi, self.AvDeliveredLumi, self.AvLiveLumi]
    

    def ParseL1Page(self): ##Not used for anything - get this information with ParseTriggerModePage
        for line in self.table:
            if len(line) < 10:
                continue
            if line[1].startswith('L1_'):
                self.L1Rates[line[1]] = float(line[len(line)-4])

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

        return [self.L1TriggerMode,self.HLTTriggerMode,self.HLTSeed]
        
    def Save(self, fileName):
        dir = os.path.dirname(fileName)    
        if not os.path.exists(dir):
            os.makedirs(dir)
        pickle.dump( self, open( fileName, 'w' ) )

    def Load(self, fileName):
        self = pickle.load( open( fileName ) )
