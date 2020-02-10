""" builder.py: static website generator influenced by staceyapp.com
    Copyleft Jonathan Foote 2019
"""

import os
import sys
from datetime import datetime
import argparse
import logging
# color logging output to terminal
import Colorer

# local files:
from content_tree import ContentTree

DEFAULT_CONFIG = {

    # copy files and data starting at this directory
    'src_root':  '/home/jtf/bitb/www/projects-source/content',
    # copy files and data to tree at this root, stuff will start one dir below
    'dest_root': '/home/jtf/bitb/www/new_www/build/',
    # root for html paths where to find css (in "/css subdir")
    'public': '/new/build/public/',

    'html_root': '/new/build/',
    # root for this tree ")
    'html_top': '/new/build/',
    # find templates in this dir
    'template_dir': 'templates',
    'date': '0/0/1970',
    'title': 'default_title',
    'name': 'Jonathan Foote',
    'hostname': 'localhost',
    'month': 'unset',
    'day': 'unset',
    'weekday': 'unset',
    'keywords': 'unset keywords'

}

if __name__ == '__main__':

    # argument parsing stuff
    parser = argparse.ArgumentParser(description='Static site generator.')
    parser.add_argument('--dry_run', '-d',  
                        action='store_true',
                        help='do not generate output')
    parser.add_argument('--verbose','-v',
                        action='store_true',
                        help='verbose flag' )
    parser.add_argument('--incremental','-i',
                        action='store_true',
                        help='only render changed files' )
    parser.add_argument('config',  nargs='?',
                        help='configuration python file',
                        type=argparse.FileType('r'),
                        default=None)
    args = parser.parse_args()


    # set up logging
    logging.basicConfig(level=logging.DEBUG)

    if args.config is not None:
        print("reading config file {}".format(args.config.name))
        exec(args.config.read())
        try:
            foo = global_dict['src_root']
        except (NameError, KeyError) as e:
            logging.error("error parsing config file. Bye.")
            raise e
            exit(1)
    else:
        logging.debug("Using default config")
        # default dict defined at top of this file
        global_dict = DEFAULT_CONFIG

   

    #print(global_dict['src_root'])

    global_dict['update_time'] = datetime.now().replace(microsecond=0).isoformat()
    now = datetime.now()
    global_dict['render_year'] = str(now.year)

    global_dict['incremental'] = args.incremental

    ctree = ContentTree(global_dict)
    ctree.slurp_walk() # walk the content directory, reading the data files
    ctree.munge_loop() # generate tags and cross-links
    if args.dry_run:
        logging.info("dry run: no output files generated.")
    else:
        ctree.dump_loop() #generate output
        #if 'rss_file' in global_dict.keys():
        ctree.generate_rss()
        ctree.generate_upload_script()


