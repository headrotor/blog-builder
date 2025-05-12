# This file defines global configuration settings for the static site generator,
# specifically tailored for a blog.

#TODO: a cleaner way to manage multiple configurations (blog_config.py, proj_config.py) might be to have them return a dictionary rather than relying on exec #to populate a global variable. This would allow for more explicit and safer loading using importlib.util.


global_dict = {

   # --- Directory and Path Configuration ---
   # 'src_root': The absolute path to the root directory where your content source files are located.
   # The generator will start copying files and data from this directory.
   # 'src_root':  '/home/jtf/gith/www_source/0.blog-source/',
    'src_root':  '/home/jtf/www_source/0.blog-source/',

    # --- Templating Configuration ---
    # 'template_dir': The absolute path to the directory where Mako HTML/XML templates are located.
    'template_dir': '/home/jtf/gith/www_source/0.blog-source/templates/',

    # 'dest_root': The absolute path to the root directory where the generated HTML files
    # and associated assets will be written. Content will be placed one level below this root.
    'dest_root': '/home/jtf/www/blog/',

    # 'public': The HTML path root for public assets like CSS and JavaScript.
    # It's usually a path relative to your web server's document root.
    'public': '/public',

    # 'html_root': The base HTML path for internal links within the generated site.
    # All generated HTML paths will be relative to this root.
    'html_root': '/blog/',

    # 'html_top': The specific HTML root for this content tree. This is used for
    # generating the top-level index page for the blog.
    'html_top': '/www/blog/', # Note: This often differs from 'html_root' if blog is a subdir of a larger site.

    # 'content_ext': The file extension used for content files (e.g., '.md' for Markdown).
    'content_ext': '.md',

    # --- RSS Feed Configuration ---
    # 'rss_file': The filename for the generated RSS feed (e.g., 'feed.rss').
    'rss_file': 'feed.rss',
    # 'rss_icon': The HTML path to the RSS feed icon.
    'rss_icon': '/public/RSSicon.png',


    # --- Site Behavior Configuration ---
    # 'warn_thumbnail': Boolean flag. If True, a warning will be logged if a 'thumb.*'
    # file is not found in a content directory.
    'warn_thumbnail':False,

    # --- Default Metadata for Pages (can be overridden by content file headers) ---
    # 'date': Default date to use if not specified in content files.
    'date': '1970-1-1',
    # 'year': Default year.
    'year': '1970',
    # 'title': Default title for pages.
    'title': 'default_title',
    # 'name': Author's name.
    'name': 'Jonathan Foote',
    # 'hostname': The hostname of the website, used for generating absolute permalinks.
    'hostname': 'rotormind.com',
    # 'blog_title': Specific title for the blog section.
    'blog_title': 'Waxing Prolix',
    # True to debug template usage
    'debug_templates': True
    
}

