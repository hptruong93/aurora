# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor
import cgi
class Network:
    
    def __init__(self):
        root = Resource()
        root.putChild("create", self.FormPage())
        factory = Site(root)
        reactor.listenTCP(5555, factory)
        reactor.run()

    class FormPage(Resource):
        def render_GET(self, request):
           return 'GET not accepted'

        def render_POST(self, request):
           return '<html><body>You submitted: %s</body></html>' % (cgi.escape(request.args["the-field"][0]),)
