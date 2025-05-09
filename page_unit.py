# In page_unit.py

import os
import sys
import codecs
import markdown
import glob # Keeping glob for now, but internal logic now uses os.listdir
import shutil
import logging
from pathlib import Path # Keeping pathlib import for consistency, though not heavily used
from mako.template import Template
from mako import exceptions # Added for Mako exception handling
from urllib.parse import urljoin


class PageUnit(object):
    """
    Holds all the information and methods needed to generate a single page
    in the static website.
    """
    # Add 'is_virtual' parameter to the constructor, defaulting to False
    def __init__(self, src_path, global_dict=None, is_virtual=False):
        """
        Initializes a PageUnit instance.

        Args:
            src_path (str): The absolute file system path to the source directory
                            containing the content file for this page.
            global_dict (dict): The global configuration dictionary for the site.
            is_virtual (bool): True if this PageUnit represents a virtual page
                               (e.g., tag page, top page) that doesn't have a
                               physical source directory for media copying.
        """
        self.gdict = global_dict
        self.is_virtual = is_virtual # Store the flag for later checks
        
        # this is the content source absolute path
        self.src_path =  os.path.abspath(src_path)

        # this is the content source relative path to src_root
        self.rel_path = os.path.relpath(self.src_path, self.gdict['src_root']) 

        num, slug = self.num_slug(self.src_path) # Corrected to use self.src_path for num_slug
        self.num = num      # number (sort) in this dir
        self.slug = slug    # clean directory name

        # calculate relative html path -- this is key
        self.html_rel_path = self.get_html_path(self.rel_path)
        
        # filesystem path of destination directory for this page's HTML and assets
        self.dest_path = os.path.join(self.gdict['dest_root'], 
                                      self.html_rel_path)
        
        # HTML path for use in links (ensure trailing slash for directories)
        self.html_path = os.path.join(self.gdict['html_root'], 
                                      self.html_rel_path)
        if not self.html_path.endswith('/'):
            self.html_path += '/'
        

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
        # file paths are in html relative path format (corrected to absolute filesystem paths in render)
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
            n, slug = self.num_slug(d) # Call num_slug correctly
            num.append(int(n))
        
        sort_order = sorted((e,i) for i,e in enumerate(num))
        if reverse:
            sort_order.reverse()
        sorted_subdirs = [self.subdirs[i[1]] for i in sort_order]

        self.subdirs = sorted_subdirs

    def print_my_paths(self):
        logging.debug("-------src_path: {}".format(self.src_path))
        logging.debug("-------rel_path: {}".format(self.rel_path))
        logging.debug("------html_path: {}".format(self.html_path))
        logging.debug("------dest_path: {}".format(self.dest_path))
        logging.debug("------dest_file: {}".format(self.dest_file if hasattr(self, 'dest_file') else 'Not set yet'))


    def get_html_path(self, rel_path):
        # remove numbering from source path for clean destination path
        # return list of parents for breadcrumbs
        #logging.debug("orig path: {}".format(rel_path)) # Changed print to logging.debug
        
        rel_html_path = ""
        dirnames = rel_path.split(os.sep)
        for d in dirnames:
            # The intention here is to remove numbers like "1.slug" -> "slug".
            # Let's use a more direct approach for splitting the directory name.
            if '.' in d:
                parts = d.split('.', 1)
                try:
                    int(parts[0]) # Check if it starts with a number
                    slug = parts[1]
                except ValueError:
                    slug = d # Not a numbered directory
            else:
                slug = d # Not a numbered directory
            rel_html_path = os.path.join(rel_html_path, slug)
        return rel_html_path


    def get_abs_html_path(self, path, abs_root=None):
        # This method was unused. It's kept for now but could be removed.
        if abs_root is None:
            abs_root = self.gdict['html_root']

        if len(path) < 1 :
            return abs_root

        #logging.debug("path {}, abs_root {}".format(path, abs_root))    # Changed print to logging.debug

        rel_html_path = os.path.relpath(path, abs_root)
        abs_html_path = os.path.join(self.gdict['html_root'], rel_html_path) 
        return abs_html_path

    def num_slug(self, pathname):
        # extract the index number of this pathname, e.g
        # 1.foo/2.bar/3.baz/haha.txt returns 3 (integer)
        # and the slug "baz"
        path = os.path.normpath(pathname)
        base = os.path.basename(path) # Operate on the base name of the path
        
        splits = base.split('.', 1) # Split only on the first dot

        num = -1
        slug = base # Default slug is the whole base name

        if len(splits) > 1:
            try:
                num = int(splits[0]) # Try to convert the first part to an integer
                slug = splits[1]     # The second part is the slug
            except ValueError:
                # If the first part is not an integer, treat the whole thing as a slug
                num = -1
                slug = base
        # If len(splits) is 1, there's no dot, so num is -1 and slug is base, which is correct.

        return num, slug


    def parse_content_file(self, file_path):
        """ read a content file, parse header info and content markdown, return
        all in a dict"""

        header_dict = {'content_raw':'', 'template':'default'}
        if file_path == None:
            logging.warning("No content file path provided to parse_content_file.") # Changed print to logging.warning
            return header_dict

        # test if file exists
        if not os.path.exists(file_path):
            logging.warning("No content file found in {}".format(file_path)) # Changed print to logging.warning
            return header_dict

        try:
            input_file = codecs.open(file_path, mode="r", encoding="utf-8")
            lines = []
            for line in input_file:
                # use hash as comment
                stripped_line = line.strip() # Strip line for comment check and later parsing
                if stripped_line.startswith('#'): # Use .startswith for more robust comment check
                    continue # Skip comment lines
                lines.append(stripped_line) # Store stripped lines
            input_file.close()    

            # parse text file until we hit "content:" -- the rest is markdown
            # header lines have first words ending in ':'
            for i, line in enumerate(lines):
                words = line.split(None, 1) # Split only on first whitespace, at most once.
                if len(words) > 0:
                    # Check if the first word ends with ':' indicating a header key.
                    # Use .endswith(':') for robustness
                    if words[0].endswith(':'):
                        key = words[0].rstrip(':') # Remove trailing colon
                        if key == 'content':
                            header_dict['content_raw'] = '\n'.join(lines[i+1:])
                            return header_dict
                        # Store header key-value pair. Strip whitespace from value.
                        header_dict[key] = words[1].strip() if len(words) > 1 else '' # Ensure value is stripped
        except Exception as e:
            logging.error("ERROR parsing content file {}: {}".format(file_path, e)) # Changed print to logging.error and added exception info
            raise e
        return header_dict


    def write_html_file_u(self, html_path, html):
        """ Write rendered unicode as UTF-8 to the given path (Deprecated: Use write_html_file)"""
        #logging.info("writing content file {}".format(html_path)) # Changed print to logging.info
        hfile = codecs.open(html_path, "w", "utf-8")
        hfile.write(html)
        hfile.close()
        logging.warning("Using deprecated write_html_file_u. Please use write_html_file.") # Add warning for deprecated method

    def write_html_file(self, html_path, html):
        """ Write rendered unicode as UTF-8 to the given path"""
        logging.info("Writing HTML file: {}".format(html_path)) # Changed to logging.info
        os.makedirs(os.path.dirname(html_path), exist_ok=True) # Ensure directory exists
        try:
            with open(html_path, "w", encoding='utf-8') as hfile:
                hfile.write(html)
        except UnicodeEncodeError as e:
            logging.error("Error rendering content file {}: {}".format(html_path, e)) # Changed print to logging.error
            logging.error("Ensure all content is valid UTF-8.") # Added helpful message
            raise # Re-raise for debugging
        except Exception as e:
            logging.error("An unexpected error occurred while writing file {}: {}".format(html_path, e))
            raise
                
    #########################################################


    def populate(self, template_dict, page_dict):
        """ add links to parents, children"""
        logging.debug("populating page: {}".format(self.html_path)) # Changed print to logging.debug
        self.ldict['html_path']  = self.html_path

        # make child paths so we can look them up in dictionary
        self.child_slugs = []
        self.children = []
        for child in self.subdirs:
            num, slug = self.num_slug(child) # Call num_slug correctly
            if num  > 0: # Check if directory is numbered
                self.child_slugs.append(slug)

        for slug in self.child_slugs:
            child_html_path = os.path.join(self.html_path, slug)
            if not child_html_path.endswith('/'): # Ensure trailing slash for directory URLs
                child_html_path += '/'
            try:
                self.children.append(page_dict[child_html_path])
            except KeyError:
                logging.debug(f"Could not find child {child_html_path} for {self.html_path}. (This might be expected if it's a non-content directory)") # Changed logging level to debug
            except Exception as e:
                logging.error(f"Unexpected error while finding child {child_html_path} for {self.html_path}: {e}") # Changed print to logging.error
 
        # make parent paths for breadcrumb navigation:
        self.parent_slugs = self.html_rel_path.split(os.sep)
        self.parents = []

        parent_html_path = self.gdict['html_root']
        if not parent_html_path.endswith('/'): # Ensure root path has trailing slash
            parent_html_path += '/'
            
        for slug in self.parent_slugs:
            if not slug: # Skip empty strings from split if path starts with '/'
                continue

            parent_html_path = urljoin(parent_html_path,slug + '/') # Use urljoin for robust URL concatenation, add trailing slash
            try:
                if parent_html_path in page_dict: # Check if it's a registered page unit
                    self.parents.append(page_dict[parent_html_path])
                # else: logging.debug(f"Parent HTML path {parent_html_path} is not a registered PageUnit.")
            except KeyError:
                logging.error("Could not find parent {}. This might indicate an issue in content parsing or path normalization.".format(parent_html_path)) # Changed print to logging.error
            except Exception as e:
                logging.error(f"Unexpected error while finding parent {parent_html_path}: {e}")

        self.level = len(self.parents)
        #logging.debug("Level of this page is: {} for {}".format(self.level, self.html_path)) # Changed print to logging.debug


        # find thumbnail if it exists:
        self.thumbnail = ""
        for f in self.files:
            root, ext = os.path.splitext(f)
            if root.lower() == 'thumb': # Case-insensitive check for 'thumb'
                self.thumbnail = f
                break # Found it, no need to check further
        if self.thumbnail == "" and self.gdict.get('warn_thumbnail', False): # Use .get for warn_thumbnail
            logging.warning("WARNING: could not find thumb.* in {}".format(self.src_path))

        self.ldict['keywords'] = 'no keywords found' # Default keywords

        # Parse content file and get dict of attributes from header
        hdict = self.parse_content_file( self.content_file)

        # Update ldict with values from the content file header
        self.ldict.update(hdict) # This was originally after permalink, moved it up to populate ldict first

        # set up the right template
        if self.ldict.get('template', 'default') == 'default': # Use ldict.get for template
            if len(self.children) > 0:
                self.template_name = 'gallery'
            else:
                self.template_name = 'leaf'
        else:
            self.template_name = self.ldict['template'] # Use ldict for template name

        # extract tags
        self.tags = [] # Ensure tags list is reset
        if 'tags' in self.ldict and self.ldict['tags']: # Check if tags exists and is not empty
            # Assuming tags are comma-separated, ensure they are stripped
            self.tags = [t.strip() for t in self.ldict['tags'].split(',') if t.strip()]
        
        # convert tag to list if a single string (redundant if previous logic is used but safe)
        if isinstance(self.tags, str): # This check is likely redundant if previous logic works.
            self.tags = [self.tags]
            
        #if len(self.tags) > 0:
        #    logging.warning("tags for {}: ".format(self.html_path)  + ";".join(self.tags)) # Example logging, commented out for now

        try:
            self.template = template_dict[self.template_name]
            # --- New Debugging Code for Template (Conditional) ---
            if self.gdict.get('debug_templates'):
                template_hierarchy_names = []
                current_template_node = self.template
                
                # Attempt to traverse the hierarchy using .parent attribute
                # Add a try-except for AttributeError if .parent is not available (for older Mako versions)
                try:
                    while current_template_node:
                        template_hierarchy_names.append(os.path.basename(current_template_node.filename))
                        current_template_node = current_template_node.parent # Use .parent
                except AttributeError:
                    # If .parent is not found, log a warning about Mako version and stop traversal
                    #logging.warning(f"Mako Template object does not have a 'parent' attribute. Cannot trace full template hierarchy for '{self.html_path}'. Please consider updating Mako if available.")
                    # Ensure at least the base template is logged if the loop breaks prematurely
                    if not template_hierarchy_names:
                        template_hierarchy_names.append(os.path.basename(self.template.filename))
                    current_template_node = None # Stop the loop

                logging.debug(f"Template resolved for '{self.html_path}': {' -> '.join(template_hierarchy_names)}")
            # --- End New Debugging Code ---

        except KeyError:
            logging.warning('WARNING: template "{}" not found, using leaf.'.format(self.template_name)) # Changed logging.warning
            self.template = template_dict.get('leaf')
            if self.template is None:
                logging.critical("CRITICAL: 'leaf' template is also missing. Cannot render page. Exiting.") # Critical exit
                sys.exit(1) # Exit on critical error

        info_str = 'generating {}'.format(self.html_path)
        info_str += ' using "{}" template'.format(self.template_name)
        logging.info(info_str) # Changed logging.info

        # Construct the permalink for the page (use urljoin for robustness)
        self.permalink = urljoin(f"http://{self.gdict['hostname']}", self.html_path.lstrip('/'))
        
        self.ldict['permalink'] = self.permalink 
        self.ldict['children'] = self.children
        self.ldict['parents'] = self.parents
        self.ldict['tags'] = self.tags
        self.ldict['level'] = len(self.parents) # Changed to use len(self.parents) directly, consistent with self.level
        self.title = self.ldict['title'] # Ensure the title from ldict is used here


        try:
            # This line converts Markdown to HTML. This is the correct place for it.
            self.ldict['content_html'] = markdown.markdown(self.ldict['content_raw'], # Use self.ldict['content_raw']
                                                           extensions=['extra'])
        except Exception as e:
            logging.error("ERROR parsing markdown in {}: {}".format(self.content_file, e)) # Changed logging.error
            raise e


    #########################################################


    def render(self, template_dict, page_dict):
        self.dest_file = os.path.join(self.dest_path,self.fname)
        dest_file = self.dest_file
        src_file = self.content_file

        # Check for incremental build conditions.
        # Using self.gdict['incremental'] as the main switch.
        if self.gdict.get('incremental', False) and os.path.isfile(dest_file) and src_file is not None:
            if os.path.getmtime(src_file) <= os.path.getmtime(dest_file): # Using getmtime for modification time
                logging.debug(f"Skipping stale page (incremental build): {dest_file}")
                return # Exit if no update needed
            else:
                logging.info(f"Content file modified, re-rendering: {src_file}")
        elif self.gdict.get('incremental', False) and not os.path.isfile(dest_file):
            logging.info(f"Destination file not found for incremental build: {dest_file}, rendering.")
            
        # make a leaf directory
        self.check_or_create_dir(self.dest_path)

        # --- CRITICAL FIX: Removed intermediate Mako rendering of content_html ---
        # The self.ldict['content_html'] is already the HTML output from Markdown.
        # Rendering it again as a Mako template here caused content to disappear or be escaped.
        # It should be directly available for the main page template.
        # Original problematic lines (removed):
        # pagetemplate = Template(self.ldict['content_html'])
        # cooked_html = pagetemplate.render(**self.ldict)
        # self.ldict['content_html'] = cooked_html
        # --- End CRITICAL FIX ---

        # copy files (media)
        # --- Conditional Media Copying for Virtual Pages ---
        if not self.is_virtual and os.path.isdir(self.src_path):
            images, js = self.copy_media(self.src_path, self.dest_path)
            self.ldict['images'] = images
            self.ldict['js_files'] = js # Changed 'js' to 'js_files' for consistency with global_dict
        else:
            # For virtual pages or cases where src_path isn't a directory
            self.ldict['images'] = [] # Ensure these are always defined for templates
            self.ldict['js_files'] = [] # Ensure these are always defined for templates
            if not self.is_virtual: # Only warn if it was expected to be a physical directory
                logging.warning(f"Skipping media copy for '{self.html_path}': Source directory does not exist or is not a directory: {self.src_path}. (This is expected for virtual pages.)")


        # render template with all variables
        # --- New Debugging Code before Final Render (Conditional) ---
        if self.gdict.get('debug_templates'):
            logging.debug(f"Final rendering of page '{self.html_path}' using template '{os.path.basename(self.template.filename)}'.")
        # --- End New Debugging Code ---
        try:
            self.html = self.template.render(**self.ldict)
        except exceptions.TemplateRuntimeError as e: # Catch specific Mako runtime errors
            logging.error(f"Error rendering main template '{self.template_name}' for page '{self.html_path}': {e}")
            raise e
        except NameError as e:
            if self.tagname is not None:
                logging.error("template subs in {}: {}".format(self.tagname, e)) # Changed print to logging.error
            if self.content_file is not None:
                logging.error("template subs in {}: {}".format(self.content_file, e)) # Changed print to logging.error
            raise e
        except Exception as e: # Catch any other general exceptions
            logging.error(f"An unexpected error occurred during template rendering for '{self.html_path}': {e}")
            raise

        self.modified.append(dest_file)
        self.write_html_file(dest_file, self.html)

    def copy_if_newer(self, src, dest_dir): # Renamed 'dest' to 'dest_dir' for clarity
        dest_file_path = os.path.join(dest_dir, os.path.basename(src)) # Build full destination file path

        # if destination exists:
        if os.path.isfile(dest_file_path):
            if os.path.getmtime(src) > os.path.getmtime(dest_file_path): # Use getmtime for modification time
                logging.debug(f"Copying (newer source): {src} to {dest_file_path}") # Changed print to logging.debug
                shutil.copy2(src,dest_file_path) # Use copy2 to preserve metadata
                self.modified.append(dest_file_path)
            else:
                logging.debug(f"Skipping (destination is newer or same): {dest_file_path}") # Changed print to logging.debug
        else: 
            logging.debug(f"Copying (destination not found): {src} to {dest_file_path}") # Changed print to logging.debug
            shutil.copy2(src,dest_file_path) # Use copy2 to preserve metadata
            self.modified.append(dest_file_path)

    def copy_media(self, src_path, html_path):
        # make a copy of images, etc in local path
        logging.debug("Copy media from  {}  to {}".format(src_path, html_path)) # Changed print to logging.debug
        images = []
        js_files = [] # Renamed 'js' to 'js_files' for consistency

        # Define allowed media extensions
        all_media_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', # Image formats
            '.mp3', '.mp4', # Audio/Video
            '.html', '.pdf', '.FCStd', '.css', '.py' # Other documents/assets
        ]
        js_like_extensions = ['.js', '.pde', '.class'] # JavaScript-like extensions

        os.makedirs(html_path, exist_ok=True) # Ensure directory exists

        # Iterate through all files in the source directory
        # Use os.path.exists and os.path.isdir to prevent FileNotFoundError if src_path is not a real directory
        if not os.path.exists(src_path) or not os.path.isdir(src_path):
            logging.warning(f"Media source directory does not exist or is not a directory: {src_path}. Skipping media copy.")
            return images, js_files

        for f_name in os.listdir(src_path):
            full_src_path = os.path.join(src_path, f_name)
            if os.path.isfile(full_src_path): # Ensure it's a file, not a directory
                root, ext = os.path.splitext(f_name)
                
                # Convert extension to lowercase for case-insensitive comparison
                ext_lower = ext.lower()

                # Check if it's a general media file
                if ext_lower in [e.lower() for e in all_media_extensions]:
                    # Exclude 'thumb.*' files from the general images list, as they are handled separately
                    if root.lower() != 'thumb':
                        if ext_lower in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']: # Classify as image for 'images' list
                            images.append(f_name)
                    self.copy_if_newer(full_src_path, html_path)

                # Check if it's a JavaScript-like file (and not already handled as general media if extension overlaps)
                if ext_lower in [e.lower() for e in js_like_extensions]:
                    js_files.append(f_name) # Add to js_files list
                    self.copy_if_newer(full_src_path, html_path) # Copy the file

        return images, js_files

    def check_or_create_dir(self, path):
        "Create the directory if it does not exist"
        if not os.path.isdir(path):
            logging.debug(f"Creating directory: {path}") # Changed print to logging.debug
            os.makedirs(path)

if __name__ == '__main__':
    logging.info("This module is part of a larger static site generator and should be run via builder.py.") # Changed print to logging.info
