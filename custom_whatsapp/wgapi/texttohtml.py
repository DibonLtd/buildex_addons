# -*- coding: utf-8 -*-
import re

from html.parser import HTMLParser

def formatHtml(text):
    # Remove Windows Linebreaks
    text = text.replace('\r\n', '\n')

    # Replace  H1
    text = re.sub(r'(\n/(?!/))(?P<id>.+)', r'<h1>\g<id></h1>', text, 1)

    # Replace  H2
    text = re.sub(r'(\n//(?!/))(?P<id>.+)', r'\n<h2>\g<id></h2>', text)

    # Replace  H3
    text = re.sub(r'(\n///(?!/))(?P<id>.+)', r'\n<h3>\g<id></h3>', text)
    
    # Replace  H4
    text = re.sub(r'(\n////(?!/))(?P<id>.+)', r'\n<h4>\g<id></h4>', text)

    # Replace IMG
    # img + link (external)
    text = re.sub(r'(?P<prefix> |\n)img__http://(?P<fileName>.*?)(?P<fileExt>\.gif|\.jpg|\.jpeg|\.png)__(?P<fileAlt>.*?)__(?P<link>.*?)__', r'\g<prefix><a href="\g<link>"><img src="http://\g<fileName>\g<fileExt>" alt="\g<fileAlt>" title="\g<fileAlt>" /></a>', text)
    # img + link (internal)
    text = re.sub(r'(?P<prefix> |\n)img__(?P<fileName>.*?)(?P<fileExt>\.gif|\.jpg|\.jpeg|\.png)__(?P<fileAlt>.*?)__(?P<link>.*?)__', r'\g<prefix><a href="\g<link>"><img src="/static/upload/\g<fileName>\g<fileExt>" alt="\g<fileAlt>" title="\g<fileAlt>" /></a>', text)
    # img only (external)
    text = re.sub(r'(?P<prefix> |\n)img__http://(?P<fileName>.*?)(?P<fileExt>\.gif|\.jpg|\.jpeg|\.png)__(?P<fileAlt>.*?)__', r'\g<prefix><img src="http://\g<fileName>\g<fileExt>" alt="\g<fileAlt>" title="\g<fileAlt>" />', text)
    # img only (internal)
    text = re.sub(r'(?P<prefix> |\n)imgright__(?P<fileName>.*?)(?P<fileExt>\.gif|\.jpg|\.jpeg|\.png)__(?P<fileAlt>.*?)__', r'\g<prefix><img src="/static/upload/\g<fileName>\g<fileExt>" alt="\g<fileAlt>" title="\g<fileAlt>" style="float:right" />', text)
    text = re.sub(r'(?P<prefix> |\n)imgcenter__(?P<fileName>.*?)(?P<fileExt>\.gif|\.jpg|\.jpeg|\.png)__(?P<fileAlt>.*?)__', r'\g<prefix><div class="row" style="text-align:center"><img src="/static/upload/\g<fileName>\g<fileExt>" alt="\g<fileAlt>" title="\g<fileAlt>" /></div>', text)
    text = re.sub(r'(?P<prefix> |\n)img__(?P<fileName>.*?)(?P<fileExt>\.gif|\.jpg|\.jpeg|\.png)__(?P<fileAlt>.*?)__', r'\g<prefix><img src="/static/upload/\g<fileName>\g<fileExt>" alt="\g<fileAlt>" title="\g<fileAlt>" />', text)
    
    # Replace A
    # We add a space to all A near a special character or at the end of a line
    # We add a double space to A with already 1 space to preserve that space after linkFormat function
    text = re.sub(r'__(?P<link>(http://|/).*?)__ ', r'__\g<link>__  ', text)
    text = re.sub(r'__(?P<link>(http://|/).*?)__(?P<anchor>\n|,|\.|;|\?|!|:|<)', r'__\g<link>__ \g<anchor>', text)
    # All A followed by a space will be targeted
    text = re.sub(r'__(?P<id>(http://|/).*?)__ ', formatLink, text)

    # Replace  LI
    text = re.sub(r'(\n- (?P<id>.+))', r'\n<li>\g<id></li>', text)
    
    # Replace TABLE
    text = re.sub(r'(!!)(?P<id>.*?)', r'</td><td>', text)
    text = re.sub(r'\n\n</td><td>(?P<id>.*)', r'\n<table class="table table-bordered table-striped table-hover"><tr><td>\g<id>', text)
    text = re.sub(r'</td><td>\n</td><td>', r'</td></tr>\n<tr><td>', text)
    text = re.sub(r'</td><td>\n\n', r'</td></tr></table>\n\n', text)
    
    # Replace DOC
    text = re.sub(r'(?P<prefix> |\n)__(?P<fileName>.*?)__(?P<anchor>.*?)__', r'\g<prefix><a href="/static/upload/\g<fileName>">\g<anchor></a>', text)
    
    # Replace BR and P
    text = re.sub(r'\n(?!\n)(?!<h1|<h2|<h3|<li|<ul|<table|<tr|<td|</td)', r'<br />', text)
    text = re.sub(r'\n<br />', r'\n<p>', text)
    text = re.sub(r'\n<p>(?P<id>.*)', r'\n<p>\g<id></p>', text)
    
    # Replace UL and LI
    text = re.sub(r'\n\n<li>(?P<id>.*)', r'\n<ul><li>\g<id>', text)
    text = re.sub(r'</li>\n(?!<li>)', r'</li></ul>\n', text)
    
    # Replace I
    text = re.sub(r'\*\*(?!\*)(?P<id>.*?)\*\*(?!\*)', r'<i>\g<id></i>', text)
    
    # Replace B
    text = re.sub(r'\*(?!\*)(?P<id>.*?)\*(?!\*)', r'<b>\g<id></b>', text)
    
    # Clean accidental empy tags
    text = re.sub(r'<p></p>', '', text)
    
    return text

def formatLink(match):
    g = match.groups()[0].partition('__')
    # No custom anchor
    if g[1] == '':
        return '<a href="'+g[0]+'">'+g[0]+'</a>'
    # Custom anchor found
    else:
        return '<a href="'+g[0]+'">'+g[2]+'</a>'

class HTMLToTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def handle_charref(self, name):
        self.text.append(chr(int(name)))

    def handle_entityref(self, name):
        # Handle named HTML entities
        # You can extend this to handle more entities if needed
        self.text.append(chr(HTMLParser.entitydefs[name]))

    def get_text(self):
        return ''.join(self.text)

def formatText(html_content):
    parser = HTMLToTextParser()
    parser.feed(html_content)
    return parser.get_text()