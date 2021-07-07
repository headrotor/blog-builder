""" pageunit.py: class to hold data and methods for single page in tree"""

import os
import sys
import codecs
import markdown
import glob
import shutil
import logging
from pathlib import Path
from mako.template import Template

class PageUnit(object):
    """ Holds all the info we need to generate/mess with a given page"""
    def __init__(self, src_path, global_dict=None):

        self.gdict = global_dict
        
         # this is the content source relative path to root
        self.src_path =  os.path.abspath(src_path)

        self.rel_path = os.path.relpath(src_path, self.gdict['src_root']) 

        self.html_path = ""  # this is the destination HTML relative path
        # make actual paths from relative paths by joining 
        # with src_root and html_root

        num, slug = self.num_slug(self.src_path)
        self.num = num      # number (sort) in this dir
        self.slug = slug    # clean directory name

        # calculate relative html path -- this is key for
        self.html_rel_path = self.get_html_path(self.rel_path)
        

        # html path for use in links
        #self.html_path = self.get_abs_html_path(html_rel_path)

        # filesystem path of source data in markdown format
        self.dest_path = os.path.join(self.gdict['dest_root'], 
                                      self.html_rel_path)
        
        # local copy of html files
        self.html_path = os.path.join(self.gdict['html_root'], 
                                      self.html_rel_path)
        

        self.title = "Lorem Ipsum"
        # local dictionary, add to stuff here for template rendering 
        self.ldict = self.gdict.copy()

        # populate with some defaults
        self.ldict['content_html'] = ""

        self.subdirs = []
        self.files = []
        self.tags = []
        self.content_file = None
        self.tagname = None
        self.fname = "index.html"

        # for ftp/scp transfer script, list of all files associated with this
        # page that have been modified and thus need copying to host. 
        # file paths are in html relative path format
        self.modified = []

        #self.print_my_paths()

    # implement "<" operator for sorting
    def __lt__(self, other):
        return self.html_path < other.html_path


    def sort_subdirs(self, reverse=True):
        """ sort by descending slug number"""

        if len(self.subdirs) < 2:
            return

        num = []
        for d in self.subdirs:
            n, slug = self.num_slug(d)
            num.append(int(n))
        
        sort_order = sorted((e,i) for i,e in enumerate(num))
        if reverse:
            sort_order.reverse()
        sorted_subdirs = [self.subdirs[i[1]] for i in sort_order]

        self.subdirs = sorted_subdirs

    def print_my_paths(self):
        print("-------src_path: {}".format(self.src_path))
        print("-------rel_path: {}".format(self.rel_path))
        print("------html_path: {}".format(self.html_path))
        print("------dest_path: {}".format(self.dest_path))

    def get_html_path(self, rel_path):
        # remove numbering from source path for clean destination path
        # return list of parents for breadcrumbs
        #print("orig path: {}".format(rel_path))
        
        rel_html_path = ""
        dirnames = rel_path.split(os.sep)
        for d in dirnames:
            num, slug = self.num_slug(d)
            rel_html_path = os.path.join(rel_html_path,slug)
        return rel_html_path



    def get_abs_html_path(self, path, abs_root=None):

        if abs_root is None:
            abs_root = self.gdict['html_root']

        if len(path) < 1 :
            return abs_root

        #print("path {}, abs_root {}".format(path, abs_root))    

        rel_html_path = os.path.relpath(path, abs_root)
        abs_html_path = os.path.join(self.gdict['html_root'], rel_html_path) 
        return abs_html_path

    def num_slug(self, pathname):
        # extract the index number of this pathname, e.g
        # 1.foo/2.bar/3.baz/haha.txt returns 3 (integer)
        # and the slug "baz"
        path = os.path.normpath(pathname)
        dirnames = path.split(os.sep)

        if len(dirnames) < 1:
            return -1., ""

        base = dirnames[-1]
        splits  = base.split('.')
        num = -1

        if len(splits) < 2:
            return -1., ""
        try:
            num = int(splits[0])
        except ValueError:
            return -1, ""

        # now find slug
        return num, splits[1]



    def parse_content_file(self, file_path):
        """ read a content file, parse header info and content markdown, return
        all in a dict"""

        header_dict = {'content_raw':'', 'template':'default'}
        if file_path is None:
            return header_dict

        # test if file exists
        if not os.path.exists(file_path):
            print("WARNING: no content file found in {}".format(file_path))
            return header_dict

        input_file = codecs.open(file_path, mode="r", encoding="utf-8")
        lines = []
        for line in input_file:
            # use hash as comment
            if line[0] !=  '#':
                lines.append(line.strip())
        input_file.close()    

        # parse text file until we hit "content:" -- the rest is markdown
        # header lines have first words ending in ':'
        try:
            for i, line in enumerate(lines):
                words = line.split()
                if len(words) > 0:
                    if words[0][-1] == ':':
                        key = words[0].strip(':')
                        if key == 'content':
                            header_dict['content_raw'] = '\n'.join(lines[i+1:])
                            return header_dict
                        header_dict[key] = ' '.join(words[1:]) 
        except Exception as e:
            print("ERROR parsing content file {}".format(file_path)) 
            raise e
        return header_dict


    def write_html_file_u(self, html_path, html):
        """ Write rendered unicode as UTF-8 to the given path"""
        ###print("writing content file {}".format(html_path))
        hfile = codecs.open(html_path, "w", "utf-8")
        hfile.write(html)
        hfile.close()

    def write_html_file(self, html_path, html):
        """ Write rendered unicode as UTF-8 to the given path"""
        logging.info("writing content file {}".format(html_path))
        with open(html_path, "w", encoding='utf-8') as hfile:
            try:
                hfile.write(html)
            except UnicodeEncodeError as e:
                print("Error rendering content file {}".format(html_path))
                print(e)
                
    #########################################################


    def populate(self, template_dict, page_dict):
        """ add links to parents, children"""
        ###print("populating page: {}".format(self.html_path))
        self.ldict['html_path']  = self.html_path

        # make child paths so we can look them up in dictionary
        self.child_slugs = []
        self.children = []
        for child in self.subdirs:
            num, slug = self.num_slug(child)
            if num  > 0:
                self.child_slugs.append(slug)

        for slug in self.child_slugs:
            child_html_path = os.path.join(self.html_path, slug)
            try:
                self.children.append(page_dict[child_html_path])
            except KeyError:
                logging.error(f"could not find child {child_html_path} for {self.html_path}")
 
        # make parent paths for breadcrumb navigation:
        self.parent_slugs = self.html_rel_path.split(os.sep)
        self.parents = []

        parent_html_path = self.gdict['html_root']
        for slug in self.parent_slugs:

            parent_html_path = os.path.join(parent_html_path,slug)
            try:
                self.parents.append(page_dict[parent_html_path])
            except KeyError:
                logging.error("could not find parent {}".format(parent_html_path))


        self.level = len(self.parents)
        #print("Level of this page is: {} for {}".format(self.level, self.html_path))


        # find thumbnail if it exists:
        self.thumbnail = ""
        for f in self.files:
            root, ext = os.path.splitext(f)
            if root == 'thumb':
                self.thumbnail = f
        if self.thumbnail == "" and self.gdict['warn_thumbnail']:
            logging.warning("WARNING: could not find thumb.* in {}".format(self.src_path))

        self.ldict['keywords'] = 'no keywords found'

        # Parse content file and get dict of attributes from header
        hdict = self.parse_content_file( self.content_file)

        # set up the right template
        if hdict['template'] == 'default':
            if len(self.children) > 0:
                self.template_name = 'gallery'
            else:
                self.template_name = 'leaf'
        else:
            self.template_name = hdict['template']

        # extract tags
        if 'tags' in hdict:
            for t in hdict['tags'].split(','):
                if len(t.strip()) > 0:
                    self.tags.append(t.strip())

        # convert tag to list if a single string:
        if isinstance(self.tags, str):
            self.tags = [self.tags]
            
        #if len(self.tags) > 0:
        #    logging.warning("tags for {}: ".format(self.html_path)  + ";".join(self.tags))

        try:
            self.template = template_dict[self.template_name]
        except KeyError:
            logging.warning('WARNING: template "{}" not found, using leaf.'.format(self.template_name))
            self.template = template_dict['leaf']

        info_str = 'generating {}'.format(self.html_path)
        #info_str += 'from {}'.format(self.src_path)
        info_str += ' using "{}" template'.format(self.template_name)
        logging.info(info_str)

        self.permalink = "http://"  + self.gdict['hostname'] + os.path.join(self.html_path, self.fname)

        self.ldict.update(hdict)

        self.ldict['permalink'] = self.permalink 
        self.ldict['children'] = self.children
        self.ldict['parents'] = self.parents
        self.ldict['tags'] = self.tags
        self.title = self.ldict['title']


        try:
            self.ldict['content_html'] = markdown.markdown(hdict['content_raw'])
        except Exception as e:
            logging.error("parsing markdown in {}".format(self.content_file)) 
            raise e


    #########################################################


    def render(self, template_dict, page_dict):
        self.dest_file = os.path.join(self.dest_path,self.fname)
        dest_file = self.dest_file
        src_file = self.content_file
        if os.path.isfile(dest_file) and src_file is not None:

            if os.path.getctime(src_file) > os.path.getctime(dest_file):
                logging.info(f"incrementally updated src file {src_file}")
            else:
                if self.gdict['incremental']:
                    #logging.info(f"stale {src_file}, skipping")
                    return
                    
        # make a leaf directory
        self.check_or_create_dir(self.dest_path)
        # copy files
        images, js  = self.copy_media(self.src_path, self.dest_path)
        self.ldict['images'] = images


        # render content html through template
        pagetemplate = Template(self.ldict['content_html'])
        cooked_html = pagetemplate.render(**self.ldict)
        self.ldict['content_html'] = cooked_html


        # render template with all variables
        try:
            self.html = self.template.render(**self.ldict)
        except NameError as e:
            if self.tagname is not None:
                logging.error("template subs in {}".format(self.tagname)) 
            if self.content_file is not None:
                logging.error("template subs in {}".format(self.content_file)) 
            raise e

        self.modified.append(dest_file)
        self.write_html_file(dest_file, self.html)

    def copy_if_newer(self, src, dest):
        # if desitnation exists:
        if os.path.isfile(dest):
            if os.path.getctime(src) > os.path.getctime(dest):
                if os.path.isdir(dest):
                    dest = os.path.join(dest, os.path.basename(src))
                shutil.copy(src,dest)
                self.modified.append(dest)
        else: 
            shutil.copy(src,dest)
            self.modified.append(dest)

    def copy_media(self, src_path, html_path):
        # make a copy of images, etc in local path
        ###print("copy media from  {}  to {}".format(src_path, html_path))
        images = []
        media = ['.jpg', '.jpeg', '.png', '.gif', '.webp',
                 '.mp3' , '.mp4', '.html', '.pdf', '.svg', '.FCStd']
        media.extend([s.upper() for s in media])
        for ext in media:
            path_glob = os.path.join(src_path, '*' + ext)
            media_files = glob.glob(path_glob)
            for f in media_files:
                #print("   copying {} to {}".format(f, html_path))
                self.copy_if_newer(f,html_path)
                root, ext = os.path.splitext(os.path.basename(f))
                # exclude thumbs from list so we don't render them twice
                if root != 'thumb':
                    images.append(os.path.basename(f))
        js = []
        for ext in ['.js', '.pde', '.class' ]:
            path_glob = os.path.join(src_path, '*' + ext)
            media_files = glob.glob(path_glob)
            for f in media_files:
                ###print("   copying {} to {}".format(f, html_path))
                self.copy_if_newer(f,html_path)
                js.append(os.path.basename(f))
        return images, js

    def check_or_create_dir(self, path):
        "Create the directory if it does not exist"
        if not os.path.isdir(path):
            os.makedirs(path)

if __name__ == '__main__':
    pass
