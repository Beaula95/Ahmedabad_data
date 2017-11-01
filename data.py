import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET
import schema

OSM_PATH = "ahmedabad.osm"
NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
lower = re.compile(r'^([a-z]|_| )*$')
numeric=re.compile(r'^([a-z]|[A-Z]|[0-9]|_)*$')
mapping={ "a":"A",
		  "b":"B",
		  "c":"C",
		  "d":"D",
		  "e":"E",
		  "f":"F",
		  "g":"G",
		  "h":"H",
		  "i":"I",
		  "j":"J",
		  "k":"K",
		  "l":"L",
		  "m":"M",
		  "n":"N",
		  "o":"O",
		  "p":"P",
		  "q":"Q",
		  "r":"R",
		  "s":"S",
		  "t":"T",
		  "u":"U",
		  "v":"V",
		  "w":"W",
		  "x":"X",
		  "y":"Y",
		  "z":"Z"
		  }
SCHEMA = schema.schema

NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
	"""Clean and shape node or way XML element to Python dict"""
	node_attribs = {}
	way_attribs = {}
	way_nodes = []
	tags = [] 
	if element.tag=="node":
		for i in node_attr_fields:
			node_attribs[i]=element.get(i)
			if i=="user":
				r=node_attribs["user"]
				if re.search(lower, r[0]):
					m=re.sub(r[0],mapping[r[0]],r[0])
					j=m+r[1:]
					node_attribs["user"]=j
					if re.search(numeric,j):
						n=j.strip('0123456789')
						node_attribs["user"]=n
		print(node_attribs)
		id1=element.attrib["id"]
		for tag in element.iter("tag"):
			ntag={}
			ntag["id"]=id1
			k = tag.attrib["k"]
			if re.search(LOWER_COLON, k):
				d=k.find(":")
				ntag["key"]=tag.attrib["k"][d+1:]
			else:
				ntag["key"]=tag.attrib["k"]
			ntag["value"]=tag.attrib["v"]
			if re.search(LOWER_COLON, k):
				d=k.find(":")
				ntag["type"]=tag.attrib["k"][:d]
			else:
				ntag["type"]="regular"
			tags.append(ntag)
            #print(ntag)
			#print(tags)
		return {'node': node_attribs, 'node_tags': tags}
	elif element.tag=="way":
		for i in way_attr_fields:
			way_attribs[i]=element.get(i)
			if i=="user":
				r=way_attribs["user"]
				if re.search(lower, r[0]):
					m=re.sub(r[0],mapping[r[0]],r[0])
					j=m+r[1:]
					way_attribs["user"]=j
					if re.search(numeric,j):
						n=j.strip('0123456789')
						way_attribs["user"]=n
		print(way_attribs)
		id2=element.attrib["id"]
		for tag in element.iter("tag"):
			wtag={}
			wtag["id"]=id2
			k=tag.attrib['k']
			if re.search(LOWER_COLON, k):
				d=k.find(":")
				wtag["key"]=tag.attrib["k"][d+1:]
			else:
				wtag["key"]=tag.attrib["k"]
			wtag["value"]=tag.attrib["v"]
			if re.search(LOWER_COLON, k):
				d=k.find(":")
				wtag["type"]=tag.attrib["k"][:d]
			else:
				wtag["type"]="regular"
			tags.append(wtag)
		#print(tags)
		i=0
		for tag in element.iter("nd"):
			wnd={}
			wnd["id"]=id2
			wnd["position"]=i
			i=i+1
			wnd["node_id"]=tag.attrib["ref"]
			#print(wnd)
			way_nodes.append(wnd)
		#print(way_nodes)
		return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}
                
     
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
			 k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
		})
    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        
        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    process_map(OSM_PATH, validate=False)
