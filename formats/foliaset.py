# -*- coding: utf-8 -*-
#----------------------------------------------------------------
# PyNLPl - FoLiA Set Definition Module
#   by Maarten van Gompel
#   Centre for Language Studies
#   Radboud University Nijmegen
#
#   https://proycon.github.io/folia
#   httsp://github.com/proycon/pynlpl
#   proycon AT anaproy DOT nl
#
#   Module for reading, editing and writing FoLiA XML
#
#   Licensed under GPLv3
#
#----------------------------------------------------------------

#pylint: disable=redefined-builtin,trailing-whitespace,superfluous-parens,bad-classmethod-argument,wrong-import-order,wrong-import-position,ungrouped-imports

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import


import sys
import io
import rdflib
from lxml import etree as ElementTree
if sys.version < '3':
    from StringIO import StringIO #pylint: disable=import-error,wrong-import-order
    from urllib import urlopen #pylint: disable=no-name-in-module,wrong-import-order
else:
    from io import StringIO,  BytesIO #pylint: disable=wrong-import-order,ungrouped-imports
    from urllib.request import urlopen #pylint: disable=E0611,wrong-import-order,ungrouped-imports


#foliaspec:namespace:NSFOLIA
#The FoLiA XML namespace
NSFOLIA = "http://ilk.uvt.nl/folia"

#foliaspec:setdefinitionnamespace:NSFOLIASETDEFINITION
NSFOLIASETDEFINITION = "http://folia.science.ru.nl/setdefinition"

class DeepValidationError(Exception):
    pass

class SetDefinitionError(DeepValidationError):
    pass

class SetType: #legacy only
    CLOSED, OPEN, MIXED = range(3)

class LegacyClassDefinition(object):
    def __init__(self,id, label, subclasses=[]):
        self.id = id
        self.label = label
        self.subclasses = subclasses

    @classmethod
    def parsexml(Class, node):
        if not node.tag == '{' + NSFOLIA + '}class':
            raise Exception("Expected class tag for this xml node, got" + node.tag)

        if 'label' in node.attrib:
            label = node.attrib['label']
        else:
            label = ""

        subclasses= []
        for subnode in node:
            if isinstance(subnode.tag, str) or (sys.version < '3' and isinstance(subnode.tag, unicode)): #pylint: disable=undefined-variable
                if subnode.tag == '{' + NSFOLIA + '}class':
                    subclasses.append( LegacyClassDefinition.parsexml(subnode) )
                elif subnode.tag[:len(NSFOLIA) +2] == '{' + NSFOLIA + '}':
                    raise Exception("Invalid tag in Class definition: " + subnode.tag)
        if '{http://www.w3.org/XML/1998/namespace}id' in node.attrib:
            idkey = '{http://www.w3.org/XML/1998/namespace}id'
        else:
            idkey = 'id'
        return LegacyClassDefinition(node.attrib[idkey],label, subclasses)


    def __iter__(self):
        for c in self.subclasses:
            yield c

    def json(self):
        jsonnode = {'id': self.id, 'label': self.label}
        jsonnode['subclasses'] = []
        for subclass in self.subclasses:
            jsonnode['subclasses'].append(subclass.json())
        return jsonnode

    def rdf(self,graph, basens,parentset, parentclass=None):
        graph.add((rdflib.term.URIRef(basens + '#' + self.id), rdflib.RDF.type, rdflib.term.URIRef(NSFOLIASETDEFINITION + '#Class')))
        graph.add((rdflib.term.URIRef(basens + '#' + self.id), rdflib.term.URIRef(NSFOLIASETDEFINITION + '#id'), rdflib.term.Literal(self.id)))
        graph.add((rdflib.term.URIRef(basens + '#' + self.id), rdflib.term.URIRef(NSFOLIASETDEFINITION + '#label'), rdflib.term.Literal(self.label)))
        graph.add((rdflib.term.URIRef(basens + '#' + self.id), rdflib.term.URIRef(NSFOLIASETDEFINITION + '#memberOf'), rdflib.term.URIRef(basens + '#Set.' + self.id) ))
        if parentclass:
            graph.add((rdflib.term.URIRef(basens + '#' + self.id), rdflib.term.URIRef(NSFOLIASETDEFINITION + '#parentClass'), rdflib.term.URIRef(basens + '#parentClass.' + self.id) ))

        for subclass in self.subclasses:
            subclass.rdf(graph,basens,parentset, self.id)

class LegacySetDefinition(object):
    def __init__(self, id, type, classes = [], subsets = [], label =None):
        self.id = id
        self.type = type
        self.label = label
        self.classes = classes
        self.subsets = subsets

    @classmethod
    def parsexml(Class, node):
        issubset = node.tag == '{' + NSFOLIA + '}subset'
        if not issubset:
            assert node.tag == '{' + NSFOLIA + '}set'
        classes = []
        subsets= []
        if 'type' in node.attrib:
            if node.attrib['type'] == 'open':
                type = SetType.OPEN
            elif node.attrib['type'] == 'closed':
                type = SetType.CLOSED
            elif node.attrib['type'] == 'mixed':
                type = SetType.MIXED
            else:
                raise Exception("Invalid set type: ", type)
        else:
            type = SetType.MIXED

        if 'label' in node.attrib:
            label = node.attrib['label']
        else:
            label = None

        for subnode in node:
            if isinstance(subnode.tag, str) or (sys.version < '3' and isinstance(subnode.tag, unicode)): #pylint: disable=undefined-variable
                if subnode.tag == '{' + NSFOLIA + '}class':
                    classes.append( LegacyClassDefinition.parsexml(subnode) )
                elif not issubset and subnode.tag == '{' + NSFOLIA + '}subset':
                    subsets.append( LegacySetDefinition.parsexml(subnode) )
                elif subnode.tag == '{' + NSFOLIA + '}constraint':
                    pass
                elif subnode.tag[:len(NSFOLIA) +2] == '{' + NSFOLIA + '}':
                    raise SetDefinitionError("Invalid tag in Set definition: " + subnode.tag)

        return LegacySetDefinition(node.attrib['{http://www.w3.org/XML/1998/namespace}id'],type,classes, subsets, label)


    def json(self):
        jsonnode = {'id': self.id}
        if self.label:
            jsonnode['label'] = self.label
        if self.type == SetType.OPEN:
            jsonnode['type'] = 'open'
        elif self.type == SetType.CLOSED:
            jsonnode['type'] = 'closed'
        elif self.type == SetType.MIXED:
            jsonnode['type'] = 'mixed'
        jsonnode['subsets'] = {}
        for subset in self.subsets:
            jsonnode['subsets'][subset.id] = subset.json()
        jsonnode['classes'] = {}
        jsonnode['classorder'] = []
        for c in sorted(self.classes, key=lambda x: x.label):
            jsonnode['classes'][c.id] = c.json()
            jsonnode['classorder'].append( c.id )
        return jsonnode

    def rdf(self,graph, basens="",parent=None):
        if not basens:
            basens = NSFOLIASETDEFINITION + "/" + self.id
        graph.add((rdflib.term.URIRef(basens + '#Set.' + self.id), rdflib.RDF.type, rdflib.term.URIRef(NSFOLIASETDEFINITION + '#Set')))
        if self.id:
            graph.add((rdflib.term.URIRef(basens + '#Set.' + self.id), rdflib.term.URIRef(NSFOLIASETDEFINITION + '#id'), rdflib.term.Literal(self.id)))
        if self.type == SetType.OPEN:
            graph.add((rdflib.term.URIRef(basens + '#Set.' + self.id), rdflib.term.URIRef(NSFOLIASETDEFINITION + '#open'), rdflib.term.Literal(True)))
        if self.label:
            graph.add((rdflib.term.URIRef(basens + '#Set.' + self.id), rdflib.term.URIRef(NSFOLIASETDEFINITION + '#label'), rdflib.term.Literal(self.label)))
        if self.parent:
            graph.add((rdflib.term.URIRef(basens + '#Set.' + self.id), rdflib.term.URIRef(NSFOLIASETDEFINITION + '#subsetOf'), rdflib.term.URIRef(basens + '#Set.' + self.parent)))

        for c in self.classes:
            c.rdf(graph, basens, self.id)

        for s in self.subsets:
            s.rdf(graph, basens, self.id)


def xmltreefromstring(s):
    """Internal function, deals with different Python versions, unicode strings versus bytes, and with the leak bug in lxml"""
    if sys.version < '3':
        #Python 2
        if isinstance(s,unicode): #pylint: disable=undefined-variable
            s = s.encode('utf-8')
        try:
            return ElementTree.parse(StringIO(s), ElementTree.XMLParser(collect_ids=False))
        except TypeError:
            return ElementTree.parse(StringIO(s), ElementTree.XMLParser()) #older lxml, may leak!!!!
    else:
        #Python 3
        if isinstance(s,str):
            s = s.encode('utf-8')
        try:
            return ElementTree.parse(BytesIO(s), ElementTree.XMLParser(collect_ids=False))
        except TypeError:
            return ElementTree.parse(BytesIO(s), ElementTree.XMLParser()) #older lxml, may leak!!!!

class SetDefinition(object):
    def __init__(self, url, format=None, basens=""):
        self.graph = rdflib.Graph()
        if not format:
            #try to guess format from URL
            if url.endswith('.ttl'):
                format = 'text/turtle'
            elif url.endswith('.n3'):
                format = 'text/n3'
            elif url.endswith('.rdf.xml') or url.endswith('.rdf'):
                format = 'application/rdf+xml'
            elif url.endswith('.xml'): #other XML will be considered legacy
                format = 'application/foliaset+xml' #legacy

        if format in ('application/foliaset+xml','legacy',None):
            #legacy format
            self.legacyset = None
            if url[0] == '/' or url[0] == '.':
                #local file
                f = io.open(url,'r',encoding='utf-8')
            else:
                #remote URL
                if not basens:
                    basens = url
                try:
                    f = urlopen(url)
                except:
                    raise DeepValidationError("Unable to download " + url)
            try:
                tree = xmltreefromstring(f.read())
            except IOError:
                raise DeepValidationError("Unable to download " + url)
            finally:
                f.close()
            root = tree.getroot()
            if root.tag != '{' + NSFOLIA + '}set':
                raise SetDefinitionError("Not a FoLiA Set Definition! Unexpected root tag:"+ root.tag)
            legacyset = LegacySetDefinition.parsexml(root)
            self.graph = rdflib.Graph()
            legacyset.rdf(self.graph, basens)
        else:
            self.graph = rdflib.Graph()
            self.graph.parse(location=url, format=format)

    def testclass(self,cls):
        raise NotImplementedError #TODO, IMPLEMENT!

    def testsubclass(self, cls, subset, subclass):
        raise NotImplementedError #TODO, IMPLEMENT!

    def json(self):
        raise NotImplementedError #TODO, IMPLEMENT!