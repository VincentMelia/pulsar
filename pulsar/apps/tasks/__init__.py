'''\
A task scheduler application with HTTP-RPC hooks
'''
import os
import pulsar
from time import time
from pulsar.utils.importer import import_modules

from .models import *
from .config import *
from .registry import registry

class TaskException(pulsar.PulsarException):
    pass

class TaskNotAvailable(TaskException):
    MESSAGE = 'Task {0} is not registered. Check your settings.'
    def __init__(self, task_name):
        super(TaskNotAvailable,self).__init__(self.MESSAGE.format(task_name))

class TaskTimeout(TaskException):
    MESSAGE = 'Task {0} timed-out (timeout was {1}).'
    def __init__(self, task, timeout):
        super(TaskNotAvailable,self).__init__(self.MESSAGE.format(task,timeout))


class TaskConsumer(object):
    
    def __init__(self, schedulter):
        self.log = schedulter.log
        self.cfg = schedulter.cfg
        import_modules(self.cfg.tasks_path)
        
    def _handle_task(self, request):
        if request.on_start():
            task = registry[request.name]
            return request, task(self, *request.args,**request.kwargs)
        else:
            raise TaskTimeout(task,request.expires)

    def _handle_end(self, request, result):
        if isinstance(result,Exception):
            request.on_finish(exception = result)
        else:
            request.on_finish(result = result)
        

class TaskRequest(object):
    time_start    = None
    time_end      = None
    result        = None
    exception     = None
    timeout       = False
    _already_revoked = False
    
    def __init__(self, task, args, kwargs, retries = 0, expires = None):
        self.time_executed = time()
        self.name = task.name
        self.id = task.make_task_id(args,kwargs)
        self.args = args
        self.kwargs = kwargs
        retries = retries
        self.expires = expires
        
    def on_start(self):
        timeout = self.revoked()
        self.timeout = timeout
        self.exception = timeout
        self.time_start = time.time()
        if timeout:
            self.time_end  = time.time()
            return False
        return True
    
    def on_finish(self, exception = None, result = None):
        self.exception = exception
        self.result = result
        if not self.time_end:
            self.time_end = time.time()
        
    def maybe_expire(self):
        if self.expires and time() > self.expires:
            return True
    
    def revoked(self):
        if self._already_revoked:
            return True
        if self.expires:
            self.maybe_expire()
        return False
    
    def execute2start(self):
        if self.time_start:
            return self.time_start - self.time_executed
        
    def execute2end(self):
        if self.time_end:
            return self.time_end - self.time_executed
        
    def duration(self):
        if self.time_end:
            return self.time_end - self.time_start         
        

class TaskApplication(pulsar.Application):
    '''A task scheduler to be used with task Workers'''
    
    def get_task_queue(self):
        return pulsar.Queue()
    
    def init(self, parser = None, opts = None, args = None):
        self.cfg.worker_class = 'task'
        import_modules(self.cfg.tasks_path)
        
    def load(self):
        '''Load the application callable'''
        TaskConsumer(self)
        
    def make_request(self, task_name, targs, tkwargs, **kwargs):
        '''Create a new Task Request'''
        if task_name in registry:
            task = registry[task_name]
            return TaskRequest(task, targs, tkwargs, **kwargs)
        else:
            raise TaskNotAvailable(task_name)
    
        
    