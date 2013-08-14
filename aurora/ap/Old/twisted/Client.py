# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
from sys import argv
from pprint import pformat
from StringIO import StringIO

from twisted.internet.task import react
from twisted.web.client import Agent
from twisted.web.client import readBody
from twisted.web.http_headers import Headers
from twisted.web.client import FileBodyProducer

class Client:
    
    def __init__(self):
        react(self.send_request)

    def cbRequest(self,response):
        print 'Response version:', response.version
        print 'Response code:', response.code
        print 'Response phrase:', response.phrase
        print 'Response headers:'
        print pformat(list(response.headers.getAllRawHeaders()))
        d = readBody(response)
        d.addCallback(Client.cbBody)
        return d

    def cbBody(self,body):
        print 'Response body:'
        print body

    def send_request(reactor, arg):
        url=b"http://localhost:5555/create"
        agent = Agent(reactor)
        body = FileBodyProducer(StringIO("hello, world"))
        d = agent.request(
            'POST', url,
            Headers({'User-Agent': ['Twisted Web Client Example']}),
            None)
        d.addCallback(Client.cbRequest)
        return d
        

    
