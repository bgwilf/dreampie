# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['HistPersist']

from os.path import abspath, dirname, basename, exists
import re
from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint

import gtk

_ = lambda s: s

class HistPersist(object):
    """
    Provide actions for storing and loading history.
    """
    
    def __init__(self, window_main, textview, status_bar):
        self.window_main = window_main
        self.textview = textview
        self.textbuffer = textview.get_buffer()
        self.status_bar = status_bar
        
        self.filename = None
    
    def _save_or_warn(self, parent, filename):
        """
        Save history to a file. On IOError, display a message and return False.
        On success, return True.
        """
        filename = abspath(filename)
        try:
            f = open(filename, 'wb')
            save_history(self.textview, f)
            f.close()
        except IOError, e:
            m = gtk.MessageDialog(d, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING,
                                    gtk.BUTTONS_OK)
            m.props.text = _('Error when saving file: %s') % e
            m.run()
            m.destroy()
            return False
        self.filename = filename
        self.status_bar.set_status(_('History saved.'))
        return True

    def save(self):
        if self.filename is None:
            self.save_as()
        self._save_or_warn(self.window_main, self.filename)
    
    def save_as(self):
        d = gtk.FileChooserDialog(
            _('Choose where to save the history'), self.window_main,
            gtk.FILE_CHOOSER_ACTION_SAVE,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
             gtk.STOCK_OK, gtk.RESPONSE_OK))
        fil = gtk.FileFilter()
        fil.set_name(_('HTML Files'))
        fil.add_pattern('*.html')
        d.add_filter(fil)
        if self.filename:
            d.set_current_folder(dirname(self.filename))
            d.set_current_name(basename(self.filename))
        else:
            d.set_current_name('dreampie-history.html')
        while True:
            r = d.run()
            if r == gtk.RESPONSE_CANCEL:
                break
            filename = abspath(d.get_filename())
            if exists(filename):
                m = gtk.MessageDialog(d, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION)
                m.props.text = _('A file named "%s" already exists.  Do '
                                    'you want to replace it?'
                                    ) % basename(filename)
                m.props.secondary_text = _(
                    'The file already exists in "%s".  Replacing it will '
                    'overwrite its contents.'
                    ) % basename(dirname(filename))
                m.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
                m.add_button(_('_Replace'), gtk.RESPONSE_OK)
                m.set_default_response(gtk.RESPONSE_CANCEL)
                mr = m.run()
                m.destroy()
                if mr == gtk.RESPONSE_CANCEL:
                    continue
                    
            success = self._save_or_warn(d, filename)
            if success:
                break
        d.destroy()
    
    def load(self):
        d = gtk.FileChooserDialog(
            _('Choose the saved history file'), self.window_main,
            gtk.FILE_CHOOSER_ACTION_OPEN,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
             gtk.STOCK_OK, gtk.RESPONSE_OK))
        fil = gtk.FileFilter()
        fil.set_name(_('HTML Files'))
        fil.add_pattern('*.html')
        d.add_filter(fil)
        while True:
            r = d.run()
            if r == gtk.RESPONSE_CANCEL:
                break
            filename = abspath(d.get_filename())
            try:
                s = open(filename, 'rb').read()
                parser = Parser(self.textbuffer)
                parser.feed(s)
                parser.close()
                self.status_bar.set_status(_('History loaded.'))
            except Exception, e:
                m = gtk.MessageDialog(d, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING,
                                        gtk.BUTTONS_OK)
                m.props.text = _('Error when loading file: %s') % e
                m.run()
                m.destroy()
            else:
                break
        d.destroy()

def _html_escape(s):
    """
    Replace special characters "&", "<" and ">" to HTML-safe sequences.
    """
    # This is taken from cgi.escape - I didn't want to import it, because of
    # py2exe
    s = s.replace("&", "&amp;") # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    return s

def _format_color(color):
    return '#%02x%02x%02x' % (color.red >> 8, color.green >> 8, color.blue >> 8)

def save_history(textview, f):
    """
    Save the history - the content of the textview - to a HTML file f.
    """
    tv = textview
    tb = tv.get_buffer()
    style = tv.get_style()

    f.write("""\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta name="DreamPie Format" content="1">
<title>DreamPie History</title>
<style>
body {
  white-space: pre-wrap;
  font-family: %s;
  font-size: %s;
  color: %s;
  background-color: %s;
}
""" % (
    style.font_desc.get_family(),
    style.font_desc.get_size(),
    _format_color(style.text[0]),
    _format_color(style.base[0]),
    )
)
    
    tt = tb.get_tag_table()
    all_tags = []
    tt.foreach(lambda tag, data: all_tags.append(tag))
    all_tags.sort(key=lambda tag: -tag.get_priority())
    
    for tag in all_tags:
        f.write("span.%s {\n" % tag.props.name)
        if tag.props.foreground_set:
            f.write("  color: %s;\n" % _format_color(tag.props.foreground_gdk))
        if tag.props.background_set:
            f.write("  background-color: %s;\n"
                    % _format_color(tag.props.background_gdk))
        if tag.props.invisible:
            f.write(" display: none;\n")
        f.write("}\n")
    
    f.write("""\
</style>
</head>
<body>""")
    
    cur_tags = []
    it = tb.get_start_iter()
    while True:
        new_tags = cur_tags[:]
        for tag in it.get_toggled_tags(False):
            new_tags.remove(tag)
        for tag in it.get_toggled_tags(True):
            new_tags.append(tag)
        new_tags.sort(key=lambda tag: -tag.get_priority())
        
        shared_prefix = 0
        while (len(cur_tags) > shared_prefix and len(new_tags) > shared_prefix
               and cur_tags[shared_prefix] is new_tags[shared_prefix]):
            shared_prefix += 1
        for i in range(len(cur_tags) - shared_prefix):
            f.write('</span>')
        for tag in new_tags[shared_prefix:]:
            f.write('<span class="%s">' % tag.props.name)
        
        if it.compare(tb.get_end_iter()) == 0:
            # We reached the end. We break here, because we want to close
            # the tags.
            break
        
        new_it = it.copy()
        new_it.forward_to_tag_toggle(None)
        text = tb.get_text(it, new_it).decode('utf8')
        text = _html_escape(text)
        f.write(text.encode('utf8'))
        
        it = new_it
        cur_tags = new_tags
    
    f.write("""\
</body>
</html>
""")

class LoadError(Exception):
    pass

class Parser(HTMLParser):
    def __init__(self, textbuffer):
        HTMLParser.__init__(self)
        
        self.textbuffer = tb = textbuffer

        self.reached_body = False
        self.version = None
        self.cur_tags = []
        self.leftmark = tb.create_mark(None, tb.get_start_iter(), True)
        self.rightmark = tb.create_mark(None, tb.get_start_iter(), False)
    
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if not self.reached_body:
            if tag == 'meta':
                if 'name' in attrs and attrs['name'] == 'DreamPie Format':
                    if attrs['content'] != '1':
                        raise LoadError("Unrecognized DreamPie Format")
                    self.version = 1
            if tag == 'body':
                if self.version is None:
                    raise LoadError("File is not a DreamPie history file.")
                self.reached_body = True
        else:
            if tag == 'span':
                if 'class' not in attrs:
                    raise LoadError("<span> without a 'class' attribute")
                self.cur_tags.append(attrs['class'])
    
    def handle_endtag(self, tag):
        if tag == 'span':
            if not self.cur_tags:
                raise LoadError("Too many </span> tags")
            self.cur_tags.pop()
    
    def insert(self, data):
        tb = self.textbuffer
        leftmark = self.leftmark; rightmark = self.rightmark
        # For some reasoin, insert_with_tags_by_name marks everything with the
        # message tag. So we do it all by ourselves...
        tb.insert(tb.get_iter_at_mark(leftmark), data)
        leftit = tb.get_iter_at_mark(leftmark)
        rightit = tb.get_iter_at_mark(rightmark)
        tb.remove_all_tags(leftit, rightit)
        for tag in self.cur_tags:
            tb.apply_tag_by_name(tag, leftit, rightit)
        tb.move_mark(leftmark, rightit)

    def handle_data(self, data):
        if self.reached_body:
            self.insert(data.decode('utf8'))
    
    def handle_charref(self, name):
        raise LoadError("Got a charref %r and not expecting it." % name)
    
    def handle_entityref(self, name):
        if self.reached_body:
            self.insert(unichr(name2codepoint[name]))
    
    def close(self):
        HTMLParser.close(self)
        
        tb = self.textbuffer
        tb.delete_mark(self.leftmark)
        tb.delete_mark(self.rightmark)

