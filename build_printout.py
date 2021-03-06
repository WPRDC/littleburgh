import re, csv, sys
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import ckanapi
from pprint import pprint
from datetime import datetime

def get_resource_data(site,resource_id,API_key=None,count=50,offset=0,fields=None):
    # Use the datastore_search API endpoint to get <count> records from
    # a CKAN resource starting at the given offset and only returning the
    # specified fields in the given order (defaults to all fields in the
    # default datastore order).
    ckan = ckanapi.RemoteCKAN(site, apikey=API_key)
    if fields is None:
        response = ckan.action.datastore_search(id=resource_id, limit=count, offset=offset)
    else:
        response = ckan.action.datastore_search(id=resource_id, limit=count, offset=offset, fields=fields)
    # A typical response is a dictionary like this
    #{u'_links': {u'next': u'/api/action/datastore_search?offset=3',
    #             u'start': u'/api/action/datastore_search'},
    # u'fields': [{u'id': u'_id', u'type': u'int4'},
    #             {u'id': u'pin', u'type': u'text'},
    #             {u'id': u'number', u'type': u'int4'},
    #             {u'id': u'total_amount', u'type': u'float8'}],
    # u'limit': 3,
    # u'records': [{u'_id': 1,
    #               u'number': 11,
    #               u'pin': u'0001B00010000000',
    #               u'total_amount': 13585.47},
    #              {u'_id': 2,
    #               u'number': 2,
    #               u'pin': u'0001C00058000000',
    #               u'total_amount': 7827.64},
    #              {u'_id': 3,
    #               u'number': 1,
    #               u'pin': u'0001C01661006700',
    #               u'total_amount': 3233.59}],
    # u'resource_id': u'd1e80180-5b2e-4dab-8ec3-be621628649e',
    # u'total': 88232}
    data = response['records']
    return data

def get_services(site):
    resource_id = "5a05b9ec-2fbf-43f2-bfff-1de2555ff7d4"
    data = get_resource_data(site,resource_id,count=9999999)
    return data

def extend_story(Story,line,indent=None):
    if line == "":
        Story.append(Spacer(1, 12))
    else:
        styles=getSampleStyleSheet()
        #styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, fontName='SourceSansPro-Bold', fontSize=10, leftIndent=1))
        left_indent = 0
        if indent is not None:
            left_indent = indent
        if re.search("Recommended",line) is not None:
            left_indent = 18
        if re.search("Requirements",line) is not None:
            left_indent = 18
        styles.add(ParagraphStyle(name='Justify-and-Indent', alignment=TA_JUSTIFY, fontSize=10, leftIndent=left_indent))
        #ptext = '<font size=12>{}</font>'.format(line)
        ptext = '{}'.format(line)
        Story.append(Paragraph(ptext, styles["Justify-and-Indent"]))

def format_meals(meals,Story,keep_kids_only=True,keep_pets_only=True,hoods=None):
    from collections import defaultdict
    ms_by_hood = defaultdict(list)
    for m in meals:
        store = True
        if not keep_kids_only:
            if m['requirements'] is not None and re.search('kids',m['requirements'], re.IGNORECASE) is not None:
                store = False

        if not keep_pets_only:
            if m['recommended_for'] is not None and m['recommended_for'] == 'all pets in need':
                store = False

        if store:
            ms_by_hood[m['neighborhood'].upper()].append(m)

    if hoods is None:
        hoods = ms_by_hood.keys()
    else:
        hoods = [h.upper() for h in hoods]

    transmitted_ms = []
    for j,hood in enumerate(sorted(ms_by_hood.keys())):
        if hood in hoods:
            extend_story(Story, "{}".format(hood))
            ms = ms_by_hood[hood]
            for k,m in enumerate(ms):
                transmitted_ms.append(m)
                extend_story(Story, "    <b>{}</b> ({})".format(m['service_name'],m['address']))
                holiday_exception = " ({})".format(m['holiday_exception']) if m['holiday_exception'] is not None else ""
                extend_story(Story, "    {}{}".format(m['schedule'], holiday_exception))
                extend_story(Story, "    {}".format(m['narrative']), 9)
                requirements = m['requirements']
                if requirements not in [None,'none','None']:
                    extend_story(Story, "       <u>Requirements</u>: {}".format(requirements))
                recommended_for = m['recommended_for']
                if recommended_for not in ['all','All in need','all who need food']:
                    extend_story(Story, "       <u>Recommended for</u>: {}".format(recommended_for))
                if k != len(ms)-1:
                    extend_story(Story, "")

            if j != len(ms_by_hood)-1:
                extend_story(Story, "")

    return transmitted_ms

if len(sys.argv) == 1:
    hoods = None
else:
    hoods_args = sys.argv[1:]
    hoodstring = ' '.join(hoods_args)
    hoods = hoodstring.split(', ')


site = "https://data.wprdc.org"
services = get_services(site)

doc = SimpleDocTemplate("meals.pdf",pagesize=letter,
                        rightMargin=52,leftMargin=52,
                        topMargin=72,bottomMargin=18)
Story=[]
width, height = letter
title = "==== Meal/food opportunities extracted from Social Service listings from BigBurgh.com ===="
styles=getSampleStyleSheet()
Story.append(Paragraph(title, styles["Normal"]))


meals = [s for s in services if re.search('meals', s['category'])]
filtered_meals = format_meals(meals,Story,keep_kids_only=False,keep_pets_only=False,hoods=hoods)

footer = "[This information was obtained for {} from https://data.wprdc.org/dataset/bigburgh-social-service-listings]".format(datetime.strftime(datetime.now(),"%b %Y"))
foooter = "<font size=8>{}</font>".format(footer)
Story.append(Paragraph(footer, styles["Normal"]))
doc.build(Story)
print("{} meal/pantry locations found in {} neighborhoods.".format(len(filtered_meals),len(hoods)))

# > python make_printout.py Squirrel Hill, Wilkinsburg, Downtown
