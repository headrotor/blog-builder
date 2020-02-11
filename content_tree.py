import os
import logging
from datetime import datetime as dt
from mako.template import Template
from mako.lookup import TemplateLookup
from mako import exceptions

from page_unit import PageUnit


class ContentTree(object):
    def __init__(self, global_dict):
        self.gdict = global_dict
        self.src_root = global_dict['src_root']
        self.dest_root = global_dict['dest_root']

        self.pages = [] # list of pages
        self.page_dict = {} # dict of pages, referenced by uri

        self.tag_pages = []
        self.tag_dict = {}

        # keep track of updated files for ftp script
        self.updated = []
        self.updated_tags = {}

        # preload some templates
        self.template_dict = self.load_templates()
        for key in self.template_dict:
            logging.info('found template "{}"'.format(key))
        if len(self.template_dict) == 0:
            logging.error("Could not find templates, exiting")
            logging.error("check template directory in config file")
            exit(0)
                
            
    def goodpath(self, path):
        """ return normalized relative path to root"""
        if os.sep != '/':
            path = '/'.join(path.split(os.sep))
        abs_path =  os.path.abspath(path)
        src_path = os.path.relpath(path, self.gdict['src_root'])
        return 

    def load_templates(self, gdict = None):
        if gdict is None:
            gdict = self.gdict
            
        # look for html files in template directory, make into mako templates

        template_dir = os.path.abspath(self.gdict['template_dir'])
        mylookup = TemplateLookup(directories=[template_dir])
        logging.info("looking for templates in {}".format(self.gdict['template_dir']))
        template_dict = {}
        files = os.listdir(template_dir)
        for f in files:
            path, fname = os.path.split(f)
            root, ext = os.path.splitext(fname)
            if ext == '.html' or ext == '.xml':
                uri = os.path.join(template_dir, f)
                # print(uri)
                # try:
                #     template = mylookup.get_template(uri)
                #     print(template.render())
                # except:
                #     print(exceptions.html_error_template().render())
                template = Template(filename=uri,
                                    lookup = mylookup,
                                    strict_undefined=True) 
#                                    module_directory='/tmp/mako_modules')
                template_dict[root] = template
        return template_dict

    ##############################################################


    def slurp_walk(self, src_root = None):
        """ walk the content source dir tree,
        and process every dir found with a .txt content file"""

        if src_root is None:
            src_root = self.src_root

        # walk the directory tree.
        for path, subdirs, files in os.walk(src_root, 
                                            followlinks=True, 
                                            topdown=True):
            
            # if there is a .txt file, it's a content file. Get the 
            # lexicographic first one

            src_path = self.goodpath(path)
            content_file_count = 0

            files.sort()

            for cf in files:
                root, ext = os.path.splitext(cf)
                if ext == self.gdict['content_ext']:
                    self.add_page(path, cf, subdirs, files)
                    content_file_count += 1

            if content_file_count == 0:
                # OK to have subdirs of crap, just make sure that's OK
                logging.warning("no content file found in {}".format(src_path))

            if content_file_count > 1:
                # May be OK but warn anyway
                logging.warning("multiple content files found in {}".format(src_path))



    def add_page(self, path, cf, subdirs, files):
        """ Found a dir with a content file. Make a PageUnit,
        process lightly and add to the page structures. """

        punit = PageUnit(path, self.gdict)
        if punit.num < 0: # if no number in the directory, then don't add
            logging.warning("Skipping un-numbered path {}".format(path))
            return

        logging.info("New page found at at {0}".format(path))
        
        # content file: read content from this txt file
        punit.content_file = os.path.join(path,cf)  

        punit.subdirs = subdirs # subdirs of this directory

        punit.sort_subdirs()

        punit.files = files     # files in this dir
        
        # add to array and dict so we can find them again
        self.pages.append(punit)
        self.page_dict[punit.html_path] = punit


    def munge_loop(self):
        """ walk through all pages and populate with parents, children
        do additional processing (collect tags, etc.)"""
        self.level1 = [] # for blogs, this is the blog year
        self.level2 = [] # for blogs, this is the blog year
        self.tags = {} # dict of list of tags, keyed by tag
        for punit in self.pages:
            punit.populate(self.template_dict, self.page_dict)

        for punit in self.pages:
            if punit.level == 1:
                self.level1.append(punit)
            if punit.level == 2:
                self.level2.append(punit)
            for tag in punit.tags:
                if tag in self.tags:
                    self.tags[tag].append(punit)
                else:
                    self.tags[tag] = [punit]

        self.level1.sort()
        self.level2.sort()

        #print(" ".join(p.html_path for p in self.level1))

        # sort tags (topics) alphabetically
        stags = sorted(self.tags.items())

        self.tags = dict(stags)

        for t, val in self.tags.items():
            val.sort()
            #print("tag {} has pages: ".format(t))
            #for v in val:
            #    print('    page: {}'.format(v.html_path))
        self.make_tag_pages()
        self.make_top_page()

    def make_tag_pages(self):
        # make a virtual page for each tag, with links to the tagged pages
        from urllib import parse
        for t, val in self.tags.items():
            val.sort()
            slug = parse.quote_plus(t)
            tag_dest =  os.path.join(self.gdict['dest_root'],'tags')
            tag_path =  os.path.join(self.gdict['html_root'],'tags')
            punit = PageUnit(tag_path, self.gdict)
            punit.slug = slug
            punit.fname = "{}.html".format(slug)
            punit.tagname = t
            punit.html_path = tag_path
            punit.dest_path = tag_dest
            #punit.ldict['dest_path'] = tag_path
            punit.ldict['html_path'] = tag_path
            punit.ldict['page_path'] = tag_path
            punit.ldict['tagname'] = t
            punit.ldict['children'] = val
            self.tag_pages.append(punit)
            self.tag_dict[t] = punit

    def make_top_page(self):
        # make a virtual page for each tag, with links to the tagged pages
        self.top_page = None
        if 'top' in self.template_dict:
            self.top_page = PageUnit(self.gdict['html_top'], self.gdict)
            self.top_page.ldict['children'] = self.level1
            self.top_page.template = self.template_dict['top']

    ##############################################################
    def dump_loop(self):
        """ loop through list of pages and figure out pathname & children """

        for punit in self.pages:
            punit.ldict['tag_dict'] = self.tag_dict
            punit.ldict['level1'] = self.level1
            punit.ldict['level2'] = self.level2
            punit.render(self.template_dict, self.page_dict)
            if len(punit.modified) > 0:
                self.updated.extend(punit.modified)
                for t in punit.tags:
                    self.updated_tags[t] = True

        for punit in self.tag_pages:
            #punit.ldict['tags'] = self.tags
            punit.ldict['tag_dict'] = self.tag_dict
            punit.ldict['level1'] = self.level1
            punit.ldict['level2'] = self.level2
            punit.template = self.template_dict['tags']
            if self.gdict['incremental']:
                t = punit.tagname
                if t in self.updated_tags.keys():
                    punit.render(self.template_dict, self.page_dict)
                    self.updated.append(punit.dest_file)
                    logging.info("incrementally updated {}".format(punit.dest_file))
            else:
                punit.render(self.template_dict, self.page_dict)

            #punit.print_my_paths()


        if self.top_page is not None:
            self.top_page.ldict['tag_dict'] = self.tag_dict
            self.top_page.ldict['level1'] = self.level1
            self.top_page.ldict['level2'] = self.level2
            self.top_page.render(self.template_dict, self.page_dict)


    def generate_rss(self):
        # generate rss file header
        header_temp = self.template_dict['feed_header']
   
        rss_xml = header_temp.render(**self.gdict)

        #generate an entry for each page
        entry_temp = self.template_dict['feed_entry']
        for punit in self.pages:
            rss_xml += entry_temp.render(**punit.ldict)

        # terminate xml
        rss_xml += "</feed>\n"

        #print(rss_xml)

        rss_path = os.path.join(self.gdict['dest_root'], 
                                self.gdict['rss_file'])
                                 
        with open(rss_path, "w", encoding='utf-8') as rss_file:
            rss_file.write(rss_xml)
        logging.info("wrote rss file {}".format(rss_path))
           

    def generate_upload_script(self):

        for u in self.updated:
            print("updated {}".format(u))


if __name__ == '__main__':
    pass
