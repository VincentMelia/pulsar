'''Asynchronous HTTP client'''
import pulsar
from pulsar import lib
from pulsar.utils import httpurl

from .iostream import AsyncIOStream


__all__ = ['HttpClient']
    

class HttpConnection(httpurl.HttpConnection):
    
    def connect(self):
        if self.timeout == 0:
            self.sock = AsyncIOStream()
            self.sock.connect((self.host, self.port))
            if self._tunnel_host:
                self._tunnel()
        else:
            httpurl.HttpConnection.connect(self)
            

class HttpResponse(httpurl.HttpResponse):
    pass
    
    
class AsyncRequest(httpurl.HttpRequest):
    response_class = HttpResponse
    def on_response(self, response):
        return response
        

class HttpClient(httpurl.HttpClient):
    timeout = 0
    client_version = pulsar.SERVER_SOFTWARE
    http_connection = HttpConnection
    request_class = AsyncRequest
    