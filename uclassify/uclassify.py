#!/usr/bin/python
# Copyright (C) 2012 Sibi <sibi@psibi.in>
#
# This file is part of pyuClassify.
#
# pyuClassify program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyuClassify program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyuClassify program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyuClassify.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:  Sibi <sibi@psibi.in>
#           Marcus Svensson <marcus@twingly.com>

from xml.dom.minidom import Document
from time import gmtime, strftime
from uclassify_eh import uClassifyError
import xml.dom.minidom
import base64
import requests
import socket


class HttpConnector(object):
    BASE_API        = 'http://api.uclassify.com'
    SCHEMA          = 'http://api.uclassify.com/1/RequestSchema'
    API_KEYS_NEEDED = True
    def __init__(self, read_api_key, write_api_key, api_url=BASE_API):
        self.read_api_key = read_api_key
        self.write_api_key = write_api_key
        self.api_url = api_url
    def send(self, xml):
        content = xml.toxml('utf-8')
        print content
        r = requests.post(self.api_url, content)
        if r.status_code == 200:
            success, status_code, text = self._getResponseCode(r.content)
            if success == "false":
                raise uClassifyError(text, status_code)
        else:
            raise uClassifyError("Bad XML Request Sent")
        return text
    def _getResponseCode(self,content):
        """Returns the status code from the content.
           :param content: (required) XML Response content
        """
        doc = xml.dom.minidom.parseString(content)
        node = doc.documentElement
        status = node.getElementsByTagName("status")
        success = status[0].getAttribute("success")
        status_code = status[0].getAttribute("statusCode")
        text = self._getText(status[0].childNodes)
        return success, status_code, text
    def _getText(self, nodelist):
        return ''.join(node.data for node in nodelist if node.nodeType == node.TEXT_NODE)
        rc = []
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)
        return ''.join(rc)


class SocketConnector(object):
    SCHEMA          = 'http://api.uclassify.com/1/server/RequestSchema'
    API_KEYS_NEEDED = False
    def __init__(self, host, port=54441, bufsize=65536):
        self.adr = (host, port)
        self.bufsize = bufsize
    def send(self, xml):
        api_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        api_socket.connect(self.adr)
        content = xml.toxml('utf-8')
        api_socket.sendall(content)
        api_socket.shutdown(socket.SHUT_WR)
        response = []
        while True:
            b = api_socket.recv(self.bufsize)
            response.append(b)
            if len(b) == 0:
                api_socket.close()
                return ''.join(response)


class uclassify(object):

    def __init__(self, connector=None):
        if connector is None:
            self.connector = SocketConnector('dev01')
        else:
            self.connector = connector

    def setWriteApiKey(self, key):
        self.writeApiKey = key

    def setReadApiKey(self, key):
        self.readApiKey = key

    def _buildbasicXMLdoc(self):
        doc = Document()
        root_element = doc.createElementNS(self.connector.SCHEMA, 'uclassify')
        root_element.setAttribute("version", "1.01")
        root_element.setAttribute("xmlns", self.connector.SCHEMA)
        doc.appendChild(root_element)

        return doc,root_element

    def _buildReadDoc(self, classifier_name):
        doc, root_element = self._buildbasicXMLdoc()
        readcalls = doc.createElement("readCalls")
        if self.connector.API_KEYS_NEEDED:
            if self.connector.read_api_key == None:
                raise uClassifyError("Read API Key not Initialized")
            readcalls.setAttribute("readApiKey", self.readApiKey)
        readcalls.setAttribute("classifierName", classifier_name)
        root_element.appendChild(readcalls)
        return doc, root_element, readcalls

    def _buildWriteDoc(self, classifier_name):
        doc, root_element = self._buildbasicXMLdoc()
        writecalls = doc.createElement("writeCalls")
        if self.connector.API_KEYS_NEEDED:
            if self.connector.write_api_key == None:
                raise uClassifyError("Write API Key not Initialized")
            writecalls.setAttribute("writeApiKey", self.connector.write_api_key)
        writecalls.setAttribute("classifierName", classifier_name)
        root_element.appendChild(writecalls)
        return doc, root_element, writecalls

    def create(self,classifierName):
        """Creates a new classifier.
           :param classifierName: (required) The Classifier Name you are going to create.
        """
        doc,root_element,writecalls = self._buildWriteDoc(classifierName)
        create = doc.createElement("create")
        cur_time = strftime("%Y%m%d%H%M", gmtime())
        create.setAttribute("id",cur_time + "create" + classifierName)
        writecalls.appendChild(create)
        return self.connector.send(doc)

    def addClass(self,className,classifierName):
        """Adds class to an existing Classifier.
           :param className: (required) A List containing various classes that has to be added for the given Classifier.
           :param classifierName: (required) Classifier where the classes will be added to.
        """
        doc, root_element, writecalls = self._buildWriteDoc(classifierName)
        for clas in className:
            addclass = doc.createElement("addClass")
            addclass.setAttribute("id","AddClass" + clas)
            addclass.setAttribute("className",clas)
            writecalls.appendChild(addclass)
        print doc
        return self.connector.send(doc)
    
    def removeClass(self,className,classifierName):
        """Removes class from an existing Classifier.
           :param className: (required) A List containing various classes that will be removed from the given Classifier.
           :param classifierName: (required) Classifier
        """
        doc, root_element, writecalls = self._buildWriteDoc(classifierName)
        for clas in className:
            addclass = doc.createElement("removeClass")
            addclass.setAttribute("id","removeClass" + clas)
            addclass.setAttribute("className",clas)
            writecalls.appendChild(addclass)
        return self.connector.send(doc)
    
    def train(self,texts,className,classifierName):
        """Performs training on a single classs.
           :param texts: (required) A List of text used up for training.
           :param className: (required) Name of the class that needs to be trained.
           :param classifierName: (required) Name of the Classifier
        """
        base64texts = []
        for text in texts:
            base64_text = base64.b64encode(text) #For Python version 3, need to change.
            base64texts.append(base64_text)
        doc, root_element, writecalls = self._buildWriteDoc(classifierName)
        textstag = doc.createElement("texts")
        root_element.appendChild(textstag)
        counter = 1
        for text in base64texts:
            textbase64 = doc.createElement("textBase64")
            traintag = doc.createElement("train")
            textbase64.setAttribute("id",className + "Text" + str(counter))
            ptext = doc.createTextNode(text)
            textbase64.appendChild(ptext)
            textstag.appendChild(textbase64)
            traintag.setAttribute("id","Train"+className+ str(counter))
            traintag.setAttribute("className",className)
            traintag.setAttribute("textId",className + "Text" + str(counter))
            counter = counter + 1
            writecalls.appendChild(traintag)
        return self.connector.send(doc)

    def untrain(self,texts,className,classifierName):
        """Performs untraining on text for a specific class.
           :param texts: (required) A List of text used up for training.
           :param className: (required) Name of the class.
           :param classifierName: (required) Name of the Classifier
        """
        base64texts = []
        for text in texts:
            base64_text = base64.b64encode(text) #For Python version 3, need to change.
            base64texts.append(base64_text)
        doc, root_element, writecalls = self._buildWriteDoc(classifierName)
        textstag = doc.createElement("texts")
        root_element.appendChild(textstag)
        counter = 1
        for text in base64texts:
            textbase64 = doc.createElement("textBase64")
            traintag = doc.createElement("untrain")
            textbase64.setAttribute("id",className + "Text" + str(counter))
            ptext = doc.createTextNode(text)
            textbase64.appendChild(ptext)
            textstag.appendChild(textbase64)
            traintag.setAttribute("id","Untrain"+className+ str(counter))
            traintag.setAttribute("className",className)
            traintag.setAttribute("textId",className + "Text" + str(counter))
            counter = counter + 1
            writecalls.appendChild(traintag)
        return self.connector.send(doc)

    def classify(self,texts,classifierName,username = None):
        """Performs classification on texts.
           :param texts: (required) A List of texts that needs to be classified.
           :param classifierName: (required) Classifier Name
           :param username: (optional): Name of the user, under whom the classifier exists.
        """
        doc, root_element, readcalls = self._buildReadDoc(classifierName)
        textstag = doc.createElement("texts")
        root_element.appendChild(textstag)
        base64texts = []
        for text in texts:
            base64_text = base64.b64encode(text) #For Python version 3, need to change.
            base64texts.append(base64_text)
        counter = 1
        for text in base64texts:
            textbase64 = doc.createElement("textBase64")
            classifytag = doc.createElement("classify")
            textbase64.setAttribute("id","Classifytext"+ str(counter))
            ptext = doc.createTextNode(text)
            textbase64.appendChild(ptext)
            classifytag.setAttribute("id","Classify"+ str(counter))
            classifytag.setAttribute("classifierName",classifierName)
            classifytag.setAttribute("textId","Classifytext"+str(counter))
            if username != None:
                classifytag.setAttribute("username",username)
            textstag.appendChild(textbase64)
            readcalls.appendChild(classifytag)
            counter = counter + 1
        return self.connector.send(doc)

    def parseClassifyResponse(self,content,texts):
        """Parses the Classifier response from the server.
           :param content: (required) XML Response from server.
        """
        counter = 0
        doc = xml.dom.minidom.parseString(content)
        node = doc.documentElement
        result = []
        classifytags = node.getElementsByTagName("classification")
        for classi in classifytags:
            text_coverage = classi.getAttribute("textCoverage")
            classtags = classi.getElementsByTagName("class")
            cresult = []
            for ctag in classtags:
                classname = ctag.getAttribute("className")
                cper = ctag.getAttribute("p")
                tup = (classname,cper)
                cresult.append(tup)
            result.append((texts[counter],text_coverage,cresult))
            counter = counter + 1
        return result
            
    def classifyKeywords(self,texts,classifierName,username = None):
        """Performs classification on texts.
           :param texts: (required) A List of texts that needs to be classified.
           :param classifierName: (required) Classifier Name
           :param username: (optional): Name of the user, under whom the classifier exists.
        """
        doc, root_element, readcalls = self._buildReadDoc(classifierName)
        textstag = doc.createElement("texts")
        root_element.appendChild(textstag)
        base64texts = []
        for text in texts:
            base64_text = base64.b64encode(text) #For Python version 3, need to change.
            base64texts.append(base64_text)
        counter = 1
        for text in base64texts:
            textbase64 = doc.createElement("textBase64")
            classifytag = doc.createElement("classifyKeywords")
            textbase64.setAttribute("id","Classifytext"+ str(counter))
            ptext = doc.createTextNode(text)
            textbase64.appendChild(ptext)
            classifytag.setAttribute("id","Classify"+ str(counter))
            classifytag.setAttribute("classifierName",classifierName)
            classifytag.setAttribute("textId","Classifytext"+str(counter))
            if username != None:
                classifytag.setAttribute("username",username)
            textstag.appendChild(textbase64)
            readcalls.appendChild(classifytag)
            counter = counter + 1
        return self.connector.send(doc)
        
        def parseClassifyKeywordResponse(self,content,texts):
            """Parses the Classifier response from the server.
              :param content: (required) XML Response from server.
            """
            counter = 0
            doc = xml.dom.minidom.parseString(content)
            node = doc.documentElement
            result = []
            keyw = []
            classifytags = node.getElementsByTagName("classification")
            keywordstags = node.getElementsByTagName("keywords")
            for keyword in keywordstags:
                classtags = keyword.getElementsByTagName("class")
                for ctag in classtags:
                    kw = ctag.firstChild.data
                if kw != "":
                    keyw.append(kw)
            for classi in classifytags:
                text_coverage = classi.getAttribute("textCoverage")
                classtags = classi.getElementsByTagName("class")
                cresult = []
                for ctag in classtags:
                    classname = ctag.getAttribute("className")
                    cper = ctag.getAttribute("p")
                    tup = (classname,cper)
                    cresult.append(tup)
                result.append((texts[counter],text_coverage,cresult,keyw))
                counter = counter + 1
            return result

    def getInformation(self,classifierName):
        """Returns Information about the Classifier in a List.
           :param classifierName: (required) Classifier Name
        """
        doc, root_element, readcalls = self._buildReadDoc(classifierName)
        getinfotag = doc.createElement("getInformation")
        getinfotag.setAttribute("id","GetInformation")
        getinfotag.setAttribute("classifierName",classifierName)
        readcalls.appendChild(getinfotag)
        return self.connector.send(doc)

    def _parseClassifierInformation(self,content):
        doc = xml.dom.minidom.parseString(content)
        node = doc.documentElement
        classinfo = node.getElementsByTagName("classInformation")
        result = []
        for classes in classinfo:
            cname = classes.getAttribute("className")
            uf = classes.getElementsByTagName("uniqueFeatures")
            tc = classes.getElementsByTagName("totalCount")
            for uniquef in uf:
                uf_data = uniquef.firstChild.data
            for totalc in tc:
                tc_data = totalc.firstChild.data
            result.append((cname,uf_data,tc_data))
        return result

    def removeClassifier(self,classifierName):
        """Removes Classifier.
           :param classifierName(required): Classifier Name
        """
        doc, root_element, writecalls = self._buildWriteDoc(classifierName)
        removetag = doc.createElement("remove")
        removetag.setAttribute("id","Remove")
        writecalls.appendChild(removetag)
        return self.connector.send(doc)


if __name__ == "__main__":
    #a.setWriteApiKey("fsqAft7Hs29BgAc1AWeCIWdGnY")
    #a.setReadApiKey("aD02ApbU29kNOG2xezDGXPEIck")
    #a.create("ManorWoma")
    #a.addClass(["man","woman"],"ManorWoma")
    #a.train(["dffddddddteddddxt1","teddddxfddddddddt2","taaaaffaaaaaedddddddddddddxt3"],"woman","ManorWoma")
    #d =a.classifyKeywords(["helloof the jungle","madam of the bses","bye jungli billi"],"ManorWoma")
    #a.getInformation("ManorWoma")
    #a.removeClassifier("Freak")
    a.removeClass(["man"],"ManorWoma")
