#!/usr/bin/python

#
# Copyright Cesar Longoria 2016-2017
# MIT License
#

# Things To Do:
# - Single socket file
#   . one global socket jives not with a class definition
# - Proper log handling
#   . everything outputs with print statements, right now
#   - decide on standardized log format
# - Daemonized thread should start *outside* the init
# - Provide a new_socket_object method of some sort
#

import os
import sys
import copy
import json
import socket
import threading
from observer import observer as O
from observer.helpers import *

default_settings = {
	'socket':'/tmp/tutor.sock'
}

def iter_recv_msg(sock,buflen):
	s = sock.recv(buflen)
	print 'gwarsh',s,len(s)
	yield s
	while len(s) == buflen:
		print 'oh come on'
		s = sock.recv(buflen)
		print 'gwarsh',s,len(s)
		print map(lambda c:ord(c),s)
		yield s

def iter_recv_msg_term(sock,buflen,term):
	# Slow, due to the 'term in s' check.  Gets around the situation where the
	# final s is precisely of length buflen, but no EOF is... raised.
	s = '.'
	while len(s) > 0:
		s = sock.recv(buflen)
		final = term in s
		yield s[:s.index(term)] if final else s
		if len(s) < buflen or final:
			break

# NOTE: Can this only be initialized once?  I'm only seeing one socket file.
class _Socketeer(object):
	def __init__(self,settings=default_settings):
		self.sock = self._init_socket(settings)
		self.settings = copy.deepcopy(settings)
		self._start_loop()
	
	def callback(self,s,conn,addr):
		conn.send('amazing '+s)
	
	def client_socket(self):
		k = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
		k.connect(self.settings['socket'])
		return k
	
	def _init_socket(self,settings=default_settings):
		if os.path.exists(settings['socket']):
			os.remove(settings['socket'])
		k = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
		k.bind(settings['socket'])
		return k
	
	def _start_loop(self):
		guy = self
		sock = self.sock
		class whatevs(threading.Thread):
			def __init__(self):
				threading.Thread.__init__(self)
				self.buflen = 3 # TODO: Set to a higher value once done with testing.
			def run(self):
				sock.listen(1)
				while True:
					conn,addr = sock.accept()
					# NOTE: Anything coming in is in string format, not binary.
					m = ''.join(list(iter_recv_msg_term(conn,self.buflen,'\0')))
					print (guy,m,conn,addr)
					guy.callback(m,conn,addr)
					conn.close()
				
		self.thread = whatevs()
		self.thread.daemon = True
		self.thread.start()

class _Observifier(object):
	def __init__(self,obs):
		self.observer = obs

class Box(_Observifier,_Socketeer):
	def __init__(self,obs,*args,**keys):
		_Socketeer.__init__(self,*args,**keys)
		_Observifier.__init__(self,obs)
	def callback(self,s,conn,addr):
		try:
			if s[0] == '{':
				# JSON object mode
				j = json.loads(s)
				method = j['method']
				path = j['path']               if j.has_key('path')  else ''
				value = json.loads(j['value']) if j.has_key('value') else None
				meta = j['meta']               if j.has_key('meta')  else None
			else:
				# method:path:value mode
				t = s.split(':',2)
				t[2] = t[2].strip()
				method = t[0]
				path = t[1]
				value = json.loads(t[2]) if len(t[2]) > 0 else None
				meta = None
			
			# NOTE: This is backwards.  It should be (ob,path,...)
			def stretch(path,ob,delim='.'):
				tokens = path.split(delim)
				for i in range(len(tokens)):
					t = {}
					t[tokens[-i-1]] = ob
					ob = t
				return ob
			def reach(path,ob,delim='.'):
				tokens = filter(lambda s:len(s)>0,path.split(delim))
				print 'tokens',tokens
				for i in range(len(tokens)):
					print 'ob',ob
					ob = ob[tokens[i]]
				return ob
			def reach2(path,ob,delim='.'):
				prev,k = None,None
				tokens = filter(lambda s:len(s)>0,path.split(delim))
				for i in range(len(tokens)):
					prev = ob
					k = tokens[i]
					ob = ob[tokens[i]]
				return prev,k
				
			print method,path
			# And here's where the magic happens.
			
			if method == 'create':
				method = 'update'
			
			if method == 'read':
				ob = reach(path,self.observer)
			
			if method == 'update':
				#q = stretch(path,value)
				q = value
				ob = reach(path,self.observer)
				print q
				print ob
				for k,v in q.iteritems():
					# Something will be thrown in the callback if this fails, data-side.
					print 'ob[%s] = %s' % (str(k),str(v))
					ob[k] = v
				print self.observer
			
			if method == 'delete':
				p,k = reach2(path,self.observer)
				try:
					del p[k]
					ob = True
				except Exception:
					ob = False
			
			# Okay, enough magic.  It's over; go home.
			conn.send(json.dumps(ob,indent=2))
		
		except Exception as e:
			print >>sys.stderr, 'EXCEPTION',e
			# TODO: Work out what on Earth the Exception return value should be.
			#   Maybe a telling message within the '<>' to ensure JSON *in*-
			#   -compatibility?
			conn.send('<>')


if __name__ == '__main__':
	# TODO: The start of the daemon thread should be called outside the init
	#   function.
	box = Box(O.Dict.Recurse({'A':{'B':{'C':5}},'D':'strayang'}))
	
	import time
	while threading.active_count() > 0:
		time.sleep(.1)


