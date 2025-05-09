# Simple Static Site Generator

A lightweight, Python-based static website generator, inspired by [StaceyApp.com](http://staceyapp.com/). This tool allows you to build content-driven websites, such as blogs or project portfolios, from Markdown files and Mako templates.

## Features

* **Markdown Content:** Write your page content using Markdown, with support for additional extensions.
* **Mako Templating:** Leverage the powerful Mako templating engine for flexible page layouts and dynamic content rendering.
* **Directory-based Structure:** Organize your content using a simple `[number].[slug]/` directory convention for automatic hierarchy and sorting.
* **Automatic Navigation:** Generates parent-child relationships and page levels for easy breadcrumb navigation.
* **Tagging System:** Categorize your content with tags, and the generator automatically creates dedicated tag pages.
* **Media Handling:** Automatically copies images and other media files from your source directories to the generated site.
* **RSS Feed Generation:** Creates an Atom/RSS feed for your blog or latest content.
* **Configurable:** Easily customize source and destination paths, templates, and site metadata via Python configuration files.
* **Incremental Builds:** Option to render only changed files for faster updates.
* **Command-Line Interface:** Supports dry runs, verbose output, and configurable input.
* **Colored Logging:** Provides colored terminal output for better readability of logs (Errors, Warnings, Info, Debug).

## Usage

To use the static site generator, run the `builder.py` script from your terminal.

```bash
python builder.py [options] [config_file]
```

### Command-Line Options:

* `--dry_run`, `-d`: Do not generate any output files. This is useful for testing your configuration and content parsing without modifying the destination directory.
* `--verbose`, `-v`: Enable verbose logging output, showing more detailed information about the build process.
* `--incremental`, `-i`: Only render files that have changed since the last build. This can significantly speed up build times for large sites.
* `config`: (Optional) Path to a Python configuration file. If not provided, the `DEFAULT_CONFIG` defined within `builder.py` will be used.

### Examples:

* **Generate a site using the default configuration:**
    ```bash
    python builder.py
    ```
* **Generate a blog using a specific configuration file:**
    ```bash
    python builder.py blog_config.py
    ```
* **Perform a dry run with verbose output for a projects site:**
    ```bash
    python builder.py --dry_run -v proj_config.py
    ```
* **Incrementally update your site:**
    ```bash
    python builder.py -i blog_config.py
    ```

## Configuration

The generator uses Python files for configuration, which define global variables influencing the build process. An example is provided in `blog_config.py` and `proj_config.py`.

A configuration file defines a `global_dict` dictionary with various parameters:

```python
global_dict = {
    'src_root':  '/home/jtf/gith/www_source/0.blog-source/', # Source directory containing your content.
    'dest_root': '/home/jtf/www/blog/',                     # Destination directory for the generated HTML.
    'public': '/public',                                    # Root for HTML paths to find CSS/public assets.
    'html_root': '/blog/',                                  # Base HTML path for internal links.
    'html_top': '/www/blog/',                               # HTML root for this specific site tree (used for top-level page).
    'content_ext': '.md',                                   # File extension for content files (e.g., '.md', '.txt').
    'rss_file': 'feed.rss',                                 # Name of the RSS feed file.
    'rss_icon': '/public/RSSicon.png',                      # Path to the RSS icon.
    'template_dir': '/home/jtf/gith/www_source/0.blog-source/templates', # Directory where Mako templates are located.
    'warn_thumbnail': False,                                # Set to True to warn if 'thumb.*' is not found in a content directory.
    'date': '0/0/1970',                                     # Default date (overridden by content file headers).
    'year': '1970',                                         # Default year (overridden by content file headers).
    'title': 'default_title',                               # Default page title (overridden by content file headers).
    'name': 'Author Name',                                 # Author's name.
    'hostname': 'rotormind.com',                            # Site hostname for permalinks.
    'blog_title': 'Waxing Prolix',                          # Specific title for a blog (optional, site-specific).
    'keywords': 'unset keywords'                            # Default keywords (overridden by content file headers).
}
```

## Content Structure

Your content should be organized in a hierarchical directory structure within the `src_root`. Directories should be prefixed with a number for sorting, followed by a slug.

Example:
```
0.blog-source/
├── 1.about/
│   └── content.md
├── 2024.year/
│   ├── 01.jan/
│   │   ├── my-first-post/
│   │   │   ├── content.md
│   │   │   └── image.jpg
│   │   └── another-post/
│   │       └── content.md
│   └── 02.feb/
│       └── yet-another-post/
│           └── content.md
└── templates/
    ├── default.html
    ├── gallery.html
    ├── leaf.html
    ├── tags.html
    ├── top.html
    ├── feed_header.xml
    └── feed_entry.xml
```

### Content Files (`.md` or `.txt`)

Each content directory should contain a content file (e.g., `content.md`). This file starts with a header section containing key-value pairs, followed by the actual Markdown content, separated by a line containing `content:`.

Example `content.md`:

```
title: My Awesome Blog Post
date: 2024/01/15
template: leaf
tags: programming, python, static site
thumbnail: thumb.jpg
content:
This is the *Markdown content* of my blog post.

It supports **bold** and _italics_.

Here's a list:
- Item 1
- Item 2
```

**Supported Header Keys:**

* `title`: The title of the page.
* `date`: The publication date of the content.
* `template`: (Optional) Specifies which Mako template to use (`default`, `gallery`, `leaf`, etc.). If omitted, the generator tries to infer (`gallery` for directories with children, `leaf` otherwise).
* `tags`: (Optional) Comma-separated list of tags for the content.
* `thumbnail`: (Optional) Filename of a thumbnail image within the same directory.

Any other key-value pairs in the header will also be available to the template.

### Media Files

Place any images (`.jpg`, `.png`, `.gif`, `.webp`, `.svg`), videos (`.mp4`, `.mp3`), or other static assets (`.pdf`, `.html`, `.css`, `.js`) directly within the content directory. They will be copied to the corresponding output directory. If a file named `thumb.*` (e.g., `thumb.jpg`, `thumb.png`) exists, it is recognized as a thumbnail for that page.

## Templates

Templates are Mako HTML/XML files located in the `template_dir` specified in your configuration.

The following variables are available within your templates:

* `global_dict`: The entire `global_dict` from your configuration file, containing site-wide settings.
* `ldict`: A dictionary specific to the current page, including:
    * All key-value pairs from the content file's header (e.g., `ldict['title']`, `ldict['date']`, `ldict['template']`).
    * `ldict['content_html']`: The rendered Markdown content of the current page. Note that this content itself can contain Mako expressions which are rendered before the main page template.
    * `ldict['html_path']`: The relative HTML path for the current page (e.g., `/blog/2024/my-post/`).
    * `ldict['permalink']`: The absolute URL for the current page.
    * `ldict['children']`: A list of `PageUnit` objects representing child pages.
    * `ldict['parents']`: A list of `PageUnit` objects representing parent pages (for breadcrumbs).
    * `ldict['tags']`: A list of tags associated with the current page.
    * `ldict['tag_dict']`: A dictionary mapping tag names to their corresponding virtual `PageUnit` objects.
    * `ldict['images']`: A list of image filenames copied from the current content directory.
    * `ldict['js_files']`: A list of JavaScript filenames copied from the current content directory.
    * `ldict['level']`: The hierarchical level of the current page (e.g., 0 for top, 1 for first-level child).
    * `ldict['render_year']`: The current year when the site is rendered.
    * `ldict['update_time']`: The site update timestamp in ISO format.
* `level1`, `level2`: (From `content_tree.py`) Lists of `PageUnit` objects at the first and second levels of your site hierarchy, useful for top-level navigation or blog year/month lists.
* `tag_dict`: (From `content_tree.py`) A dictionary mapping tag names to their corresponding virtual `PageUnit` objects, useful for generating a tag cloud or list.

**Special Templates:**

* `default.html`: The default template for pages, if not explicitly specified.
* `gallery.html`: Used if `template: default` and the page has children.
* `leaf.html`: Used if `template: default` and the page has no children.
* `tags.html`: Used for rendering the virtual tag pages.
* `top.html`: Used for rendering the top-level page of the site (`html_top`).
* `feed_header.xml`, `feed_entry.xml`: Used to construct the RSS feed.

## Dependencies

This project requires the following Python libraries:

* [`markdown`]([https://pypi.org/project/Markdown/](https://pypi.org/project/Markdown/))
* [`Mako`]([https://pypi.org/project/Mako/](https://pypi.org/project/Mako/))

You can install them using pip:

```bash
pip install markdown Mako
```

