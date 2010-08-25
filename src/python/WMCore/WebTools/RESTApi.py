#!/usr/bin/env python
"""
_RESTApi_

A standard class implementing a REST interface. You should configure the 
application to point at this class, with a model and formatter class configured:

active.section_('rest')
active.rest.object = 'WMCore.WebTools.RESTApi'
active.rest.templates = environ['WTBASE'] + '/templates/WMCore/WebTools/'
active.rest.database = 'sqlite:////Users/metson/Documents/Workspace/GenDB/gendb.lite'
active.rest.section_('model')
active.rest.model.object = 'RESTModel'
active.rest.model.database = 'sqlite:////Users/metson/Documents/Workspace/GenDB/gendb.lite'
active.rest.model.templates = environ['WTBASE'] + '/templates/WMCore/WebTools/'
active.rest.section_('formatter')
active.rest.formatter.object = 'RESTFormatter'
active.rest.formatter.templates = '/templates/WMCore/WebTools/'

"""

__revision__ = "$Id: RESTApi.py,v 1.6 2009/03/16 12:07:58 metson Exp $"
__version__ = "$Revision: 1.6 $"

from WMCore.WebTools.WebAPI import WebAPI
from WMCore.WebTools.Page import Page, exposejson, exposexml
from WMCore.WMFactory import WMFactory
from cherrypy import expose, request, response
from cherrypy.lib.cptools import accept
try:
    # Python 2.6
    import json
except:
    # Prior to 2.6 requires simplejson
    import simplejson as json

class RESTApi(WebAPI):
    """
    Don't subclass this, use the RESTModel as a base for your application code
    """
    __version__ = 1
    def __init__(self, config = {}):
        
        #formatterconfig = config.section_('formatter')
        #formatterconfig.application = config.application
        self.set_formatter(config)
        
        #modelconfig = config.section_('model')
        #modelconfig.application = config.application
        self.set_model(config)
        
        self.__doc__ = self.model.__doc__
        
        WebAPI.__init__(self, config)
        self.methods.update({'GET':{'args':[],
                                 'call':self.model.handle_get,
                                 'version': 1},
                            'POST':{'args':[],
                                 'call':self.model.handle_post,
                                 'version': 1},
                            'PUT':{'args':[],
                                 'call':self.model.handle_put,
                                 'version': 1},
                            'DELETE':{'args':[],
                                 'call':self.model.handle_delete,
                                 'version': 1},
                            'UPDATE':{'args':[],
                                 'call':self.model.handle_update,
                                 'version': 1}})
        
        self.supporttypes  = ['application/xml', 'application/atom+xml',
                             'text/json', 'text/x-json', 'application/json',
                             'text/html','text/plain']
        
    def set_model(self, config):
        factory = WMFactory('webtools_factory')
        self.model = factory.loadObject(config.model.object, config)
        
    def set_formatter(self, config):
        factory = WMFactory('webtools_factory')
        self.formatter = factory.loadObject(config.formatter.object, config)

    @expose
    def index(self, *args, **kwargs):
        """
        Return the auto-generated documentation for the API
        """
        if len(args) == 0 and len(kwargs) == 0:
            self.debug('returning documentation')
            return self.templatepage('API', methods = self.methods, 
                                 application = self.config.application)
        else:
            return self.buildResponse(args, kwargs)
    @expose
    def default(self, *args, **kwargs):
        """
        Return the autogenerated documentation for the API (by calling index())
        """
        if len(args) == 0 and len(kwargs) == 0:
            return self.index()
        else:
            return self.buildResponse(args, kwargs)
    
    def buildResponse(self, args, kwargs):
        """
        Set the headers for the response appropriately and format the response 
        data (e.g. serialise to XML, JSON, RSS/ATOM).
        """
        datatype = accept(self.supporttypes)
        response.headers['Content-Type'] = datatype
        
        data = self.methods[request.method]['call'](args, kwargs)
        
        if datatype in ('text/json', 'text/x-json', 'application/json'):
            # Serialise to json
            return self.formatter.json(data)
        elif datatype == 'application/xml':
            # Serialise to xml
            return self.formatter.xml(data)
        elif datatype == 'application/atom+xml':
            # Serialise to atom
            return self.formatter.atom(data)

        # TODO: Add other specific content types
        response.headers['Content-Length'] = len(data)
        return data
