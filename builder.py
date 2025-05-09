#!/home/jtf/anaconda3/bin/python

"""
builder.py: Static Website Generator

This script orchestrates the process of generating a static website from
Markdown content files and Mako templates. It is influenced by staceyapp.com.

Copyleft Jonathan Foote 2019
"""

""" TODO
Improvements for builder.py:

Configuration Loading (exec()):
Suggestion: Replace exec(args.config.read()) with a safer and more explicit method for loading Python configurations, such as importlib.util.module_from_spec. This makes the code more robust and secure by treating the config file as a module to be imported, rather than arbitrary executable code.
Error Handling:
Suggestion: The try-except block for config file parsing is good. Ensure sys.exit(1) is used for graceful termination on critical errors.
Logging Levels:
Suggestion: Consider encapsulating the global_dict within a Config class or a dedicated configuration object. This would allow for more structured access to configuration values and potentially make it easier to manage runtime modifications to the config (like adding update_time).
"""


import os
import sys
from datetime import datetime
import argparse
import logging
# color logging output to terminal
import Colorer # Custom module to add color to logging output

# local files:
from content_tree import ContentTree # Manages the site structure and rendering logic

# Default configuration settings. These are used if no external config file is provided.
DEFAULT_CONFIG = {
    # --- Directory and Path Configuration ---
    'src_root':  '/home/jtf/bitb/www/projects-source/content',
    'dest_root': '/home/jtf/bitb/www/new_www/build/',
    'public': '/new/build/public/', # Path for public assets like CSS
    'html_root': '/new/build/',     # Base HTML path for internal links
    'html_top': '/new/build/',      # HTML root for the top-level page

    # --- Templating Configuration ---
    'template_dir': 'templates',    # Relative or absolute path to the templates directory.
                                    # Note: If relative, it should be relative to the script's execution path.

    # --- Default Metadata (can be overridden by content file headers or blog_config.py) ---
    'date': '1970-1-1',
    'title': 'default_title',
    'name': 'Jonathan Foote',
    'hostname': 'localhost',
    'month': 'unset',               # Placeholder, likely populated during content processing.
    'day': 'unset',                 # Placeholder.
    'weekday': 'unset',             # Placeholder.
    'keywords': 'unset keywords'
}

if __name__ == '__main__':
    # Set up argument parsing for command-line options.
    parser = argparse.ArgumentParser(description='Static site generator.')
    parser.add_argument('--dry_run', '-d',
                        action='store_true',
                        help='do not generate output files')
    parser.add_argument('--verbose','-v',
                        action='store_true',
                        help='enable verbose logging output' )
    parser.add_argument('--incremental','-i',
                        action='store_true',
                        help='only render changed files' )
    parser.add_argument('config',  nargs='?', # '?' means 0 or 1 argument.
                        help='configuration python file path',
                        type=argparse.FileType('r'), # Automatically opens the file for reading.
                        default=None)
    args = parser.parse_args()

    # Set up logging. The Colorer module patches StreamHandler for colored output.
    # Set level based on verbose flag.
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Load configuration.
    if args.config is not None:
        logging.info(f"Reading config file: {args.config.name}")
        try:
            # This executes the content of the config file, expecting it to define `global_dict`.
            # WARNING: Using `exec()` with arbitrary file input can be a security risk
            # if the input file source is not trusted.
            exec(args.config.read())
            # Verify that global_dict was actually defined and has a critical key.
            # Accessing a key will raise KeyError if global_dict is not a dict or key is missing.
            _ = global_dict['src_root'] # Simple check.
        except (NameError, KeyError) as e:
            logging.error(f"Error parsing config file '{args.config.name}'. Please ensure it defines 'global_dict' with a 'src_root' key. Exiting.")
            sys.exit(1) # Exit gracefully on error.
        except Exception as e:
            logging.error(f"An unexpected error occurred while reading config file '{args.config.name}': {e}")
            sys.exit(1)
    else:
        logging.info("No config file provided. Using default configuration.")
        # Use the default dictionary defined at the top of this file.
        global_dict = DEFAULT_CONFIG

    # Add dynamic runtime information to the global dictionary.
    global_dict['update_time'] = datetime.now().replace(microsecond=0).isoformat()
    now = datetime.now()
    global_dict['render_year'] = str(now.year)

    # Pass incremental flag from command line to global config.
    global_dict['incremental'] = args.incremental

    # Initialize the ContentTree, which manages the site's content and structure.
    logging.info("Initializing content tree...")
    ctree = ContentTree(global_dict)

    # Step 1: Slurp - Walk the content directory and parse all content files into PageUnit objects.
    logging.info("Step 1: Slurping content files...")
    ctree.slurp_walk()

    # Step 2: Munge - Process the collected page data, establish relationships (parents, children, tags).
    logging.info("Step 2: Munging content relationships and tags...")
    ctree.munge_loop()

    # Step 3: Dump - Generate the static HTML files and copy media.
    if args.dry_run:
        logging.info("Dry run: No output files will be generated.")
    else:
        logging.info("Step 3: Dumping generated content to destination...")
        ctree.dump_loop()

        # Generate RSS feed if configured.
        if 'rss_file' in global_dict:
            logging.info(f"Generating RSS feed: {global_dict['rss_file']}")
            ctree.generate_rss()
        else:
            logging.info("RSS file not configured. Skipping RSS generation.")


        # Generate the upload script (e.g., for FTP/SCP).
        # This method is currently a 'pass' and needs implementation.
        logging.info("Generating upload script (if implemented)...")
        ctree.generate_upload_script()

    logging.info("Static site generation complete.")
