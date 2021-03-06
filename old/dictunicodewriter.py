import cStringIO
import codecs
import csv

class DictUnicodeWriter(object):
	"""
	Code borrowed from http://stackoverflow.com/a/5838817
	"""
	def __init__(self, f, fieldnames, dialect=csv.excel, encoding="utf-8", **kwds):
		# Redirect output to a queue
		self.queue = cStringIO.StringIO()
		self.writer = csv.DictWriter(self.queue, fieldnames, dialect=dialect, **kwds)
		self.stream = f
		self.encoder = codecs.getincrementalencoder(encoding)()

	def writerow(self, D):
		self.writer.writerow({k:v.encode("utf-8") for k,v in D.items()})
		# Fetch UTF-8 output from the queue ...
		data = self.queue.getvalue()
		data = data.decode("utf-8")
		# ... and reencode it into the target encoding
		data = self.encoder.encode(data)
		# write to the target stream
		self.stream.write(data)
		# empty queue
		self.queue.truncate(0)
	
	def writerows(self, rows):
		for D in rows:
			self.writerow(D)
	
	def writeheader(self):
		self.writer.writeheader()