import os
import logging
from datetime import datetime as dt
from mako.template import Template
from mako.lookup import TemplateLookup
from mako import exceptions # For Mako template exceptions, useful for debugging rendering issues.
import sys # Added for sys.exit for clean exits on critical errors.

from page_unit import PageUnit # Imports the PageUnit class for managing individual pages.


class ContentTree(object):
    """
    Manages the entire content structure of the static site.
    It walks the source directory, processes content files, builds page relationships,
    and orchestrates the rendering of all HTML pages and the RSS feed.
    """
    def __init__(self, global_dict):
        """
        Initializes the ContentTree with global configuration settings.

        Args:
            global_dict (dict): A dictionary containing site-wide configuration
                                settings (e.g., source/destination roots, template directory).
        """
        self.gdict = global_dict
        self.src_root = global_dict['src_root']
        self.dest_root = global_dict['dest_root']

        self.pages = []       # List of all PageUnit objects found.
        self.page_dict = {}   # Dictionary of PageUnit objects, keyed by their HTML URI (path).

        self.tag_pages = []   # List of virtual PageUnit objects created for tags.
        self.tag_dict = {}    # Dictionary mapping tag names to their virtual PageUnit objects.

        # List to keep track of paths to files that have been modified/generated
        # during the current build, primarily for potential upload scripts.
        self.updated = []
        # Dictionary to track which tags have had associated pages updated,
        # for incremental tag page regeneration.
        self.updated_tags = {}

        # Preload templates from the specified directory.
        self.template_dict = self.load_templates()
        if not self.template_dict: # Check if template_dict is empty
            logging.critical("No templates found. Please check 'template_dir' in your config file. Exiting.")
            sys.exit(1) # Exit cleanly if no templates are found.
        for key in self.template_dict:
            logging.info(f'Found template: "{key}"')


    # NOTE: The 'goodpath' method is defined but not currently used anywhere in the class.
    # It appears to be an artifact or intended for future use.
    def goodpath(self, path):
        """
        (UNUSED) Returns a normalized relative path to the source root.
        This function's purpose is not clear in the current implementation as
        PageUnit handles its own path calculations.
        """
        if os.sep != '/':
            path = '/'.join(path.split(os.sep)) # Convert OS-specific path separators to forward slashes.
        abs_path =  os.path.abspath(path) # Get absolute path.
        src_path = os.path.relpath(path, self.gdict['src_root']) # Get path relative to source root.
        return src_path # Return the relative path (though the function always returns None in current state)

    def load_templates(self, gdict=None):
        """
        Loads Mako HTML and XML templates from the configured template directory.

        Args:
            gdict (dict, optional): Global dictionary to use. Defaults to self.gdict.

        Returns:
            dict: A dictionary where keys are template names (filename without extension)
                  and values are compiled Mako Template objects.
        """
        if gdict is None:
            gdict = self.gdict

        template_dir = os.path.abspath(self.gdict['template_dir'])
        mylookup = TemplateLookup(directories=[template_dir]) # Mako lookup for includes.
        logging.info(f"Looking for templates in: {template_dir}")

        template_dict = {}
        if not os.path.isdir(template_dir):
            logging.error(f"Template directory not found: {template_dir}")
            return template_dict

        files = os.listdir(template_dir)
        for f in files:
            # Only process .html or .xml files as templates.
            root, ext = os.path.splitext(f)
            if ext in ('.html', '.xml'):
                uri = os.path.join(template_dir, f) # Full path to the template file.
                try:
                    # Compile the Mako template.
                    # strict_undefined=True raises errors for undefined variables, which is good for debugging.
                    # module_directory='/tmp/mako_modules' specifies where compiled template modules are cached.
                    template = Template(filename=uri,
                                        lookup=mylookup,
                                        strict_undefined=True)
#                                       module_directory='/tmp/mako_modules') # This line was commented out.
                    template_dict[root] = template
                except exceptions.TemplateLookupException as e:
                    logging.error(f"Error loading template '{f}': {e}")
                except Exception as e:
                    logging.error(f"An unexpected error occurred while loading template '{f}': {e}")
                    # print(exceptions.html_error_template().render()) # Mako's error rendering, useful for direct debugging.
        return template_dict

    ##############################################################

    def slurp_walk(self, src_root=None):
        """
        Walks the content source directory tree, identifying content directories
        and creating `PageUnit` objects for each.
        A directory is considered a content unit if it contains a file with the
        configured `content_ext` (e.g., '.md').
        """
        if src_root is None:
            src_root = self.src_root

        # os.walk generates (dirpath, dirnames, filenames) for each directory.
        # topdown=True processes directories before their files/subdirectories.
        # followlinks=True allows traversing symbolic links.
        for path, subdirs, files in os.walk(src_root,
                                            followlinks=True,
                                            topdown=True):

            content_file_count = 0
            files.sort() # Sort files alphabetically for consistent processing.

            for cf in files:
                _root, ext = os.path.splitext(cf) # _root is unused but required for splitext.
                # Check if the file is a content file based on extension.
                if ext == self.gdict['content_ext']:
                    self.add_page(path, cf, subdirs, files)
                    content_file_count += 1

            if content_file_count == 0:
                # It's OK for directories to not have content files, but if it's
                # within the content tree, it might be an oversight.
                # Using relpath for cleaner log output.
                relative_path = os.path.relpath(path, self.src_root)
                logging.warning(f"No content file ({self.gdict['content_ext']}) found in: {relative_path}")

            if content_file_count > 1:
                # Multiple content files in one directory can lead to ambiguity.
                relative_path = os.path.relpath(path, self.src_root)
                logging.warning(f"Multiple content files found in: {relative_path}. Using the first one found in sorted order.")


    def add_page(self, path, cf, subdirs, files):
        """
        Creates a `PageUnit` object for a found content directory and adds it
        to the internal lists (`self.pages`, `self.page_dict`).

        Args:
            path (str): The absolute path to the content directory.
            cf (str): The filename of the content file within that directory.
            subdirs (list): List of subdirectory names in `path`.
            files (list): List of filenames in `path`.
        """
        punit = PageUnit(path, self.gdict)
        if punit.num < 0: # If the directory name doesn't start with a number (e.g., '0.slug'), skip it.
            logging.debug(f"Skipping un-numbered path: {path}") # Changed to debug as this might be intentional for auxiliary dirs.
            return

        logging.info(f"Discovered new page at: {punit.src_path}")

        # Assign the full path to the content file.
        punit.content_file = os.path.join(path, cf)

        punit.subdirs = subdirs # Store immediate subdirectories.

        punit.sort_subdirs() # Sort subdirectories by their numeric prefix.

        punit.files = files     # Store files in this directory.

        # Add the PageUnit to the main list and dictionary for easy lookup by HTML path.
        self.pages.append(punit)
        self.page_dict[punit.html_path] = punit


    def munge_loop(self):
        """
        Second pass over all `PageUnit` objects to establish relationships,
        collect tags, and prepare data for rendering.
        """
        self.level1 = [] # List to hold PageUnit objects at level 1 (e.g., blog years).
        self.level2 = [] # List to hold PageUnit objects at level 2 (e.g., blog months).
        self.tags = {}   # Dictionary to store lists of PageUnit objects, keyed by tag name.

        # First iteration: Populate basic relationships and parse content file headers.
        for punit in self.pages:
            # `populate` fills in parents, children, parses content file, determines template.
            punit.populate(self.template_dict, self.page_dict)

        # Second iteration: Categorize pages by level and collect tags.
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

        self.level1.sort() # Sort level 1 pages (e.g., by year).
        self.level2.sort() # Sort level 2 pages (e.g., by month).

        # Sort tags (topics) alphabetically by their keys.
        # This ensures consistent order when generating tag lists.
        stags = sorted(self.tags.items())
        self.tags = dict(stags)

        # For each tag, sort the list of associated pages.
        for t, val in self.tags.items():
            val.sort() # Sort pages within each tag alphabetically by HTML path.
            # Example debug output:
            # logging.debug(f"Tag '{t}' has pages:")
            # for v in val:
            #     logging.debug(f"    - {v.html_path}")

        # Create virtual pages for each tag and the top-level page.
        self.make_tag_pages()
        self.make_top_page()

    def _get_sortable_date_or_log_error(self, page_unit):
        """
        Attempts to parse the page's date using the expected '%Y-%m-%d' format.
        If parsing fails (ValueError), logs an error with the content file name
        and returns a default date for sorting to allow the process to continue.
        """
        date_string = page_unit.ldict.get('date')
        # Prepare file info for logging. Use content_file for the actual source file.
        file_info_for_log = f" in file: {os.path.relpath(page_unit.content_file, self.src_root)}" if page_unit and page_unit.content_file else f" for virtual page: {page_unit.html_path}"

        # Ensure date_string is stripped of any leading/trailing whitespace
        # that might interfere with strict parsing.
        if date_string:
            date_string = date_string.strip()
        else:
            # If date_string is None or empty after strip, use default and warn
            logging.warning(f"Empty date string found for page '{page_unit.html_path}'{file_info_for_log}. Using default date (1970-01-01) for sorting.")
            # Return a parsed default date to ensure consistent sorting behavior
            return dt.strptime('1970-01-01', '%Y-%m-%d') # Default date format changed to match.

        try:
            # Attempt to parse with the new, strict format '%Y-%m-%d'
            parsed_date = dt.strptime(date_string, '%Y-%m-%d')
            return parsed_date
        except ValueError as e:
            # Log the error with the specific date string and the content file
            logging.error(f"Date format error for page '{page_unit.html_path}'{file_info_for_log}: "
                          f"Could not parse date '{date_string}' with expected format '%Y-%m-%d'. Error: {e}") # Log message updated
            # Return a default date to allow sorting to continue,
            # so that one problematic page doesn't halt the entire RSS generation.
            return dt.strptime('1970-01-01', '%Y-%m-%d') # Default date format changed to match.


    def make_tag_pages(self):
        """
        Creates a virtual `PageUnit` for each unique tag found.
        These virtual pages will serve as index pages for all content
        associated with that tag.
        """
        from urllib.parse import quote_plus # Used for URL-encoding tag slugs.

        for t, val in self.tags.items():
            val.sort() # Ensure pages are sorted for consistency on tag pages.
            slug = quote_plus(t) # URL-encode the tag name to create a clean slug.

            # Construct destination paths for the tag page.
            tag_dest = os.path.join(self.gdict['dest_root'], 'tags') # Filesystem path.
            tag_html_base_path = os.path.join(self.gdict['html_root'], 'tags') # HTML path for the 'tags' directory.

            punit = PageUnit(os.path.join(self.gdict['src_root'], 'tags', slug), self.gdict) # Dummy src_path, as it's virtual.
            punit.slug = slug # Set the URL slug for the tag page.
            punit.fname = "index.html" # Tag pages are usually index.html within their slugged dir.
            punit.tagname = t # Store the original tag name.

            # Update local dictionary for the tag page's template rendering.
            punit.html_rel_path = os.path.join(os.path.relpath(tag_html_base_path, self.gdict['html_root']), slug) # e.g., tags/programming
            punit.html_path = os.path.join(tag_html_base_path, slug) # E.g., /blog/tags/programming/
            punit.dest_path = os.path.join(tag_dest, slug) # E.g., /path/to/www/blog/tags/programming/
            punit.dest_file = os.path.join(punit.dest_path, punit.fname) # E.g., /path/to/www/blog/tags/programming/index.html


            punit.ldict['html_path'] = punit.html_path # Path for use in template links.
            punit.ldict['page_path'] = punit.html_path # Alias for html_path.
            punit.ldict['tagname'] = t # Original tag name.
            punit.ldict['children'] = val # The list of pages associated with this tag.
            punit.ldict['title'] = f"Posts tagged with '{t}'" # Dynamic title for tag page.

            self.tag_pages.append(punit)
            self.tag_dict[t] = punit # Map tag name to its PageUnit.

    def make_top_page(self):
        """
        Creates a virtual `PageUnit` for the site's top-level page if a 'top' template exists.
        This page often serves as the main index or homepage.
        """
        self.top_page = None
        if 'top' in self.template_dict:
            logging.info("Creating virtual top-level page.")
            # The src_path for the top page is the html_top path within src_root (conceptually).
            # This is a bit of a hack, as `PageUnit` expects a file-system path, but for a virtual
            # page, it doesn't truly exist. We're passing it to make PageUnit constructor happy.
            dummy_src_path = os.path.join(self.gdict['src_root'], self.gdict['html_top'].strip('/'))
            self.top_page = PageUnit(dummy_src_path, self.gdict)

            # Configure specific properties for the top page.
            self.top_page.ldict['children'] = self.level1 # Top page's children are usually level 1 pages.
            self.top_page.template = self.template_dict['top']
            self.top_page.fname = 'index.html' # Top page is usually index.html.
            self.top_page.html_rel_path = "" # The top page has no relative path.
            self.top_page.html_path = self.gdict['html_top'] # Use configured HTML top for URL.
            self.top_page.dest_path = self.gdict['dest_root'] # Destination is the root build dir.
            self.top_page.dest_file = os.path.join(self.top_page.dest_path, self.top_page.fname)
            # The top page might have its own title set in config.
            self.top_page.ldict['title'] = self.gdict.get('blog_title', self.gdict.get('title', 'Homepage'))


    ##############################################################
    def dump_loop(self):
        """
        Third pass: Renders all content pages, tag pages, and the top page
        to their final HTML files.
        """
        # Sort tag_dict alphabetically by key for consistent output (e.g., tag cloud).
        self.tag_dict = dict(sorted(self.tag_dict.items(), key=lambda x: x[0].lower()))

        # Render each individual content page.
        for punit in self.pages:
            punit.ldict['tag_dict'] = self.tag_dict # Make tag dictionary available to all pages.
            punit.ldict['level1'] = self.level1     # Make level1 pages available.
            punit.ldict['level2'] = self.level2     # Make level2 pages available.
            punit.render(self.template_dict, self.page_dict) # Render the page.
            if len(punit.modified) > 0:
                self.updated.extend(punit.modified) # Collect paths of updated files.
                for t in punit.tags:
                    self.updated_tags[t] = True # Mark associated tags as updated.

        # Render virtual pages for each tag.
        for punit in self.tag_pages:
            punit.ldict['tag_dict'] = self.tag_dict # Make tag dictionary available.
            punit.ldict['level1'] = self.level1     # Make level1 pages available.
            punit.ldict['level2'] = self.level2     # Make level2 pages available.
            punit.template = self.template_dict['tags'] # Explicitly use 'tags' template.

            # Handle incremental rendering for tag pages.
            if self.gdict['incremental']:
                t = punit.tagname
                # Re-render tag page only if a page associated with this tag was updated.
                if t in self.updated_tags:
                    logging.info(f"Incrementally updating tag page: {punit.dest_file}")
                    punit.render(self.template_dict, self.page_dict)
                    self.updated.append(punit.dest_file) # Add tag page to updated list.
                else:
                    logging.debug(f"Skipping stale tag page (incremental build): {punit.dest_file}")
            else:
                # Full build: render all tag pages.
                punit.render(self.template_dict, self.page_dict)

            # punit.print_my_paths() # Debugging aid.


        # Render the site's top-level page if it exists.
        if self.top_page is not None:
            self.top_page.ldict['tag_dict'] = self.tag_dict
            self.top_page.ldict['level1'] = self.level1
            self.top_page.ldict['level2'] = self.level2
            # The top page is always rendered, as it often acts as an index for the site.
            self.top_page.render(self.template_dict, self.page_dict)
            # Add top_page's output to updated list if it was rendered.
            if len(self.top_page.modified) > 0:
                self.updated.extend(self.top_page.modified)


    def generate_rss(self):
        """
        Generates the RSS (Atom) feed for the site's content.
        It uses 'feed_header' and 'feed_entry' templates.
        """
        # Ensure 'feed_header' and 'feed_entry' templates exist.
        if 'feed_header' not in self.template_dict or 'feed_entry' not in self.template_dict:
            logging.error("Cannot generate RSS feed: 'feed_header.xml' or 'feed_entry.xml' templates not found.")
            return

        header_temp = self.template_dict['feed_header']

        # Render the RSS header using global dictionary values.
        rss_xml = header_temp.render(**self.gdict)

        # Generate an entry for each page.
        # For a blog, pages should be sorted by date, most recent first.
        # Ensure the 'date' key is present before sorting; fallback to a default date.
        # It's assumed content files have a 'date' in 'YYYY-MM-DD' format.
        sorted_pages_for_rss = sorted(
            self.pages,
            key=lambda p: self._get_sortable_date_or_log_error(p), # Pass the entire PageUnit 'p' here
            reverse=True
        )
        # Limit RSS feed to a reasonable number of entries (e.g., 10 or 20).
        max_rss_entries = 20
        entry_temp = self.template_dict['feed_entry']
        for punit in sorted_pages_for_rss[:max_rss_entries]:
            # Check if the page should be included in RSS (e.g., only blog posts, not galleries).
            # This requires a new config setting or page metadata. For now, all are included.
            # Pass the page's local dictionary to the entry template.
            try:
                rss_xml += entry_temp.render(**punit.ldict)
            except exceptions.TemplateRuntimeError as e:
                logging.error(f"Error rendering RSS entry for page {punit.html_path}: {e}")
                logging.error("Skipping this entry in RSS feed.")
                continue # Skip to next page if an error occurs.

        # Terminate the RSS XML.
        rss_xml += "</feed>\n"

        # Construct the full path for the RSS file.
        rss_path = os.path.join(self.gdict['dest_root'],
                                self.gdict['rss_file'])

        # Ensure the destination directory exists before writing.
        os.makedirs(os.path.dirname(rss_path), exist_ok=True)

        # Write the RSS XML to the file.
        with open(rss_path, "w", encoding='utf-8') as rss_file:
            rss_file.write(rss_xml)
        logging.info(f"Wrote RSS file: {rss_path}")


    def generate_upload_script(self):
        """
        (PLACEHOLDER) Generates a script (e.g., shell script) that can be used
        to upload only the modified/generated files to the remote host.
        Currently, this method is empty (`pass`).

        Example implementation:
        ```
        if self.updated:
            upload_script_path = os.path.join(self.gdict['dest_root'], 'upload_updated.sh')
            with open(upload_script_path, 'w') as f:
                f.write("#!/bin/bash\n\n")
                f.write("REMOTE_HOST=\"user@host\"\n")
                f.write(f"REMOTE_DEST_ROOT=\"{self.gdict['html_top'].rstrip('/')}\"\n\n") # Use html_top as remote root.
                f.write("echo \"Uploading updated files...\"\n\n")
                for fpath in self.updated:
                    # Calculate relative path from dest_root to upload to remote.
                    rel_fpath = os.path.relpath(fpath, self.gdict['dest_root'])
                    remote_dir = os.path.dirname(os.path.join("$REMOTE_DEST_ROOT", rel_fpath))
                    f.write(f"mkdir -p \"$REMOTE_HOST:$(dirname $REMOTE_DEST_ROOT/{rel_fpath})\"\n") # Create remote dir
                    f.write(f"scp -q \"{fpath}\" \"$REMOTE_HOST:$(dirname $REMOTE_DEST_ROOT/{rel_fpath})/{os.path.basename(fpath)}\"\n")
                f.write("\necho \"Upload complete.\"\n")
            os.chmod(upload_script_path, 0o755) # Make the script executable.
            logging.info(f"Generated upload script: {upload_script_path}")
        else:
            logging.info("No files updated, skipping upload script generation.")
        ```
        """
        pass


if __name__ == '__main__':
    # This block will only execute if content_tree.py is run directly,
    # which is typically not how this module is intended to be used.
    # It's primarily a class to be imported by builder.py.
    print("This module is part of a larger static site generator and should be run via builder.py.")
