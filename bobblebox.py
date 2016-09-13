#!/usr/bin/python

#
# Copyright Cesar Longoria 2016-2017
# MIT License
#

import os
import sys
import json
import socket
import threading
from observer import observer as O
from observer.helpers import *

default_settings = {
	'socket':'/tmp/tutor.sock'
}

# NOTE: Can this only be initialized once?  I'm only seeing one socket file.
class _Socketeer(object):
	def __init__(self,settings=default_settings):
		self.sock = self._init_socket(settings)
		self._start_loop()
	
	def callback(self,s,conn,addr):
		conn.send('amazing '+s)
	
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
				self.buflen = 5
			def run(self):
				sock.listen(1)
				while True:
					conn,addr = sock.accept()
					m = ''.join(list(self._iter_recv_msg(conn)))
					print (guy,m,conn,addr)
					guy.callback(m,conn,addr)
					conn.close()
			def _iter_recv_msg(self,conn):
				s = '.'
				while 0 < len(s) <= self.buflen:
					s = conn.recv(self.buflen)
					yield s
				
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
			method = s[:s.index('{')]
			path = method[method.index(':')+1:] if ':' in method else ''
			method = method[:method.index(':')] if ':' in method else method
			query = json.loads(s[s.index('{'):])
			
			def stretch(path,ob,delim='.'):
				tokens = path.split(delim)
				for i in range(len(tokens)):
					t = {}
					t[tokens[-i-1]] = ob
					ob = t
				return ob
			def reach(path,ob,delim='.'):
				tokens = path.split(delim)
				for i in range(len(tokens)):
					ob = ob[tokens[i]]
				return ob
				
			print method,path
			# And here's where the magic happens.
			
			if method == 'create':
				pass
			
			elif method == 'read':
				pass
			
			elif method == 'update':
				#q = stretch(path,query)
				q = query
				ob = reach(path,self.observer)
				print q
				print ob
				for k,v in q.iteritems():
					# Something will be thrown in the callback if this fails, data-side.
					ob[k] = v
				print self.observer
			
			elif method == 'delete':
				pass
			
			# Okay, enough magic.  It's over; go home.
			conn.send(json.dumps(ob,indent=2))
		except Exception:
			pass


if __name__ == '__main__':
	box = Box(O.Dict.Recurse({'A':{'B':{'C':5}}}))
	
	import time
	while threading.active_count() > 0:
		time.sleep(.1)


