# coding: utf-8
from wikitools import wiki, api
import csv
import cStringIO
import codecs
import dateutil.parser
import calendar

_sample_article_name = 'Social_network'
_sample_category_name = 'Category:21st-century_aviation_accidents_and_incidents'

def wikipedia_query(query_params):
	"""
	An extremely basic wrapper for the wikitools api.
	"""
	site = wiki.Wiki() # This defaults to en.wikipedia.org
	request = api.APIRequest(site, query_params)
	result = request.query()
	return result[query_params['action']]

def page_revisions(page_title, page_id=-1, rvlimit=5000, debug=False):
	"""
	Given a dictionary containing the title and pageid of a page 
	on Wikipedia, this will return basic identifying information 
	for all revisions. Each revision entry will inclue the 
	original page title and pageid, the user who made the revision, the 
	timestamp of the revision (in seconds since the UNIX epoch 
	- 1/1/1970), and the unique revision id for the page.
	"""
	if debug:
		print "Getting revisions for page '%s' (%d)." % (page_title, page_id)
	result = wikipedia_query({'action': 'query', 
								'titles': page_title, 
								'prop': 'revisions', 
								'rvprop': 'ids|timestamp|user|userid',
								'rvlimit': str(rvlimit)})
	revisions = []
	if result and 'pages' in result.keys():
		page_number = result['pages'].keys()[0]
		revisions = result['pages'][page_number]['revisions']
		revisions = sorted(revisions, key=lambda revision: revision['timestamp'])
		if debug:
			print "~~@ Found %d revisions." % len(revisions)
		for i, revision in enumerate(revisions):
			# The timestamp as supplied by wikitools is in the standard ISO 
			# timestamp format. We may want to use this more flexibly in Python, 
			# so we'll convert it to number of seconds since the UNIX epoch.
			iso_timestamp = revision['timestamp']
			py_timestamp = dateutil.parser.parse(iso_timestamp)
			seconds_since_epoch = calendar.timegm(py_timestamp.timetuple())
			if 'userhidden' in revision.keys():
				revision['user'] = "userhidden"
				revision['userid'] = ''
			if 'userid' in revision.keys() and revision['userid'] == 0 and 'anon' in revision.keys():
				# Then we'll take the user, which contains an IP address,
				# and re-format it from vvv.xxx.yyy.zzz to 
				# vvvxxxyyyzzz0000000000
				ip = revision['user']
				revision['userid'] = ''.join(['0'*(3-len(octet))+octet for octet in ip.split('.')]) + "0000000000"
			revisions[i] = {'title': page_title, 
							'pageid': str(page_id),
							'user': revision['user'], 
							'userid': str(revision['userid']),
							'timestamp': str(seconds_since_epoch), 
							'revid': str(revision['revid'])}
	return revisions

def crawl_category(category_title, depth=1, debug=False):
	"""
	Given the proper name of a category on Wikipedia, this will return
	a list comprised of the category given along with all sub-categories 
	found therein. With a depth > 1, this will explore that many 
	sublevels of sub-categories for each category found. 
	"""
	explored_categories = set()
	categories_to_explore = set([category_title])
#	print repr(categories_to_explore)
	while depth > 0:
		subcategories = set()
		for category in categories_to_explore:
			if category not in explored_categories:
#				print "Exploring category '%s'..." % category
				new_subcategories = category_subcategories(category, debug=debug)
				if debug:
					print "Found %d subcategories of '%s':" % (len(new_subcategories), category)
					for ns in new_subcategories:
						print "  %s" % ns
				subcategories.update(new_subcategories)
#				categories_to_explore.remove(category)
				explored_categories.add(category)
			else:
				if debug:
					print "'%s' has already been explored!" % category
				pass
		categories_to_explore = set(subcategories)
		depth = depth - 1
	return list(explored_categories.union(categories_to_explore))

def category_pages(category_title, debug=False):
	"""
	Given the proper name of a category on Wikipedia, this will return
	a list of all proper page titles (not categories) found within that
	category.
	"""
	params = {'action': 'query', 
				'list': 'categorymembers', 
				'cmtitle': category_title, 
				'cmtype': 'page',
				'cmlimit': '500'}
	if debug:
		print "Querying Wikipedia for sub-pages of '%s'..." % (category_title)
	results = wikipedia_query(params)
	pages = []
	if 'categorymembers' in results.keys() and len(results['categorymembers']) > 0:
		if debug:
			print "Found %d sub-pages!" % (len(results['categorymembers']))
		pages = [{'title': page['title'], 'pageid': page['pageid']} for page in results['categorymembers']]
	return pages

def category_subcategories(category_title, debug=False):
	"""
	Given the proper name of a category on Wikipedia, this
	will return a list of the titles only of all sub-categories. If
	there are no sub-categories, the list returned is empty. 
	"""
	params = {'action': 'query',
				'list': 'categorymembers',
				'cmtitle': category_title,
				'cmtype': 'subcat',
				'cmlimit': '500'}
	if debug:
		print "Querying Wikipedia for sub-categories of '%s'..." % (category_title)
	results = wikipedia_query(params)
	subcategories = []
	if 'categorymembers' in results.keys() and len(results['categorymembers']) > 0:
		if debug:
			print "Found %d sub-categories!" % (len(results['categorymembers']))
		subcategories = [category['title'] for category in results['categorymembers']]
	return subcategories
		

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

		
def main():
	category_name = ''
	while category_name == '':
		category_name = raw_input("Enter a category name: ")
	category_name = unicode("Category:" + category_name)
	category_depth = -1
	while category_depth <= 0: 
		try:
			category_depth = int(raw_input("Enter a traversal depth (integer >= 1): "))
		except ValueError:
			print "Please enter an integer greater than or equal to 1."

	# First we find all categories and sub-categories
	all_categories = crawl_category(category_name, depth=category_depth, debug=True)			
	
	# Next we find all pages that exist in each of those category 
	# pages
	pages = []
	for category in all_categories:
		new_pages = category_pages(category, debug=True)
		for page in new_pages:
			if page not in pages:
				pages.append(page)

	# Next we get the revision history for each one of those pages
	all_revisions = []
	for page in pages:
		all_revisions += page_revisions(page_title=page['title'], 
										page_id=page['pageid'], debug=True)
	
	# Now we dump it all to a CSV file with Unicode support
	csv_filename = category_name + "-depth" + str(category_depth) + ".csv"
	print "Writing revisions to file '%s'." % csv_filename
	csv_file = open(csv_filename, "wb")
	# Below two line taken from http://stackoverflow.com/a/583881
	# BOM (optional...Excel needs it to open UTF-8 file properly)
	csv_file.write(u'\ufeff'.encode('utf8'))
	dw = DictUnicodeWriter(csv_file, 
							['pageid', 'userid', 'title', 'user', 'timestamp', 'revid'],
							delimiter=',',
							quotechar='"')
#	dw.writeheader()
	dw.writerows(all_revisions)
	csv_file.close()

if __name__ == "__main__":
	main()
